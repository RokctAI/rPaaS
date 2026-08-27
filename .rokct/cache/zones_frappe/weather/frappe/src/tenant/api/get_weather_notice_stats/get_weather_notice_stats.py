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

"""TENANT-side admin telemetry: per-warning delivery/ack aggregates (sw6).

The "did they actually see it?" number: for each warning pushed on this
tenant, how many pushes went out, how many were acknowledged at each level
(delivered/seen/opened), the ack percentage, and the median minutes from
push to first "seen" - e.g. "sent 41, 73% acked, median 12 minutes to
seen". Aggregation lives tenant-side because the Weather Notice Delivery
ledger is tenant-side (per-subscriber state never leaves the tenant).

System Manager only (the retraining-report gating pattern); read-only;
internal errors are admin-logged (rate-limited) and reported in-band -
never a traceback.
"""
from __future__ import annotations

import frappe

from ....warnings_engine.admin_log import TITLE_ACK, log_admin_error
from ... import delivery

#: at most this many ledger rows are aggregated per call (newest pushes
#: first) - plenty for the admin view, bounded for the DB.
MAX_ROWS = 20000


def _require_system_manager():
    """Admin telemetry only: any caller without System Manager is refused."""
    roles = set(frappe.get_roles())
    if "System Manager" not in roles:
        raise frappe.PermissionError(
            "get_weather_notice_stats is admin telemetry "
            "(System Manager only)")


def _fetch_rows(warning_id=None) -> list:
    filters = {"kind": delivery.KIND_SUBSCRIBER}
    if warning_id:
        filters["warning_id"] = str(warning_id).strip()
    return frappe.get_all(
        delivery.DELIVERY_DOCTYPE,
        filters=filters,
        fields=["warning_id", "watch_location", "event_class", "severity",
                "push_sent_at", "acked_event", "acked_at", "seen_at"],
        order_by="push_sent_at desc",
        limit_page_length=MAX_ROWS,
    )


def _whitelist(fn):
    return frappe.whitelist()(fn) if frappe is not None else fn


@_whitelist
def get_weather_notice_stats(warning_id=None):
    """Delivery-assurance aggregates per warning (System Manager only).

    warning_id: optional filter to one warning; omitted = every warning
    with ledger rows, newest push first.
    """
    _require_system_manager()
    try:
        return {
            "admin_only": True,
            "warnings": delivery.build_stats(_fetch_rows(warning_id)),
        }
    except Exception:
        log_admin_error(TITLE_ACK)
        return {
            "admin_only": True,
            "error": True,
            "warnings": [],
        }
