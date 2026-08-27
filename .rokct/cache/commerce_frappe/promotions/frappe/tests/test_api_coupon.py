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
from paas.api.coupon.coupon import check_coupon


class TestCouponAPI(FrappeTestCase):
    def setUp(self):
        # Create a shop
        if not frappe.db.exists("Shop", "TestShopAPICoupon"):
            self.shop = frappe.get_doc({
                "doctype": "Shop",
                "shop_name": "TestShopAPICoupon",
                "user": "Administrator",
                "phone": "+14155552671",
                "uuid": "test-coupon-shop-uuid",
                "owner": "Administrator"
            }).insert(ignore_permissions=True)
        else:
            self.shop = frappe.get_doc("Shop", "TestShopAPICoupon")

        # Create coupons
        if not frappe.db.exists(
            "Coupon", {
                "code": "VALID10", "shop": self.shop.name}):
            self.valid_coupon = frappe.get_doc({
                "doctype": "Coupon",
                "code": "VALID10",
                "shop": self.shop.name,
                "type": "Percentage",
                "amount": 10,
                "discount_amount": 10,
                "expired_at": "2099-12-31",
                "quantity": 10
            }).insert(ignore_permissions=True)
        else:
            self.valid_coupon = frappe.get_doc(
                "Coupon", {"code": "VALID10", "shop": self.shop.name})

        if not frappe.db.exists(
            "Coupon", {
                "code": "EXPIRED", "shop": self.shop.name}):
            self.expired_coupon = frappe.get_doc({
                "doctype": "Coupon",
                "code": "EXPIRED",
                "shop": self.shop.name,
                "type": "Fixed",
                "amount": 5,
                "discount_amount": 5,
                "expired_at": "2020-01-01 00:00:00"
            }).insert(ignore_permissions=True)
        else:
            self.expired_coupon = frappe.get_doc(
                "Coupon", {"code": "EXPIRED", "shop": self.shop.name})

        if not frappe.db.exists(
            "Coupon", {
                "code": "ZEROQ", "shop": self.shop.name}):
            self.zero_quantity_coupon = frappe.get_doc({
                "doctype": "Coupon",
                "code": "ZEROQ",
                "shop": self.shop.name,
                "type": "Percentage",
                "amount": 20,
                "discount_amount": 20,
                "expired_at": "2099-12-31",
                "quantity": 0
            }).insert(ignore_permissions=True)
        else:
            self.zero_quantity_coupon = frappe.get_doc(
                "Coupon", {"code": "ZEROQ", "shop": self.shop.name})

    def tearDown(self):
        try:
            self.valid_coupon.delete(ignore_permissions=True)
            self.expired_coupon.delete(ignore_permissions=True)
            self.zero_quantity_coupon.delete(ignore_permissions=True)
        except Exception:
            pass

        if hasattr(self, "shop") and self.shop:
            try:
                self.shop.delete(ignore_permissions=True)
            except Exception:
                pass

    def test_check_valid_coupon(self):
        result = check_coupon(code="VALID10", shop_id=self.shop.name)
        self.assertEqual(result.get("code"), "VALID10")
        self.assertEqual(result.get("discount_amount"), 10)

    def test_check_invalid_coupon(self):
        result = check_coupon(code="INVALID", shop_id=self.shop.name)
        self.assertEqual(result.get("status"), "error")
        self.assertEqual(result.get("message"), "Invalid Coupon")

    def test_check_expired_coupon(self):
        result = check_coupon(code="EXPIRED", shop_id=self.shop.name)
        self.assertEqual(result.get("status"), "error")
        self.assertEqual(result.get("message"), "Coupon expired")

    def test_check_zero_quantity_coupon(self):
        result = check_coupon(code="ZEROQ", shop_id=self.shop.name)
        self.assertEqual(result.get("status"), "error")
        self.assertEqual(result.get("message"), "Coupon has been fully used")

    def test_missing_parameters(self):
        with self.assertRaises(frappe.exceptions.ValidationError):
            check_coupon(code="", shop_id=self.shop.name)
        with self.assertRaises(frappe.exceptions.ValidationError):
            check_coupon(code="VALID10", shop_id="")
