from typing import Any, Optional
# Tenant context: session.user validation
import frappe
import json


@frappe.whitelist()
def create_faq(data: Any) -> Any:
    """
    Creates a new FAQ.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc({"doctype": "FAQ", **data})
    doc.insert()
    return doc.as_dict()


@frappe.whitelist(allow_guest=True)
def get_faqs(type: Any=None) -> Any:
    """
    Retrieves FAQs, optionally filtered by type.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    filters = {"active": 1}
    if type:
        filters["type"] = type

    return frappe.get_list(
        "FAQ", filters=filters, fields=["name", "question", "answer", "type"]
    )


@frappe.whitelist()
def update_faq(name: Any, data: Any) -> Any:
    """
    Updates an FAQ.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("FAQ", name)
    doc.update(data)
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def delete_faq(name: Any) -> Any:
    """
    Deletes an FAQ.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    frappe.delete_doc("FAQ", name)
    return {"status": "success"}
