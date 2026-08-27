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

"""TENANT-side human escalation ladder for unacknowledged top-severity
notices (sw6).

When a TOP-SEVERITY ("warning" tier - internal enum, never user-facing
wording) notice has been pushed to subscribers and NOBODY has acknowledged
it after the configured window, a human should hear about it. This hourly
job walks the admin-configured Weather Escalation Contact rows in priority
order, one rung per step interval, notifying each contact through every
channel that is actually composed and configured:

  push   contact has a linked User -> the comms push sender (the same
         guarded frappe.get_attr seam push.py uses);
  email  contact has an email -> "severe_weather_email_target" dotted path
         (default: the comms module's send_tenant_email, which falls back
         to the control-plane relay);
  sms    contact has a phone AND the SMS fallback channel is live (same
         resolver + gateway gate as sms_fallback.py);
  voice  documented pluggable seam ONLY: "severe_weather_voice_target"
         dotted path, no default - nothing in comms or the framework
         offers voice today. When configured, called as
         fn(phone=..., message=...).

Every step is recorded as a kind="escalation" Weather Notice Delivery row
carrying a single-use ack token; the notification carries an acknowledge
link (api/ack_weather_escalation) that acks the row and STOPS the ladder.
Any subscriber ack also stops it - the point is "someone saw it", not
"everyone was paged".

MASTER SWITCH (site config): "severe_weather_escalation_enabled" - default
ON, the flag is an off-switch. With no enabled contacts configured the job
is a SILENT no-op (not even a log line): merging costs nothing until an
admin builds a ladder. A contact none of whose channels could be reached
still consumes its rung (with one admin log line), so a broken rung can
never wedge the ladder. Copy goes through the messages layer
(render_escalation / escalation_sms_text) - calm phrasing, SAWS-safe.

Never raises. All datetimes are UTC (naive).
"""
from __future__ import annotations

import datetime as dt

import frappe

from ..warnings_engine import messages, push
from ..warnings_engine.admin_log import TITLE_ESCALATION, log_admin_error
from . import delivery, sms_fallback

CONTACT_DOCTYPE = "Weather Escalation Contact"

# ----- site config keys ---------------------------------------------------- #
#: MASTER SWITCH - default ON; set 0 to disable (the flag is an off-switch).
CONF_ENABLED = "severe_weather_escalation_enabled"
#: minutes a top-severity notice may stay unacknowledged before rung 1.
CONF_WINDOW_MINUTES = "severe_weather_escalation_minutes"
#: minutes between ladder rungs.
CONF_STEP_MINUTES = "severe_weather_escalation_step_minutes"
#: dotted path of the email sender: fn(recipients=[...], subject=, message=).
CONF_EMAIL_TARGET = "severe_weather_email_target"
#: dotted path of a voice-call sender: fn(phone=..., message=...). NO
#: default - voice is a pluggable seam, nothing offers it today.
CONF_VOICE_TARGET = "severe_weather_voice_target"
#: base URL for the acknowledge link (default: frappe.utils.get_url()).
CONF_ACK_BASE_URL = "severe_weather_ack_base_url"

#: composed path of the comms module's tenant email utility (local Email
#: Account first, control-plane relay second).
DEFAULT_EMAIL_TARGET = "{app_name}.comms.comms.tenant_utils.send_tenant_email"

DEFAULT_WINDOW_MINUTES = 60
DEFAULT_STEP_MINUTES = 30

#: only the top internal severity tier escalates to humans.
TOP_SEVERITY = "warning"

#: notices older than this age out of the scan entirely.
MAX_AGE_HOURS = 48

#: at most this many distinct warnings are escalated per run.
MAX_WARNINGS_PER_RUN = 50


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


# --------------------------------------------------------------------------- #
# config readers (guarded)
# --------------------------------------------------------------------------- #

def escalation_enabled() -> bool:
    try:
        from frappe.utils import cint
        raw = frappe.conf.get(CONF_ENABLED)
        if raw is None:
            return True  # default ON - the flag is an off-switch
        return bool(cint(raw))
    except Exception:
        return False


def _minutes(key, default) -> int:
    try:
        from frappe.utils import cint
        raw = frappe.conf.get(key)
        if raw is None:
            return default
        return max(cint(raw), 1)
    except Exception:
        return default


def window_minutes() -> int:
    return _minutes(CONF_WINDOW_MINUTES, DEFAULT_WINDOW_MINUTES)


def step_minutes() -> int:
    return _minutes(CONF_STEP_MINUTES, DEFAULT_STEP_MINUTES)


# --------------------------------------------------------------------------- #
# collaborators (each one guarded)
# --------------------------------------------------------------------------- #

def _contacts() -> list:
    """Enabled ladder contacts in priority order; [] when the doctype is
    absent or nobody is configured (the silent-no-op case)."""
    try:
        return frappe.get_all(
            CONTACT_DOCTYPE,
            filters={"enabled": 1},
            fields=["name", "contact_name", "priority", "user", "email",
                    "phone", "watch_location"],
            order_by="priority asc, name asc",
            limit_page_length=0,
        )
    except Exception:
        return []


def _get(row, key):
    return row.get(key) if isinstance(row, dict) else getattr(row, key, None)


def _scope_ok(contact, cell) -> bool:
    scope = (_get(contact, "watch_location") or "").strip()
    return not scope or scope == cell


def _resolve_email_sender():
    """The comms email utility via guarded frappe.get_attr; None = email
    channel absent on this shell."""
    try:
        path = ((frappe.conf.get(CONF_EMAIL_TARGET) or "").strip()
                or DEFAULT_EMAIL_TARGET)
    except Exception:
        path = DEFAULT_EMAIL_TARGET
    try:
        sender = frappe.get_attr(path)
        if not callable(sender):
            raise TypeError(f"email target is not callable: {path}")
        return sender
    except Exception:
        return None  # comms absent: the other channels still run


def _resolve_voice_sender():
    """The voice seam: resolved ONLY when explicitly configured."""
    try:
        path = (frappe.conf.get(CONF_VOICE_TARGET) or "").strip()
    except Exception:
        path = ""
    if not path:
        return None  # seam not plugged: silent skip, not an error
    try:
        sender = frappe.get_attr(path)
        if not callable(sender):
            raise TypeError(f"voice target is not callable: {path}")
        return sender
    except Exception:
        log_admin_error(TITLE_ESCALATION,
                        f"voice target not resolvable: {path}")
        return None


def _new_token() -> str:
    try:
        import secrets
        return secrets.token_urlsafe(24)
    except Exception:
        import uuid
        return uuid.uuid4().hex


def _ack_url(token):
    """Absolute acknowledge link, or None when no base URL is derivable
    (channels still notify; the copy simply omits the link)."""
    base = ""
    try:
        base = (frappe.conf.get(CONF_ACK_BASE_URL) or "").strip()
    except Exception:
        base = ""
    if not base:
        try:
            base = (frappe.utils.get_url() or "").strip()
        except Exception:
            base = ""
    if not base:
        return None
    app = __name__.split(".")[0]
    return (f"{base.rstrip('/')}/api/method/"
            f"{app}.tenant.api.ack_weather_escalation?token={token}")


def _active_warning(cell, warning_id):
    """The warning dict if it is still active at its cell, else None."""
    from .push_sync import _parse_cell
    from .api.get_weather_warnings.get_weather_warnings import (
        fetch_cell_warnings,
    )
    coords = _parse_cell(cell)
    if not coords:
        return None
    try:
        response = fetch_cell_warnings(*coords)
    except Exception:
        log_admin_error(TITLE_ESCALATION)
        return None
    for warning in (response or {}).get("warnings") or []:
        if str(warning.get("id") or "") == str(warning_id):
            # DRILL FENCE (fail-closed, mirrors push.py): the proxy fetch
            # above already excludes training-exercise records
            # (include_drills stays False), but a drill-flagged payload
            # must never page a human contact.
            if warning.get("is_drill"):
                return None
            return warning
    return None


# --------------------------------------------------------------------------- #
# entry point (scheduled hourly on tenant shells; never raises)
# --------------------------------------------------------------------------- #

def run_escalation():
    """Hourly scheduler entry (tenant persona). Never raises."""
    try:
        return _run()
    except Exception:
        log_admin_error(TITLE_ESCALATION)
        return {"status": "error"}


def _run(now: dt.datetime | None = None) -> dict:
    if not escalation_enabled():
        return {"status": "disabled"}
    contacts = _contacts()
    if not contacts:
        return {"status": "no_contacts"}  # silent no-op by design
    now = now or _utcnow()
    candidates = _unacked_top_warnings(now)
    notified = 0
    for cand in candidates:
        try:
            notified += _escalate(cand, contacts, now)
        except Exception:
            log_admin_error(TITLE_ESCALATION)
    return {"status": "ok", "warnings": len(candidates),
            "notified": notified}


def _unacked_top_warnings(now: dt.datetime) -> list:
    """Distinct top-severity warnings pushed >= window ago with NO ack from
    anyone (subscriber or contact), oldest push first."""
    floor = now - dt.timedelta(hours=MAX_AGE_HOURS)
    cutoff = now - dt.timedelta(minutes=window_minutes())
    if cutoff <= floor:
        return []
    try:
        rows = frappe.get_all(
            delivery.DELIVERY_DOCTYPE,
            filters={
                "kind": delivery.KIND_SUBSCRIBER,
                "severity": TOP_SEVERITY,
                "push_sent_at": ["between", [floor, cutoff]],
            },
            fields=["warning_id", "watch_location", "event_class",
                    "severity", "push_sent_at"],
            order_by="push_sent_at asc",
            limit_page_length=0,
        )
    except Exception:
        return []
    out, seen = [], set()
    for row in rows:
        wid = str(_get(row, "warning_id") or "").strip()
        if not wid or wid in seen:
            continue
        seen.add(wid)
        if delivery.warning_has_ack(wid):
            continue  # someone saw it - no humans need paging
        out.append(row)
        if len(out) >= MAX_WARNINGS_PER_RUN:
            break
    return out


def _escalate(cand, contacts, now: dt.datetime) -> int:
    """Advance one warning's ladder by at most one rung. Returns 1 when a
    contact was notified."""
    wid = str(_get(cand, "warning_id") or "").strip()
    cell = (_get(cand, "watch_location") or "").strip()

    steps = delivery.escalation_rows(wid)
    if any(_get(step, "acked_event") for step in steps):
        return 0  # a contact already acknowledged: ladder stopped
    if steps:
        last = max((s for s in steps), key=lambda s: _get(s, "notified_at")
                   or dt.datetime.min)
        last_at = _get(last, "notified_at")
        if last_at and now - last_at < dt.timedelta(minutes=step_minutes()):
            return 0  # pacing: one rung per step interval

    warning = _active_warning(cell, wid)
    if not warning:
        return 0  # expired: nobody gets paged for a dead notice

    already = {(_get(step, "contact") or "") for step in steps}
    contact = next(
        (c for c in contacts
         if _get(c, "name") not in already and _scope_ok(c, cell)), None)
    if contact is None:
        return 0  # ladder exhausted

    token = _new_token()
    channels = _notify_contact(contact, warning, token)
    if not channels:
        log_admin_error(TITLE_ESCALATION, (
            f"escalation contact {_get(contact, 'name')!r} unreachable on "
            "every channel - rung consumed, next contact is due after the "
            "step interval"))
    delivery.record_escalation(
        wid, cell, warning.get("event_class"), warning.get("severity"),
        contact=_get(contact, "name"), priority=_get(contact, "priority"),
        channels=",".join(channels), token=token, now=now)
    return 1


def _notify_contact(contact, warning, token) -> list:
    """Fire every configured channel for one contact; returns the channels
    that were actually handed a message."""
    headline = warning.get("headline") or ""
    body_copy = messages.render_escalation(headline,
                                           warning.get("message") or "",
                                           _ack_url(token))
    channels = []

    user = (_get(contact, "user") or "").strip()
    if user:
        sender = push._resolve_sender()
        if sender is not None:
            try:
                sender(user=user, title=body_copy["subject"],
                       body=body_copy["body"],
                       data={"type": "severe_weather_escalation",
                             "warning_id": str(warning.get("id") or "")})
                channels.append("push")
            except Exception:
                log_admin_error(TITLE_ESCALATION)

    email = (_get(contact, "email") or "").strip()
    if email:
        sender = _resolve_email_sender()
        if sender is not None:
            try:
                sender(recipients=[email], subject=body_copy["subject"],
                       message=body_copy["body"])
                channels.append("email")
            except Exception:
                log_admin_error(TITLE_ESCALATION)

    phone = (_get(contact, "phone") or "").strip()
    if phone:
        sender = sms_fallback._resolve_sms_sender()
        if sender is not None and sms_fallback._gateway_configured():
            try:
                sender(receivers=[phone],
                       msg=messages.escalation_sms_text(headline,
                                                        _ack_url(token)))
                channels.append("sms")
            except Exception:
                log_admin_error(TITLE_ESCALATION)
        voice = _resolve_voice_sender()
        if voice is not None:
            try:
                voice(phone=phone, message=body_copy["body"])
                channels.append("voice")
            except Exception:
                log_admin_error(TITLE_ESCALATION)
    return channels
