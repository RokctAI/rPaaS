from typing import Any, Optional
import frappe
from paas.api.delivery_man.delivery_man import (
    get_deliveryman_orders as _get_orders,
)


@frappe.whitelist()
def get_driver_orders_paginate(limit_start: Any=0, limit_page_length: Any=20) -> Any:
    """
    Get driver orders paginate API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return _get_orders(limit_start, limit_page_length)


@frappe.whitelist()
def fetch_current_order() -> Any:
    """
    Fetch current order API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized")

    order = frappe.get_list(
        "Order",
        filters={
            "deliveryman": user,
            "status": ["in", ["On a Way", "Accepted"]],
        },
        fields=["name", "shop", "total_price", "status", "creation"],
        limit=1,
    )
    if order:
        doc = frappe.get_doc("Order", order[0].name)
        return {"data": doc.as_dict()}
    return {"data": {}}


@frappe.whitelist()
def set_current_order(order_id: Any) -> Any:
    """
    Set current order API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if frappe.db.exists("Order", order_id):
        doc = frappe.get_doc("Order", order_id)
        if doc.deliveryman == user:
            doc.status = "On a Way"
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def attach_order_to_me(order_id: Any) -> Any:
    """
    Attach order to me API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if frappe.db.exists("Order", order_id):
        doc = frappe.get_doc("Order", order_id)
        if not doc.deliveryman:
            doc.deliveryman = user
            doc.status = "Accepted"
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def update_driver_order_status(order_id: Any, status: Any) -> Any:
    """
    Update driver order status API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if frappe.db.exists("Order", order_id):
        doc = frappe.get_doc("Order", order_id)
        if doc.deliveryman == frappe.session.user:
            doc.status = status
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def upload_order_image(order_id: Any, image_url: Any=None) -> Any:
    """
    Upload order image API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not image_url:
        return {"status": False}
    if frappe.db.exists("Order", order_id):
        doc = frappe.get_doc("Order", order_id)
        if hasattr(doc, "delivery_photo"):
            doc.delivery_photo = image_url
            doc.save(ignore_permissions=True)
            return {"status": True}
    return {"status": True}
