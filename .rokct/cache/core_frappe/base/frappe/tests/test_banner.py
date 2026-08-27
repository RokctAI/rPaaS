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
from {app_name}.api.banner.banner import get_ads, get_ad, like_banner
from {app_name}.api.admin_content.admin_content import create_admin_banner


class TestBanner(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # cleanup
        frappe.db.delete("Banner", {"title": "Test Banner"})

        # Create a Banner ensuring it's an ad
        self.banner = frappe.get_doc({
            "doctype": "Banner",
            "title": "Test Banner",
            "is_ad": 1,
            "image": "/files/test_banner.jpg",
            "is_active": 1,
            "likes": 0
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_banner_read_and_like(self):
        # 1. Get Ads
        ads = get_ads()
        self.assertTrue(len(ads) > 0)
        found = any(ad['name'] == self.banner.name for ad in ads)
        self.assertTrue(found)

        # 2. Get Ad by ID
        ad = get_ad(self.banner.name)
        self.assertEqual(ad.name, self.banner.name)

        # 3. Like Banner
        like_banner(self.banner.name)
        self.assertEqual(
            frappe.db.get_value(
                "Banner",
                self.banner.name,
                "likes"),
            1)
