import frappe
import json
from paas.api.utils import _get_seller_shop


@frappe.whitelist()
def get_seller_shop_working_days():
    """
    Retrieves the working days for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    working_days = frappe.get_all(
        "Shop Working Day",
        filters={"shop": shop},
        fields=["day_of_week", "opening_time", "closing_time", "is_closed"],
    )
    return working_days


@frappe.whitelist()
def update_seller_shop_working_days(working_days_data):
    """
    Updates the working days for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(working_days_data, str):
        working_days_data = json.loads(working_days_data)

    # Clear existing working days for the shop
    frappe.db.delete("Shop Working Day", {"shop": shop})

    for day_data in working_days_data:
        frappe.get_doc(
            {"doctype": "Shop Working Day", "shop": shop, **day_data}
        ).insert(ignore_permissions=True)

    return {
        "status": "success",
        "message": "Working days updated successfully."}


@frappe.whitelist()
def get_seller_shop_closed_days():
    """
    Retrieves the closed days for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    closed_days = frappe.get_all(
        "Shop Closed Day", filters={"shop": shop}, fields=["date"]
    )
    return [d.date for d in closed_days]


@frappe.whitelist()
def add_seller_shop_closed_day(date):
    """
    Adds a closed day for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    frappe.get_doc({"doctype": "Shop Closed Day", "shop": shop,
                   "date": date}).insert(ignore_permissions=True)

    return {"status": "success", "message": "Closed day added successfully."}


@frappe.whitelist()
def delete_seller_shop_closed_day(date):
    """
    Deletes a closed day for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    frappe.db.delete("Shop Closed Day", {"shop": shop, "date": date})

    return {"status": "success", "message": "Closed day deleted successfully."}


@frappe.whitelist()
def get_shop_users(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of users for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    shop_users = frappe.get_all(
        "User Shop",
        filters={"shop": shop},
        fields=["user", "role"],
        limit_start=limit_start,
        limit=limit_page_length,
    )
    return shop_users


@frappe.whitelist()
def add_shop_user(user_email: str, role: str):
    """
    Adds a user to the current seller's shop with a specific role.
    """
    owner = frappe.session.user
    shop = _get_seller_shop(owner)

    user_to_add = frappe.db.get_value("User", {"email": user_email}, "name")
    if not user_to_add:
        frappe.throw("User not found.")

    if frappe.db.exists("User Shop", {"user": user_to_add, "shop": shop}):
        frappe.throw("User is already a member of this shop.")

    frappe.get_doc(
        {"doctype": "User Shop", "user": user_to_add, "shop": shop, "role": role}
    ).insert(ignore_permissions=True)

    return {"status": "success", "message": "User added to shop successfully."}


@frappe.whitelist()
def remove_shop_user(user_to_remove: str):
    """
    Removes a user from the current seller's shop.
    """
    owner = frappe.session.user
    shop = _get_seller_shop(owner)

    frappe.db.delete("User Shop", {"user": user_to_remove, "shop": shop})

    return {
        "status": "success",
        "message": "User removed from shop successfully."}


@frappe.whitelist()
def get_seller_branches(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of branches for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    branches = frappe.get_list(
        "Branch",
        filters={"shop": shop},
        fields=["name", "branch_name", "address", "latitude", "longitude"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return branches


@frappe.whitelist()
def create_seller_branch(branch_data):
    """
    Creates a new branch for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(branch_data, str):
        branch_data = json.loads(branch_data)

    branch_data["shop"] = shop
    branch_data["owner"] = user

    new_branch = frappe.get_doc({"doctype": "Branch", **branch_data})
    new_branch.insert(ignore_permissions=True)
    return new_branch.as_dict()


@frappe.whitelist()
def update_seller_branch(branch_name, branch_data):
    """
    Updates a branch for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(branch_data, str):
        branch_data = json.loads(branch_data)

    branch = frappe.get_doc("Branch", branch_name)

    if branch.shop != shop:
        frappe.throw(
            "You are not authorized to update this branch.",
            frappe.PermissionError)

    branch.update(branch_data)
    branch.save(ignore_permissions=True)
    return branch.as_dict()


@frappe.whitelist()
def delete_seller_branch(branch_name):
    """
    Deletes a branch for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    branch = frappe.get_doc("Branch", branch_name)

    if branch.shop != shop:
        frappe.throw(
            "You are not authorized to delete this branch.",
            frappe.PermissionError)

    frappe.delete_doc("Branch", branch_name, ignore_permissions=True)
    return {"status": "success", "message": "Branch deleted successfully."}


@frappe.whitelist()
def get_seller_deliveryman_settings():
    """
    Retrieves the deliveryman settings for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if not frappe.db.exists("Shop Deliveryman Settings", {"shop": shop}):
        return {}

    return frappe.get_doc(
        "Shop Deliveryman Settings", {
            "shop": shop}).as_dict()


@frappe.whitelist()
def update_seller_deliveryman_settings(settings_data):
    """
    Updates the deliveryman settings for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(settings_data, str):
        settings_data = json.loads(settings_data)

    if not frappe.db.exists("Shop Deliveryman Settings", {"shop": shop}):
        settings = frappe.new_doc("Shop Deliveryman Settings")
        settings.shop = shop
    else:
        settings = frappe.get_doc("Shop Deliveryman Settings", {"shop": shop})

    settings.update(settings_data)
    settings.save(ignore_permissions=True)
    return settings.as_dict()


# --- ALIASES FOR FLUTTER ENDPOINTS ---


@frappe.whitelist()
def update_shop_working_days(working_days_data=None):
    return update_seller_shop_working_days(working_days_data)
