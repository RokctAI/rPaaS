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
from paas.api.shop.shop import get_nearest_delivery_points


class TestDeliveryPointAPI(FrappeTestCase):
    def setUp(self):
        # Create a test delivery point
        if not frappe.db.exists("Delivery Point", "Test Delivery Point"):
            self.delivery_point = frappe.get_doc({
                "doctype": "Delivery Point",
                "name": "Test Delivery Point",
                "active": 1,
                "price": 10.0,
                "address": "123 Test Street",
                "latitude": 12.340000,
                "longitude": 56.780000,
            }).insert(ignore_permissions=True)
        else:
            self.delivery_point = frappe.get_doc(
                "Delivery Point", "Test Delivery Point")

    def tearDown(self):
        try:
            self.delivery_point.delete(ignore_permissions=True)
        except Exception:
            pass

    def test_get_nearest_delivery_points(self):
        # Test with coordinates close to the test point
        points = get_nearest_delivery_points(latitude=12.34, longitude=56.78)
        self.assertTrue(isinstance(points, list))
        self.assertTrue(len(points) > 0)
        self.assertEqual(points[0].get("name"), self.delivery_point.name)

    def test_get_nearest_delivery_points_far_away(self):
        # Test with coordinates far from the test point
        points = get_nearest_delivery_points(latitude=40.0, longitude=-74.0)
        self.assertTrue(isinstance(points, list))
        self.assertEqual(len(points), 0)

    def test_get_inactive_delivery_point(self):
        self.delivery_point.active = 0
        self.delivery_point.save(ignore_permissions=True)

        points = get_nearest_delivery_points(latitude=12.34, longitude=56.78)
        self.assertEqual(len(points), 0)

    def test_invalid_parameters(self):
        # With strict type hints, Frappe might raise FrappeTypeError or standard Python TypeError
        # We need to catch either, or simply assertRaises(Exception) if we want to be broad
        # But let's try to be specific based on previous error logs:
        # frappe.exceptions.FrappeTypeError
        try:
            from frappe.exceptions import FrappeTypeError
            ErrorType = FrappeTypeError
        except ImportError:
            ErrorType = TypeError

        with self.assertRaises((frappe.exceptions.ValidationError, ErrorType, TypeError)):
            get_nearest_delivery_points(latitude=None, longitude=56.78)
        with self.assertRaises((frappe.exceptions.ValidationError, ErrorType, TypeError)):
            get_nearest_delivery_points(latitude=12.34, longitude=None)
        with self.assertRaises((frappe.exceptions.ValidationError, ErrorType, ValueError)):
            # "invalid" string might cause ValueError inside float() conversion if it bypasses type check
            # or TypeError if type check catches it.
            get_nearest_delivery_points(
                latitude="invalid", longitude="invalid")
