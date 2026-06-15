# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.user.user import create_order_refund, get_user_order_refunds


class TestOrderRefundsAPI(FrappeTestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test_refunds@example.com"):
            self.test_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_refunds@example.com",
                    "first_name": "Test",
                    "last_name": "Refunds",
                    "send_welcome_email": 0,
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_user = frappe.get_doc("User", "test_refunds@example.com")
        self.test_user.add_roles("System Manager")

        # Create a test shop
        if not frappe.db.exists("Shop", "Test Refund Shop"):
            self.test_shop = frappe.get_doc(
                {
                    "doctype": "Shop",
                    "shop_name": "Test Refund Shop",
                    "user": self.test_user.name,
                    "uuid": "test_refund_shop_uuid",
                    "phone": "+14155552671",
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_shop = frappe.get_doc("Shop", "Test Refund Shop")

        # Create a test product
        if not frappe.db.exists(
            "Product", {"title": "Test Refund Product", "shop": self.test_shop.name}
        ):
            self.test_product = frappe.get_doc(
                {
                    "doctype": "Product",
                    "title": "Test Refund Product",
                    "shop": self.test_shop.name,
                    "price": 50,
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_product = frappe.get_doc(
                "Product", {"title": "Test Refund Product", "shop": self.test_shop.name}
            )

        # Create a test order
        if not frappe.db.exists(
            "Order", {"user": self.test_user.name, "status": "Delivered"}
        ):
            self.order = frappe.get_doc(
                {
                    "doctype": "Order",
                    "user": self.test_user.name,
                    "shop": self.test_shop.name,
                    "status": "Delivered",
                    "order_items": [
                        {"product": self.test_product.name, "quantity": 1, "price": 50}
                    ],
                }
            ).insert(ignore_permissions=True)
        else:
            self.order = frappe.get_doc(
                "Order", {"user": self.test_user.name, "status": "Delivered"}
            )

        # Log in as the test user
        frappe.set_user(self.test_user.name)

    def tearDown(self):
        # Log out
        frappe.set_user("Administrator")
        if frappe.db.exists("User", self.test_user.name):
            try:
                frappe.delete_doc(
                    "User", self.test_user.name, force=True, ignore_permissions=True
                )
            except frappe.exceptions.LinkExistsError:
                frappe.db.set_value("User", self.test_user.name, "enabled", 0)

    def test_create_and_get_order_refund(self):
        refund = create_order_refund(order=self.order.name, cause="Item was damaged")
        self.assertEqual(refund.get("order"), self.order.name)
        self.assertEqual(refund.get("cause"), "Item was damaged")
        self.assertEqual(refund.get("status"), "Pending")

        refunds = get_user_order_refunds()
        self.assertEqual(len(refunds), 1)
        self.assertEqual(refunds[0].get("order"), self.order.name)

    def test_permission_on_create_refund(self):
        # Create another user
        other_user = frappe.get_doc(
            {
                "doctype": "User",
                "email": "other_refund@example.com",
                "first_name": "Other",
            }
        ).insert(ignore_permissions=True)

        # Log in as other_user
        frappe.set_user(other_user.name)

        # other_user should not be able to create a refund for self.order
        with self.assertRaises(frappe.PermissionError):
            create_order_refund(order=self.order.name, cause="I want a refund")

        # Clean up
        frappe.set_user("Administrator")
        other_user.delete(ignore_permissions=True)
