"""Backtest harness - implements the FROZEN metric definitions from PLAN.md verbatim.

Frozen definitions (PLAN.md "Acceptance thresholds", frozen 2026-08-19):
  * Evaluation unit: (event, location) pairs, detection at the nearest ERA5 grid
    point (that is exactly what the extracted series are).
  * Hit: a warning of the correct event class active in [onset - 7 d, onset]
    with at least the minimum lead time.
  * POD = hits / all sampled cataloged events of that class; misses reported
    individually.
  * FAR = false alarms / all alarms, measured on matched non-event control
    periods: false alarms are warning episodes on control series; "all alarms"
    is those plus the warning episodes on event series of the same class.
  * False-alarm budget: at most 2 severe warnings per location-year on control
    data. Implemented conservatively as ALL warning-or-worse episodes (not just
    the "severe" tier) per control location-year - counting more alarms than a
    tier-only reading would, so the budget cannot be passed on a technicality.
  * Lead time: hours from first firing of the warning to event onset; median
    per class (computed over hits).

Minimum lead per class: flash flood 6 h, flood 24 h, destructive wind 12 h,
tornado 3 h.

Cohorts:
  * dev: runs freely (data.py's holdout guard still applies underneath).
  * holdout: SINGLE USE. Requires --cohort holdout --holdout
    --i-understand-single-use, refuses if HOLDOUT_RUN_MARKER.json already
    exists, and writes that tamper-evident marker (config SHA-256, timestamps,
    results digest, self-signature) so the one run is on the record.

Usage:
  python3 backtest.py                         # dev cohort, detector_config.json
  python3 backtest.py --classes flood --max-events 50 --out results_smoke
  python3 backtest.py --cohort holdout --holdout --i-understand-single-use
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MINING_DIR = os.path.normpath(os.path.join(HERE, "..", "mining"))
for p in (HERE, MINING_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import pandas as pd

import data                                   # mining/data.py: dev loader + holdout guard
import detector
from features import compute_features         # mining/features.py: causal features

MARKER_PATH = os.path.join(HERE, "HOLDOUT_RUN_MARKER.json")
DEFAULT_CONFIG = os.path.join(HERE, "detector_config.json")

HIT_WINDOW_H = 168                 # 7 days before onset
HOURS_PER_LOC_YEAR = 8766          # 365.25 * 24
BUDGET_MAX_PER_LOC_YEAR = 2.0

#: frozen acceptance thresholds (PLAN.md) - DO NOT EDIT.
FROZEN = {
    "flash_flood":      {"pod": 0.60, "far": 0.60, "min_lead_h": 6},
    "flood":            {"pod": 0.65, "far": 0.50, "min_lead_h": 24},
    "destructive_wind": {"pod": 0.70, "far": 0.40, "min_lead_h": 12},
    "tornado":          {"pod": 0.40, "far": 0.75, "min_lead_h": 3},
}

_HOLDOUT_UNLOCKED = False          # set only by holdout_gate()


# --------------------------------------------------------------------------- #
# holdout gate (single use, tamper-evident)
# --------------------------------------------------------------------------- #

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _signed(payload: dict) -> dict:
    body = json.dumps(payload, sort_keys=True, default=str)
    return {**payload, "signature_sha256": hashlib.sha256(body.encode()).hexdigest()}


def holdout_gate(holdout_flag: bool, i_understand: bool, config_path: str,
                 marker_path: str = MARKER_PATH) -> dict:
    """Refuse holdout access unless both flags are given AND no marker exists.

    On success, unlocks the holdout loader and writes the preliminary marker
    (config hash + start time) IMMEDIATELY - a crashed run still burns the
    single use, which is the point.
    """
    global _HOLDOUT_UNLOCKED
    if not (holdout_flag and i_understand):
        raise SystemExit(
            "REFUSED: the holdout cohort is single-use and reserved for the final "
            "backtest with the frozen tuned config. Re-run with BOTH "
            "--holdout AND --i-understand-single-use if that is really what "
            "you are doing.")
    if os.path.exists(marker_path):
        raise SystemExit(
            f"REFUSED: {marker_path} exists - the single holdout run has already "
            "been performed (or started). The holdout backtest cannot be repeated; "
            "results stand as recorded.")
    marker = _signed({
        "purpose": "single-use holdout backtest marker (tamper-evident)",
        "config_path": os.path.abspath(config_path),
        "config_sha256": _sha256_file(config_path),
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "started",
    })
    with open(marker_path, "w") as f:
        json.dump(marker, f, indent=2)
    _HOLDOUT_UNLOCKED = True
    return marker


def finalize_marker(marker: dict, results_digest: str,
                    marker_path: str = MARKER_PATH) -> None:
    payload = {k: v for k, v in marker.items() if k != "signature_sha256"}
    payload.update(status="completed",
                   finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                   results_sha256=results_digest)
    with open(marker_path, "w") as f:
        json.dump(_signed(payload), f, indent=2)


# --------------------------------------------------------------------------- #
# cohort loading (dev via mining/data.py; holdout only behind the gate)
# --------------------------------------------------------------------------- #

def _load_holdout_series(event_class: str) -> dict:
    """Holdout mirror of data.load_series. Callable only after holdout_gate()."""
    if not _HOLDOUT_UNLOCKED:
        raise data.HoldoutAccessError(
            "HOLDOUT GUARD: holdout series requested without passing the "
            "single-use gate (--holdout --i-understand-single-use).")
    raw = data._read_manifest_raw()
    sel = raw[(raw["cohort"] == "holdout") & (raw["event_class"] == event_class)]
    by_id = sel.set_index("series_id")
    out: dict = {}
    paths = [os.path.join(data.SERIES_DIR, f"{event_class}_holdout.parquet")]
    paths += sorted(glob.glob(os.path.join(
        data.PARTS_DIR, f"{event_class}_holdout.*.parquet")))
    for path in paths:
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_parquet(path)
        except Exception:
            continue                        # part file still being written
        df = df[df["series_id"].isin(set(by_id.index) - set(out))]
        for sid, g in df.groupby("series_id", sort=False):
            out[sid] = g.set_index("time")[data.VALUE_COLUMNS].astype(np.float32)
    for sid in sorted((set(by_id.index) & data.done_series_ids()) - set(out)):
        df = data._reconstruct_from_cache(by_id.loc[sid])
        if df is not None:
            out[sid] = df
    for sid, df in out.items():
        row = by_id.loc[sid]
        idx = pd.date_range(row.window_start, row.window_end, freq="1h",
                            inclusive="left")
        if len(df) != len(idx) or not df.index.equals(idx):
            out[sid] = df[~df.index.duplicated()].reindex(idx)
    return out


def load_cohort(event_class: str, cohort: str,
                max_events: int | None = None, verbose: bool = False):
    """-> (manifest rows for loaded series, {series_id: feature DataFrame}).

    Features are computed once here and reused for every detector run
    (tune.py re-runs the detector many times over the same features).
    """
    if cohort == "dev":
        series = data.load_series(event_class, max_events=max_events,
                                  verbose=verbose)
        manifest = data.load_manifest()
    elif cohort == "holdout":
        series = _load_holdout_series(event_class)     # raises unless gated
        manifest = data._read_manifest_raw()
        manifest = manifest[manifest["cohort"] == "holdout"]
    else:
        raise ValueError(f"unknown cohort {cohort!r}")
    rows = manifest[manifest["series_id"].isin(series.keys())].copy()
    feats = {sid: compute_features(df) for sid, df in series.items()}
    return rows, feats


# --------------------------------------------------------------------------- #
# metric evaluation (pure functions - tune.py reuses these)
# --------------------------------------------------------------------------- #

def run_detector_over(feats: dict, rule) -> dict:
    """{series_id: DetectionResult} for one class rule over precomputed features."""
    out = {}
    for sid, fdf in feats.items():
        times = list(fdf.index)
        cols = {name: fdf[name].astype(float).tolist()
                for name in rule.feature_names}
        out[sid] = detector.run_class(times, cols, rule)
    return out


def _qualifying_alarms(res, onset, min_lead_h: int):
    """Alarms active in [onset-7d, onset] with >= the class minimum lead."""
    lo = onset - pd.Timedelta(hours=HIT_WINDOW_H)
    latest_fire = onset - pd.Timedelta(hours=min_lead_h)
    return [a for a in res.alarms
            if a.last_active_at >= lo and a.first_fired_at <= latest_fire]


def score_class(klass: str, rows: pd.DataFrame, results: dict) -> dict:
    """Frozen metrics for one class given detector results per series.

    rows: manifest rows (must include every series in `results` to be scored).
    Returns metrics plus itemized hits / misses / false alarms.
    """
    min_lead = FROZEN[klass]["min_lead_h"]
    ev = rows[(rows["role"] == "event") & (rows["event_class"] == klass)]
    ct = rows[(rows["role"] == "control") & (rows["event_class"] == klass)]

    hits, misses, leads = [], [], []
    n_event_alarms = 0
    for r in ev.itertuples():
        res = results.get(r.series_id)
        if res is None:
            continue
        onset = pd.Timestamp(r.onset_eff)
        n_event_alarms += len(res.alarms)
        qual = _qualifying_alarms(res, onset, min_lead)
        if qual:
            first = min(qual, key=lambda a: a.first_fired_at)
            lead_h = (onset - first.first_fired_at).total_seconds() / 3600.0
            leads.append(lead_h)
            hits.append({"event_id": r.event_id, "series_id": r.series_id,
                         "onset_utc": onset, "lead_h": round(lead_h, 1),
                         "max_severity": first.max_severity,
                         "confidence": round(first.max_confidence, 3),
                         "fired_conditions": "|".join(first.fired_conditions)})
        else:
            lo = onset - pd.Timedelta(hours=HIT_WINDOW_H)
            in_window = [a for a in res.alarms
                         if a.last_active_at >= lo and a.first_fired_at <= onset]
            reason = ("insufficient_lead" if in_window
                      else "alarm_outside_window" if res.alarms else "no_alarm")
            best = max((a.max_confidence for a in res.alarms), default=0.0)
            misses.append({"event_id": r.event_id, "series_id": r.series_id,
                           "onset_utc": onset, "reason": reason,
                           "best_confidence": round(best, 3),
                           "lat": r.lat, "lon": r.lon, "country": r.country,
                           "event_type": r.event_type, "major": r.major})

    false_alarms = []
    control_hours = 0
    for r in ct.itertuples():
        res = results.get(r.series_id)
        if res is None:
            continue
        control_hours += len(res.times)
        for a in res.alarms:
            false_alarms.append({
                "series_id": r.series_id, "event_id": r.event_id,
                "event_class": klass, "control_year": r.control_year,
                "control_quality": r.control_quality,
                "first_fired_at": a.first_fired_at,
                "last_active_at": a.last_active_at,
                "max_severity": a.max_severity,
                "confidence": round(a.max_confidence, 3),
                "fired_conditions": "|".join(a.fired_conditions)})

    n_scored_events = len(hits) + len(misses)
    n_false = len(false_alarms)
    all_alarms = n_false + n_event_alarms
    loc_years = control_hours / HOURS_PER_LOC_YEAR
    leads_arr = np.array(sorted(leads))
    return {
        "event_class": klass,
        "n_events": n_scored_events,
        "n_controls": int((ct["series_id"].isin(results.keys())).sum()),
        "hits": len(hits),
        "pod": len(hits) / n_scored_events if n_scored_events else float("nan"),
        "n_false_alarms": n_false,
        "n_event_alarms": n_event_alarms,
        "far": n_false / all_alarms if all_alarms else float("nan"),
        "control_loc_years": round(loc_years, 3),
        "budget_per_loc_year": (n_false / loc_years if loc_years
                                else float("nan")),
        "median_lead_h": float(np.median(leads_arr)) if len(leads) else float("nan"),
        "lead_p25_h": float(np.percentile(leads_arr, 25)) if leads else float("nan"),
        "lead_p75_h": float(np.percentile(leads_arr, 75)) if leads else float("nan"),
        "lead_min_h": float(leads_arr[0]) if leads else float("nan"),
        "lead_max_h": float(leads_arr[-1]) if leads else float("nan"),
        "hit_list": hits, "miss_list": misses, "false_alarm_list": false_alarms,
        "leads_h": [round(x, 1) for x in leads],
    }


def passes_frozen(m: dict) -> dict:
    """Per-criterion pass/fail against the frozen numbers (NaN never passes)."""
    t = FROZEN[m["event_class"]]
    ok = {
        "pod": m["pod"] >= t["pod"],
        "far": m["far"] <= t["far"],
        "median_lead": m["median_lead_h"] >= t["min_lead_h"],
        "budget": m["budget_per_loc_year"] <= BUDGET_MAX_PER_LOC_YEAR,
    }
    ok = {k: bool(v) and not pd.isna(v) for k, v in ok.items()}
    ok["all"] = all(ok.values())
    return ok


# --------------------------------------------------------------------------- #
# report writing
# --------------------------------------------------------------------------- #

def _fmt(x, nd=2):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def write_outputs(all_metrics: list, cross_budget: dict, out_dir: str,
                  cohort: str, partial: bool, config_path: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for m in all_metrics:
        t, ok = FROZEN[m["event_class"]], passes_frozen(m)
        rows.append({k: m[k] for k in
                     ("event_class", "n_events", "n_controls", "hits", "pod",
                      "n_event_alarms", "n_false_alarms", "far",
                      "control_loc_years", "budget_per_loc_year",
                      "median_lead_h", "lead_p25_h", "lead_p75_h")}
                    | {"pod_target": t["pod"], "far_target": t["far"],
                       "min_lead_target_h": t["min_lead_h"],
                       "budget_target": BUDGET_MAX_PER_LOC_YEAR,
                       "pass_all": ok["all"]})
    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(out_dir, "results.csv"), index=False)

    misses = pd.DataFrame([x for m in all_metrics for x in m["miss_list"]])
    fas = pd.DataFrame([x for m in all_metrics for x in m["false_alarm_list"]])
    leads = pd.DataFrame([{"event_class": m["event_class"], "lead_h": v}
                          for m in all_metrics for v in m["leads_h"]])
    misses.to_csv(os.path.join(out_dir, "misses.csv"), index=False)
    fas.to_csv(os.path.join(out_dir, "false_alarms.csv"), index=False)
    leads.to_csv(os.path.join(out_dir, "lead_times.csv"), index=False)

    lines = [f"# Backtest results - {cohort} cohort", ""]
    if partial:
        lines += ["> **PARTIAL DATA / PLACEHOLDER CONFIG.** Extraction still "
                  "running and/or the config is untuned; these numbers validate "
                  "the machinery, not the algorithm.", ""]
    lines += [f"Generated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M:%S} UTC. "
              f"Config: `{os.path.basename(config_path)}` "
              f"(sha256 `{_sha256_file(config_path)[:16]}...`). "
              "Metrics follow the frozen definitions in PLAN.md verbatim; "
              "targets shown in parentheses.", "",
              "| class | events | controls | POD | FAR | budget /loc-yr | "
              "median lead h | lead IQR h | pass |",
              "|---|---|---|---|---|---|---|---|---|"]
    for m in all_metrics:
        t, ok = FROZEN[m["event_class"]], passes_frozen(m)
        flag = "PASS" if ok["all"] else "fail: " + ",".join(
            k for k, v in ok.items() if k != "all" and not v)
        lines.append(
            f"| {m['event_class']} | {m['n_events']} | {m['n_controls']} "
            f"| {_fmt(m['pod'])} (>={t['pod']}) | {_fmt(m['far'])} (<={t['far']}) "
            f"| {_fmt(m['budget_per_loc_year'])} (<={BUDGET_MAX_PER_LOC_YEAR:.0f}) "
            f"| {_fmt(m['median_lead_h'], 1)} (>={t['min_lead_h']}) "
            f"| {_fmt(m['lead_p25_h'], 1)}..{_fmt(m['lead_p75_h'], 1)} | {flag} |")
    lines += ["", f"Cross-class alarm budget on all controls combined: "
              f"{_fmt(cross_budget.get('alarms_per_loc_year', float('nan')))} "
              f"warnings/loc-yr over {_fmt(cross_budget.get('loc_years', 0.0), 1)} "
              "control location-years (informational; the frozen budget is "
              "per-class above).", ""]
    for m in all_metrics:
        lines += [f"## {m['event_class']} - misses ({len(m['miss_list'])})", ""]
        if m["miss_list"]:
            lines += ["| event_id | onset (UTC) | reason | best conf |", "|---|---|---|---|"]
            lines += [f"| {x['event_id']} | {x['onset_utc']} | {x['reason']} "
                      f"| {x['best_confidence']} |" for x in m["miss_list"]]
        else:
            lines += ["(none)"]
        lines += ["", f"## {m['event_class']} - false alarms "
                  f"({len(m['false_alarm_list'])}) - full list in false_alarms.csv", ""]
        for x in m["false_alarm_list"][:15]:
            lines.append(f"- {x['series_id']} fired {x['first_fired_at']} "
                         f"({x['max_severity']}, conf {x['confidence']}, "
                         f"{x['fired_conditions']})")
        if len(m["false_alarm_list"]) > 15:
            lines.append(f"- ... {len(m['false_alarm_list']) - 15} more in the CSV")
        lines.append("")
    md_path = os.path.join(out_dir, "results.md")
    with open(md_path, "w") as f:
        f.write("\n".join(lines))
    return _sha256_file(os.path.join(out_dir, "results.csv"))


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def run_backtest(cohort: str, config_path: str, classes: list | None,
                 max_events: int | None, out_dir: str,
                 verbose: bool = True) -> list:
    rules = detector.load_config(config_path)
    classes = classes or list(FROZEN)
    all_metrics = []
    cross_alarms, cross_hours = 0, 0
    for klass in classes:
        rows, feats = load_cohort(klass, cohort, max_events=max_events,
                                  verbose=verbose)
        if verbose:
            n_ev = int((rows["role"] == "event").sum())
            print(f"{klass}: {n_ev} events, {len(rows) - n_ev} controls loaded")
        results = run_detector_over(feats, rules[klass])
        m = score_class(klass, rows, results)
        all_metrics.append(m)
        # informational cross-class budget: every class rule over every control
        ctl_ids = set(rows.loc[rows["role"] == "control", "series_id"])
        for sid in ctl_ids & set(feats):
            fdf = feats[sid]
            cross_hours += len(fdf)
            for ok, rule in rules.items():
                if ok == klass:
                    cross_alarms += len(results[sid].alarms)
                else:
                    cross_alarms += len(run_detector_over({sid: fdf}, rule)[sid].alarms)
    cross_budget = {
        "loc_years": cross_hours / HOURS_PER_LOC_YEAR,
        "alarms_per_loc_year": (cross_alarms / (cross_hours / HOURS_PER_LOC_YEAR)
                                if cross_hours else float("nan")),
    }
    manifest = (data.load_manifest() if cohort == "dev"
                else data._read_manifest_raw().query("cohort == 'holdout'"))
    partial = len(set(manifest["series_id"]) & data.done_series_ids()) < len(manifest)
    digest = write_outputs(all_metrics, cross_budget, out_dir, cohort,
                           partial, config_path)
    if verbose:
        print(f"results -> {out_dir} (partial={partial})")
    return all_metrics, digest, partial


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cohort", choices=["dev", "holdout"], default="dev")
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--classes", nargs="+", choices=list(FROZEN), default=None)
    ap.add_argument("--max-events", type=int, default=None)
    ap.add_argument("--out", default=None,
                    help="output dir (default results_<cohort>/ next to this file)")
    ap.add_argument("--holdout", action="store_true",
                    help="required (with --i-understand-single-use) for --cohort holdout")
    ap.add_argument("--i-understand-single-use", action="store_true")
    args = ap.parse_args()

    out_dir = args.out or os.path.join(HERE, f"results_{args.cohort}")
    marker = None
    if args.cohort == "holdout":
        marker = holdout_gate(args.holdout, args.i_understand_single_use,
                              args.config)
        print("holdout gate passed - this is THE single holdout run; "
              f"marker written to {MARKER_PATH}")
    _, digest, _ = run_backtest(args.cohort, args.config, args.classes,
                                args.max_events, out_dir)
    if marker is not None:
        finalize_marker(marker, digest)
        print("holdout marker finalized (results digest recorded)")


if __name__ == "__main__":
    main()
