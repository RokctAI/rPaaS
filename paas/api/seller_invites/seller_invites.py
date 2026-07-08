# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import frappe
from ..utils import _get_seller_shop


@frappe.whitelist()
def get_seller_invites():
    """
    Retrieves a list of invitations for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    invitations = frappe.get_all(
        "Invitation", filters={"shop": shop}, fields=["user", "role", "status"]
    )
    return invitations
