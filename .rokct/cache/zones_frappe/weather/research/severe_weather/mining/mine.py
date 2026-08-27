"""Mining harness: features -> onset-aligned composites -> AUC-by-lead rankings.

DEV COHORT ONLY (enforced by data.py's holdout guard). Runs on whatever series are
available: finalized parquet after the extraction completes, or partial data
reconstructed from the extraction cache while it is still running - results from a
partial run are marked PARTIAL in results/run_meta.json and in the report.

Usage:
    python3 mine.py [--classes flood flash_flood ...] [--max-events N] [--out DIR]

Outputs under --out (default mining/results/):
    composites.parquet   median/IQR curves, events vs controls, per class/feature/rel-hour
    auc_by_lead.parquet  + .csv   discriminative power per class/feature/lead
    rankings.csv         per (class, lead) feature ranking by |AUC - 0.5|
    run_meta.json        series counts, partial flag, timings
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time

import numpy as np
import pandas as pd

import composites as cz
import data
from features import FEATURE_NAMES, compute_features

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def build_class_matrix(series: dict[str, pd.DataFrame], manifest: pd.DataFrame,
                       ) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Stack per-series feature curves on the rel-hour grid.

    Returns (mat[n_series, n_grid, n_feat], is_event[n_series], series_ids).
    Row i of a complete window sits at rel hour i - 336, so grid rows are simply
    REL_GRID + 336 (data.load_series guarantees the 408-hour index).
    """
    by_id = manifest.set_index("series_id")
    grid_rows = cz.REL_GRID + data.ONSET_INDEX
    mats, flags, ids = [], [], []
    for sid, df in series.items():
        feats = compute_features(df)
        mats.append(feats.to_numpy(dtype=np.float32)[grid_rows, :])
        flags.append(by_id.loc[sid, "role"] == "event")
        ids.append(sid)
    if not mats:
        return (np.zeros((0, cz.REL_GRID.size, len(FEATURE_NAMES)), np.float32),
                np.zeros(0, bool), [])
    return np.stack(mats), np.asarray(flags), ids


def run(classes: list[str] | None = None, max_events: int | None = None,
        out_dir: str = RESULTS_DIR, verbose: bool = True) -> dict:
    classes = classes or data.CLASSES
    os.makedirs(out_dir, exist_ok=True)
    manifest = data.load_manifest()

    n_dev_total = len(manifest)
    n_done_dev = len(set(manifest["series_id"]) & data.done_series_ids())
    have_final = all(os.path.exists(os.path.join(data.SERIES_DIR, f"{k}_dev.parquet"))
                     for k in classes)
    partial = (not have_final) and n_done_dev < n_dev_total

    comp_frames, auc_frames, counts = [], [], {}
    t0 = time.time()
    for klass in classes:
        t1 = time.time()
        series = data.load_series(klass, max_events=max_events, verbose=verbose)
        mat, is_event, _ids = build_class_matrix(series, manifest)
        counts[klass] = {"event": int(is_event.sum()),
                         "control": int((~is_event).sum())}
        if verbose:
            print(f"{klass}: {counts[klass]['event']} events, "
                  f"{counts[klass]['control']} controls "
                  f"({time.time() - t1:.0f}s load+features)")
        if mat.shape[0] == 0:
            continue
        comp_frames.append(cz.composite_table(mat, is_event, FEATURE_NAMES, klass))
        auc_frames.append(cz.auc_table(mat, is_event, FEATURE_NAMES, klass))

    comp = (pd.concat(comp_frames, ignore_index=True) if comp_frames
            else pd.DataFrame())
    auc = pd.concat(auc_frames, ignore_index=True) if auc_frames else pd.DataFrame()
    comp.to_parquet(os.path.join(out_dir, "composites.parquet"), index=False)
    auc.to_parquet(os.path.join(out_dir, "auc_by_lead.parquet"), index=False)
    auc.to_csv(os.path.join(out_dir, "auc_by_lead.csv"), index=False)
    if len(auc):
        cz.rank_features(auc).to_csv(os.path.join(out_dir, "rankings.csv"), index=False)

    meta = {
        "generated_utc": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "partial": bool(partial),
        "dev_series_in_manifest": int(n_dev_total),
        "dev_series_extracted": int(n_done_dev),
        "classes": classes,
        "counts_used": counts,
        "n_features": len(FEATURE_NAMES),
        "leads_h": list(cz.LEADS),
        "runtime_s": round(time.time() - t0, 1),
        "cohort": "dev",   # holdout is never read here; see data.py guard
    }
    with open(os.path.join(out_dir, "run_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    if verbose:
        print(f"mining run complete in {meta['runtime_s']}s -> {out_dir} "
              f"(partial={partial}, {n_done_dev}/{n_dev_total} dev series extracted)")
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--classes", nargs="+", default=None, choices=data.CLASSES)
    ap.add_argument("--max-events", type=int, default=None,
                    help="cap event series per class (controls follow), for quick tests")
    ap.add_argument("--out", default=RESULTS_DIR)
    args = ap.parse_args()
    run(args.classes, args.max_events, args.out)


if __name__ == "__main__":
    main()
