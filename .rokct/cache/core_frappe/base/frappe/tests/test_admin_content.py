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
from {app_name}.api.admin_content.admin_content import (
    create_admin_banner,
    get_admin_banners,
    update_admin_banner,
    delete_admin_banner,
    create_admin_faq,
    get_admin_faqs,
    update_admin_faq,
    delete_admin_faq,
    create_admin_faq_category)


class TestAdminContent_New(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # Cleanup
        frappe.db.delete("Banner", {"title": "Admin Banner"})
        frappe.db.delete("FAQ", {"question": "Admin Question"})

    def tearDown(self):
        frappe.db.rollback()

    def test_admin_banner_crud(self):
        # Create
        data = {"title": "Admin Banner", "is_active": 1, "image": "test.jpg"}
        banner = create_admin_banner(data)
        self.assertEqual(banner['title'], "Admin Banner")
        self.assertIsNone(banner['shop'])

        # Get
        banners = get_admin_banners()
        self.assertTrue(len(banners) > 0)

        # Update
        update_admin_banner(banner['name'], {"title": "Updated Admin Banner"})
        self.assertEqual(
            frappe.db.get_value(
                "Banner",
                banner['name'],
                "title"),
            "Updated Admin Banner")

        # Delete
        delete_admin_banner(banner['name'])
        self.assertFalse(frappe.db.exists("Banner", banner['name']))

    def test_admin_faq_crud(self):
        # 1. Create Category
        cat = create_admin_faq_category({"category_name": "Admin Cat"})

        # 2. Create FAQ
        faq = create_admin_faq(
            {"question": "Admin Question", "answer": "Ans", "faq_category": cat['name']})
        self.assertEqual(faq['question'], "Admin Question")

        # 3. Get
        faqs = get_admin_faqs()
        self.assertTrue(len(faqs) > 0)

        # 4. Update
        update_admin_faq(faq['name'], {"question": "Updated Q"})
        self.assertEqual(
            frappe.db.get_value(
                "FAQ",
                faq['name'],
                "question"),
            "Updated Q")

        # 5. Delete
        delete_admin_faq(faq['name'])
        self.assertFalse(frappe.db.exists("FAQ", faq['name']))
