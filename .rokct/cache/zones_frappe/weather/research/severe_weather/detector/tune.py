"""Dev-only parameter search for the detector - NEVER touches the holdout cohort.

Data access goes exclusively through mining/data.py (via backtest.load_cohort
with cohort="dev"), so the pre-registered holdout guard applies: any attempt to
reach 2018+ series raises HoldoutAccessError.

Per class, random search (seeded) over rule parameters:
  * condition on/off thresholds - shifted in units of their hysteresis gap,
    biased toward stricter settings; the on/off gap is preserved;
  * per-condition persistence hours;
  * warning-score tier thresholds (watch/warning/severe move together);
  * cooldown hours.

Objective (frozen thresholds are the constraint set, not the target to tune to):
  maximize POD subject to FAR <= frozen FAR limit and false-alarm budget
  <= 2 warnings per control location-year, evaluated per fold.

Overfitting control: k-fold by LOCATION CLUSTER (10x10-degree cells, matching
the sampling strata) - series from one region always land in the same fold, so
a parameter set must work across regions, not memorize one. A candidate is
feasible only if every fold with enough data meets the FAR + budget
constraints; feasible candidates are ranked by mean fold POD (tie-break:
higher median lead).

Outputs:
  * tuned config (default: detector_config.json, i.e. overwrites in place -
    pass --out to write elsewhere) with provenance fields;
  * tuning_report.md - every candidate tried, per-fold dev scores, the pick.

Usage:
  python3 tune.py [--classes ...] [--n-iter 40] [--kfolds 5] [--seed 42]
                  [--base-config detector_config.json] [--out detector_config.json]
                  [--max-events N]
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np
import pandas as pd

import backtest
import detector
from backtest import FROZEN, BUDGET_MAX_PER_LOC_YEAR

MIN_FOLD_EVENTS = 5      # folds with fewer scored events don't constrain POD
MIN_FOLD_CONTROLS = 5


# --------------------------------------------------------------------------- #
# folds by location cluster
# --------------------------------------------------------------------------- #

def location_cluster(lat: float, lon: float) -> str:
    """10x10-degree cell, matching the sampling strata in SAMPLING.md."""
    return f"{int(np.floor(lat / 10.0))}_{int(np.floor(lon / 10.0))}"


def assign_folds(rows: pd.DataFrame, k: int) -> pd.Series:
    """Deterministic fold id per series, grouped by location cluster.

    Controls share their event's location, so an event and its matched
    controls always land in the same fold.
    """
    clusters = rows.apply(lambda r: location_cluster(r["lat"], r["lon"]), axis=1)
    def fold_of(c):
        return int(hashlib.md5(c.encode()).hexdigest(), 16) % k
    return clusters.map(fold_of)


# --------------------------------------------------------------------------- #
# candidate generation
# --------------------------------------------------------------------------- #

def perturb_class_config(base: dict, rng: random.Random) -> dict:
    """One random candidate: jitter thresholds/persistence/tiers/cooldown."""
    cand = copy.deepcopy(base)
    for c in cand["conditions"]:
        gap = abs(c["on"] - c["off"]) or max(abs(c["on"]) * 0.1, 1e-3)
        shift = rng.uniform(-1.0, 2.0) * gap      # biased toward stricter
        if c["direction"] == "above":
            c["on"] = round(c["on"] + shift, 4)
            c["off"] = round(c["on"] - gap, 4)
        else:
            c["on"] = round(c["on"] - shift, 4)
            c["off"] = round(c["on"] + gap, 4)
        c["persistence_h"] = max(1, int(c.get("persistence_h", 1))
                                 + rng.choice([-1, 0, 0, 0, 1, 2]))
    warning = round(rng.uniform(0.45, 0.80), 3)
    cand["severity_on"] = {"watch": round(max(0.2, warning - 0.15), 3),
                           "warning": warning,
                           "severe": round(min(0.95, warning + 0.20), 3)}
    cand["cooldown_h"] = rng.choice([12, 24, 48])
    return cand


def summarize_params(cd: dict) -> str:
    conds = "; ".join(f"{c['name']} {c['direction'][:2]} {c['on']}"
                      f"(p{c['persistence_h']})" for c in cd["conditions"])
    return (f"warn>={cd['severity_on']['warning']}, cool={cd['cooldown_h']}h / "
            + conds)   # no '|': these strings land in markdown table cells


# --------------------------------------------------------------------------- #
# evaluation
# --------------------------------------------------------------------------- #

def eval_candidate(klass: str, class_cfg: dict, rows: pd.DataFrame,
                   feats: dict, folds: pd.Series, k: int) -> dict:
    """Detector runs once over all series; metrics aggregated per fold."""
    rule = detector.rule_from_dict(klass, class_cfg)
    results = backtest.run_detector_over(feats, rule)
    fold_metrics = []
    for f in range(k):
        sub = rows[folds == f]
        if not len(sub):
            continue
        m = backtest.score_class(klass, sub, results)
        m["fold"] = f
        fold_metrics.append(m)
    limit = FROZEN[klass]["far"]
    pods, feas, leads = [], [], []
    for m in fold_metrics:
        if m["n_events"] >= MIN_FOLD_EVENTS:
            pods.append(m["pod"])
            if not np.isnan(m["median_lead_h"]):
                leads.append(m["median_lead_h"])
        if m["n_controls"] >= MIN_FOLD_CONTROLS:
            ok = ((np.isnan(m["far"]) or m["far"] <= limit)
                  and m["budget_per_loc_year"] <= BUDGET_MAX_PER_LOC_YEAR)
            feas.append(ok)
    return {
        "fold_metrics": fold_metrics,
        "mean_pod": float(np.mean(pods)) if pods else float("nan"),
        "median_lead_h": float(np.median(leads)) if leads else float("nan"),
        "feasible": bool(feas) and all(feas),
        "n_constrained_folds": len(feas),
    }


def tune_class(klass: str, base_cfg: dict, n_iter: int, k: int, seed: int,
               max_events: int | None, verbose: bool = True) -> tuple[dict, list, dict]:
    rows, feats = backtest.load_cohort(klass, "dev", max_events=max_events)
    ev = int((rows["role"] == "event").sum())
    if verbose:
        print(f"{klass}: tuning on {ev} events / {len(rows) - ev} controls "
              f"(dev, {rows['series_id'].nunique()} series loaded)")
    folds = assign_folds(rows, k)          # index-aligned with rows

    rng = random.Random(seed)
    candidates = [("base", copy.deepcopy(base_cfg))]
    candidates += [(f"cand_{i:03d}", perturb_class_config(base_cfg, rng))
                   for i in range(n_iter)]

    trials = []
    for name, cfg in candidates:
        r = eval_candidate(klass, cfg, rows, feats, folds, k)
        trials.append({"name": name, "cfg": cfg, **r})
        if verbose:
            print(f"  {name}: POD={r['mean_pod']:.3f} "
                  f"lead={r['median_lead_h']:.0f}h "
                  f"feasible={r['feasible']}" if not np.isnan(r["mean_pod"])
                  else f"  {name}: no scorable events")

    feasible = [t for t in trials if t["feasible"] and not np.isnan(t["mean_pod"])]
    pool = feasible or [t for t in trials if not np.isnan(t["mean_pod"])] or trials
    best = max(pool, key=lambda t: (t["mean_pod"]
                                    if not np.isnan(t["mean_pod"]) else -1,
                                    t["median_lead_h"]
                                    if not np.isnan(t["median_lead_h"]) else -1))
    best_cfg = copy.deepcopy(best["cfg"])
    best_cfg["notes"] = (best_cfg.get("notes", "") +
                         f" [tuned {dt.date.today()}: {best['name']}, "
                         f"dev mean-fold POD={best['mean_pod']:.3f}, "
                         f"feasible={best['feasible']}]")
    return best_cfg, trials, best


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--classes", nargs="+", choices=list(FROZEN), default=None)
    ap.add_argument("--n-iter", type=int, default=40)
    ap.add_argument("--kfolds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--base-config",
                    default=os.path.join(HERE, "detector_config.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "detector_config.json"),
                    help="where to write the tuned config")
    ap.add_argument("--report", default=os.path.join(HERE, "tuning_report.md"))
    ap.add_argument("--max-events", type=int, default=None)
    args = ap.parse_args()

    with open(args.base_config) as f:
        full = json.load(f)
    classes = args.classes or list(full["classes"])

    report = [f"# Detector tuning report - dev cohort only",
              "",
              f"Generated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M:%S} UTC. "
              f"Base config `{os.path.basename(args.base_config)}`; "
              f"{args.n_iter} random candidates/class + base; "
              f"{args.kfolds}-fold by 10-degree location cluster; seed {args.seed}. "
              "Feasibility: FAR and false-alarm budget within the frozen limits "
              "in EVERY fold with enough data; ranked by mean fold POD. "
              "The holdout cohort was not touched (mining/data.py guard).", ""]

    for klass in classes:
        best_cfg, trials, best = tune_class(
            klass, full["classes"][klass], args.n_iter, args.kfolds, args.seed,
            args.max_events)
        full["classes"][klass] = best_cfg
        report += [f"## {klass}", "",
                   f"Picked **{best['name']}** "
                   f"(mean fold POD {best['mean_pod']:.3f}, "
                   f"median lead {best['median_lead_h']:.0f} h, "
                   f"feasible={best['feasible']}): "
                   f"`{summarize_params(best['cfg'])}`", "",
                   "| candidate | mean POD | median lead h | feasible | params |",
                   "|---|---|---|---|---|"]
        def _n(x, nd=3):
            return "n/a" if x is None or np.isnan(x) else f"{x:.{nd}f}"
        for t in sorted(trials, key=lambda t: -(t["mean_pod"]
                                                if not np.isnan(t["mean_pod"])
                                                else -1)):
            report.append(f"| {t['name']} | {_n(t['mean_pod'])} "
                          f"| {_n(t['median_lead_h'], 0)} | {t['feasible']} "
                          f"| {summarize_params(t['cfg'])} |")
        report.append("")
        # per-fold detail for the pick
        report += ["Per-fold scores of the pick:", "",
                   "| fold | events | controls | POD | FAR | budget | median lead h |",
                   "|---|---|---|---|---|---|---|"]
        for m in best["fold_metrics"]:
            report.append(f"| {m['fold']} | {m['n_events']} | {m['n_controls']} "
                          f"| {_n(m['pod'], 2)} | {_n(m['far'], 2)} "
                          f"| {_n(m['budget_per_loc_year'], 2)} "
                          f"| {_n(m['median_lead_h'], 0)} |")
        report.append("")

    full["version"] = f"tuned-{dt.date.today()}"
    full["tuning"] = {"seed": args.seed, "n_iter": args.n_iter,
                      "kfolds": args.kfolds, "cohort": "dev",
                      "base_config": os.path.basename(args.base_config),
                      "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    with open(args.out, "w") as f:
        json.dump(full, f, indent=2)
    with open(args.report, "w") as f:
        f.write("\n".join(report))
    print(f"tuned config -> {args.out}\nreport -> {args.report}")


if __name__ == "__main__":
    main()
