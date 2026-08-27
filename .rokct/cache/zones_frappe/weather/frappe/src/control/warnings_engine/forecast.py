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

"""Forecast-feed detection pass - the SAME frozen detector, run forward (sw7).

The observed-basis evaluator can only be as current as its archive: the
default ERA5 source trails real time by ~2-7 days, so a signal it fires is
honest but can already be history (the Hawaii live test: Hurricane Lala was
detected correctly - five days after the fact - and TS Moke never entered
the archive at all). This pass closes that gap by walking the IDENTICAL
frozen conditions (detector_config.json, sha-verified - NO threshold is
changed, added, or relaxed here) over a timeline that extends into the
future: 408 h of trailing history plus the next `horizon_hours` of hourly
forecast, all from the Open-Meteo forecast API source
(sources/openmeteo_forecast.py), causally, exactly as the evaluator walks
observed data.

What a firing produces - and what it deliberately does NOT:

  * One "Severe Weather Forecast Signal" row per (location, class) with an
    open forecast-tier episode: basis "forecast", the predicted first
    warning-tier hour, lead hours, peak tier/confidence over the forecast
    window, model + source + frozen-config sha. ADMIN/TELEMETRY ONLY.
  * It NEVER creates, refreshes, upgrades, or expires a Severe Weather
    Warning record, never pushes, and never reaches any end-user surface.
    Observed-basis and forecast-basis signals live in different doctypes and
    can never mix in any statistic (the retraining report reads only the
    outcome ledger, which only judges observed-basis episodes).

Fire-and-verify ledger (the honesty mechanism - no accuracy is claimed until
it accumulates):

  * every fired signal stays recorded; a later forecast run that no longer
    shows the event refreshes the row but never deletes it;
  * verify_forecast_signals (daily) settles open signals once the OBSERVED
    configured source (sources.base.get_data_source() - ERA5 by default) has
    data past the predicted window, using the outcome ledger's own peak
    extraction and verdict thresholds (outcomes.py): "hit" when extremes
    materialized, "false_alarm" when nothing extreme followed. Data gaps are
    never judged - the row stays open and is retried;
  * the same daily pass files a "missed_event" row for every observed-basis
    warning-tier episode that NO forecast signal preceded - the third column
    of the hit / false-alarm / miss accounting, mirroring the retraining
    report's shape. Verification always runs while rows are pending (a fired
    claim is always settled), but new firings and miss accounting require
    the master switch - with the pass off, "we never predicted it" is a
    statement about configuration, not skill.

Safety properties (mirrors the evaluator's contract):
  * MASTER SWITCH severe_weather_forecast_detection, default OFF
    (fail-closed): forecast-basis detection is unvalidated until this ledger
    says otherwise - enabling it is a deliberate operator decision;
  * per-location error isolation, rate-limited admin logging under stable
    titles; run_forecast_pass / verify_forecast_signals never raise;
  * one forecast fetch per location per pass (point + one multi-location
    neighborhood call), at most once per hour (cache short-circuit).

Site-config flags (frappe.conf):
  severe_weather_forecast_detection      MASTER SWITCH, default OFF; only an
                                         explicit truthy value ("1"/"true"/
                                         "yes"/"on") enables
  severe_weather_forecast_horizon_hours  forward horizon, default 72
                                         (clamped 24..120)
  severe_weather_forecast_url / _api_key / _model   source config (see
                                         sources/openmeteo_forecast.py)

All datetimes are UTC (naive), matching the rest of the engine.
"""
from __future__ import annotations

import datetime as dt
import json

from . import detector, features, outcomes
from ...warnings_engine.admin_log import log_admin_error
from .evaluator import STALE_DAYS, VALIDITY_HOURS, WINDOW_HOURS

SIGNAL_DOCTYPE = "Severe Weather Forecast Signal"
WATCH_DOCTYPE = "Weather Watch Location"
WARNING_DOCTYPE = "Severe Weather Warning"

#: stable admin Error Log titles (rate-limited; live here like basin.py's).
TITLE_FORECAST_PASS = "SevereWeather: forecast pass failed"
TITLE_FORECAST_SIGNAL = "SevereWeather: forecast signal recorded"

#: MASTER SWITCH - default OFF (fail-closed; see module docstring).
CONFIG_FLAG = "severe_weather_forecast_detection"

#: forward horizon flag + bounds.
HORIZON_FLAG = "severe_weather_forecast_horizon_hours"
DEFAULT_HORIZON_HOURS = 72
MIN_HORIZON_HOURS = 24
MAX_HORIZON_HOURS = 120

#: evidence JSON schema version.
SCHEMA_VERSION = 1

#: basis tag carried by every row this module writes - the hard separator
#: between forecast-fired and observed-basis signals.
BASIS_FORECAST = "forecast"

STATUS_OPEN = "open"
STATUS_HIT = "hit"
STATUS_FALSE_ALARM = "false_alarm"
STATUS_MISSED_EVENT = "missed_event"

#: observed aftermath appended to a signal's predicted window before judging
#: (same settling margin as the outcome ledger's POST_EPISODE_HOURS).
VERIFY_POST_HOURS = 48

#: verification cost bounds per daily run (the rest catch up later).
SIGNALS_PER_RUN_CAP = 200
MISS_BACKFILL_DAYS = 30

#: a signal covers an observed episode when it was issued before the
#: episode's onset and predicted the first warning-tier hour within this
#: tolerance of the actual onset.
MISS_COVER_TOLERANCE_HOURS = 48

#: pass-wide once-per-hour short-circuit cache key.
RUN_CACHE_KEY = "sww_forecast_last_run_hour"  # compliance-ignore: py-hardcoded-secret (cache-key name, not a credential)


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)


def is_enabled() -> bool:
    """Master flag, default OFF - only an explicit truthy value enables.

    Fail-closed on any trouble reading config: forecast-basis detection is
    unvalidated (FUSION.md), so the safe state is off.
    """
    try:
        import frappe
        raw = frappe.conf.get(CONFIG_FLAG)
    except Exception:
        return False
    if raw is None:
        return False
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def horizon_hours() -> int:
    """Configured forward horizon, clamped to sane bounds."""
    try:
        import frappe
        raw = frappe.conf.get(HORIZON_FLAG)
        value = int(float(raw)) if raw is not None else DEFAULT_HORIZON_HOURS
    except Exception:
        value = DEFAULT_HORIZON_HOURS
    return min(max(value, MIN_HORIZON_HOURS), MAX_HORIZON_HOURS)


# --------------------------------------------------------------------------- #
# hourly firing pass
# --------------------------------------------------------------------------- #

def run_forecast_pass(source=None, now=None):
    """Scheduled (hourly): run the frozen detector over the forecast feed.

    source / now are injectable for offline tests only. Master-flagged
    (default OFF), hour-short-circuited, never raises.
    """
    try:
        if not is_enabled():
            return
        import frappe
        from frappe.utils import get_datetime

        rules = detector.load_rules()
        if source is None:
            from .sources.openmeteo_forecast import OpenMeteoForecastSource
            source = OpenMeteoForecastSource()
        now = now or _utcnow()

        # once per hour: the pass costs one forecast fetch per location.
        try:
            cached = frappe.cache().get_value(RUN_CACHE_KEY)
            if cached == now.isoformat():
                return
        except Exception:
            pass

        hours_ahead = horizon_hours()
        stale_before = now - dt.timedelta(days=STALE_DAYS)
        locations = frappe.get_all(
            WATCH_DOCTYPE,
            filters={"active": 1},
            fields=["name", "latitude", "longitude", "label",
                    "last_requested_at"],
        )
        for loc in locations:
            last_requested = (get_datetime(loc.last_requested_at)
                              if loc.last_requested_at else None)
            if last_requested and last_requested < stale_before:
                continue  # same staleness contract as the evaluator
            try:
                _evaluate_location(source, rules, loc, now, hours_ahead)
            except Exception:
                log_admin_error(TITLE_FORECAST_PASS)

        try:
            frappe.cache().set_value(RUN_CACHE_KEY, now.isoformat())
        except Exception:
            pass
    except Exception:
        log_admin_error(TITLE_FORECAST_PASS)


def _evaluate_location(source, rules, loc, now, hours_ahead):
    """One location: trailing window + forecast horizon, one causal walk."""
    start = now - dt.timedelta(hours=WINDOW_HOURS)
    end = now + dt.timedelta(hours=hours_ahead)
    series = source.hourly_series(
        loc.latitude, loc.longitude,
        list(features.POINT_VARIABLES), start, end)
    nbr = source.neighborhood_precipitation(
        loc.latitude, loc.longitude, start, end)
    feats = features.compute_features(series, nbr)
    n = WINDOW_HOURS + hours_ahead
    times = [start + dt.timedelta(hours=i) for i in range(n)]
    results = detector.run_all(times, feats, rules)
    for event_class, result in results.items():
        _record_signal(loc, event_class, result, source, now, hours_ahead)


def first_forecast_firing(result, future0: int):
    """(index, lead_hours) of the first warning-tier hour at/after `future0`
    (the index of "now" in the combined timeline), or None."""
    for i in range(future0, len(result.tier)):
        if result.tier[i] >= detector.WARNING_TIER:
            return i, i - future0
    return None


def _record_signal(loc, event_class, result, source, now, hours_ahead):
    """Insert-or-refresh the OPEN signal for (location, class).

    A fired signal is never deleted or downgraded by a later forecast run -
    the ledger keeps every claim until observed data settles it.
    """
    fired = first_forecast_firing(result, WINDOW_HOURS)
    if fired is None:
        return
    idx, lead_h = fired
    first_at = now + dt.timedelta(hours=lead_h)
    future_tiers = result.tier[WINDOW_HOURS:]
    future_confs = result.confidence[WINDOW_HOURS:]
    peak_tier = max(future_tiers)
    peak_conf = max(future_confs)
    already_active = (WINDOW_HOURS > 0
                      and result.tier[WINDOW_HOURS - 1] >= detector.WARNING_TIER)
    fired_conditions = ()
    for alarm in result.alarms:
        if alarm.first_fired_at <= first_at <= alarm.last_active_at:
            fired_conditions = alarm.fired_conditions
            break

    evidence = {
        "version": SCHEMA_VERSION,
        "basis": BASIS_FORECAST,
        "issued_at": now.isoformat(),
        "first_forecast_at": first_at.isoformat(),
        "lead_hours": lead_h,
        "horizon_hours": hours_ahead,
        "peak_tier": peak_tier,
        "peak_confidence": round(float(peak_conf), 3),
        "already_active_at_issue": bool(already_active),
        "fired_conditions": list(fired_conditions),
        "source": source.name,
        "model": getattr(source, "model", "") or "best_match",
        "config_sha256": detector.CONFIG_SHA256,
    }

    import frappe

    existing = frappe.db.get_value(
        SIGNAL_DOCTYPE,
        {"watch_location": loc.name, "event_class": event_class,
         "status": STATUS_OPEN},
        ["name", "peak_tier", "peak_confidence", "refresh_count"],
        as_dict=True,
    )
    if existing:
        frappe.db.set_value(SIGNAL_DOCTYPE, existing.name, {
            "refreshed_at": now,
            "refresh_count": int(existing.refresh_count or 0) + 1,
            "first_forecast_at": first_at,
            "lead_hours": lead_h,
            # peaks are high-water marks across refreshes - a weakening
            # forecast never quietly shrinks the original claim
            "peak_tier": max(peak_tier, int(existing.peak_tier or 0)),
            "peak_confidence": round(max(float(peak_conf),
                                         float(existing.peak_confidence or 0.0)), 3),
            "evidence": json.dumps(evidence),
        })
        return
    frappe.get_doc({
        "doctype": SIGNAL_DOCTYPE,
        "watch_location": loc.name,
        "event_class": event_class,
        "basis": BASIS_FORECAST,
        "status": STATUS_OPEN,
        "issued_at": now,
        "refreshed_at": now,
        "refresh_count": 0,
        "first_forecast_at": first_at,
        "lead_hours": lead_h,
        "horizon_hours": hours_ahead,
        "peak_tier": peak_tier,
        "peak_confidence": round(float(peak_conf), 3),
        "model": evidence["model"],
        "source": source.name,
        "config_sha256": detector.CONFIG_SHA256,
        "evidence": json.dumps(evidence),
    }).insert(ignore_permissions=True)
    log_admin_error(TITLE_FORECAST_SIGNAL, (
        f"forecast-basis {event_class} signal at {loc.name}: first "
        f"warning-tier hour {first_at.isoformat()} (+{lead_h} h), peak tier "
        f"{peak_tier}, confidence {round(float(peak_conf), 3)}. Admin-only; "
        "verified later against observed data."))


# --------------------------------------------------------------------------- #
# daily verification pass - the honest ledger
# --------------------------------------------------------------------------- #

def verify_forecast_signals(observed_source=None, now=None):
    """Scheduled (daily): settle open signals against OBSERVED data and file
    missed_event rows.

    Settling always runs while open rows exist (a fired claim is always
    verified, even after the operator turns the pass off); the miss scan
    requires the master switch (see module docstring). Never raises.
    """
    try:
        import frappe

        if observed_source is None:
            from .sources.base import get_data_source
            observed_source = get_data_source()
        horizon = observed_source.data_horizon_utc()
        now = now or _utcnow()

        open_signals = frappe.get_all(
            SIGNAL_DOCTYPE,
            filters={"status": STATUS_OPEN},
            fields=["name", "watch_location", "event_class", "issued_at",
                    "first_forecast_at"],
            order_by="issued_at asc",
            limit_page_length=SIGNALS_PER_RUN_CAP,
        )
        for sig in open_signals:
            try:
                _settle_signal(observed_source, sig, horizon, now)
            except Exception:
                log_admin_error(TITLE_FORECAST_PASS)

        if is_enabled():
            _scan_missed_events(now)
    except Exception:
        log_admin_error(TITLE_FORECAST_PASS)


def _settle_signal(observed_source, sig, horizon, now):
    """hit / false_alarm for one open signal, using the outcome ledger's own
    peak extraction and verdict thresholds (outcomes.py) - the forecast path
    is held to exactly the observed bar, no new thresholds."""
    import frappe
    from frappe.utils import get_datetime

    issued_at = get_datetime(sig.issued_at)
    predicted = get_datetime(sig.first_forecast_at)
    if not issued_at or not predicted:
        return
    validity = VALIDITY_HOURS.get(sig.event_class, 24)
    window_end = predicted + dt.timedelta(hours=validity + VERIFY_POST_HOURS)
    if horizon < window_end:
        return  # observed data has not caught up yet: stays open, retried

    coords = frappe.db.get_value(
        WATCH_DOCTYPE, sig.watch_location, ["latitude", "longitude"],
        as_dict=True)
    if not coords:
        return
    series = observed_source.hourly_series(
        coords.latitude, coords.longitude,
        list(outcomes.OUTCOME_VARIABLES), issued_at, window_end)
    peaks = outcomes.observed_peaks(series, issued_at)
    normals = outcomes._load_normals(sig.watch_location)
    pctl = outcomes.precip_weekly_pctl(peaks, normals)
    verdict = outcomes.episode_verdict(sig.event_class, peaks, pctl)
    if verdict is None:
        return  # data gap: never judged blind, retried on a later horizon

    hit = verdict == outcomes.VERDICT_VERIFIED
    verification = {
        "version": SCHEMA_VERSION,
        "window": {"start": issued_at.isoformat(),
                   "end": window_end.isoformat()},
        "observed": {
            "max_precip_24h_mm": peaks.get("max_precip_24h_mm"),
            "precip_weekly_pctl": pctl,
            "max_gust_ms": peaks.get("max_gust_ms"),
        },
        "verdict": verdict,
        "observed_source": getattr(observed_source, "name", "unknown"),
        "data_horizon": horizon.isoformat(),
        "verified_at": now.isoformat(),
    }
    frappe.db.set_value(SIGNAL_DOCTYPE, sig.name, {
        "status": STATUS_HIT if hit else STATUS_FALSE_ALARM,
        "verified_at": now,
        "verification": json.dumps(verification),
    })


def _scan_missed_events(now):
    """File one missed_event row per observed-basis warning-tier episode no
    forecast signal preceded - the ledger's miss column."""
    import frappe
    from frappe.utils import get_datetime

    floor = now - dt.timedelta(days=MISS_BACKFILL_DAYS)
    episodes = frappe.get_all(
        WARNING_DOCTYPE,
        filters={
            "event_class": ["in", list(outcomes.VERIFIABLE_CLASSES)],
            "severity": ["not in", list(outcomes.EXCLUDED_SEVERITIES)],
            "onset": ["between", [floor, now]],
        },
        fields=["name", "watch_location", "event_class", "onset", "is_drill"],
        order_by="onset desc",
        limit_page_length=SIGNALS_PER_RUN_CAP,
    )
    tol = dt.timedelta(hours=MISS_COVER_TOLERANCE_HOURS)
    for ep in episodes:
        if ep.is_drill:
            continue  # drill fence: replayed exercises are not real weather
        onset = get_datetime(ep.onset)
        if not onset:
            continue
        # already accounted for this episode?
        if frappe.get_all(
                SIGNAL_DOCTYPE,
                filters={"warning": ep.name, "status": STATUS_MISSED_EVENT},
                fields=["name"], limit_page_length=1):
            continue
        # covered by any signal issued before onset predicting near it?
        # (any status: a signal later judged false_alarm still predicted)
        covered = False
        for sig in frappe.get_all(
                SIGNAL_DOCTYPE,
                filters={"watch_location": ep.watch_location,
                         "event_class": ep.event_class,
                         "issued_at": ["<=", onset]},
                fields=["name", "first_forecast_at"]):
            predicted = get_datetime(sig.first_forecast_at)
            if predicted and abs(predicted - onset) <= tol:
                covered = True
                break
        if covered:
            continue
        frappe.get_doc({
            "doctype": SIGNAL_DOCTYPE,
            "watch_location": ep.watch_location,
            "event_class": ep.event_class,
            "basis": BASIS_FORECAST,
            "status": STATUS_MISSED_EVENT,
            "warning": ep.name,
            "issued_at": now,
            "verified_at": now,
            "config_sha256": detector.CONFIG_SHA256,
            "evidence": json.dumps({
                "version": SCHEMA_VERSION,
                "basis": BASIS_FORECAST,
                "kind": "missed_event",
                "warning": ep.name,
                "onset": onset.isoformat(),
                "cover_tolerance_hours": MISS_COVER_TOLERANCE_HOURS,
                "recorded_at": now.isoformat(),
            }),
        }).insert(ignore_permissions=True)
