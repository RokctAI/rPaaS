import frappe
from paas.api.delivery_man.delivery_man import (
    get_deliveryman_parcel_orders as _get_parcel_orders,
)


@frappe.whitelist()
def get_driver_parcel_orders_paginate(limit_start=0, limit_page_length=20):
    return _get_parcel_orders(limit_start, limit_page_length)


@frappe.whitelist()
def add_parcel_order_review(order_id, rating, comment=None):
    if frappe.db.exists("Parcel Order", order_id):
        doc = frappe.new_doc("Review")
        doc.reference_doctype = "Parcel Order"
        doc.reference_name = order_id
        doc.rating = rating
        doc.comment = comment
        doc.user = frappe.session.user
        doc.insert(ignore_permissions=True)
        return {"status": True}
    return {"status": False}


@frappe.whitelist()
def attach_parcel_order_to_me(order_id):
    user = frappe.session.user
    if frappe.db.exists("Parcel Order", order_id):
        doc = frappe.get_doc("Parcel Order", order_id)
        if not doc.deliveryman:
            doc.deliveryman = user
            doc.status = "Accepted"
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def set_current_parcel_order(order_id):
    user = frappe.session.user
    if frappe.db.exists("Parcel Order", order_id):
        doc = frappe.get_doc("Parcel Order", order_id)
        if doc.deliveryman == user:
            doc.status = "On a Way"
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def update_driver_parcel_order_status(order_id, status):
    if frappe.db.exists("Parcel Order", order_id):
        doc = frappe.get_doc("Parcel Order", order_id)
        if doc.deliveryman == frappe.session.user:
            doc.status = status
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}
