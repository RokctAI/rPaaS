"""Bulk-shear candidate features from the 100 m wind top-up extraction.

Extends the conventions of mining/features.py (causal throughout, right-aligned
rolling windows, backward differences, NaN where inputs are NaN, float32 output)
without modifying the committed mining module. Input is one series' hourly window
joined across the two extractions:

  df10  - the main extraction frame (needs wind_u/v_component_10m, wind_speed_10m)
  df100 - the wind100 top-up frame (wind_u/v_component_100m, wind_speed_100m),
          same DatetimeIndex (timestamps align exactly by construction)

The 0-6 km bulk shear that actually discriminates tornado environments is not
observable from ERA5 single levels; |V100 - V10| is the best low-level proxy the
bucket offers (the lowest ~100 m of the storm-relative helicity layer).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

#: feature -> (family, short description), same shape as mining/features.py FEATURES
W100_FEATURES: dict[str, tuple[str, str]] = {
    "bulk_shear":          ("shear100", "|V100 - V10| vector wind difference (m/s)"),
    "bulk_shear_delta_6h": ("shear100", "6 h change in bulk shear (m/s)"),
    "bulk_shear_delta_24h": ("shear100", "24 h change in bulk shear (m/s)"),
    "speed_ratio_100_10":  ("shear100", "100 m / 10 m speed ratio (decoupling proxy)"),
    "dir_veer_levels":     ("shear100", "absolute directional veer between 10 m and 100 m wind (deg)"),
}
W100_FEATURE_NAMES = list(W100_FEATURES)


def compute_wind100_features(df10: pd.DataFrame, df100: pd.DataFrame) -> pd.DataFrame:
    """Shear features for one hourly window; both frames must share their index."""
    if not df10.index.equals(df100.index):
        raise ValueError("df10/df100 index mismatch - timestamps must align exactly")
    f = pd.DataFrame(index=df10.index)
    u10 = df10["wind_u_component_10m"].astype(float)
    v10 = df10["wind_v_component_10m"].astype(float)
    u100 = df100["wind_u_component_100m"].astype(float)
    v100 = df100["wind_v_component_100m"].astype(float)
    s10 = df10["wind_speed_10m"].astype(float)
    s100 = np.hypot(u100, v100)

    shear = np.hypot(u100 - u10, v100 - v10)
    f["bulk_shear"] = shear
    f["bulk_shear_delta_6h"] = shear - shear.shift(6)
    f["bulk_shear_delta_24h"] = shear - shear.shift(24)
    f["speed_ratio_100_10"] = s100 / s10.clip(lower=0.5)

    d10 = pd.Series(np.degrees(np.arctan2(u10, v10)), index=f.index)
    d100 = pd.Series(np.degrees(np.arctan2(u100, v100)), index=f.index)
    veer = ((d100 - d10 + 180.0) % 360.0 - 180.0).abs()
    calm = (s10 < 1.0) | (s100 < 1.0)  # direction is noise in near-calm air
    f["dir_veer_levels"] = veer.where(~calm)

    return f[W100_FEATURE_NAMES].astype(np.float32)
