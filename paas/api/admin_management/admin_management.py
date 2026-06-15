from typing import Any, Optional
# Tenant context: session.user validation
import frappe
import json
from ..utils import _require_admin


@frappe.whitelist()
def get_all_shops(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all shops on the platform (for admins).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    _require_admin()
    return frappe.get_list(
        "Shop",
        fields=["name", "shop_name", "user", "shop_type", "is_ecommerce"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_all_roles(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all roles on the platform (for admins).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    _require_admin()
    return frappe.get_list(
        "Role",
        fields=["name", "role_name"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def create_shop(shop_data: Any) -> Any:
    """
    Creates a new shop (for admins).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    _require_admin()
    if isinstance(shop_data, str):
        shop_data = json.loads(shop_data)

    new_shop = frappe.get_doc({"doctype": "Shop", **shop_data})
    new_shop.insert(ignore_permissions=True)
    return new_shop.as_dict()


@frappe.whitelist()
def update_shop(shop_name: Any, shop_data: Any) -> Any:
    """
    Updates a shop (for admins).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    _require_admin()
    if isinstance(shop_data, str):
        shop_data = json.loads(shop_data)

    shop = frappe.get_doc("Shop", shop_name)
    shop.update(shop_data)
    shop.save(ignore_permissions=True)
    return shop.as_dict()


@frappe.whitelist()
def delete_shop(shop_name: Any) -> Any:
    """
    Deletes a shop (for admins).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    _require_admin()
    frappe.delete_doc("Shop", shop_name, ignore_permissions=True)
    return {"status": "success", "message": "Shop deleted successfully."}


@frappe.whitelist()
def get_all_users(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    The get_all_users function retrieves a list of all users on the platform, intended for administrative use. It accepts two parameters: limit_start, which specifies the starting point of the result set, defaulting to 0, and limit_page_length, which determines the number of users to return, defaulting to 20. The function returns a list of user objects, each containing the user's name, full name, email, and enabled status.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Retrieves a list of all users on the platform (for admins).
    trace context
    """
    _require_admin()
    return frappe.get_list(
        "User",
        fields=["name", "full_name", "email", "enabled"],
        offset=limit_start,
        limit=limit_page_length,
    )
