# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.user.user import (
    add_user_address,
    get_user_addresses,
    get_user_address,
    update_user_address,
    delete_user_address,
)
import json


class TestUserAddressAPI(FrappeTestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test_address@example.com"):
            self.test_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_address@example.com",
                    "first_name": "Test",
                    "last_name": "Address",
                    "send_welcome_email": 0,
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_user = frappe.get_doc("User", "test_address@example.com")
        self.test_user.add_roles("System Manager")

        # Log in as the test user
        frappe.set_user(self.test_user.name)

    def tearDown(self):
        # Log out
        frappe.set_user("Administrator")
        # Cleanup addresses linked to the test user
        frappe.db.delete("User Address", {"user": self.test_user.name})
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

    def test_add_and_get_user_address(self):
        address_data = {
            "title": "Home",
            "address": {"city": "Testville"},
            "location": {"lat": 1, "lng": 2},
        }
        response = add_user_address(address_data=json.dumps(address_data))
        added_address = response

        self.assertEqual(added_address.get("title"), "Home")
        self.assertEqual(added_address.get("user"), self.test_user.name)

        # Test get single address
        response = get_user_address(name=added_address.get("name"))
        retrieved_address = response
        self.assertEqual(retrieved_address.get("title"), "Home")

        # Test get all addresses
        response = get_user_addresses()
        addresses = response
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses[0].get("title"), "Home")

    def test_update_user_address(self):
        _address_data = {"title": "Work"}
        response = add_user_address(address_data=json.dumps({"title": "Initial"}))
        added_address = response

        update_data = {"title": "Updated Work"}
        response = update_user_address(
            name=added_address.get("name"), address_data=json.dumps(update_data)
        )
        updated_address = response

        self.assertEqual(updated_address.get("title"), "Updated Work")

    def test_delete_user_address(self):
        response = add_user_address(address_data=json.dumps({"title": "To be deleted"}))
        added_address = response

        response = delete_user_address(name=added_address.get("name"))
        self.assertEqual(response.get("status"), "success")

        response = get_user_addresses()
        addresses = response
        deleted_addr = [
            addr for addr in addresses if addr.get("name") == added_address.get("name")
        ]
        self.assertEqual(len(deleted_addr), 0)

    def test_permission_on_user_address(self):
        # Create another user and an address for them
        if not frappe.db.exists("User", "other_addr@example.com"):
            other_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "other_addr@example.com",
                    "first_name": "Other",
                }
            ).insert(ignore_permissions=True)
        else:
            other_user = frappe.get_doc("User", "other_addr@example.com")

        # Switch to other user to create address
        frappe.set_user(other_user.name)

        # Check if address already exists to avoid DuplicateEntryError
        if not frappe.db.exists(
            "User Address", {"user": other_user.name, "title": "Other's Home"}
        ):
            other_address = add_user_address(
                address_data=json.dumps({"title": "Other's Home"})
            )
        else:
            other_address = frappe.get_all(
                "User Address",
                filters={"user": other_user.name, "title": "Other's Home"},
            )[0]

        # Switch back to test_user
        frappe.set_user(self.test_user.name)

        # test_user should not be able to get, update, or delete other_user's
        # address
        address_name = (
            other_address.get("name")
            if isinstance(other_address, dict)
            else other_address.name
        )
        with self.assertRaises(frappe.PermissionError):
            get_user_address(name=address_name)

        with self.assertRaises(frappe.PermissionError):
            update_user_address(
                name=address_name, address_data=json.dumps({"title": "Hacked"})
            )

        with self.assertRaises(frappe.PermissionError):
            delete_user_address(name=address_name)

        # Clean up other user session
        frappe.set_user("Administrator")
        # Cleanup addresses linked to the other user
        frappe.db.delete("User Address", {"user": "other_addr@example.com"})
        if frappe.db.exists("User", "other_addr@example.com"):
            try:
                frappe.delete_doc(
                    "User",
                    "other_addr@example.com",
                    force=True,
                    ignore_permissions=True,
                )
            except (
                frappe.LinkExistsError,
                frappe.exceptions.LinkExistsError,
                Exception,
            ):
                try:
                    frappe.db.set_value("User", "other_addr@example.com", "enabled", 0)
                    frappe.db.commit()
                except Exception:
                    pass
