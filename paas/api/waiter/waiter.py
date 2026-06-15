from typing import Any, Optional
import frappe


@frappe.whitelist()
def get_waiter_orders(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of orders assigned to the current waiter.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your orders.",
            frappe.AuthenticationError,
        )

    orders = frappe.get_list(
        "Order",
        filters={"waiter": user},
        fields=["name", "shop", "total_price", "status", "creation"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return orders


@frappe.whitelist()
def get_waiter_order_report(from_date: str, to_date: str) -> Any:
    """
    Retrieves a report of orders for the current waiter within a date range.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your order report.",
            frappe.AuthenticationError,
        )

    orders = frappe.get_all(
        "Order",
        filters={
            "waiter": user,
            "creation": ["between", [from_date, to_date]],
        },
        fields=["name", "shop", "total_price", "status", "creation"],
        order_by="creation desc",
    )
    return orders
