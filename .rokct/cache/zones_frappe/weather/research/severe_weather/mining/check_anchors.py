"""Feature-library spot-check on 3 named anchor events (machinery validation).

Extracts each anchor's window directly via era5_extract (served from the extraction
read-cache built during anchor validation) and prints key features at fixed hours
before onset, so a human can confirm the physics reads correctly, e.g. does
rain-on-saturated-soil light up before the Ahr 2021 flood?

Scope note: the Ahr 2021 anchor lies in the holdout era (2018+). It is used here
solely to smoke-test feature code on an event whose raw signature was already
examined and published in extraction/ANCHOR_VALIDATION.md BEFORE the acceptance
thresholds froze - it was explicitly requested for this check, no statistic from it
feeds the mining results, and this script bypasses (and does not weaken) the mining
loader's holdout guard. The other two anchors are dev-era.
"""
from __future__ import annotations

import datetime as dt
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "extraction")))
import era5_extract as ex  # noqa: E402

from features import compute_features  # noqa: E402

# (label, class, lat, lon, effective onset UTC, features to show)
ANCHORS = [
    ("Hurricane Katrina 2005 [dev]", "destructive_wind", 26.3, -88.6,
     dt.datetime(2005, 8, 28, 17),
     ["mslp_hpa", "mslp_tend_24h", "mslp_tend_6h", "gust", "gust_delta_6h",
      "tcwv", "precip_sum_24h"]),
    ("Elbe flood 2002 [dev]", "flood", 48.57, 13.03,
     dt.datetime(2002, 8, 7, 0),
     ["precip_sum_24h", "precip_sum_72h", "api_96h", "sm_pct", "sm_sat_ratio",
      "rain_on_sat_24h", "wet_frac_72h"]),
    ("Ahr valley flood 2021 [holdout-era anchor, machinery check only]", "flood",
     51.16, 6.63, dt.datetime(2021, 7, 14, 0),
     ["precip_sum_24h", "precip_sum_72h", "api_96h", "sm_pct", "sm_sat_ratio",
      "rain_on_sat_24h", "rain_on_sat_72h"]),
]

SHOW_REL_H = [-168, -72, -48, -24, -12, -6, 0, 12, 24]


def check_anchor(label, klass, lat, lon, onset, feat_names):
    print(f"\n=== {label} ({klass}) @ {lat},{lon}, onset {onset:%Y-%m-%d %HZ} ===")
    df = ex.extract_window(lat, lon, onset)          # onset-14d .. onset+3d
    feats = compute_features(df)
    onset_i = 336
    header = f"{'feature':>18} | " + " | ".join(f"{h:>7}" for h in SHOW_REL_H)
    print(header)
    print("-" * len(header))
    for ft in feat_names:
        vals = []
        for h in SHOW_REL_H:
            v = feats[ft].iloc[onset_i + h]
            vals.append(f"{v:7.2f}" if np.isfinite(v) else "      -")
        print(f"{ft:>18} | " + " | ".join(vals))
    # "lights up" check: near-onset value vs the feature's own pre-window level
    for ft in feat_names:
        x = feats[ft].to_numpy(dtype=float)
        pre, near = x[:onset_i - 72], x[onset_i - 48:onset_i + 1]
        if not (np.isfinite(pre).any() and np.isfinite(near).any()):
            continue
        base = np.nanpercentile(pre, 95)
        peak = np.nanmax(near)
        lit = "LIGHTS UP" if peak > base else "-"
        print(f"  {ft}: pre-window p95 (t<-72h) = {base:.2f}, "
              f"max in [-48h, 0] = {peak:.2f}  {lit}")


if __name__ == "__main__":
    for anchor in ANCHORS:
        check_anchor(*anchor)
    print("\nanchor spot-check complete")
