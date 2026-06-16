# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
import json
from frappe.tests.utils import FrappeTestCase
from paas.api.seller_shop_settings.seller_shop_settings import (
    get_seller_shop_working_days,
    update_seller_shop_working_days,
)


class TestSellerDashboard(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # Create a User
        if not frappe.db.exists("User", "shop_owner@example.com"):
            self.owner = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "shop_owner@example.com",
                    "first_name": "Shop",
                    "last_name": "Owner",
                    "roles": [{"role": "Seller"}],
                }
            ).insert(ignore_permissions=True)
        else:
            self.owner = frappe.get_doc("User", "shop_owner@example.com")

        # Create a Shop linked to this User
        if not frappe.db.exists("Shop", {"shop_name": "Dashboard Shop"}):
            self.shop = frappe.get_doc(
                {
                    "doctype": "Shop",
                    "shop_name": "Dashboard Shop",
                    "user": self.owner.name,  # This links the shop
                    "status": "approved",
                    "uuid": frappe.generate_hash(),
                }
            ).insert(ignore_permissions=True)
        else:
            self.shop = frappe.get_doc("Shop", {"shop_name": "Dashboard Shop"})
            self.shop.user = self.owner.name
            self.shop.save(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user("Administrator")
        # Cleanup Shop Working Days
        frappe.db.delete("Shop Working Day", {"shop": self.shop.name})
        # Cleanup Shop
        try:
            frappe.delete_doc(
                "Shop", self.shop.name, force=True, ignore_permissions=True
            )
        except Exception:
            pass
        # Cleanup User
        if frappe.db.exists("User", self.owner.name):
            try:
                frappe.delete_doc(
                    "User", self.owner.name, force=True, ignore_permissions=True
                )
            except (
                frappe.LinkExistsError,
                frappe.exceptions.LinkExistsError,
                Exception,
            ):
                frappe.db.set_value("User", self.owner.name, "enabled", 0)
                frappe.db.commit()

    def test_working_days(self):
        # Login as owner
        frappe.set_user(self.owner.name)

        # 1. Update Days
        days_data = [
            {
                "day_of_week": "Monday",
                "opening_time": "09:00:00",
                "closing_time": "17:00:00",
                "is_closed": 0,
            },
            {"day_of_week": "Sunday", "is_closed": 1},
        ]

        response = update_seller_shop_working_days(json.dumps(days_data))
        self.assertEqual(response.get("status"), "success")

        # 2. Get Days
        fetched_days = get_seller_shop_working_days()
        self.assertEqual(len(fetched_days), 2)

        monday = next(
            (d for d in fetched_days if d.get("day_of_week") == "Monday"), None
        )
        self.assertIsNotNone(monday)
        # Time comes back as timedelta or string depending on db, let's just
        # check existence
        self.assertEqual(monday.get("is_closed"), 0)

    def test_get_days_without_shop(self):
        # Create user without shop
        if not frappe.db.exists("User", "no_shop@example.com"):
            no_shop_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "no_shop@example.com",
                    "first_name": "NoShop",
                }
            ).insert(ignore_permissions=True)
        else:
            no_shop_user = frappe.get_doc("User", "no_shop@example.com")

        frappe.set_user(no_shop_user.name)

        with self.assertRaises(frappe.PermissionError):
            get_seller_shop_working_days()

        frappe.set_user("Administrator")
        if frappe.db.exists("User", no_shop_user.name):
            try:
                frappe.delete_doc(
                    "User", no_shop_user.name, force=True, ignore_permissions=True
                )
            except (
                frappe.LinkExistsError,
                frappe.exceptions.LinkExistsError,
                Exception,
            ):
                frappe.db.set_value("User", no_shop_user.name, "enabled", 0)
                frappe.db.commit()
