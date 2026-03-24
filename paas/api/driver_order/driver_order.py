import frappe
from paas.api.delivery_man.delivery_man import get_deliveryman_orders as _get_orders


@frappe.whitelist()
def get_driver_orders_paginate(limit_start=0, limit_page_length=20):
    return _get_orders(limit_start, limit_page_length)


@frappe.whitelist()
def fetch_current_order():
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized")

    order = frappe.get_list(
        'Order', filters={
            'deliveryman': user, 'status': [
                'in', [
                    'On a Way', 'Accepted']]}, fields=[
            'name', 'shop', 'total_price', 'status', 'creation'], limit=1)
    if order:
        doc = frappe.get_doc('Order', order[0].name)
        return {"data": doc.as_dict()}
    return {"data": {}}


@frappe.whitelist()
def set_current_order(order_id):
    user = frappe.session.user
    if frappe.db.exists('Order', order_id):
        doc = frappe.get_doc('Order', order_id)
        if doc.deliveryman == user:
            doc.status = 'On a Way'
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def attach_order_to_me(order_id):
    user = frappe.session.user
    if frappe.db.exists('Order', order_id):
        doc = frappe.get_doc('Order', order_id)
        if not doc.deliveryman:
            doc.deliveryman = user
            doc.status = 'Accepted'
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def update_driver_order_status(order_id, status):
    if frappe.db.exists('Order', order_id):
        doc = frappe.get_doc('Order', order_id)
        if doc.deliveryman == frappe.session.user:
            doc.status = status
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def upload_order_image(order_id, image_url=None):
    if not image_url:
        return {"status": False}
    if frappe.db.exists('Order', order_id):
        doc = frappe.get_doc('Order', order_id)
        if hasattr(doc, 'delivery_photo'):
            doc.delivery_photo = image_url
            doc.save(ignore_permissions=True)
            return {"status": True}
    return {"status": True}
