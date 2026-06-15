from typing import Any, Optional
import frappe
from paas.api.delivery_man.delivery_man import (
    get_deliveryman_order_report as _get_report,
)


@frappe.whitelist()
def get_order_report(from_date: Any=None, to_date: Any=None) -> Any:
    """
    The get_order_report function generates a sales report for orders placed within a specified date range. It accepts two optional parameters: from_date and to_date, which represent the start and end dates of the reporting period, respectively. If either parameter is not provided, the function defaults to a date range of the last month, with from_date set to one month prior to the current date and to_date set to the current date. The function returns the sales report data for the specified period, obtained by calling the get_seller_sales_report function with the determined date range.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not from_date or not to_date:
        from_date = frappe.utils.add_months(frappe.utils.today(), -1)
        to_date = frappe.utils.today()

    return _get_report(from_date, to_date)
