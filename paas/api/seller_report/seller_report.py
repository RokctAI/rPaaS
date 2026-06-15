from typing import Any, Optional
import frappe
from paas.api.seller_reports.seller_reports import get_seller_sales_report


@frappe.whitelist()
def get_order_report(from_date: Any=None, to_date: Any=None) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not from_date or not to_date:
        from_date = frappe.utils.add_months(frappe.utils.today(), -1)
        to_date = frappe.utils.today()

    return get_seller_sales_report(from_date, to_date)


@frappe.whitelist()
def get_order_report_paginate(limit_start: Any=0, limit_page_length: Any=20) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    # Depending on legacy requirements, this often just returns recent orders
    # or paginated sales report
    user = frappe.session.user
    from paas.api.utils import _get_seller_shop

    shop = _get_seller_shop(user)

    orders = frappe.get_list(
        "Order",
        filters={"shop": shop},
        fields=["name", "user", "grand_total", "status", "creation"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return orders
