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

"""Pure-UTC trading-session model — frappe-free pure module.

Everything here is timestamp-in, verdict-out. No function reads a clock
inside its logic: callers pass a ``datetime`` (the engine passes one in),
and only the thin ``ts or _utc_now()`` default at each public entry point
touches the wall clock at all. That keeps every boundary case testable
with a literal timestamp.

THE BOUNDARIES, STATED EXACTLY (all UTC, all approximations):

    Sydney    22:00 - 07:00   (wraps midnight)
    Tokyo     00:00 - 09:00
    London    08:00 - 17:00
    New York  13:00 - 22:00

    Weekend   closed from Friday 22:00 to Sunday 22:00

Windows are half-open ``[open, close)``: the opening minute belongs to the
session, the closing minute does not. Friday 22:00 is therefore the first
closed instant of the weekend and Sunday 22:00 the first open instant of
the new week — matching the New York close and the Sydney open, so the
weekly calendar has no gap and no overlap at its seams.

DST IS DELIBERATELY IGNORED. These are fixed UTC windows, not the local
09:00-17:00 of each financial centre. Real session edges drift by an hour
twice a year (and the northern and southern hemispheres drift in opposite
directions); modelling that would mean carrying four tz databases to
sharpen numbers that are conventions to begin with — there is no bell that
rings when "the London session" starts. These windows are the common
textbook approximation, they are stable and reproducible, and the
MARKET_STATE.md doc says exactly this so nobody mistakes them for
broker-accurate timestamps.

The weekend closure is likewise an approximation: retail platforms close
between roughly 21:00 and 22:00 UTC on Friday and reopen between roughly
21:00 and 22:00 UTC on Sunday, varying by broker and by season. 22:00 was
chosen for both edges because it coincides with this model's New York
close and Sydney open.

Session activity and market closure are separate questions composed at
the end: ``active_sessions`` returns ``[]`` whenever the market is closed,
even though the raw Sydney window overlaps early Saturday.
"""

from datetime import datetime, timezone

#: Session open/close hours, UTC, half-open [open, close). A window whose
#: open hour is greater than its close hour wraps midnight (Sydney).
SESSION_WINDOWS_UTC = {
    "sydney": (22, 7),
    "tokyo": (0, 9),
    "london": (8, 17),
    "new_york": (13, 22),
}

#: The two overlap windows traders actually talk about. Sydney-Tokyo also
#: overlaps for hours, but nobody sizes a position around it; it is
#: readable from ``active`` anyway.
OVERLAP_PAIRS = (
    ("tokyo", "london"),
    ("london", "new_york"),
)

#: Weekend closure edges, UTC. Half-open like the sessions: Friday 22:00
#: is closed, Sunday 22:00 is open.
WEEKEND_CLOSE_UTC = (4, 22)  # (weekday, hour) — Friday 22:00
WEEKEND_OPEN_UTC = (6, 22)  # (weekday, hour) — Sunday 22:00


def _utc_now():
    """The only clock read in the module, and only ever as a default.

    Not ``frappe.utils.now`` — that returns SITE-LOCAL time, and feeding a
    site-local wall clock into fixed UTC windows would shift every
    boundary by the site's offset. This model is UTC-in, UTC-out.
    """
    return datetime.now(timezone.utc)


def as_utc(ts):
    """Coerce a datetime to an aware-UTC datetime.

    A naive datetime is TAKEN AS ALREADY UTC (never as local time — the
    module is pure and has no idea what "local" is). An aware one is
    converted. Anything else raises, because a session verdict computed
    from a garbled timestamp is worse than no verdict.
    """
    if not isinstance(ts, datetime):
        raise TypeError(
            "sessions expects a datetime, got {0!r}".format(type(ts).__name__)
        )
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def _in_window(hour, open_hour, close_hour):
    """Half-open [open, close) membership, handling midnight wrap."""
    if open_hour <= close_hour:
        return open_hour <= hour < close_hour
    return hour >= open_hour or hour < close_hour


def is_market_open(ts=None):
    """Whether the forex market is open at ``ts`` (default: now, UTC).

    Closed exactly on [Friday 22:00, Sunday 22:00) UTC; open the rest of
    the week — spot forex trades continuously through weekdays.
    """
    moment = as_utc(ts if ts is not None else _utc_now())
    weekday, hour = moment.weekday(), moment.hour
    close_day, close_hour = WEEKEND_CLOSE_UTC
    open_day, open_hour = WEEKEND_OPEN_UTC

    if weekday == close_day:
        return hour < close_hour
    if weekday == open_day:
        return hour >= open_hour
    if close_day < weekday < open_day:  # Saturday
        return False
    return True


def raw_active_sessions(ts=None):
    """Which session windows contain ``ts``, IGNORING weekend closure.

    Split out so the boundary arithmetic is testable on its own; almost
    every caller wants ``active_sessions`` instead.
    """
    moment = as_utc(ts if ts is not None else _utc_now())
    hour = moment.hour
    return [
        name
        for name, (open_hour, close_hour) in SESSION_WINDOWS_UTC.items()
        if _in_window(hour, open_hour, close_hour)
    ]


def active_sessions(ts=None):
    """Sessions active at ``ts``, honouring the weekend closure.

    Returns ``[]`` for any closed-market instant — the raw Sydney window
    covers early Saturday UTC, and reporting "Sydney is trading" while
    the market is shut would be exactly the kind of fabricated liveliness
    this SDK refuses elsewhere.
    """
    moment = as_utc(ts if ts is not None else _utc_now())
    if not is_market_open(moment):
        return []
    return raw_active_sessions(moment)


def session_overlaps(ts=None):
    """The named overlap flags at ``ts``, as ``{"tokyo_london": bool,
    "london_new_york": bool}``. All False whenever the market is closed."""
    active = set(active_sessions(ts))
    return {
        "{0}_{1}".format(first, second): first in active and second in active
        for first, second in OVERLAP_PAIRS
    }


def session_state(ts=None):
    """The whole session verdict for one instant, in one dict:
    ``{"ts", "market_open", "active", "overlaps"}`` with ``ts`` echoed
    back as an ISO-8601 UTC string so the caller can see exactly which
    instant was judged."""
    moment = as_utc(ts if ts is not None else _utc_now())
    return {
        "ts": moment.isoformat(),
        "market_open": is_market_open(moment),
        "active": active_sessions(moment),
        "overlaps": session_overlaps(moment),
    }
