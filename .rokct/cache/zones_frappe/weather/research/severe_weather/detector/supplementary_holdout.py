"""Post-hoc breakdowns of the SINGLE holdout backtest (reporting, not tuning).

Slices ONLY the recorded artifacts of the one gated run
(results_holdout/holdout_cache.pkl: manifest rows, per-event outcomes, hazard
arrays, armed-hour counts, all captured during that run). No holdout series
file is opened here; the single-use marker stays as finalized.

Reuses the exact breakdown functions from supplementary_dev.py (severity /
region / contamination / de-seasonalized budget) so holdout and dev post-hoc
numbers are computed identically.

Usage: python3 supplementary_holdout.py -> posthoc_holdout.md (fragment)
"""
from __future__ import annotations

import os
import pickle
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import supplementary_dev as sd
from supplementary_dev import (bucket_stats, deaths_bucket, damage_bucket,
                               severity_bucket, md_table, event_table,
                               contamination, ANCHORS, CLASSES,
                               FROZEN_ANNUALIZATION, SEASON_WINDOWS_PER_YEAR)

CACHE = os.path.join(HERE, "results_holdout", "holdout_cache.pkl")
CATALOG = os.path.normpath(os.path.join(HERE, "..", "catalog",
                                        "events.parquet"))
OUT = os.path.join(HERE, "posthoc_holdout.md")


def anchor_report_holdout(tables: dict) -> list:
    cat = pd.read_parquet(CATALOG).set_index("event_id")
    lines = ["| anchor | class | sampled rows in holdout | outcome |",
             "|---|---|---|---|"]
    for label, rep in ANCHORS:
        if rep not in cat.index:
            continue
        row = cat.loc[rep]
        klass = row["event_class"]
        t = tables.get(klass)
        if t is None:
            continue
        near = t[(abs(pd.to_datetime(t["onset_catalog"])
                      - pd.Timestamp(row["start_utc"])) <= pd.Timedelta(days=2))
                 & (abs(t["lat"] - row["lat"]) <= 3.0)
                 & (abs(t["lon"] - row["lon"]) <= 3.0)]
        if len(near) == 0:
            status = ("dev cohort (pre-2018), evaluated in SUPPLEMENTARY_DEV.md"
                      if pd.Timestamp(row["start_utc"])
                      < pd.Timestamp("2018-01-01")
                      else "not sampled into holdout")
            lines.append(f"| {label} | {klass} | 0 | {status} |")
            continue
        hits = near[near["hit"]]
        if len(hits):
            leads = ", ".join(f"{v:.0f}h" for v in sorted(hits["lead_h"]))
            outcome = f"HIT {len(hits)}/{len(near)} (leads: {leads})"
        else:
            reasons = near["miss_reason"].value_counts()
            outcome = ("MISSED " + f"0/{len(near)} ("
                       + ", ".join(f"{k} x{v}" for k, v in reasons.items())
                       + ")")
        lines.append(f"| {label} | {klass} | {len(near)} | {outcome} |")
    return lines


def main():
    with open(CACHE, "rb") as f:
        cache = pickle.load(f)
    metrics = cache["metrics"]
    all_res, tables, cont = {}, {}, {}
    for klass in CLASSES:
        res = {"rows": cache[klass]["rows"], "metrics": metrics[klass],
               "hazard": cache[klass]["hazard"],
               "armed": cache[klass]["armed"]}
        all_res[klass] = res
        tables[klass] = event_table(klass, res)
        cont[klass] = contamination(klass, res)

    L = []
    # severity
    L += ["### POD by severity (post-hoc)", ""]
    for klass in CLASSES:
        t = tables[klass]
        L += [f"#### {klass}", ""]
        mb = bucket_stats(t, t["major"].map({True: "major",
                                             False: "non-major"}))
        L += md_table(mb.sort_index(), "major flag") + [""]
        db = bucket_stats(t, t["deaths"].map(deaths_bucket))
        order = [b for b in ("0", "1-9", "10+", "unknown") if b in db.index]
        L += md_table(db.loc[order], "deaths") + [""]
        sb = bucket_stats(t, t.apply(severity_bucket, axis=1))
        L += md_table(sb.sort_index(), "magnitude bucket") + [""]
        if t["damage_usd"].notna().any():
            gb = bucket_stats(t, t["damage_usd"].map(damage_bucket))
            order = [b for b in ("$0", "<$1M", "$1M-$100M", ">$100M",
                                 "unknown") if b in gb.index]
            L += md_table(gb.loc[order], "damage") + [""]

    # region / year
    L += ["### POD by region and year (post-hoc)", ""]
    for klass in CLASSES:
        t = tables[klass]
        L += [f"#### {klass}", ""]
        L += md_table(bucket_stats(t, "region3").sort_index(), "region") + [""]
        yr = bucket_stats(t, "year")
        yr.index = [str(int(y)) for y in yr.index]
        L += md_table(yr, "year") + [""]

    # anchors
    L += ["### Named holdout-era anchor events", "",
          "Representative anchor rows from `catalog/ANCHORS.md` plus catalog "
          "siblings sampled into holdout (same class, onset within 2 days, "
          "within 3 deg of the representative point).", ""]
    L += anchor_report_holdout(tables) + [""]

    # contamination
    L += ["### Control-contamination check (post-hoc)", "",
          "| class | hazard | false alarms | >=p99 | >=p99.9 | >=event peak | "
          "US alarms: >=p99.9 | non-US alarms: >=p99.9 |",
          "|---|---|---|---|---|---|---|---|"]
    for klass in CLASSES:
        c = cont[klass]
        r, ru, rn = (c["alarm_rates"], c["alarm_rates_us"],
                     c["alarm_rates_nonus"])
        n_us = c["n_alarms_us"]
        n_non = c["n_false"] - n_us
        L.append(
            f"| {klass} | {'24h precip' if c['var'] == 'p24' else 'gust'} "
            f"| {c['n_false']} | {r['c_p99']:.0%} | {r['c_p999']:.0%} "
            f"| {r['c_evpeak']:.0%} "
            f"| {'-' if n_us == 0 else format(ru['c_p999'], '.0%')} (n={n_us}) "
            f"| {'-' if n_non == 0 else format(rn['c_p999'], '.0%')} "
            f"(n={n_non}) |")
    L += ["", "Post-hoc adjusted FAR / budget with contaminated control "
          "windows excluded (the frozen numbers remain the metrics of "
          "record):", "",
          "| class | frozen FAR | FAR excl. >=p99.9 | FAR excl. >=event-peak "
          "| frozen budget | budget excl. >=p99.9 | budget excl. "
          ">=event-peak |",
          "|---|---|---|---|---|---|---|"]
    for klass in CLASSES:
        m = metrics[klass]
        a = cont[klass]["adjusted"]
        L.append(f"| {klass} | {m['far']:.3f} | {a['c_p999']['far']:.3f} "
                 f"| {a['c_evpeak']['far']:.3f} "
                 f"| {m['budget_per_loc_year']:.2f} "
                 f"| {a['c_p999']['budget']:.2f} "
                 f"| {a['c_evpeak']['budget']:.2f} |")

    # budget note
    L += ["", "### De-seasonalized alarm-budget note (post-hoc)", "",
          "| class | false alarms / 408h control window | frozen: /loc-yr "
          f"(x{FROZEN_ANNUALIZATION:.1f}) | season-only: /yr "
          f"(x{SEASON_WINDOWS_PER_YEAR:.1f}, quiet=0) | control hours at "
          "watch+ | at warning+ |",
          "|---|---|---|---|---|---|"]
    for klass in CLASSES:
        m = metrics[klass]
        arm = all_res[klass]["armed"]
        w = m["n_false_alarms"] / m["n_controls"]
        L.append(f"| {klass} | {w:.3f} | {m['budget_per_loc_year']:.2f} "
                 f"| {w * SEASON_WINDOWS_PER_YEAR:.2f} "
                 f"| {arm['watch_plus'] / arm['hours']:.2%} "
                 f"| {arm['warning_plus'] / arm['hours']:.2%} |")
    L += [""]

    with open(OUT, "w") as f:
        f.write("\n".join(L))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
