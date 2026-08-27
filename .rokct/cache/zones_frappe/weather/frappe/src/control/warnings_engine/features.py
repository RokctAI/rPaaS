# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""Causal precursor features for the severe-weather detector - production port.

Ports EXACTLY the features the frozen detector rules reference, with the same
semantics as the research feature library (mining/features.py plus the
neighborhood and 100 m wind top-ups on the research branch): right-aligned
rolling windows with the same min_periods, backward differences, expanding
causal percentiles, NaN wherever history is insufficient. numpy only - no
pandas in production.

Inputs are hourly numpy arrays in the ERA5 storage units documented in the S3
source module (precipitation mm/h, pressure_msl Pa, winds m/s, temperature and
dew point degC, soil moisture m3/m3, TCWV kg/m2).

Features computed (per frozen class rules):
  flood:            precip_sum_24h, precip_sum_48h, rain_on_sat_24h, rain_on_sat_72h
  flash_flood:      tcwv_anom_7d, nbr_rain_on_sat_6h, nbr_max_sum_12h, nbr_wet_frac
  destructive_wind: mslp_tend_24h, gust_max_24h, wspd_10m, tcwv_anom_7d
  tornado:          bulk_shear, theta_e, theta_e_delta_24h, tcwv_anom_7d, mslp_tend_24h
"""
from __future__ import annotations

import numpy as np

WET_THRESHOLD_MM_H = 0.1   # "wet hour" definition (as research)

#: point variables the feature set needs, in ERA5 storage units.
POINT_VARIABLES = (
    "precipitation",
    "soil_moisture_0_to_7cm",
    "pressure_msl",
    "wind_gusts_10m",
    "wind_u_component_10m",
    "wind_v_component_10m",
    "wind_u_component_100m",
    "wind_v_component_100m",
    "temperature_2m",
    "dew_point_2m",
    "total_column_integrated_water_vapour",
)

#: every feature name this module emits.
FEATURE_NAMES = (
    "precip_sum_24h", "precip_sum_48h",
    "rain_on_sat_24h", "rain_on_sat_72h",
    "tcwv_anom_7d",
    "mslp_tend_24h", "gust_max_24h", "wspd_10m",
    "theta_e", "theta_e_delta_24h", "bulk_shear",
    "nbr_rain_on_sat_6h", "nbr_max_sum_12h", "nbr_wet_frac",
)


def _as_f64(x) -> np.ndarray:
    return np.asarray(x, dtype=np.float64)


def rolling_sum(x: np.ndarray, window: int, min_periods: int) -> np.ndarray:
    """Right-aligned NaN-tolerant rolling sum (pandas rolling(...).sum() semantics)."""
    x = _as_f64(x)
    n = x.size
    valid = np.isfinite(x)
    cs = np.concatenate(([0.0], np.cumsum(np.where(valid, x, 0.0))))
    cc = np.concatenate(([0], np.cumsum(valid.astype(np.int64))))
    idx = np.arange(n)
    start = np.maximum(0, idx - window + 1)
    sums = cs[idx + 1] - cs[start]
    counts = cc[idx + 1] - cc[start]
    out = np.where(counts >= min_periods, sums, np.nan)
    return out


def rolling_mean(x: np.ndarray, window: int, min_periods: int) -> np.ndarray:
    """Right-aligned NaN-tolerant rolling mean over valid values."""
    x = _as_f64(x)
    n = x.size
    valid = np.isfinite(x)
    cs = np.concatenate(([0.0], np.cumsum(np.where(valid, x, 0.0))))
    cc = np.concatenate(([0], np.cumsum(valid.astype(np.int64))))
    idx = np.arange(n)
    start = np.maximum(0, idx - window + 1)
    sums = cs[idx + 1] - cs[start]
    counts = (cc[idx + 1] - cc[start]).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        means = sums / counts
    return np.where(counts >= min_periods, means, np.nan)


def rolling_max(x: np.ndarray, window: int, min_periods: int) -> np.ndarray:
    """Right-aligned NaN-tolerant rolling max over valid values."""
    x = _as_f64(x)
    n = x.size
    out = np.full(n, np.nan)
    for i in range(n):
        seg = x[max(0, i - window + 1): i + 1]
        finite = seg[np.isfinite(seg)]
        if finite.size >= min_periods:
            out[i] = finite.max()
    return out


def backward_diff(x: np.ndarray, hours: int) -> np.ndarray:
    """x[t] - x[t-hours]; NaN where either endpoint is missing."""
    x = _as_f64(x)
    out = np.full(x.size, np.nan)
    if x.size > hours:
        out[hours:] = x[hours:] - x[:-hours]
    return out


def causal_percentile(x: np.ndarray, min_history: int = 48) -> np.ndarray:
    """Percentile of x[t] among its own past values x[0..t] (expanding, causal).

    NaN where x[t] is NaN or fewer than min_history valid past values exist.
    Same definition as the research library.
    """
    x = _as_f64(x)
    n = x.size
    out = np.full(n, np.nan)
    valid = np.isfinite(x)
    with np.errstate(invalid="ignore"):
        le = x[None, :] <= x[:, None]          # le[i, j]: x[j] <= x[i]
    past = np.tril(np.ones((n, n), dtype=bool))  # j <= i
    m = past & valid[None, :]
    cnt = (le & m).sum(axis=1).astype(np.float64)
    tot = m.sum(axis=1).astype(np.float64)
    ok = valid & (tot >= min_history)
    out[ok] = cnt[ok] / tot[ok]
    return out


def theta_e_proxy(t_c: np.ndarray, td_c: np.ndarray, p_hpa: np.ndarray) -> np.ndarray:
    """Surface equivalent potential temperature, Bolton-style approximation (K)."""
    t_c, td_c, p_hpa = _as_f64(t_c), _as_f64(td_c), _as_f64(p_hpa)
    t_k = t_c + 273.15
    e = 6.112 * np.exp(17.67 * td_c / (td_c + 243.5))      # vapour pressure, hPa
    r = 0.622 * e / np.clip(p_hpa - e, 1.0, None)          # mixing ratio, kg/kg
    return (t_k + 2.501e6 / 1005.7 * r) * (1000.0 / p_hpa) ** 0.2854


def compute_features(series: dict, nbr_precip=None) -> dict:
    """Compute every feature the frozen rules reference.

    series:     mapping variable name -> hourly numpy array (aligned, same
                length), keys per POINT_VARIABLES, ERA5 storage units.
    nbr_precip: optional (n, k) array of neighborhood precipitation cells
                (mm/h, one column per grid cell in the 7x7 box, off-grid
                cells NaN). When None the nbr_* features are all-NaN, which
                de-arms the flash_flood neighborhood conditions (no alarm,
                never a crash).

    Returns {feature_name: numpy float64 array}.
    """
    missing = [v for v in POINT_VARIABLES if v not in series]
    if missing:
        raise KeyError(f"variables not provided: {missing}")
    p = _as_f64(series["precipitation"])
    n = p.size
    f: dict = {}

    # -- rainfall accumulations (min_periods = max(2, 75% of window)) --
    sum24 = rolling_sum(p, 24, max(2, int(24 * 0.75)))
    sum48 = rolling_sum(p, 48, max(2, int(48 * 0.75)))
    sum72 = rolling_sum(p, 72, max(2, int(72 * 0.75)))
    f["precip_sum_24h"] = sum24
    f["precip_sum_48h"] = sum48

    # -- soil-moisture percentile and rain-on-saturated-soil interactions --
    sm_pct = causal_percentile(_as_f64(series["soil_moisture_0_to_7cm"]))
    f["rain_on_sat_24h"] = sum24 * sm_pct
    f["rain_on_sat_72h"] = sum72 * sm_pct

    # -- moisture --
    tcwv = _as_f64(series["total_column_integrated_water_vapour"])
    f["tcwv_anom_7d"] = tcwv - rolling_mean(tcwv, 168, 120)

    # -- pressure (Pa -> hPa) and wind --
    mslp_hpa = _as_f64(series["pressure_msl"]) / 100.0
    f["mslp_tend_24h"] = backward_diff(mslp_hpa, 24)
    f["gust_max_24h"] = rolling_max(_as_f64(series["wind_gusts_10m"]), 24, 18)
    u10 = _as_f64(series["wind_u_component_10m"])
    v10 = _as_f64(series["wind_v_component_10m"])
    f["wspd_10m"] = np.hypot(u10, v10)

    # -- instability / shear proxies --
    th_e = theta_e_proxy(_as_f64(series["temperature_2m"]),
                         _as_f64(series["dew_point_2m"]), mslp_hpa)
    f["theta_e"] = th_e
    f["theta_e_delta_24h"] = backward_diff(th_e, 24)
    u100 = _as_f64(series["wind_u_component_100m"])
    v100 = _as_f64(series["wind_v_component_100m"])
    f["bulk_shear"] = np.hypot(u100 - u10, v100 - v10)

    # -- neighborhood rain (7x7 cells around the point) --
    if nbr_precip is not None:
        cells = _as_f64(nbr_precip)
        if cells.ndim != 2 or cells.shape[0] != n:
            raise ValueError("nbr_precip must be (n_hours, n_cells)")
        # per-cell causal accumulations, then reduce across cells
        min6 = max(2, int(6 * 0.75))
        min12 = max(2, int(12 * 0.75))
        sums6 = np.column_stack([rolling_sum(cells[:, j], 6, min6)
                                 for j in range(cells.shape[1])])
        sums12 = np.column_stack([rolling_sum(cells[:, j], 12, min12)
                                  for j in range(cells.shape[1])])
        nbr_max6 = _nan_row_max(sums6)
        f["nbr_max_sum_12h"] = _nan_row_max(sums12)
        f["nbr_rain_on_sat_6h"] = nbr_max6 * sm_pct
        n_valid = np.isfinite(cells).sum(axis=1).astype(np.float64)
        n_valid[n_valid == 0] = np.nan
        with np.errstate(invalid="ignore"):
            f["nbr_wet_frac"] = (cells > WET_THRESHOLD_MM_H).sum(axis=1) / n_valid
    else:
        nan = np.full(n, np.nan)
        f["nbr_max_sum_12h"] = nan.copy()
        f["nbr_rain_on_sat_6h"] = nan.copy()
        f["nbr_wet_frac"] = nan.copy()

    return f


def _nan_row_max(a: np.ndarray) -> np.ndarray:
    """Row-wise max ignoring NaN; NaN where a row has no finite value."""
    out = np.full(a.shape[0], np.nan)
    any_finite = np.isfinite(a).any(axis=1)
    if any_finite.any():
        with np.errstate(all="ignore"):
            out[any_finite] = np.nanmax(a[any_finite], axis=1)
    return out
