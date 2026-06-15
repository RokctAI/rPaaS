# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt
import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, Mock
from paas.api.payment.payment import initiate_paypal_payment, handle_paypal_callback


class TestPayPalAPI(FrappeTestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test_paypal_user@example.com"):
            self.test_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_paypal_user@example.com",
                    "first_name": "Test",
                    "last_name": "User",
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_user = frappe.get_doc("User", "test_paypal_user@example.com")

        # Create Shop
        if not frappe.db.exists("Shop", {"shop_name": "PayPal Shop"}):
            self.shop = frappe.get_doc(
                {
                    "doctype": "Shop",
                    "shop_name": "PayPal Shop",
                    "user": self.test_user.name,
                    "uuid": "paypal-shop-uuid",
                    "status": "approved",
                    "phone": "+14155552671",
                }
            ).insert(ignore_permissions=True)
        else:
            self.shop = frappe.get_doc("Shop", {"shop_name": "PayPal Shop"})

        # Create Product
        if not frappe.db.exists("Product", {"title": "PayPal Product"}):
            self.product = frappe.get_doc(
                {
                    "doctype": "Product",
                    "shop": self.shop.name,
                    "title": "PayPal Product",
                    "price": 100,
                }
            ).insert(ignore_permissions=True)
        else:
            self.product = frappe.get_doc("Product", {"title": "PayPal Product"})

        # Create a test order
        self.test_order = frappe.get_doc(
            {
                "doctype": "Order",
                "user": self.test_user.name,
                "shop": self.shop.name,
                "total_price": 100,
                "currency": "USD",
                "order_items": [
                    {"product": self.product.name, "quantity": 1, "price": 100}
                ],
            }
        ).insert(ignore_permissions=True)

        # Create PayPal Payment Gateway
        if not frappe.db.exists("PaaS Payment Gateway", "PayPal"):
            frappe.get_doc(
                {
                    "doctype": "PaaS Payment Gateway",
                    "gateway_controller": "PayPal",
                    "is_sandbox": 1,
                    "settings": [
                        {"key": "paypal_sandbox_client_id", "value": "test_client_id"},
                        {"key": "paypal_sandbox_client_secret", "value": "test_secret"},
                        {"key": "paypal_mode", "value": "sandbox"},
                    ],
                }
            ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user("Administrator")
        if (
            hasattr(self, "test_user")
            and self.test_user
            and frappe.db.exists("User", self.test_user.name)
        ):
            try:
                frappe.delete_doc(
                    "User", self.test_user.name, ignore_permissions=True, force=True
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
            hasattr(self, "shop")
            and self.shop
            and frappe.db.exists("Shop", self.shop.name)
        ):
            try:
                frappe.delete_doc(
                    "Shop", self.shop.name, force=True, ignore_permissions=True
                )
            except Exception:
                pass

    @patch("paas.api.payment.payment.requests.post")
    def test_initiate_paypal_payment(self, mock_post):
        # Mock the responses from PayPal API
        mock_auth_response = Mock()
        mock_auth_response.json.return_value = {"access_token": "test_access_token"}

        mock_order_response = Mock()
        mock_order_response.json.return_value = {
            "id": "test_paypal_order_id",
            "links": [
                {
                    "rel": "approve",
                    "href": "https://www.sandbox.paypal.com/checkoutnow?token=test_paypal_order_id",
                }
            ],
        }

        mock_post.side_effect = [mock_auth_response, mock_order_response]

        response = initiate_paypal_payment(self.test_order.name)

        self.assertIn("redirect_url", response)
        self.assertIn("test_paypal_order_id", response["redirect_url"])

        self.assertTrue(
            frappe.db.exists(
                "Transaction", {"payment_reference": "test_paypal_order_id"}
            )
        )

    @patch("paas.api.payment.payment.requests.get")
    @patch("paas.api.payment.payment.requests.post")
    def test_handle_paypal_callback(self, mock_post, mock_get):
        # Create a dummy transaction to be updated by the callback
        frappe.get_doc(
            {
                "doctype": "Transaction",
                "payable_type": "Order",
                "payable_id": self.test_order.name,
                "payment_reference": "test_paypal_order_id_callback",
                "status": "Pending",
            }
        ).insert(ignore_permissions=True)

        # Mock the responses from PayPal API
        mock_auth_response = Mock()
        mock_auth_response.json.return_value = {"access_token": "test_access_token"}
        mock_post.return_value = mock_auth_response

        mock_order_response = Mock()
        mock_order_response.json.return_value = {"status": "COMPLETED"}
        mock_get.return_value = mock_order_response

        # Simulate a callback from PayPal
        with patch("frappe.form_dict", {"token": "test_paypal_order_id_callback"}):
            handle_paypal_callback()

        # Check if the transaction and order status were updated
        updated_transaction = frappe.get_doc(
            "Transaction", {"payment_reference": "test_paypal_order_id_callback"}
        )
        self.assertEqual(updated_transaction.status, "Paid")

        updated_order = frappe.get_doc("Order", self.test_order.name)
        self.assertEqual(updated_order.status, "Paid")
