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

"""Guarded read of the weather module's active severe-weather heads-ups,
for annotating CUSTOMER-facing order payloads (list_orders /
get_order_details - the marketplace apps' active-order glance card and
order pages) with an optional ``weather_notice`` field for the order's
drop-off grid cell.

This is the orders-module twin of the delivery module's per-stop
annotation (RokctAI/zones, delivery/frappe/src/weather_notice/
weather_notice.py): couriers see the weather on their stop payloads,
customers see the same weather riding along on their own order data -
so the marketplace/customer apps never talk to the weather module at
all ("orderdata walks with weather").

MASTER SWITCH (site config): "severe_weather_order_notices"
DEFAULT: ON. The flag is an OFF-switch: an admin sets
``"severe_weather_order_notices": 0`` in site_config.json to disable the
annotation on a site; an absent key means enabled. (Same key and same
off-switch convention as the delivery module's stop annotation and the
weather module's "severe_weather_push_enabled".)

The orders module composes into shells WITH or WITHOUT the weather
module, so everything here is guarded dynamic dispatch (the weather
push.py pattern): ``frappe.get_attr`` over the composed weather read
paths, and any failure - module absent, misconfigured tenant,
unreachable control plane - is a silent no-op. Callers see "no notice",
never an error, and the ``weather_notice`` field is simply ABSENT from
serialized orders.

Read paths tried, in order ({app_name} tokens are substituted by the
backend composer):

  - the tenant proxy's cache-through cell fetch
    (weather/frappe/src/tenant/api/get_weather_warnings/get_weather_warnings.py
    ``fetch_cell_warnings``) - present on tenant-marked AND unmarked shells;
    deliberately free of subscriber-registration side effects, and itself
    fail-silent (returns {"warnings": [], ...} on any problem);
  - the control-side serving endpoint
    (weather/frappe/src/control/api/get_weather_warnings/get_weather_warnings.py
    ``get_weather_warnings``) - control-marked shells only.

Both accept (grid_lat, grid_lng) positionally; coordinates are rounded to
the same 0.25 degree evaluation grid the weather module uses, so passing
already-rounded values is idempotent for the endpoint variant.

Copy: every user-facing string in a notice is the weather module's own
server-rendered calm copy (warnings_engine/messages.py - heads-up
possibility phrasing, never the word "warning"). The internal severity
enum rides along for machines; clients render ``severity_label``/``text``,
never the enum.
"""
from __future__ import annotations

import json
import math

import frappe
from frappe.utils import cint

#: MASTER SWITCH - default ON; set 0 to disable (the flag is an off-switch).
CONF_ENABLED = "severe_weather_order_notices"

#: composed dotted paths of the weather module's active-warnings read, in
#: preference order (see module docstring). Shells without weather resolve
#: neither and every notice read is a silent no-op.
WARNINGS_SOURCE_CANDIDATES = (
    "{app_name}.weather.tenant.api.get_weather_warnings.fetch_cell_warnings",
    "{app_name}.weather.control.api.get_weather_warnings.get_weather_warnings",
)

#: the weather module's evaluation grid (ERA5 cells) - keep in sync with
#: GRID_STEP in weather/frappe/src/*/api/get_weather_warnings/.
GRID_STEP = 0.25

#: internal severity enum, ranked. "advisory" (neighbor-propagated soft
#: notices) is deliberately excluded: order notices surface heads_up and
#: warning tiers only, mirroring the delivery module's stop annotation.
SEVERITY_RANK = {"heads_up": 1, "warning": 2}


def notices_enabled() -> bool:
    """The master switch; bad config reads as OFF (fail quiet)."""
    try:
        raw = frappe.conf.get(CONF_ENABLED)
        if raw is None:
            return True  # default ON - the flag is an off-switch
        return bool(cint(raw))
    except Exception:
        return False


def parse_location_dict(value):
    """Parse a location JSON string/dict into {"latitude", "longitude"}
    floats, or None when malformed (never raises - Order.location is a
    free-text field; same parser as the delivery module's
    _parse_location_dict)."""
    data = value
    if isinstance(data, str):
        text = data.strip()
        if not text:
            return None
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            return None
    if not isinstance(data, dict):
        return None
    lat = data.get("latitude", data.get("lat"))
    lon = data.get("longitude", data.get("long", data.get("lng")))
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon)):
        # json.loads accepts NaN/Infinity literals; a NaN here would
        # serialize as invalid JSON for the app's decoder.
        return None
    return {"latitude": lat, "longitude": lon}


def _grid_round(value: float) -> float:
    return round(float(value) / GRID_STEP) * GRID_STEP


def _resolve_warnings_source():
    """frappe.get_attr the first resolvable weather read path, or None.

    None means "this shell composes no weather module" (or the layout
    changed) - callers treat it as "no notices", never an error.
    """
    for path in WARNINGS_SOURCE_CANDIDATES:
        try:
            source = frappe.get_attr(path)
            if callable(source):
                return source
        except Exception:
            continue
    return None


def active_cell_warnings(latitude, longitude) -> list:
    """Active heads-up/warning-tier entries for the grid cell of a point.

    Returns copies of the weather response's entry dicts (id, event_class,
    severity, severity_label, headline, message, onset, valid_until,
    issued_at), filtered to the severities order notices may surface, each
    carrying the response's data ``attribution`` (CC-BY: rendered on every
    surface that displays a notice). Empty list on ANY problem - absent
    weather module, invalid coordinates, malformed response - by contract.
    """
    try:
        lat = float(latitude)
        lng = float(longitude)
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            return []
        if not (math.isfinite(lat) and math.isfinite(lng)):
            return []
    except (TypeError, ValueError):
        return []

    source = _resolve_warnings_source()
    if source is None:
        return []

    try:
        response = source(_grid_round(lat), _grid_round(lng))
        entries = (response or {}).get("warnings")
        if not isinstance(entries, list):
            return []
        attribution = (response or {}).get("attribution")
        return [
            dict(entry, attribution=attribution)
            for entry in entries
            if isinstance(entry, dict)
            and entry.get("severity") in SEVERITY_RANK
            and entry.get("headline")
        ]
    except Exception:
        return []


def order_weather_notice(latitude, longitude):
    """The single most relevant active heads-up for an order's drop-off,
    or None.

    Serialized onto customer-facing order payloads as the optional
    ``weather_notice`` field: the weather module's server-authored one-liner
    (``text`` = headline, ``detail`` = full message), the severity word
    (``severity_label``) and the valid window (``onset``/``valid_until``).
    Highest severity wins; ties keep the entry expiring last (the weather
    response is ordered valid_until desc). Never raises; None means "no
    field" - shells without the weather module, a disabled master switch
    and quiet weather all look identical to the caller.
    """
    try:
        if not notices_enabled():
            return None
        entries = active_cell_warnings(latitude, longitude)
        if not entries:
            return None
        top = max(
            enumerate(entries),
            key=lambda pair: (
                SEVERITY_RANK.get(pair[1].get("severity"), 0),
                -pair[0],
            ),
        )[1]
        return {
            "text": top.get("headline"),
            "detail": top.get("message"),
            "severity": top.get("severity"),
            "severity_label": top.get("severity_label"),
            "event_class": top.get("event_class"),
            "onset": top.get("onset"),
            "valid_until": top.get("valid_until"),
            "attribution": top.get("attribution"),
        }
    except Exception:
        return None
