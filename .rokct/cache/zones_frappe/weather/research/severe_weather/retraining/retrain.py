"""Human-triggered offline retraining harness - tune on era A, prove on era B.

This script is the ONLY sanctioned way to turn outcome-ledger evidence into a
candidate detector config, and it automates nothing: a human runs it, reads
the report it writes, and (separately) decides whether to open a PR shipping
the candidate. See RETRAINING.md in this folder for the full discipline.

What it does, in order:

  1. LEDGER GATE - reads a Severe Weather Outcome ledger export (JSON or CSV)
     and summarizes it with the SAME aggregation code the admin report
     endpoint uses (frappe/src/control/api/get_retraining_report/, loaded by
     file path), so the harness and the desk report can never disagree.
     Classes without enough ledger evidence are skipped (override: --force).
  2. ERA SPLIT - splits the research dev cohort by event onset into era A
     (tuning) and era B (blind evaluation). Both eras MUST end before
     2018-01-01: the 2018+ holdout was spent by the single gated run
     (detector/results_holdout/ + HOLDOUT_RUN_MARKER) and is never re-read -
     any attempt raises mining/data.py's HoldoutAccessError. All series
     access goes through backtest.load_cohort(cohort="dev"), so the
     pre-registered holdout guard applies underneath as well.
  3. TUNE ON ERA A - reuses detector/tune.py verbatim (assign_folds,
     perturb_class_config, eval_candidate: same seeded random search, same
     k-fold-by-location-cluster overfitting control, same frozen-constraint
     feasibility rule) restricted to era-A series only.
  4. PROVE ON ERA B - the single winning candidate per class is evaluated
     ONCE, blind, on era B with detector/backtest.py's frozen scoring
     (run_detector_over + score_class + passes_frozen). Nothing is re-tuned
     after seeing era-B numbers; if the candidate disappoints, the answer is
     a new run with a new seed/structure, not a peek-and-tweak.
  5. OUTPUT - a NEW versioned candidate config
     (detector_config_candidate_<tag>.json, sha256 recorded in a .sha256
     sidecar and in the report) plus retraining_report_<tag>.md. The harness
     REFUSES to write detector_config.json or detector_config_tuned.json -
     the shipped config only ever changes by a human merging a PR.

Usage:
  python3 retrain.py --ledger ledger_export.json \
      --era-a 1996-01-01:2011-01-01 --era-b 2011-01-01:2018-01-01 \
      [--classes flash_flood ...] [--n-iter 40] [--kfolds 5] [--seed 42] \
      [--base-config ../detector/detector_config_tuned.json] \
      [--max-events N] [--min-ledger-rows 20] [--force] [--tag TAG] \
      [--out-dir runs/<tag>] [--dry-run]

Era format: START:END (dates, END exclusive). --dry-run runs the ledger gate
and every refusal check, then stops before touching any series data.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DETECTOR_DIR = os.path.normpath(os.path.join(HERE, "..", "detector"))
MINING_DIR = os.path.normpath(os.path.join(HERE, "..", "mining"))
for _p in (DETECTOR_DIR, MINING_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import pandas as pd

import backtest            # detector/backtest.py - frozen metrics + loader
import data                # mining/data.py - dev loader + HoldoutAccessError
import detector            # detector/detector.py - the state machine
import tune                # detector/tune.py - search + fold + feasibility

# Importing run_backtest_holdout patches backtest.load_cohort to the combined
# point + w100 bulk-shear + nbr neighborhood feature construction - the exact
# code path that produced the dev results of record and the single holdout
# run. Reused, not duplicated; the holdout branch of that loader stays behind
# the single-use gate and is never called from here (cohort is always "dev").
import run_backtest_holdout  # noqa: F401  (side effect: combined loader)

REPORT_API_PATH = os.path.normpath(os.path.join(
    HERE, "..", "..", "..", "frappe", "src", "control", "api",
    "get_retraining_report", "get_retraining_report.py"))

#: first day of the SPENT single-use holdout era (extraction/SAMPLING.md).
HOLDOUT_START = pd.Timestamp("2018-01-01")

#: configs this harness must never write - shipped configs change only by a
#: human merging a PR that carries a reviewed candidate.
PROTECTED_BASENAMES = ("detector_config.json", "detector_config_tuned.json")

#: default per-class ledger volume required before a retune is worth running
#: (matches MIN_OUTCOMES_FOR_VERDICT in the admin report endpoint).
DEFAULT_MIN_LEDGER_ROWS = 20


# --------------------------------------------------------------------------- #
# refusal checks (all raise before any series data is touched)
# --------------------------------------------------------------------------- #

def parse_era(text: str, name: str) -> tuple:
    try:
        start_s, end_s = text.split(":")
        start, end = pd.Timestamp(start_s), pd.Timestamp(end_s)
    except Exception:
        raise SystemExit(
            f"REFUSED: {name} must look like YYYY-MM-DD:YYYY-MM-DD "
            f"(got {text!r})")
    if not start < end:
        raise SystemExit(f"REFUSED: {name} start must precede its end")
    return start, end


def check_eras(era_a: tuple, era_b: tuple) -> None:
    """Era discipline: A strictly before B, both clear of the spent holdout."""
    for name, (start, end) in (("era A", era_a), ("era B", era_b)):
        if end > HOLDOUT_START:
            raise data.HoldoutAccessError(
                f"HOLDOUT GUARD: {name} ({start.date()}..{end.date()}) "
                f"reaches into {HOLDOUT_START.date()}+. That era is the "
                "original single-use holdout - it was SPENT by the gated run "
                "recorded in detector/results_holdout/ and can never be "
                "re-used for tuning or evaluation.")
    if era_b[0] < era_a[1]:
        raise SystemExit(
            "REFUSED: era B must start at or after era A ends - the whole "
            "point is proving the candidate on time it never saw.")


def check_out_path(path: str) -> None:
    """Refuse any output that could overwrite a shipped/protected config."""
    base = os.path.basename(path)
    if base in PROTECTED_BASENAMES:
        raise SystemExit(
            f"REFUSED: {base} is a protected config. Candidates are NEW "
            "versioned files (detector_config_candidate_<tag>.json); the "
            "shipped config changes only via a reviewed, human-merged PR.")
    real = os.path.realpath(path)
    for protected in PROTECTED_BASENAMES:
        if real == os.path.realpath(os.path.join(DETECTOR_DIR, protected)):
            raise SystemExit(f"REFUSED: {path} resolves to the protected "
                             f"config {protected}.")


# --------------------------------------------------------------------------- #
# ledger gate (reuses the admin report endpoint's aggregation verbatim)
# --------------------------------------------------------------------------- #

def load_report_module():
    """The frappe-side report module, loaded by file path (frappe-free half)."""
    spec = importlib.util.spec_from_file_location(
        "sw_retraining_report", REPORT_API_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_ledger(path: str) -> list:
    """Ledger export rows as list[dict]. JSON (array or {'data': [...]}) or CSV."""
    if path.lower().endswith(".csv"):
        return pd.read_csv(path).to_dict("records")
    with open(path) as f:
        parsed = json.load(f)
    if isinstance(parsed, dict):
        parsed = parsed.get("data", [])
    if not isinstance(parsed, list):
        raise SystemExit(f"REFUSED: {path} is not a ledger export "
                         "(expected a JSON array or {'data': [...]})")
    return parsed


def ledger_gate(rows: list, classes: list, min_rows: int,
                force: bool) -> tuple:
    """(classes worth retuning, per-class ledger summary). Human-readable."""
    report_mod = load_report_module()
    summary = report_mod.summarize_ledger(rows)
    eligible = []
    for klass in classes:
        c = summary[klass]
        total = c["counts"]["total"]
        if total >= min_rows or force:
            eligible.append(klass)
            note = "" if total >= min_rows else " (forced despite thin ledger)"
            print(f"  {klass}: {total} ledger row(s), verdict "
                  f"{c['verdict']}{note}")
        else:
            print(f"  {klass}: SKIPPED - only {total} ledger row(s) "
                  f"(need {min_rows}; --force overrides)")
    return eligible, summary


# --------------------------------------------------------------------------- #
# era split over the dev cohort
# --------------------------------------------------------------------------- #

def split_eras(rows: pd.DataFrame, era_a: tuple, era_b: tuple) -> tuple:
    """(rows_a, rows_b): events assigned by onset; controls follow their event.

    Matched controls are same-location/other-year windows; they belong to the
    era their EVENT belongs to, so an event and its controls always move
    together (mirrors tune.py's fold rule).
    """
    ev = rows[rows["role"] == "event"]
    onset = pd.to_datetime(ev["onset_catalog"])
    ids_a = set(ev.loc[(onset >= era_a[0]) & (onset < era_a[1]), "event_id"])
    ids_b = set(ev.loc[(onset >= era_b[0]) & (onset < era_b[1]), "event_id"])
    rows_a = rows[rows["event_id"].isin(ids_a)].copy()
    rows_b = rows[rows["event_id"].isin(ids_b)].copy()
    return rows_a, rows_b


def _subset_feats(feats: dict, rows: pd.DataFrame) -> dict:
    keep = set(rows["series_id"])
    return {sid: fdf for sid, fdf in feats.items() if sid in keep}


# --------------------------------------------------------------------------- #
# tune on A (tune.py primitives), prove on B (backtest.py frozen scoring)
# --------------------------------------------------------------------------- #

def tune_on_era_a(klass: str, base_cfg: dict, rows_a: pd.DataFrame,
                  feats_a: dict, n_iter: int, kfolds: int,
                  seed: int) -> tuple:
    """Best candidate on era A - tune.py's search/feasibility/pick verbatim."""
    folds = tune.assign_folds(rows_a, kfolds)
    rng = random.Random(seed)
    candidates = [("base", copy.deepcopy(base_cfg))]
    candidates += [(f"cand_{i:03d}", tune.perturb_class_config(base_cfg, rng))
                   for i in range(n_iter)]
    trials = []
    for name, cfg in candidates:
        r = tune.eval_candidate(klass, cfg, rows_a, feats_a, folds, kfolds)
        trials.append({"name": name, "cfg": cfg, **r})
    feasible = [t for t in trials
                if t["feasible"] and not np.isnan(t["mean_pod"])]
    pool = (feasible
            or [t for t in trials if not np.isnan(t["mean_pod"])]
            or trials)
    best = max(pool, key=lambda t: (
        t["mean_pod"] if not np.isnan(t["mean_pod"]) else -1,
        t["median_lead_h"] if not np.isnan(t["median_lead_h"]) else -1))
    return best, trials


def evaluate_on_era_b(klass: str, cfg: dict, rows_b: pd.DataFrame,
                      feats_b: dict) -> tuple:
    """ONE blind pass of the chosen candidate over era B, frozen metrics."""
    rule = detector.rule_from_dict(klass, cfg)
    results = backtest.run_detector_over(feats_b, rule)
    metrics = backtest.score_class(klass, rows_b, results)
    return metrics, backtest.passes_frozen(metrics)


# --------------------------------------------------------------------------- #
# outputs
# --------------------------------------------------------------------------- #

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def write_candidate(full_cfg: dict, out_path: str) -> str:
    check_out_path(out_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(full_cfg, f, indent=2)
    sha = _sha256_file(out_path)
    with open(out_path + ".sha256", "w") as f:
        f.write(f"{sha}  {os.path.basename(out_path)}\n")
    return sha


def _fmt(x, nd=3):
    return ("n/a" if x is None or (isinstance(x, float) and np.isnan(x))
            else f"{x:.{nd}f}")


def build_report_md(tag: str, args, ledger_summary: dict, per_class: dict,
                    candidate_file: str, candidate_sha: str,
                    base_sha: str) -> str:
    lines = [
        f"# Retraining run `{tag}` - candidate evaluation report",
        "",
        f"Generated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M:%S} UTC "
        "by retraining/retrain.py (human-triggered; nothing here ships "
        "automatically - adoption is a reviewed, human-merged PR).",
        "",
        f"* Ledger export: `{os.path.basename(args.ledger)}`",
        f"* Era A (tuning): {args.era_a} - Era B (blind eval): {args.era_b} "
        f"(both pre-{HOLDOUT_START.date()}; the spent holdout was not "
        "touched)",
        f"* Base config: `{os.path.basename(args.base_config)}` "
        f"(sha256 `{base_sha[:16]}...`)",
        f"* Candidate: `{os.path.basename(candidate_file)}` "
        f"(sha256 `{candidate_sha}`)",
        f"* Search: {args.n_iter} candidates/class, {args.kfolds}-fold by "
        f"location cluster, seed {args.seed}",
        "",
        "## Ledger evidence that motivated this run",
        "",
    ]
    for klass, c in ledger_summary.items():
        if klass.startswith("_"):
            continue
        counts = c["counts"]
        lines.append(f"* {klass}: {c['verdict']} - {counts['hits']} hit(s), "
                     f"{counts['false_alarms']} false alarm(s), "
                     f"{counts['candidate_misses']} candidate miss(es)")
    lines += ["", "## Era-B blind results vs the frozen bars (PLAN.md)", "",
              "| class | era-A pick | era-A mean POD | era-B events | "
              "era-B POD | era-B FAR | era-B budget /loc-yr | "
              "era-B median lead h | frozen pass |",
              "|---|---|---|---|---|---|---|---|---|"]
    for klass, r in per_class.items():
        m, ok, best = r["metrics_b"], r["passes"], r["best"]
        t = backtest.FROZEN[klass]
        flag = ("PASS" if ok["all"] else "fail: " + ",".join(
            k for k, v in ok.items() if k != "all" and not v))
        lines.append(
            f"| {klass} | {best['name']} | {_fmt(best['mean_pod'])} "
            f"| {m['n_events']} | {_fmt(m['pod'])} (>={t['pod']}) "
            f"| {_fmt(m['far'])} (<={t['far']}) "
            f"| {_fmt(m['budget_per_loc_year'], 2)} "
            f"(<={backtest.BUDGET_MAX_PER_LOC_YEAR:.0f}) "
            f"| {_fmt(m['median_lead_h'], 1)} (>={t['min_lead_h']}) "
            f"| {flag} |")
    lines += ["",
              "Era-B numbers are single-look: the candidate was chosen on "
              "era A alone and evaluated exactly once above. If it "
              "disappoints, run again with a different seed or structure - "
              "do not tweak against these numbers.",
              "",
              "## Era-A tuning detail (top 10 per class)", ""]
    for klass, r in per_class.items():
        lines += [f"### {klass}", "",
                  "| candidate | mean POD | median lead h | feasible | "
                  "params |", "|---|---|---|---|---|"]
        ranked = sorted(r["trials"], key=lambda t: -(
            t["mean_pod"] if not np.isnan(t["mean_pod"]) else -1))
        for t in ranked[:10]:
            lines.append(f"| {t['name']} | {_fmt(t['mean_pod'])} "
                         f"| {_fmt(t['median_lead_h'], 0)} | {t['feasible']} "
                         f"| {tune.summarize_params(t['cfg'])} |")
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", required=True,
                    help="Severe Weather Outcome ledger export (JSON or CSV)")
    ap.add_argument("--era-a", required=True,
                    help="tuning era, START:END (END exclusive, pre-2018)")
    ap.add_argument("--era-b", required=True,
                    help="blind evaluation era, START:END (after era A, "
                         "pre-2018)")
    ap.add_argument("--classes", nargs="+", choices=list(backtest.FROZEN),
                    default=list(backtest.FROZEN))
    ap.add_argument("--n-iter", type=int, default=40)
    ap.add_argument("--kfolds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--base-config",
                    default=os.path.join(DETECTOR_DIR,
                                         "detector_config_tuned.json"))
    ap.add_argument("--max-events", type=int, default=None)
    ap.add_argument("--min-ledger-rows", type=int,
                    default=DEFAULT_MIN_LEDGER_ROWS)
    ap.add_argument("--force", action="store_true",
                    help="retune classes even when the ledger is thin")
    ap.add_argument("--tag", default=None,
                    help="run tag (default: <date>_seed<seed>)")
    ap.add_argument("--out-dir", default=None,
                    help="output dir (default: runs/<tag>/ next to this "
                         "file; never the detector dir)")
    ap.add_argument("--dry-run", action="store_true",
                    help="run the ledger gate + refusal checks, then stop "
                         "before touching series data")
    args = ap.parse_args()

    era_a = parse_era(args.era_a, "--era-a")
    era_b = parse_era(args.era_b, "--era-b")
    check_eras(era_a, era_b)

    tag = args.tag or f"{dt.date.today():%Y%m%d}_seed{args.seed}"
    out_dir = args.out_dir or os.path.join(HERE, "runs", tag)
    candidate_file = os.path.join(out_dir,
                                  f"detector_config_candidate_{tag}.json")
    check_out_path(candidate_file)

    print(f"ledger gate ({args.ledger}):")
    rows = load_ledger(args.ledger)
    classes, ledger_summary = ledger_gate(rows, args.classes,
                                          args.min_ledger_rows, args.force)
    if not classes:
        raise SystemExit("nothing to retune: no requested class has enough "
                         "ledger evidence (see counts above; --force "
                         "overrides).")
    if args.dry_run:
        print(f"dry run complete: would retune {classes}, era A {args.era_a}"
              f" -> era B {args.era_b}, candidate -> {candidate_file}")
        return

    with open(args.base_config) as f:
        full = json.load(f)
    base_sha = _sha256_file(args.base_config)

    per_class = {}
    for klass in classes:
        rows_all, feats = backtest.load_cohort(klass, "dev",
                                               max_events=args.max_events)
        rows_a, rows_b = split_eras(rows_all, era_a, era_b)
        feats_a, feats_b = (_subset_feats(feats, rows_a),
                            _subset_feats(feats, rows_b))
        n_ev_a = int((rows_a["role"] == "event").sum())
        n_ev_b = int((rows_b["role"] == "event").sum())
        print(f"{klass}: era A {n_ev_a} events / era B {n_ev_b} events")
        if not n_ev_a or not n_ev_b:
            print(f"  SKIPPED - an era has no events for this class")
            continue
        best, trials = tune_on_era_a(klass, full["classes"][klass], rows_a,
                                     feats_a, args.n_iter, args.kfolds,
                                     args.seed)
        metrics_b, passes = evaluate_on_era_b(klass, best["cfg"], rows_b,
                                              feats_b)
        print(f"  era-A pick {best['name']} (mean POD "
              f"{_fmt(best['mean_pod'])}); era-B POD {_fmt(metrics_b['pod'])}"
              f" FAR {_fmt(metrics_b['far'])} -> "
              f"{'PASS' if passes['all'] else 'below bar'}")
        full["classes"][klass] = copy.deepcopy(best["cfg"])
        per_class[klass] = {"best": best, "trials": trials,
                            "metrics_b": metrics_b, "passes": passes}

    if not per_class:
        raise SystemExit("no class produced a candidate (era split left no "
                         "events) - nothing written.")

    full["version"] = f"candidate-{tag}"
    full["retraining"] = {
        "harness": "research/severe_weather/retraining/retrain.py",
        "ledger_export": os.path.basename(args.ledger),
        "era_a": args.era_a, "era_b": args.era_b,
        "seed": args.seed, "n_iter": args.n_iter, "kfolds": args.kfolds,
        "base_config": os.path.basename(args.base_config),
        "base_config_sha256": base_sha,
        "classes_retuned": sorted(per_class),
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "note": ("CANDIDATE ONLY - adoption requires a human-reviewed PR; "
                 "the spent 2018+ holdout was not touched."),
    }
    sha = write_candidate(full, candidate_file)
    report_md = build_report_md(tag, args, ledger_summary, per_class,
                                candidate_file, sha, base_sha)
    report_path = os.path.join(out_dir, f"retraining_report_{tag}.md")
    with open(report_path, "w") as f:
        f.write(report_md)
    print(f"candidate -> {candidate_file}\n  sha256 {sha}\n"
          f"report -> {report_path}")


if __name__ == "__main__":
    main()
