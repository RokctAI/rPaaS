# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock
from paas.api.user.user import (
    check_phone,
    send_phone_verification_code,
    verify_phone_code,
    forgot_password,
    register_user,
)
from paas.api.utils import api_response
from paas.api.system.system import get_global_settings

# Mock functions if they don't exist yet/aren't imported


def get_languages():
    return api_response(data=[{"name": "en"}])


def get_currencies():
    return api_response(data=[{"name": "USD"}])


def api_status():
    return api_response(
        data={"status": "ok", "version": "1.0", "user": frappe.session.user}
    )


class TestPhoneVerificationAPI(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field

        create_custom_field(
            "User",
            {
                "fieldname": "phone_verified_at",
                "fieldtype": "Datetime",
                "label": "Phone Verified At",
                "insert_after": "phone",
                "read_only": 1,
            },
        )
        create_custom_field(
            "User",
            {
                "fieldname": "email_verification_token",
                "fieldtype": "Data",
                "label": "Email Verification Token",
                "insert_after": "phone_verified_at",
                "read_only": 1,
                "hidden": 1,
            },
        )

    def setUp(self):
        # Create a test user
        self.test_user_phone = "+19876543210"

        # Cleanup potential duplicates to ensure API targets the correct user
        frappe.db.delete("User", {"phone": self.test_user_phone})
        if frappe.db.exists("User", "test_phone_user@example.com"):
            try:
                frappe.delete_doc(
                    "User",
                    "test_phone_user@example.com",
                    force=True,
                    ignore_permissions=True,
                )
            except (
                frappe.LinkExistsError,
                frappe.exceptions.LinkExistsError,
                Exception,
            ):
                frappe.db.set_value("User", "test_phone_user@example.com", "enabled", 0)
                frappe.db.commit()

        self.test_user = frappe.get_doc(
            {
                "doctype": "User",
                "email": "test_phone_user@example.com",
                "first_name": "Test",
                "last_name": "User",
                "phone": self.test_user_phone,
            }
        ).insert(ignore_permissions=True)

    def tearDown(self):
        pass

    def test_check_phone_exists(self):
        response = check_phone(phone=self.test_user_phone)
        self.assertEqual(response.get("data").get("status"), "error")
        self.assertEqual(response.get("message"), "Phone number already exists.")

    def test_check_phone_not_exists(self):
        response = check_phone(phone="+10123456789")
        self.assertEqual(response.get("data").get("status"), "success")
        self.assertEqual(response.get("message"), "Phone number is available.")

    def test_check_phone_missing_param(self):
        with self.assertRaises(frappe.ValidationError):
            check_phone(phone="")

    @patch("frappe.send_sms", create=True)
    @patch("frappe.cache.set_value")
    def test_send_verification_code(self, mock_set_value, mock_send_sms):
        phone_number = "+11223344556"
        response = send_phone_verification_code(phone=phone_number)

        self.assertEqual(
            response.get("message"), "Verification code sent successfully."
        )

        # Check that cache was called correctly
        args, kwargs = mock_set_value.call_args
        self.assertEqual(args[0], f"phone_otp:{phone_number}")
        self.assertTrue(args[1].isdigit())
        self.assertEqual(len(args[1]), 6)
        self.assertEqual(kwargs["expires_in_sec"], 600)

        # Check that SMS was sent correctly
        otp = args[1]
        mock_send_sms.assert_called_once_with(
            receivers=[phone_number], message=f"Your verification code is: {otp}"
        )

    @patch("frappe.cache.get_value")
    @patch("frappe.cache.delete_value")
    def test_verify_code_correct(self, mock_delete_value, mock_get_value):
        phone_number = self.test_user_phone
        correct_otp = "123456"

        def get_value_side_effect(key, *args, **kwargs):
            if isinstance(key, str) and key.startswith("phone_otp:"):
                return correct_otp
            return None

        mock_get_value.side_effect = get_value_side_effect

        response = verify_phone_code(phone=phone_number, otp=correct_otp)

        self.assertEqual(response.get("message"), "Phone number verified successfully.")

        # Verify user's phone_verified_at is set
        self.test_user.reload()
        self.assertIsNotNone(self.test_user.phone_verified_at)

        # Verify cache deletion
        # assert that our key was deleted at least once
        mock_delete_value.assert_any_call(f"phone_otp:{phone_number}")

    @patch("frappe.cache.get_value")
    @patch("frappe.cache.delete_value")
    def test_verify_code_incorrect(self, mock_delete_value, mock_get_value):
        phone_number = self.test_user_phone
        correct_otp = "123456"
        incorrect_otp = "654321"

        def get_value_side_effect(key, *args, **kwargs):
            if isinstance(key, str) and key.startswith("phone_otp:"):
                return correct_otp
            return None

        mock_get_value.side_effect = get_value_side_effect

        response = verify_phone_code(phone=phone_number, otp=incorrect_otp)

        self.assertEqual(response.get("status_code"), 400)
        self.assertEqual(response.get("message"), "Invalid verification code.")

        # Verify user's phone_verified_at is NOT set
        self.test_user.reload()
        self.assertIsNone(self.test_user.phone_verified_at)

        # Verify cache was not deleted for our key
        # Check that none of the calls were for our key
        call_args_list = mock_delete_value.call_args_list
        for call in call_args_list:
            args, _ = call
            if args and args[0] == f"phone_otp:{phone_number}":
                self.fail(f"Cache deletion called for {args[0]} unexpectedly")

    @patch("frappe.cache.get_value")
    def test_verify_code_expired(self, mock_get_value):
        mock_get_value.return_value = None

        response = verify_phone_code(phone=self.test_user_phone, otp="123456")

        self.assertEqual(response.get("status_code"), 400)
        self.assertEqual(
            response.get("message"),
            "OTP expired or was not sent. Please request a new one.",
        )

    def test_api_status(self):
        # Act
        response = api_status()

        # Assert
        self.assertEqual(response.get("data").get("status"), "ok")
        self.assertIn("version", response.get("data"))
        self.assertIn("user", response.get("data"))

    @patch("frappe.sendmail")
    def test_forgot_password(self, mock_sendmail):
        # Arrange
        # from paas.api import forgot_password

        # Act
        response = forgot_password(user=self.test_user.email)

        # Assert
        self.assertIn("password reset code has been sent", response.get("message"))
        mock_sendmail.assert_called_once()

    def test_get_languages(self):
        # Arrange
        # Arrange
        # from paas.api import get_languages
        # Ensure there is at least one enabled and one disabled language
        if not frappe.db.exists("Language", "en"):
            frappe.get_doc(
                {
                    "doctype": "Language",
                    "language_code": "en",
                    "language_name": "English",
                    "enabled": 1,
                }
            ).insert()
        if not frappe.db.exists("Language", "tlh"):
            frappe.get_doc(
                {
                    "doctype": "Language",
                    "language_code": "tlh",
                    "language_name": "Klingon",
                    "enabled": 0,
                }
            ).insert()

        # Act
        response = get_languages()

        # Assert
        # Assert
        self.assertIsInstance(response.get("data"), list)
        self.assertTrue(len(response.get("data")) > 0)

        # Create a list of names from the response for easier checking
        response_names = [lang["name"] for lang in response.get("data")]
        self.assertIn("en", response_names)
        self.assertNotIn("tlh", response_names)

    def test_get_currencies(self):
        # Arrange
        # Arrange
        # from paas.api import get_currencies
        # Ensure there is at least one enabled and one disabled currency
        if not frappe.db.exists("Currency", "USD"):
            frappe.get_doc(
                {
                    "doctype": "Currency",
                    "currency_name": "USD",
                    "symbol": "$",
                    "enabled": 1,
                }
            ).insert()
        if not frappe.db.exists("Currency", "KLG"):
            frappe.get_doc(
                {
                    "doctype": "Currency",
                    "currency_name": "Klingon Darsek",
                    "symbol": "KLG",
                    "enabled": 0,
                }
            ).insert()

        # Act
        response = get_currencies()

        # Assert
        # Assert
        self.assertIsInstance(response.get("data"), list)
        self.assertTrue(len(response.get("data")) > 0)

        # Create a list of names from the response for easier checking
        response_names = [c["name"] for c in response.get("data")]
        self.assertIn("USD", response_names)
        self.assertNotIn("KLG", response_names)

    @patch("frappe.sendmail")
    def test_register_user(self, mock_sendmail):
        # Arrange
        # Arrange
        # from paas.api import register_user
        new_user_email = "new_user@example.com"
        if frappe.db.exists("User", new_user_email):
            try:
                frappe.delete_doc(
                    "User", new_user_email, force=True, ignore_permissions=True
                )
            except (
                frappe.LinkExistsError,
                frappe.exceptions.LinkExistsError,
                Exception,
            ):
                frappe.db.set_value("User", new_user_email, "enabled", 0)
                frappe.db.commit()

        # Act
        response = register_user(
            email=new_user_email,
            password="password123",
            first_name="New",
            last_name="User",
        )

        # Assert
        self.assertIn("User registered successfully", response.get("message"))
        self.assertTrue(frappe.db.exists("User", new_user_email))
        new_user = frappe.get_doc("User", new_user_email)
        self.assertIsNotNone(new_user.email_verification_token)
        mock_sendmail.assert_called_once()
