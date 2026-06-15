from typing import Any, Optional
import frappe
import json


@frappe.whitelist(allow_guest=True)
def get_branches(shop_id: str) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Retrieves a list of branches for a given shop.
    """
    if not frappe.db.exists("Company", shop_id):
        frappe.throw("Shop not found.")

    branches = frappe.get_list(
        "Branch",
        filters={"shop": shop_id},
        fields=["name", "address", "latitude", "longitude"],
    )
    return branches


@frappe.whitelist(allow_guest=True)
def get_branch(branch_id: str) -> Any:
    """
    Retrieves a single branch.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return frappe.get_doc("Branch", branch_id).as_dict()


@frappe.whitelist()
def create_branch(branch_data: Any) -> Any:
    """
    Creates a new branch.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(branch_data, str):
        branch_data = json.loads(branch_data)

    branch = frappe.get_doc(
        {
            "doctype": "Branch",
            "branch_name": branch_data.get("name"),
            "address": branch_data.get("address"),
            "latitude": branch_data.get("latitude"),
            "longitude": branch_data.get("longitude"),
            "shop": branch_data.get("shop"),
            "owner": frappe.session.user,
        }
    )
    branch.insert(ignore_permissions=True)
    return branch.as_dict()


@frappe.whitelist()
def update_branch(branch_id: Any, branch_data: Any) -> Any:
    """
    Updates an existing branch.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(branch_data, str):
        branch_data = json.loads(branch_data)

    branch = frappe.get_doc("Branch", branch_id)
    if (
        branch.owner != frappe.session.user
        and "System Manager" not in frappe.get_roles(frappe.session.user)
    ):
        frappe.throw(
            "You are not authorized to update this branch.",
            frappe.PermissionError,
        )

    branch.branch_name = branch_data.get("name", branch.branch_name)
    branch.address = branch_data.get("address", branch.address)
    branch.latitude = branch_data.get("latitude", branch.latitude)
    branch.longitude = branch_data.get("longitude", branch.longitude)
    branch.shop = branch_data.get("shop", branch.shop)
    branch.save(ignore_permissions=True)
    return branch.as_dict()


@frappe.whitelist()
def delete_branch(branch_id: Any) -> Any:
    """
    Deletes a branch.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    branch = frappe.get_doc("Branch", branch_id)
    if (
        branch.owner != frappe.session.user
        and "System Manager" not in frappe.get_roles(frappe.session.user)
    ):
        frappe.throw(
            "You are not authorized to delete this branch.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Branch", branch_id, ignore_permissions=True)
    return {"status": "success", "message": "Branch deleted successfully."}
