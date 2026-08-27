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

"""Drill / replay mode (sw6) - a HUMAN-TRIGGERED training-exercise runner.

Replays a past window of archived observed data through the live severe-
weather pipeline so operators can rehearse against real historical episodes.
The replay reuses the engine's existing pieces rather than duplicating them:

  * data access: :class:`ReplaySource` wraps whichever WarningsDataSource
    the site is configured with (sources/base.get_data_source - the same S3
    archive or API the hourly evaluator reads) and clamps every read AND the
    reported data horizon to a moving HISTORICAL CURSOR, so the frozen
    pipeline sees the archive exactly as it would have at that moment;
  * evaluation: each replay step runs the untouched production path -
    features.compute_features -> detector.run_all (the frozen detector) ->
    evaluator.severity_for_tier / messages.render - one step per cursor
    advance, exactly like one hourly evaluator tick.

What a drill run writes: Severe Weather Warning records flagged is_drill=1
and tagged with a drill_run_id, upserted per (location, class, run) exactly
like the live evaluator's idempotent upsert. Drill records are visible to
admin surfaces (desk, the drill-inclusive API views) and NOWHERE else.

DRILL FENCE - a drill can never reach a real end user (fail-closed; each
point is enforced at the consumer, not here, so a bug in this module cannot
open a path):
  * push:            never called by this runner, and push._notify refuses
                     any record whose is_drill flag is set OR unreadable;
  * client API:      control get_weather_warnings excludes is_drill records
                     unless the caller explicitly asks (never cached then);
                     the tenant proxy inherits both behaviors;
  * outcome ledger:  outcomes.py excludes drill records from judgement and
                     from miss-coverage checks;
  * propagation:     drill records never seed advisories or consensus;
  * live evaluator:  its upsert lookups skip is_drill records, so a drill
                     can never be adopted as (or block) the live record;
  * CAP feed:        drill records appear only on explicit request, and
                     then with CAP status Exercise.

Lifecycle: drill records carry a REAL validity window of DRILL_TTL_HOURS
from the run (the historical window is preserved inside precursors), so the
existing daily sweep (evaluator.sweep_expired_warnings) expires them like
any lapsed record; api/clear_drill deletes them immediately by run id or
wholesale.

HONEST SCOPE / LIMITS (deliberate):
  * synchronous: run_drill_replay runs in the calling request. Each step per
    location costs one archive window fetch (a few hundred small ranged S3
    GETs, typically seconds); the caps below (MAX_LOCATIONS, MAX_SPAN_DAYS,
    MAX_STEPS) keep a worst-case run in the low minutes. Longer exercises =
    several smaller calls.
  * data availability: bounded by the configured source's archive - for the
    default openmeteo_s3 source that is ERA5 (1940 onward, trailing real
    time by ~2-7 days). The requested end is clamped to the source horizon;
    hours the archive cannot serve are NaN and simply never fire.
  * replayed surface: the frozen detector classes only (flash_flood, flood,
    destructive_wind, tornado). The additive passes (fusion, climatology,
    propagation, cold_front, basin) are NOT replayed - they either need
    forecast data that no longer exists for past dates or write additional
    record classes that would multiply the fence surface for little training
    value. Copy is the plain messages.render rendering.

All datetimes are UTC (naive), like the rest of the engine.
"""
from __future__ import annotations

import datetime as dt
import json

from ...warnings_engine.admin_log import TITLE_DRILL, log_admin_error

WARNING_DOCTYPE = "Severe Weather Warning"

#: real validity of a drill record - how long the exercise stays visible on
#: admin surfaces before the daily sweep expires it.
DRILL_TTL_HOURS = 24

#: replay pacing: hours of archive consumed per replay step ("speed"). One
#: step = one simulated hourly-evaluator tick at the step's cursor.
DEFAULT_STEP_HOURS = 24
MIN_STEP_HOURS = 1
MAX_STEP_HOURS = 168

#: run-size caps (see HONEST SCOPE above).
MAX_SPAN_DAYS = 31
MAX_LOCATIONS = 5
MAX_STEPS = 240


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


# --------------------------------------------------------------------------- #
# the historical-cursor source wrapper (pure; no frappe)
# --------------------------------------------------------------------------- #

class ReplaySource:
    """A WarningsDataSource view frozen at a historical cursor.

    Implements the exact sources/base.WarningsDataSource interface by
    delegating to a real source, with two clamps that make the wrapped
    archive look like the past: data_horizon_utc() reports the cursor (never
    beyond the real archive horizon), and every series read is truncated at
    the cursor so no data "from the future" can leak into a replayed
    evaluation.
    """

    def __init__(self, inner, cursor: dt.datetime):
        self.inner = inner
        self.real_horizon = inner.data_horizon_utc()
        self.cursor = min(cursor, self.real_horizon)

    @property
    def name(self) -> str:
        return f"drill:{self.inner.name}"

    def set_cursor(self, cursor: dt.datetime) -> None:
        self.cursor = min(cursor, self.real_horizon)

    def data_horizon_utc(self) -> dt.datetime:
        return self.cursor

    def hourly_series(self, latitude, longitude, variables, start_utc, end_utc):
        return self.inner.hourly_series(
            latitude, longitude, variables, start_utc,
            min(end_utc, self.cursor))

    def neighborhood_precipitation(self, latitude, longitude, start_utc, end_utc):
        return self.inner.neighborhood_precipitation(
            latitude, longitude, start_utc, min(end_utc, self.cursor))


def iter_cursors(start: dt.datetime, end: dt.datetime, step_hours: int):
    """The replay cursor schedule: start, start+step, ..., always including
    end (so the final state of the window is always evaluated). Pure."""
    step = dt.timedelta(hours=step_hours)
    cursor = start
    while cursor < end:
        yield cursor
        cursor = min(cursor + step, end)
    yield end


def clamp_window(start: dt.datetime, end: dt.datetime,
                 real_horizon: dt.datetime, step_hours) -> tuple:
    """Validate/clamp (start, end, step_hours); raises ValueError with a
    plain-language reason on an unusable window. Pure."""
    try:
        step_hours = int(step_hours or DEFAULT_STEP_HOURS)
    except (TypeError, ValueError):
        raise ValueError(f"speed must be a whole number of hours "
                         f"({MIN_STEP_HOURS}-{MAX_STEP_HOURS})")
    step_hours = min(max(step_hours, MIN_STEP_HOURS), MAX_STEP_HOURS)
    end = min(end, real_horizon)
    if end <= start:
        raise ValueError(
            "the requested window is empty after clamping to the archive "
            f"horizon ({real_horizon.isoformat()}) - the archive trails "
            "real time by a few days")
    if (end - start) > dt.timedelta(days=MAX_SPAN_DAYS):
        raise ValueError(f"window longer than {MAX_SPAN_DAYS} days - run "
                         "several smaller drills instead")
    steps = len(list(iter_cursors(start, end, step_hours)))
    if steps > MAX_STEPS:
        raise ValueError(f"{steps} replay steps exceed the {MAX_STEPS}-step "
                         "cap - use a larger speed or a shorter window")
    return start, end, step_hours


# --------------------------------------------------------------------------- #
# one replay step = one simulated evaluator tick (production pieces, reused)
# --------------------------------------------------------------------------- #

def detect_at_cursor(source, rules, loc, cursor: dt.datetime) -> dict:
    """Run the untouched production evaluation for one location at one
    historical cursor: the evaluator's own window arithmetic, feature port
    and frozen detector. Returns detector.run_all's {event_class: result}.

    Injectable seam: run_drill_replay takes detect_fn=... so offline tests
    can replace the numeric stack with fixtures; this default IS the
    production path.
    """
    from . import detector, features  # noqa: F401  (rules come from detector)
    from .evaluator import WINDOW_HOURS

    start = cursor - dt.timedelta(hours=WINDOW_HOURS)
    series = source.hourly_series(
        loc.latitude, loc.longitude, list(features.POINT_VARIABLES),
        start, cursor)
    nbr = source.neighborhood_precipitation(
        loc.latitude, loc.longitude, start, cursor)
    feats = features.compute_features(series, nbr)
    times = [start + dt.timedelta(hours=i) for i in range(WINDOW_HOURS)]
    from .detector import run_all
    return run_all(times, feats, rules)


# --------------------------------------------------------------------------- #
# frappe-side runner
# --------------------------------------------------------------------------- #

def run_drill_replay(locations, start: dt.datetime, end: dt.datetime,
                     step_hours=DEFAULT_STEP_HOURS, run_id: str | None = None,
                     now: dt.datetime | None = None, detect_fn=None) -> dict:
    """Replay [start, end] for the given watch-location rows; write drill
    records. Returns a summary dict; raises ValueError on an unusable
    window (the endpoint turns that into a plain-language refusal).

    locations: EXISTING Weather Watch Location rows (name, latitude,
    longitude, label) - the runner never creates watch locations, so a
    drill cannot enlarge the live evaluator's coverage as a side effect.
    """
    from . import detector
    from .sources.base import get_data_source

    now = now or _utcnow()
    run_id = run_id or f"drill-{now.strftime('%Y%m%d%H%M%S')}"
    locations = list(locations)[:MAX_LOCATIONS]

    rules = detector.load_rules()
    inner = get_data_source()
    source = ReplaySource(inner, end)
    start, end, step_hours = clamp_window(
        start, end, source.real_horizon, step_hours)

    detect = detect_fn or detect_at_cursor
    counters = {"created": 0, "updated": 0, "expired": 0}
    errors = 0
    steps = 0
    for cursor in iter_cursors(start, end, step_hours):
        source.set_cursor(cursor)
        steps += 1
        for loc in locations:
            try:
                results = detect(source, rules, loc, cursor)
                for event_class, result in results.items():
                    _upsert_drill_warning(loc, event_class, result, source,
                                          cursor, now, run_id, counters)
            except Exception:
                errors += 1
                log_admin_error(TITLE_DRILL)

    return {
        "run_id": run_id,
        "is_drill": 1,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "step_hours": step_hours,
        "steps": steps,
        "locations": [loc.name for loc in locations],
        "records": counters,
        "step_errors": errors,
        "archive_horizon": source.real_horizon.isoformat(),
        "expires_at": (now + dt.timedelta(hours=DRILL_TTL_HOURS)).isoformat(),
    }


def _upsert_drill_warning(loc, event_class, result, source, cursor, now,
                          run_id, counters) -> None:
    """The evaluator's idempotent per-(location, class) upsert, restricted
    to THIS run's drill records and stripped of every live side effect: no
    push, no fusion/climatology enrichment, no propagation seeding."""
    import frappe

    from ...warnings_engine import messages
    from .detector import CONFIG_SHA256
    from .evaluator import severity_for_tier, validity_end

    existing = frappe.db.get_value(
        WARNING_DOCTYPE,
        {"watch_location": loc.name, "event_class": event_class,
         "status": "active", "is_drill": 1, "drill_run_id": run_id},
        "name",
    )
    final_tier = result.tier[-1] if result.tier else 0
    severity = severity_for_tier(event_class, final_tier)
    if severity is None:
        if existing:
            frappe.db.set_value(WARNING_DOCTYPE, existing,
                                {"status": "expired"})
            counters["expired"] += 1
        return

    episode = result.alarms[-1]
    rendered = messages.render(event_class, severity,
                               getattr(loc, "label", None))
    precursors = json.dumps({
        "fired_conditions": list(episode.fired_conditions),
        "confidence": round(result.confidence[-1], 3),
        "max_confidence": round(episode.max_confidence, 3),
        "detector_tier": final_tier,
        "data_horizon": cursor.isoformat(),
        "source": source.name,
        "config_sha256": CONFIG_SHA256,
        "drill": {
            "run_id": run_id,
            "cursor": cursor.isoformat(),
            "historical_onset": episode.first_fired_at.isoformat(),
            "historical_valid_until":
                validity_end(event_class, cursor).isoformat(),
        },
    })
    fields = {
        "severity": rendered["severity"],
        "headline": rendered["headline"],
        "message": rendered["message"],
        "onset": episode.first_fired_at,
        # REAL validity = exercise TTL, so admin surfaces show the drill now
        # and the daily sweep retires it; the HISTORICAL window lives in the
        # precursors drill block above.
        "valid_until": now + dt.timedelta(hours=DRILL_TTL_HOURS),
        "precursors": precursors,
        "detector_tier": final_tier,
        "confidence": round(result.confidence[-1], 3),
        "status": "active",
        "is_drill": 1,
        "drill_run_id": run_id,
    }
    if existing:
        frappe.db.set_value(WARNING_DOCTYPE, existing, fields)
        counters["updated"] += 1
    else:
        doc = {
            "doctype": WARNING_DOCTYPE,
            "watch_location": loc.name,
            "event_class": event_class,
            "issued_at": now,
        }
        doc.update(fields)
        frappe.get_doc(doc).insert(ignore_permissions=True)
        counters["created"] += 1


def clear_drill_records(run_id: str | None = None) -> int:
    """Delete drill records - all of them, or one run's. Returns the count.
    Deletion is scoped by is_drill=1 at the query, so this can never touch
    a real record."""
    import frappe

    filters = {"is_drill": 1}
    if run_id:
        filters["drill_run_id"] = run_id
    rows = frappe.get_all(WARNING_DOCTYPE, filters=filters,
                          fields=["name"], limit_page_length=0)
    deleted = 0
    for row in rows:
        try:
            frappe.delete_doc(WARNING_DOCTYPE, row.name, force=1,
                              ignore_permissions=True)
            deleted += 1
        except Exception:
            log_admin_error(TITLE_DRILL)
    return deleted
