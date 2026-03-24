import frappe
import json


@frappe.whitelist()
def create_faq(data):
    """
    Creates a new FAQ.
    """
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc({"doctype": "FAQ", **data})
    doc.insert()
    return doc.as_dict()


@frappe.whitelist(allow_guest=True)
def get_faqs(type=None):
    """
    Retrieves FAQs, optionally filtered by type.
    """
    filters = {"active": 1}
    if type:
        filters["type"] = type

    return frappe.get_list(
        "FAQ", filters=filters, fields=["name", "question", "answer", "type"]
    )


@frappe.whitelist()
def update_faq(name, data):
    """
    Updates an FAQ.
    """
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("FAQ", name)
    doc.update(data)
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def delete_faq(name):
    """
    Deletes an FAQ.
    """
    frappe.delete_doc("FAQ", name)
    return {"status": "success"}
