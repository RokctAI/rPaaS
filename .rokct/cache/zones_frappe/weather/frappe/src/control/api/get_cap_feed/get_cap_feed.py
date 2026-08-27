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

"""CONTROL-side ADMIN endpoint: currently-active severe-weather heads-ups as
an OASIS CAP 1.2 feed (sw6).

CAP (Common Alerting Protocol 1.2, the OASIS standard consumed by official
agencies and alert aggregators) is the interchange format; this endpoint
renders every currently-active Severe Weather Warning record as one CAP
``<alert>`` element, wrapped in a minimal Atom envelope (the index-feed
convention aggregators expect: one ``<entry>`` per alert, the alert embedded
as ``<content type="application/cap+xml">``).

ACCESS: authenticated, System Manager only (an API-key principal carrying the
System Manager role passes the same gate). This is deliberately NOT a public
unauthenticated feed - whether it should ever be exposed publicly is a
product/legal decision above this module (see the PR that introduced it).

Tier mapping (internal severity enum -> CAP protocol tokens; CAP's own enum
values such as severity "Severe" are protocol vocabulary, not end-user copy):

  internal    urgency    severity   certainty   rationale
  ---------   --------   --------   ---------   --------------------------------
  advisory    Future     Minor      Possible    neighbor-propagated soft notice,
                                                strictly below heads_up
  heads_up    Expected   Moderate   Possible    early notice - "possible"
                                                phrasing, frozen detector tier 2
  warning     Expected   Severe     Likely      strongest tier - frozen detector
                                                tier 3 ("likely"/"expected" copy)

Other structural choices:
  * category is always Met; status is Actual (Exercise for drill records,
    which appear ONLY when the caller explicitly passes include_drills);
    msgType Alert; scope Public (a protocol token describing the intended
    audience of the MESSAGE - actual distribution stays gated by the
    authentication above).
  * effective = issued_at, onset = onset, expires = valid_until - the
    record's own validity window, all UTC (CAP requires an explicit offset,
    so timestamps are serialized as ...+00:00; the spec disallows "Z").
  * area: one <circle> covering the record's 0.25 degree evaluation grid
    cell - center at the cell coordinates, radius the cell's half-diagonal
    (latitude-dependent, ~15-20 km).
  * headline/description carry EXACTLY the calm end-user strings persisted
    on the record by the messages layer (src/warnings_engine/messages.py):
    heads-up possibility phrasing only - the word "warning" and official
    level taxonomy never appear in any end-user-facing text field, and the
    <event> names below follow the same rule.
  * Open-Meteo attribution (CC-BY-4.0) rides in an <info>/<parameter> named
    "attribution" on every alert, and in the Atom <rights> element.
  * identifier/sent/sender are deterministic functions of record data (no
    wall-clock reads per alert), so the same records always render the same
    alerts; only the Atom envelope's <updated> falls back to "now" when the
    feed is empty.

The builder half (records in, XML out) is frappe-free and pure - the offline
tests feed it fixture records and assert structure, mapping, and wording.
"""
from __future__ import annotations

import datetime as dt
import math
from xml.etree import ElementTree as ET

try:  # composed into the control product: frappe + common admin logging
    import frappe
    from ....warnings_engine.admin_log import TITLE_CAP_FEED, log_admin_error
except ImportError:  # standalone/offline reuse
    frappe = None

    def log_admin_error(title, message=None):  # noqa: D103 - stand-in
        pass

    TITLE_CAP_FEED = "SevereWeather: CAP feed error"

WARNING_DOCTYPE = "Severe Weather Warning"
WATCH_DOCTYPE = "Weather Watch Location"

CAP_NS = "urn:oasis:names:tc:emergency:cap:1.2"
ATOM_NS = "http://www.w3.org/2005/Atom"

#: sender identifier carried in every alert; overridable per site
#: ("severe_weather_cap_sender" in site config).
DEFAULT_SENDER = "severe-weather.rokct.ai"
CONF_SENDER = "severe_weather_cap_sender"

#: internal severity enum -> CAP urgency/severity/certainty (see module
#: docstring for the rationale table).
SEVERITY_TO_CAP = {
    "advisory": {"urgency": "Future", "severity": "Minor",
                 "certainty": "Possible"},
    "heads_up": {"urgency": "Expected", "severity": "Moderate",
                 "certainty": "Possible"},
    "warning": {"urgency": "Expected", "severity": "Severe",
                "certainty": "Likely"},
}

#: <event> per event class - end-user-facing text, so the same wording rule
#: as messages.py applies: calm nouns, never official warning taxonomy.
EVENT_NAMES = {
    "flash_flood": "Flash flooding",
    "flood": "Flooding",
    "destructive_wind": "Damaging winds",
    "tornado": "Severe storms",
    "cold_front": "Cool change",
    "upstream_flood": "Rising river levels",
}

#: <senderName> - also end-user-facing text (displayed by CAP consumers).
SENDER_NAME = "Rokct weather heads-up service"

FEED_TITLE = "Severe weather heads-ups"

GRID_STEP = 0.25  # the evaluation grid (see warnings_engine/sources)

#: km per degree of latitude (spherical mean) - good to <1% for a cell radius.
KM_PER_DEG_LAT = 111.2


# --------------------------------------------------------------------------- #
# pure builder (no frappe) - fixture-tested offline
# --------------------------------------------------------------------------- #

def cap_timestamp(value) -> str | None:
    """Naive-UTC datetime (or ISO string) -> CAP dateTime with an explicit
    +00:00 offset (CAP 1.2 requires the offset form and disallows "Z")."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if value.tzinfo is not None:
        value = value.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return value.replace(microsecond=0).isoformat() + "+00:00"


def cell_radius_km(latitude: float) -> float:
    """Radius (km) of the circle covering a 0.25 degree grid cell centered
    at this latitude: the cell's half-diagonal, so no part of the cell falls
    outside the circle."""
    half = GRID_STEP / 2.0
    dlat_km = half * KM_PER_DEG_LAT
    dlon_km = half * KM_PER_DEG_LAT * abs(math.cos(math.radians(latitude)))
    return round(math.hypot(dlat_km, dlon_km), 1)


def alert_identifier(sender: str, record: dict) -> str:
    """Deterministic CAP identifier: sender + record name + issue time."""
    issued = record.get("issued_at")
    stamp = ""
    ts = cap_timestamp(issued)
    if ts:
        stamp = "." + ts[:19].replace("-", "").replace(":", "")
    return f"{sender}.{record['name']}{stamp}"


def _sub(parent, tag: str, text=None):
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = str(text)
    return el


def build_alert(record: dict, sender: str = DEFAULT_SENDER) -> ET.Element:
    """One Severe Weather Warning record -> one CAP 1.2 <alert> Element.

    record: dict with name, event_class, severity, headline, message, onset,
    valid_until, issued_at, latitude, longitude, optional label/is_drill.
    Raises KeyError/ValueError on a record too malformed to render - the
    endpoint skips such records rather than emitting a broken alert.
    """
    severity = record["severity"]
    mapping = SEVERITY_TO_CAP[severity]  # KeyError -> caller skips
    lat = float(record["latitude"])
    lon = float(record["longitude"])

    alert = ET.Element(f"{{{CAP_NS}}}alert")
    _sub(alert, f"{{{CAP_NS}}}identifier", alert_identifier(sender, record))
    _sub(alert, f"{{{CAP_NS}}}sender", sender)
    sent = cap_timestamp(record.get("issued_at"))
    if not sent:
        raise ValueError(f"record {record.get('name')} has no issued_at")
    _sub(alert, f"{{{CAP_NS}}}sent", sent)
    _sub(alert, f"{{{CAP_NS}}}status",
         "Exercise" if record.get("is_drill") else "Actual")
    _sub(alert, f"{{{CAP_NS}}}msgType", "Alert")
    _sub(alert, f"{{{CAP_NS}}}scope", "Public")

    info = _sub(alert, f"{{{CAP_NS}}}info")
    _sub(info, f"{{{CAP_NS}}}language", "en")
    _sub(info, f"{{{CAP_NS}}}category", "Met")
    _sub(info, f"{{{CAP_NS}}}event",
         EVENT_NAMES.get(record["event_class"], "Notable weather"))
    _sub(info, f"{{{CAP_NS}}}urgency", mapping["urgency"])
    _sub(info, f"{{{CAP_NS}}}severity", mapping["severity"])
    _sub(info, f"{{{CAP_NS}}}certainty", mapping["certainty"])
    effective = cap_timestamp(record.get("issued_at"))
    if effective:
        _sub(info, f"{{{CAP_NS}}}effective", effective)
    onset = cap_timestamp(record.get("onset"))
    if onset:
        _sub(info, f"{{{CAP_NS}}}onset", onset)
    expires = cap_timestamp(record.get("valid_until"))
    if expires:
        _sub(info, f"{{{CAP_NS}}}expires", expires)
    _sub(info, f"{{{CAP_NS}}}senderName", SENDER_NAME)
    if record.get("headline"):
        _sub(info, f"{{{CAP_NS}}}headline", record["headline"])
    if record.get("message"):
        _sub(info, f"{{{CAP_NS}}}description", record["message"])
    parameter = _sub(info, f"{{{CAP_NS}}}parameter")
    _sub(parameter, f"{{{CAP_NS}}}valueName", "attribution")
    _sub(parameter, f"{{{CAP_NS}}}value", _attribution())

    area = _sub(info, f"{{{CAP_NS}}}area")
    _sub(area, f"{{{CAP_NS}}}areaDesc",
         record.get("label") or f"grid cell {lat:.2f},{lon:.2f}")
    _sub(area, f"{{{CAP_NS}}}circle",
         f"{lat:.2f},{lon:.2f} {cell_radius_km(lat)}")
    return alert


def _attribution() -> str:
    """The Open-Meteo CC-BY-4.0 attribution from the messages layer (single
    source of truth); a stdlib-only fallback keeps the builder importable
    standalone."""
    try:
        from ....warnings_engine.messages import ATTRIBUTION
        return ATTRIBUTION
    except ImportError:
        return "Weather data by Open-Meteo.com"


def build_cap_feed(records: list, sender: str = DEFAULT_SENDER,
                   now: dt.datetime | None = None) -> str:
    """Records (dicts, see build_alert) -> Atom-wrapped CAP 1.2 feed XML.

    Deterministic for a fixed record set: alerts are ordered by record name,
    every alert field derives from record data, and the feed <updated> is
    the newest issued_at (falling back to `now`/utcnow only when the feed is
    empty). Malformed records are skipped, never allowed to break the feed.
    """
    ET.register_namespace("", ATOM_NS)
    ET.register_namespace("cap", CAP_NS)
    feed = ET.Element(f"{{{ATOM_NS}}}feed")
    _sub(feed, f"{{{ATOM_NS}}}id", f"urn:rokct:cap-feed:{sender}")
    _sub(feed, f"{{{ATOM_NS}}}title", FEED_TITLE)
    _sub(feed, f"{{{ATOM_NS}}}rights", _attribution())

    entries = []
    newest = None
    for record in sorted(records, key=lambda r: str(r.get("name"))):
        try:
            alert = build_alert(record, sender=sender)
        except Exception:
            log_admin_error(TITLE_CAP_FEED,
                            f"CAP feed skipped malformed record "
                            f"{record.get('name')!r}")
            continue
        sent = alert.find(f"{{{CAP_NS}}}sent").text
        newest = max(newest, sent) if newest else sent
        entries.append((alert, sent))

    updated = newest or cap_timestamp(now or dt.datetime.utcnow())
    _sub(feed, f"{{{ATOM_NS}}}updated", updated)

    for alert, sent in entries:
        entry = _sub(feed, f"{{{ATOM_NS}}}entry")
        _sub(entry, f"{{{ATOM_NS}}}id",
             "urn:rokct:cap:" + alert.find(f"{{{CAP_NS}}}identifier").text)
        title = alert.find(
            f"{{{CAP_NS}}}info/{{{CAP_NS}}}headline")
        _sub(entry, f"{{{ATOM_NS}}}title",
             title.text if title is not None else FEED_TITLE)
        _sub(entry, f"{{{ATOM_NS}}}updated", sent)
        content = _sub(entry, f"{{{ATOM_NS}}}content")
        content.set("type", "application/cap+xml")
        content.append(alert)

    return ('<?xml version="1.0" encoding="UTF-8"?>'
            + ET.tostring(feed, encoding="unicode"))


# --------------------------------------------------------------------------- #
# the whitelisted endpoint (frappe-side)
# --------------------------------------------------------------------------- #

def _require_system_manager():
    """Authenticated admin surface: any caller without the System Manager
    role (session or API-key principal alike) is refused."""
    roles = set(frappe.get_roles())
    if "System Manager" not in roles:
        raise frappe.PermissionError(
            "get_cap_feed is an authenticated admin feed (System Manager "
            "only); public exposure is a separate product decision")


def _truthy(value) -> bool:
    """Conservative flag parse: only an explicit yes counts (fail closed)."""
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _fetch_active_records(include_drills: bool) -> list:
    now = dt.datetime.utcnow().replace(microsecond=0)
    filters = {"status": "active", "valid_until": [">", now]}
    if not include_drills:
        # drill fence (fail-closed default): exercise records appear only
        # on explicit request - and then as CAP status Exercise
        filters["is_drill"] = ["!=", 1]
    rows = frappe.get_all(
        WARNING_DOCTYPE,
        filters=filters,
        fields=["name", "watch_location", "event_class", "severity",
                "headline", "message", "onset", "valid_until", "issued_at",
                "is_drill"],
        limit_page_length=0,
    )
    if not rows:
        return []
    cells = {}
    for loc in frappe.get_all(
            WATCH_DOCTYPE,
            filters={"name": ["in", sorted({r.watch_location for r in rows})]},
            fields=["name", "latitude", "longitude", "label"],
            limit_page_length=0):
        cells[loc.name] = loc
    records = []
    for row in rows:
        cell = cells.get(row.watch_location)
        if cell is None:
            continue  # orphaned record: no coordinates, no alert
        record = dict(row)
        record["latitude"] = cell.latitude
        record["longitude"] = cell.longitude
        record["label"] = cell.label
        records.append(record)
    return records


def _whitelist(fn):
    return frappe.whitelist()(fn) if frappe is not None else fn


@_whitelist
def get_cap_feed(include_drills=None):
    """Currently-active heads-ups as an Atom-wrapped OASIS CAP 1.2 feed.

    System Manager only; read-only. Returns the XML document as a string.
    include_drills: only an explicitly truthy value adds drill records
    (rendered with CAP status Exercise). Internal errors are admin-logged
    (rate-limited) and yield a valid empty feed - never a traceback.
    """
    _require_system_manager()
    try:
        sender = ((frappe.conf.get(CONF_SENDER) or "").strip()
                  or DEFAULT_SENDER)
        records = _fetch_active_records(_truthy(include_drills))
        xml = build_cap_feed(records, sender=sender)
    except Exception:
        log_admin_error(TITLE_CAP_FEED)
        xml = build_cap_feed([], sender=DEFAULT_SENDER)
    try:  # serve as XML when running under a real bench request
        frappe.local.response["content_type"] = "application/xml"
    except Exception:
        pass
    return xml
