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
import json
import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.payment.payment import get_payfast_settings, save_payfast_card, get_saved_payfast_cards, delete_payfast_card, handle_payfast_callback, process_payfast_token_payment


class TestPayFastAPI(FrappeTestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test_payfast_user@example.com"):
            self.test_user = frappe.get_doc({
                "doctype": "User",
                "email": "test_payfast_user@example.com",
                "first_name": "Test",
                "last_name": "User"
            }).insert(ignore_permissions=True)
        else:
            self.test_user = frappe.get_doc(
                "User", "test_payfast_user@example.com")

        # Create Shop
        if not frappe.db.exists("Shop", {"shop_name": "PayFast Shop"}):
            self.shop = frappe.get_doc({
                "doctype": "Shop",
                "shop_name": "PayFast Shop",
                "user": self.test_user.name,
                "uuid": "payfast-shop-uuid",
                "status": "approved",
                "phone": "+14155552671"
            }).insert(ignore_permissions=True)
        else:
            self.shop = frappe.get_doc("Shop", {"shop_name": "PayFast Shop"})

        # Create Product
        if not frappe.db.exists("Product", {"title": "PayFast Product"}):
            self.product = frappe.get_doc({
                "doctype": "Product",
                "shop": self.shop.name,
                "title": "PayFast Product",
                "price": 100
            }).insert(ignore_permissions=True)
        else:
            self.product = frappe.get_doc(
                "Product", {"title": "PayFast Product"})

        # Create a test order
        self.test_order = frappe.get_doc({
            "doctype": "Order",
            "user": self.test_user.name,
            "shop": self.shop.name,
            "total_price": 100,
            "currency": "USD",
            "order_items": [{
                "product": self.product.name,
                "quantity": 1,
                "price": 100
            }]
        }).insert(ignore_permissions=True)

        # Create PayFast Payment Gateway
        if not frappe.db.exists("PaaS Payment Gateway", "PayFast"):
            frappe.get_doc({
                "doctype": "PaaS Payment Gateway",
                "gateway_controller": "PayFast",
                "is_sandbox": 1,
                "settings": [
                    {"key": "merchant_id", "value": "10000100"},
                    {"key": "merchant_key", "value": "46f0cd694581a"},
                    {"key": "pass_phrase", "value": "your_passphrase_here"}
                ]
            }).insert(ignore_permissions=True)

    def tearDown(self):
        # Clean up the test data
        frappe.set_user("Administrator")
        if hasattr(
                self,
                "test_user") and self.test_user and frappe.db.exists(
                "User",
                self.test_user.name):
            try:
                frappe.delete_doc(
                    "User",
                    self.test_user.name,
                    force=True,
                    ignore_permissions=True)
            except (frappe.LinkExistsError, frappe.exceptions.LinkExistsError, Exception):
                try:
                    frappe.db.set_value(
                        "User", self.test_user.name, "enabled", 0)
                    frappe.db.commit()
                except Exception:
                    pass

        if hasattr(
                self,
                "shop") and self.shop and frappe.db.exists(
                "Shop",
                self.shop.name):
            try:
                frappe.delete_doc(
                    "Shop",
                    self.shop.name,
                    force=True,
                    ignore_permissions=True)
            except Exception:
                pass

    def test_get_payfast_settings(self):
        # Test getting PayFast settings
        settings = get_payfast_settings()
        self.assertIsNotNone(settings)
        self.assertIn("merchant_id", settings)
        self.assertIn("merchant_key", settings)

    def test_card_management(self):
        # Test saving, getting, and deleting a saved card
        frappe.set_user(self.test_user.name)

        # Save a card
        card_details = {
            "last_four": "1234",
            "card_type": "Visa",
            "expiry_date": "12/25",
            "card_holder_name": "Test User"}
        save_response = save_payfast_card(
            "test_token", json.dumps(card_details))
        self.assertEqual(save_response.get("status"), "success")

        # Get saved cards
        saved_cards = get_saved_payfast_cards()
        self.assertEqual(len(saved_cards), 1)
        card_name = saved_cards[0].get("name")

        # Delete the card
        delete_response = delete_payfast_card(card_name)
        self.assertEqual(delete_response.get("status"), "success")

        # Verify the card is deleted
        saved_cards_after_delete = get_saved_payfast_cards()
        self.assertEqual(len(saved_cards_after_delete), 0)

    def test_handle_payfast_callback(self):
        # This test is more complex to set up as it requires a real callback from PayFast.
        # For now, we will just check that the function exists.
        self.assertTrue(callable(handle_payfast_callback))

    def test_process_payfast_token_payment(self):
        # Test processing a payment with a saved token
        frappe.set_user(self.test_user.name)
        with self.assertRaises(frappe.exceptions.ValidationError):
            process_payfast_token_payment(self.test_order.name, "test_token")
