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

"""Push notifications for severe-weather heads-ups, via the comms module.

MASTER SWITCH (site config):  "severe_weather_push_enabled"
DEFAULT: ON (product go-ahead).  The flag remains the OFF-switch: an admin
sets ``"severe_weather_push_enabled": 0`` in site_config.json to disable
pushes on a site; an absent key means enabled.

The evaluator calls :func:`notify_warning_upsert` every time it upserts an
ACTIVE Severe Weather Warning record.  This module decides whether that
upsert is push-worthy and, when it is, fans a push out to the users
subscribed to the watch location (Weather Watch Subscriber rows, written by
the get_weather_warnings endpoint).

When a push happens (all of these must hold):
  - the master switch is on;
  - the record's rendered severity outranks what was already pushed for this
    episode (``last_push_severity`` on the record): a brand-new episode
    pushes once, a refresh of the same episode never pushes again, and a
    tier ESCALATION (heads_up -> warning severity) pushes again immediately
    (escalations bypass the cooldown);
  - for a NEW episode only: no push for the same (location, event class)
    went out within the cooldown window ("severe_weather_push_cooldown_hours",
    default 12) - this stops expire/re-detect flapping from spamming;
  - the current UTC hour is outside the optional quiet-hours window
    ("severe_weather_push_quiet_hours", e.g. "21-06").  A push suppressed by
    quiet hours records nothing, so it is retried (and sent) on the next
    evaluator pass outside the window.

Delivery goes through the comms module's whitelisted sender
(``send_push_notification(user, title, body, data)``, comms module in
RokctAI/core, re-exported for the composed dotted path) resolved by
``frappe.get_attr`` on a config-overridable dotted path
("severe_weather_push_target").  The weather module composes into shells
WITHOUT comms: a missing/renamed target, an import error, or a send failure
is a silent no-op plus one rate-limited admin Error Log line - never an
exception into the evaluator, never anything user-visible.

Copy: title/body are exactly the calm strings from messages.py (headline +
message) - heads-up possibility phrasing only, never the word "warning".

All datetimes are UTC (naive), like the rest of the warnings engine.
"""
from __future__ import annotations

import datetime as dt

import frappe
from frappe.utils import cint

from . import messages
from .admin_log import TITLE_PUSH, log_admin_error

WARNING_DOCTYPE = "Severe Weather Warning"
SUBSCRIBER_DOCTYPE = "Weather Watch Subscriber"

# ----- site config keys ---------------------------------------------------- #
#: MASTER SWITCH - default ON; set 0 to disable (the flag is an off-switch).
CONF_ENABLED = "severe_weather_push_enabled"
#: dotted path of the sender callable; default = the composed comms module.
CONF_TARGET = "severe_weather_push_target"
#: no repeat push per (location, event class) within this many hours.
CONF_COOLDOWN_HOURS = "severe_weather_push_cooldown_hours"
#: optional UTC quiet window "HH-HH" (start inclusive, end exclusive),
#: e.g. "21-06"; empty/absent = no quiet hours.
CONF_QUIET_HOURS = "severe_weather_push_quiet_hours"

#: composed path of the comms module's FCM sender:
#: send_push_notification(user, title, body, data) (whitelisted; comms
#: manifest.json maps "{app_name}.api.notification.send_push_notification"
#: to exactly this target).  The {app_name} token is substituted by the
#: backend composer; in shells composed without the comms module the path
#: simply fails to resolve and pushes are a silent no-op.
DEFAULT_TARGET = "{app_name}.comms.tenant.api.notification.send_push_notification"

DEFAULT_COOLDOWN_HOURS = 12

#: subscribers who have not requested the location in this long are not
#: pushed to (mirrors the evaluator's STALE_DAYS).
SUBSCRIBER_FRESH_DAYS = 30

#: internal severity enum, ranked (index order of messages.SEVERITY_WORDS:
#: heads_up < warning).
_SEVERITY_RANK = {word: i + 1 for i, word in enumerate(messages.SEVERITY_WORDS)}


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


# --------------------------------------------------------------------------- #
# config readers (each one guarded: bad config means "feature off"/default)
# --------------------------------------------------------------------------- #

def push_enabled() -> bool:
    try:
        raw = frappe.conf.get(CONF_ENABLED)
        if raw is None:
            return True  # default ON - the flag is an off-switch
        return bool(cint(raw))
    except Exception:
        return False


def cooldown_hours() -> int:
    try:
        raw = frappe.conf.get(CONF_COOLDOWN_HOURS)
    except Exception:
        raw = None
    if raw is None:
        return DEFAULT_COOLDOWN_HOURS
    return max(cint(raw), 0)


def parse_quiet_hours(raw):
    """Parse "HH-HH" (or [start, end]) into (start_hour, end_hour) or None."""
    if raw in (None, ""):
        return None
    try:
        if isinstance(raw, (list, tuple)) and len(raw) == 2:
            start, end = raw
        else:
            parts = str(raw).split("-")
            if len(parts) != 2:
                return None
            start, end = parts
        start, end = int(str(start).strip()) % 24, int(str(end).strip()) % 24
    except (TypeError, ValueError):
        return None
    if start == end:
        return None  # degenerate window
    return start, end


def in_quiet_hours(now: dt.datetime | None = None) -> bool:
    try:
        window = parse_quiet_hours(frappe.conf.get(CONF_QUIET_HOURS))
    except Exception:
        window = None
    if not window:
        return False
    hour = (now or _utcnow()).hour
    start, end = window
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end  # window wraps midnight


# --------------------------------------------------------------------------- #
# collaborators
# --------------------------------------------------------------------------- #

def _resolve_sender():
    """frappe.get_attr the configured sender; None (plus one rate-limited
    admin log line) when the comms module is absent or the path is wrong."""
    try:
        path = (frappe.conf.get(CONF_TARGET) or "").strip() or DEFAULT_TARGET
    except Exception:
        path = DEFAULT_TARGET
    try:
        sender = frappe.get_attr(path)
        if not callable(sender):
            raise TypeError(f"push target is not callable: {path}")
        return sender
    except Exception:
        log_admin_error(
            TITLE_PUSH,
            f"push target not resolvable (comms module absent?): {path}")
        return None


def _subscribers(location_name: str, now: dt.datetime | None = None) -> list:
    """Distinct fresh subscriber users of a watch location.

    The subscriber registry is a TENANT-side doctype; on the control shell
    (which runs the engine but has no tenant users) the table simply does not
    exist and the guarded query below yields the empty list - a composition
    state, not an error.
    """
    cutoff = (now or _utcnow()) - dt.timedelta(days=SUBSCRIBER_FRESH_DAYS)
    try:
        rows = frappe.get_all(
            SUBSCRIBER_DOCTYPE,
            filters={"watch_location": location_name,
                     "last_requested_at": [">=", cutoff]},
            fields=["user"],
        )
    except Exception:
        return []  # registry absent (control shell): nobody to push to
    users = []
    for row in rows:
        user = ((row.get("user") if isinstance(row, dict)
                 else getattr(row, "user", None)) or "").strip()
        if user and user != "Guest" and user not in users:
            users.append(user)
    return users


def _in_cooldown(location_name: str, event_class: str, now: dt.datetime) -> bool:
    """True when any (location, class) record was pushed within the window."""
    hours = cooldown_hours()
    if hours <= 0:
        return False
    rows = frappe.get_all(
        WARNING_DOCTYPE,
        filters={"watch_location": location_name,
                 "event_class": event_class,
                 "last_pushed_at": [">=", now - dt.timedelta(hours=hours)]},
        fields=["name"],
        limit=1,
    )
    return bool(rows)


# --------------------------------------------------------------------------- #
# entry point (called by the evaluator; never raises)
# --------------------------------------------------------------------------- #

def notify_warning_upsert(warning_name, location_name, event_class, rendered):
    """Push-notify subscribers about an upserted ACTIVE warning record.

    rendered: the messages.render() dict already stored on the record
    (severity, headline, message).  Guaranteed never to raise - any internal
    problem is a rate-limited admin log line at most.
    """
    try:
        return _notify(warning_name, location_name, event_class, rendered)
    except Exception:
        log_admin_error(TITLE_PUSH)
        return "error"


def _notify(warning_name, location_name, event_class, rendered,
            now: dt.datetime | None = None) -> str:
    """The decision pipeline; returns a short reason string (for tests)."""
    if not push_enabled():
        return "disabled"

    severity = (rendered or {}).get("severity")
    rank = _SEVERITY_RANK.get(severity, 0)
    if not rank:
        return "no_severity"

    # DRILL FENCE (fail-closed): training-exercise records written by the
    # drill replay runner (control/warnings_engine/drill.py, is_drill=1) must
    # NEVER reach a real end user. The runner never calls this module, but
    # this belt-and-braces check holds even if some future caller forwards a
    # drill record here - and an unreadable flag counts as a drill.
    try:
        if cint(frappe.db.get_value(WARNING_DOCTYPE, warning_name,
                                    "is_drill") or 0):
            return "drill"
    except Exception:
        return "drill_check_failed"  # fail closed: no push without a verdict

    prev = None
    try:
        prev = frappe.db.get_value(WARNING_DOCTYPE, warning_name,
                                   "last_push_severity")
    except Exception:
        prev = None
    prev_rank = _SEVERITY_RANK.get(prev, 0) if prev else 0
    if rank <= prev_rank:
        return "already_notified"  # refresh (or de-escalation) - never repush

    now = now or _utcnow()
    if prev_rank == 0 and _in_cooldown(location_name, event_class, now):
        return "cooldown"  # new episode too soon after the last pushed one

    if in_quiet_hours(now):
        # Nothing recorded: the next evaluator pass outside the window
        # retries and sends (deferral, not a drop).
        return "quiet_hours"

    sender = _resolve_sender()
    if sender is None:
        return "no_sender"  # comms absent: silent no-op (rate-limited log)

    users = _subscribers(location_name, now)
    if not users:
        return "no_subscribers"

    data = {
        "type": "severe_weather",
        "event_class": event_class,
        "severity": severity,
        "watch_location": str(location_name),
        "warning_id": str(warning_name),
    }
    sent = 0
    for user in users:
        try:
            sender(user=user, title=rendered["headline"],
                   body=rendered["message"], data=data)
            sent += 1
        except Exception:
            log_admin_error(TITLE_PUSH)

    # Record the attempt even when individual sends failed: repeat spam is
    # worse than a lost transient - failures are in the admin log.
    try:
        frappe.db.set_value(WARNING_DOCTYPE, warning_name, {
            "last_push_severity": severity,
            "last_pushed_at": now,
        })
    except Exception:
        log_admin_error(TITLE_PUSH)
    return f"sent:{sent}"
