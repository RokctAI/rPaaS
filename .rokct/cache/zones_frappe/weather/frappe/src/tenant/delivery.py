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

"""TENANT-side delivery/ack ledger for severe-weather notices (sw6).

One "Weather Notice Delivery" row per (warning id x recipient) records what
was sent when and what the recipient's device (or an escalation contact)
acknowledged. The ledger is the shared substrate of the whole
delivery-assurance chain:

  * the hourly push-sync job (push_sync.py) records push_sent_at for every
    push it successfully hands to the comms sender;
  * the client fires the whitelisted ack endpoint
    (api/ack_weather_notice) fire-and-forget on delivered/seen/opened, and
    record_ack() below stores the HIGHEST event seen so far
    (opened > seen > delivered - upgrade-only, idempotent);
  * the SMS fallback job (sms_fallback.py) picks unacked rows after its
    window and stamps sms_sent_at - the send-once guarantee;
  * the escalation ladder (escalation.py) appends kind="escalation" rows,
    one per notified contact, whose ack (via tokened link) stops the ladder;
  * the admin stats endpoint (api/get_weather_notice_stats) aggregates
    subscriber rows into "sent / ack % / median minutes to seen".

Every write here is guarded: on a shell where the doctype is not composed
(or any other trouble) each helper degrades to a no-op/None result - the
ledger must never break push delivery, the client endpoint, or a scheduler
pass. All datetimes are UTC (naive), like the rest of the engine.
"""
from __future__ import annotations

import datetime as dt

import frappe

DELIVERY_DOCTYPE = "Weather Notice Delivery"

#: ack ladder, upgrade-only: opened beats seen beats delivered.
EVENT_RANK = {"delivered": 1, "seen": 2, "opened": 3}
ACK_EVENTS = tuple(EVENT_RANK)
SEEN_RANK = EVENT_RANK["seen"]

KIND_SUBSCRIBER = "subscriber"
KIND_ESCALATION = "escalation"

#: sanity bound on client-supplied identifiers (rate-sane: junk never hits
#: the table).
MAX_ID_CHARS = 140

#: record_ack outcomes (stable strings - the endpoint and tests key on them).
ACK_RECORDED = "recorded"
ACK_UPGRADED = "upgraded"
ACK_NOOP = "noop"
ACK_UNKNOWN = "unknown"
ACK_BAD_REQUEST = "bad_request"
ACK_ERROR = "error"


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


def parse_client_ts(value):
    """Client-claimed ISO timestamp -> naive UTC datetime, or None.

    Purely informational (server clocks rule the metrics); malformed input
    is dropped, never an error back to the client.
    """
    if not value or not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed.replace(microsecond=0)


def _as_dt(value):
    """Datetime or ISO/DB string -> naive datetime, else None (pure)."""
    if isinstance(value, dt.datetime):
        return value
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")
                                         ).replace(tzinfo=None)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# writes (all guarded - never raise)
# --------------------------------------------------------------------------- #

def record_push_sent(warning_id, user, watch_location, event_class,
                     severity, now: dt.datetime | None = None):
    """Upsert the subscriber row for one successfully dispatched push.

    A re-push of the same warning (tier escalation) refreshes push_sent_at
    and severity on the existing row - the fallback window restarts from the
    newest push, and any ack already recorded stays recorded.
    """
    try:
        wid = str(warning_id or "").strip()
        if not wid or not user:
            return None
        now = now or _utcnow()
        existing = frappe.db.get_value(
            DELIVERY_DOCTYPE,
            {"warning_id": wid, "user": user, "kind": KIND_SUBSCRIBER},
            ["name"], as_dict=True)
        if existing:
            frappe.db.set_value(DELIVERY_DOCTYPE, existing.name, {
                "push_sent_at": now,
                "severity": severity,
            })
            return existing.name
        doc = frappe.get_doc({
            "doctype": DELIVERY_DOCTYPE,
            "kind": KIND_SUBSCRIBER,
            "warning_id": wid,
            "user": user,
            "watch_location": watch_location,
            "event_class": event_class,
            "severity": severity,
            "push_sent_at": now,
        })
        doc.insert(ignore_permissions=True)
        return getattr(doc, "name", None)
    except Exception:
        return None  # ledger trouble must never break push delivery


def record_ack(warning_id, user, event, client_ts=None,
               now: dt.datetime | None = None) -> str:
    """Record one client ack; idempotent and upgrade-only.

    opened(3) > seen(2) > delivered(1): only a strictly higher event writes.
    acked_at is the FIRST ack of any rank; seen_at the first rank >= seen -
    that is the timestamp the "median minutes to seen" metric uses. Unknown
    (warning, user) pairs and bad input return stable outcome strings the
    endpoint logs-and-200s on. Never raises.
    """
    try:
        rank = EVENT_RANK.get((event or "").strip(), 0)
        wid = str(warning_id or "").strip()
        if not rank or not wid or len(wid) > MAX_ID_CHARS:
            return ACK_BAD_REQUEST
        row = frappe.db.get_value(
            DELIVERY_DOCTYPE,
            {"warning_id": wid, "user": user, "kind": KIND_SUBSCRIBER},
            ["name", "acked_event", "acked_at", "seen_at"], as_dict=True)
        if not row:
            return ACK_UNKNOWN
        prev_rank = EVENT_RANK.get((row.acked_event or "").strip(), 0)
        if rank <= prev_rank:
            return ACK_NOOP  # replay or downgrade: read-only, still a 200
        now = now or _utcnow()
        updates = {"acked_event": event.strip()}
        if not row.acked_at:
            updates["acked_at"] = now
        if rank >= SEEN_RANK and not row.seen_at:
            updates["seen_at"] = now
        parsed_ts = parse_client_ts(client_ts)
        if parsed_ts is not None:
            updates["ack_client_ts"] = parsed_ts
        frappe.db.set_value(DELIVERY_DOCTYPE, row.name, updates)
        return ACK_UPGRADED if prev_rank else ACK_RECORDED
    except Exception:
        return ACK_ERROR


def record_sms_sent(row_name, now: dt.datetime | None = None) -> None:
    """Stamp sms_sent_at - the send-once mark (recorded even when the actual
    gateway send failed: repeat spam is worse than a lost transient, the
    failure is in the admin log). Never raises."""
    try:
        frappe.db.set_value(DELIVERY_DOCTYPE, row_name,
                            {"sms_sent_at": now or _utcnow()})
    except Exception:
        pass


def record_escalation(warning_id, watch_location, event_class, severity,
                      contact, priority, channels, token,
                      now: dt.datetime | None = None):
    """Append one kind="escalation" row: contact X was notified for warning
    Y at time Z via the listed channels, ack reachable through token."""
    try:
        doc = frappe.get_doc({
            "doctype": DELIVERY_DOCTYPE,
            "kind": KIND_ESCALATION,
            "warning_id": str(warning_id or "").strip(),
            "watch_location": watch_location,
            "event_class": event_class,
            "severity": severity,
            "contact": contact,
            "escalation_priority": priority,
            "channels": channels,
            "ack_token": token,
            "notified_at": now or _utcnow(),
        })
        doc.insert(ignore_permissions=True)
        return getattr(doc, "name", None)
    except Exception:
        return None


def record_escalation_ack(token, now: dt.datetime | None = None) -> str:
    """Ack-by-token for the escalation acknowledge link. Idempotent; unknown
    tokens are a stable outcome, never an error. Never raises."""
    try:
        tok = str(token or "").strip()
        if not tok or len(tok) > MAX_ID_CHARS:
            return ACK_BAD_REQUEST
        row = frappe.db.get_value(
            DELIVERY_DOCTYPE,
            {"ack_token": tok, "kind": KIND_ESCALATION},
            ["name", "acked_event"], as_dict=True)
        if not row:
            return ACK_UNKNOWN
        if row.acked_event:
            return ACK_NOOP
        now = now or _utcnow()
        frappe.db.set_value(DELIVERY_DOCTYPE, row.name, {
            "acked_event": "opened",
            "acked_at": now,
            "seen_at": now,
        })
        return ACK_RECORDED
    except Exception:
        return ACK_ERROR


# --------------------------------------------------------------------------- #
# reads (all guarded - empty results on any trouble)
# --------------------------------------------------------------------------- #

def find_sms_candidates(now: dt.datetime, window_minutes: int,
                        max_age_hours: int, limit: int) -> list:
    """Subscriber rows due an SMS: pushed at least window_minutes ago (but
    younger than max_age_hours - old rows age out of the scan), heads_up or
    stronger, no ack, no SMS yet. Oldest first."""
    try:
        floor = now - dt.timedelta(hours=max_age_hours)
        cutoff = now - dt.timedelta(minutes=window_minutes)
        if cutoff <= floor:
            return []
        return frappe.get_all(
            DELIVERY_DOCTYPE,
            filters={
                "kind": KIND_SUBSCRIBER,
                "severity": ["in", ["heads_up", "warning"]],
                "push_sent_at": ["between", [floor, cutoff]],
                "acked_event": ["is", "not set"],
                "sms_sent_at": ["is", "not set"],
            },
            fields=["name", "warning_id", "user", "watch_location",
                    "event_class", "severity", "push_sent_at"],
            order_by="push_sent_at asc",
            limit_page_length=limit,
        )
    except Exception:
        return []  # ledger absent on this shell: nothing to fall back on


def warning_has_ack(warning_id) -> bool:
    """True when ANY row (subscriber or escalation contact) acknowledged
    this warning - the escalation ladder's stop condition."""
    try:
        rows = frappe.get_all(
            DELIVERY_DOCTYPE,
            filters={"warning_id": str(warning_id or "").strip(),
                     "acked_event": ["in", list(ACK_EVENTS)]},
            fields=["name"],
            limit_page_length=1,
        )
        return bool(rows)
    except Exception:
        return False


def escalation_rows(warning_id) -> list:
    """This warning's escalation steps so far, in ladder order."""
    try:
        return frappe.get_all(
            DELIVERY_DOCTYPE,
            filters={"warning_id": str(warning_id or "").strip(),
                     "kind": KIND_ESCALATION},
            fields=["name", "contact", "escalation_priority", "notified_at",
                    "acked_event"],
            order_by="escalation_priority asc",
            limit_page_length=0,
        )
    except Exception:
        return []


# --------------------------------------------------------------------------- #
# stats (pure aggregation - the admin endpoint's math, offline-testable)
# --------------------------------------------------------------------------- #

def _median(values):
    values = sorted(values)
    if not values:
        return None
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0


def build_stats(rows) -> list:
    """Aggregate subscriber ledger rows into per-warning delivery stats.

    Returns a list (newest push first) of:
      {warning_id, watch_location, event_class, severity, sent,
       delivered, seen, opened, acked, ack_pct, median_minutes_to_seen}

    delivered/seen/opened are DISJOINT buckets keyed on each row's highest
    event; acked is their sum. median_minutes_to_seen is over
    (seen_at - push_sent_at) of rows that reached at least "seen" (opened
    implies seen). Pure: rows may carry datetimes or DB strings.
    """
    grouped = {}
    for raw in rows or []:
        row = raw if isinstance(raw, dict) else vars(raw)
        wid = str(row.get("warning_id") or "").strip()
        if not wid:
            continue
        agg = grouped.setdefault(wid, {
            "warning_id": wid,
            "watch_location": row.get("watch_location"),
            "event_class": row.get("event_class"),
            "severity": row.get("severity"),
            "sent": 0, "delivered": 0, "seen": 0, "opened": 0, "acked": 0,
            "_seen_minutes": [], "_last_push": None,
        })
        pushed = _as_dt(row.get("push_sent_at"))
        if pushed is None:
            continue
        agg["sent"] += 1
        if agg["_last_push"] is None or pushed > agg["_last_push"]:
            agg["_last_push"] = pushed
        rank = EVENT_RANK.get((row.get("acked_event") or "").strip(), 0)
        if not rank:
            continue
        agg["acked"] += 1
        if rank == EVENT_RANK["delivered"]:
            agg["delivered"] += 1
        elif rank == EVENT_RANK["seen"]:
            agg["seen"] += 1
        else:
            agg["opened"] += 1
        if rank >= SEEN_RANK:
            seen_at = _as_dt(row.get("seen_at")) or _as_dt(row.get("acked_at"))
            if seen_at is not None and seen_at >= pushed:
                agg["_seen_minutes"].append(
                    (seen_at - pushed).total_seconds() / 60.0)

    out = []
    for agg in grouped.values():
        minutes = agg.pop("_seen_minutes")
        last_push = agg.pop("_last_push")
        agg["ack_pct"] = (round(100.0 * agg["acked"] / agg["sent"], 1)
                          if agg["sent"] else 0.0)
        median = _median(minutes)
        agg["median_minutes_to_seen"] = (round(median, 1)
                                         if median is not None else None)
        out.append((last_push or dt.datetime.min, agg))
    out.sort(key=lambda pair: pair[0], reverse=True)
    return [agg for _, agg in out]
