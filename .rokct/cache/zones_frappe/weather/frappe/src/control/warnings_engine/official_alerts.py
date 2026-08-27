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

"""Official-alert relay awareness for the warnings endpoint (SAWS context).

South African legal context: only the national weather service (SAWS) may
issue official severe-weather warnings, which is why every end-user string
this feature produces is heads-up possibility phrasing (see messages.py).
The app ALREADY renders official alerts: the get_weather control-plane proxy
returns a weatherapi.com-shaped payload whose ``alerts.alert`` list the
weather widgets display as-is. This module only makes the two surfaces aware
of each other - it never suppresses, rephrases, or re-issues anything.

What it does, additively, in the get_weather_warnings response path: when
the tenant-side 10-minute cache written by get_weather (cache key
``weather_proxy_<location>``, get_weather.py) holds a payload for this watch
location's ``label`` and that payload carries entries in ``alerts.alert``,

  * the response gains ``"official_alerts_present": true``, and
  * each heads-up ``message`` gets a gentle cross-reference sentence
    pointing at the alerts the app already shows.

STRICTLY CACHE-READ-ONLY: this module never makes an external call and
never triggers a proxy fetch - a cold cache simply means no decoration.
The label -> cache-key mapping mirrors get_weather's own normalisation, so
the relay only activates for cells whose watch-location ``label`` matches
the location string clients pass to get_weather (the design doc's
city<->cell mapping seam). When the cached payload carries its own
coordinates they must sit within MATCH_TOLERANCE_DEG of the grid cell,
guarding against a label that resolves to a far-away city.

Config flag (site config key ``severe_weather_official_alert_relay``):
  unset (default)  relay ON for South African locations only. ZA is resolved
                   from the payload's ``location.country`` field when present
                   (authoritative; "south africa" / "za" / "zaf",
                   case-insensitive); the ZA lat/lng bounding box on the grid
                   cell (lat -35..-22, lng 16..33) is the fallback when the
                   payload has no usable country.
  truthy           relay ON for every location.
  falsy (0, "0", "off", "false", "no") relay OFF everywhere.

Combined-copy cap (wave-2 integration decision): fusion (fusion.py) and the
seasonal note (climatology.py) may each have appended one sentence to a
message in the evaluator. The relay's cross-reference is the LOWEST-priority
extra (fusion > seasonal > relay) and is only appended while the message
carries fewer than two of those sentences, so no message ever accumulates
more than two appended sentences.

Failure contract: any error anywhere returns the response exactly as built
today - no new field, no extra sentence, nothing logged to end users.
Dependency-free in the request path (stdlib + frappe only); the copy-cap
check lazily imports the sibling engine modules' copy constants inside a
guard, and only once a decoration is actually about to happen.
"""
from __future__ import annotations

import frappe

#: site-config key controlling the relay (see module docstring for values).
CONFIG_FLAG = "severe_weather_official_alert_relay"

#: The one cross-reference sentence appended to our heads-up copy. It names
#: SAWS's own artifact ("official weather alert") - our own notices keep
#: their heads-up/notice nouns and never use official warning taxonomy.
CROSS_REFERENCE_LINE = ("An official weather alert is also in effect for your "
                        "area — check the weather alerts in the app.")

#: South Africa bounding box (generous, mainland) - the fallback ZA test
#: when the cached payload has no usable location.country field.
ZA_LAT_RANGE = (-35.0, -22.0)
ZA_LNG_RANGE = (16.0, 33.0)

#: accepted spellings of the payload's location.country for South Africa.
ZA_COUNTRY_WORDS = {"south africa", "za", "zaf"}

#: cached payload accepted only when its own coordinates sit within this
#: many degrees of the grid cell (3 grid steps) - see module docstring.
MATCH_TOLERANCE_DEG = 0.75

_FALSY_STRINGS = {"", "0", "false", "off", "no"}

#: at most this many extra sentences (fusion + seasonal + relay combined) may
#: ever ride on one approved message; the relay is the lowest-priority one.
MAX_APPENDED_SENTENCES = 2


def _appended_extra_count(message: str) -> int:
    """How many wave-2 extra sentences the stored message already carries.

    Recognition is by the appending modules' own copy constants (fusion
    appends at most one message sentence - timing or softening; the seasonal
    note is at most one more). A module that cannot be imported cannot have
    appended its sentence either (same install), so its contribution safely
    counts as zero.
    """
    count = 0
    try:
        from . import fusion
        markers = [tmpl.split("{when}")[0].strip()
                   for tmpl in fusion.TIMING_MESSAGE_SUFFIX.values()]
        markers.append(fusion.SOFTEN_MESSAGE_SUFFIX.strip())
        if any(marker and marker in message for marker in markers):
            count += 1
    except Exception:
        pass
    try:
        from . import climatology
        if any(note and note in message
               for note in climatology.NOTE_SENTENCES):
            count += 1
    except Exception:
        pass
    return count


def proxy_cache_key(label: str) -> str:
    """The exact tenant cache key get_weather.py writes for a location."""
    return f"weather_proxy_{label.lower().replace(' ', '_')}"


def _cached_forecast_payload(label):
    """The 10-min-cached get_weather payload for this label, or None.

    Cache read only - never an external call, never a proxy fetch.
    """
    payload = frappe.cache().get_value(proxy_cache_key(label))
    return payload if isinstance(payload, dict) else None


def _payload_location(payload: dict) -> dict:
    location = payload.get("location")
    return location if isinstance(location, dict) else {}


def _matches_cell(payload: dict, grid_lat, grid_lng) -> bool:
    """True when the payload's own coordinates are near the grid cell.

    Missing or unparseable payload coordinates are accepted (the payload was
    cached for this cell's own label); present-and-far coordinates reject.
    """
    location = _payload_location(payload)
    try:
        lat = float(location.get("lat"))
        lng = float(location.get("lon"))
    except (TypeError, ValueError):
        return True
    return (abs(lat - float(grid_lat)) <= MATCH_TOLERANCE_DEG
            and abs(lng - float(grid_lng)) <= MATCH_TOLERANCE_DEG)


def _active_official_alerts(payload: dict) -> list:
    """Non-empty dict entries of alerts.alert; [] for absent/malformed."""
    alerts = payload.get("alerts")
    if not isinstance(alerts, dict):
        return []
    entries = alerts.get("alert")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict) and entry]


def _is_za_location(payload: dict, grid_lat, grid_lng) -> bool:
    """ZA resolution: payload country field first, bounding box fallback."""
    country = _payload_location(payload).get("country")
    if isinstance(country, str) and country.strip():
        return country.strip().lower() in ZA_COUNTRY_WORDS
    try:
        lat, lng = float(grid_lat), float(grid_lng)
    except (TypeError, ValueError):
        return False
    return (ZA_LAT_RANGE[0] <= lat <= ZA_LAT_RANGE[1]
            and ZA_LNG_RANGE[0] <= lng <= ZA_LNG_RANGE[1])


def _relay_enabled(payload: dict, grid_lat, grid_lng) -> bool:
    """Config-flag gate: unset -> ZA-only; truthy -> everywhere; falsy -> off."""
    flag = frappe.conf.get(CONFIG_FLAG)
    if flag is not None:
        if isinstance(flag, str):
            return flag.strip().lower() not in _FALSY_STRINGS
        return bool(flag)
    return _is_za_location(payload, grid_lat, grid_lng)


def apply_official_alert_relay(response, grid_lat, grid_lng, label):
    """Decorate a get_weather_warnings response with official-alert awareness.

    Purely additive: sets ``official_alerts_present`` and appends the
    cross-reference sentence to each heads-up message, only when the cached
    forecast payload for ``label`` carries active official alerts and the
    relay is enabled for this location. On any error, cold cache, missing
    label, disabled flag, or absent alerts the response is returned exactly
    as passed in - byte-identical to today's behavior.
    """
    try:
        if not isinstance(response, dict) or not label:
            return response
        payload = _cached_forecast_payload(label)
        if not payload:
            return response
        if not _matches_cell(payload, grid_lat, grid_lng):
            return response
        if not _active_official_alerts(payload):
            return response
        if not _relay_enabled(payload, grid_lat, grid_lng):
            return response
        decorated = []
        for item in response.get("warnings") or []:
            entry = dict(item)
            message = entry.get("message")
            if (isinstance(message, str) and message
                    and CROSS_REFERENCE_LINE not in message
                    and _appended_extra_count(message)
                    < MAX_APPENDED_SENTENCES):
                entry["message"] = message.rstrip() + " " + CROSS_REFERENCE_LINE
            decorated.append(entry)
        response["warnings"] = decorated
        response["official_alerts_present"] = True
        return response
    except Exception:
        return response
