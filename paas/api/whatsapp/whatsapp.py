from typing import Any, Optional
import frappe


@frappe.whitelist(allow_guest=True)
def flow_endpoint() -> Any:
    """
    Endpoint for WhatsApp Flows.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return {"status": "success"}


@frappe.whitelist(allow_guest=True)
def hook() -> Any:
    """
    Webhook for WhatsApp updates.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return {"status": "success"}
