# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.banner.banner import get_ads, get_ad, like_banner
from paas.api.admin_content.admin_content import create_admin_banner


class TestBanner(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # cleanup
        frappe.db.delete("Banner", {"title": "Test Banner"})

        # Create a Banner ensuring it's an ad
        self.banner = frappe.get_doc(
            {
                "doctype": "Banner",
                "title": "Test Banner",
                "is_ad": 1,
                "image": "/files/test_banner.jpg",
                "is_active": 1,
                "likes": 0,
            }
        ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_banner_read_and_like(self):
        # 1. Get Ads
        ads = get_ads()
        self.assertTrue(len(ads) > 0)
        found = any(ad["name"] == self.banner.name for ad in ads)
        self.assertTrue(found)

        # 2. Get Ad by ID
        ad = get_ad(self.banner.name)
        self.assertEqual(ad.name, self.banner.name)

        # 3. Like Banner
        like_banner(self.banner.name)
        self.assertEqual(frappe.db.get_value("Banner", self.banner.name, "likes"), 1)
