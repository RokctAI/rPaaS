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
from paas.api.brand.brand import create_brand, get_brands, get_brand_by_uuid, update_brand, delete_brand


class TestBrand(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # Cleanup
        frappe.db.delete("Brand", {"title": "Test Brand"})

    def tearDown(self):
        frappe.db.rollback()

    def test_brand_crud(self):
        # 1. Create
        brand_data = {
            "title": "Test Brand",
            "slug": "test-brand",
            "active": 1
        }
        brand = create_brand(brand_data)
        self.assertTrue(brand['uuid'])
        self.assertEqual(brand['title'], "Test Brand")

        # 2. Get List
        brands = get_brands()
        self.assertTrue(len(brands) > 0)

        # 3. Get by UUID
        fetched_brand = get_brand_by_uuid(brand['uuid'])
        self.assertEqual(fetched_brand['title'], "Test Brand")

        # 4. Update
        updated_data = {"title": "Updated Brand"}
        update_brand(brand['uuid'], updated_data)
        self.assertEqual(
            frappe.db.get_value(
                "Brand", {
                    "uuid": brand['uuid']}, "title"), "Updated Brand")

        # 5. Delete
        delete_brand(brand['uuid'])
        self.assertFalse(frappe.db.exists("Brand", {"uuid": brand['uuid']}))
