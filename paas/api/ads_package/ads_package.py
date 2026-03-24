import frappe
import json


@frappe.whitelist()
def create_ads_package(data):
    """
    Creates a new Ads Package.
    """
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc({"doctype": "Ads Package", **data})
    doc.insert()
    return doc.as_dict()


@frappe.whitelist()
def get_ads_packages():
    """
    Retrieves all active Ads Packages.
    """
    return frappe.get_list("Ads Package", filters={"active": 1}, fields=["*"])


@frappe.whitelist()
def update_ads_package(name, data):
    """
    Updates an Ads Package.
    """
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Ads Package", name)
    doc.update(data)
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def delete_ads_package(name):
    """
    Deletes an Ads Package.
    """
    frappe.delete_doc("Ads Package", name)
    return {"status": "success"}
