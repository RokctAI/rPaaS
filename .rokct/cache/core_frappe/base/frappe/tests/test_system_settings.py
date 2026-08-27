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
from {app_name}.api.system.system import get_global_settings


class TestSystemSettingsAPI(FrappeTestCase):
    def setUp(self):
        # Create Settings Single Doc if not exists (it should exist as Single)
        # We can set values on it
        settings = frappe.get_single("Settings")
        settings.project_title = "Test App"
        settings.service_fee = 15.5
        settings.deliveryman_order_acceptance_time = 10
        settings.save()

        # Create Global Settings Single Doc
        global_settings = frappe.get_single("Global Settings")
        global_settings.google_maps_api_key = "TEST_API_KEY"
        global_settings.save()

    def test_get_global_settings(self):
        response = get_global_settings()
        data = response.get("data")

        self.assertTrue(isinstance(data, list))

        # Helper to find value by key
        def get_value(key):
            found = next((item for item in data if item["key"] == key), None)
            return found["value"] if found else None

        self.assertEqual(get_value("app_name"), "Test App")
        self.assertEqual(get_value("default_tax"), "15.5")
        self.assertEqual(get_value("deliveryman_order_acceptance_time"), "10")
        self.assertEqual(get_value("google_maps_key"), "TEST_API_KEY")
        self.assertEqual(get_value("default_language"), "en")
