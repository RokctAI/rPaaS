"""THE single gated holdout backtest of the frozen tuned config.

Mirrors run_backtest_dev.py exactly (same backtest.run_backtest scoring path,
same combined point + w100 bulk-shear + nbr neighborhood feature construction
that produced the dev results of record) but for the holdout cohort, behind
backtest.holdout_gate (single use, tamper-evident marker).

Modes:
  python3 run_backtest_holdout.py --dry-run-dev   # mechanics rehearsal on DEV
      (patched loader, all 4 classes, max_events=15, scratch output dir;
       plus holdout pre-flight checks that touch METADATA only - the gate and
       every holdout series/top-up file stay untouched)
  python3 run_backtest_holdout.py --execute --holdout --i-understand-single-use
      THE run. Writes results_holdout/ + HOLDOUT_RUN_MARKER.json and a cache
      pickle (rows/metrics/hazard/armed) so post-hoc breakdowns of the SAME
      run need no further holdout data access.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACTION_DIR = os.path.normpath(os.path.join(HERE, "..", "extraction"))
for p in (HERE, os.path.normpath(os.path.join(HERE, "..", "mining")),
          EXTRACTION_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import backtest
import data
from features import compute_features
from wind100_features import compute_wind100_features, W100_FEATURE_NAMES
from nbr_features import compute_nbr_features, NBR_FEATURE_NAMES

CONFIG = os.path.join(HERE, "detector_config_tuned.json")
FROZEN_CONFIG_SHA256 = ("758ba92bb6ce69c11fc6586c2f64722321e51d19d4c86490"
                        "6cbead9046162ac8")
W100_DIR = os.path.join(EXTRACTION_DIR, "series", "wind100")
NBR_DIR = os.path.join(EXTRACTION_DIR, "series", "nbr_precip")

#: side-channel capture for post-hoc slicing of the SAME single run
CAPTURE: dict = {}


def _by_sid(path: str, keep: set) -> dict:
    if not os.path.exists(path):
        return {}
    df = pd.read_parquet(path)
    return {sid: g.set_index("time")
            for sid, g in df.groupby("series_id", sort=False) if sid in keep}


def load_cohort_full_any(event_class: str, cohort: str = "dev",
                         max_events: int | None = None, verbose: bool = False):
    """Combined full-feature loader for either cohort.

    dev     -> identical construction to combined_loader.load_cohort_full
               (the dev results of record).
    holdout -> point series via backtest._load_holdout_series (refuses unless
               the single-use gate has been passed) + the *_holdout_* top-up
               files, joined exactly as on dev.
    """
    if cohort == "dev":
        series = data.load_series(event_class, max_events=max_events,
                                  verbose=verbose)
        manifest = data.load_manifest()
    elif cohort == "holdout":
        series = backtest._load_holdout_series(event_class)   # gate-enforced
        manifest = data._read_manifest_raw()
        manifest = manifest[manifest["cohort"] == "holdout"]
    else:
        raise ValueError(f"unknown cohort {cohort!r}")
    rows = manifest[manifest["series_id"].isin(series.keys())].copy()
    keep = set(series)
    w100 = _by_sid(os.path.join(
        W100_DIR, f"{event_class}_{cohort}_w100.parquet"), keep)
    nbr = _by_sid(os.path.join(
        NBR_DIR, f"{event_class}_{cohort}_nbr.parquet"), keep)
    feats, hazard = {}, {}
    for sid, df in series.items():
        f = compute_features(df)
        g = w100.get(sid)
        if g is not None:
            g = g[~g.index.duplicated()].reindex(df.index)
            f = f.join(compute_wind100_features(df, g))
        else:
            for name in W100_FEATURE_NAMES:
                f[name] = np.nan
        g = nbr.get(sid)
        if g is not None:
            g = g[~g.index.duplicated()].reindex(df.index)
            f = f.join(compute_nbr_features(g, sm_pct=f["sm_pct"]))
        else:
            for name in NBR_FEATURE_NAMES:
                f[name] = np.nan
        feats[sid] = f
        hazard[sid] = {"times": f.index,
                       "gust": df["wind_gusts_10m"].to_numpy(np.float32),
                       "p24": f["precip_sum_24h"].to_numpy(np.float32)}
    CAPTURE[event_class] = {"rows": rows, "hazard": hazard}
    if verbose:
        print(f"{event_class}: w100 {len(w100)}, nbr {len(nbr)} "
              f"of {len(series)} series")
    return rows, feats


backtest.load_cohort = load_cohort_full_any

_orig_score_class = backtest.score_class


def _capturing_score_class(klass, rows, results):
    """Capture the class's own detector results (armed-hour counts on controls
    for the post-hoc budget note) before scoring - same values, zero change."""
    cap = CAPTURE.get(klass)
    if cap is not None and "armed" not in cap:
        ct = rows[rows["role"] == "control"]
        armed = {"hours": 0, "watch_plus": 0, "warning_plus": 0}
        for r in ct.itertuples():
            res = results.get(r.series_id)
            if res is None:
                continue
            armed["hours"] += len(res.tier)
            armed["watch_plus"] += sum(1 for t in res.tier if t >= 1)
            armed["warning_plus"] += sum(1 for t in res.tier if t >= 2)
        cap["armed"] = armed
    return _orig_score_class(klass, rows, results)


backtest.score_class = _capturing_score_class


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def preflight() -> None:
    """Everything checkable without touching the gate or any holdout series."""
    assert _sha256(CONFIG) == FROZEN_CONFIG_SHA256, \
        "detector_config_tuned.json does not match the frozen sha256"
    assert not os.path.exists(backtest.MARKER_PATH), \
        "HOLDOUT_RUN_MARKER.json already exists - the single run is spent"
    import pyarrow.parquet as pq
    m = data._read_manifest_raw()
    h = m[m["cohort"] == "holdout"]
    for klass in backtest.FROZEN:
        n = (h["event_class"] == klass).sum()
        f = pq.ParquetFile(os.path.join(data.SERIES_DIR,
                                        f"{klass}_holdout.parquet"))
        assert f.metadata.num_rows == n * 408, \
            f"{klass}: holdout parquet rows != manifest series x 408"
    for path, ref in [
            (os.path.join(W100_DIR, "destructive_wind_holdout_w100.parquet"),
             os.path.join(W100_DIR, "destructive_wind_dev_w100.parquet")),
            (os.path.join(W100_DIR, "tornado_holdout_w100.parquet"),
             os.path.join(W100_DIR, "tornado_dev_w100.parquet")),
            (os.path.join(NBR_DIR, "flash_flood_holdout_nbr.parquet"),
             os.path.join(NBR_DIR, "flash_flood_dev_nbr.parquet")),
            (os.path.join(NBR_DIR, "flood_holdout_nbr.parquet"),
             os.path.join(NBR_DIR, "flood_dev_nbr.parquet"))]:
        a = pq.ParquetFile(path).schema_arrow.names
        b = pq.ParquetFile(ref).schema_arrow.names
        assert a == b, f"schema mismatch {path} vs dev"
    # every rule feature is producible: point features + top-up feature names
    import detector
    rules = detector.load_config(CONFIG)
    known = None
    for klass, rule in rules.items():
        if known is None:
            probe_df = next(iter(data.load_series(
                klass, max_events=1).values()))
            known = set(compute_features(probe_df).columns) \
                | set(W100_FEATURE_NAMES) | set(NBR_FEATURE_NAMES)
        missing = [f for f in rule.feature_names if f not in known]
        assert not missing, f"{klass}: unresolvable features {missing}"
    print("preflight OK: config sha matches frozen, no marker, holdout "
          "parquets complete, top-up schemas match dev, all rule features "
          "resolvable")


def summarize(all_metrics, out_dir, digest, partial):
    summary = {"partial": bool(partial), "results_digest": digest,
               "classes": {}}
    for m in all_metrics:
        reasons = collections.Counter(x["reason"] for x in m["miss_list"])
        summary["classes"][m["event_class"]] = {
            "n_events": m["n_events"], "hits": m["hits"], "pod": m["pod"],
            "far": m["far"], "budget_per_loc_year": m["budget_per_loc_year"],
            "n_false_alarms": m["n_false_alarms"],
            "n_event_alarms": m["n_event_alarms"],
            "control_loc_years": m["control_loc_years"],
            "median_lead_h": m["median_lead_h"],
            "lead_p25_h": m["lead_p25_h"], "lead_p75_h": m["lead_p75_h"],
            "lead_min_h": m["lead_min_h"], "lead_max_h": m["lead_max_h"],
            "miss_reasons": {r: int(reasons.get(r, 0)) for r in
                             ("no_alarm", "insufficient_lead",
                              "alarm_outside_window")},
        }
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run-dev", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--i-understand-single-use", action="store_true")
    args = ap.parse_args()

    preflight()
    if args.dry_run_dev:
        out = os.path.join(HERE, "results_dryrun_dev")
        all_metrics, digest, partial = backtest.run_backtest(
            "dev", CONFIG, None, 15, out)
        for m in all_metrics:
            print(f"dry-run {m['event_class']}: {m['hits']}/{m['n_events']} "
                  f"hits, {m['n_false_alarms']} false alarms")
        for klass, cap in CAPTURE.items():
            assert "armed" in cap and "hazard" in cap, f"capture failed {klass}"
        print("dry run OK - loader resolves every rule feature on the "
              "combined path; gate untouched")
        return

    if not args.execute:
        raise SystemExit("pass --dry-run-dev or --execute")
    marker = backtest.holdout_gate(args.holdout, args.i_understand_single_use,
                                   CONFIG)
    print("holdout gate passed - this is THE single holdout run; marker "
          f"written to {backtest.MARKER_PATH}")
    out = os.path.join(HERE, "results_holdout")
    all_metrics, digest, partial = backtest.run_backtest(
        "holdout", CONFIG, None, None, out)
    backtest.finalize_marker(marker, digest)
    print("holdout marker finalized (results digest recorded)")
    summarize(all_metrics, out, digest, partial)
    cache = {k: {"rows": v["rows"], "hazard": v["hazard"],
                 "armed": v.get("armed")} for k, v in CAPTURE.items()}
    cache["metrics"] = {m["event_class"]: m for m in all_metrics}
    with open(os.path.join(out, "holdout_cache.pkl"), "wb") as f:
        pickle.dump(cache, f)
    print("cache pickled for post-hoc slicing; summary.json written")


if __name__ == "__main__":
    main()
