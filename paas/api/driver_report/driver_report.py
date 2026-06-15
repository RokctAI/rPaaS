from typing import Any, Optional
import frappe
from paas.api.delivery_man.delivery_man import (
    get_deliveryman_order_report as _get_report,
)


@frappe.whitelist()
def get_order_report(from_date: Any=None, to_date: Any=None) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not from_date or not to_date:
        from_date = frappe.utils.add_months(frappe.utils.today(), -1)
        to_date = frappe.utils.today()

    return _get_report(from_date, to_date)
