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

"""Unit tests for the merged driver route endpoint (get_driver_route),
the enriched paginate wrapper and the update_location parameter
tolerance.

Follows the test_cod_driver_order.py stub harness: a minimal frappe/paas
stub is installed when no bench is available; the REAL route_utils module
is additionally loaded under its composed name so the ordering logic
under test is the production one, and paas.delivery.api.dispatch_route is stubbed
with a controllable fake.
"""

import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DRIVER_ORDER_PATH = os.path.abspath(
    os.path.join(
        TESTS_DIR, "..", "src", "tenant", "api", "driver_order", "driver_order.py"
    )
)
DRIVER_PATH = os.path.abspath(
    os.path.join(TESTS_DIR, "..", "src", "tenant", "api", "driver", "driver.py")
)
ROUTE_UTILS_PATH = os.path.abspath(
    os.path.join(
        TESTS_DIR, "..", "..", "..", "delivery", "frappe", "src", "tenant", "api",
        "route", "route_utils.py",
    )
)


def _ensure_module(name):
    if name in sys.modules:
        return sys.modules[name]
    sys.modules[name] = types.ModuleType(name)
    return sys.modules[name]


def _ensure_stubs():
    """Install minimal frappe/paas stubs, superset-compatible with the
    sibling test_cod_driver_order.py harness."""
    try:
        import frappe  # noqa: F401
        if not hasattr(frappe, "whitelist"):
            frappe.whitelist = lambda *a, **k: (lambda fn: fn)
        for attr in ("throw", "db", "get_doc", "get_list", "get_all",
                     "session"):
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
        frappe_mod.session = MagicMock()
        frappe_mod.PermissionError = type(
            "PermissionError", (Exception,), {}
        )
        frappe_mod.AuthenticationError = type(
            "AuthenticationError", (Exception,), {}
        )
        sys.modules["frappe"] = frappe_mod
        sys.modules["frappe.utils"] = utils_mod

    _ensure_module("paas")
    _ensure_module("paas.delivery")
    _ensure_module("paas.delivery.tenant")
    _ensure_module("paas.delivery.tenant.api")
    delivery_man_pkg = _ensure_module("paas.delivery.tenant.api.delivery_man")
    if "paas.delivery.tenant.api.delivery_man.delivery_man" not in sys.modules:
        delivery_man_mod = types.ModuleType(
            "paas.delivery.tenant.api.delivery_man.delivery_man"
        )
        sys.modules["paas.delivery.tenant.api.delivery_man.delivery_man"] = (
            delivery_man_mod
        )
        delivery_man_pkg.delivery_man = delivery_man_mod
    delivery_man_mod = sys.modules["paas.delivery.tenant.api.delivery_man.delivery_man"]
    for attr in ("get_deliveryman_orders", "get_deliveryman_parcel_orders",
                 "get_deliveryman_statistics"):
        if not hasattr(delivery_man_mod, attr):
            setattr(delivery_man_mod, attr, MagicMock())

    _ensure_module("paas.delivery.tenant.api.route")
    if "paas.delivery.tenant.api.route.route_utils" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "paas.delivery.tenant.api.route.route_utils", ROUTE_UTILS_PATH
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["paas.delivery.tenant.api.route.route_utils"] = module
        spec.loader.exec_module(module)

    _ensure_module("paas.delivery.tenant.api.dispatch_route")
    if "paas.delivery.tenant.api.dispatch_route.dispatch_route" not in sys.modules:
        dispatch_mod = types.ModuleType(
            "paas.delivery.tenant.api.dispatch_route.dispatch_route"
        )
        dispatch_mod.get_active_dispatch_stops = MagicMock(
            return_value=(None, [])
        )
        sys.modules["paas.delivery.tenant.api.dispatch_route.dispatch_route"] = (
            dispatch_mod
        )


def _load(path, alias):
    """Exec a src template exactly as the composer ships it: the composer
    copies these files substituting {app_name} with the target app package
    (paas), so the same substitution is applied before compiling."""
    _ensure_stubs()
    if alias in sys.modules:
        return sys.modules[alias]
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read().replace("{app_name}", "paas")
    module = types.ModuleType(alias)
    module.__file__ = path
    sys.modules[alias] = module
    exec(compile(source, path, "exec"), module.__dict__)
    return module


driver_order = _load(DRIVER_ORDER_PATH, "route_test_driver_order")
driver = _load(DRIVER_PATH, "route_test_driver")

DRIVER_USER = "driver@example.com"

# Johannesburg landmarks (see delivery test_route_utils.py).
SANDTON = (-26.1076, 28.0567)
ROSEBANK = (-26.1438, 28.0436)
CBD = (-26.2041, 28.0473)
SOWETO = (-26.2678, 27.8585)


def _loc_json(coords):
    return '{"latitude": %s, "longitude": %s}' % coords


class FakeDB:
    def __init__(self, fake):
        self.fake = fake

    def get_value(self, doctype, name, fieldname=None, as_dict=False):
        if doctype == "Shop":
            return self.fake.shop_locations.get(name)
        if doctype == "PaaS Payment Gateway":
            return self.fake.gateways.get(name)
        if doctype == "Deliveryman Profile":
            return self.fake.driver_profile
        return None

    def exists(self, doctype, name):
        return False

    def count(self, doctype, filters=None):
        if doctype == "Order":
            return self.fake.order_count
        return 0


class FakeFrappe:
    PermissionError = type("PermissionError", (Exception,), {})
    AuthenticationError = type("AuthenticationError", (Exception,), {})

    def __init__(self, user=DRIVER_USER):
        self.session = types.SimpleNamespace(user=user)
        self.orders = []
        self.parcels = []
        self.transactions = {}
        self.gateways = {}
        self.shop_locations = {}
        self.driver_profile = None
        self.order_count = 0
        self.db = FakeDB(self)

    def throw(self, message, exc=None):
        raise (exc or Exception)(message)

    def get_all(self, doctype, filters=None, fields=None, order_by=None,
                limit=None):
        if doctype == "Order":
            return [dict(o) for o in self.orders]
        if doctype == "Parcel Order":
            return [dict(p) for p in self.parcels]
        if doctype == "Transaction":
            payable = (filters or {}).get("payable_id")
            return [dict(t) for t in self.transactions.get(payable, [])]
        return []


class DriverRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.fake = FakeFrappe()
        driver_order.frappe = self.fake
        self.dispatch_mod = sys.modules[
            "paas.delivery.tenant.api.dispatch_route.dispatch_route"
        ]
        self._saved_dispatch = self.dispatch_mod.get_active_dispatch_stops
        self.dispatch_mod.get_active_dispatch_stops = MagicMock(
            return_value=(None, [])
        )

    def tearDown(self):
        self.dispatch_mod.get_active_dispatch_stops = (
            self._saved_dispatch
        )


class TestGetDriverRoute(DriverRouteTestCase):
    def test_guest_is_rejected(self):
        self.fake.session.user = "Guest"
        with self.assertRaises(FakeFrappe.AuthenticationError):
            driver_order.get_driver_route()

    def test_order_yields_pickup_before_dropoff_with_payment_tag(self):
        self.fake.shop_locations["Water Depot"] = _loc_json(SANDTON)
        self.fake.orders = [
            {
                "name": "ORD-1", "shop": "Water Depot",
                "total_price": 250, "status": "Accepted",
                "location": _loc_json(CBD), "address": None,
            }
        ]
        self.fake.transactions["ORD-1"] = [
            {"name": "TX-1", "payment_gateway": "GW-CASH",
             "status": "Pending"},
        ]
        self.fake.gateways["GW-CASH"] = "Cash"
        # Start right next to the drop-off: the pickup must still come
        # first.
        stops = driver_order.get_driver_route(
            latitude=CBD[0] + 0.001, longitude=CBD[1] + 0.001
        )
        self.assertEqual(
            [(s["stop_type"], s["ref_name"]) for s in stops],
            [("pickup", "ORD-1"), ("dropoff", "ORD-1")],
        )
        self.assertEqual(stops[0]["label"], "Water Depot")
        self.assertEqual(stops[0]["latitude"], SANDTON[0])
        self.assertEqual(stops[1]["meta"]["payment_tag"], "cash")
        self.assertEqual(stops[1]["meta"]["total_price"], 250)
        self.assertEqual([s["sequence"] for s in stops], [1, 2])

    def test_shipped_order_has_no_pickup_stop(self):
        self.fake.shop_locations["Water Depot"] = _loc_json(SANDTON)
        self.fake.orders = [
            {
                "name": "ORD-1", "shop": "Water Depot",
                "total_price": 100, "status": "Shipped",
                "location": _loc_json(CBD), "address": None,
            }
        ]
        stops = driver_order.get_driver_route(
            latitude=SANDTON[0], longitude=SANDTON[1]
        )
        self.assertEqual(
            [(s["stop_type"], s["ref_name"]) for s in stops],
            [("dropoff", "ORD-1")],
        )

    def test_malformed_order_location_never_crashes(self):
        self.fake.orders = [
            {
                "name": "ORD-1", "shop": None, "total_price": 100,
                "status": "Accepted", "location": "not json at all",
                "address": "12 Main Rd",
            }
        ]
        stops = driver_order.get_driver_route(
            latitude=SANDTON[0], longitude=SANDTON[1]
        )
        self.assertEqual(len(stops), 1)
        self.assertTrue(stops[0]["missing_coordinates"])
        self.assertEqual(stops[0]["label"], "12 Main Rd")

    def test_parcel_customer_text_destination_goes_to_tail(self):
        self.fake.parcels = [
            {
                "name": "PAR-1", "status": "Accepted", "total_price": 80,
                "address_from": _loc_json(ROSEBANK),
                "address_to": "Customer: Jane Doe",
                "username_from": "Depot", "username_to": "Jane Doe",
                "cod_amount": 80,
            }
        ]
        self.fake.orders = [
            {
                "name": "ORD-1", "shop": None, "total_price": 100,
                "status": "Shipped", "location": _loc_json(CBD),
                "address": None,
            }
        ]
        stops = driver_order.get_driver_route(
            latitude=SANDTON[0], longitude=SANDTON[1]
        )
        # Rosebank pickup is nearest, then the CBD drop-off; the
        # coordinate-less parcel drop-off rides the tail.
        self.assertEqual(
            [(s["ref_doctype"], s["stop_type"]) for s in stops],
            [
                ("Parcel Order", "pickup"),
                ("Order", "dropoff"),
                ("Parcel Order", "dropoff"),
            ],
        )
        self.assertTrue(stops[2]["missing_coordinates"])
        self.assertEqual(stops[2]["label"], "Jane Doe")
        self.assertEqual(stops[0]["meta"]["payment_tag"], "cash")

    def test_dispatch_stops_are_merged_and_ordered(self):
        self.dispatch_mod.get_active_dispatch_stops.return_value = (
            types.SimpleNamespace(name="DR-1"),
            [
                {
                    "stop_type": "delivery",
                    "ref_doctype": "Dispatch Route Stop",
                    "ref_name": "s1",
                    "label": "Rosebank Spaza",
                    "latitude": ROSEBANK[0],
                    "longitude": ROSEBANK[1],
                    "quantity": 18, "unit": "bottles",
                    "meta": {"route_id": "DR-1"},
                }
            ],
        )
        self.fake.orders = [
            {
                "name": "ORD-1", "shop": None, "total_price": 100,
                "status": "Shipped", "location": _loc_json(SOWETO),
                "address": None,
            }
        ]
        stops = driver_order.get_driver_route(
            latitude=SANDTON[0], longitude=SANDTON[1]
        )
        # Rosebank (dispatch) is nearer to Sandton than Soweto.
        self.assertEqual(
            [s["ref_name"] for s in stops], ["s1", "ORD-1"]
        )
        self.assertEqual(stops[0]["quantity"], 18)
        self.assertEqual(stops[0]["unit"], "bottles")

    def test_start_falls_back_to_deliveryman_profile(self):
        self.fake.driver_profile = {
            "latitude": SOWETO[0], "longitude": SOWETO[1],
        }
        self.fake.orders = [
            {"name": "O-CBD", "shop": None, "total_price": 1,
             "status": "Shipped", "location": _loc_json(CBD),
             "address": None},
            {"name": "O-SAN", "shop": None, "total_price": 1,
             "status": "Shipped", "location": _loc_json(SANDTON),
             "address": None},
        ]
        stops = driver_order.get_driver_route()
        # From Soweto the CBD is nearer than Sandton.
        self.assertEqual(
            [s["ref_name"] for s in stops], ["O-CBD", "O-SAN"]
        )


class TestGetDriverOrdersPaginate(DriverRouteTestCase):
    def setUp(self):
        super().setUp()
        self._saved_get_orders = driver_order._get_orders

    def tearDown(self):
        driver_order._get_orders = self._saved_get_orders
        super().tearDown()

    def test_returns_data_and_meta_shape(self):
        rows = [{"name": "ORD-1"}, {"name": "ORD-2"}]
        driver_order._get_orders = lambda *a, **k: rows
        self.fake.order_count = 7
        # Give the stubbed delivery_man module a working normalizer so
        # the count path runs.
        delivery_man_mod = sys.modules[
            "paas.delivery.tenant.api.delivery_man.delivery_man"
        ]
        had = hasattr(delivery_man_mod, "normalize_statuses")
        delivery_man_mod.normalize_statuses = lambda s: (
            ["Accepted", "Shipped"] if s else None
        )
        try:
            result = driver_order.get_driver_orders_paginate(
                statuses='["accepted", "on_a_way"]'
            )
        finally:
            if not had:
                del delivery_man_mod.normalize_statuses
        self.assertEqual(result["data"], rows)
        self.assertEqual(result["meta"], {"total": 7})

    def test_meta_falls_back_to_row_count_without_normalizer(self):
        rows = [{"name": "ORD-1"}]
        driver_order._get_orders = lambda *a, **k: rows
        result = driver_order.get_driver_orders_paginate()
        self.assertEqual(result["data"], rows)
        self.assertEqual(result["meta"], {"total": 1})


class FakeProfileDoc:
    def __init__(self):
        self.user = None
        self.latitude = None
        self.longitude = None
        self.saved = False

    def save(self, ignore_permissions=False):
        self.saved = True

    def insert(self, ignore_permissions=False):
        pass


class TestUpdateLocation(unittest.TestCase):
    def setUp(self):
        self.doc = FakeProfileDoc()
        fake = FakeFrappe()
        fake.db.exists = lambda doctype, name: True
        fake.get_doc = lambda doctype, name: self.doc
        driver.frappe = fake

    def test_accepts_latitude_longitude_keys(self):
        result = driver.update_location(
            latitude=-26.1, longitude=28.05
        )
        self.assertTrue(result["status"])
        self.assertEqual(self.doc.latitude, -26.1)
        self.assertEqual(self.doc.longitude, 28.05)
        self.assertTrue(self.doc.saved)

    def test_accepts_legacy_lat_lng_keys(self):
        result = driver.update_location(lat=-26.2, lng=28.04)
        self.assertTrue(result["status"])
        self.assertEqual(self.doc.latitude, -26.2)
        self.assertEqual(self.doc.longitude, 28.04)


if __name__ == "__main__":
    unittest.main()
