import frappe
import json
from ..utils import _require_admin


@frappe.whitelist()
def get_deliveryman_global_settings():
    """
    Retrieves the global deliveryman settings (for admins).
    """
    _require_admin()
    return frappe.get_doc("DeliveryMan Settings").as_dict()


@frappe.whitelist()
def update_deliveryman_global_settings(settings_data):
    """
    Updates the global deliveryman settings (for admins).
    """
    _require_admin()
    if isinstance(settings_data, str):
        settings_data = json.loads(settings_data)

    settings = frappe.get_doc("DeliveryMan Settings")
    settings.update(settings_data)
    settings.save(ignore_permissions=True)
    return settings.as_dict()


@frappe.whitelist()
def get_parcel_order_settings(
    limit_start: int = 0, limit_page_length: int = 20
):
    """
    Retrieves a list of all parcel order settings (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Parcel Order Setting",
        fields=["*"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def create_parcel_order_setting(setting_data):
    """
    Creates a new parcel order setting (for admins).
    """
    _require_admin()
    if isinstance(setting_data, str):
        setting_data = json.loads(setting_data)

    new_setting = frappe.get_doc(
        {"doctype": "Parcel Order Setting", **setting_data}
    )
    new_setting.insert(ignore_permissions=True)
    return new_setting.as_dict()


@frappe.whitelist()
def update_parcel_order_setting(setting_name, setting_data):
    """
    Updates a parcel order setting (for admins).
    """
    _require_admin()
    if isinstance(setting_data, str):
        setting_data = json.loads(setting_data)

    setting = frappe.get_doc("Parcel Order Setting", setting_name)
    setting.update(setting_data)
    setting.save(ignore_permissions=True)
    return setting.as_dict()


@frappe.whitelist()
def delete_parcel_order_setting(setting_name):
    """
    Deletes a parcel order setting (for admins).
    """
    _require_admin()
    frappe.delete_doc(
        "Parcel Order Setting", setting_name, ignore_permissions=True
    )
    return {
        "status": "success",
        "message": "Parcel order setting deleted successfully.",
    }


@frappe.whitelist()
def get_all_delivery_zones(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of all delivery zones on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Delivery Zone",
        fields=["name", "shop"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_delivery_vehicle_types(
    limit_start: int = 0, limit_page_length: int = 20
):
    """
    Retrieves a list of all delivery vehicle types on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Delivery Vehicle Type",
        fields=["name"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def create_delivery_vehicle_type(type_data):
    """
    Creates a new delivery vehicle type (for admins).
    """
    _require_admin()
    if isinstance(type_data, str):
        type_data = json.loads(type_data)

    new_type = frappe.get_doc(
        {"doctype": "Delivery Vehicle Type", **type_data}
    )
    new_type.insert(ignore_permissions=True)
    return new_type.as_dict()


@frappe.whitelist()
def update_delivery_vehicle_type(type_name, type_data):
    """
    Updates a delivery vehicle type (for admins).
    """
    _require_admin()
    if isinstance(type_data, str):
        type_data = json.loads(type_data)

    type_doc = frappe.get_doc("Delivery Vehicle Type", type_name)
    type_doc.update(type_data)
    type_doc.save(ignore_permissions=True)
    return type_doc.as_dict()


@frappe.whitelist()
def delete_delivery_vehicle_type(type_name):
    """
    Deletes a delivery vehicle type (for admins).
    """
    _require_admin()
    frappe.delete_doc(
        "Delivery Vehicle Type", type_name, ignore_permissions=True
    )
    return {
        "status": "success",
        "message": "Delivery vehicle type deleted successfully.",
    }


@frappe.whitelist()
def get_all_delivery_man_delivery_zones(
    limit_start: int = 0, limit_page_length: int = 20
):
    """
    Retrieves a list of all delivery man delivery zones on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Deliveryman Delivery Zone",
        fields=["name", "deliveryman", "delivery_zone"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_all_shop_working_days(
    limit_start: int = 0, limit_page_length: int = 20
):
    """
    Retrieves a list of all shop working days on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Shop Working Day",
        fields=[
            "name",
            "shop",
            "day_of_week",
            "opening_time",
            "closing_time",
            "is_closed",
        ],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_all_shop_closed_days(
    limit_start: int = 0, limit_page_length: int = 20
):
    """
    Retrieves a list of all shop closed days on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Shop Closed Day",
        fields=["name", "shop", "date"],
        offset=limit_start,
        limit=limit_page_length,
    )
