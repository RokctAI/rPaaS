import frappe
import json
import uuid


@frappe.whitelist()
def get_brands(limit_start: int = 0, limit_page_length: int = 10):
    """
    Retrieves a list of brands.
    """
    brands = frappe.get_list(
        "Brand",
        fields=["name", "uuid", "title", "slug", "active", "image", "shop"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name desc",
    )
    return brands


@frappe.whitelist()
def get_brand_by_uuid(uuid: str):
    """
    Retrieves a single brand by its UUID.
    """
    brand = frappe.get_doc("Brand", {"uuid": uuid})
    return brand.as_dict()


@frappe.whitelist()
def create_brand(brand_data):
    """
    Creates a new brand.
    """
    if isinstance(brand_data, str):
        brand_data = json.loads(brand_data)

    brand_uuid = brand_data.get("uuid") or str(uuid.uuid4())

    if not brand_data.get("title"):
        frappe.throw("Brand title is required.")

    if frappe.db.exists("Brand", {"uuid": brand_uuid}):
        frappe.throw("Brand with this UUID already exists.")

    brand = frappe.get_doc(
        {
            "doctype": "Brand",
            "uuid": brand_uuid,
            "title": brand_data.get("title"),
            "slug": brand_data.get("slug"),
            "active": brand_data.get("active", 1),
            "image": brand_data.get("image"),
            "shop": brand_data.get("shop"),
        }
    )
    brand.insert(ignore_permissions=True)
    return brand.as_dict()


@frappe.whitelist()
def update_brand(uuid, brand_data):
    """
    Updates an existing brand by its UUID.
    """
    if not uuid:
        frappe.throw("UUID is required to update a brand.")

    if isinstance(brand_data, str):
        brand_data = json.loads(brand_data)

    brand_name = frappe.db.get_value("Brand", {"uuid": uuid}, "name")
    if not brand_name:
        frappe.throw("Brand not found.")

    brand = frappe.get_doc("Brand", brand_name)

    updatable_fields = ["title", "slug", "active", "image", "shop"]

    for key, value in brand_data.items():
        if key in updatable_fields:
            brand.set(key, value)

    brand.save(ignore_permissions=True)
    return brand.as_dict()


@frappe.whitelist()
def delete_brand(uuid):
    """
    Deletes a brand by its UUID.
    """
    if not uuid:
        frappe.throw("UUID is required to delete a brand.")

    brand_name = frappe.db.get_value("Brand", {"uuid": uuid}, "name")
    if not brand_name:
        frappe.throw("Brand not found.")

    frappe.delete_doc("Brand", brand_name, ignore_permissions=True)

    return {"status": "success", "message": "Brand deleted successfully."}
