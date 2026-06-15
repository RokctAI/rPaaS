from typing import Any, Optional
import frappe
from ..utils import _get_seller_shop


@frappe.whitelist()
def get_seller_transactions(limit_start: Any=0, limit_page_length: Any=20) -> Any:
    """
    Retrieves a list of transactions for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    orders = frappe.get_all("Order", filters={"shop": shop}, pluck="name")

    if not orders:
        return []

    transactions = frappe.get_all(
        "Transaction",
        filters={"reference_name": ["in", orders]},
        fields=[
            "name",
            "transaction_date",
            "reference_doctype",
            "reference_name",
            "debit",
            "credit",
            "currency",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return transactions


@frappe.whitelist()
def get_seller_shop_payments(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of shop payments for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    orders = frappe.get_all("Order", filters={"shop": shop}, pluck="name")

    if not orders:
        return []

    payments = frappe.get_all(
        "Transaction",
        filters={"reference_name": ["in", orders], "credit": [">", 0]},
        fields=[
            "name",
            "transaction_date",
            "reference_doctype",
            "reference_name",
            "credit",
            "currency",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return payments


@frappe.whitelist()
def get_seller_payment_to_partners(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of payments to partners for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    payouts = frappe.get_list(
        "Payout",
        filters={"shop": shop},
        fields=["name", "deliveryman", "amount", "payment_date", "status"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="payment_date desc",
    )
    return payouts
