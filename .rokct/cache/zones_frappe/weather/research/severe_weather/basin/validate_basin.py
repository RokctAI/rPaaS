"""Historical validation of the upstream-flood basin signal (basin.py).

Replays the EXACT production signal math (the engine module is loaded by
file path - no copy of the logic) causally over hourly ERA5 precipitation
from the public s3://openmeteo archive, at documented downstream flood
events, and reports when each tier (advisory / heads_up / warning) would
first have fired relative to the documented downstream milestone.

Validation cases (all pre-2018 - thresholds in basin.DEFAULTS were chosen
against these; the 2026 case is a BLIND demonstration, run with the same
frozen numbers, never a tuning input):

  limpopo_1977   Chokwe / Xai-Xai inundated 12 Feb 1977 (river-routed; the
                 local detector was silent at Chokwe until in-event -
                 LIMPOPO_CASE_STUDY.md)
  laingsburg_1981  Buffels River flood wave hit Laingsburg 25 Jan 1981
                 (~08:00 local overflow, town flooded by 14:00 local;
                 104+ deaths). Small catchment (~2,264 km2 mapped) - the
                 documented stress test of this signal's lower limit.
  limpopo_2000   Limpopo overflowed at Chokwe/Xai-Xai 11-13 Feb 2000 (peak
                 flow at Chokwe 13 Feb); second crest 25-27 Feb after Eline.
  limpopo_2013   Chokwe evacuation from 22 Jan 2013, town inundated
                 23-25 Jan.
  limpopo_2026   BLIND DEMO - Xai-Xai area evacuation order 20 Jan 2026,
                 Gaza >40% submerged (national disaster declared 18 Jan).

Sources for the milestone dates: LIMPOPO_CASE_STUDY.md section 1 (fully
referenced); Laingsburg - SA History Online / 1981 flood literature
(re-verified 2026-08-21: rain 24-25 Jan over the Baviaans/Wilgerhout/
Buffels catchment, flood through town midday 25 Jan).

Also computed with --baseline: the 1995-2017 (dev-era) alarm climatology of
the signal at Chokwe - episodes per year at each tier - so the lead-time
claims come with an honest false-alarm denominator.

Usage (network: anonymous S3 ranged reads, cached under extraction/cache):
    python validate_basin.py [--baseline] [--case NAME ...]

Output: verdicts to stdout + results JSON next to this script
(basin_validation.json), consumed by BASIN.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "weather", "research",
                                "severe_weather", "extraction"))

import era5_extract  # noqa: E402  (research extraction infra)

ENGINE_BASIN = os.path.join(REPO, "weather", "frappe", "src", "control",
                            "warnings_engine", "basin.py")

spec = importlib.util.spec_from_file_location("engine_basin", ENGINE_BASIN)
basin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(basin)

UTC = dt.datetime

CASES = {
    "limpopo_1977": {
        "targets": {"chokwe": (-24.53, 32.98), "xai_xai": (-25.05, 33.64)},
        "window": (UTC(1977, 1, 10), UTC(1977, 3, 5)),
        "milestone": UTC(1977, 2, 12, 0),
        "milestone_desc": "Chokwe/Xai-Xai inundation 12 Feb 1977",
    },
    "laingsburg_1981": {
        "targets": {"laingsburg": (-33.196, 20.858)},
        "window": (UTC(1981, 1, 10), UTC(1981, 2, 5)),
        # Buffels overflowed ~08:00 local (06:00 UTC); town under water by
        # 14:00 local (12:00 UTC) on 25 Jan 1981.
        "milestone": UTC(1981, 1, 25, 6),
        "milestone_desc": "Buffels River flood through Laingsburg 25 Jan 1981",
    },
    "limpopo_2000": {
        "targets": {"chokwe": (-24.53, 32.98), "xai_xai": (-25.05, 33.64)},
        "window": (UTC(2000, 1, 1), UTC(2000, 3, 15)),
        "milestone": UTC(2000, 2, 11, 0),
        "milestone_desc": "Limpopo overflow at Chokwe/Xai-Xai 11-13 Feb 2000",
    },
    "limpopo_2013": {
        "targets": {"chokwe": (-24.53, 32.98), "xai_xai": (-25.05, 33.64)},
        "window": (UTC(2013, 1, 1), UTC(2013, 2, 15)),
        "milestone": UTC(2013, 1, 22, 0),
        "milestone_desc": "Chokwe evacuation from 22 Jan 2013",
    },
    "limpopo_2026": {
        "targets": {"chokwe": (-24.53, 32.98), "xai_xai": (-25.05, 33.64)},
        "window": (UTC(2025, 12, 15), UTC(2026, 2, 15)),
        "milestone": UTC(2026, 1, 20, 0),
        "milestone_desc": "Xai-Xai area evacuation order 20 Jan 2026 (BLIND DEMO)",
        "blind_demo": True,
    },
}

TIERS = ("advisory", "heads_up", "warning")


def fetch_precip(lat, lon, start, end):
    return era5_extract.fetch_variable(lat, lon, start, end, "precipitation")


def signal_series(target_latlon, start, end, cfg, art):
    """Hourly causal replay: for every hour h in [start+168h, end) compute
    the production signal from the trailing accumulations at the sampled
    upstream cells. Returns (times, signals, tiers, local72)."""
    key = basin.cell_key(*target_latlon)
    upstream = basin.upstream_subbasins(art, key, cfg["max_dist_km"])
    area = sum(u["sub_area_km2"] for u in upstream)
    points = basin.select_points(upstream, cfg)
    if not points or area < cfg["min_upstream_area_km2"]:
        return None
    fetch_start = start - dt.timedelta(hours=basin.ACCUM_LONG_H)
    series = {p["key"]: fetch_precip(p["lat"], p["lon"], fetch_start, end)
              for p in points}
    local = fetch_precip(target_latlon[0], target_latlon[1], fetch_start, end)
    n = int((end - start).total_seconds() // 3600)
    off = basin.ACCUM_LONG_H
    times, signals, tiers, local72 = [], [], [], []
    for h in range(n):
        t = start + dt.timedelta(hours=h)
        accums = {}
        for p in points:
            window = series[p["key"]][h:off + h]
            accums[p["key"]] = (basin.accumulate(window, basin.ACCUM_SHORT_H),
                                basin.accumulate(window, basin.ACCUM_LONG_H))
        sig = basin.signal_from_accums(points, accums, area, cfg)
        times.append(t)
        signals.append(sig)
        tiers.append(basin.tier_for_signal(sig, cfg))
        local72.append(basin.accumulate(local[h:off + h], basin.ACCUM_SHORT_H))
    return {"times": times, "signals": signals, "tiers": tiers,
            "local72": local72, "n_points": len(points),
            "upstream_area_km2": round(area, 1)}


def first_crossings(times, tiers):
    """{tier: first time at/above that tier}."""
    rank = {t: i + 1 for i, t in enumerate(TIERS)}
    out = {}
    for t, tier in zip(times, tiers):
        if tier is None:
            continue
        for name, r in rank.items():
            if rank[tier] >= r and name not in out:
                out[name] = t
    return out


def episodes(times, tiers, min_tier="heads_up"):
    """Contiguous runs at/above min_tier -> [(start, end)]."""
    rank = {t: i + 1 for i, t in enumerate(TIERS)}
    need = rank[min_tier]
    runs, cur = [], None
    for t, tier in zip(times, tiers):
        on = tier is not None and rank[tier] >= need
        if on and cur is None:
            cur = [t, t]
        elif on:
            cur[1] = t
        elif cur is not None:
            runs.append(tuple(cur))
            cur = None
    if cur is not None:
        runs.append(tuple(cur))
    return runs


def run_case(name, case, cfg, art):
    print(f"\n=== {name}: {case['milestone_desc']} ===")
    results = {"milestone": case["milestone"].isoformat(),
               "milestone_desc": case["milestone_desc"],
               "blind_demo": bool(case.get("blind_demo")), "targets": {}}
    for tname, latlon in case["targets"].items():
        rep = signal_series(latlon, case["window"][0], case["window"][1],
                            cfg, art)
        if rep is None:
            print(f"  {tname}: no basin coverage (fail-closed)")
            results["targets"][tname] = {"covered": False}
            continue
        cross = first_crossings(rep["times"], rep["tiers"])
        m = case["milestone"]
        tgt = {"covered": True, "n_points": rep["n_points"],
               "upstream_area_km2": rep["upstream_area_km2"],
               "tiers": {}}
        print(f"  {tname}: {rep['n_points']} upstream sample cells, "
              f"{rep['upstream_area_km2']:.0f} km2 upstream")
        for tier in TIERS:
            t = cross.get(tier)
            if t is None:
                print(f"    {tier:9s}: never fired in window")
                tgt["tiers"][tier] = None
                continue
            lead_h = (m - t).total_seconds() / 3600.0
            i = rep["times"].index(t)
            sig = rep["signals"][i]
            loc72 = rep["local72"][i]
            print(f"    {tier:9s}: first {t:%Y-%m-%d %H:%M}Z  "
                  f"lead {lead_h:+7.1f} h ({lead_h / 24:+.1f} d)  "
                  f"upstream72={sig['rain_72h_mm']:.0f}mm "
                  f"lag~{sig['lag_hours']:.0f}h local72="
                  f"{'?' if loc72 is None else format(loc72, '.0f')}mm")
            tgt["tiers"][tier] = {
                "first": t.isoformat(), "lead_hours": round(lead_h, 1),
                "upstream_rain_72h_mm": sig["rain_72h_mm"],
                "lag_hours": sig["lag_hours"],
                "local_rain_72h_mm": None if loc72 is None else round(loc72, 1),
            }
        results["targets"][tname] = tgt
    return results


def fast_signal_series(target_latlon, start, end, cfg, art):
    """Vectorized replica of signal_series for multi-decade baselines.

    The trailing-accumulation math is numpy cumsum instead of the engine's
    per-hour basin.accumulate; equivalence is ASSERTED on 200 random
    (point, hour) samples every run, so the baseline numbers remain the
    production semantics."""
    import numpy as np
    import random

    key = basin.cell_key(*target_latlon)
    upstream = basin.upstream_subbasins(art, key, cfg["max_dist_km"])
    area = sum(u["sub_area_km2"] for u in upstream)
    points = basin.select_points(upstream, cfg)
    if not points or area < cfg["min_upstream_area_km2"]:
        return None
    fetch_start = start - dt.timedelta(hours=basin.ACCUM_LONG_H)
    off = basin.ACCUM_LONG_H
    n = int((end - start).total_seconds() // 3600)
    acc = {}
    raw = {}
    for p in points:
        arr = np.asarray(fetch_precip(p["lat"], p["lon"], fetch_start, end),
                         dtype=np.float64)
        raw[p["key"]] = arr
        finite = np.isfinite(arr)
        csum = np.concatenate(([0.0], np.cumsum(np.where(finite, arr, 0.0))))
        ccnt = np.concatenate(([0], np.cumsum(finite)))
        per_window = {}
        for w in (basin.ACCUM_SHORT_H, basin.ACCUM_LONG_H):
            e = np.arange(off, off + n)
            s = e - w
            sums = csum[e] - csum[s]
            cnts = ccnt[e] - ccnt[s]
            vals = np.where(cnts >= basin.MIN_FINITE_FRAC * w,
                            sums / np.maximum(cnts, 1) * w, np.nan)
            per_window[w] = vals
        acc[p["key"]] = per_window
    # equivalence spot-check vs the engine's accumulate
    rng = random.Random(7)
    for _ in range(200):
        p = rng.choice(points)
        h = rng.randrange(n)
        w = rng.choice((basin.ACCUM_SHORT_H, basin.ACCUM_LONG_H))
        ref = basin.accumulate(raw[p["key"]][h:off + h], w)
        fast = acc[p["key"]][w][h]
        if ref is None:
            assert not np.isfinite(fast), (p["key"], h, w, fast)
        else:
            assert abs(ref - fast) < 1e-6, (p["key"], h, w, ref, fast)
    times, tiers = [], []
    for h in range(n):
        accums = {}
        for p in points:
            a72 = acc[p["key"]][basin.ACCUM_SHORT_H][h]
            a168 = acc[p["key"]][basin.ACCUM_LONG_H][h]
            accums[p["key"]] = (None if np.isnan(a72) else float(a72),
                                None if np.isnan(a168) else float(a168))
        sig = basin.signal_from_accums(points, accums, area, cfg)
        times.append(start + dt.timedelta(hours=h))
        tiers.append(basin.tier_for_signal(sig, cfg))
    return {"times": times, "tiers": tiers, "n_points": len(points),
            "upstream_area_km2": round(area, 1)}


def run_baseline(cfg, art, lat=-24.53, lon=32.98, y0=1995, y1=2018):
    """Dev-era (pre-2018) alarm climatology at Chokwe: honest false-alarm
    denominator for the lead claims. Never touches 2018+ for tuning."""
    print(f"\n=== baseline: chokwe {y0}-{y1 - 1}, episodes per tier ===")
    start, end = UTC(y0, 1, 1), UTC(y1, 1, 1)
    rep = fast_signal_series((lat, lon), start, end, cfg, art)
    out = {}
    for tier in TIERS:
        runs = episodes(rep["times"], rep["tiers"], tier)
        per_yr = len(runs) / float(y1 - y0)
        dur = [(b - a).total_seconds() / 3600 + 1 for a, b in runs]
        out[tier] = {
            "episodes": len(runs), "per_year": round(per_yr, 2),
            "median_duration_h": (sorted(dur)[len(dur) // 2] if dur else 0),
            "starts": [a.isoformat() for a, b in runs],
        }
        print(f"  {tier:9s}: {len(runs)} episodes in {y1 - y0} yr "
              f"({per_yr:.2f}/yr)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append", choices=sorted(CASES))
    ap.add_argument("--baseline", action="store_true")
    args = ap.parse_args()
    cfg = dict(basin.DEFAULTS)
    art = basin.load_map(os.path.join(
        REPO, "weather", "frappe", "src", "control", "warnings_engine",
        "basin_map.json"))
    assert art, "basin_map.json missing - run build_basin_map.py first"
    results = {"config": {k: v for k, v in cfg.items() if k != "enabled"},
               "cases": {}, "baseline": None}
    for name in (args.case or sorted(CASES)):
        results["cases"][name] = run_case(name, CASES[name], cfg, art)
    if args.baseline:
        results["baseline"] = run_baseline(cfg, art)
    out = os.path.join(HERE, "basin_validation.json")
    with open(out, "w", newline="\n") as f:
        json.dump(results, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
