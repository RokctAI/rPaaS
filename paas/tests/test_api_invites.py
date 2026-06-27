# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.user.user import create_invite, get_user_invites, update_invite_status


class TestInvitesAPI(FrappeTestCase):
    def setUp(self):
        # Create test users
        if not frappe.db.exists("User", "inviter@example.com"):
            self.inviting_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "inviter@example.com",
                    "first_name": "Inviter",
                }
            ).insert(ignore_permissions=True)
        else:
            self.inviting_user = frappe.get_doc("User", "inviter@example.com")

        if not frappe.db.exists("User", "invited@example.com"):
            self.invited_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "invited@example.com",
                    "first_name": "Invited",
                }
            ).insert(ignore_permissions=True)
        else:
            self.invited_user = frappe.get_doc("User", "invited@example.com")

        # Create a test shop (Company)
        if not frappe.db.exists("Company", "Test Invite Shop"):
            self.shop = frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": "Test Invite Shop",
                    "default_currency": "INR",
                    "country": "India",
                }
            ).insert(ignore_permissions=True)
        else:
            self.shop = frappe.get_doc("Company", "Test Invite Shop")

    def tearDown(self):
        frappe.db.delete("Invitation")
        if frappe.db.exists("Company", "Test Invite Shop"):
            try:
                self.shop.delete(ignore_permissions=True)
            except frappe.exceptions.LinkExistsError:
                pass

        for user_email in ["inviter@example.com", "invited@example.com"]:
            if frappe.db.exists("User", user_email):
                try:
                    frappe.delete_doc("User", user_email, ignore_permissions=True)
                except frappe.exceptions.LinkExistsError:
                    frappe.db.set_value("User", user_email, "enabled", 0)
        frappe.set_user("Administrator")

    def test_create_and_get_invites(self):
        # Log in as the inviting user to create the invite
        frappe.set_user(self.inviting_user.name)
        invite = create_invite(
            shop=self.shop.name, user=self.invited_user.name, role="Collaborator"
        )
        self.assertEqual(invite.get("shop"), self.shop.name)
        self.assertEqual(invite.get("user"), self.invited_user.name)
        self.assertEqual(invite.get("status"), "New")

        # Log in as the invited user to see the invite
        frappe.set_user(self.invited_user.name)
        invites = get_user_invites()
        self.assertEqual(len(invites), 1)
        self.assertEqual(invites[0].get("shop"), self.shop.name)

    def test_update_invite_status(self):
        # Create an invite first
        frappe.set_user(self.inviting_user.name)
        invite = create_invite(
            shop=self.shop.name, user=self.invited_user.name, role="Collaborator"
        )

        # Log in as the invited user to update the status
        frappe.set_user(self.invited_user.name)
        updated_invite = update_invite_status(
            name=invite.get("name"), status="Accepted"
        )
        self.assertEqual(updated_invite.get("status"), "Accepted")

        # Test invalid status
        with self.assertRaises(frappe.exceptions.ValidationError):
            update_invite_status(name=invite.get("name"), status="InvalidStatus")

    def test_permission_on_invite_update(self):
        # Create an invite
        frappe.set_user(self.inviting_user.name)
        invite = create_invite(
            shop=self.shop.name, user=self.invited_user.name, role="Collaborator"
        )

        # The inviting user should not be able to update the status
        with self.assertRaises(frappe.PermissionError):
            update_invite_status(name=invite.get("name"), status="Accepted")
