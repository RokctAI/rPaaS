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

"""CONTROL-side ADMIN endpoint: the vulnerable-site notice board (sw6).

The Weather Vulnerable Site registry itself is administered by standard
desk doctype CRUD - the house pattern (Weather Watch Location's "admins may
add or deactivate rows here"); no bespoke create/update endpoints exist or
are needed. This endpoint is the QUERY surface an admin dashboard reads:
every site notice (warnings_engine/sites.py) joined with its parent
warning's live state, so a disaster-management admin sees at a glance which
registered assets currently have an active heads-up against them.

System Manager only, read-only. Internal errors are admin-logged
(rate-limited, TITLE_SITES) and reported in-band as {"error": true, ...} -
the endpoint never leaks a traceback. All datetimes are UTC.
"""
from __future__ import annotations

import datetime as dt

import frappe
from frappe.utils import cint

from ....warnings_engine.admin_log import TITLE_SITES, log_admin_error
from ....warnings_engine.messages import SEVERITY_LABELS

NOTICE_DOCTYPE = "Weather Site Notice"
WARNING_DOCTYPE = "Severe Weather Warning"

MAX_LIMIT = 500
DEFAULT_LIMIT = 200


def _require_system_manager():
    """Admin surface only: any caller without System Manager is refused."""
    roles = set(frappe.get_roles())
    if "System Manager" not in roles:
        raise frappe.PermissionError(
            "get_site_notices is an admin surface (System Manager only)")


def _iso_utc(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = frappe.utils.get_datetime(value)
    return value.replace(microsecond=0).isoformat() + "Z"


@frappe.whitelist()
def get_site_notices(site=None, status="active", limit=None):
    """Site notices joined with their parent warning's live state.

    site: optional Weather Vulnerable Site name to filter on.
    status: "active" (default - only notices whose parent warning is active
            and still valid) or "all" (full history, newest first).
    limit: page size, default 200, capped at 500.
    """
    _require_system_manager()
    try:
        return _build(site, status, limit)
    except Exception:
        log_admin_error(TITLE_SITES)
        return {"admin_only": True, "error": True, "notices": []}


def _build(site, status, limit) -> dict:
    now = dt.datetime.utcnow().replace(microsecond=0)
    page = min(max(cint(limit) or DEFAULT_LIMIT, 1), MAX_LIMIT)
    filters = {}
    if site:
        filters["vulnerable_site"] = str(site)
    rows = frappe.get_all(
        NOTICE_DOCTYPE,
        filters=filters,
        fields=["name", "warning", "vulnerable_site", "watch_location",
                "event_class", "site_name", "site_type", "severity",
                "headline", "message", "generated_at"],
        order_by="generated_at desc",
        limit_page_length=page,
    )
    warning_names = sorted({r.warning for r in rows if r.warning})
    warning_state = {}
    if warning_names:
        for w in frappe.get_all(
                WARNING_DOCTYPE,
                filters={"name": ["in", warning_names]},
                fields=["name", "status", "valid_until"]):
            warning_state[w.name] = w
    notices = []
    for row in rows:
        state = warning_state.get(row.warning)
        warning_status = state.status if state else None
        valid_until = state.valid_until if state else None
        live = bool(state and warning_status == "active" and valid_until
                    and frappe.utils.get_datetime(valid_until) > now)
        if str(status or "active") == "active" and not live:
            continue
        notices.append({
            "id": row.name,
            "kind": "site_notice",
            "warning": row.warning,
            "warning_status": warning_status,
            "live": live,
            "valid_until": _iso_utc(valid_until),
            "site": row.vulnerable_site,
            "site_name": row.site_name,
            "site_type": row.site_type,
            "watch_location": row.watch_location,
            "event_class": row.event_class,
            "severity": row.severity,
            "severity_label": SEVERITY_LABELS.get(row.severity, ""),
            "headline": row.headline,
            "message": row.message,
            "generated_at": _iso_utc(row.generated_at),
        })
    return {
        "admin_only": True,
        "generated_at": _iso_utc(now),
        "notices": notices,
    }
