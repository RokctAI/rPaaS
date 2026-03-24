import frappe
from paas.api.utils import _get_seller_shop


@frappe.whitelist()
def get_seller_request_models(
    limit_start: int = 0, limit_page_length: int = 20
):
    """
    Retrieves a list of request models for the current seller.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your request models.",
            frappe.AuthenticationError,
        )

    request_models = frappe.get_list(
        "Request Model",
        filters={"created_by_user": user},
        fields=["name", "model_type", "model", "status", "created_at"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return request_models


@frappe.whitelist()
def get_seller_customer_addresses(
    limit_start: int = 0, limit_page_length: int = 20
):
    """
    Retrieves a list of customer addresses for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    t_order = frappe.qb.DocType("Order")
    customer_ids = (
        frappe.qb.from_(t_order)
        .select(frappe.qb.fn.Distinct(t_order.user))
        .where(t_order.shop == shop)
    ).run(pluck=True)

    if not customer_ids:
        return []

    addresses = frappe.get_all(
        "User Address",
        filters={"user": ["in", customer_ids]},
        fields=["name", "user", "title", "address", "location", "active"],
        offset=limit_start,
        limit=limit_page_length,
    )
    return addresses
