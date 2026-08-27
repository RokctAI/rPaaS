"""Blind case-study runner: frozen detector over multi-decade Limpopo basin series.

Protocol:
  * Config: detector/detector_config_tuned.json - FROZEN (tuned on the pre-2018
    global dev cohort only). Loaded read-only; nothing here writes or alters it.
  * Features: mining/features.py + extraction/nbr_features.py +
    extraction/wind100_features.py, computed causally over the full series.
  * ONE documented deviation, forced by scale: mining/features.py computes sm_pct
    (causal soil-moisture percentile) by an O(n^2) broadcast that is only viable
    on 408-h event windows. On a 277,000-h continuous series we substitute a
    TRAILING 408-h rolling percentile (same "fraction of history <= current
    value" definition, method='max' rank, min 48 valid hours) - 408 h is exactly
    the dev-window length, so the amount of history behind each percentile
    matches the tuned regime as closely as a continuous run allows. Still fully
    causal. No thresholds were touched.

Outputs (in this directory):
  alarms.csv            every warning-tier episode, all points/eras/classes
  features/<pt>_<era>.parquet   full causal feature frames (for the precursor
                                timelines in the report; not committed)

Usage: python3 run_detector.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
for sub in ("mining", "extraction", "detector"):
    p = os.path.join(ROOT, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

import features as feat_mod                       # noqa: E402
from nbr_features import compute_nbr_features     # noqa: E402
from wind100_features import compute_wind100_features  # noqa: E402
import detector                                   # noqa: E402
from extract_limpopo import POINTS, ERAS          # noqa: E402

CONFIG = os.path.join(ROOT, "detector", "detector_config_tuned.json")
SERIES = os.path.join(HERE, "series")
FEAT_DIR = os.path.join(HERE, "features")
DEV_WINDOW_H = 408   # dev event-window length -> trailing percentile history


def rolling_causal_percentile(x: np.ndarray, min_history: int = 48) -> np.ndarray:
    """Trailing-408h stand-in for features.causal_percentile (see module docstring)."""
    s = pd.Series(x)
    return (s.rolling(DEV_WINDOW_H, min_periods=min_history)
             .rank(method="max", pct=True).to_numpy())


def compute_all_features(df: pd.DataFrame, nbr: pd.DataFrame) -> pd.DataFrame:
    orig = feat_mod.causal_percentile
    feat_mod.causal_percentile = rolling_causal_percentile   # documented deviation
    try:
        f = feat_mod.compute_features(df)
    finally:
        feat_mod.causal_percentile = orig
    f = f.join(compute_wind100_features(df, df[[
        "wind_u_component_100m", "wind_v_component_100m"]]))
    f = f.join(compute_nbr_features(nbr, sm_pct=f["sm_pct"]))
    return f


def main():
    os.makedirs(FEAT_DIR, exist_ok=True)
    rules = detector.load_config(CONFIG)
    rows = []
    for name, lat, lon in POINTS:
        for era in ERAS:
            base = os.path.join(SERIES, f"{name}_{era}")
            df = pd.read_parquet(base + ".parquet")
            nbr = pd.read_parquet(base + "_nbr.parquet")
            fpath = os.path.join(FEAT_DIR, f"{name}_{era}.parquet")
            if os.path.exists(fpath):
                f = pd.read_parquet(fpath)
            else:
                f = compute_all_features(df, nbr)
                f.to_parquet(fpath, compression="zstd")
            times = list(f.index)
            for klass, rule in rules.items():
                cols = {n: f[n].astype(float).tolist() for n in rule.feature_names}
                res = detector.run_class(times, cols, rule)
                for a in res.alarms:
                    rows.append({
                        "point": name, "era": era, "event_class": klass,
                        "first_fired_at": a.first_fired_at,
                        "last_active_at": a.last_active_at,
                        "max_severity": a.max_severity,
                        "max_confidence": round(a.max_confidence, 3),
                        "fired_conditions": "|".join(a.fired_conditions)})
                print(f"{name}/{era}/{klass}: {len(res.alarms)} alarms", flush=True)
    out = pd.DataFrame(rows).sort_values(["first_fired_at", "point"])
    out.to_csv(os.path.join(HERE, "alarms.csv"), index=False)
    print(f"total warning episodes: {len(out)} -> alarms.csv")


if __name__ == "__main__":
    main()
