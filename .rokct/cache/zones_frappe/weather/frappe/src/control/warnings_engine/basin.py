# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""Basin-scale flood routing: the upstream-flood signal (wave 5).

THE BLIND SPOT THIS CLOSES (documented, not hypothetical): the per-cell
detector reads local rain-on-saturated-soil, so a downstream cell inheriting
a flood wave from upstream rain is warned late or not at all -
LIMPOPO_CASE_STUDY.md: Chokwe silent until in-event in Feb 1977 while the
upstream escarpment cell had warned 128 h earlier; the first Feb-2000 river
rise missed by the flood rule at every lower-basin point. The classic South
African example is Laingsburg, 25 Jan 1981: the Buffels River flood wave
came down from catchment rain upstream while the town itself was not the
rain center.

WHAT IT DOES: for a watch location's ERA5 cell, aggregate recent OBSERVED
precipitation over the cell's upstream catchment - cells hydrologically
upstream per the committed HydroBASINS-derived basin map (basin_map.json,
see weather/research/severe_weather/basin/) - area-weighted and
distance-banded, into a single upstream-rain quantity. When that quantity
crosses the validated thresholds the cell gets a distinct upstream_flood
record at advisory / heads_up / warning severity, with calm river-specific
copy from the message layer and full technical detail (sampled upstream
cells, per-cell accumulations, flow distances, lag estimate) in the admin
precursors JSON. Thresholds were validated on pre-2018 basin history only
(1977, 2000, 2013 Limpopo; 1981 Laingsburg - see
weather/research/severe_weather/basin/BASIN.md); the Dec 2025 - Feb 2026
Limpopo event is a blind demonstration, never a tuning input.

STRICT NON-INTERFERENCE CONTRACT (mirrors climatology.py / cold_front.py):
  - the frozen per-class detector is untouched; nothing here is an input to
    detector.run_class, and nothing here can create, suppress or re-tier a
    flash_flood / flood / destructive_wind / tornado episode;
  - upstream_flood is its OWN event class with its own copy surface
    (messages.py) and its own record lifecycle, owned entirely by this
    module plus the daily sweep;
  - fail-closed everywhere: no basin map, a cell outside the mapped region,
    a cell with too small an upstream catchment, a data fetch failure -
    each degrades to "no upstream signal", never to an error a user can
    see and never to a changed evaluation of the frozen classes;
  - evaluate_cell NEVER raises (rate-limited admin log inside).

COST: at most MAX_POINTS upstream sample cells per watch cell, one
variable (precipitation), ACCUM_LONG_H hours - a handful of ranged reads
per cell per data-horizon advance, cached cross-location for CACHE_TTL_S
(nearby watch cells share upstream sample cells). The basin map itself is
a one-time ~340 KB JSON load, cached per process.

FORECAST: deliberately observed-rain only in v1. The fusion module's
forecast covers the LOCAL cell - useless here by construction (the whole
point is rain the local cell does not see). Upstream forecast aggregation
is the documented follow-up in BASIN.md.

Site-config flags (frappe.conf, severe_weather_basin_<key> over DEFAULTS):
  severe_weather_basin_enabled          master switch; default ON
                                        ("0"/"false"/"no"/"off" disables)
  severe_weather_basin_<threshold key>  any numeric DEFAULTS override

This module is importable STANDALONE (no frappe, no package context): the
research validation harness (weather/research/severe_weather/basin/) loads
it by file path and replays the exact production signal math over decades
of ERA5 history. Everything frappe- or engine-relative is imported lazily
inside the shell functions at the bottom.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os

EVENT_CLASS = "upstream_flood"

#: stable admin Error Log title (grep key; rate-limited via admin_log)
TITLE_BASIN = "SevereWeather: basin routing failed"

#: precursors mode discriminator - basin records are recognisable to every
#: other pass (and excluded from advisory seeding / consensus, which key on
#: their own class tables and do not know this class).
BASIN_MODE = "basin_upstream"

#: the committed artifact, produced by
#: weather/research/severe_weather/basin/build_basin_map.py from
#: HydroBASINS v1c level 7 (license: free for commercial use, attribution
#: required - carried inside the artifact's "source" block).
MAP_FILENAME = "basin_map.json"

#: trailing accumulation windows over upstream cells (hours).
ACCUM_SHORT_H = 72
ACCUM_LONG_H = 168

#: fraction of an accumulation window that must be finite per sampled cell.
MIN_FINITE_FRAC = 0.75

#: configuration defaults; every numeric key is overridable via site config
#: "severe_weather_basin_<key>". Thresholds are mm of area-weighted rain
#: accumulated over the sampled upstream catchment - values set by the
#: pre-2018 validation in BASIN.md (Limpopo 1977/2000/2013, Laingsburg 1981).
DEFAULTS = {
    "enabled": 1,                   # master switch (the flag is an off-switch)
    "min_upstream_area_km2": 2000.0,  # below this the cell has no meaningful
                                      # river-routed exposure - no-op
    "max_dist_km": 1500.0,          # ignore catchment beyond this flow distance
    "max_points": 12,               # upstream sample cells per watch cell
    "celerity_kmh": 4.0,            # flood-wave speed for the lag estimate
                                    # (Limpopo 2000: ~400 km in ~4 days)
    "advisory_mm_72h": 40.0,        # area-weighted upstream 72 h rain tiers
    "heads_up_mm_72h": 70.0,
    "warning_mm_72h": 110.0,        # pure 72 h burst arm (small catchments)
    "warning_combo_mm_72h": 60.0,   # compound arm: a still-heavy 72 h rate
    "warning_combo_mm_168h": 120.0, # on top of an extreme 7-day basin total
                                    # - in 23 pre-2018 years at Chokwe this
                                    # combination occurred ONLY in the 1996,
                                    # 2000 and 2013 flood periods (BASIN.md)
    "long_mm_168h": 100.0,          # advisory long-rain arm: sustained 7-day
    "long_short_mm_72h": 30.0,      # basin rain with real 72 h rain still
                                    # falling -> at least advisory
}

#: distance bands (km along the river network) for upstream sampling; each
#: band contributes up to max_points / len(bands) sample cells, largest
#: sub-basins first, so nearby and far catchment are both represented.
DISTANCE_BANDS = ((0.0, 150.0), (150.0, 400.0), (400.0, 800.0),
                  (800.0, 1500.0))

#: validity horizon of a surfaced record: the estimated arrival lag plus a
#: buffer, clamped - upstream water takes days, not hours, to arrive.
VALIDITY_MIN_H = 24
VALIDITY_MAX_H = 120
VALIDITY_BUFFER_H = 24

#: per-upstream-cell accumulation cache TTL (seconds) - shared by every
#: watch cell that samples the same upstream cell in the same tick family.
CACHE_TTL_S = 2 * 3600

#: retry backoff after a failed upstream fetch for a cell (seconds).
FETCH_BACKOFF_S = 3600

SEVERITY_ORDER = ("advisory", "heads_up", "warning")


# --------------------------------------------------------------------------- #
# basin map loading (pure; cached per process)
# --------------------------------------------------------------------------- #

_map_cache: dict = {"path": None, "map": None, "failed": False}


def default_map_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        MAP_FILENAME)


def load_map(path: str | None = None):
    """The parsed basin artifact, or None (fail-closed) when unavailable.

    Cached per process; a missing/corrupt file is remembered as failed so
    the hourly job does not re-stat/re-parse every tick.
    """
    path = path or default_map_path()
    if _map_cache["path"] == path:
        return _map_cache["map"]
    art = None
    try:
        with open(path) as f:
            candidate = json.load(f)
        if (isinstance(candidate, dict) and candidate.get("version") == 1
                and "subbasins" in candidate and "cells" in candidate):
            art = candidate
            # index: sub-basin -> its direct upstream neighbours
            ups: dict = {}
            for hid, row in art["subbasins"].items():
                ups.setdefault(str(row[0]), []).append(hid)
            art["_upstream_index"] = ups
    except Exception:
        art = None
    _map_cache.update(path=path, map=art, failed=art is None)
    return art


def cell_key(latitude: float, longitude: float) -> str:
    """ERA5 join discipline (PLAN.md section 1): index 0 = 90S / 180W."""
    la = int(round((float(latitude) + 90.0) / 0.25))
    lo = int(round((float(longitude) + 180.0) / 0.25)) % 1440
    return f"{la}_{lo}"


def key_latlon(key: str) -> tuple[float, float]:
    la, lo = key.split("_")
    return int(la) * 0.25 - 90.0, int(lo) * 0.25 - 180.0


# --------------------------------------------------------------------------- #
# upstream traversal + sample selection (pure)
# --------------------------------------------------------------------------- #

def upstream_subbasins(art: dict, key: str, max_dist_km: float) -> list[dict]:
    """Strictly-upstream sub-basins of the cell's sub-basin, by NEXT_DOWN
    reversal, with along-network distance deltas (km). Sorted near to far.

    [] when the cell is unmapped. The cell's OWN sub-basin is excluded -
    local rain is the frozen detector's job, not this signal's.
    """
    target = art["cells"].get(key)
    if target is None:
        return []
    subs = art["subbasins"]
    ups_index = art["_upstream_index"]
    base = subs[str(target)][2]
    out, seen, frontier = [], {str(target)}, [str(target)]
    while frontier:
        nxt = []
        for t in frontier:
            for up in ups_index.get(t, ()):
                if up in seen:
                    continue
                seen.add(up)
                row = subs[up]
                delta = row[2] - base
                if delta > max_dist_km:
                    continue
                out.append({
                    "hybas_id": int(up),
                    "delta_km": round(max(delta, 0.0), 1),
                    "sub_area_km2": row[3],
                    "up_area_km2": row[4],
                    "rep_key": f"{row[5]}_{row[6]}",
                })
                nxt.append(up)
        frontier = nxt
    out.sort(key=lambda r: (r["delta_km"], -r["sub_area_km2"]))
    return out


def select_points(upstream: list[dict], cfg: dict) -> list[dict]:
    """Distance-banded sample of upstream sub-basins, largest area first
    within each band, merged per representative grid cell.

    Returns [{key, lat, lon, weight_km2, delta_km}] with at most
    cfg["max_points"] entries; weight is the summed sub-basin area behind
    that sample cell, delta the area-weighted mean flow distance.
    """
    max_points = int(cfg["max_points"])
    per_band = max(1, max_points // len(DISTANCE_BANDS))
    chosen: list[dict] = []
    for lo, hi in DISTANCE_BANDS:
        band = [u for u in upstream if lo <= u["delta_km"] < hi]
        band.sort(key=lambda r: -r["sub_area_km2"])
        chosen.extend(band[:per_band])
    if len(chosen) < max_points:
        rest = sorted((u for u in upstream if u not in chosen),
                      key=lambda r: -r["sub_area_km2"])
        chosen.extend(rest[:max_points - len(chosen)])
    merged: dict[str, dict] = {}
    for u in chosen[:max_points * 2]:
        m = merged.setdefault(u["rep_key"], {"key": u["rep_key"],
                                             "weight_km2": 0.0, "_wd": 0.0})
        m["weight_km2"] += u["sub_area_km2"]
        m["_wd"] += u["sub_area_km2"] * u["delta_km"]
    points = []
    for m in merged.values():
        lat, lon = key_latlon(m["key"])
        points.append({
            "key": m["key"], "lat": lat, "lon": lon,
            "weight_km2": round(m["weight_km2"], 1),
            "delta_km": round(m["_wd"] / m["weight_km2"], 1)
            if m["weight_km2"] else 0.0,
        })
    points.sort(key=lambda p: p["delta_km"])
    return points[:max_points]


def accumulate(values, window_h: int):
    """Trailing accumulation (mm) over the last window_h entries of an
    hourly mm/h series; None when finite coverage is below MIN_FINITE_FRAC.
    Gap-tolerant: the mean of finite hours is scaled to the full window."""
    tail = list(values)[-window_h:]
    finite = []
    for v in tail:
        if v is None:
            continue
        try:
            fv = float(v)  # accepts numpy scalars too
        except (TypeError, ValueError):
            continue
        if not math.isnan(fv):
            finite.append(fv)
    if len(tail) < window_h or len(finite) < MIN_FINITE_FRAC * window_h:
        return None
    return (sum(finite) / len(finite)) * window_h


def signal_from_accums(points: list[dict], accums: dict,
                       upstream_area_km2: float, cfg: dict):
    """Area-weighted upstream-rain signal from per-point accumulations.

    accums: {point key: (accum_72h_mm or None, accum_168h_mm or None)}.
    Returns the signal dict, or None when fewer than half the sampled
    weight has usable data (fail-closed - never guess from thin coverage).
    """
    total_w = sum(p["weight_km2"] for p in points)
    if total_w <= 0:
        return None
    w72 = w168 = s72 = s168 = 0.0
    wd = wr = 0.0
    detail = []
    for p in points:
        a72, a168 = accums.get(p["key"], (None, None))
        detail.append({"cell": p["key"], "delta_km": p["delta_km"],
                       "weight_km2": p["weight_km2"],
                       "rain_72h_mm": None if a72 is None else round(a72, 1),
                       "rain_168h_mm": None if a168 is None else round(a168, 1)})
        if a72 is not None:
            w72 += p["weight_km2"]
            s72 += p["weight_km2"] * a72
            wd += p["weight_km2"] * max(a72, 0.01) * p["delta_km"]
            wr += p["weight_km2"] * max(a72, 0.01)
        if a168 is not None:
            w168 += p["weight_km2"]
            s168 += p["weight_km2"] * a168
    if w72 < 0.5 * total_w:
        return None
    rain72 = s72 / w72
    rain168 = (s168 / w168) if w168 >= 0.5 * total_w else None
    mean_dist = (wd / wr) if wr > 0 else 0.0
    lag_h = mean_dist / float(cfg["celerity_kmh"]) if cfg["celerity_kmh"] else 0.0
    return {
        "rain_72h_mm": round(rain72, 1),
        "rain_168h_mm": None if rain168 is None else round(rain168, 1),
        "mean_dist_km": round(mean_dist, 1),
        "lag_hours": round(lag_h, 1),
        "upstream_area_km2": round(upstream_area_km2, 1),
        "sampled_area_km2": round(total_w, 1),
        "points": detail,
    }


def tier_for_signal(signal, cfg: dict):
    """None | advisory | heads_up | warning from the validated thresholds.

    Drivers (area-weighted mm of rain over the sampled upstream catchment):
      warning   a 72 h burst alone (warning_mm_72h - relevant for small,
                fast catchments), OR the compound arm: still-heavy 72 h
                rain (warning_combo_mm_72h) on top of an extreme 7-day
                basin total (warning_combo_mm_168h). On the 1995-2017
                Chokwe baseline the compound arm fired ONLY in the 1996,
                2000 and 2013 documented flood periods.
      heads_up  72 h >= heads_up_mm_72h (0.22 episodes/yr on the baseline,
                every one in a documented flood period).
      advisory  72 h >= advisory_mm_72h, or the long-rain arm: a sustained
                7-day basin total (long_mm_168h) with real 72 h rain still
                falling (long_short_mm_72h).
    """
    if not signal:
        return None
    r72 = signal.get("rain_72h_mm")
    if r72 is None:
        return None
    r168 = signal.get("rain_168h_mm")
    if r72 >= float(cfg["warning_mm_72h"]):
        return "warning"
    if (r168 is not None and r72 >= float(cfg["warning_combo_mm_72h"])
            and r168 >= float(cfg["warning_combo_mm_168h"])):
        return "warning"
    if r72 >= float(cfg["heads_up_mm_72h"]):
        return "heads_up"
    if r72 >= float(cfg["advisory_mm_72h"]):
        return "advisory"
    if (r168 is not None and r168 >= float(cfg["long_mm_168h"])
            and r72 >= float(cfg["long_short_mm_72h"])):
        return "advisory"
    return None


def validity_hours(signal) -> int:
    lag = float((signal or {}).get("lag_hours") or 0.0)
    return int(min(max(lag + VALIDITY_BUFFER_H, VALIDITY_MIN_H),
                   VALIDITY_MAX_H))


# --------------------------------------------------------------------------- #
# configuration (lazy frappe)
# --------------------------------------------------------------------------- #

def load_config() -> dict:
    """DEFAULTS with severe_weather_basin_<key> site-config overrides.
    Never raises (defaults on any trouble)."""
    cfg = dict(DEFAULTS)
    try:
        import frappe
        conf = getattr(frappe, "conf", None) or {}
    except Exception:
        return cfg
    for key, default in DEFAULTS.items():
        raw = conf.get("severe_weather_basin_" + key)
        if raw is None:
            continue
        try:
            if key == "enabled":
                cfg[key] = 0 if str(raw).strip().lower() in (
                    "0", "false", "no", "off") else 1
            elif key == "max_points":
                cfg[key] = int(float(raw))
            else:
                cfg[key] = float(raw)
        except (TypeError, ValueError):
            pass
    return cfg


# --------------------------------------------------------------------------- #
# evaluator shell (frappe; NEVER raises)
# --------------------------------------------------------------------------- #

def _fetch_accums(source, point: dict, horizon) -> tuple:
    """(accum_72h, accum_168h) for one upstream sample cell, cached
    cross-location (nearby watch cells share upstream cells) and backed off
    on failure so a broken cell cannot re-pay fetches every tick."""
    import frappe

    iso = horizon.strftime("%Y%m%d%H")
    cache_key = f"sww_basin_accum_{point['key']}_{iso}"
    backoff_key = f"sww_basin_backoff_{point['key']}"
    try:
        cached = frappe.cache().get_value(cache_key)
        if cached is not None:
            return tuple(cached)
    except Exception:
        pass
    try:
        if frappe.cache().get_value(backoff_key):
            return (None, None)
    except Exception:
        pass
    try:
        start = horizon - dt.timedelta(hours=ACCUM_LONG_H)
        series = source.hourly_series(
            point["lat"], point["lon"], ["precipitation"], start, horizon)
        precip = list(series["precipitation"])
        result = (accumulate(precip, ACCUM_SHORT_H),
                  accumulate(precip, ACCUM_LONG_H))
    except Exception:
        try:
            frappe.cache().set_value(backoff_key, 1,
                                     expires_in_sec=FETCH_BACKOFF_S)
        except Exception:
            pass
        raise
    try:
        frappe.cache().set_value(cache_key, list(result),
                                 expires_in_sec=CACHE_TTL_S)
    except Exception:
        pass
    return result


def compute_cell_signal(source, latitude, longitude, horizon,
                        cfg=None, art=None):
    """The full per-cell pipeline: map -> upstream -> sample -> fetch ->
    signal. Returns (signal or None, tier or None). Raises only for fetch
    problems (caller logs); every no-coverage path returns (None, None)."""
    cfg = cfg or load_config()
    art = art or load_map()
    if art is None:
        return None, None
    key = cell_key(latitude, longitude)
    upstream = upstream_subbasins(art, key, float(cfg["max_dist_km"]))
    if not upstream:
        return None, None
    upstream_area = sum(u["sub_area_km2"] for u in upstream)
    if upstream_area < float(cfg["min_upstream_area_km2"]):
        return None, None
    points = select_points(upstream, cfg)
    if not points:
        return None, None
    accums = {p["key"]: _fetch_accums(source, p, horizon) for p in points}
    signal = signal_from_accums(points, accums, upstream_area, cfg)
    return signal, tier_for_signal(signal, cfg)


def evaluate_cell(source, loc, horizon, now):
    """Evaluator hook (wired at the end of _evaluate_location): compute the
    upstream-flood signal for one watch cell and upsert/expire the cell's
    upstream_flood record. GUARANTEED not to raise."""
    try:
        cfg = load_config()
        if not cfg.get("enabled"):
            return
        if load_map() is None:
            return  # fail-closed: no basin data on this deployment
        signal, tier = compute_cell_signal(
            source, loc.latitude, loc.longitude, horizon, cfg)
        _upsert_basin_record(loc, signal, tier, source, horizon, now)
    except Exception:
        try:
            from ...warnings_engine.admin_log import log_admin_error
            log_admin_error(TITLE_BASIN)
        except Exception:
            pass


def _upsert_basin_record(loc, signal, tier, source, horizon, now):
    """Idempotent upsert of the cell's single upstream_flood record; expiry
    when the signal has lapsed. Mirrors evaluator._upsert_warning but owns
    only this class - it can never touch a frozen-detector record."""
    import frappe

    from ...warnings_engine import messages, push

    existing = frappe.db.get_value(
        "Severe Weather Warning",
        {"watch_location": loc.name, "event_class": EVENT_CLASS,
         "status": "active",
         # drill fence: replay records (warnings_engine/drill.py) are never
         # the live record - updating one would tag real weather as a drill
         "is_drill": ["!=", 1]},
        "name",
    )
    if tier is None:
        if existing:
            frappe.db.set_value("Severe Weather Warning", existing,
                                {"status": "expired"})
        return
    valid_until = horizon + dt.timedelta(hours=validity_hours(signal))
    if valid_until <= now:
        # honest freshness: data too old for this to be a live heads-up
        if existing:
            frappe.db.set_value("Severe Weather Warning", existing,
                                {"status": "expired"})
        return
    rendered = messages.render(EVENT_CLASS, tier, loc.get("label"))
    precursors = json.dumps({
        "mode": BASIN_MODE,
        "signal": signal,
        "tier": tier,
        "data_horizon": horizon.isoformat(),
        "source": getattr(source, "name", "unknown"),
    })
    fields = {
        "severity": rendered["severity"],
        "headline": rendered["headline"],
        "message": rendered["message"],
        "onset": horizon,
        "valid_until": valid_until,
        "precursors": precursors,
        "status": "active",
    }
    if existing:
        frappe.db.set_value("Severe Weather Warning", existing, fields)
        record_name = existing
    else:
        doc = {"doctype": "Severe Weather Warning",
               "watch_location": loc.name,
               "event_class": EVENT_CLASS,
               "issued_at": now}
        doc.update(fields)
        record_name = frappe.get_doc(doc).insert(
            ignore_permissions=True).name
    # push rides the existing severity-ranked pipeline: advisory ranks
    # below heads_up and is never pushed (push._SEVERITY_RANK); a new
    # heads_up/warning episode or an escalation pushes once, exactly like
    # the frozen classes.
    push.notify_warning_upsert(record_name, loc.name, EVENT_CLASS, {
        "severity": fields["severity"],
        "headline": fields["headline"],
        "message": fields["message"],
    })
    # sw6 vulnerable sites (sites.py): the same ride-the-upsert hook as the
    # evaluator - registered bridges/crossings downstream get a per-site
    # river-rise line. Advisory-tier records are skipped inside (site
    # notices exist at heads_up and above only); guaranteed not to raise.
    from .sites import sync_site_notices
    sync_site_notices(record_name, loc.name, EVENT_CLASS,
                      fields["severity"], now)
