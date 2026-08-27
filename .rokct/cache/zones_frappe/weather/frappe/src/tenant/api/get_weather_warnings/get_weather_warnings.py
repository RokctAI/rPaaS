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

"""TENANT-side thin proxy: severe-weather heads-ups for a location.

Composed only into tenant products (src/tenant/ persona folder - see
frappe_sdk_management.md, role-based composition). Clients call the exact
same cmd as before ("tenant.api.get_weather_warnings", payload
{"latitude": .., "longitude": .., "locale": optional}); the heavy lifting
now happens on the control site, which runs the warnings engine.

The proxy reuses the get_weather proxy's control-plane mechanism verbatim
(src/weather/get_weather/get_weather.py): connection details come from site
config keys set during tenant provisioning ("control_plane_url",
"api_secret", optional "control_plane_scheme"), the call goes out with the
X-Rokct-Secret / X-Rokct-Tenant headers via frappe.make_get_request, and the
response is cached tenant-side for 10 minutes (CACHE_TTL_SECONDS = 600) per
0.25 degree grid cell.

Forwarding IS the registration: the control-side endpoint registers the
queried grid cell as a Weather Watch Location, so the hourly control-side
evaluator starts covering every cell any tenant asks about. Logged-in
callers are additionally recorded tenant-locally as Weather Watch Subscriber
rows (the audience for the tenant push-sync job - src/tenant/push_sync.py).

Failure contract (identical to the engine-side endpoint): internal errors
NEVER reach the end user - a misconfigured tenant, an unreachable control
plane, or a malformed reply all return {"warnings": [], ...} after a
rate-limited admin log line. The end-user surface for failure is nothing.
"""
from __future__ import annotations

import datetime as dt

import frappe

from ....warnings_engine.admin_log import TITLE_API, log_admin_error
from ....warnings_engine.messages import ATTRIBUTION

SUBSCRIBER_DOCTYPE = "Weather Watch Subscriber"

GRID_STEP = 0.25  # the control-side evaluation grid (ERA5 cells)
CACHE_TTL_SECONDS = 600  # the get_weather proxy pattern

#: dotted alias of the control-side serving endpoint. The control shell's
#: composed app package is named "control" - the same conservative assumption
#: the get_weather proxy hardcodes in its "control.control.api.get_weather"
#: URL; "api.get_weather_warnings" is the {app_name}.api.get_weather_warnings
#: alias this module's manifest declares in its app_type.control block.
CONTROL_METHOD = "control.api.get_weather_warnings"

#: a subscriber row's last_requested_at is refreshed at most this often (the
#: push fan-out only needs coarse freshness - see push.SUBSCRIBER_FRESH_DAYS).
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
    locale: optional, forwarded for forward compatibility.
    include_drills: optional; DRILL FENCE default. Only an explicitly truthy
    value ("1"/"true"/"yes"/"on") asks the control plane to include
    training-exercise records (is_drill=1) - for admin/training surfaces
    only. A drill-inclusive response bypasses and never populates the tenant
    cache, so real clients can never be served one.
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

    grid_lat, grid_lng = _grid_round(lat), _grid_round(lng)
    grid_key = _grid_key(grid_lat, grid_lng)
    try:
        response = fetch_cell_warnings(grid_lat, grid_lng, locale=locale,
                                       include_drills=_truthy(include_drills))
        _register_subscriber(grid_key)
        return response if response is not None else _empty_response()
    except Exception:
        log_admin_error(TITLE_API)
        return _empty_response()


def fetch_cell_warnings(grid_lat: float, grid_lng: float, locale=None,
                        include_drills: bool = False):
    """Cache-through fetch of a grid cell's active heads-ups from control.

    Shared by the client endpoint above and the hourly push-sync job
    (src/tenant/push_sync.py) - deliberately does NOT touch the subscriber
    registry, so a scheduler identity never self-subscribes. Returns the
    control site's response dict, or an empty envelope on any failure.

    include_drills=True (admin/training surfaces only) forwards the drill
    flag to the control plane and BYPASSES the tenant cache in both
    directions - a drill-inclusive payload is never stored where a real
    client could receive it.
    """
    grid_key = _grid_key(grid_lat, grid_lng)
    cache_key = f"weather_warnings_{grid_key}"
    if not include_drills:
        try:
            cached = frappe.cache().get_value(cache_key)
            if cached:
                return cached
        except Exception:
            pass  # cache trouble must not break the endpoint

    try:
        response = _fetch_from_control(grid_lat, grid_lng, locale,
                                       include_drills)
    except Exception:
        log_admin_error(TITLE_API)
        return _empty_response()

    if not include_drills:
        try:
            frappe.cache().set_value(cache_key, response,
                                     expires_in_sec=CACHE_TTL_SECONDS)
        except Exception:
            pass
    return response


def _fetch_from_control(grid_lat: float, grid_lng: float, locale=None,
                        include_drills: bool = False) -> dict:
    """One HTTPS round-trip to the control plane (the get_weather mechanism).

    Raises on any problem - callers own the fail-silent contract.
    """
    control_plane_url = frappe.conf.get("control_plane_url")
    api_secret = frappe.conf.get("api_secret")
    if not control_plane_url or not api_secret:
        raise ValueError(
            "tenant site is not configured to reach the control plane")

    scheme = frappe.conf.get("control_plane_scheme", "https")
    api_url = f"{scheme}://{control_plane_url}/api/method/{CONTROL_METHOD}"
    headers = {
        "X-Rokct-Secret": api_secret,
        "X-Rokct-Tenant": frappe.local.site,
        "Accept": "application/json",
    }
    params = {"latitude": grid_lat, "longitude": grid_lng}
    if locale:
        params["locale"] = locale
    if include_drills:
        params["include_drills"] = 1

    response = frappe.make_get_request(api_url, headers=headers, params=params)

    # /api/method/* replies arrive as {"message": <return value>}; unwrap so
    # tenant clients receive exactly the shape control-side clients receive.
    if isinstance(response, dict) and set(response) == {"message"}:
        response = response["message"]
    if not isinstance(response, dict) or not isinstance(
            response.get("warnings"), list):
        raise ValueError("malformed warnings payload from the control plane")
    return response


def _register_subscriber(grid_key: str) -> None:
    """Upsert the calling user's (grid cell, user) subscription row.

    Feeds the tenant push-sync fan-out (src/tenant/push_sync.py). The
    watch_location field stores the 0.25 degree grid key string - on tenant
    shells the Weather Watch Location doctype does not exist (it is
    control-side), and grid keys ARE watch-location names on control (the
    doctype autonames by grid_key). Additive and fully guarded: anonymous /
    Guest sessions are skipped and NO failure here may break the endpoint.
    """
    try:
        user = getattr(getattr(frappe, "session", None), "user", None)
        if not user or user == "Guest":
            return
        now = dt.datetime.utcnow().replace(microsecond=0)
        existing = frappe.db.get_value(
            SUBSCRIBER_DOCTYPE,
            {"watch_location": grid_key, "user": user},
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
            "watch_location": grid_key,
            "user": user,
            "last_requested_at": now,
        }).insert(ignore_permissions=True)
    except Exception:
        pass  # subscriber registry must never break the warnings endpoint
