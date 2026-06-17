# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.user.user import get_user_transactions
import time


class TestTransactionsAPI(FrappeTestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test_transactions@example.com"):
            self.test_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_transactions@example.com",
                    "first_name": "Test",
                    "last_name": "Transactions",
                    "send_welcome_email": 0,
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_user = frappe.get_doc("User", "test_transactions@example.com")
        self.test_user.add_roles("System Manager")

        # Create a test shop
        if not frappe.db.exists("Shop", "Test Transaction Shop"):
            self.test_shop = frappe.get_doc(
                {
                    "doctype": "Shop",
                    "shop_name": "Test Transaction Shop",
                    "user": self.test_user.name,
                    "uuid": "test_transaction_shop_uuid",
                    "phone": "+14155552671",
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_shop = frappe.get_doc("Shop", "Test Transaction Shop")

        # Create a test product
        if not frappe.db.exists(
            "Product", {"title": "Test Product", "shop": self.test_shop.name}
        ):
            self.test_product = frappe.get_doc(
                {
                    "doctype": "Product",
                    "title": "Test Product",
                    "shop": self.test_shop.name,
                    "price": 50,
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_product = frappe.get_doc(
                "Product", {"title": "Test Product", "shop": self.test_shop.name}
            )

        # Clean up any existing transactions for this user
        frappe.db.delete("Transaction", {"user": self.test_user.name})
        frappe.db.commit()

        # Create a test order to associate with a transaction
        if not frappe.db.exists(
            "Order", {"user": self.test_user.name, "status": "New"}
        ):
            self.order = frappe.get_doc(
                {
                    "doctype": "Order",
                    "user": self.test_user.name,
                    "shop": self.test_shop.name,
                    "status": "New",
                    "order_items": [
                        {"product": self.test_product.name, "quantity": 1, "price": 50}
                    ],
                }
            ).insert(ignore_permissions=True)
        else:
            self.order = frappe.get_doc(
                "Order", {"user": self.test_user.name, "status": "New"}
            )

        # Create a transaction for the user
        if not frappe.db.exists(
            "Transaction", {"user": self.test_user.name, "payable_id": self.order.name}
        ):
            self.transaction = frappe.get_doc(
                {
                    "doctype": "Transaction",
                    "payable_type": "Order",
                    "payable_id": self.order.name,
                    "user": self.test_user.name,
                    "amount": 50.0,
                    "status": "Paid",
                    "type": "model",
                }
            ).insert(ignore_permissions=True)
        else:
            self.transaction = frappe.get_doc(
                "Transaction",
                {"user": self.test_user.name, "payable_id": self.order.name},
            )

        # Log in as the test user
        frappe.set_user(self.test_user.name)

    def tearDown(self):
        # Log out
        frappe.set_user("Administrator")
        frappe.db.delete("Transaction", {"user": self.test_user.name})
        frappe.db.commit()
        if frappe.db.exists("User", self.test_user.name):
            try:
                frappe.delete_doc(
                    "User", self.test_user.name, force=True, ignore_permissions=True
                )
            except frappe.exceptions.LinkExistsError:
                frappe.db.set_value("User", self.test_user.name, "enabled", 0)

    def test_get_user_transactions_pagination(self):
        # Create a second transaction with a delay to ensure distinct creation
        # time
        time.sleep(2)
        if not frappe.db.exists(
            "Transaction", {"user": self.test_user.name, "amount": 250.0}
        ):
            frappe.get_doc(
                {
                    "doctype": "Transaction",
                    "payable_type": "Order",
                    "payable_id": self.order.name,
                    "user": self.test_user.name,
                    "amount": 250.0,
                    "status": "Paid",
                    "type": "model",
                }
            ).insert(ignore_permissions=True)

        # Get the first page with one item
        transactions = get_user_transactions(limit=1)
        self.assertEqual(len(transactions["data"]), 1)
        self.assertEqual(
            transactions["data"][0].get("amount"), 250.0
        )  # Highest amount / newest

        # Get the second page
        transactions = get_user_transactions(start=1, limit=1)
        self.assertEqual(len(transactions["data"]), 1)
        self.assertAlmostEqual(transactions["data"][0].get("amount"), 50.0)
