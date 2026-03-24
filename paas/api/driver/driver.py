import frappe
import json
from paas.api.delivery_man.delivery_man import (
    get_deliveryman_statistics as _get_deliveryman_statistics,
)


@frappe.whitelist()
def get_driver_statistics():
    return _get_deliveryman_statistics()


@frappe.whitelist()
def update_location(lat=None, lng=None):
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
def set_online_status():
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
def get_car_requests():
    return []


@frappe.whitelist()
def update_car_info(car_model=None, car_number=None, color=None):
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
