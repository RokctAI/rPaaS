# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.admin_logistics.admin_logistics import (
    get_deliveryman_global_settings,
    update_deliveryman_global_settings,
    create_parcel_order_setting,
    get_parcel_order_settings,
    create_delivery_vehicle_type,
    get_delivery_vehicle_types,
)


class TestAdminLogistics(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # Ensure Settings Doc exists
        if not frappe.db.exists("DeliveryMan Settings", "DeliveryMan Settings"):
            frappe.get_doc({"doctype": "DeliveryMan Settings"}).insert(
                ignore_permissions=True
            )

    def tearDown(self):
        frappe.db.rollback()

    def test_deliveryman_settings(self):
        get_deliveryman_global_settings()
        update_deliveryman_global_settings({"default_commission_rate": 5})
        self.assertEqual(
            frappe.db.get_single_value(
                "DeliveryMan Settings", "default_commission_rate"
            ),
            5,
        )

    def test_parcel_order_settings(self):
        # Create
        setting = create_parcel_order_setting({"type": "Test Type", "price": 10})
        self.assertEqual(setting["type"], "Test Type")

        # Get
        settings = get_parcel_order_settings()
        self.assertTrue(len(settings) > 0)

    def test_vehicle_type(self):
        # Create
        vtype = create_delivery_vehicle_type({"name": "Bike", "base_fare": 10})
        # Name might be randomized/hashed, so check if it exists instead of
        # equality
        self.assertTrue(vtype.get("name"))

        # Get
        types = get_delivery_vehicle_types()
        self.assertTrue(len(types) > 0)
