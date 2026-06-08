# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.booking.booking import (
    create_booking_slot,
    create_reservation,
    get_my_reservations,
    update_reservation_status,
)
from frappe.utils import add_days, now_datetime


class TestBookingFeature(FrappeTestCase):
    def setUp(self):
        # Create a Test User
        if not frappe.db.exists("User", "test_booker@example.com"):
            self.user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_booker@example.com",
                    "first_name": "Test",
                    "last_name": "Booker",
                }
            ).insert(ignore_permissions=True)
        else:
            self.user = frappe.get_doc("User", "test_booker@example.com")

        # Create a Shop
        if not frappe.db.exists("Shop", "Test Shop"):
            self.shop = frappe.get_doc(
                {
                    "doctype": "Shop",
                    "shop_name": "Test Shop",
                    "user": self.user.name,
                    "uuid": "test_booking_shop_uuid",
                    "phone": "+14155552671",
                }
            ).insert(ignore_permissions=True)
        else:
            self.shop = frappe.get_doc("Shop", "Test Shop")

        # Create a Shop Section
        if not frappe.db.exists(
            "Shop Section", {"shop": self.shop.name, "area": "Main Hall"}
        ):
            self.section = frappe.get_doc(
                {"doctype": "Shop Section", "shop": self.shop.name, "area": "Main Hall"}
            ).insert(ignore_permissions=True)
        else:
            self.section = frappe.get_doc(
                "Shop Section", {"shop": self.shop.name, "area": "Main Hall"}
            )

        # Create a Table
        if not frappe.db.exists("Table", "T1"):
            self.table = frappe.get_doc(
                {
                    "doctype": "Table",
                    "name": "T1",
                    "shop_section": self.section.name,
                    "chair_count": 4,
                }
            ).insert(ignore_permissions=True)
        else:
            self.table = frappe.get_doc("Table", "T1")

        frappe.set_user(self.user.name)

    def tearDown(self):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", self.user.name):
            try:
                frappe.delete_doc(
                    "User", self.user.name, force=True, ignore_permissions=True
                )
            except frappe.exceptions.LinkExistsError:
                frappe.db.set_value("User", self.user.name, "enabled", 0)
        # Also clean up Shop and Shop Section if needed, but User delete might cascade if Owner.
        # If Shop remains, next run uses existing Shop.
        # But reservations?
        frappe.db.delete("User Booking", {"user": "test_booker@example.com"})
        frappe.db.commit()

    def test_booking_flow(self):
        # 1. Create a Booking Slot (as Admin/Seller)
        frappe.set_user("Administrator")
        slot_data = {
            "shop": self.shop.name,
            "start_time": "10:00:00",
            "end_time": "22:00:00",
            "max_time": 60,
        }
        slot = create_booking_slot(slot_data)
        self.assertTrue(slot)

        # 2. Create a Reservation (as User)
        frappe.set_user(self.user.name)
        start_date = add_days(now_datetime(), 1)
        end_date = frappe.utils.add_to_date(start_date, hours=1)  # 1 hour later

        res_data = {
            "booking": slot.name,
            "table": self.table.name,
            "start_date": start_date,
            "end_date": end_date,
            "guest_count": 2,
            "note": "Anniversary",
        }
        reservation = create_reservation(res_data)
        self.assertEqual(reservation.status, "New")
        self.assertEqual(reservation.user, self.user.name)

        # 3. Verify Availability (Double Booking Check)
        # Attempt to book same table same time
        with self.assertRaises(frappe.ValidationError):
            create_reservation(res_data)

        # 4. Cancel Reservation
        update_reservation_status(reservation.name, "Cancelled")

        # 5. Verify Availability Again (Should be free now)
        # Note: Logic might need to filter out cancelled bookings.
        # Let's check if create_reservation succeeds now.
        reservation_2 = create_reservation(res_data)
        self.assertEqual(reservation_2.status, "New")
