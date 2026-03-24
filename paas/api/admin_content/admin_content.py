import frappe
import json
from ..utils import _require_admin


@frappe.whitelist()
def get_admin_stories(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of all stories on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Story",
        fields=["name", "title", "shop", "expires_at"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_admin_banners(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of platform-wide banners (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Banner",
        filters={"shop": None},
        fields=["name", "title", "image", "link", "is_active"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def create_admin_banner(banner_data):
    """
    Creates a new platform-wide banner (for admins).
    """
    _require_admin()
    if isinstance(banner_data, str):
        banner_data = json.loads(banner_data)

    banner_data["shop"] = None

    new_banner = frappe.get_doc({"doctype": "Banner", **banner_data})
    new_banner.insert(ignore_permissions=True)
    return new_banner.as_dict()


@frappe.whitelist()
def update_admin_banner(banner_name, banner_data):
    """
    Updates a platform-wide banner (for admins).
    """
    _require_admin()
    if isinstance(banner_data, str):
        banner_data = json.loads(banner_data)

    banner = frappe.get_doc("Banner", banner_name)
    banner.update(banner_data)
    banner.save(ignore_permissions=True)
    return banner.as_dict()


@frappe.whitelist()
def delete_admin_banner(banner_name):
    """
    Deletes a platform-wide banner (for admins).
    """
    _require_admin()
    frappe.delete_doc("Banner", banner_name, ignore_permissions=True)
    return {"status": "success", "message": "Banner deleted successfully."}


@frappe.whitelist()
def get_admin_faqs(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of all FAQs (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "FAQ",
        fields=["name", "question", "faq_category", "is_active"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def create_admin_faq(faq_data):
    """
    Creates a new FAQ (for admins).
    """
    _require_admin()
    if isinstance(faq_data, str):
        faq_data = json.loads(faq_data)

    new_faq = frappe.get_doc({"doctype": "FAQ", **faq_data})
    new_faq.insert(ignore_permissions=True)
    return new_faq.as_dict()


@frappe.whitelist()
def update_admin_faq(faq_name, faq_data):
    """
    Updates an FAQ (for admins).
    """
    _require_admin()
    if isinstance(faq_data, str):
        faq_data = json.loads(faq_data)

    faq = frappe.get_doc("FAQ", faq_name)
    faq.update(faq_data)
    faq.save(ignore_permissions=True)
    return faq.as_dict()


@frappe.whitelist()
def delete_admin_faq(faq_name):
    """
    Deletes an FAQ (for admins).
    """
    _require_admin()
    frappe.delete_doc("FAQ", faq_name, ignore_permissions=True)
    return {"status": "success", "message": "FAQ deleted successfully."}


@frappe.whitelist()
def get_admin_faq_categories(
    limit_start: int = 0, limit_page_length: int = 20
):
    """
    Retrieves a list of all FAQ categories (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "FAQ Category",
        fields=["name", "category_name"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def create_admin_faq_category(category_data):
    """
    Creates a new FAQ category (for admins).
    """
    _require_admin()
    if isinstance(category_data, str):
        category_data = json.loads(category_data)

    new_category = frappe.get_doc({"doctype": "FAQ Category", **category_data})
    new_category.insert(ignore_permissions=True)
    return new_category.as_dict()


@frappe.whitelist()
def update_admin_faq_category(category_name, category_data):
    """
    Updates an FAQ category (for admins).
    """
    _require_admin()
    if isinstance(category_data, str):
        category_data = json.loads(category_data)

    category = frappe.get_doc("FAQ Category", category_name)
    category.update(category_data)
    category.save(ignore_permissions=True)
    return category.as_dict()


@frappe.whitelist()
def delete_admin_faq_category(category_name):
    """
    Deletes an FAQ category (for admins).
    """
    _require_admin()
    frappe.delete_doc("FAQ Category", category_name, ignore_permissions=True)
    return {
        "status": "success",
        "message": "FAQ category deleted successfully.",
    }
