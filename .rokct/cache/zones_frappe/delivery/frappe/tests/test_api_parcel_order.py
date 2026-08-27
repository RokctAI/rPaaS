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
from paas.api.parcel.parcel import create_parcel_order, get_parcel_orders, get_user_parcel_order, update_parcel_status
import json


class TestParcelOrderAPI(FrappeTestCase):
    def setUp(self):  # noqa: C901
        # Create a test user
        if not frappe.db.exists("User", "test_parcel_order@example.com"):
            self.test_user = frappe.get_doc({
                "doctype": "User",
                "email": "test_parcel_order@example.com",
                "first_name": "Test",
                "last_name": "Parcel",
                "send_welcome_email": 0
            }).insert(ignore_permissions=True)
            self.test_user.add_roles("System Manager")
        else:
            self.test_user = frappe.get_doc(
                "User", "test_parcel_order@example.com")

        # Create a parcel order setting
        if not frappe.db.exists("Parcel Order Setting", "Standard"):
            self.parcel_setting = frappe.get_doc({
                "doctype": "Parcel Order Setting",
                "name": "Standard",
                "type": "Standard",
                "price": 10
            }).insert(ignore_permissions=True)
        else:
            self.parcel_setting = frappe.get_doc(
                "Parcel Order Setting", "Standard")

        # Create a delivery point
        if not frappe.db.exists("Delivery Point", "Test Delivery Point"):
            self.delivery_point = frappe.get_doc({
                "doctype": "Delivery Point",
                "name": "Test Delivery Point",
                "address": "123 Test Street"
            }).insert(ignore_permissions=True)
        else:
            self.delivery_point = frappe.get_doc(
                "Delivery Point", "Test Delivery Point")

        # Create a test shop (required for Product)
        if not frappe.db.exists("Shop", "Parcel Test Shop"):
            self.test_shop = frappe.get_doc({
                "doctype": "Shop",
                "shop_name": "Parcel Test Shop",
                "user": self.test_user.name,
                "uuid": "parcel_test_shop_uuid",
                "phone": "+14155552671"
            }).insert(ignore_permissions=True)
        else:
            self.test_shop = frappe.get_doc("Shop", "Parcel Test Shop")

        # Create a test product "Test Item"
        if not frappe.db.exists("Product", "Test Item"):
            self.test_product = frappe.get_doc({
                "doctype": "Product",
                "name": "Test Item",
                "title": "Test Item",
                "shop": self.test_shop.name,
                "price": 50
            }).insert(ignore_permissions=True)

        # Create ERPNext Item "Test Item" if it doesn't exist (Parcel Order links to Item, not Product currently?)
        # Or Parcel Order Item has a field 'item_code' linked to Item.

        # Clean up any stale Test Item
        if frappe.db.exists("Item", "Test Item"):
            frappe.delete_doc(
                "Item",
                "Test Item",
                force=True,
                ignore_permissions=True)

        # 0. Create Item Group "All Item Groups" if missing
        if not frappe.db.exists("Item Group", "All Item Groups"):
            frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": "All Item Groups",
                "is_group": 1
            }).insert(ignore_permissions=True)

        # 1. Create UOM "Nos" if missing
        if not frappe.db.exists("UOM", "Nos"):
            frappe.get_doc({
                "doctype": "UOM",
                "uom_name": "Nos",
                "must_be_whole_number": 1
            }).insert(ignore_permissions=True)

        # 2. Create Unique Shop
        self.shop_name = f"Test Shop {frappe.generate_hash(length=5)}"
        # Check if Shop doctype exists (it must)
        if frappe.db.exists("DocType", "Shop"):
            self.test_shop = frappe.get_doc({
                "doctype": "Shop",
                "shop_name": self.shop_name,
                "uuid": frappe.generate_hash(length=10),  # Add mandatory UUID
                "user": self.test_user.name,
                "status": "approved",
                "open": 1,
                "visibility": 1,
                "delivery": 1,
                "phone": "+919999999999"
            }).insert(ignore_permissions=True)
            frappe.db.commit()

            # 3. Create Unique Product (The 'item' field in Parcel Order Item
            # links to Product)

            # Create Shop Unit "Kg" if missing (Shop Unit is Shop-specific)
            # We create it for this specific shop
            unit_name = f"Kg-{self.shop_name}"
            if not frappe.db.exists("Shop Unit", unit_name):
                shop_unit = frappe.get_doc({
                    "doctype": "Shop Unit",
                    "name": unit_name,
                    "unit_name": "Kg",
                    "shop": self.test_shop.name
                }).insert(ignore_permissions=True)
                unit_name = shop_unit.name
            frappe.db.commit()

            self.product_name = f"Test Product {frappe.generate_hash(length=5)}"
            self.product = frappe.get_doc({
                "doctype": "Product",
                "title": self.product_name,
                "shop": self.test_shop.name,
                "price": 10.0,
                "unit": unit_name,
                "active": 1,
                "track_stock": 0
            }).insert(ignore_permissions=True)
            frappe.db.commit()
            self.item_code = self.product.name
        else:
            # Fallback if Shop doesn't exist (unlikely in PaaS)
            self.item_code = "Test Item"

        # Log in as the test user
        frappe.set_user(self.test_user.name)

    def tearDown(self):
        # Log out
        frappe.set_user("Administrator")
        # Clean up created documents
        frappe.db.delete("Parcel Order", {"user": self.test_user.name})
        if hasattr(self, "parcel_setting"):
            frappe.db.delete(
                "Parcel Order Setting", {
                    "name": self.parcel_setting.name})
        if hasattr(self, "delivery_point"):
            frappe.db.delete(
                "Delivery Point", {
                    "name": self.delivery_point.name})

        if hasattr(self, "product") and self.product:
            frappe.delete_doc(
                "Product",
                self.product.name,
                force=True,
                ignore_permissions=True)

        if hasattr(self, "test_shop") and self.test_shop:
            frappe.delete_doc(
                "Shop",
                self.test_shop.name,
                force=True,
                ignore_permissions=True)

        # Clean up Item if we created it previously (legacy cleanup)
        if frappe.db.exists("Item", "Test Item"):
            frappe.delete_doc(
                "Item",
                "Test Item",
                force=True,
                ignore_permissions=True)

        if frappe.db.exists("User", self.test_user.name):
            try:
                frappe.delete_doc(
                    "User",
                    self.test_user.name,
                    force=True,
                    ignore_permissions=True)
            except (frappe.LinkExistsError, frappe.exceptions.LinkExistsError, Exception):
                frappe.db.set_value("User", self.test_user.name, "enabled", 0)
                frappe.db.commit()

    def test_create_parcel_order(self):
        order_data = {
            "total_price": 100.0,
            "currency": "USD",
            "type": self.parcel_setting.name,
            "address_from": {"city": "City A"},
            "address_to": {"city": "City B"},
        }
        res = create_parcel_order(order_data=json.dumps(order_data))
        order = res.get("data")
        self.assertEqual(order.get("user"), self.test_user.name)
        self.assertEqual(order.get("total_price"), 100.0)

    def test_create_parcel_order_with_delivery_point(self):
        order_data = {
            "destination_type": "delivery_point",
            "delivery_point_id": self.delivery_point.name,
            "items": [{"item_code": self.item_code, "quantity": 1}],
            "total_price": 50.0,
            "type": self.parcel_setting.name
        }
        res = create_parcel_order(order_data=json.dumps(order_data))
        order = res.get("data")
        self.assertEqual(order.get("delivery_point"), self.delivery_point.name)
        self.assertEqual(len(order.get("items")), 1)

    def test_get_parcel_orders(self):
        # Create a parcel order first
        order_data = {"type": self.parcel_setting.name, "total_price": 50.0}
        create_parcel_order(order_data=json.dumps(order_data))

        res = get_parcel_orders()
        orders = res.get("data")
        self.assertTrue(isinstance(orders, list))
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].get("status"), "New")

    def test_get_user_parcel_order(self):
        # Create a parcel order first
        order_data = {"type": self.parcel_setting.name, "total_price": 123.45}
        create_res = create_parcel_order(order_data=json.dumps(order_data))
        created_order = create_res.get("data")

        res = get_user_parcel_order(name=created_order.get("name"))
        order = res.get("data")
        self.assertEqual(order.get("name"), created_order.get("name"))
        self.assertEqual(order.get("total_price"), 123.45)

    def test_get_other_user_parcel_order_permission(self):
        # Create another user and an order for them
        other_user = frappe.get_doc({
            "doctype": "User", "email": "other@example.com", "first_name": "Other"
        }).insert(ignore_permissions=True)

        # Switch to other user to create order
        frappe.set_user(other_user.name)
        order_data = {"type": self.parcel_setting.name, "total_price": 50.0}
        other_res = create_parcel_order(order_data=json.dumps(order_data))
        other_order = other_res.get("data")

        # Switch back to test_user
        frappe.set_user(self.test_user.name)

        # test_user should not be able to get other_user's order
        with self.assertRaises(frappe.PermissionError):
            get_user_parcel_order(name=other_order.get("name"))

        # Clean up other user
        frappe.set_user("Administrator")
        # 5. Cleanup other user
        frappe.db.delete("Parcel Order", {"user": other_user.name})
        other_user.delete(ignore_permissions=True)

    def test_update_parcel_status(self):
        # Create a parcel order first
        order_data = {"type": self.parcel_setting.name, "total_price": 50.0}
        create_res = create_parcel_order(order_data=json.dumps(order_data))
        created_order = create_res.get("data")

        # Update the status
        res = update_parcel_status(
            parcel_order_id=created_order.get("name"),
            status="Accepted")
        updated_order = res.get("data")
        self.assertEqual(updated_order.get("status"), "Accepted")
