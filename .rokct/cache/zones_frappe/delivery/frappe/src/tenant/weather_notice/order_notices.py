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

"""Hourly job: tell the customer and the shop when severe weather may
delay an active order - WITHOUT either app needing the weather SDK.

For every ACTIVE order (status New/Accepted/Shipped - not yet Delivered or
Cancelled) whose drop-off grid cell OR shop grid cell has an active
WARNING-tier severe-weather notice overlapping the order's expected
delivery window, one push goes to the order's customer and one to the
shop's user, through the comms module's ``send_push_notification`` (guarded
frappe.get_attr dispatch - the weather push.py pattern; comms absent =
silent no-op). Couriers see the same weather through the per-stop
``weather_notice`` annotation (weather_notice.py); customers and shops get
it as order comms, so the marketplace/customer apps never talk to the
weather module at all.

Expected delivery window (the Order doctype - orders module, RokctAI/
commerce - carries real scheduling fields):
  - ``delivery_date`` + ``delivery_time`` set -> [that instant, +1 hour];
  - ``delivery_date`` only                   -> that whole day;
  - neither -> [order creation, creation + "severe_weather_order_notices_
    horizon_hours" (default 24)] - the order-placed+horizon fallback.
Windows already fully in the past notify nobody (the delivery moment has
passed). Overlap against a notice's [onset, valid_until]; a notice with no
onset counts as already under way. Warning validity is UTC and order
scheduling is site-local; at grid-cell/hour granularity that skew is
accepted and documented here.

Send-once: each (order, notice episode, audience) pair is recorded as a
Weather Order Notice row (delivery module doctype) the moment a push is
attempted, and never re-sent - a refresh of the same warning record keeps
its id, so an episode notifies each audience exactly once per order.

MASTER SWITCH: "severe_weather_order_notices" (weather_notice.py - default
ON, set 0 in site_config.json to turn the whole feature off).

Copy: calm, no meteorology, and NEVER the word "warning" in anything a
user sees (the weather module's legal constraint - messages.py). E.g.
"Your delivery may be delayed - heavy rain is expected near the delivery
area."
"""
from __future__ import annotations

import datetime as dt

import frappe
from frappe.utils import cint

from . import weather_notice

NOTICE_DOCTYPE = "Weather Order Notice"

#: only orders still moving toward a delivery are considered.
ACTIVE_ORDER_STATUSES = ("New", "Accepted", "Shipped")

#: fallback expected-delivery horizon (hours after order placement) for
#: orders without delivery_date/delivery_time; override with site config
#: "severe_weather_order_notices_horizon_hours".
CONF_HORIZON_HOURS = "severe_weather_order_notices_horizon_hours"
DEFAULT_HORIZON_HOURS = 24

#: a scheduled (date+time) delivery is treated as this long a window.
SLOT_WINDOW_HOURS = 1

#: orders older than this never notify (bounds the hourly scan; any order
#: still undelivered after a week has bigger problems than the weather).
MAX_ORDER_AGE_DAYS = 7

#: composed path of the comms module's FCM sender (send_push_notification
#: (user, title, body, data)); shells without comms resolve nothing and the
#: job is a silent no-op - the weather push.py pattern.
COMMS_TARGET = "{app_name}.comms.tenant.api.notification.send_push_notification"

#: only the strong tier notifies customers/shops; couriers also see
#: heads_up through the per-stop annotation.
NOTIFY_SEVERITY = "warning"

#: calm per-event-class reason phrases (weather module event classes; see
#: weather/frappe/src/warnings_engine/messages.py CLASS_MAX_SEVERITY for
#: which classes can reach the warning tier at all).
REASON_PHRASES = {
    "flash_flood": "heavy rain is expected",
    "flood": "flooding is expected",
    "destructive_wind": "very strong winds are expected",
}
DEFAULT_REASON = "severe weather is expected"

CUSTOMER_TITLE = "About your delivery"
CUSTOMER_BODY = "Your delivery may be delayed - {reason} near the delivery area."
SHOP_TITLE = "Deliveries may run late"
SHOP_BODY = "Order {order} may be delayed - {reason} near the delivery area."


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


def horizon_hours() -> int:
    try:
        raw = frappe.conf.get(CONF_HORIZON_HOURS)
    except Exception:
        raw = None
    if raw is None:
        return DEFAULT_HORIZON_HOURS
    return max(cint(raw), 1)


def _resolve_sender():
    """frappe.get_attr the comms sender; None when comms is absent."""
    try:
        sender = frappe.get_attr(COMMS_TARGET)
        return sender if callable(sender) else None
    except Exception:
        return None


def _as_datetime(value):
    """Best-effort parse of a date/datetime-ish value to naive datetime."""
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time())
    text = str(value).strip().replace("T", " ").rstrip("Z")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(text[:len(fmt) + 2].strip(), fmt)
        except ValueError:
            continue
    return None


def _as_time(value):
    """Best-effort parse of a Time field value (frappe loads these as
    timedelta) to a dt.time, or None."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.timedelta):
        seconds = int(value.total_seconds()) % 86400
        return dt.time(seconds // 3600, (seconds % 3600) // 60, seconds % 60)
    if isinstance(value, dt.time):
        return value
    text = str(value).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return dt.datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def expected_delivery_window(order, now=None):
    """(start, end) naive datetimes of when this order should be delivered.

    Uses the Order doctype's real scheduling fields (delivery_date Date +
    delivery_time Time) when present; otherwise falls back to order
    placement + the configured horizon. None when nothing parseable exists.
    """
    date_part = _as_datetime(order.get("delivery_date"))
    if date_part is not None:
        date_only = date_part.date()
        time_part = _as_time(order.get("delivery_time"))
        if time_part is not None:
            start = dt.datetime.combine(date_only, time_part)
            return start, start + dt.timedelta(hours=SLOT_WINDOW_HOURS)
        start = dt.datetime.combine(date_only, dt.time())
        return start, start + dt.timedelta(days=1)
    placed = _as_datetime(order.get("creation"))
    if placed is None:
        placed = now or _utcnow()
    return placed, placed + dt.timedelta(hours=horizon_hours())


def _parse_iso(value):
    """The weather response's ISO-8601 "...Z" strings to naive datetime."""
    return _as_datetime(value)


def _overlaps(entry, window) -> bool:
    """Does a notice's validity overlap the order's expected window?"""
    start, end = window
    valid_until = _parse_iso(entry.get("valid_until"))
    if valid_until is not None and valid_until <= start:
        return False
    onset = _parse_iso(entry.get("onset"))  # None: already under way
    if onset is not None and onset >= end:
        return False
    return True


def _reason(entry) -> str:
    return REASON_PHRASES.get(entry.get("event_class"), DEFAULT_REASON)


def _already_sent(order_name, notice_id, audience) -> bool:
    try:
        return bool(frappe.db.get_value(
            NOTICE_DOCTYPE,
            {"order": order_name, "notice": notice_id, "audience": audience},
            "name",
        ))
    except Exception:
        return True  # can't prove it's new: silence beats repeat spam


def _record_sent(order_name, notice_id, audience, user, now) -> None:
    try:
        frappe.get_doc({
            "doctype": NOTICE_DOCTYPE,
            "order": order_name,
            "notice": notice_id,
            "audience": audience,
            "user": user,
            "sent_at": now,
        }).insert(ignore_permissions=True)
    except Exception:
        pass  # the ledger must never break the run


def _order_coords(order):
    """Drop-off (lat, lng) from Order.location JSON, or None."""
    try:
        from ..api.delivery_man.delivery_man import _parse_location_dict
        parsed = _parse_location_dict(order.get("location"))
        if parsed:
            return parsed["latitude"], parsed["longitude"]
    except Exception:
        pass
    return None


def _shop_row(shop_name, cache):
    """{"user", "coords"} for a Shop (owner user + parsed location)."""
    if not shop_name:
        return {"user": None, "coords": None}
    if shop_name in cache:
        return cache[shop_name]
    row = {"user": None, "coords": None}
    try:
        from ..api.delivery_man.delivery_man import _parse_location_dict
        value = frappe.db.get_value(
            "Shop", shop_name, ["user", "location"], as_dict=True)
        if value:
            row["user"] = value.get("user")
            parsed = _parse_location_dict(value.get("location"))
            if parsed:
                row["coords"] = (parsed["latitude"], parsed["longitude"])
    except Exception:
        pass
    cache[shop_name] = row
    return row


def _cell_warning_notices(coords, cache):
    """WARNING-tier active entries for a coordinate's grid cell, cached
    per run per rounded cell."""
    if not coords:
        return []
    try:
        key = (weather_notice._grid_round(coords[0]),
               weather_notice._grid_round(coords[1]))
    except Exception:
        return []
    if key not in cache:
        cache[key] = [
            entry for entry in
            weather_notice.active_cell_warnings(coords[0], coords[1])
            if entry.get("severity") == NOTIFY_SEVERITY
        ]
    return cache[key]


def run_order_weather_notices():
    """Scheduler entry point (hourly). Never raises."""
    try:
        return _run()
    except Exception:
        try:
            frappe.log_error(
                frappe.get_traceback(), "Weather Order Notices")
        except Exception:
            pass
        return "error"


def _run(now=None):
    """The decision pipeline; returns a short reason string (for tests)."""
    if not weather_notice.notices_enabled():
        return "disabled"

    sender = _resolve_sender()
    if sender is None:
        return "no_sender"  # comms absent: silent no-op

    now = now or _utcnow()
    try:
        orders = frappe.get_all(
            "Order",
            filters={
                "status": ["in", list(ACTIVE_ORDER_STATUSES)],
                "creation": [
                    ">=", now - dt.timedelta(days=MAX_ORDER_AGE_DAYS)],
            },
            fields=["name", "user", "shop", "status", "location",
                    "delivery_date", "delivery_time", "creation"],
        )
    except Exception:
        return "no_orders"  # Order doctype absent on this shell
    if not orders:
        return "no_orders"

    cell_cache = {}
    shop_cache = {}
    sent = 0
    for order in orders:
        try:
            sent += _process_order(
                order, now, sender, cell_cache, shop_cache)
        except Exception:
            continue  # one bad order must not starve the rest
    return f"sent:{sent}"


def _process_order(order, now, sender, cell_cache, shop_cache) -> int:
    window = expected_delivery_window(order, now=now)
    if window is None or window[1] <= now:
        return 0  # the expected delivery moment has passed

    shop = _shop_row(order.get("shop"), shop_cache)

    # union of overlapping warning-tier notices over both cells, id-deduped
    notices = {}
    for coords in (_order_coords(order), shop["coords"]):
        for entry in _cell_warning_notices(coords, cell_cache):
            if not entry.get("id"):
                continue
            if _overlaps(entry, window):
                notices.setdefault(entry["id"], entry)
    if not notices:
        return 0

    order_name = order.get("name")
    audiences = (
        ("Customer", order.get("user"), CUSTOMER_TITLE, CUSTOMER_BODY),
        ("Shop", shop["user"], SHOP_TITLE, SHOP_BODY),
    )
    sent = 0
    for notice_id, entry in notices.items():
        for audience, user, title, body_tpl in audiences:
            if not user or user == "Guest":
                continue
            if _already_sent(order_name, notice_id, audience):
                continue
            body = body_tpl.format(
                reason=_reason(entry), order=order_name)
            data = {
                "type": "weather_order_notice",
                "order_id": str(order_name),
                "notice_id": str(notice_id),
                "event_class": entry.get("event_class"),
                "severity": entry.get("severity"),
                "valid_until": entry.get("valid_until"),
            }
            try:
                sender(user=user, title=title, body=body, data=data)
                sent += 1
            except Exception:
                pass  # failures land in comms' own logging
            # Record the attempt even when the send failed: repeat spam is
            # worse than a lost transient (the weather push.py stance).
            _record_sent(order_name, notice_id, audience, user, now)
    return sent
