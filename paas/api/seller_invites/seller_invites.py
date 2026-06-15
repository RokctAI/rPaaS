from typing import Any, Optional
import frappe
from ..utils import _get_seller_shop


@frappe.whitelist()
def get_seller_invites() -> Any:
    """
    Retrieves a list of invitations for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    invitations = frappe.get_all(
        "Invitation", filters={"shop": shop}, fields=["user", "role", "status"]
    )
    return invitations
