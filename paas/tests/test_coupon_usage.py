# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt
import frappe
import json
from frappe.tests.utils import FrappeTestCase
from paas.api.order.order import create_order


class TestCouponUsage(FrappeTestCase):
    def setUp(self):
        if not frappe.db.exists("User", "test_coupon_user@example.com"):
            self.test_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_coupon_user@example.com",
                    "first_name": "Test",
                    "last_name": "User",
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_user = frappe.get_doc("User", "test_coupon_user@example.com")

        if not frappe.db.exists("Shop", "Test Shop for Coupon Usage"):
            self.test_shop = frappe.get_doc(
                {
                    "doctype": "Shop",
                    "shop_name": "Test Shop for Coupon Usage",
                    "min_amount": 0,
                    "user": self.test_user.name,
                    "phone": "+14155552671",
                    "uuid": frappe.generate_hash(),
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_shop = frappe.get_doc("Shop", "Test Shop for Coupon Usage")

        if not frappe.db.exists("Product", "Test Product for Coupon"):
            self.test_product = frappe.get_doc(
                {
                    "doctype": "Product",
                    "title": "Test Product for Coupon",
                    "shop": self.test_shop.name,
                    "price": 100,
                    "active": 1,
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_product = frappe.get_doc("Product", "Test Product for Coupon")

        if not frappe.db.exists(
            "Coupon", {"code": "TEST10", "shop": self.test_shop.name}
        ):
            self.test_coupon = frappe.get_doc(
                {
                    "doctype": "Coupon",
                    "coupon_name": "Test Coupon",
                    "code": "TEST10",
                    "type": "Percentage",
                    "discount_percentage": 10,
                    "discount_amount": 10,
                    "expired_at": "2030-01-01",
                    "shop": self.test_shop.name,
                }
            ).insert(ignore_permissions=True)
        else:
            self.test_coupon = frappe.get_doc(
                "Coupon", {"code": "TEST10", "shop": self.test_shop.name}
            )

        if not frappe.db.exists("Currency", "USD"):
            frappe.get_doc(
                {
                    "doctype": "Currency",
                    "currency_name": "USD",
                    "symbol": "$",
                    "enabled": 1,
                }
            ).insert(ignore_permissions=True)
        self.test_currency = "USD"
        self.test_currency = "USD"

    def tearDown(self):  # noqa: C901
        frappe.set_user("Administrator")
        if frappe.db.exists("User", self.test_user.name):
            try:
                frappe.delete_doc("User", self.test_user.name, ignore_permissions=True)
            except (
                frappe.LinkExistsError,
                frappe.exceptions.LinkExistsError,
                Exception,
            ):
                try:
                    frappe.db.set_value("User", self.test_user.name, "enabled", 0)
                    frappe.db.commit()
                except Exception:
                    pass

        try:
            if (
                hasattr(self, "test_shop")
                and self.test_shop
                and frappe.db.exists("Shop", self.test_shop.name)
            ):
                frappe.delete_doc("Shop", self.test_shop.name, ignore_permissions=True)
            if (
                hasattr(self, "test_product")
                and self.test_product
                and frappe.db.exists("Product", self.test_product.name)
            ):
                frappe.delete_doc(
                    "Product", self.test_product.name, ignore_permissions=True
                )
            if (
                hasattr(self, "test_coupon")
                and self.test_coupon
                and frappe.db.exists("Coupon", self.test_coupon.name)
            ):
                frappe.delete_doc(
                    "Coupon", self.test_coupon.name, ignore_permissions=True
                )
        except Exception:
            pass

    def test_create_order_with_coupon_records_usage(self):
        frappe.set_user(self.test_user.name)
        order_data = {
            "user": self.test_user.name,
            "shop": self.test_shop.name,
            "delivery_type": "Delivery",
            "currency": self.test_currency,
            "rate": 1,
            "order_items": [
                {"product": self.test_product.name, "quantity": 1, "price": 100}
            ],
            "coupon_code": self.test_coupon.code,
        }

        order_dict = create_order(json.dumps(order_data))
        self.assertIsNotNone(order_dict)
        order_name = order_dict["data"].get("name")

        # Check if Coupon Usage was created
        coupon_usage_exists = frappe.db.exists(
            "Coupon Usage",
            {
                "user": self.test_user.name,
                "coupon": self.test_coupon.name,
                "order": order_name,
            },
        )
        self.assertTrue(coupon_usage_exists, "Coupon Usage document was not created.")
