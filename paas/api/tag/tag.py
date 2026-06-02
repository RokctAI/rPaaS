# Tenant context: session.user validation
import frappe


@frappe.whitelist()
def get_tags(lang: str = "en"):
    """
    Retrieves all tags.
    """
    return frappe.get_list("Tag", fields=["name", "description"])
