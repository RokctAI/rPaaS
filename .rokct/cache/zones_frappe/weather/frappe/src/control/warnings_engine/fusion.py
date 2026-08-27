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

"""Forecast fusion for severe-weather heads-ups (wave 2).

The observed-data detector (detector.py) issues heads-ups from precursor
build-up alone. This module fuses an ACTIVE episode with the forecast the
platform already has - the module's own ``get_weather`` control-plane proxy
(weatherapi.com-shaped payload, already cached tenant-side) - to:

  (a) sharpen timing in the end-user copy ("later today" / "tomorrow" /
      "on Thursday") from when forecast heavy rain / strong wind arrives;
  (b) apply a BOUNDED severity adjustment: active flood-class precursors plus
      a heavy forecast 24 h rain total may upgrade heads_up -> warning (one
      step, still clamped by messages.CLASS_MAX_SEVERITY). A dry forecast may
      soften the wording with an extra sentence but NEVER suppresses or
      downgrades an observed-data episode.

Hard rules (all load-bearing):
  - fusion is advisory-only on top of the frozen detector: it can never
    create an episode, never remove one, and never lower the severity the
    detector produced;
  - every fetch/parse problem degrades silently to the un-fused rendering
    (rate-limited admin log; end users never see fusion errors);
  - no external forecast API is ever called from here - only the module's
    own get_weather proxy path (its 600 s tenant cache is reused as-is);
  - all copy stays within messages.py's legal constraint: calm possibility
    phrasing, never the word "warning", no official level taxonomy. The
    appended sentences below are part of that reviewed copy surface;
  - day names are locale-safe (fixed English table, never strftime %A) and
    derived in the location's timezone (forecast payload ``location.tz_id``)
    when available, else UTC with "around <weekday>" phrasing;
  - tornado is deliberately untouched (soft capped line only, by product
    decision in messages.py).

Site-config flag: ``severe_weather_forecast_fusion`` (default ON; set 0 to
disable fusion entirely - the un-fused wave-1 behavior).
"""
from __future__ import annotations

import datetime as dt
import math

import frappe

from ...warnings_engine import messages
from ...warnings_engine.admin_log import log_admin_error

#: stable admin Error Log title for fusion problems (rate-limited).
TITLE_FUSION = "SevereWeather: forecast fusion failed"

# --------------------------------------------------------------------------- #
# FUSION RULES - the complete, reviewable rule surface. Every behavior of this
# module is parameterized here and only here.
# --------------------------------------------------------------------------- #

#: site-config flag (frappe.conf). Missing/None = ON. "0"/"false"/"off" = OFF.
SITE_CONFIG_FLAG = "severe_weather_forecast_fusion"

#: classes whose fusion signal is forecast rain.
RAIN_CLASSES = ("flash_flood", "flood")
#: classes whose fusion signal is forecast wind (timing only, no upgrade).
WIND_CLASSES = ("destructive_wind",)
#: tornado is deliberately absent: its surface is a single soft heads-up line.

#: how far ahead forecast hours are considered.
FORECAST_HORIZON_HOURS = 72

#: an hour with at least this much rain counts as "heavy rain arriving" for
#: timing sharpening (rain classes).
HEAVY_RAIN_HOUR_MM = 5.0

#: an hour with gusts at/above this counts as "strong wind arriving" for
#: timing sharpening (wind classes).
STRONG_WIND_GUST_KPH = 75.0

#: bounded upgrade rule (rain classes only): an ACTIVE heads_up episode whose
#: detector confidence is at least UPGRADE_MIN_CONFIDENCE, with a forecast
#: rolling-24 h rain total at/above UPGRADE_PRECIP_24H_MM inside the horizon,
#: is upgraded one step: heads_up -> warning (then clamped by the class cap).
#: Nothing is ever upgraded past "warning", from tier "none"/"watch", or for
#: wind/tornado classes.
UPGRADE_PRECIP_24H_MM = 50.0
UPGRADE_MIN_CONFIDENCE = 0.45

#: softening rule: when the forecast covers at least a full 24 h and its
#: maximum rolling-24 h rain total is below this, one calming sentence is
#: appended. Severity and surfacing are NEVER changed by a dry forecast.
SOFTEN_PRECIP_24H_MM = 2.0

#: minimum number of usable future forecast hours before any rain-total rule
#: (upgrade) may fire; below this the horizon is too short to trust.
MIN_FORECAST_HOURS = 6

#: unit sanity: values outside these bounds are discarded as corrupt.
MAX_SANE_HOUR_PRECIP_MM = 500.0   # world-record hourly rain is ~305 mm
MAX_SANE_GUST_KPH = 410.0         # strongest measured surface gust ~408 km/h

#: locale-safe weekday names (dt.weekday() order). Never strftime("%A").
WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday")

#: appended copy - part of the reviewed end-user surface (calm possibility
#: phrasing; never the word "warning"; no level taxonomy). {when} is a
#: timing phrase from _timing_phrase().
TIMING_HEADLINE_SUFFIX = {
    "rain": " - heavy rain forecast {when}",
    "wind": " - strong winds forecast {when}",
}
TIMING_MESSAGE_SUFFIX = {
    "rain": " The forecast shows the heaviest rain arriving {when}.",
    "wind": " The forecast shows the strongest winds arriving {when}.",
}
SOFTEN_MESSAGE_SUFFIX = (
    " The latest forecast shows little further rain, but conditions can "
    "change quickly - stay aware if you're near water."
)


# --------------------------------------------------------------------------- #
# public entry point (the evaluator's single hook)
# --------------------------------------------------------------------------- #

def fuse_warning(loc, event_class, severity, confidence, now_utc, fetch=None):
    """Fuse one ACTIVE episode with the location's forecast.

    loc:         watch-location row (attrs: label, latitude, longitude).
    event_class: detector event class.
    severity:    client-facing severity from the observed-data detector
                 ("heads_up" | "warning").
    confidence:  detector confidence (0..1) at the evaluation instant.
    now_utc:     naive UTC evaluation time.
    fetch:       optional injectable forecast fetcher (tests); defaults to
                 the module's own get_weather control-plane proxy.

    Returns (severity, rendered, meta):
      severity  possibly upgraded (never downgraded, never suppressed);
      rendered  messages.render() dict, possibly with timing/softening copy;
      meta      JSON-safe dict for the admin precursors blob, or None when
                fusion did not run / had nothing to add.

    Never raises for fusion-specific reasons: any fetch/parse failure returns
    the plain un-fused rendering after a rate-limited admin log. (A missing
    copy key in messages.render raises exactly as it does without fusion -
    that contract is unchanged.)
    """
    base = messages.render(event_class, severity, getattr(loc, "label", None))
    try:
        if not fusion_enabled():
            return severity, base, None
        if event_class in RAIN_CLASSES:
            kind = "rain"
        elif event_class in WIND_CLASSES:
            kind = "wind"
        else:
            return severity, base, None   # tornado & unknown: untouched

        payload = _forecast_payload(loc, fetch)
        if payload is None:
            return severity, base, None
        hours, tzname = _forecast_hours(payload, now_utc)
        if not hours:
            return severity, base, None   # forecast empty / too short: skip

        return _fuse(loc, event_class, kind, severity, confidence,
                     now_utc, hours, tzname)
    except Exception:
        log_admin_error(TITLE_FUSION)
        return severity, base, None


def fusion_enabled() -> bool:
    """Site-config flag, default ON."""
    try:
        value = frappe.conf.get(SITE_CONFIG_FLAG)
    except Exception:
        return True
    if value is None:
        return True
    return str(value).strip().lower() not in ("0", "false", "no", "off", "")


# --------------------------------------------------------------------------- #
# fusion core (pure given parsed hours - unit-testable offline)
# --------------------------------------------------------------------------- #

def _fuse(loc, event_class, kind, severity, confidence, now_utc, hours, tzname):
    first_heavy = _first_heavy_at(kind, hours)
    max24, span_hours = _max_rolling_24h_mm(hours)

    new_severity = severity
    if (kind == "rain"
            and severity == "heads_up"
            and float(confidence or 0.0) >= UPGRADE_MIN_CONFIDENCE
            and span_hours >= MIN_FORECAST_HOURS
            and max24 is not None
            and max24 >= UPGRADE_PRECIP_24H_MM):
        new_severity = messages.cap_severity(event_class, "warning")

    rendered = messages.render(event_class, new_severity,
                               getattr(loc, "label", None))
    meta = {
        "applied": True,
        "kind": kind,
        "tz": tzname,
        "forecast_span_h": span_hours,
        "max_24h_mm": None if max24 is None else round(max24, 1),
    }
    if new_severity != severity:
        meta["adjusted_from"] = severity

    softened = False
    if first_heavy is not None:
        when = _timing_phrase(first_heavy, now_utc, tzname)
        rendered["headline"] += TIMING_HEADLINE_SUFFIX[kind].format(when=when)
        rendered["message"] += TIMING_MESSAGE_SUFFIX[kind].format(when=when)
        meta["timing"] = when
        meta["first_heavy_at"] = first_heavy.isoformat() + "Z"
    elif (kind == "rain" and span_hours >= 24
            and max24 is not None and max24 < SOFTEN_PRECIP_24H_MM):
        # Dry forecast: soften wording only. NEVER suppress or downgrade.
        rendered["message"] += SOFTEN_MESSAGE_SUFFIX
        softened = True
    meta["softened"] = softened

    if new_severity == severity and "timing" not in meta and not softened:
        return severity, rendered, None   # nothing fused: keep admin blob lean
    return new_severity, rendered, meta


def _first_heavy_at(kind, hours):
    """UTC time of the first forecast hour crossing the class's signal bar."""
    for when, precip_mm, gust_kph in hours:
        if kind == "rain" and precip_mm is not None \
                and precip_mm >= HEAVY_RAIN_HOUR_MM:
            return when
        if kind == "wind" and gust_kph is not None \
                and gust_kph >= STRONG_WIND_GUST_KPH:
            return when
    return None


def _max_rolling_24h_mm(hours):
    """(max rolling-24 h rain sum or None, forecast span in whole hours).

    Sums use only sane values; with under 24 h of span the max is a lower
    bound (fine for the upgrade rule, which only needs "at least X"; the
    softening rule separately requires span >= 24 h before calling it dry).
    """
    if not hours:
        return None, 0
    span_hours = int((hours[-1][0] - hours[0][0]).total_seconds() // 3600) + 1
    best = None
    for i, (start, _p, _g) in enumerate(hours):
        end = start + dt.timedelta(hours=24)
        total = 0.0
        for when, precip_mm, _gust in hours[i:]:
            if when >= end:
                break
            if precip_mm is not None:
                total += precip_mm
        if best is None or total > best:
            best = total
    return best, span_hours


def _timing_phrase(when_utc, now_utc, tzname):
    """Locale-safe timing phrase in the location's local calendar.

    With a resolvable timezone: "later today" / "tomorrow" / "on <Weekday>".
    Without one (UTC approximation): always "around <Weekday>".
    """
    tz = _resolve_tz(tzname)
    if tz is not None:
        local_when = when_utc.replace(tzinfo=dt.timezone.utc).astimezone(tz)
        local_now = now_utc.replace(tzinfo=dt.timezone.utc).astimezone(tz)
        delta_days = (local_when.date() - local_now.date()).days
        if delta_days <= 0:
            return "later today"
        if delta_days == 1:
            return "tomorrow"
        return "on " + WEEKDAY_NAMES[local_when.weekday()]
    return "around " + WEEKDAY_NAMES[when_utc.weekday()]


def _resolve_tz(tzname):
    if not tzname:
        return None
    try:
        import zoneinfo
        return zoneinfo.ZoneInfo(tzname)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# forecast fetch + parse (weatherapi.com payload shape)
# --------------------------------------------------------------------------- #

def _forecast_payload(loc, fetch=None):
    """Fetch the location's forecast via the module's own get_weather proxy.

    The proxy call is by location string: the watch location's label when an
    admin set one, else "lat,lng" (a query form the upstream provider
    accepts). The proxy's own 600 s tenant cache is reused untouched; on any
    failure fusion is skipped after a rate-limited admin log.
    """
    query = (getattr(loc, "label", None) or "").strip()
    if not query:
        lat = getattr(loc, "latitude", None)
        lng = getattr(loc, "longitude", None)
        if lat is None or lng is None:
            return None
        query = f"{float(lat):.4f},{float(lng):.4f}"
    fetch = fetch or _fetch_forecast_via_proxy
    try:
        return _unwrap(fetch(query))
    except Exception:
        log_admin_error(TITLE_FUSION)
        return None


def _fetch_forecast_via_proxy(location_query):
    """Default fetcher: the module's own cached control-plane proxy.

    Imported lazily because get_weather.py carries compose-time tokens and
    is only importable on a composed shell; never called in offline tests
    (they inject a fixture fetcher).
    """
    from ...tenant.weather.get_weather.get_weather import get_weather
    return get_weather(location_query)


def _unwrap(payload):
    """Unwrap a possible {"message": {...}} Frappe response envelope."""
    if not isinstance(payload, dict):
        return None
    if "forecast" not in payload and isinstance(payload.get("message"), dict):
        payload = payload["message"]
    return payload if isinstance(payload, dict) else None


def _forecast_hours(payload, now_utc):
    """Parse forecast.forecastday[].hour[] -> sorted future (time, mm, gust).

    Returns ([(utc_naive_datetime, precip_mm|None, gust_kph|None), ...],
    tz_id|None). Only hours in (now, now + FORECAST_HORIZON_HOURS] are kept;
    values failing unit sanity become None. A forecast shorter than the
    horizon simply yields fewer hours.
    """
    forecast = (payload or {}).get("forecast") or {}
    days = forecast.get("forecastday") or []
    location = (payload or {}).get("location") or {}
    tzname = location.get("tz_id") or None
    tz = _resolve_tz(tzname)

    horizon_end = now_utc + dt.timedelta(hours=FORECAST_HORIZON_HOURS)
    out = []
    for day in days:
        for hour in (day or {}).get("hour") or []:
            when = _hour_time_utc(hour, tz)
            if when is None or when < now_utc or when > horizon_end:
                continue
            out.append((when,
                        _sane(hour.get("precip_mm"), 0.0, MAX_SANE_HOUR_PRECIP_MM),
                        _sane(hour.get("gust_kph", hour.get("wind_kph")),
                              0.0, MAX_SANE_GUST_KPH)))
    out.sort(key=lambda item: item[0])
    return out, tzname


def _hour_time_utc(hour, tz):
    """One forecast hour's timestamp as naive UTC (prefer time_epoch)."""
    epoch = hour.get("time_epoch")
    if epoch is not None:
        try:
            return dt.datetime.fromtimestamp(
                int(epoch), dt.timezone.utc).replace(tzinfo=None)
        except (ValueError, OSError, OverflowError, TypeError):
            return None
    raw = hour.get("time")
    if not raw:
        return None
    try:
        local = dt.datetime.strptime(str(raw), "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    if tz is not None:
        return local.replace(tzinfo=tz).astimezone(
            dt.timezone.utc).replace(tzinfo=None)
    return local   # no tz: treated as UTC (the "around <weekday>" mode)


def _sane(value, lo, hi):
    """Numeric within [lo, hi] or None (unit sanity)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or number < lo or number > hi:
        return None
    return number
