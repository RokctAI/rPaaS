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
from frappe.utils import get_datetime, now_datetime

MAX_EVENT_LENGTH = 140
MAX_SESSION_ID_LENGTH = 140
MAX_CONTEXT_LENGTH = 10000


@frappe.whitelist()
def track_event(event: Any, context: Any=None) -> Any:
    """
    Records a client usage event from the frontend as a Client Usage Event
    document. Usage lane only — events are NOT routed into the Brain/error
    pipeline (see log_frontend_error for that lane).
    """
    if frappe.conf.get("app_role") != "tenant":
        frappe.throw(
            "This action can only be performed on a tenant site.",
            title="Action Not Allowed",
        )

    if not event or not isinstance(event, str) or not event.strip():
        return {
            "status": "error",
            "message": "event must be a non-empty string.",
        }

    event = event.strip()
    if len(event) > MAX_EVENT_LENGTH:
        return {
            "status": "error",
            "message": f"event must be at most {MAX_EVENT_LENGTH} characters.",
        }

    try:
        properties = {}
        session_id = None
        timestamp = None

        if context:
            if isinstance(context, str) and len(context) > MAX_CONTEXT_LENGTH:
                context = context[:MAX_CONTEXT_LENGTH]
            try:
                context_data = (
                    json.loads(context) if isinstance(context, str) else context
                )
                if isinstance(context_data, dict):
                    props = context_data.get("properties")
                    if isinstance(props, dict):
                        properties = props
                    session_id = context_data.get("session_id")
                    timestamp = context_data.get("timestamp")
            except json.JSONDecodeError:
                # If context is not valid JSON, keep the raw string so it is
                # not lost.
                properties = {"raw_context": context}

        if session_id is not None:
            session_id = str(session_id)[:MAX_SESSION_ID_LENGTH]

        ts_value = now_datetime()
        if timestamp:
            try:
                ts_value = get_datetime(str(timestamp).replace("Z", "+00:00"))
            except Exception:
                pass

        doc = frappe.new_doc("Client Usage Event")
        doc.event = event
        doc.properties = json.dumps(properties)
        doc.session_id = session_id
        doc.timestamp = ts_value
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "success", "message": "Usage event recorded."}

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Failed to record usage event")
        return {"status": "error", "message": "Failed to record usage event."}
