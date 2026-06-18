# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.product.product import get_products, get_product_by_uuid


class TestProductAPI(FrappeTestCase):
    def setUp(self):
        # Create a Shop
        if not frappe.db.exists("Shop", "Product Test Shop"):
            self.shop = frappe.get_doc(
                {
                    "doctype": "Shop",
                    "shop_name": "Product Test Shop",
                    "status": "approved",
                    "open": 1,
                    "visibility": 1,
                    "user": "Administrator",
                    "uuid": frappe.generate_hash(),
                    "phone": "+14155552671",
                }
            ).insert(ignore_permissions=True)
        else:
            self.shop = frappe.get_doc("Shop", "Product Test Shop")

        # Create a Product (Item)
        # Ensure UOM 'Unit' exists
        if not frappe.db.exists("UOM", "Unit"):
            frappe.get_doc({"doctype": "UOM", "uom_name": "Unit", "enabled": 1}).insert(
                ignore_permissions=True
            )

        # Ensure Custom Fields exist (since they seem missing found in test
        # env)
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field

        if not frappe.db.has_column("Item", "uuid"):
            create_custom_field(
                "Item",
                {
                    "fieldname": "uuid",
                    "label": "UUID",
                    "fieldtype": "Data",
                    "unique": 1,
                },
            )

        if not frappe.db.has_column("Item", "is_visible_in_website"):
            create_custom_field(
                "Item",
                {
                    "fieldname": "is_visible_in_website",
                    "label": "Is Visible In Website",
                    "fieldtype": "Check",
                    "default": 1,
                },
            )

        if not frappe.db.has_column("Item", "status"):
            create_custom_field(
                "Item",
                {
                    "fieldname": "status",
                    "label": "Status",
                    "fieldtype": "Select",
                    "options": "Published\nDraft",
                    "default": "Published",
                },
            )

        if not frappe.db.has_column("Item", "approval_status"):
            create_custom_field(
                "Item",
                {
                    "fieldname": "approval_status",
                    "label": "Approval Status",
                    "fieldtype": "Select",
                    "options": "Approved\nPending",
                    "default": "Approved",
                },
            )

        frappe.clear_cache(doctype="Item")

        if not frappe.db.exists("Item", "Test Product 1"):
            self.product = frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": "Test Product 1",
                    "item_name": "Test Product 1",
                    "item_group": "All Item Groups",
                    "shop": self.shop.name,
                    "standard_rate": 100,
                    "description": "A test product",
                    "is_stock_item": 1,
                    "opening_stock": 10,
                    "stock_uom": "Unit",
                    "uuid": frappe.generate_hash(),
                    "is_visible_in_website": 1,
                    "status": "Published",
                    "approval_status": "Approved",
                }
            ).insert(ignore_permissions=True)
        else:
            self.product = frappe.get_doc("Item", "Test Product 1")

    def tearDown(self):
        frappe.set_user("Administrator")
        # Cleanup
        if frappe.db.exists("Item", "Test Product 1"):
            frappe.delete_doc(
                "Item", "Test Product 1", force=True, ignore_permissions=True
            )

        if frappe.db.exists("Shop", "Product Test Shop"):
            # Shop deletion might require deleting items first, which we did
            # above
            try:
                frappe.delete_doc(
                    "Shop", "Product Test Shop", force=True, ignore_permissions=True
                )
            except Exception:
                pass

    def test_get_products(self):
        """Test fetching products list."""
        response = get_products(limit_page_length=20)
        products = response.get("data")

        self.assertIsInstance(products, list)

        product_names = [p["name"] for p in products]
        self.assertIn("Test Product 1", product_names)

        # Verify structure
        test_prod = next(p for p in products if p["name"] == "Test Product 1")
        self.assertIn("item_name", test_prod)
        self.assertIn("standard_rate", test_prod)
        self.assertEqual(test_prod["standard_rate"], 100.0)

    def test_products_search(self):
        # Create dummy items
        if not frappe.db.exists("Item", "Searchable Product"):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": "Searchable Product",
                    "item_name": "Searchable Product",
                    "item_group": "All Item Groups",
                    "shop": self.shop.name,
                    "standard_rate": 200,
                    "stock_uom": "Unit",  # Fixed: Mandatory field
                    "is_stock_item": 0,
                    "description": "A very specific searchable description.",
                    "status": "Published",
                    "approval_status": "Approved",
                }
            ).insert(ignore_permissions=True)

        response = get_products(search="Searchable")
        products = response.get("data")
        self.assertTrue(any(p["item_name"] == "Searchable Product" for p in products))

    def test_get_product_by_uuid(self):
        """Test fetching a single product by UUID."""
        # Setup UUID for the item if not present (Item doesn't always have UUID by default unless custom field)
        # Assuming Item has a uuid field based on previous context, or we use name?
        # api/product/product.py: get_product_by_uuid uses "uuid" field.

        # Check if Item has uuid field
        if not self.product.get("uuid"):
            import uuid

            self.product.uuid = str(uuid.uuid4())
            self.product.save(ignore_permissions=True)

        response = get_product_by_uuid(uuid=self.product.uuid)
        product_details = response.get("data")

        self.assertIsNotNone(product_details)
        self.assertEqual(product_details["name"], "Test Product 1")
        self.assertEqual(product_details["uuid"], self.product.uuid)
