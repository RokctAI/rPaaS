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

"""TENANT-side SMS fallback for unacknowledged severe-weather pushes (sw6).

Push is best-effort: tokens go stale, phones sit in dead zones, apps get
uninstalled. This hourly job gives heads_up-or-stronger notices a second
leg: a subscriber whose push was recorded in the Weather Notice Delivery
ledger but who has NOT acknowledged it (no delivered/seen/opened event)
within the fallback window gets ONE SMS - send-once per (warning x
subscriber), stamped on the ledger row before anything else can race.

MASTER SWITCH (site config): "severe_weather_sms_fallback_enabled" -
default ON, the flag is an off-switch. The feature is nonetheless INERT by
default, because sending requires BOTH of:

  * a resolvable SMS sender callable ("severe_weather_sms_target" dotted
    path via guarded frappe.get_attr; the default is the framework's own
    SMS Settings sender - the core comms module exposes NO SMS channel
    today, so the framework seam is the only real one); the callable
    contract is fn(receivers=[phone], msg=text);
  * a configured gateway (SMS Settings.sms_gateway_url non-empty).

Missing either one is a guarded no-op with one rate-limited admin log line
- merging this costs nothing until an SMS gateway is actually configured.

Per candidate row the job re-fetches the cell's currently-active warnings
through the tenant proxy's cache-through fetch (one fetch per cell per
run): a notice that already expired sends nothing, and the SMS text is the
warning's own server-rendered calm copy (headline + message) trimmed to
SMS length by messages.sms_text - removal-only, so the SAWS copy rules
hold. Subscribers without a phone number on their User record are skipped.

Never raises; window math is exact regardless of scheduler cadence (a row
is due once push_sent_at is older than the window and stays due until it
ages out at MAX_AGE_HOURS or gets its send-once stamp). All datetimes are
UTC (naive).
"""
from __future__ import annotations

import datetime as dt

import frappe

from ..warnings_engine import messages
from ..warnings_engine.admin_log import TITLE_SMS, log_admin_error
from . import delivery

# ----- site config keys ---------------------------------------------------- #
#: MASTER SWITCH - default ON; set 0 to disable (the flag is an off-switch).
CONF_ENABLED = "severe_weather_sms_fallback_enabled"
#: minutes a push may stay unacknowledged before the SMS goes out.
CONF_WINDOW_MINUTES = "severe_weather_sms_fallback_minutes"
#: dotted path of the SMS sender callable: fn(receivers=[...], msg=...).
CONF_TARGET = "severe_weather_sms_target"

#: the framework's SMS Settings sender - the only SMS seam that exists
#: today (the comms module in RokctAI/core has push + email + a WhatsApp
#: commerce bot, but no SMS sender). Sites route through a different
#: provider by overriding CONF_TARGET with any callable taking
#: (receivers, msg).
DEFAULT_TARGET = "frappe.core.doctype.sms_settings.sms_settings.send_sms"

DEFAULT_WINDOW_MINUTES = 30

#: rows older than this age out of the candidate scan entirely - the
#: warning is long over either way, and the scan stays bounded.
MAX_AGE_HOURS = 48

#: cost/bill guard: at most this many SMS per hourly run.
MAX_SMS_PER_RUN = 200


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


# --------------------------------------------------------------------------- #
# config readers (guarded: bad config means "feature off"/default)
# --------------------------------------------------------------------------- #

def sms_fallback_enabled() -> bool:
    try:
        from frappe.utils import cint
        raw = frappe.conf.get(CONF_ENABLED)
        if raw is None:
            return True  # default ON - the flag is an off-switch
        return bool(cint(raw))
    except Exception:
        return False


def window_minutes() -> int:
    try:
        from frappe.utils import cint
        raw = frappe.conf.get(CONF_WINDOW_MINUTES)
        if raw is None:
            return DEFAULT_WINDOW_MINUTES
        return max(cint(raw), 1)
    except Exception:
        return DEFAULT_WINDOW_MINUTES


# --------------------------------------------------------------------------- #
# collaborators (each one guarded)
# --------------------------------------------------------------------------- #

def _resolve_sms_sender():
    """frappe.get_attr the configured SMS sender; None (plus one
    rate-limited admin log line) when no SMS channel is composed."""
    try:
        path = (frappe.conf.get(CONF_TARGET) or "").strip() or DEFAULT_TARGET
    except Exception:
        path = DEFAULT_TARGET
    try:
        sender = frappe.get_attr(path)
        if not callable(sender):
            raise TypeError(f"sms target is not callable: {path}")
        return sender
    except Exception:
        log_admin_error(
            TITLE_SMS,
            f"sms fallback inert: no sms sender at {path} - "
            "the comms module exposes no sms channel today")
        return None


def _gateway_configured() -> bool:
    """True when SMS Settings carries a gateway URL. Sites overriding
    CONF_TARGET with a custom provider may not use SMS Settings at all -
    they can set the gateway URL to any marker value, or we trust their
    target once this returns True."""
    try:
        url = frappe.db.get_single_value("SMS Settings", "sms_gateway_url")
        return bool((url or "").strip())
    except Exception:
        return False


def _user_phone(user):
    """The subscriber's phone (mobile first). None = cannot SMS them."""
    try:
        # compliance-ignore: obs-db-tracing (in-process ORM read inside the scheduled SMS-fallback run; no incoming request trace to propagate)
        row = frappe.db.get_value("User", user, ["mobile_no", "phone"],
                                  as_dict=True)
        if not row:
            return None
        phone = (row.mobile_no or row.phone or "").strip()
        return phone or None
    except Exception:
        return None


def _active_warnings_by_cell(cells) -> dict:
    """{cell: {warning_id: warning dict}} via the proxy's cache-through
    fetch - one fetch per distinct cell per run, largely cache-served."""
    from .push_sync import _parse_cell
    from .api.get_weather_warnings.get_weather_warnings import (
        fetch_cell_warnings,
    )
    out = {}
    for cell in cells:
        coords = _parse_cell(cell)
        if not coords:
            out[cell] = {}
            continue
        try:
            response = fetch_cell_warnings(*coords)
            warnings = (response or {}).get("warnings") or []
            out[cell] = {str(w.get("id") or ""): w for w in warnings}
        except Exception:
            log_admin_error(TITLE_SMS)
            out[cell] = {}
    return out


# --------------------------------------------------------------------------- #
# entry point (scheduled hourly on tenant shells; never raises)
# --------------------------------------------------------------------------- #

def run_sms_fallback():
    """Hourly scheduler entry (tenant persona). Never raises."""
    try:
        return _run()
    except Exception:
        log_admin_error(TITLE_SMS)
        return {"status": "error"}


def _run(now: dt.datetime | None = None) -> dict:
    if not sms_fallback_enabled():
        return {"status": "disabled"}

    now = now or _utcnow()
    rows = delivery.find_sms_candidates(now, window_minutes(),
                                        MAX_AGE_HOURS, MAX_SMS_PER_RUN)
    if not rows:
        return {"status": "ok", "candidates": 0, "sent": 0}

    # resolve the channel only when there is work: an idle tenant never
    # even logs the inert-channel line.
    sender = _resolve_sms_sender()
    if sender is None:
        return {"status": "no_channel", "candidates": len(rows), "sent": 0}
    if not _gateway_configured():
        log_admin_error(TITLE_SMS, "sms fallback inert: no sms gateway "
                                   "configured (SMS Settings)")
        return {"status": "no_gateway", "candidates": len(rows), "sent": 0}

    def _get(row, key):
        return row.get(key) if isinstance(row, dict) else getattr(row, key,
                                                                  None)

    cells = []
    for row in rows:
        cell = (_get(row, "watch_location") or "").strip()
        if cell and cell not in cells:
            cells.append(cell)
    active = _active_warnings_by_cell(cells)

    sent = 0
    for row in rows:
        cell = (_get(row, "watch_location") or "").strip()
        warning = active.get(cell, {}).get(str(_get(row, "warning_id")))
        if not warning:
            continue  # expired/replaced: never SMS about a dead notice
        # DRILL FENCE (fail-closed, mirrors push.py): the proxy fetch above
        # already excludes training-exercise records (include_drills stays
        # False), but if a drill-flagged payload ever reaches this loop it
        # must never cost anyone an SMS.
        if warning.get("is_drill"):
            continue
        if warning.get("severity") not in ("heads_up", "warning"):
            continue  # advisory tier never earns an SMS
        phone = _user_phone(_get(row, "user"))
        if not phone:
            continue
        text = messages.sms_text(warning.get("headline") or "",
                                 warning.get("message") or "")
        if not text:
            continue
        # send-once: stamp FIRST, so no failure mode can double-send.
        delivery.record_sms_sent(_get(row, "name"), now)
        try:
            sender(receivers=[phone], msg=text)
            sent += 1
        except Exception:
            log_admin_error(TITLE_SMS)
    return {"status": "ok", "candidates": len(rows), "sent": sent}
