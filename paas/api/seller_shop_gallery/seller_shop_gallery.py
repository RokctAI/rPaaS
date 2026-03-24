import frappe
import json
from ..utils import _get_seller_shop


@frappe.whitelist()
def get_seller_shop_galleries(
        limit_start: int = 0,
        limit_page_length: int = 20):
    """
    Retrieves a list of shop gallery images for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    galleries = frappe.get_list(
        "Shop Gallery",
        filters={"shop": shop},
        fields=["name", "image"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return galleries


@frappe.whitelist()
def create_seller_shop_gallery(gallery_data):
    """
    Creates a new shop gallery image for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(gallery_data, str):
        gallery_data = json.loads(gallery_data)

    gallery_data["shop"] = shop

    new_gallery = frappe.get_doc({"doctype": "Shop Gallery", **gallery_data})
    new_gallery.insert(ignore_permissions=True)
    return new_gallery.as_dict()


@frappe.whitelist()
def delete_seller_shop_gallery(gallery_name):
    """
    Deletes a shop gallery image for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    gallery = frappe.get_doc("Shop Gallery", gallery_name)

    if gallery.shop != shop:
        frappe.throw(
            "You are not authorized to delete this gallery image.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Shop Gallery", gallery_name, ignore_permissions=True)
    return {
        "status": "success",
        "message": "Gallery image deleted successfully."}
