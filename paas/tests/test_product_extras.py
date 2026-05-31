# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.product_extra.product_extra import create_extra_group, create_extra_value
from paas.api.stock.stock import create_stock


class TestProductExtras(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # Create a Shop
        self.shop = frappe.get_doc(
            {
                "doctype": "Shop",
                "shop_name": "Pizza Shop",
                "title": "Pizza Shop",
                "uuid": "pizza_shop_uuid",
                "phone": "+14155552671",
                "user": "Administrator",
            }
        ).insert(ignore_permissions=True)

        # Create a Product
        self.product = frappe.get_doc(
            {
                "doctype": "Product",
                "title": "Margherita Pizza",
                "shop": self.shop.name,
                "price": 100,
            }
        ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_extras_flow(self):
        # 1. Create Extra Group (e.g. Size)
        group_data = {"title": "Size", "type": "text", "shop": self.shop.name}
        group = create_extra_group(group_data)
        self.assertEqual(group.title, "Size")

        # 2. Create Extra Values (Small, Large)
        val_small = create_extra_value({"value": "Small", "extra_group": group.name})
        val_large = create_extra_value({"value": "Large", "extra_group": group.name})
        self.assertEqual(val_small.value, "Small")

        # 3. Link Group to Product
        self.product.append("extras", {"extra_group": group.name})
        self.product.save()
        self.assertEqual(len(self.product.extras), 1)

        # 4. Create Stock (Variant) for "Large" Pizza
        stock_data = {
            "product": self.product.name,
            "sku": "PIZZA-L",
            "price": 120,
            "quantity": 50,
            "shop": self.shop.name,
            "extras": [val_large.name],
        }
        stock = create_stock(stock_data)

        # Verify Stock
        self.assertEqual(stock.sku, "PIZZA-L")
        self.assertEqual(stock.price, 120)
        self.assertEqual(len(stock.stock_extras), 1)
        self.assertEqual(stock.stock_extras[0].extra_value, val_large.name)
