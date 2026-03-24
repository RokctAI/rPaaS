import frappe
import json


def _require_admin():
    """Helper function to ensure the user has the System Manager role."""
    if "System Manager" not in frappe.get_roles():
        frappe.throw(
            "You are not authorized to perform this action.",
            frappe.PermissionError)


@frappe.whitelist(allow_guest=True)
def get_page(route: str):
    """
    Retrieves a single web page by its route.
    """
    page = frappe.get_doc("Web Page", {"route": route})
    if not page.published:
        frappe.throw("Page not published.", frappe.PermissionError)

    # The original response has a nested translation object.
    # We will simulate this structure.
    return {
        "id": page.name,
        "type": page.route,
        "img": page.image,
        "active": page.published,
        "translation": {
            "title": page.title,
            "description": page.main_section,
        },
    }


@frappe.whitelist()
def get_admin_pages(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of all web pages on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Web Page",
        fields=["name", "title", "route", "published"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_admin_web_page(route: str):
    """
    Retrieves a web page for admin management.
    """
    _require_admin()
    return frappe.get_doc("Web Page", {"route": route}).as_dict()


@frappe.whitelist()
def update_admin_web_page(route: str, page_data):
    """
    Updates a web page (for admins).
    """
    _require_admin()
    if isinstance(page_data, str):
        page_data = json.loads(page_data)

    page = frappe.get_doc("Web Page", {"route": route})
    page.update(page_data)
    page.save(ignore_permissions=True)
    return page.as_dict()
