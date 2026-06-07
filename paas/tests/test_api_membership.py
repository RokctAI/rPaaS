# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.user.user import get_user_membership, get_user_membership_history


class TestMembershipAPI(FrappeTestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test_membership@example.com"):
            self.test_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_membership@example.com",
                    "first_name": "Test",
                    "last_name": "Membership",
                    "send_welcome_email": 0,
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_user = frappe.get_doc("User", "test_membership@example.com")
        self.test_user.add_roles("System Manager")

        # Create a membership plan
        if not frappe.db.exists("Membership", {"title": "Gold Plan"}):
            self.membership_plan = frappe.get_doc(
                {
                    "doctype": "Membership",
                    "title": "Gold Plan",
                    "price": 100.0,
                    "duration": 1,
                    "duration_unit": "Months",
                }
            ).insert(ignore_permissions=True)
        else:
            self.membership_plan = frappe.get_doc("Membership", {"title": "Gold Plan"})

        # Create a user membership
        if not frappe.db.exists(
            "User Membership",
            {"user": self.test_user.name, "membership": self.membership_plan.name},
        ):
            self.user_membership = frappe.get_doc(
                {
                    "doctype": "User Membership",
                    "user": self.test_user.name,
                    "membership": self.membership_plan.name,
                    "start_date": frappe.utils.nowdate(),
                    "end_date": frappe.utils.add_months(frappe.utils.nowdate(), 1),
                }
            ).insert(ignore_permissions=True)
        else:
            self.user_membership = frappe.get_doc(
                "User Membership",
                {"user": self.test_user.name, "membership": self.membership_plan.name},
            )

        # Log in as the test user
        frappe.set_user(self.test_user.name)

    def tearDown(self):
        # Log out
        frappe.set_user("Administrator")
        try:
            if hasattr(self, "user_membership") and self.user_membership:
                self.user_membership.delete(ignore_permissions=True)
            if hasattr(self, "membership_plan") and self.membership_plan:
                self.membership_plan.delete(ignore_permissions=True)
        except Exception:
            pass

        if (
            hasattr(self, "test_user")
            and self.test_user
            and frappe.db.exists("User", self.test_user.name)
        ):
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

    def test_get_user_membership(self):
        membership = get_user_membership()
        self.assertIsNotNone(membership)
        self.assertEqual(membership.get("membership"), self.membership_plan.name)

    def test_get_user_membership_history(self):
        history = get_user_membership_history()
        self.assertTrue(isinstance(history, list))
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].get("membership"), self.membership_plan.name)

    def test_get_user_membership_no_active_membership(self):
        self.user_membership.is_active = 0
        self.user_membership.save(ignore_permissions=True)

        membership = get_user_membership()
        self.assertIsNone(membership)
