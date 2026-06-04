# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.notification.notification import get_user_notifications


class TestNotificationsAPI(FrappeTestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test_notifications@example.com"):
            self.test_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_notifications@example.com",
                    "first_name": "Test",
                    "last_name": "Notifications",
                    "send_welcome_email": 0,
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_user = frappe.get_doc("User", "test_notifications@example.com")
        self.test_user.add_roles("System Manager")

        # Create notification type if not exists (Usually standard, but Alert
        # might be missing)
        if not frappe.db.exists("Notification Type", "Alert"):
            # Assuming 'Notification Type' is a doctype, or it's just a select/link options.
            # The error was LinkValidationError, link to 'Notification Type'.
            # Standard Frappe actually doesn't use 'Notification Type' link in Notification Log usually?
            # 'type' is a Select in standard Notification Log.
            # But here key is 'notification_type', likely custom or mapped.
            pass

        # If 'notification_type' is a Link field to 'Notification Type' DocType:
        # We need to construct it. But let's check if the DocType exists first.
        # However, to be safe, standard Notification Log uses 'type' (Select).
        # PaaS seems to use 'notification_type'. Inspecting error: "Could not find Notification Type: Alert"
        # imply it is a Link.

        # Create 'Alert' Notification Type if it doesn't exist
        # We handle the case where Notification Type might not be a standard doctype in some envs
        # Warning: Verify if Notification Type exists as a DocType first
        # Create Unique 'Alert' Notification Type
        # Check if 'Warning' type exists (using 'Alert' might conflict if unique constraint exists on type)
        # We will use 'Warning' for this test to avoid collision if 'Alert' exists but with different name
        # Actually, let's just find ANY type that is 'Alert' or create one
        # safely.

        existing_alert = frappe.db.get_value(
            "Notification Type", {"type": "Alert"}, "name"
        )
        if not existing_alert:
            try:
                self.alert_type_doc = frappe.get_doc(
                    {"doctype": "Notification Type", "name": "Alert", "type": "Alert"}
                ).insert(ignore_permissions=True)
            except frappe.DuplicateEntryError:
                # Race condition or it exists now
                self.alert_type_doc = frappe.get_doc(
                    "Notification Type", {"type": "Alert"}
                )
        else:
            self.alert_type_doc = frappe.get_doc("Notification Type", existing_alert)

        frappe.db.commit()

        # Clean up any existing notifications for this user to ensure test
        # isolation
        frappe.db.delete("Notification Log", {"user": self.test_user.name})

        # Create a notification log for the user
        self.notification_log = frappe.get_doc(
            {
                "doctype": "Notification Log",
                "subject": f"Test Notification {frappe.generate_hash()}",
                "user": self.test_user.name,  # Was for_user
                "type": "Alert",
                "message": "Test Content",  # Was email_content
                "notification_type": self.alert_type_doc.name,
            }
        ).insert(ignore_permissions=True)

        # Log in as the test user
        frappe.set_user(self.test_user.name)

    def tearDown(self):
        # Log out
        frappe.set_user("Administrator")
        frappe.db.delete("Notification Log", {"user": self.test_user.name})
        if frappe.db.exists("User", self.test_user.name):
            try:
                self.test_user.delete(ignore_permissions=True)
            except frappe.exceptions.LinkExistsError:
                frappe.db.set_value("User", self.test_user.name, "enabled", 0)

    def test_get_user_notifications(self):
        notifications = get_user_notifications()
        self.assertTrue(isinstance(notifications, list))
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].get("subject"), self.notification_log.subject)

    def test_get_notification_settings(self):
        from paas.api.notification.notification import get_notification_settings

        response = get_notification_settings()
        data = response.get("data")
        # Structure is {data: [...]}
        settings_list = data.get("data")

        print(settings_list)
        self.assertTrue(isinstance(settings_list, list))
        # Should contain at least our Alert type
        self.assertTrue(any(s.get("type") == "Alert" for s in settings_list))

    def test_update_notification_settings(self):
        from paas.api.notification.notification import (
            update_notification_settings,
            get_notification_settings,
        )

        # Turn it off
        response = update_notification_settings(type="Alert", active=0)
        self.assertEqual(
            response.get("message"), "Notification settings updated successfully."
        )

        # Verify it's off
        response = get_notification_settings()
        settings_list = response.get("data").get("data")
        alert_setting = next(s for s in settings_list if s.get("type") == "Alert")
        self.assertFalse(alert_setting.get("active"))

        # Turn it back on
        update_notification_settings(type="Alert", active=1)

        # Verify it's on
        response = get_notification_settings()
        settings_list = response.get("data").get("data")
        alert_setting = next(s for s in settings_list if s.get("type") == "Alert")
        self.assertTrue(alert_setting.get("active"))
