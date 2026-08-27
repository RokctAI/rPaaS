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

"""CONTROL-side serving endpoint: current severe-weather heads-ups for a
location.

This is the engine-side implementation, composed only into the control
product (src/control/ persona folder - see frappe_sdk_management.md, role-
based composition). It answers two callers with one contract:

  - the control product's own clients, through the platform gateway as cmd
    "tenant.api.get_weather_warnings" (directly-registered locations keep
    working exactly as before this split);
  - tenant backends' thin proxies (src/tenant/api/get_weather_warnings/),
    which forward their callers' coordinates over HTTPS to the alias
    "api.get_weather_warnings" on the control plane - so a tenant call IS
    the registration: the cell lands in Weather Watch Location below and
    the hourly evaluator starts covering it.

Payload {"latitude": .., "longitude": .., "locale": optional}. The
coordinates are rounded to the 0.25 degree evaluation grid; the call
registers/refreshes the grid cell as a Weather Watch Location (so the hourly
evaluator starts covering it) and returns the cell's currently-active
heads-ups as server-rendered friendly strings plus minimal structured fields.
Logged-in callers are additionally recorded as Weather Watch Subscriber rows
where that (tenant-side) doctype is installed; on the control shell the
subscriber registry is absent and registration is a guarded no-op (push to
tenant users is the tenant push-sync job's business - src/tenant/push_sync.py).

Failure contract: internal errors NEVER reach the end user - any problem
returns {"warnings": [], ...} after a rate-limited admin log. The end-user
surface for failure is nothing.

All user-facing text is heads-up possibility phrasing (see messages.py for
the legal constraint); the "severity" field is an internal enum - clients
render "severity_label" / the strings, never the enum.

Advisory records (severity "advisory", written by the propagation pass -
warnings_engine/propagation.py) ARE included in the response, with
severity_label "Worth knowing". Deliberate: clients that do not know the
enum value fail closed and render nothing (the current dart banner knows
only heads_up|warning), so the backend can ship and enable propagation
first; advisories surface to users only once a client learns the value and
renders it strictly BELOW heads_up in prominence.

Response caching: 600 s per grid cell (the get_weather pattern).

Official-alert relay (additive, warnings_engine/official_alerts.py): when
the get_weather proxy's own 10-min cache holds a forecast payload for this
cell's label that carries active official alerts, the response additionally
gains "official_alerts_present": true and each message gets a gentle
cross-reference sentence. ZA-only by default, config-gated, cache-read-only,
and fail-silent - any problem leaves the response exactly as documented
above.
"""
from __future__ import annotations

import datetime as dt

import frappe

from ....warnings_engine.admin_log import TITLE_API, log_admin_error
from ....warnings_engine.messages import ATTRIBUTION

WATCH_DOCTYPE = "Weather Watch Location"
WARNING_DOCTYPE = "Severe Weather Warning"
SUBSCRIBER_DOCTYPE = "Weather Watch Subscriber"

GRID_STEP = 0.25  # ERA5 evaluation grid (see warnings_engine/sources/openmeteo_s3.py)
CACHE_TTL_SECONDS = 600

#: a subscriber row's last_requested_at is refreshed at most this often - the
#: push fan-out only needs coarse freshness (30-day cutoff), so the hot path
#: stays read-mostly.
SUBSCRIBER_REFRESH_HOURS = 6


def _iso_utc(value) -> str:
    if value is None:
        return None
    if isinstance(value, str):
        value = frappe.utils.get_datetime(value)
    return value.replace(microsecond=0).isoformat() + "Z"


def _empty_response() -> dict:
    return {
        "warnings": [],
        "attribution": ATTRIBUTION,
        "generated_at": _iso_utc(dt.datetime.utcnow()),
    }


def _grid_round(value: float) -> float:
    return round(float(value) / GRID_STEP) * GRID_STEP


def _grid_key(grid_lat: float, grid_lng: float) -> str:
    return f"{grid_lat:.2f},{grid_lng:.2f}"


def _truthy(value) -> bool:
    """Conservative flag parse: only an explicit yes counts (fail closed)."""
    return str(value).strip().lower() in ("1", "true", "yes", "on")


@frappe.whitelist()
def get_weather_warnings(latitude=None, longitude=None, locale=None,
                         include_drills=None):
    """Active severe-weather heads-ups for the grid cell nearest a point.

    latitude/longitude: required coordinates (the shop/branch location).
    locale: optional, accepted for forward compatibility - copy is currently
    English-only and rendered server-side.
    include_drills: optional; DRILL FENCE default. Training-exercise records
    written by the drill replay runner (warnings_engine/drill.py,
    is_drill=1) are excluded from every response unless this flag is
    explicitly truthy ("1"/"true"/"yes"/"on" - anything else, including
    absence and garbage, excludes them). A drill-inclusive response is never
    cached, so a real client can never be served one by cache collision;
    each of its warnings carries "is_drill" so admin/training surfaces can
    label them.
    """
    try:
        lat = float(latitude)
        lng = float(longitude)
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            raise ValueError(f"coordinates out of range: {lat}, {lng}")
    except (TypeError, ValueError):
        log_admin_error(TITLE_API, "get_weather_warnings called with invalid "
                                   f"coordinates: {latitude!r}, {longitude!r}")
        return _empty_response()

    drills = _truthy(include_drills)
    grid_lat, grid_lng = _grid_round(lat), _grid_round(lng)
    grid_key = _grid_key(grid_lat, grid_lng)
    cache_key = f"weather_warnings_{grid_key}"
    try:
        cached = None if drills else frappe.cache().get_value(cache_key)
        if cached:
            # The response cache is shared per grid cell, so subscriber
            # registration must still happen on cache hits (watch locations
            # are named by grid_key, and a cached response implies the
            # location row exists).
            _register_subscriber(grid_key)
            return cached
    except Exception:
        pass  # cache trouble must not break the endpoint

    try:
        location_name, location_label = _register_watch_location(
            grid_key, grid_lat, grid_lng)
        _register_subscriber(location_name)
        response = {
            "warnings": _active_warnings(location_name,
                                         include_drills=drills),
            "attribution": ATTRIBUTION,
            "generated_at": _iso_utc(dt.datetime.utcnow()),
        }
        try:
            # Additive official-alert awareness (fail-silent by contract:
            # any error here leaves the response exactly as built above).
            from ...warnings_engine.official_alerts import (
                apply_official_alert_relay,
            )
            response = apply_official_alert_relay(
                response, grid_lat, grid_lng, location_label)
        except Exception:
            pass
        if not drills:  # a drill-inclusive payload must never be cached
            try:
                frappe.cache().set_value(cache_key, response,
                                         expires_in_sec=CACHE_TTL_SECONDS)
            except Exception:
                pass
        return response
    except Exception:
        log_admin_error(TITLE_API)
        return _empty_response()


def _register_watch_location(grid_key: str, grid_lat: float, grid_lng: float):
    """Upsert the grid cell's watch location; refresh last_requested_at.

    Returns (name, label) - the label feeds the official-alert relay's
    cache lookup. A row an admin deactivated stays deactivated (desk is the
    escape hatch); the request timestamp still refreshes so the sweep never
    flaps it.
    """
    now = dt.datetime.utcnow().replace(microsecond=0)
    existing = frappe.db.get_value(
        WATCH_DOCTYPE, {"grid_key": grid_key}, ["name", "label"], as_dict=True)
    if existing:
        frappe.db.set_value(WATCH_DOCTYPE, existing.name,
                            {"last_requested_at": now})
        return existing.name, existing.label
    doc = frappe.get_doc({
        "doctype": WATCH_DOCTYPE,
        "grid_key": grid_key,
        "latitude": grid_lat,
        "longitude": grid_lng,
        "active": 1,
        "last_requested_at": now,
    })
    doc.insert(ignore_permissions=True)
    return doc.name, None


def _register_subscriber(location_name: str) -> None:
    """Upsert the calling user's (watch location, user) subscription row.

    Feeds the severe-weather push fan-out ("users of a watch location" -
    see warnings_engine/push.py). Additive and fully guarded: anonymous /
    Guest sessions are skipped and NO failure here may break the endpoint.
    """
    try:
        user = getattr(getattr(frappe, "session", None), "user", None)
        if not user or user == "Guest":
            return
        now = dt.datetime.utcnow().replace(microsecond=0)
        existing = frappe.db.get_value(
            SUBSCRIBER_DOCTYPE,
            {"watch_location": location_name, "user": user},
            ["name", "last_requested_at"],
            as_dict=True,
        )
        if existing:
            last = (frappe.utils.get_datetime(existing.last_requested_at)
                    if existing.last_requested_at else None)
            if last and now - last < dt.timedelta(hours=SUBSCRIBER_REFRESH_HOURS):
                return  # fresh enough - keep the hot path read-only
            frappe.db.set_value(SUBSCRIBER_DOCTYPE, existing.name,
                                {"last_requested_at": now})
            return
        frappe.get_doc({
            "doctype": SUBSCRIBER_DOCTYPE,
            "watch_location": location_name,
            "user": user,
            "last_requested_at": now,
        }).insert(ignore_permissions=True)
    except Exception:
        pass  # subscriber registry must never break the warnings endpoint


def _active_warnings(location_name: str, include_drills: bool = False) -> list:
    from ....warnings_engine.messages import SEVERITY_LABELS

    now = dt.datetime.utcnow()
    filters = {
        "watch_location": location_name,
        "status": "active",
        "valid_until": [">", now],
    }
    if not include_drills:
        # drill fence (fail-closed default): training-exercise records
        # (warnings_engine/drill.py) never reach a client response unless
        # the caller explicitly asked for them.
        filters["is_drill"] = ["!=", 1]
    fields = ["name", "event_class", "severity", "headline", "message",
              "onset", "valid_until", "issued_at"]
    if include_drills:
        fields += ["is_drill", "drill_run_id"]
    rows = frappe.get_all(
        WARNING_DOCTYPE,
        filters=filters,
        fields=fields,
        order_by="valid_until desc",
    )
    warnings = []
    for row in rows:
        item = {
            "id": row.name,
            "event_class": row.event_class,
            "severity": row.severity,
            "severity_label": SEVERITY_LABELS.get(row.severity, ""),
            "headline": row.headline,
            "message": row.message,
            "onset": _iso_utc(row.onset),
            "valid_until": _iso_utc(row.valid_until),
            "issued_at": _iso_utc(row.issued_at),
        }
        if include_drills:
            # only the drill-inclusive (admin/training) payload carries the
            # flag - the standard client payload shape is unchanged
            item["is_drill"] = 1 if row.get("is_drill") else 0
            if row.get("drill_run_id"):
                item["drill_run_id"] = row.get("drill_run_id")
        warnings.append(item)

    # sw6 vulnerable sites (warnings_engine/sites.py): attach the cell's
    # per-site notices to their parent warning, each marked
    # kind="site_notice" so clients can tell them from plain cell heads-ups.
    # Strictly additive and fail-closed: any problem leaves the response
    # exactly as built above, clients that do not know the key ignore it,
    # and the notices then flow through the tenant proxy + push-sync fetch
    # unchanged (they ride the same cached cell payload as the warning).
    # Drill records never have site notices (sites.sync_site_notices refuses
    # them at generation time), so the drill-inclusive admin view gains
    # nothing here either.
    try:
        from ...warnings_engine.sites import active_site_notices
        notices = active_site_notices([w["id"] for w in warnings])
        for w in warnings:
            if notices.get(w["id"]):
                w["site_notices"] = notices[w["id"]]
    except Exception:
        pass
    return warnings
