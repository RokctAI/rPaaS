# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt
import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.order.order import create_order, list_orders, get_order_details, update_order_status, add_order_review, cancel_order
import json


class TestOrderAPI(FrappeTestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test_order_user@example.com"):
            self.test_user = frappe.get_doc({
                "doctype": "User",
                "email": "test_order_user@example.com",
                "first_name": "Test",
                "last_name": "User"
            }).insert(ignore_permissions=True)
        else:
            self.test_user = frappe.get_doc(
                "User", "test_order_user@example.com")

        # Create a test shop
        if not frappe.db.exists("Shop", "Test Order Shop"):
            self.test_shop = frappe.get_doc({
                "doctype": "Shop",
                "shop_name": "Test Order Shop",
                "user": self.test_user.name,
                "uuid": "test_order_shop_uuid",
                "tax": 10,
                "phone": "+14155552671"
            }).insert(ignore_permissions=True)
        else:
            self.test_shop = frappe.get_doc("Shop", "Test Order Shop")

        # Update Permission Settings
        if frappe.db.exists("Permission Settings", "Permission Settings"):
            permission_settings = frappe.get_doc(
                "Permission Settings", "Permission Settings")
            permission_settings.service_fee = 10
            permission_settings.save(ignore_permissions=True)

        # Create a test product
        if not frappe.db.exists("Product",
                                {"title": "Test Order Product",
                                 "shop": self.test_shop.name}):
            self.test_product = frappe.get_doc({
                "doctype": "Product",
                "title": "Test Order Product",
                "shop": self.test_shop.name,
                "price": 100
            }).insert(ignore_permissions=True)
        else:
            self.test_product = frappe.get_doc(
                "Product", {"title": "Test Order Product", "shop": self.test_shop.name})

        # Ensure USD currency exists
        if not frappe.db.exists("Currency", "USD"):
            frappe.get_doc({
                "doctype": "Currency",
                "currency_name": "USD",
                "symbol": "$",
                "enabled": 1
            }).insert(ignore_permissions=True)
        self.test_currency = "USD"

        # Create Stock record
        if not frappe.db.exists("Stock",
                                {"shop": self.test_shop.name,
                                 "product": self.test_product.name}):
            self.test_stock = frappe.get_doc({
                "doctype": "Stock",
                "shop": self.test_shop.name,
                "product": self.test_product.name,
                "price": 100,
                "quantity": 10
            }).insert(ignore_permissions=True)
        else:
            self.test_stock = frappe.get_doc(
                "Stock", {"shop": self.test_shop.name, "product": self.test_product.name})
            self.test_stock.quantity = 10
            self.test_stock.save(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", self.test_user.name):
            try:
                frappe.delete_doc(
                    "User",
                    self.test_user.name,
                    force=True,
                    ignore_permissions=True)
            except (frappe.LinkExistsError, frappe.exceptions.LinkExistsError, Exception):
                frappe.db.set_value("User", self.test_user.name, "enabled", 0)
                frappe.db.commit()

        if hasattr(
                self,
                "test_shop") and self.test_shop and frappe.db.exists(
                "Shop",
                self.test_shop.name):
            try:
                # Cleanup products for this shop first
                frappe.db.delete("Product", {"shop": self.test_shop.name})
                frappe.delete_doc(
                    "Shop",
                    self.test_shop.name,
                    force=True,
                    ignore_permissions=True)
            except Exception:
                pass

    def test_create_order_and_calculation(self):
        # Test creating a new order and that the calculation is correct
        order_data = {
            "user": self.test_user.name,
            "shop": self.test_shop.name,
            "delivery_type": "Delivery",
            "currency": self.test_currency,
            "rate": 1,
            "order_items": [
                {
                    "product": self.test_product.name,
                    "quantity": 2,
                    "price": 100
                }
            ]
        }
        order_dict = create_order(json.dumps(order_data))
        self.assertIsNotNone(order_dict)

        order = frappe.get_doc("Order", order_dict["data"].get("name"))
        # 2 * 100 = 200 (subtotal)
        # + 10% tax = 220
        # + 10 service fee = 230
        self.assertEqual(order.total_price, 230)

    def test_list_orders(self):
        # Test listing orders for the current user
        frappe.set_user(self.test_user.name)
        orders = list_orders()
        self.assertIsNotNone(orders)
        self.assertIsInstance(orders["data"], list)

    def test_get_order_details(self):
        # Test getting the details of a specific order
        order = frappe.get_doc({
            "doctype": "Order",
            "user": self.test_user.name,
            "shop": self.test_shop.name,
            "order_items": [
                {
                    "product": self.test_product.name,
                    "quantity": 1,
                    "price": 100
                }
            ]
        }).insert(ignore_permissions=True)
        frappe.set_user(self.test_user.name)
        order_details = get_order_details(order.name)
        self.assertIsNotNone(order_details)
        self.assertEqual(order_details["data"].get("name"), order.name)

    def test_update_order_status(self):
        # Test updating the status of an order
        order = frappe.get_doc({
            "doctype": "Order",
            "user": self.test_user.name,
            "shop": self.test_shop.name,
            "order_items": [
                {
                    "product": self.test_product.name,
                    "quantity": 1,
                    "price": 100
                }
            ]
        }).insert(ignore_permissions=True)
        frappe.set_user(self.test_user.name)
        updated_order = update_order_status(order.name, "Accepted")
        self.assertIsNotNone(updated_order)
        self.assertEqual(updated_order["data"].get("status"), "Accepted")

        # Verify Stock reduction
        self.test_stock.reload()
        # Started with 10, ordered 1 -> should be 9
        self.assertEqual(self.test_stock.quantity, 9)

    def test_add_order_review(self):
        # Test adding a review to an order
        order = frappe.get_doc({
            "doctype": "Order",
            "user": self.test_user.name,
            "shop": self.test_shop.name,
            "status": "Delivered",
            "order_items": [
                {
                    "product": self.test_product.name,
                    "quantity": 1,
                    "price": 100
                }
            ]
        }).insert(ignore_permissions=True)

        frappe.set_user(self.test_user.name)
        review = add_order_review(order.name, 5, "Great service!")
        self.assertIsNotNone(review)
        self.assertEqual(review["data"].get("rating"), 5)
        self.assertEqual(review["data"].get("comment"), "Great service!")

    def test_cancel_order(self):
        # Test cancelling an order
        order = frappe.get_doc({
            "doctype": "Order",
            "user": self.test_user.name,
            "shop": self.test_shop.name,
            "status": "New",
            "order_items": [
                {
                    "product": self.test_product.name,
                    "quantity": 1,
                    "price": 100
                }
            ]
        }).insert(ignore_permissions=True)
        frappe.set_user(self.test_user.name)
        cancelled_order = cancel_order(order.name)
        self.assertIsNotNone(cancelled_order)
        self.assertEqual(cancelled_order["data"].get("status"), "Cancelled")

        # Verify Stock is UNCHANGED for New -> Cancelled
        self.test_stock.reload()
        self.assertEqual(self.test_stock.quantity, 10)

    def test_cancel_accepted_order(self):
        # Test cancelling an accepted order via status update
        order = frappe.get_doc({
            "doctype": "Order",
            "user": self.test_user.name,
            "shop": self.test_shop.name,
            "status": "New",
            "order_items": [
                {
                    "product": self.test_product.name,
                    "quantity": 1,
                    "price": 100
                }
            ]
        }).insert(ignore_permissions=True)

        # Though update requires admin/shop owner usually tested as admin in
        # tearDown but here set_user
        frappe.set_user(self.test_user.name)
        # We need update_order_status to work.

        # 1. Accept Order -> Stock -1
        update_order_status(order.name, "Accepted")
        self.test_stock.reload()
        self.assertEqual(self.test_stock.quantity, 9)

        # 2. Cancel Order -> Stock +1
        # update_order_status handles the transition
        update_order_status(order.name, "Cancelled")
        self.test_stock.reload()
        self.assertEqual(self.test_stock.quantity, 10)
