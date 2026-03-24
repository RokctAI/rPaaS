import frappe
import json


@frappe.whitelist(allow_guest=True)
def get_receipts(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of receipts, formatted for frontend compatibility.
    """
    receipts = frappe.get_list(
        "Receipt", fields=["*"], offset=limit_start, limit=limit_page_length
    )

    # This is a simplified representation. A full implementation would
    # need to replicate the complex price calculation and relationship loading
    # from the original Laravel RestReceiptResource.

    return receipts


@frappe.whitelist(allow_guest=True)
def get_receipt(id: str):
    """
    Retrieves a single receipt.
    """
    receipt = frappe.get_doc("Receipt", id)

    # Again, this is a simplified representation.
    return receipt.as_dict()
