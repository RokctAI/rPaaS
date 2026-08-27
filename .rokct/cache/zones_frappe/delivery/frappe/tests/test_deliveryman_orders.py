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

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""Unit tests for the extended deliveryman order list (delivery_man.py):
status normalization and the OrderDetailData-shaped serialization with
parsed coordinates, shop coords from the Shop.location JSON and the
transaction payment tag. Stub harness per test_cod_driver_order.py."""

import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DELIVERY_MAN_PATH = os.path.abspath(
    os.path.join(
        TESTS_DIR, "..", "src", "tenant", "api", "delivery_man", "delivery_man.py"
    )
)


def _ensure_stubs():
    try:
        import frappe  # noqa: F401
        if not hasattr(frappe, "whitelist"):
            frappe.whitelist = lambda *a, **k: (lambda fn: fn)
        for attr in ("throw", "db", "get_doc", "get_list", "get_all",
                     "session", "new_doc", "qb"):
            if not hasattr(frappe, attr):
                setattr(frappe, attr, MagicMock())
        for exc in ("PermissionError", "AuthenticationError"):
            if not hasattr(frappe, exc):
                setattr(frappe, exc, type(exc, (Exception,), {}))
    except ImportError:
        frappe_mod = types.ModuleType("frappe")
        utils_mod = types.ModuleType("frappe.utils")
        utils_mod.cint = lambda v: int(float(v or 0))
        utils_mod.now_datetime = MagicMock()
        utils_mod.add_to_date = MagicMock()
        frappe_mod.utils = utils_mod
        frappe_mod.whitelist = lambda *a, **k: (lambda fn: fn)
        frappe_mod.throw = MagicMock(side_effect=Exception("frappe.throw"))
        frappe_mod.db = MagicMock()
        frappe_mod.get_doc = MagicMock()
        frappe_mod.get_list = MagicMock()
        frappe_mod.get_all = MagicMock()
        frappe_mod.new_doc = MagicMock()
        frappe_mod.qb = MagicMock()
        frappe_mod.session = MagicMock()
        frappe_mod.PermissionError = type(
            "PermissionError", (Exception,), {}
        )
        frappe_mod.AuthenticationError = type(
            "AuthenticationError", (Exception,), {}
        )
        sys.modules["frappe"] = frappe_mod
        sys.modules["frappe.utils"] = utils_mod


def _load_delivery_man():
    _ensure_stubs()
    if "orders_test_delivery_man" in sys.modules:
        return sys.modules["orders_test_delivery_man"]
    spec = importlib.util.spec_from_file_location(
        "orders_test_delivery_man", DELIVERY_MAN_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["orders_test_delivery_man"] = module
    spec.loader.exec_module(module)
    return module


delivery_man = _load_delivery_man()


class FakeDB:
    def __init__(self, fake):
        self.fake = fake

    def get_value(self, doctype, name, fieldname=None, as_dict=False):
        if doctype == "Shop":
            return self.fake.shops.get(name)
        if doctype == "PaaS Payment Gateway":
            return self.fake.gateways.get(name)
        return None


class FakeFrappe:
    PermissionError = type("PermissionError", (Exception,), {})
    AuthenticationError = type("AuthenticationError", (Exception,), {})

    def __init__(self):
        self.session = types.SimpleNamespace(user="driver@example.com")
        self.shops = {}
        self.gateways = {}
        self.transactions = {}
        self.orders = []
        self.captured_filters = None
        self.db = FakeDB(self)

    def throw(self, message, exc=None):
        raise (exc or Exception)(message)

    def get_list(self, doctype, filters=None, fields=None, offset=0,
                 limit=20, order_by=None):
        self.captured_filters = filters
        return [dict(o) for o in self.orders]

    def get_all(self, doctype, filters=None, fields=None, order_by=None,
                limit=None):
        if doctype == "Transaction":
            payable = (filters or {}).get("payable_id")
            return [dict(t) for t in self.transactions.get(payable, [])]
        return []


class DeliverymanOrdersTestCase(unittest.TestCase):
    def setUp(self):
        self.fake = FakeFrappe()
        delivery_man.frappe = self.fake


class TestNormalizeStatuses(unittest.TestCase):
    def test_legacy_lowercase_json_string(self):
        self.assertEqual(
            delivery_man.normalize_statuses(
                '["accepted", "ready", "on_a_way"]'
            ),
            ["Accepted", "Shipped"],
        )

    def test_canonical_list_passthrough(self):
        self.assertEqual(
            delivery_man.normalize_statuses(["Delivered"]), ["Delivered"]
        )

    def test_unknown_and_empty_yield_none(self):
        self.assertIsNone(delivery_man.normalize_statuses(None))
        self.assertIsNone(delivery_man.normalize_statuses([]))
        self.assertIsNone(delivery_man.normalize_statuses(["bogus"]))


class TestSerializeDeliverymanOrder(DeliverymanOrdersTestCase):
    def test_full_shape_with_coordinates_shop_and_cash_tag(self):
        self.fake.shops["Water Depot"] = {
            "location": '{"latitude": -26.1, "longitude": 28.05}',
            "logo": "/files/logo.png",
        }
        self.fake.transactions["ORD-9"] = [
            {"name": "TX-1", "payment_gateway": "GW", "status": "Pending"}
        ]
        self.fake.gateways["GW"] = "Cash"
        row = delivery_man.serialize_deliveryman_order(
            {
                "name": "ORD-9",
                "shop": "Water Depot",
                "total_price": 320,
                "delivery_fee": 25,
                "status": "Accepted",
                "creation": "2026-08-15 08:00:00",
                "location": '{"latitude": "-26.2", "longitude": "28.04"}',
                "address": "12 Main Rd",
            }
        )
        self.assertEqual(row["name"], "ORD-9")
        self.assertIsNone(row["id"])  # non-numeric Frappe name
        self.assertEqual(
            row["location"], {"latitude": -26.2, "longitude": 28.04}
        )
        self.assertEqual(row["address"], {"address": "12 Main Rd"})
        self.assertEqual(row["shop"]["uuid"], "Water Depot")
        self.assertEqual(
            row["shop"]["translation"], {"title": "Water Depot"}
        )
        self.assertEqual(
            row["shop"]["location"],
            {"latitude": -26.1, "longitude": 28.05},
        )
        self.assertEqual(row["shop"]["logo_img"], "/files/logo.png")
        self.assertEqual(
            row["transaction"], {"payment_system": {"tag": "cash"}}
        )
        self.assertEqual(row["total_price"], 320)

    def test_numeric_name_becomes_int_id(self):
        row = delivery_man.serialize_deliveryman_order(
            {"name": "1042", "total_price": 10, "status": "New"}
        )
        self.assertEqual(row["id"], 1042)

    def test_malformed_location_yields_none_without_crash(self):
        row = delivery_man.serialize_deliveryman_order(
            {"name": "ORD-1", "location": "not-json", "status": "New"}
        )
        self.assertIsNone(row["location"])
        self.assertIsNone(row["transaction"])
        self.assertIsNone(row["shop"])

    def test_nan_infinity_location_yields_none(self):
        # json.loads accepts NaN/Infinity literals; a NaN coordinate
        # would serialize as invalid JSON for the app's decoder.
        row = delivery_man.serialize_deliveryman_order(
            {
                "name": "ORD-1",
                "location": '{"latitude": NaN, "longitude": Infinity}',
                "status": "New",
            }
        )
        self.assertIsNone(row["location"])

    def test_adult_flag_rides_along_when_set(self):
        row = delivery_man.serialize_deliveryman_order(
            {"name": "ORD-1", "status": "New", "contains_adult_items": 1}
        )
        self.assertEqual(row["contains_adult_items"], 1)

    def test_adult_flag_absent_when_false(self):
        # weather_notice precedent: absence is the false state.
        row = delivery_man.serialize_deliveryman_order(
            {"name": "ORD-1", "status": "New", "contains_adult_items": 0}
        )
        self.assertNotIn("contains_adult_items", row)

    def test_adult_flag_absent_when_doctype_predates_field(self):
        # FakeFrappe has no get_meta: the guarded lookup must swallow
        # that (an orders module predating the field) and emit nothing.
        row = delivery_man.serialize_deliveryman_order(
            {"name": "ORD-1", "status": "New"}
        )
        self.assertNotIn("contains_adult_items", row)

    def test_adult_flag_fetched_when_row_lacks_the_field(self):
        # Rows from a fields-list that predates the flag: the serializer
        # consults Order meta and fetches the value itself.
        self.fake.get_meta = lambda doctype: types.SimpleNamespace(
            has_field=lambda f: f == "contains_adult_items"
        )
        orig_get_value = self.fake.db.get_value

        def _get_value(doctype, name, fieldname=None, as_dict=False):
            if doctype == "Order" and fieldname == "contains_adult_items":
                return 1 if name == "ORD-18" else 0
            return orig_get_value(doctype, name, fieldname, as_dict)

        self.fake.db.get_value = _get_value
        row = delivery_man.serialize_deliveryman_order(
            {"name": "ORD-18", "status": "New"}
        )
        self.assertEqual(row["contains_adult_items"], 1)
        row = delivery_man.serialize_deliveryman_order(
            {"name": "ORD-1", "status": "New"}
        )
        self.assertNotIn("contains_adult_items", row)


class TestGetDeliverymanOrders(DeliverymanOrdersTestCase):
    def test_statuses_filter_is_normalized(self):
        self.fake.orders = [
            {"name": "ORD-1", "status": "Accepted", "total_price": 10}
        ]
        rows = delivery_man.get_deliveryman_orders(
            statuses='["accepted", "on_a_way"]'
        )
        self.assertEqual(
            self.fake.captured_filters["status"],
            ["in", ["Accepted", "Shipped"]],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "ORD-1")

    def test_guest_is_rejected(self):
        self.fake.session.user = "Guest"
        with self.assertRaises(FakeFrappe.AuthenticationError):
            delivery_man.get_deliveryman_orders()


if __name__ == "__main__":
    unittest.main()
