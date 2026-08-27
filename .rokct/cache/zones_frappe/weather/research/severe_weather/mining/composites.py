"""Event-vs-control statistics on onset-aligned feature matrices.

The mining harness (mine.py) samples every series' feature curves on a common
relative-hour grid aligned on the effective onset (rel hour 0 = onset_eff; controls
use their pseudo-onset, window_start + 14 d, per SAMPLING.md). This module turns the
stacked matrix (n_series, n_grid, n_features) into:

  * composite curves: median + IQR per feature per rel hour, events vs controls;
  * discriminative power per feature at fixed lead times: rank AUC (event vs
    control, tie-corrected Mann-Whitney), Cliff's delta, robust standardized
    median difference, and the raw medians.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.stats import rankdata

#: rel-hour grid (3-hourly, -14 d .. +69 h; 0 = onset)
REL_GRID = np.arange(-336, 72, 3)
#: lead times (hours before onset) at which discriminative power is scored
LEADS = (6, 12, 24, 48, 72)


def rank_auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """P(random event value > random control value), ties counted half."""
    n1, n2 = pos.size, neg.size
    if n1 == 0 or n2 == 0:
        return np.nan
    r = rankdata(np.concatenate([pos, neg]))
    return float((r[:n1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n2))


def _clean(x: np.ndarray) -> np.ndarray:
    return x[np.isfinite(x)]


def composite_table(mat: np.ndarray, is_event: np.ndarray, feat_names: list[str],
                    event_class: str, rel_grid: np.ndarray = REL_GRID) -> pd.DataFrame:
    """Long table: (class, feature, rel_h) -> median/q25/q75 for events and controls."""
    assert mat.shape[1] == rel_grid.size and mat.shape[2] == len(feat_names)
    ev, ct = mat[is_event], mat[~is_event]
    rows = []
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN slices at gap hours
        for fi, name in enumerate(feat_names):
            for pop, tag in ((ev, "event"), (ct, "control")):
                if pop.shape[0] == 0:
                    q = np.full((3, rel_grid.size), np.nan)
                    n = np.zeros(rel_grid.size, dtype=int)
                else:
                    vals = pop[:, :, fi]
                    q = np.nanpercentile(vals, [25, 50, 75], axis=0)
                    n = np.isfinite(vals).sum(axis=0)
                rows.append(pd.DataFrame({
                    "event_class": event_class, "feature": name, "role": tag,
                    "rel_h": rel_grid, "q25": q[0], "median": q[1], "q75": q[2], "n": n}))
    return pd.concat(rows, ignore_index=True)


def auc_table(mat: np.ndarray, is_event: np.ndarray, feat_names: list[str],
              event_class: str, rel_grid: np.ndarray = REL_GRID,
              leads: tuple = LEADS) -> pd.DataFrame:
    """Discriminative power of each feature at each lead time (rel hour -lead)."""
    rows = []
    for lead in leads:
        gi = np.where(rel_grid == -lead)[0]
        if gi.size == 0:
            continue
        gi = gi[0]
        for fi, name in enumerate(feat_names):
            pos = _clean(mat[is_event, gi, fi])
            neg = _clean(mat[~is_event, gi, fi])
            auc = rank_auc(pos, neg)
            med_e = float(np.median(pos)) if pos.size else np.nan
            med_c = float(np.median(neg)) if neg.size else np.nan
            if pos.size and neg.size:
                iqr = np.percentile(np.concatenate([pos, neg]), 75) - \
                      np.percentile(np.concatenate([pos, neg]), 25)
                robust_d = (med_e - med_c) / iqr if iqr > 0 else np.nan
            else:
                robust_d = np.nan
            rows.append({
                "event_class": event_class, "feature": name, "lead_h": lead,
                "auc": auc, "abs_auc": abs(auc - 0.5) + 0.5 if np.isfinite(auc) else np.nan,
                "cliffs_delta": 2 * auc - 1 if np.isfinite(auc) else np.nan,
                "robust_d": robust_d, "median_event": med_e, "median_control": med_c,
                "n_event": int(pos.size), "n_control": int(neg.size)})
    return pd.DataFrame(rows)


def rank_features(auc_df: pd.DataFrame, min_n: int = 20) -> pd.DataFrame:
    """Per (class, lead) ranking by |AUC - 0.5|; small samples are excluded.

    abs_auc folds direction: a feature with AUC 0.30 discriminates as strongly as
    one with 0.70 (the sign lives on in `auc` / `cliffs_delta`).
    """
    d = auc_df[(auc_df["n_event"] >= min_n) & (auc_df["n_control"] >= min_n)].copy()
    d = d.sort_values(["event_class", "lead_h", "abs_auc"],
                      ascending=[True, True, False])
    d["rank"] = d.groupby(["event_class", "lead_h"]).cumcount() + 1
    return d
