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

"""TENANT-side hourly push-sync: severe-weather pushes for local subscribers.

The warnings engine (and its Severe Weather Warning records) now lives on the
control site only; tenant users are reached by THIS job instead of by the
control-side evaluator. Every hour it walks the distinct grid cells this
tenant's fresh Weather Watch Subscriber rows point at, fetches each cell's
currently-active heads-ups through the tenant proxy's cache-through fetch
(api/get_weather_warnings/fetch_cell_warnings - largely served by the 10-min
response cache), and dispatches pushes through the shared decision helpers in
warnings_engine/push.py (common):

  - master switch push.push_enabled() ("severe_weather_push_enabled",
    default ON - the flag is an off-switch);
  - severity ranking: a brand-new episode pushes once, a refresh of the same
    episode never pushes again, a tier ESCALATION (heads_up -> warning)
    pushes again immediately (escalations bypass the cooldown);
  - per-(cell, class) cooldown push.cooldown_hours() for NEW episodes only;
  - quiet hours push.in_quiet_hours(): a suppressed push records nothing, so
    it is retried (and sent) on the next hourly pass outside the window;
  - delivery via push._resolve_sender() (the comms module's whitelisted
    sender) to push._subscribers(cell) - the fresh subscriber users.

Push state (which warning id was pushed at which severity, and when) lives in
frappe.cache() keyed per (cell, event class) with a 7-day TTL - the tenant
has no warning records to store last_push_severity/last_pushed_at on. A
premature cache eviction can at worst repeat one push after the fact; the
admin-facing failure surface is the usual rate-limited Error Log line.

Never raises; any internal problem is a rate-limited admin log line at most
(the evaluator's contract). All datetimes are UTC (naive).
"""
from __future__ import annotations

import datetime as dt

import frappe

from ..warnings_engine import push
from ..warnings_engine.admin_log import TITLE_PUSH, log_admin_error
from . import delivery

SUBSCRIBER_DOCTYPE = "Weather Watch Subscriber"

#: at most this many distinct grid cells are synced per hourly run.
MAX_CELLS_PER_RUN = 200

#: push-state cache entries outlive any episode + cooldown; eviction at worst
#: repeats one push.
STATE_TTL_SECONDS = 7 * 24 * 3600

_STATE_KEY_PREFIX = "sw_push_sync_"  # compliance-ignore: py-hardcoded-secret (cache-key name prefix, not a credential)


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


def run_push_sync():
    """Hourly scheduler entry (tenant persona). Never raises."""
    try:
        return _sync()
    except Exception:
        log_admin_error(TITLE_PUSH)
        return {"status": "error"}


def _sync(now: dt.datetime | None = None) -> dict:
    if not push.push_enabled():
        return {"status": "disabled"}
    now = now or _utcnow()
    cells = _subscribed_cells(now)
    sent = 0
    for cell in cells[:MAX_CELLS_PER_RUN]:
        try:
            sent += _sync_cell(cell, now)
        except Exception:
            log_admin_error(TITLE_PUSH)
    return {"status": "ok", "cells": len(cells), "sent": sent}


def _subscribed_cells(now: dt.datetime) -> list:
    """Distinct grid keys with at least one fresh subscriber."""
    cutoff = now - dt.timedelta(days=push.SUBSCRIBER_FRESH_DAYS)
    try:
        rows = frappe.get_all(
            SUBSCRIBER_DOCTYPE,
            filters={"last_requested_at": [">=", cutoff]},
            fields=["watch_location"],
        )
    except Exception:
        return []  # registry absent/unreadable: nothing to sync
    cells = []
    for row in rows:
        cell = ((row.get("watch_location") if isinstance(row, dict)
                 else getattr(row, "watch_location", None)) or "").strip()
        if cell and cell not in cells:
            cells.append(cell)
    return cells


def _parse_cell(cell: str):
    """Grid key "lat,lng" -> (lat, lng) floats, or None when malformed."""
    try:
        lat_s, lng_s = str(cell).split(",")
        lat, lng = float(lat_s), float(lng_s)
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            return None
        return lat, lng
    except (TypeError, ValueError):
        return None


def _sync_cell(cell: str, now: dt.datetime) -> int:
    coords = _parse_cell(cell)
    if not coords:
        return 0
    from .api.get_weather_warnings.get_weather_warnings import (
        fetch_cell_warnings,
    )
    response = fetch_cell_warnings(*coords)
    warnings = (response or {}).get("warnings") or []
    sent = 0
    for warning in warnings:
        if _consider(cell, warning, now).startswith("sent"):
            sent += 1
    return sent


def _state_key(cell: str, event_class: str) -> str:
    return f"{_STATE_KEY_PREFIX}{cell}_{event_class}"


def _get_state(cell: str, event_class: str):
    try:
        state = frappe.cache().get_value(_state_key(cell, event_class))
        return state if isinstance(state, dict) else None
    except Exception:
        return None


def _put_state(cell: str, event_class: str, state: dict) -> None:
    try:
        frappe.cache().set_value(_state_key(cell, event_class), state,
                                 expires_in_sec=STATE_TTL_SECONDS)
    except Exception:
        pass


def _consider(cell: str, warning: dict, now: dt.datetime) -> str:
    """Decide-and-dispatch for one active warning of one cell.

    Mirrors push._notify()'s pipeline with cache-backed state; returns a
    short reason string (for tests).
    """
    event_class = (warning or {}).get("event_class") or ""
    severity = (warning or {}).get("severity")
    rank = push._SEVERITY_RANK.get(severity, 0)
    if not rank or not event_class:
        return "no_severity"

    warning_id = str((warning or {}).get("id") or "")
    state = _get_state(cell, event_class)
    prev_rank = 0
    if state and state.get("warning_id") == warning_id:
        prev_rank = int(state.get("severity_rank") or 0)
    if rank <= prev_rank:
        return "already_notified"  # refresh (or de-escalation) - never repush

    if prev_rank == 0 and _in_cooldown(state, now):
        return "cooldown"  # new episode too soon after the last pushed one

    if push.in_quiet_hours(now):
        # Nothing recorded: the next hourly pass outside the window retries
        # and sends (deferral, not a drop).
        return "quiet_hours"

    sender = push._resolve_sender()
    if sender is None:
        return "no_sender"  # comms absent: silent no-op (rate-limited log)

    users = push._subscribers(cell, now)
    if not users:
        return "no_subscribers"

    data = {
        "type": "severe_weather",
        "event_class": event_class,
        "severity": severity,
        "watch_location": cell,
        "warning_id": warning_id,
    }
    sent = 0
    for user in users:
        try:
            sender(user=user, title=(warning.get("headline") or ""),
                   body=(warning.get("message") or ""), data=data)
            sent += 1
            # delivery-assurance ledger (sw6): one row per warning x user,
            # the substrate for acks, the SMS fallback window, and the
            # escalation ladder. Fully guarded inside - never raises, and a
            # shell without the doctype is a silent no-op.
            delivery.record_push_sent(warning_id, user, cell, event_class,
                                      severity, now)
        except Exception:
            log_admin_error(TITLE_PUSH)

    # Record the attempt even when individual sends failed: repeat spam is
    # worse than a lost transient - failures are in the admin log.
    _put_state(cell, event_class, {
        "warning_id": warning_id,
        "severity_rank": rank,
        "pushed_at": now.isoformat(),
    })
    return f"sent:{sent}"


def _in_cooldown(state, now: dt.datetime) -> bool:
    hours = push.cooldown_hours()
    if hours <= 0 or not state:
        return False
    try:
        pushed_at = dt.datetime.fromisoformat(str(state.get("pushed_at")))
    except (TypeError, ValueError):
        return False
    return now - pushed_at < dt.timedelta(hours=hours)
