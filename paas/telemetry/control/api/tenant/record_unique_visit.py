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

import frappe
from frappe.utils import nowdate


@frappe.whitelist(allow_guest=True)
def record_unique_visit(
    visitor_id, client_ip=None, user_id=None, app_version=None, os=None, os_version=None
):
    """
    Records a unique visit on the control panel.
    Deduplicates using visitor IP + visitor_id in a Redis Set.
    Also logs user identification and device metadata.
    """
    if not visitor_id:
        return {"status": "error", "message": "Missing visitor_id"}

    ip = client_ip or frappe.local.request.ip or "unknown"
    date_str = nowdate()
    cache_key = f"unique_visitors_control:{date_str}"

    frappe.cache().sadd(cache_key, f"{ip}:{visitor_id}")
    frappe.cache().expire(cache_key, 172800)

    metadata = f"OS: {os or 'unknown'}, OS Version: {os_version or 'unknown'}, App Version: {app_version or 'unknown'}"
    frappe.log_error(
        message=f"Telemetry: Visitor {visitor_id} from IP {ip}. Metadata: {metadata}. Identified as user {user_id or 'guest'}",
        title="Visitor Telemetry",
    )

    return {"status": "success"}
