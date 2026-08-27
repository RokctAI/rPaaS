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
from paas.api.ads_package.ads_package import create_ads_package, get_ads_packages


class TestAdsPackage(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_ads_package_crud(self):
        # 1. Create Ads Package
        data = {
            "title": "Premium Banner",
            "price": 50,
            "time_type": "day",
            "time": 7
        }
        package = create_ads_package(data)
        self.assertEqual(package.title, "Premium Banner")
        self.assertEqual(package.price, 50)

        # 2. Get Ads Packages
        packages = get_ads_packages()
        self.assertTrue(len(packages) > 0)
        self.assertEqual(packages[0].title, "Premium Banner")
