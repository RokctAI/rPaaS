import frappe
import json


@frappe.whitelist()
def create_stock(data):
    """
    Creates a new Stock (Variant) for a Product.
    """
    if isinstance(data, str):
        data = json.loads(data)

    # Extract extras if present
    extras = data.pop("extras", [])

    doc = frappe.get_doc({"doctype": "Stock", **data})

    # Add extras to child table
    for extra_value_id in extras:
        doc.append("stock_extras", {"extra_value": extra_value_id})

    doc.insert()
    return doc.as_dict()


@frappe.whitelist()
def get_product_stocks(product_id):
    """
    Retrieves all Stock variants for a Product.
    """
    return frappe.get_list(
        "Stock", filters={"product": product_id}, fields=["*"]
    )


@frappe.whitelist()
def update_stock(name, data):
    """
    Updates a Stock item.
    """
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Stock", name)

    # Handle extras update if provided
    if "extras" in data:
        extras = data.pop("extras")
        doc.set("stock_extras", [])  # Clear existing
        for extra_value_id in extras:
            doc.append("stock_extras", {"extra_value": extra_value_id})

    doc.update(data)
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def delete_stock(name):
    """
    Deletes a Stock item.
    """
    frappe.delete_doc("Stock", name)
    return {"status": "success"}
