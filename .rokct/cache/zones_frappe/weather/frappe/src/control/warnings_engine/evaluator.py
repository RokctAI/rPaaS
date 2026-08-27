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

"""Severe-weather evaluator - the scheduled backend jobs.

Hourly (evaluate_watch_locations): for every active Weather Watch Location,
pull the rolling feature window from the configured data source, compute
features, run the frozen detector, and upsert Severe Weather Warning records.
Daily (sweep_expired_warnings): expire lapsed records and deactivate stale
watch locations.

Safety properties (the jobs run hourly on BOTH shell products for every
site, so all of these are load-bearing):
  - data-horizon short-circuit: a location already evaluated against the
    source's current data horizon is skipped, so most hourly ticks cost one
    small meta read (the ERA5 archive advances daily);
  - idempotent: warnings are keyed (location, event_class, active) and
    re-evaluation updates in place - never duplicates;
  - per-location error isolation: one bad location cannot starve the rest;
    failures land in the desk Error Log under stable rate-limited titles and
    on the location's own health fields (last_error, consecutive_failures);
  - honest freshness: an episode only surfaces to users while
    (data horizon + per-class validity) is still in the future - warnings
    computed from data too old to act on are silently not issued.

All datetimes handled here and stored on the two doctypes are UTC (naive).

Client-facing severity mapping (calm-copy product decision): the detector's
"warning" tier maps to the user severity "heads_up"; only the "severe" tier
maps to the stronger "warning" severity - and tornado is additionally capped
at heads_up (soft "storms possible" line only). A third severity "advisory"
(strictly below heads_up) is owned by the propagation pass (propagation.py):
the evaluator never creates, refreshes, or expires advisory records.

Wave-2 additions (all strictly additive to the frozen wave-1 detector - none
can create, suppress, or re-tier a detector episode):
  climatology.py     per-cell seasonal context annotation + one calm sentence
  fusion.py          forecast timing copy + bounded heads_up->warning upgrade
  propagation.py     neighbor advisories + basin consensus (post-loop pass)
  push.py            push notifications on new episodes / escalations
  official_alerts.py endpoint-side official-alert cross-reference (relay)
  cold_front.py      informational cold-front ("cool change") detection at
                     the ADVISORY tier only; its records seed the neighbor
                     pass but are never pushed and never escalate

Wave-5 addition (strictly additive):
  basin.py           basin-scale flood routing - aggregates observed rain
                     over a cell's upstream catchment (committed
                     HydroBASINS-derived basin_map.json) into a distinct
                     upstream_flood record (advisory/heads_up/warning) so
                     downstream cells hear about river-routed water days
                     ahead, even with no local rain. Fail-closed without
                     basin data; never touches the frozen detector classes.

Wave-6 addition (strictly additive):
  sites.py           vulnerable-site registry glue - admin-registered named
                     assets (Weather Vulnerable Site: schools, clinics,
                     low-water bridges, river crossings) keep their grid
                     cell registered as a watch location, and every active
                     warning upsert additionally upserts one calm per-site
                     notice (Weather Site Notice) served alongside the
                     warning. Fail-closed with no registered sites; never
                     creates, suppresses, or re-tiers a warning record.

Wave-7 addition (strictly additive, admin-only):
  forecast.py        forecast-feed detection - the SAME frozen detector run
                     over the Open-Meteo forecast API timeline (default OFF)
                     so signals can fire AHEAD of events instead of trailing
                     the reanalysis archive. Firings land in their own
                     "Severe Weather Forecast Signal" ledger (basis
                     "forecast"), never touch Severe Weather Warning records
                     or any end-user surface, and are settled hit /
                     false_alarm / missed_event against observed data by a
                     daily verification pass. See FUSION.md.

Wave-3 addition (strictly additive, admin-only):
  outcomes.py        automatic outcome ledger - a daily verification pass
                     records, per ended episode, whether extremes actually
                     materialized (verified / unverified) and flags unwarned
                     disaster-grade extremes as candidate misses. Evidence
                     base for a HUMAN-triggered retraining run; nothing is
                     consumed automatically and nothing is user-facing.

Site-config flags (frappe.conf, per tenant site) - single reference:
  severe_weather_source                   wave 1: data source selector
                                          (default "openmeteo_s3")
  severe_weather_forecast_fusion          fusion; default ON
                                          ("0"/"false"/"no"/"off" disables)
  severe_weather_seasonal_climatology     seasonal context; default ON
  severe_weather_official_alert_relay     relay; default ON for South African
                                          locations only (truthy = everywhere,
                                          falsy = off)
  severe_weather_push_enabled             push MASTER SWITCH; default ON
                                          (the flag is an off-switch)
  severe_weather_push_target              sender dotted path (see push.py)
  severe_weather_push_cooldown_hours      default 12
  severe_weather_push_quiet_hours         optional UTC "HH-HH" window
  weather_propagation_enabled             propagation MASTER SWITCH; default OFF
  weather_propagation_neighbor_radius_km  default 150
  weather_propagation_flood_radius_factor default 0.6
  weather_propagation_direction_half_angle_deg  default 60
  weather_propagation_basin_radius_km     default 300
  weather_propagation_consensus_k         default 4
  severe_weather_cold_front               cold-front advisory MASTER FLAG;
                                          default ON (advisory tier is muted
                                          in current clients; "0"/"false"/
                                          "no"/"off" disables)
  severe_weather_cold_front_cooldown_h    per-cell re-issue cooldown,
                                          default 72
  severe_weather_cold_front_<key>         any other cold_front.DEFAULTS
                                          threshold (see cold_front.py)
  severe_weather_outcome_ledger           outcome ledger (outcomes.py);
                                          default ON
  severe_weather_basin_enabled            basin routing MASTER SWITCH;
                                          default ON (fail-closed no-op
                                          where basin_map.json has no
                                          coverage); "0"/"false"/"no"/"off"
                                          disables
  severe_weather_basin_<key>              any other basin.DEFAULTS numeric
                                          override (thresholds, celerity,
                                          max_points - see basin.py)
  severe_weather_sites_enabled            vulnerable-site MASTER SWITCH
                                          (sites.py); default ON ("0"/
                                          "false"/"no"/"off" disables)
  severe_weather_forecast_detection       forecast-feed detection MASTER
                                          SWITCH (forecast.py); default OFF -
                                          only an explicit truthy value
                                          enables (fail-closed; the
                                          reanalysis-tuned detector is not
                                          yet validated on forecast data)
  severe_weather_forecast_horizon_hours   forward horizon, default 72
  severe_weather_forecast_url             forecast source base URL (default
                                          the public Open-Meteo forecast API)
  severe_weather_forecast_api_key         optional commercial key
  severe_weather_forecast_model           optional models= override
                                          (default best_match)
"""
from __future__ import annotations

import datetime as dt
import json

import frappe
from frappe.utils import cint, get_datetime

from ...warnings_engine import messages, push
from . import detector, fusion
from ...warnings_engine.admin_log import (
    TITLE_DETECTOR_CONFIG,
    TITLE_EVALUATION,
    TITLE_SOURCE_FETCH,
    log_admin_error,
)

WATCH_DOCTYPE = "Weather Watch Location"
WARNING_DOCTYPE = "Severe Weather Warning"

#: hours of hourly history per evaluation - the research window (14 d before
#: + 3 d after = 408 h): long enough for the 168 h TCWV baseline, the 72 h
#: accumulations and the causal soil-moisture percentile to be well defined.
WINDOW_HOURS = 408

#: a watch location nobody requested for this long is skipped, and
#: deactivated by the daily sweep.
STALE_DAYS = 30

#: how long past the data horizon an active episode stays a live heads-up.
VALIDITY_HOURS = {
    "flash_flood": 24,
    "flood": 48,
    "destructive_wind": 24,
    "tornado": 12,
}

LAST_ERROR_MAXLEN = 500


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


def severity_for_tier(event_class: str, tier: int):
    """Map a detector tier to the client-facing severity enum (or None).

    Detector tiers: 0 none, 1 watch, 2 warning, 3 severe. Only warning+
    episodes surface at all; "warning" tier -> "heads_up", "severe" tier ->
    "warning", further capped per class (tornado never exceeds heads_up).
    """
    if tier < detector.WARNING_TIER:
        return None
    word = "warning" if tier >= 3 else "heads_up"
    return messages.cap_severity(event_class, word)


def validity_end(event_class: str, horizon: dt.datetime) -> dt.datetime:
    return horizon + dt.timedelta(hours=VALIDITY_HOURS.get(event_class, 24))


# --------------------------------------------------------------------------- #
# scheduled entry points
# --------------------------------------------------------------------------- #

def evaluate_watch_locations():
    """Scheduled (hourly): evaluate every active, recently-requested watch
    location against the data source's current horizon."""
    try:
        rules = detector.load_rules()
    except Exception:
        log_admin_error(TITLE_DETECTOR_CONFIG)
        return

    from .sources.base import get_data_source

    try:
        source = get_data_source()
        horizon = source.data_horizon_utc()
    except Exception:
        log_admin_error(TITLE_SOURCE_FETCH)
        return

    now = _utcnow()

    # sw6 vulnerable sites (sites.py): keep every enabled registered site's
    # grid cell a registered, fresh watch location BEFORE the loop below
    # reads the registry, so admin-registered assets are covered even when
    # no client ever queries their cell. Guaranteed not to raise; exact
    # no-op without sites (fail-closed).
    from .sites import ensure_sites_covered
    try:
        ensure_sites_covered(now)
    except Exception:
        log_admin_error(TITLE_EVALUATION)

    stale_before = now - dt.timedelta(days=STALE_DAYS)
    locations = frappe.get_all(
        WATCH_DOCTYPE,
        filters={"active": 1},
        fields=["name", "latitude", "longitude", "label",
                "last_requested_at", "last_evaluated_horizon",
                "consecutive_failures"],
    )
    for loc in locations:
        last_requested = get_datetime(loc.last_requested_at) if loc.last_requested_at else None
        if last_requested and last_requested < stale_before:
            continue  # stale: skipped now, deactivated by the daily sweep
        last_horizon = (get_datetime(loc.last_evaluated_horizon)
                        if loc.last_evaluated_horizon else None)
        if last_horizon and last_horizon >= horizon:
            continue  # freshness short-circuit: source data has not advanced
        try:
            _evaluate_location(source, rules, loc, horizon, now)
            frappe.db.set_value(WATCH_DOCTYPE, loc.name, {
                "last_evaluated_at": now,
                "last_evaluated_horizon": horizon,
                "last_error": None,
                "consecutive_failures": 0,
            })
        except Exception as exc:
            log_admin_error(TITLE_EVALUATION)
            try:
                frappe.db.set_value(WATCH_DOCTYPE, loc.name, {
                    "last_error": str(exc)[:LAST_ERROR_MAXLEN],
                    "consecutive_failures": cint(loc.consecutive_failures) + 1,
                })
            except Exception:
                pass

    # sw2 propagation pass (propagation.py): neighbor advisories + basin
    # consensus over the state the loop above just wrote. No-op unless
    # weather_propagation_enabled is set; isolates its own per-record errors.
    from .propagation import run_propagation_pass
    try:
        run_propagation_pass(now)
    except Exception:
        log_admin_error(TITLE_EVALUATION)


def sweep_expired_warnings():
    """Scheduled (daily): expire lapsed warnings; deactivate stale watch
    locations (no client request in STALE_DAYS)."""
    now = _utcnow()
    try:
        lapsed = frappe.get_all(
            WARNING_DOCTYPE,
            filters={"status": "active", "valid_until": ["<", now]},
            fields=["name"],
        )
        for row in lapsed:
            frappe.db.set_value(WARNING_DOCTYPE, row.name, {"status": "expired"})

        stale_before = now - dt.timedelta(days=STALE_DAYS)
        stale = frappe.get_all(
            WATCH_DOCTYPE,
            filters={"active": 1, "last_requested_at": ["<", stale_before]},
            fields=["name"],
        )
        for row in stale:
            frappe.db.set_value(WATCH_DOCTYPE, row.name, {"active": 0})
    except Exception:
        log_admin_error(TITLE_EVALUATION)


# --------------------------------------------------------------------------- #
# per-location evaluation
# --------------------------------------------------------------------------- #

def _evaluate_location(source, rules, loc, horizon, now):
    from . import climatology, features

    start = horizon - dt.timedelta(hours=WINDOW_HOURS)
    series = source.hourly_series(
        loc.latitude, loc.longitude, list(features.POINT_VARIABLES), start, horizon)
    nbr = source.neighborhood_precipitation(loc.latitude, loc.longitude, start, horizon)
    feats = features.compute_features(series, nbr)
    # sw2 propagation: stash the steering direction from the already-fetched
    # wind series so the post-loop propagation pass can be direction-aware
    # without fetching anything (None -> conservative isotropic fallback).
    steering_deg = _steering_deg(series)
    times = [start + dt.timedelta(hours=i) for i in range(WINDOW_HOURS)]
    results = detector.run_all(times, feats, rules)
    # Optional seasonal-climatology context (config-flagged, default ON).
    # STRICTLY additive: computed AFTER the frozen detector has run, never an
    # input to it - it can only enrich precursors/copy of episodes that
    # already fired. None on any failure (rate-limited admin log inside).
    seasonal = climatology.seasonal_context(source, loc, series, horizon)
    for event_class, result in results.items():
        _upsert_warning(loc, event_class, result, source, horizon, now,
                        seasonal, steering_deg)

    # sw2.1 cold-front pass (cold_front.py): informational "cool change"
    # advisory detected from the SAME already-fetched series - strictly
    # additive (never touches the frozen detector classes above), hard-capped
    # at the advisory tier, never pushed, and guaranteed not to raise.
    from . import cold_front
    cold_front.evaluate_cell(loc, series, times, horizon, now, steering_deg)

    # sw5 basin-routing pass (basin.py): the upstream-flood signal - heavy
    # rain over the cell's upstream catchment (per the committed HydroBASINS
    # basin map) raising a distinct upstream_flood record days ahead of the
    # river's arrival, even when this cell sees no rain. Strictly additive
    # (its own event class, own record lifecycle), fail-closed when basin
    # data is absent, and guaranteed not to raise.
    from . import basin
    basin.evaluate_cell(source, loc, horizon, now)


#: hours of recent wind averaged into the stored steering direction.
STEERING_HOURS = 6


def _steering_deg(series):
    """Mean recent wind direction (deg clockwise from N, blowing toward),
    from the series the evaluator already fetched. None on any problem -
    the propagation pass then falls back to its conservative isotropic
    reduced radius."""
    try:
        import math

        def _mean_tail(name):
            vals = [v for v in list(series[name])[-STEERING_HOURS:]
                    if v is not None and not math.isnan(v)]
            if len(vals) < 3:
                raise ValueError("too few wind samples")
            return sum(vals) / len(vals)

        u = (_mean_tail("wind_u_component_10m")
             + _mean_tail("wind_u_component_100m")) / 2.0
        v = (_mean_tail("wind_v_component_10m")
             + _mean_tail("wind_v_component_100m")) / 2.0
        from .propagation import steering_deg_from_uv
        return round(steering_deg_from_uv(u, v), 1)
    except Exception:
        return None


def _upsert_warning(loc, event_class, result, source, horizon, now,
                    seasonal=None, steering_deg=None):
    """Idempotent per-(location, class) upsert of the active warning record.

    Advisory records are excluded from the lookup: their lifecycle (refresh,
    outranking expiry) is owned entirely by the propagation pass plus the
    daily sweep - the evaluator neither refreshes nor expires them.
    """
    existing = frappe.db.get_value(
        WARNING_DOCTYPE,
        {"watch_location": loc.name, "event_class": event_class,
         "status": "active", "severity": ["!=", "advisory"],
         # drill fence: replay records (warnings_engine/drill.py) are never
         # the live record - updating one would tag real weather as a drill
         "is_drill": ["!=", 1]},
        "name",
    )
    final_tier = result.tier[-1] if result.tier else 0
    severity = severity_for_tier(event_class, final_tier)

    if severity is None:
        # No live episode: an existing active record is over, mark it expired.
        if existing:
            frappe.db.set_value(WARNING_DOCTYPE, existing, {"status": "expired"})
        return

    valid_until = validity_end(event_class, horizon)
    if valid_until <= now:
        # The source data is too old for this episode to be a live heads-up.
        # Users see nothing; the episode stays an admin-side matter.
        if existing:
            frappe.db.set_value(WARNING_DOCTYPE, existing, {"status": "expired"})
        return

    episode = result.alarms[-1]  # still-open episode (ends at the series end)
    # --- sw2 SEASONAL ANNOTATION (climatology.py): bounded, additive
    # context computed from the frozen detector's own inputs - records the
    # snapshot + a bounded confidence annotation (rain classes only) and MAY
    # yield one calm extra sentence. Never creates or re-tiers an episode.
    seasonal_extras = {}
    seasonal_sentence = None
    if seasonal is not None:
        from . import climatology
        seasonal_extras["seasonal"] = seasonal
        if event_class in climatology.RAIN_CLASSES:
            seasonal_extras["confidence_seasonal_boosted"] = (
                climatology.bounded_confidence_boost(
                    result.confidence[-1], seasonal))
            seasonal_sentence = climatology.seasonal_note(seasonal)
    # --- sw2 FUSION HOOK (fusion.py): forecast timing + bounded severity
    # adjustment. Behind site-config flag (default ON); never raises for
    # fusion-specific reasons; never suppresses or downgrades the episode.
    severity, rendered, fusion_meta = fusion.fuse_warning(
        loc, event_class, severity, result.confidence[-1], now)
    # --- end fusion hook ---------------------------------------------------
    # Combined-copy rule: fusion's own copy (timing/softening, at most one
    # extra message sentence) comes first, then the seasonal sentence - at
    # most TWO appended sentences ever leave the evaluator. The endpoint-side
    # official-alert relay (official_alerts.py) appends its cross-reference
    # only when fewer than two are present (priority fusion > seasonal >
    # relay), so the combined message never carries more than two extras.
    message = rendered["message"]
    if seasonal_sentence:
        message = f"{message} {seasonal_sentence}"
    precursor_data = {
        "fired_conditions": list(episode.fired_conditions),
        "confidence": round(result.confidence[-1], 3),
        "max_confidence": round(episode.max_confidence, 3),
        "detector_tier": final_tier,
        "first_fired_at": episode.first_fired_at.isoformat(),
        "data_horizon": horizon.isoformat(),
        "source": source.name,
        "config_sha256": detector.CONFIG_SHA256,
        # sw2 fusion hook: admin-side trace of any forecast fusion applied
        "fusion": fusion_meta,
        # sw2 propagation: recent mean wind direction (deg clockwise from N,
        # blowing toward) for direction-aware neighbor advisories
        "steering_deg": steering_deg,
    }
    # sw2 seasonal annotation: snapshot + bounded confidence annotation (the
    # tier above and the raw confidence stay the frozen detector's own).
    precursor_data.update(seasonal_extras)
    precursors = json.dumps(precursor_data)
    fields = {
        "severity": rendered["severity"],
        "headline": rendered["headline"],
        "message": message,
        "onset": episode.first_fired_at,
        "valid_until": valid_until,
        "precursors": precursors,
        # queryable admin-view duplicates of the precursors JSON, so the
        # desk list view / report builder can show and filter them
        "detector_tier": final_tier,
        "confidence": round(result.confidence[-1], 3),
        "status": "active",
    }
    if existing:
        frappe.db.set_value(WARNING_DOCTYPE, existing, fields)
        warning_name = existing
    else:
        doc = {
            "doctype": WARNING_DOCTYPE,
            "watch_location": loc.name,
            "event_class": event_class,
            "issued_at": now,
        }
        doc.update(fields)
        warning_name = frappe.get_doc(doc).insert(ignore_permissions=True).name

    # Push notification for a new episode or a severity escalation - never
    # for a plain refresh. Master switch severe_weather_push_enabled is OFF
    # by default; notify_warning_upsert never raises (see push.py). The push
    # carries exactly the copy persisted above (fusion + seasonal included).
    push.notify_warning_upsert(warning_name, loc.name, event_class, {
        "severity": fields["severity"],
        "headline": fields["headline"],
        "message": fields["message"],
    })

    # sw6 vulnerable sites (sites.py): per-site notices for admin-registered
    # assets in this cell, attached to the warning record just upserted and
    # served alongside it. Fail-closed no-op when the cell has no enabled
    # sites; guaranteed not to raise.
    from .sites import sync_site_notices
    sync_site_notices(warning_name, loc.name, event_class,
                      fields["severity"], now)
