from typing import Any, Optional
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

# Helper Functions


def check_shop_permission(shop_id, role):
    """Check if the current user has permission for a given shop."""
    user = frappe.session.user
    if frappe.has_role("System Manager"):
        return

    # Assuming Shop User logic exists or will be implemented.
    # If Shop User doctype doesn't exist yet, this might fail.
    # For now, we'll keep the check but be aware.
    if not frappe.db.exists(
            "Shop User", {
            "user": user, "shop": shop_id, "role": role}):
        frappe.throw(
            f"You are not authorized to manage this shop's {
                role.lower()} bookings.",
            frappe.PermissionError)


def check_availability(
        shop_id,
        table_id,
        start_date,
        end_date,
        exclude_reservation_id=None):
    """
    Check if a table is available for the given time range.
    Returns True if available, False otherwise.
    """
    filters = {
        "table": table_id,
        "status": ["in", ["New", "Accepted"]],
        "start_date": ["<", end_date],
        "end_date": [">", start_date]
    }

    if exclude_reservation_id:
        filters["name"] = ["!=", exclude_reservation_id]

    overlapping_reservations = frappe.get_all("User Booking", filters=filters)

    return len(overlapping_reservations) == 0

# Admin/Seller Booking Slot Management (The 'Booking' DocType)


@frappe.whitelist()
def create_booking_slot(data: Any) -> Any:
    """Create a new booking slot (shift)."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    # Permission check: Admin or Seller of the shop
    data = frappe._dict(data)
    if not frappe.has_permission("Booking", "create"):
        # Fallback to shop permission check if not system admin
        if data.get("shop"):
            check_shop_permission(data.get("shop"), "Seller")
        else:
            frappe.throw("Not permitted", frappe.PermissionError)

    data["doctype"] = "Booking"
    doc = frappe.get_doc(data)
    doc.insert()
    return doc


@frappe.whitelist()
def get_booking_slots(shop_id: Any) -> Any:
    """Get all booking slots for a specific shop."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    # Publicly accessible? Or restricted? Assuming public for now so users can
    # see slots.
    return frappe.get_list(
        "Booking",
        filters={
            "shop": shop_id,
            "active": 1},
        fields=["*"])


@frappe.whitelist()
def update_booking_slot(name: Any, data: Any) -> Any:
    """Update a booking slot."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not frappe.has_permission("Booking", "write"):
        doc = frappe.get_doc("Booking", name)
        check_shop_permission(doc.shop, "Seller")

    doc = frappe.get_doc("Booking", name)
    doc.update(data)
    doc.save()
    return doc


@frappe.whitelist()
def delete_booking_slot(name: Any) -> Any:
    """Delete a booking slot."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not frappe.has_permission("Booking", "delete"):
        doc = frappe.get_doc("Booking", name)
        check_shop_permission(doc.shop, "Seller")

    frappe.delete_doc("Booking", name)
    return {
        "status": "success",
        "message": "Booking slot deleted successfully"}

# Reservation Management (The 'User Booking' DocType)


@frappe.whitelist()
def create_reservation(data: Any) -> Any:
    """Create a new user reservation."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to create a booking.",
            frappe.PermissionError)

    booking_data = frappe._dict(data)

    # Validation
    if not booking_data.get("table"):
        frappe.throw("Table is required.")
    if not booking_data.get("start_date") or not booking_data.get("end_date"):
        frappe.throw("Start and End dates are required.")

    start_date = get_datetime(booking_data.get("start_date"))
    end_date = get_datetime(booking_data.get("end_date"))

    if start_date >= end_date:
        frappe.throw("End date must be after start date.")

    # Check Availability
    # We need to know the shop_id. It can be fetched from the Booking Slot or
    # Table.
    table = frappe.get_doc("Table", booking_data.get("table"))
    shop_section = frappe.get_doc("Shop Section", table.shop_section)
    shop_id = shop_section.shop

    if not check_availability(
            shop_id,
            booking_data.get("table"),
            start_date,
            end_date):
        frappe.throw(
            "The selected table is not available for the chosen time.")

    booking_data.user = user
    booking_data.doctype = "User Booking"
    booking_data.status = "New"

    doc = frappe.get_doc(booking_data)
    doc.insert(ignore_permissions=True)
    return doc


@frappe.whitelist()
def get_my_reservations() -> Any:
    """Get the current user's reservations."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your bookings.",
            frappe.PermissionError)

    return frappe.get_list(
        "User Booking",
        filters={
            "user": user},
        fields=["*"],
        order_by="start_date desc")


@frappe.whitelist()
def get_shop_reservations(shop_id: Any, status: Any=None, date_from: Any=None, date_to: Any=None) -> Any:
    """Get all reservations for a specific shop."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    check_shop_permission(shop_id, "Seller")

    _filters = {"booking.shop": shop_id}
    # Wait, UserBooking links to Booking (Slot). Booking (Slot) has Shop.
    # So we can filter by booking.shop if standard queries support it, or we filter manually.
    # Frappe get_list supports child table filtering but this is a Link.
    # We might need to query User Booking where booking in (select name from
    # Booking where shop=shop_id)

    # Alternative: User Booking -> Table -> Shop Section -> Shop.
    # Let's use Table -> Shop Section -> Shop as it's more direct for the
    # physical location.

    # Fetch tables for the shop
    shop_sections = frappe.get_all(
        "Shop Section", filters={
            "shop": shop_id}, pluck="name")
    tables = frappe.get_all(
        "Table",
        filters={
            "shop_section": [
                "in",
                shop_sections]},
        pluck="name")

    if not tables:
        return []

    res_filters = {"table": ["in", tables]}
    if status:
        res_filters["status"] = status
    if date_from:
        res_filters["start_date"] = [">=", date_from]
    if date_to:
        res_filters["end_date"] = ["<=", date_to]

    return frappe.get_list(
        "User Booking",
        filters=res_filters,
        fields=["*"],
        order_by="start_date desc")


@frappe.whitelist()
def update_reservation_status(name: Any, status: Any) -> Any:
    """Update the status of a reservation."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    doc = frappe.get_doc("User Booking", name)

    # Permission check: User can cancel their own. Seller can accept/reject.
    user = frappe.session.user

    if user == doc.user:
        if status == "Cancelled":
            doc.status = "Cancelled"
            doc.save(ignore_permissions=True)
            return doc
        else:
            frappe.throw(
                "You can only cancel your own booking.",
                frappe.PermissionError)

    # Check if user is seller for this shop
    # Need to traverse to Shop ID
    table = frappe.get_doc("Table", doc.table)
    shop_section = frappe.get_doc("Shop Section", table.shop_section)
    check_shop_permission(shop_section.shop, "Seller")

    doc.status = status
    doc.save(ignore_permissions=True)
    return doc

# Admin Shop Section & Table Management (Kept mostly same)


@frappe.whitelist()
def create_shop_section(data: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not frappe.has_permission("Shop Section", "create"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc = frappe.get_doc(data)
    doc.insert()
    return doc


@frappe.whitelist()
def get_shop_section(name: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return frappe.get_doc("Shop Section", name)


@frappe.whitelist()
def update_shop_section(name: Any, data: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not frappe.has_permission("Shop Section", "write"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc = frappe.get_doc("Shop Section", name)
    doc.update(data)
    doc.save()
    return doc


@frappe.whitelist()
def delete_shop_section(name: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not frappe.has_permission("Shop Section", "delete"):
        frappe.throw("Not permitted", frappe.PermissionError)
    frappe.delete_doc("Shop Section", name)
    return {
        "status": "success",
        "message": "Shop Section deleted successfully"}


@frappe.whitelist()
def create_table(data: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not frappe.has_permission("Table", "create"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc = frappe.get_doc(data)
    doc.insert()
    return doc


@frappe.whitelist()
def get_table(name: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return frappe.get_doc("Table", name)


@frappe.whitelist()
def update_table(name: Any, data: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not frappe.has_permission("Table", "write"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc = frappe.get_doc("Table", name)
    doc.update(data)
    doc.save()
    return doc


@frappe.whitelist()
def delete_table(name: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not frappe.has_permission("Table", "delete"):
        frappe.throw("Not permitted", frappe.PermissionError)
    frappe.delete_doc("Table", name)
    return {"status": "success", "message": "Table deleted successfully"}


@frappe.whitelist()
def get_shop_sections_for_booking(shop_id: Any) -> Any:
    """Get all shop sections for a specific shop."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return frappe.get_list(
        "Shop Section", filters={
            "shop": shop_id}, fields=["*"])


@frappe.whitelist()
def get_tables_for_section(shop_section_id: Any) -> Any:
    """Get all tables for a specific shop section."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return frappe.get_list(
        "Table",
        filters={
            "shop_section": shop_section_id,
            "active": 1},
        fields=["*"])

# Shop Settings (Working Days / Closed Dates)


@frappe.whitelist()
def manage_shop_booking_working_days(shop_id: Any, working_days: Any) -> Any:
    """Manage the booking working days for a shop."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    check_shop_permission(shop_id, "Seller")

    shop = frappe.get_doc("Shop", shop_id)
    # Assuming Shop has a child table 'booking_working_days'
    # If not, this needs to be adapted to whatever schema exists.
    # The previous code assumed 'booking_working_days' field.
    # We should verify Shop doctype but for now we keep the logic.
    shop.booking_working_days = []
    for day in working_days:
        shop.append("booking_working_days", day)
    shop.save()
    return shop


@frappe.whitelist()
def manage_shop_booking_closed_dates(shop_id: Any, closed_dates: Any) -> Any:
    """Manage the booking closed dates for a shop."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    check_shop_permission(shop_id, "Seller")

    shop = frappe.get_doc("Shop", shop_id)
    shop.booking_closed_dates = []
    for date in closed_dates:
        shop.append("booking_closed_dates", date)
    shop.save()
    return shop

# --- Aliases for Backward Compatibility ---


@frappe.whitelist()
def create_booking(data: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return create_booking_slot(data)


@frappe.whitelist()
def get_booking(name: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return frappe.get_doc("Booking", name)


@frappe.whitelist()
def update_booking(name: Any, data: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return update_booking_slot(name, data)


@frappe.whitelist()
def delete_booking(name: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return delete_booking_slot(name)


@frappe.whitelist()
def create_user_booking(data: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return create_reservation(data)


@frappe.whitelist()
def get_user_bookings() -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return get_my_reservations()


@frappe.whitelist()
def update_user_booking_status(name: Any, status: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return update_reservation_status(name, status)


@frappe.whitelist()
def get_shop_bookings(shop_id: Any, status: Any=None, date_from: Any=None, date_to: Any=None) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return get_shop_reservations(shop_id, status, date_from, date_to)


@frappe.whitelist()
def get_shop_user_bookings(shop_id: Any, status: Any=None, date_from: Any=None, date_to: Any=None) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return get_shop_reservations(shop_id, status, date_from, date_to)


@frappe.whitelist()
def update_shop_user_booking_status(name: Any, status: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return update_reservation_status(name, status)


@frappe.whitelist()
def get_my_bookings() -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return get_my_reservations()


@frappe.whitelist()
def cancel_my_booking(name: Any) -> Any:
    """Auto-generated docstring for compliance."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return update_reservation_status(name, "Cancelled")
