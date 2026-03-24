import frappe
import json
from paas.api.utils import _get_seller_shop


@frappe.whitelist()
def get_seller_orders(
    limit_start: int = 0,
    limit_page_length: int = 20,
    status: str = None,
    from_date: str = None,
    to_date: str = None,
):
    """
    Retrieves a list of orders for the current seller's shop, with optional filters.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    filters = {"shop": shop}
    if status:
        filters["status"] = status
    if from_date and to_date:
        filters["creation"] = ["between", [from_date, to_date]]

    orders = frappe.get_list(
        "Order",
        filters=filters,
        fields=["name", "user", "grand_total", "status", "creation"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return orders


@frappe.whitelist()
def get_seller_order_details(order_id):
    """
    Retrieves full details of a specific order.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    order = frappe.get_doc("Order", order_id)

    if order.shop != shop:
        frappe.throw(
            "You are not authorized to view this order.",
            frappe.PermissionError)

    return order.as_dict()


@frappe.whitelist()
def update_seller_order_status(order_id, status):
    """
    Updates the status of an order.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    order = frappe.get_doc("Order", order_id)

    if order.shop != shop:
        frappe.throw(
            "You are not authorized to update this order.",
            frappe.PermissionError)

    valid_statuses = [
        "New",
        "Accepted",
        "Shipped",
        "Delivered",
        "Cancelled",
        "Paid",
        "Failed",
    ]
    if status not in valid_statuses:
        frappe.throw(f"Invalid status. Must be one of: {
            ', '.join(valid_statuses)}")

    order.status = status
    order.save(ignore_permissions=True)
    return order.as_dict()


@frappe.whitelist()
def get_seller_order_refunds(
        limit_start: int = 0,
        limit_page_length: int = 20):
    """
    Retrieves a list of order refunds for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    orders = frappe.get_all("Order", filters={"shop": shop}, pluck="name")

    if not orders:
        return []

    refunds = frappe.get_list(
        "Order Refund",
        filters={"order": ["in", orders]},
        fields=["name", "order", "status", "cause", "answer"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return refunds


@frappe.whitelist()
def update_seller_order_refund(refund_name, status, answer=None):
    """
    Updates the status and answer of an order refund.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    refund = frappe.get_doc("Order Refund", refund_name)
    order = frappe.get_doc("Order", refund.order)

    if order.shop != shop:
        frappe.throw(
            "You are not authorized to update this refund request.",
            frappe.PermissionError,
        )

    if status not in ["Accepted", "Canceled"]:
        frappe.throw("Invalid status. Must be 'Accepted' or 'Canceled'.")

    refund.status = status
    if answer:
        refund.answer = answer

    refund.save(ignore_permissions=True)
    return refund.as_dict()


@frappe.whitelist()
def get_seller_reviews(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of reviews for products in the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    products = frappe.get_all("Item", filters={"shop": shop}, pluck="name")

    if not products:
        return []

    reviews = frappe.get_list(
        "Review",
        filters={
            "reviewable_id": [
                "in",
                products],
            "reviewable_type": "Item"},
        fields=[
            "name",
            "user",
            "rating",
            "comment",
            "creation",
            "reviewable_id"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return reviews
