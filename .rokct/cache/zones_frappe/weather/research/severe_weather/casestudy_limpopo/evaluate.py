"""Evaluate the frozen detector's alarms against documented Limpopo flood events.

Scoring mirrors detector/backtest.py's frozen conventions: a hit is a
warning-or-worse episode of the class active in [onset - 7 d, onset] whose first
firing precedes onset by at least the class minimum lead (flood 24 h,
flash_flood 6 h). Lead = onset - first_fired_at.

Ground-truth onsets (UTC; sources in LIMPOPO_CASE_STUDY.md):
  * rain_onset  - when damaging rain/flash flooding began over the upper basin
                  (applies to thohoyandou, musina, pafuri, mapai);
  * river_onset - when the lower-Limpopo river flood reached Chokwe/Xai-Xai
                  (applies to chokwe, xai_xai).

Outputs: evaluation.json (+ printed tables pasted into the case study).
"""
from __future__ import annotations

import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
UPPER = ["thohoyandou", "musina", "pafuri", "mapai"]
LOWER = ["chokwe", "xai_xai"]
MIN_LEAD_H = {"flood": 24, "flash_flood": 6}
HIT_WINDOW_H = 168

EVENTS = [
    {"id": "1977", "label": "Feb 1977 (TS Emilie)",
     "rain_onset": "1977-02-01", "river_onset": "1977-02-12"},
    {"id": "2000", "label": "Feb 2000 (Connie antecedent + Eline)",
     "rain_onset": "2000-02-08", "river_onset": "2000-02-12",
     "secondary": "2000-02-25"},
    {"id": "2013", "label": "Jan 2013",
     "rain_onset": "2013-01-14", "river_onset": "2013-01-22"},
    {"id": "2026", "label": "Dec 2025 - Feb 2026 (BLIND)",
     "rain_onset": "2026-01-12", "river_onset": "2026-01-20"},
]


def main():
    al = pd.read_csv(os.path.join(HERE, "alarms.csv"),
                     parse_dates=["first_fired_at", "last_active_at"])
    out = {"per_event": [], "yearly_counts": {}, "flood_alarm_list": []}

    print("== per-event scoring (flood + flash_flood classes) ==")
    for ev in EVENTS:
        for point in UPPER + LOWER:
            onset = pd.Timestamp(ev["rain_onset"] if point in UPPER
                                 else ev["river_onset"])
            lo = onset - pd.Timedelta(hours=HIT_WINDOW_H)
            for klass in ("flood", "flash_flood"):
                cand = al[(al["point"] == point) & (al["event_class"] == klass)]
                # any episode overlapping the pre-onset window
                win = cand[(cand["last_active_at"] >= lo)
                           & (cand["first_fired_at"] <= onset)]
                qual = win[win["first_fired_at"]
                           <= onset - pd.Timedelta(hours=MIN_LEAD_H[klass])]
                # context: episodes during the event itself (onset .. +10 d)
                during = cand[(cand["first_fired_at"] > onset)
                              & (cand["first_fired_at"]
                                 <= onset + pd.Timedelta(days=10))]
                rec = {"event": ev["id"], "point": point, "class": klass,
                       "onset": str(onset.date()),
                       "hit": bool(len(qual)),
                       "n_in_window": int(len(win)),
                       "n_during": int(len(during))}
                if len(qual):
                    first = qual.sort_values("first_fired_at").iloc[0]
                    rec["first_fired"] = str(first["first_fired_at"])
                    rec["lead_h"] = round(
                        (onset - first["first_fired_at"]).total_seconds() / 3600, 1)
                    rec["max_severity"] = first["max_severity"]
                    rec["confidence"] = float(first["max_confidence"])
                elif len(win):
                    first = win.sort_values("first_fired_at").iloc[0]
                    rec["first_fired"] = str(first["first_fired_at"])
                    rec["lead_h"] = round(
                        (onset - first["first_fired_at"]).total_seconds() / 3600, 1)
                    rec["note"] = "in window but lead below class minimum"
                out["per_event"].append(rec)
                if len(win) or len(during):
                    print(rec)

    # yearly episode counts per class (modern era), to judge rarity
    al["year"] = al["first_fired_at"].dt.year
    yc = (al[al["era"] == "modern"]
          .groupby(["event_class", "year"]).size().unstack(fill_value=0))
    print("\n== modern-era episodes per year (all 6 points combined) ==")
    print(yc.T.to_string())
    out["yearly_counts"] = {k: {int(y): int(v) for y, v in row.items()}
                            for k, row in yc.iterrows()}

    fl = al[al["event_class"] == "flood"].sort_values("first_fired_at")
    print(f"\n== all flood-class episodes ({len(fl)}) ==")
    print(fl.drop(columns=["year"]).to_string(index=False))
    out["flood_alarm_list"] = fl.drop(columns=["year"]).astype(str).to_dict("records")

    ff = al[al["event_class"] == "flash_flood"]
    print(f"\nflash_flood episodes total: {len(ff)}; "
          f"per point-year (modern): "
          f"{len(ff[ff.era == 'modern']) / (6 * 31.6):.2f}")

    with open(os.path.join(HERE, "evaluation.json"), "w") as f:
        json.dump(out, f, indent=2, default=str)
    print("-> evaluation.json")


if __name__ == "__main__":
    main()
