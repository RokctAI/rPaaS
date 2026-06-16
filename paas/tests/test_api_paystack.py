# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt
import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, Mock
from paas.api.payment.payment import initiate_paystack_payment, handle_paystack_callback


class TestPayStackAPI(FrappeTestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test_paystack_user@example.com"):
            self.test_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_paystack_user@example.com",
                    "first_name": "Test",
                    "last_name": "User",
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_user = frappe.get_doc("User", "test_paystack_user@example.com")

        # Create a test shop
        if not frappe.db.exists("Shop", "Test PayStack Shop"):
            self.test_shop = frappe.get_doc(
                {
                    "doctype": "Shop",
                    "shop_name": "Test PayStack Shop",
                    "user": self.test_user.name,
                    "uuid": "test_paystack_shop_uuid",
                    "phone": "+14155552671",
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_shop = frappe.get_doc("Shop", "Test PayStack Shop")

        # Create a test product
        if not frappe.db.exists(
            "Product", {"title": "Test Product", "shop": self.test_shop.name}
        ):
            self.test_product = frappe.get_doc(
                {
                    "doctype": "Product",
                    "title": "Test Product",
                    "shop": self.test_shop.name,
                    "price": 100,
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_product = frappe.get_doc(
                "Product", {"title": "Test Product", "shop": self.test_shop.name}
            )

        # Create a test order
        self.test_order = frappe.get_doc(
            {
                "doctype": "Order",
                "user": self.test_user.name,
                "shop": self.test_shop.name,
                "total_price": 100,
                "currency": "USD",
                "order_items": [
                    {"product": self.test_product.name, "quantity": 1, "price": 100}
                ],
            }
        ).insert(ignore_permissions=True)

        # Create PayStack Payment Gateway
        if not frappe.db.exists("PaaS Payment Gateway", "PayStack"):
            frappe.get_doc(
                {
                    "doctype": "PaaS Payment Gateway",
                    "gateway_controller": "PayStack",
                    "is_sandbox": 1,
                    "settings": [{"key": "paystack_sk", "value": "test_secret_key"}],
                }
            ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", self.test_user.name):
            try:
                frappe.delete_doc(
                    "User", self.test_user.name, force=True, ignore_permissions=True
                )
            except (
                frappe.LinkExistsError,
                frappe.exceptions.LinkExistsError,
                Exception,
            ):
                try:
                    frappe.db.set_value("User", self.test_user.name, "enabled", 0)
                    frappe.db.commit()
                except Exception:
                    pass

        if (
            hasattr(self, "test_shop")
            and self.test_shop
            and frappe.db.exists("Shop", self.test_shop.name)
        ):
            try:
                frappe.delete_doc(
                    "Shop", self.test_shop.name, force=True, ignore_permissions=True
                )
            except Exception:
                pass

    @patch("paas.api.payment.payment.requests.post")
    def test_initiate_paystack_payment(self, mock_post):
        # Mock the response from PayStack API
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/test_url",
                "reference": "test_reference",
            },
        }
        mock_post.return_value = mock_response

        response = initiate_paystack_payment(self.test_order.name)

        self.assertIn("redirect_url", response)
        self.assertIn("test_url", response["redirect_url"])

        # Verify a transaction was created
        self.assertTrue(
            frappe.db.exists("Transaction", {"payment_reference": "test_reference"})
        )

    @patch("paas.api.payment.payment.requests.get")
    def test_handle_paystack_callback(self, mock_get):
        # Create a dummy transaction to be updated by the callback
        frappe.get_doc(
            {
                "doctype": "Transaction",
                "payable_type": "Order",
                "payable_id": self.test_order.name,
                "payment_reference": "test_reference_callback",
                "status": "Pending",
            }
        ).insert(ignore_permissions=True)

        # Mock the response from PayStack API
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"status": "success"}}
        mock_get.return_value = mock_response

        # Simulate a callback from PayStack
        with patch("frappe.form_dict", {"reference": "test_reference_callback"}):
            handle_paystack_callback()

        # Check if the transaction and order status were updated
        updated_transaction = frappe.get_doc(
            "Transaction", {"payment_reference": "test_reference_callback"}
        )
        self.assertEqual(updated_transaction.status, "Paid")

        updated_order = frappe.get_doc("Order", self.test_order.name)
        self.assertEqual(updated_order.status, "Paid")
