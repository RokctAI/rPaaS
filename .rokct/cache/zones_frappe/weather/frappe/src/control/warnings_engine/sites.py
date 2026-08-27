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

"""Vulnerable-site registry glue - the sw6 pass (strictly additive).

Disaster-management orgs think in named physical assets - a school, a
clinic, a low-water bridge, a river crossing - not in coordinates. Admins
register such assets as Weather Vulnerable Site rows (standard desk CRUD,
the watch-location house pattern); this module wires the registry into the
EXISTING watch-location/warning/push machinery:

  coverage   ensure_site_cell_covered / ensure_sites_covered upsert the
             site's 0.25 degree grid cell as a Weather Watch Location -
             exactly the get_weather_warnings registration pattern - and
             keep refreshing last_requested_at, so the hourly evaluator
             covers every registered asset's cell and the daily stale sweep
             never drops it. Called from the site doctype controller (on
             insert/update) and from the top of the hourly evaluator run.

  notices    sync_site_notices is called next to push.notify_warning_upsert
             on every ACTIVE warning upsert (evaluator + basin passes). For
             each ENABLED site in the warning's cell it renders one calm,
             site-specific line through messages.render_site_notice (the
             same legal constraint as all end-user copy) and upserts a
             Weather Site Notice row LINKED to the warning record. Notices
             refresh their copy on a severity escalation and otherwise stay
             put; their live window IS the parent warning's (they are only
             ever served alongside an active warning), so no extra sweep.

  serving    active_site_notices is the serve-time join used by the
             control-side get_weather_warnings endpoint: each active
             warning's dict gains a "site_notices" list (marked
             kind="site_notice"), which then flows through the tenant proxy
             and its 10-minute cell cache UNCHANGED - no parallel delivery
             pipeline. The per-warning push body also stays byte-identical
             (clients fetch the cell payload, notices included, exactly as
             today); notices never generate pushes of their own.

Fail-closed everywhere: no registered site (or no registry table at all on
an older shell) means byte-identical pre-sw6 behavior; every entry point is
guaranteed not to raise into its caller (rate-limited admin log at most,
under TITLE_SITES).

Site-config flag (frappe.conf): severe_weather_sites_enabled - MASTER
SWITCH, default ON ("0"/"false"/"no"/"off" disables both the coverage
refresh and notice generation; already-written notices simply stop being
refreshed and expire with their warnings).

All datetimes are UTC (naive), like the rest of the warnings engine.
"""
from __future__ import annotations

import datetime as dt

import frappe
from frappe.utils import get_datetime

from ...warnings_engine import messages
from ...warnings_engine.admin_log import TITLE_SITES, log_admin_error

SITE_DOCTYPE = "Weather Vulnerable Site"
NOTICE_DOCTYPE = "Weather Site Notice"
WATCH_DOCTYPE = "Weather Watch Location"
WARNING_RECORD_DOCTYPE = "Severe Weather Warning"

GRID_STEP = 0.25  # the evaluation grid (see control/api/get_weather_warnings)

#: MASTER SWITCH - default ON; the flag is an off-switch.
CONF_ENABLED = "severe_weather_sites_enabled"
_FALSY = ("0", "false", "no", "off")

#: a site cell's last_requested_at is refreshed at most this often by the
#: hourly pass (mirrors SUBSCRIBER_REFRESH_HOURS - coarse freshness only,
#: the stale cutoff is 30 days).
REFRESH_HOURS = 6


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


def sites_enabled() -> bool:
    try:
        raw = frappe.conf.get(CONF_ENABLED)
        if raw is None:
            return True  # default ON - the flag is an off-switch
        return str(raw).strip().lower() not in _FALSY
    except Exception:
        return False


def grid_key_for(latitude, longitude):
    """Grid-rounded "lat,lng" key for a site's coordinates, or None when the
    coordinates are unusable (same rounding as the serving endpoint)."""
    try:
        lat, lng = float(latitude), float(longitude)
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            return None
    except (TypeError, ValueError):
        return None
    grid_lat = round(lat / GRID_STEP) * GRID_STEP
    grid_lng = round(lng / GRID_STEP) * GRID_STEP
    return f"{grid_lat:.2f},{grid_lng:.2f}"


# --------------------------------------------------------------------------- #
# coverage: a registered site's grid cell is always a live watch location
# --------------------------------------------------------------------------- #

def ensure_site_cell_covered(latitude, longitude, now=None, refresh_hours=0):
    """Upsert the watch location for a site's grid cell; refresh its
    last_requested_at (the get_weather_warnings registration pattern, so the
    hourly evaluator covers the cell and the stale sweep keeps it).

    refresh_hours > 0 throttles the refresh write: an existing row whose
    last_requested_at is younger than that stays untouched (read-only pass).
    Returns the watch-location name, or None on any failure - guaranteed
    never to raise (rate-limited admin log at most).
    """
    try:
        grid_key = grid_key_for(latitude, longitude)
        if not grid_key:
            return None
        lat_s, lng_s = grid_key.split(",")
        now = now or _utcnow()
        existing = frappe.db.get_value(
            WATCH_DOCTYPE, {"grid_key": grid_key},
            ["name", "last_requested_at"], as_dict=True)
        if existing:
            if refresh_hours > 0 and existing.last_requested_at:
                try:
                    last = get_datetime(existing.last_requested_at)
                    if last and now - last < dt.timedelta(hours=refresh_hours):
                        return existing.name  # fresh enough - no write
                except Exception:
                    pass
            frappe.db.set_value(WATCH_DOCTYPE, existing.name,
                                {"last_requested_at": now})
            return existing.name
        doc = frappe.get_doc({
            "doctype": WATCH_DOCTYPE,
            "grid_key": grid_key,
            "latitude": float(lat_s),
            "longitude": float(lng_s),
            "active": 1,
            "last_requested_at": now,
        })
        doc.insert(ignore_permissions=True)
        return doc.name
    except Exception:
        log_admin_error(TITLE_SITES)
        return None


def on_site_saved(doc) -> None:
    """Weather Vulnerable Site controller hook (insert AND update): cover the
    site's grid cell immediately and stamp the watch_location link on the
    row. Never raises - saving a registry row must not fail because coverage
    momentarily could not be arranged (the hourly pass self-heals)."""
    try:
        if not sites_enabled():
            return
        name = ensure_site_cell_covered(doc.latitude, doc.longitude)
        if name and getattr(doc, "watch_location", None) != name:
            frappe.db.set_value(SITE_DOCTYPE, doc.name,
                                {"watch_location": name})
            doc.watch_location = name
    except Exception:
        log_admin_error(TITLE_SITES)


def ensure_sites_covered(now=None) -> int:
    """Hourly (from the top of the evaluator run): keep every ENABLED site's
    grid cell registered and fresh, and heal a stale/missing watch_location
    link (e.g. after a coordinate edit or a bulk import that bypassed the
    controller). Returns how many sites are covered; never raises."""
    if not sites_enabled():
        return 0
    now = now or _utcnow()
    try:
        rows = frappe.get_all(
            SITE_DOCTYPE,
            filters={"enabled": 1},
            fields=["name", "latitude", "longitude", "watch_location"],
        )
    except Exception:
        return 0  # registry absent (pre-migration shell): fail-closed no-op
    if not isinstance(rows, (list, tuple)):
        return 0
    covered = 0
    for row in rows:
        try:
            location = ensure_site_cell_covered(
                row.latitude, row.longitude, now, refresh_hours=REFRESH_HOURS)
            if not location:
                continue
            if row.watch_location != location:
                frappe.db.set_value(SITE_DOCTYPE, row.name,
                                    {"watch_location": location})
            covered += 1
        except Exception:
            log_admin_error(TITLE_SITES)  # one bad site cannot starve the rest
    return covered


# --------------------------------------------------------------------------- #
# notices: one calm site-specific line per (active warning, enabled site)
# --------------------------------------------------------------------------- #

def sync_site_notices(warning_name, location_name, event_class, severity,
                      now=None) -> int:
    """Upsert the per-site notices of one ACTIVE warning upsert.

    Called by the evaluator and the basin pass right after
    push.notify_warning_upsert - the same "ride the upsert" hook point. For
    every enabled site whose watch_location is the warning's cell, renders
    the site line through messages.render_site_notice and upserts the
    (warning, site) Weather Site Notice row; an existing row is rewritten
    only on a severity change (escalation copy). Classes/severities without
    approved site copy (cold_front, the advisory tier) are silently skipped.

    Returns how many notices are in place; guaranteed never to raise, and a
    cell without enabled sites is an exact no-op (fail-closed). A DRILL
    warning record (warnings_engine/drill.py, is_drill=1) never generates
    site notices - and an unreadable drill flag counts as a drill (the same
    fail-closed rule as push).
    """
    try:
        return _sync(warning_name, location_name, event_class, severity, now)
    except Exception:
        log_admin_error(TITLE_SITES)
        return 0


def _sync(warning_name, location_name, event_class, severity, now=None) -> int:
    if not sites_enabled():
        return 0
    # DRILL FENCE (fail-closed): training-exercise records must never name
    # real assets - a drill generating Weather Site Notice rows would leak
    # into the serve-time join exactly like a real warning's notices. The
    # drill runner never calls this module, but the fence holds even if a
    # future caller forwards a drill record here.
    try:
        drill_flag = frappe.db.get_value(WARNING_RECORD_DOCTYPE,
                                         str(warning_name), "is_drill")
    except Exception:
        return 0  # fail closed: no notices without a verdict on the flag
    if str(drill_flag).strip().lower() in ("1", "true"):
        return 0
    try:
        sites = frappe.get_all(
            SITE_DOCTYPE,
            filters={"enabled": 1, "watch_location": str(location_name)},
            fields=["name", "site_name", "site_type", "route_label"],
        )
    except Exception:
        return 0  # registry absent: fail-closed no-op
    if not isinstance(sites, (list, tuple)) or not sites:
        return 0
    now = now or _utcnow()
    count = 0
    for site in sites:
        try:
            rendered = messages.render_site_notice(
                event_class, severity, site.site_name, site.site_type,
                site.route_label)
        except KeyError:
            continue  # no approved site copy for this class/severity
        try:
            fields = {
                "severity": rendered["severity"],
                "headline": rendered["headline"],
                "message": rendered["message"],
                "site_name": site.site_name,
                "site_type": site.site_type,
                "generated_at": now,
            }
            existing = frappe.db.get_value(
                NOTICE_DOCTYPE,
                {"warning": str(warning_name), "vulnerable_site": site.name},
                ["name", "severity"], as_dict=True)
            if existing:
                if existing.severity != rendered["severity"]:
                    frappe.db.set_value(NOTICE_DOCTYPE, existing.name, fields)
                count += 1
                continue
            doc = {
                "doctype": NOTICE_DOCTYPE,
                "warning": str(warning_name),
                "vulnerable_site": site.name,
                "watch_location": str(location_name),
                "event_class": event_class,
            }
            doc.update(fields)
            frappe.get_doc(doc).insert(ignore_permissions=True)
            count += 1
        except Exception:
            log_admin_error(TITLE_SITES)  # one bad site cannot starve the rest
    return count


# --------------------------------------------------------------------------- #
# serving: the endpoint-side join (control/api/get_weather_warnings)
# --------------------------------------------------------------------------- #

def active_site_notices(warning_names) -> dict:
    """Site notices for a set of warning names, keyed by warning name.

    Each notice dict is client-shaped and marked kind="site_notice" so
    consumers can tell it from a plain cell heads-up. Sites disabled after
    a notice was written are filtered out here (disabled sites are silent
    end to end). Fail-closed: {} on any problem, leaving the caller's
    response exactly its pre-sw6 shape.
    """
    names = [str(n) for n in (warning_names or []) if n]
    if not names:
        return {}
    try:
        rows = frappe.get_all(
            NOTICE_DOCTYPE,
            filters={"warning": ["in", names]},
            fields=["name", "warning", "vulnerable_site", "site_name",
                    "site_type", "severity", "headline", "message"],
            order_by="site_name asc",
        )
        if not isinstance(rows, (list, tuple)) or not rows:
            return {}
        enabled_rows = frappe.get_all(
            SITE_DOCTYPE,
            filters={"name": ["in", sorted({r.vulnerable_site for r in rows})],
                     "enabled": 1},
            fields=["name"],
        )
        if not isinstance(enabled_rows, (list, tuple)):
            return {}
        enabled = {r.name for r in enabled_rows}
        out = {}
        for row in rows:
            if row.vulnerable_site not in enabled:
                continue  # site disabled since the notice was written
            out.setdefault(row.warning, []).append({
                "kind": "site_notice",
                "id": row.name,
                "site": row.vulnerable_site,
                "site_name": row.site_name,
                "site_type": row.site_type,
                "severity": row.severity,
                "severity_label": messages.SEVERITY_LABELS.get(
                    row.severity, ""),
                "headline": row.headline,
                "message": row.message,
            })
        return out
    except Exception:
        return {}
