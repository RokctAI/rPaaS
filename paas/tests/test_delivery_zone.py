# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
import json
from frappe.tests.utils import FrappeTestCase
from paas.api.delivery_zone.delivery_zone import (
    create_delivery_zone,
    check_delivery_availability,
)


class TestDeliveryZone(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # Create a Shop
        self.shop = frappe.get_doc(
            {
                "doctype": "Shop",
                "shop_name": "Zone Shop",
                "price": 10,
                "price_per_km": 2,
                "min_amount": 15,
                "user": "Administrator",
                "phone": "+14155552671",
                "uuid": frappe.generate_hash(),
                "delivery_fee": 0,
                # Simple location at 0,0
                "location": json.dumps(
                    {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "geometry": {"type": "Point", "coordinates": [0, 0]},
                            }
                        ],
                    }
                ),
            }
        ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_zone_check(self):
        # 1. Define a simple square polygon around 10,10 to 20,20
        polygon = [[10, 10], [20, 10], [20, 20], [10, 20], [10, 10]]

        # 2. Create Delivery Zone
        # Test validation for delivery zone creation
        zone_data = {"shop": self.shop.name, "coordinates": json.dumps(polygon)}
        create_delivery_zone(zone_data)

        # 3. Check point INSIDE polygon (15, 15)
        result_inside = check_delivery_availability(15, 15, self.shop.name)
        self.assertTrue(len(result_inside) > 0)
        self.assertEqual(result_inside[0]["shop"], self.shop.name)

        # 4. Check point OUTSIDE polygon (5, 5)
        result_outside = check_delivery_availability(5, 5, self.shop.name)
        self.assertEqual(len(result_outside), 0)
