from typing import Any, Optional
import frappe
import json
from paas.api.delivery_man.delivery_man import (
    get_deliveryman_statistics as _get_deliveryman_statistics,
)


@frappe.whitelist()
def get_driver_statistics() -> Any:
    """
    Get driver statistics API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return _get_deliveryman_statistics()


@frappe.whitelist()
def update_location(lat: Any=None, lng: Any=None) -> Any:
    """
    Update location API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized")

    if not frappe.db.exists("Deliveryman Settings", {"user": user}):
        doc = frappe.new_doc("Deliveryman Settings")
        doc.user = user
        doc.insert(ignore_permissions=True)
    else:
        doc = frappe.get_doc("Deliveryman Settings", {"user": user})

    if hasattr(doc, "latitude") and hasattr(doc, "longitude"):
        doc.latitude = lat
        doc.longitude = lng
        doc.save(ignore_permissions=True)
    return {"status": True, "message": "Location updated"}


@frappe.whitelist()
def set_online_status() -> Any:
    """
    Set online status API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized")

    if frappe.db.exists("Deliveryman Settings", {"user": user}):
        doc = frappe.get_doc("Deliveryman Settings", {"user": user})
        doc.online = 1 if not doc.online else 0
        doc.save(ignore_permissions=True)
        return {"status": True, "online": doc.online}
    return {"status": False}


@frappe.whitelist()
def get_car_requests() -> Any:
    """
    Get car requests API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return []


@frappe.whitelist()
def update_car_info(car_model: Any=None, car_number: Any=None, color: Any=None) -> Any:
    """
    Update car info API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if frappe.db.exists("Deliveryman Settings", {"user": user}):
        doc = frappe.get_doc("Deliveryman Settings", {"user": user})
        if hasattr(doc, "car_model"):
            doc.car_model = car_model
            doc.car_number = car_number
            doc.color = color
            doc.save(ignore_permissions=True)
            return doc.as_dict()
    return {}
