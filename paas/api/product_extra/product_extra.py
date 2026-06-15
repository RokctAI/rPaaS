from typing import Any, Optional
# Tenant context: session.user validation
import frappe
import json

# --- Product Extra Group APIs ---


@frappe.whitelist()
def create_extra_group(data: Any) -> Any:
    """
    Creates a new Product Extra Group.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc({"doctype": "Product Extra Group", **data})
    doc.insert()
    return doc.as_dict()


@frappe.whitelist()
def get_extra_groups(shop_id: Any=None) -> Any:
    """
    Retrieves Extra Groups, optionally filtered by shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    filters = {}
    if shop_id:
        filters["shop"] = shop_id

    return frappe.get_list(
        "Product Extra Group", filters=filters, fields=["*"]
    )


@frappe.whitelist()
def update_extra_group(name: Any, data: Any) -> Any:
    """
    Updates an Extra Group.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Product Extra Group", name)
    doc.update(data)
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def delete_extra_group(name: Any) -> Any:
    """
    Deletes an Extra Group.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    frappe.delete_doc("Product Extra Group", name)
    return {"status": "success"}


# --- Product Extra Value APIs ---


@frappe.whitelist()
def create_extra_value(data: Any) -> Any:
    """
    Creates a new Product Extra Value.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc({"doctype": "Product Extra Value", **data})
    doc.insert()
    return doc.as_dict()


@frappe.whitelist()
def get_extra_values(group_id: Any) -> Any:
    """
    Retrieves Extra Values for a specific group.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return frappe.get_list(
        "Product Extra Value", filters={"extra_group": group_id}, fields=["*"]
    )


@frappe.whitelist()
def update_extra_value(name: Any, data: Any) -> Any:
    """
    Updates an Extra Value.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Product Extra Value", name)
    doc.update(data)
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def delete_extra_value(name: Any) -> Any:
    """
    Deletes an Extra Value.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    frappe.delete_doc("Product Extra Value", name)
    return {"status": "success"}
