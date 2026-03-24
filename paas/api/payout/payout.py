import frappe
from paas.api.utils import api_response


@frappe.whitelist()
def request_payout(amount: float, lang: str = "en"):
    """
    Requests a payout for the current user/seller.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to request a payout.")

    # Placeholder logic
    payout = frappe.get_doc(
        {
            "doctype": "Payout",
            "user": user,
            "amount": amount,
            "status": "Pending",
        }
    )
    payout.insert(ignore_permissions=True)

    return {"status": "success", "message": "Payout requested."}
