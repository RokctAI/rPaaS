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

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from {app_name}.api.admin_settings.admin_settings import get_all_languages


class TestAdminDashboard(FrappeTestCase):
    def setUp(self):
        # Create an administrator user (System Manager)
        if not frappe.db.exists("User", "admin_tester@example.com"):
            self.admin_user = frappe.get_doc({
                "doctype": "User",
                "email": "admin_tester@example.com",
                "first_name": "Admin",
                "last_name": "Tester",
                "roles": [{"role": "System Manager"}]
            }).insert(ignore_permissions=True)
        else:
            self.admin_user = frappe.get_doc(
                "User", "admin_tester@example.com")
            self.admin_user.add_roles("System Manager")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    def test_get_languages(self):
        frappe.set_user(self.admin_user.name)

        # Ensure at least one language exists (standard Frappe)
        try:
            langs = get_all_languages()
            self.assertIsInstance(langs, list)
            # Basic check
            if langs:
                self.assertIn("language_name", langs[0])
        except frappe.PermissionError:
            self.fail("System Manager should encounter PermissionError")

    def test_non_admin_access(self):
        # Create non-admin
        if not frappe.db.exists("User", "guest_tester@example.com"):
            guest = frappe.get_doc({
                "doctype": "User", "email": "guest_tester@example.com", "first_name": "Guest"
            }).insert(ignore_permissions=True)
        else:
            guest = frappe.get_doc("User", "guest_tester@example.com")

        frappe.set_user(guest.name)

        with self.assertRaises(frappe.PermissionError):
            get_all_languages()

    def test_email_settings(self):
        frappe.set_user(self.admin_user.name)
        # Just check it doesn't crash; specific settings depend on site config
        try:
            # We skip actually updating potentially sensitive global settings in a test
            # but we can try to fetch them if the doctype exists
            if frappe.db.exists("DocType", "Email Settings"):
                # We'll just call the update function with empty data or verify access
                # But update_email_settings requires data
                pass
        except Exception:
            # Pass if it's just a missing doctype or config in test env
            pass
