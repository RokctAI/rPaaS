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

import frappe
from frappe.tests.utils import FrappeTestCase
from {app_name}.api.user.user import create_request_model, get_user_request_models
import json


class TestRequestModelAPI(FrappeTestCase):
    def setUp(self):
        # Create a test user
        self.test_user = frappe.get_doc({
            "doctype": "User",
            "email": "test_request_model@example.com",
            "first_name": "Test",
            "last_name": "Request",
            "send_welcome_email": 0
        }).insert(ignore_permissions=True)
        self.test_user.add_roles("System Manager")

        # Create a test shop
        self.shop = frappe.get_doc({
            "doctype": "Shop",
            "shop_name": "Test Request Shop",
            "user": self.test_user.name,
            "phone": "+14155552671",
            "uuid": frappe.generate_hash()
        }).insert(ignore_permissions=True)

        # Create a test product to request changes for
        self.product = frappe.get_doc({
            "doctype": "Product",
            "title": "Test Product",
            "shop": self.shop.name
        }).insert(ignore_permissions=True)

        frappe.db.commit()

        # Log in as the test user
        frappe.set_user(self.test_user.name)

    def tearDown(self):
        # Log out
        frappe.set_user("Administrator")
        frappe.db.delete(
            "Request Model", {
                "created_by_user": self.test_user.name})
        try:
            self.product.delete(ignore_permissions=True)
        except Exception:
            pass
        # Shop must be deleted before User due to link
        try:
            self.shop.delete(ignore_permissions=True)
        except Exception:
            pass

        if frappe.db.exists("User", self.test_user.name):
            try:
                self.test_user.delete(ignore_permissions=True)
            except frappe.exceptions.LinkExistsError:
                frappe.db.set_value("User", self.test_user.name, "enabled", 0)
        frappe.db.commit()

    def test_create_and_get_request_models(self):
        request_data = {
            "new_field": "new_value"
        }
        request = create_request_model(
            model_type="Product",
            model_id=self.product.name,
            data=request_data
        )
        self.assertEqual(request.get("model_type"), "Product")
        self.assertEqual(request.get("model"), self.product.name)
        self.assertEqual(request.get("created_by_user"), self.test_user.name)

        requests = get_user_request_models()
        self.assertEqual(len(requests["data"]), 1)
        self.assertEqual(requests["data"][0].get("model"), self.product.name)
