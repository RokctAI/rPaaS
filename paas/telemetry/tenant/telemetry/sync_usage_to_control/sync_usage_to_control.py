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

from typing import Any, Optional
import frappe
import json
from frappe.utils import nowdate
from paas.core.helpers import *


def sync_usage_to_control():
    """
    Scheduled task to sync yesterday's usage event counts (per event) to the
    control panel. Mirrors sync_visitors_to_control.
    """
    try:
        # Check if tracking is disabled/rejected for this tenant
        try:
            sub_details = get_subscription_details()
            if sub_details and sub_details.get("reject_visitor_tracking"):
                return
        except Exception:
            pass

        from frappe.utils.data import add_days
        yesterday = add_days(nowdate(), -1)

        rows = frappe.get_all(
            "Client Usage Event",
            filters={
                "timestamp": ["between", [f"{yesterday} 00:00:00", f"{yesterday} 23:59:59"]],
            },
            fields=["event"],
        )
        if not rows:
            return

        usage_counts = {}
        for row in rows:
            usage_counts[row.event] = usage_counts.get(row.event, 0) + 1

        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        if not control_plane_url or not api_secret:
            return

        import requests
        scheme = frappe.conf.get("control_plane_scheme", "https")
        api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.tenant.report_tenant_usage"

        trace_id = frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else "usage-sync-trace"
        headers = {
            "X-Rokct-Secret": api_secret,
            "X-Rokct-Tenant": frappe.local.site,
            "x-trace-id": trace_id or ""
        }
        data = {
            "date": yesterday,
            "usage_counts": json.dumps(usage_counts)
        }

        response = requests.post(api_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

    except Exception as e:
        frappe.log_error(f"Failed to sync usage counts to control panel: {e}\n{frappe.get_traceback()}", "Usage Sync Failed")
