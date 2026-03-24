import frappe
import json


def _require_admin():
    """Helper function to ensure the user has the System Manager role."""
    if "System Manager" not in frappe.get_roles():
        frappe.throw(
            "You are not authorized to perform this action.",
            frappe.PermissionError,
        )


@frappe.whitelist(allow_guest=True)
def get_careers(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of active careers, formatted for frontend compatibility.
    """
    careers = frappe.get_list(
        "Career",
        filters={"is_active": 1},
        fields=["name", "title", "description", "location", "category"],
        offset=limit_start,
        limit=limit_page_length,
    )

    formatted_careers = []
    for career in careers:
        # The original response has a nested translation object.
        # We will simulate this structure.
        formatted_careers.append(
            {
                "id": career.name,
                "location": career.location,
                "active": True,
                "category": {"name": career.category},
                "translation": {
                    "title": career.title,
                    "description": career.description,
                },
            }
        )

    return formatted_careers


@frappe.whitelist(allow_guest=True)
def get_career(id: str):
    """
    Retrieves a single career by its ID (name).
    """
    career = frappe.get_doc("Career", id)
    if not career.is_active:
        frappe.throw("Career not active.", frappe.PermissionError)

    return {
        "id": career.name,
        "location": career.location,
        "active": True,
        "category": {"name": career.category},
        "translation": {
            "title": career.title,
            "description": career.description,
        },
    }


@frappe.whitelist()
def get_admin_careers(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of all careers on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Career",
        fields=["name", "title", "location", "category", "is_active"],
        offset=limit_start,
        limit=limit_page_length,
    )
