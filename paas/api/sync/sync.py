# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
import json
from paas.api.utils import api_response


@frappe.whitelist()
def sync_brain_events(events):
    """
    Ingests a list of brain events from the mobile app.
    'events' should be a list of dictionaries.
    """
    if isinstance(events, str):
        try:
            events = json.loads(events)
        except Exception:
            frappe.throw("Invalid events format. Expected JSON.")

    if not isinstance(events, list):
        frappe.throw("Events must be a list.")

    ingested_count = 0
    for event_data in events:
        try:
            # Check for required fields
            if not event_data.get(
                    "source") or not event_data.get("event_type"):
                continue

            doc = frappe.get_doc({
                "doctype": "Brain Event",
                "source": event_data.get("source"),
                "event_type": event_data.get("event_type"),
                "entity_id": event_data.get("entity_id"),
                "entity_type": event_data.get("entity_type"),
                "payload": json.dumps(event_data.get("payload", {})),
                "user": frappe.session.user,
                "timestamp": event_data.get("timestamp") or frappe.utils.now()
            })

            # If shop is provided, use it
            if event_data.get("shop"):
                doc.shop = event_data.get("shop")

            doc.insert(ignore_permissions=True)
            ingested_count += 1
        except Exception as e:
            frappe.log_error(
                f"Brain Event Ingestion Failed: {
                    str(e)}", "sync_brain_events")
            continue

    frappe.db.commit()
    return api_response(
        data={"ingested": ingested_count},
        message=f"Successfully ingested {ingested_count} brain events."
    )
