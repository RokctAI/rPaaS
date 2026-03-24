import frappe
import json

# --- Product Extra Group APIs ---


@frappe.whitelist()
def create_extra_group(data):
    """
    Creates a new Product Extra Group.
    """
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc({"doctype": "Product Extra Group", **data})
    doc.insert()
    return doc.as_dict()


@frappe.whitelist()
def get_extra_groups(shop_id=None):
    """
    Retrieves Extra Groups, optionally filtered by shop.
    """
    filters = {}
    if shop_id:
        filters["shop"] = shop_id

    return frappe.get_list(
        "Product Extra Group",
        filters=filters,
        fields=["*"])


@frappe.whitelist()
def update_extra_group(name, data):
    """
    Updates an Extra Group.
    """
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Product Extra Group", name)
    doc.update(data)
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def delete_extra_group(name):
    """
    Deletes an Extra Group.
    """
    frappe.delete_doc("Product Extra Group", name)
    return {"status": "success"}


# --- Product Extra Value APIs ---


@frappe.whitelist()
def create_extra_value(data):
    """
    Creates a new Product Extra Value.
    """
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc({"doctype": "Product Extra Value", **data})
    doc.insert()
    return doc.as_dict()


@frappe.whitelist()
def get_extra_values(group_id):
    """
    Retrieves Extra Values for a specific group.
    """
    return frappe.get_list(
        "Product Extra Value", filters={"extra_group": group_id}, fields=["*"]
    )


@frappe.whitelist()
def update_extra_value(name, data):
    """
    Updates an Extra Value.
    """
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Product Extra Value", name)
    doc.update(data)
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def delete_extra_value(name):
    """
    Deletes an Extra Value.
    """
    frappe.delete_doc("Product Extra Value", name)
    return {"status": "success"}
