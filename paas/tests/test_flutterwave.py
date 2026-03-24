# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt
import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock
from paas.api.payment.payment import initiate_flutterwave_payment, flutterwave_callback


class TestFlutterwave(FrappeTestCase):

    def setUp(self):
        # Save original state to restore in tearDown
        self._original_session_user = frappe.session.user
        self._original_request = getattr(frappe, "request", None)
        self._original_response = getattr(frappe.local, "response", None)

        # Create a mock user
        self.user = MagicMock()
        self.user.name = "test@example.com"
        frappe.session.user = self.user.name

        # Create a mock order
        self.order = MagicMock()
        self.order.name = "TEST-ORDER-001"
        self.order.user = self.user.name
        self.order.owner = self.user.name
        self.order.payment_status = "Pending"
        self.order.grand_total = 100.00

        # Create mock Flutterwave settings
        self.flutterwave_settings = MagicMock()
        self.flutterwave_settings.enabled = 1
        self.flutterwave_settings.get_password.return_value = "test_secret_key"
        self.flutterwave_settings.success_redirect_url = "https://test.com/success"
        self.flutterwave_settings.failure_redirect_url = "https://test.com/failure"

        # Patch get_website_settings to return a dummy logo
        self.patcher_settings = patch(
            "frappe.get_website_settings",
            return_value="http://test.com/logo.png")
        self.patcher_settings.start()

    def tearDown(self):
        # Restore original state
        frappe.session.user = self._original_session_user
        if hasattr(frappe, "request"):
            frappe.request = self._original_request
        if hasattr(frappe.local, "response"):
            frappe.local.response = self._original_response
        frappe.set_user("Administrator")
        self.patcher_settings.stop()

    @patch('paas.api.payment.payment.frappe.db.commit')
    @patch('paas.api.payment.payment.frappe.get_doc')
    @patch('paas.api.payment.payment.requests.post')
    def test_initiate_flutterwave_payment_success(
            self, mock_post, mock_get_doc, mock_commit):
        # Arrange
        mock_get_doc.side_effect = [
            self.order, self.flutterwave_settings, self.user]

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "success",
            "data": {"link": "https://flutterwave.com/pay/test"}
        }
        mock_post.return_value = mock_response

        # Act
        result = initiate_flutterwave_payment(self.order.name)

        # Assert
        self.assertEqual(
            result, {
                "payment_url": "https://flutterwave.com/pay/test"})
        self.order.save.assert_called_once()
        mock_commit.assert_called_once()
        self.assertIn(
            "TEST-ORDER-001",
            self.order.custom_payment_transaction_id)

    @patch('paas.api.payment.payment.frappe.get_doc')
    def test_initiate_flutterwave_payment_already_paid(self, mock_get_doc):
        # Arrange
        self.order.payment_status = "Paid"
        mock_get_doc.return_value = self.order

        # Act & Assert
        with self.assertRaises(frappe.ValidationError):
            initiate_flutterwave_payment(self.order.name)

    @patch('paas.api.payment.payment.frappe.db.commit')
    @patch('paas.api.payment.payment.frappe.get_doc')
    @patch('paas.api.payment.payment.requests.get')
    def test_flutterwave_callback_success(
            self, mock_get, mock_get_doc, mock_commit):
        # Arrange
        mock_get_doc.side_effect = [self.flutterwave_settings, self.order]

        mock_verification_response = MagicMock()
        mock_verification_response.json.return_value = {
            "status": "success",
            "data": {
                "tx_ref": "TEST-ORDER-001-12345",
                "amount": 100.00
            }
        }
        mock_get.return_value = mock_verification_response

        frappe.request = MagicMock()
        frappe.request.args = {
            "status": "successful",
            "tx_ref": "TEST-ORDER-001-12345",
            "transaction_id": "FLW-TXN-123"
        }
        frappe.local.response = {}

        # Act
        flutterwave_callback()

        # Assert
        self.assertEqual(self.order.payment_status, "Paid")
        self.assertEqual(
            self.order.custom_payment_transaction_id,
            "FLW-TXN-123")
        self.order.save.assert_called_once()
        mock_commit.assert_called_once()
        self.assertEqual(frappe.local.response["type"], "redirect")
        self.assertEqual(
            frappe.local.response["location"],
            self.flutterwave_settings.success_redirect_url)

    @patch('paas.api.payment.payment.frappe.db.commit')
    @patch('paas.api.payment.payment.frappe.get_doc')
    def test_flutterwave_callback_cancelled(self, mock_get_doc, mock_commit):
        # Arrange
        mock_get_doc.side_effect = [self.flutterwave_settings, self.order]

        frappe.request = MagicMock()
        frappe.request.args = {
            "status": "cancelled",
            "tx_ref": "TEST-ORDER-001-12345",
        }
        frappe.local.response = {}

        # Act
        flutterwave_callback()

        # Assert
        self.assertEqual(self.order.payment_status, "Failed")
        self.order.save.assert_called_once()
        mock_commit.assert_called_once()
        self.assertEqual(frappe.local.response["type"], "redirect")
        self.assertIn(
            self.flutterwave_settings.failure_redirect_url,
            frappe.local.response["location"])
        self.assertIn("reason=cancelled", frappe.local.response["location"])
