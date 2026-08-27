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
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.parcel_order_setting.parcel_order_setting import (
    create_parcel_order_setting,
    get_parcel_order_settings,
    update_parcel_order_setting,
    delete_parcel_order_setting
)


class TestParcelSettingsFeature(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # Create a Parcel Option
        self.option = frappe.get_doc({
            "doctype": "Parcel Option",
            "title": "Insurance",
            "price": 50
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_crud_parcel_settings(self):
        # 1. Create Setting with Options
        data = {
            "type": "Express Box",
            "price": 100,
            "price_per_km": 10,
            "parcel_options": [
                {"parcel_option": self.option.name}
            ]
        }
        setting = create_parcel_order_setting(data)
        self.assertEqual(setting.get("type"), "Express Box")
        self.assertEqual(len(setting.get("parcel_options")), 1)
        self.assertEqual(setting.get("parcel_options")[
                         0].get("parcel_option"), self.option.name)

        # 2. Retrieve Settings
        settings_list = get_parcel_order_settings()
        self.assertTrue(len(settings_list) > 0)
        found = False
        for s in settings_list:
            if s.name == setting.get("name"):
                found = True
                break
        self.assertTrue(found)

        # 3. Update Setting
        update_data = {
            "price": 150
        }
        updated_setting = update_parcel_order_setting(
            setting.get("name"), update_data)
        self.assertEqual(updated_setting.get("price"), 150)

        # 4. Delete Setting
        delete_parcel_order_setting(setting.get("name"))
        with self.assertRaises(frappe.DoesNotExistError):
            frappe.get_doc("Parcel Order Setting", setting.get("name"))
