"""Displaced-rain candidate features from the 7x7 neighborhood-precipitation top-up.

Motivation (extraction/ANCHOR_VALIDATION.md): for the flood classes the ERA5
precipitation maximum sits a median ~0.6 deg from the catalog point, so point
features systematically miss the causal rain. These features let each hour take
the strongest precipitation signal anywhere in the +-0.75 deg neighborhood.

Extends the conventions of mining/features.py (causal throughout, right-aligned
rolling windows with min_periods, NaN where history is insufficient, float32
output) without modifying the committed mining module. Inputs for one series:

  nbr    - neighborhood frame from series/nbr_precip/ (hourly DatetimeIndex,
           49 float32 columns p{r}{c}, r,c in 0..6: precip in mm/h at grid offset
           dlat = r-3, dlon = c-3; p33 is the series' own point; off-grid
           latitudes are NaN and are simply excluded cell-wise)
  sm_pct - optional causal soil-moisture percentile series from the POINT
           extraction (mining/features.py "sm_pct", same index); when given, the
           rain-on-saturated-soil interactions are emitted.

Cell-wise rolling sums are computed per cell first, then reduced across cells,
so nbr_max_sum_Wh = max over the 49 cells of each cell's OWN W-hour accumulation
(the displaced-maximum reading), not the sum of a per-hour spatial max.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

WET_THRESHOLD_MM_H = 0.1     # same "wet hour" definition as mining/features.py
SUM_WINDOWS = (6, 12, 24, 48, 72)
RAINSAT_WINDOWS = (6, 24, 72)

#: feature -> (family, short description), same shape as mining/features.py FEATURES
NBR_FEATURES: dict[str, tuple[str, str]] = {
    **{f"nbr_max_sum_{w}h":
       ("nbr_rain", f"max over 7x7 cells of the cell's own {w} h rain accumulation (mm)")
       for w in SUM_WINDOWS},
    **{f"nbr_p90_sum_{w}h":
       ("nbr_rain", f"90th pct over 7x7 cells of the cell's own {w} h rain accumulation (mm)")
       for w in SUM_WINDOWS},
    "nbr_wet_frac":     ("nbr_extent", f"fraction of 7x7 cells with precip > {WET_THRESHOLD_MM_H} mm/h now"),
    "nbr_wet_frac_24h": ("nbr_extent", "fraction of 7x7 cells with > 1 mm rain in the last 24 h"),
    **{f"nbr_rain_on_sat_{w}h":
       ("nbr_interaction", f"nbr_max {w} h accumulation x point soil-moisture percentile")
       for w in RAINSAT_WINDOWS},
}
NBR_FEATURE_NAMES = list(NBR_FEATURES)

CELL_COLS = [f"p{r}{c}" for r in range(7) for c in range(7)]


def compute_nbr_features(nbr: pd.DataFrame, sm_pct: pd.Series | None = None,
                         ) -> pd.DataFrame:
    """Neighborhood features for one hourly window (index preserved)."""
    cells = nbr[CELL_COLS].astype(np.float32)
    f = pd.DataFrame(index=nbr.index)

    for w in SUM_WINDOWS:
        # per-cell causal accumulation, tolerating up to 25% NaN gaps (as features.py)
        sums = cells.rolling(w, min_periods=max(2, int(w * 0.75))).sum()
        a = sums.to_numpy()
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN leading rows
            f[f"nbr_max_sum_{w}h"] = np.nanmax(a, axis=1, initial=-np.inf)
            f[f"nbr_p90_sum_{w}h"] = np.nanpercentile(a, 90, axis=1)
        f.loc[~np.isfinite(f[f"nbr_max_sum_{w}h"]), f"nbr_max_sum_{w}h"] = np.nan

    vals = cells.to_numpy()
    n_valid = np.isfinite(vals).sum(axis=1).astype(float)
    n_valid[n_valid == 0] = np.nan
    with np.errstate(invalid="ignore"):
        f["nbr_wet_frac"] = (vals > WET_THRESHOLD_MM_H).sum(axis=1) / n_valid

    sums24 = cells.rolling(24, min_periods=18).sum().to_numpy()
    n24 = np.isfinite(sums24).sum(axis=1).astype(float)
    n24[n24 == 0] = np.nan
    with np.errstate(invalid="ignore"):
        f["nbr_wet_frac_24h"] = (sums24 > 1.0).sum(axis=1) / n24

    for w in RAINSAT_WINDOWS:
        if sm_pct is not None:
            f[f"nbr_rain_on_sat_{w}h"] = f[f"nbr_max_sum_{w}h"] * sm_pct.astype(float)
        else:
            f[f"nbr_rain_on_sat_{w}h"] = np.nan

    return f[NBR_FEATURE_NAMES].astype(np.float32)
