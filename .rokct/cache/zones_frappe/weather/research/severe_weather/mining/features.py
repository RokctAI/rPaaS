"""Candidate precursor feature library for severe-weather signature mining.

Input: one extracted window as an hourly DataFrame (UTC DatetimeIndex, the 13 value
columns produced by the extraction - units per extraction/ANCHOR_VALIDATION.md;
pressure_msl is stored in Pa and converted to hPa here).

Every feature is CAUSAL: the value at time t uses only data at times <= t (rolling
windows are right-aligned, tendencies are backward differences, percentiles are
computed against the series' own expanding history). NaN gaps (the documented
missing chunks) are tolerated: rolling statistics use min_periods, recursive
features skip gaps, and features stay NaN where history is insufficient - the
mining harness drops NaNs per comparison.

Known limitation (follow-up): the extraction variable set has no 100 m wind
components, so the requested |V100-V10| shear proxy cannot be computed; gust_factor
(gust / mean speed) and dir_veer_6h (10 m directional veer over 6 h) stand in as
shear/mixing proxies until a 100 m top-up extraction is run.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

WET_THRESHOLD_MM_H = 0.1   # "wet hour" definition
API_HALFLIFE_H = 96        # antecedent precipitation index decay half-life (4 days)

#: feature -> (family, short description). The report generator uses both.
FEATURES: dict[str, tuple[str, str]] = {
    "precip_1h":        ("rain", "hourly precipitation (mm/h)"),
    "precip_sum_3h":    ("rain", "3 h rainfall accumulation (mm)"),
    "precip_sum_6h":    ("rain", "6 h rainfall accumulation (mm)"),
    "precip_sum_12h":   ("rain", "12 h rainfall accumulation (mm)"),
    "precip_sum_24h":   ("rain", "24 h rainfall accumulation (mm)"),
    "precip_sum_48h":   ("rain", "48 h rainfall accumulation (mm)"),
    "precip_sum_72h":   ("rain", "72 h rainfall accumulation (mm)"),
    "api_96h":          ("wetness", "antecedent precipitation index (exp decay, 96 h half-life)"),
    "wet_spell_h":      ("wetness", f"consecutive hours with precip > {WET_THRESHOLD_MM_H} mm/h"),
    "wet_frac_72h":     ("wetness", "fraction of the last 72 h that was wet"),
    "sm_0_7":           ("soil", "soil moisture 0-7 cm (m3/m3)"),
    "sm_delta_7d":      ("soil", "7-day change in soil moisture 0-7 cm"),
    "sm_pct":           ("soil", "causal percentile of soil moisture within own window history"),
    "sm_sat_ratio":     ("soil", "soil moisture / running max of own history (saturation proxy)"),
    "sm_7_28":          ("soil", "soil moisture 7-28 cm (m3/m3)"),
    "sm2_delta_7d":     ("soil", "7-day change in soil moisture 7-28 cm"),
    "mslp_hpa":         ("pressure", "mean sea-level pressure (hPa)"),
    "mslp_tend_3h":     ("pressure", "3 h MSLP tendency (hPa)"),
    "mslp_tend_6h":     ("pressure", "6 h MSLP tendency (hPa)"),
    "mslp_tend_24h":    ("pressure", "24 h MSLP tendency (hPa)"),
    "gust":             ("wind", "10 m wind gust (m/s)"),
    "gust_delta_6h":    ("wind", "6 h gust change (m/s)"),
    "gust_max_24h":     ("wind", "max gust over the last 24 h (m/s)"),
    "wspd_10m":         ("wind", "10 m mean wind speed (m/s)"),
    "wspd_delta_6h":    ("wind", "6 h mean-wind change (m/s)"),
    "gust_factor":      ("shear", "gust / mean 10 m speed (gustiness-mixing proxy; no 100 m wind extracted)"),
    "dir_veer_6h":      ("shear", "absolute 10 m wind-direction change over 6 h (deg)"),
    "dewpoint_dep":     ("moisture", "dew-point depression T - Td (K)"),
    "theta_e":          ("moisture", "surface equivalent potential temperature proxy (K, Bolton approx)"),
    "theta_e_delta_24h": ("moisture", "24 h change in theta-e proxy (K)"),
    "tcwv":             ("moisture", "total column water vapour (kg/m2)"),
    "tcwv_anom_7d":     ("moisture", "TCWV minus its own 7-day rolling mean (kg/m2)"),
    "blh":              ("boundary_layer", "boundary layer height (m)"),
    "blh_delta_24h":    ("boundary_layer", "24 h change in boundary layer height (m)"),
    "snow_accum_14d":   ("snow", "14-day snowfall water-equivalent accumulation (mm)"),
    "snowmelt_proxy":   ("snow", "T2m above 0 C when antecedent snowfall > 1 mm WE (melt-degree proxy)"),
    "rain_on_sat_6h":   ("interaction", "6 h rain accumulation x soil-moisture percentile"),
    "rain_on_sat_24h":  ("interaction", "24 h rain accumulation x soil-moisture percentile"),
    "rain_on_sat_72h":  ("interaction", "72 h rain accumulation x soil-moisture percentile"),
}
FEATURE_NAMES = list(FEATURES)


def _run_length_wet(p: np.ndarray) -> np.ndarray:
    """Consecutive wet hours ending at each t (NaN precip counts as dry)."""
    wet = np.nan_to_num(p, nan=0.0) > WET_THRESHOLD_MM_H
    idx = np.arange(p.size)
    last_dry = np.maximum.accumulate(np.where(wet, -1, idx))
    return np.where(wet, idx - last_dry, 0).astype(float)


def causal_percentile(x: np.ndarray, min_history: int = 48) -> np.ndarray:
    """Percentile of x[t] among its own past values x[0..t] (expanding, causal).

    Returns NaN where x[t] is NaN or fewer than min_history valid past values exist.
    O(n^2) by broadcast - fine for 408-hour windows.
    """
    n = x.size
    out = np.full(n, np.nan)
    valid = np.isfinite(x)
    with np.errstate(invalid="ignore"):
        le = x[None, :] <= x[:, None]          # le[i, j]: x[j] <= x[i]
    past = np.tril(np.ones((n, n), dtype=bool))  # j <= i
    m = past & valid[None, :]
    cnt = (le & m).sum(axis=1).astype(float)
    tot = m.sum(axis=1).astype(float)
    ok = valid & (tot >= min_history)
    out[ok] = cnt[ok] / tot[ok]
    return out


def _theta_e_proxy(t_c: pd.Series, td_c: pd.Series, p_hpa: pd.Series) -> pd.Series:
    """Surface equivalent potential temperature, Bolton-style approximation (K)."""
    t_k = t_c + 273.15
    e = 6.112 * np.exp(17.67 * td_c / (td_c + 243.5))      # vapour pressure, hPa
    r = 0.622 * e / (p_hpa - e).clip(lower=1.0)            # mixing ratio, kg/kg
    return (t_k + 2.501e6 / 1005.7 * r) * (1000.0 / p_hpa) ** 0.2854


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """All candidate precursor features for one hourly window. Causal throughout."""
    f = pd.DataFrame(index=df.index)
    p = df["precipitation"].astype(float)

    # -- rainfall accumulations (right-aligned rolling sums; tolerate 25% gaps) --
    f["precip_1h"] = p
    for w in (3, 6, 12, 24, 48, 72):
        f[f"precip_sum_{w}h"] = p.rolling(w, min_periods=max(2, int(w * 0.75))).sum()

    # -- antecedent wetness --
    alpha = 1.0 - 0.5 ** (1.0 / API_HALFLIFE_H)
    # recursive API_t = k*API_{t-1} + P_t == unnormalized causal EWM; gaps treated as dry
    f["api_96h"] = p.fillna(0.0).ewm(alpha=alpha, adjust=False).mean() / alpha
    f.loc[p.isna() & (p.notna().cumsum() == 0), "api_96h"] = np.nan  # leading gap
    f["wet_spell_h"] = _run_length_wet(p.to_numpy())
    f["wet_frac_72h"] = ((p > WET_THRESHOLD_MM_H).astype(float).where(p.notna())
                         .rolling(72, min_periods=54).mean())

    # -- soil moisture --
    sm = df["soil_moisture_0_to_7cm"].astype(float)
    sm2 = df["soil_moisture_7_to_28cm"].astype(float)
    f["sm_0_7"] = sm
    f["sm_delta_7d"] = sm - sm.shift(168)
    f["sm_pct"] = causal_percentile(sm.to_numpy())
    runmax = sm.expanding(min_periods=24).max()
    f["sm_sat_ratio"] = sm / runmax.where(runmax > 1e-6)
    f["sm_7_28"] = sm2
    f["sm2_delta_7d"] = sm2 - sm2.shift(168)

    # -- pressure (Pa -> hPa) --
    mslp = df["pressure_msl"].astype(float) / 100.0
    f["mslp_hpa"] = mslp
    for w in (3, 6, 24):
        f[f"mslp_tend_{w}h"] = mslp - mslp.shift(w)

    # -- wind --
    g = df["wind_gusts_10m"].astype(float)
    ws = df["wind_speed_10m"].astype(float)
    f["gust"] = g
    f["gust_delta_6h"] = g - g.shift(6)
    f["gust_max_24h"] = g.rolling(24, min_periods=18).max()
    f["wspd_10m"] = ws
    f["wspd_delta_6h"] = ws - ws.shift(6)
    f["gust_factor"] = g / ws.clip(lower=0.5)

    u = df["wind_u_component_10m"].astype(float)
    v = df["wind_v_component_10m"].astype(float)
    wdir = pd.Series(np.degrees(np.arctan2(u, v)), index=df.index)
    dd = (wdir - wdir.shift(6) + 180.0) % 360.0 - 180.0
    veer = dd.abs()
    calm = (ws < 1.0) | (ws.shift(6) < 1.0)   # direction is noise in near-calm air
    f["dir_veer_6h"] = veer.where(~calm)

    # -- moisture / instability proxies --
    t = df["temperature_2m"].astype(float)
    td = df["dew_point_2m"].astype(float)
    f["dewpoint_dep"] = t - td
    th_e = _theta_e_proxy(t, td, mslp)
    f["theta_e"] = th_e
    f["theta_e_delta_24h"] = th_e - th_e.shift(24)
    tcwv = df["total_column_integrated_water_vapour"].astype(float)
    f["tcwv"] = tcwv
    f["tcwv_anom_7d"] = tcwv - tcwv.rolling(168, min_periods=120).mean()

    # -- boundary layer --
    blh = df["boundary_layer_height"].astype(float)
    f["blh"] = blh
    f["blh_delta_24h"] = blh - blh.shift(24)

    # -- snow / melt --
    sn = df["snowfall_water_equivalent"].astype(float)
    accum = sn.rolling(336, min_periods=240).sum()
    f["snow_accum_14d"] = accum
    f["snowmelt_proxy"] = t.clip(lower=0.0).where(accum.notna()) * (accum > 1.0)

    # -- interactions: rain falling on saturated soil --
    for w in (6, 24, 72):
        f[f"rain_on_sat_{w}h"] = f[f"precip_sum_{w}h"] * f["sm_pct"]

    return f[FEATURE_NAMES].astype(np.float32)
