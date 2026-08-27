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

"""Unit tests for the Dispatch Route driver endpoints.

Pure unit tests following the test_cod_driver_order.py stub harness: a
minimal frappe stub is installed when no bench is available, the real
route_utils module is loaded under its composed name
(paas.delivery.api.route.route_utils), and the endpoint module's `frappe` /
`now_datetime` names are rebound per test to controllable fakes.
"""

import datetime
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DISPATCH_ROUTE_PATH = os.path.abspath(
    os.path.join(
        TESTS_DIR, "..", "src", "tenant", "api", "dispatch_route",
        "dispatch_route.py",
    )
)
ROUTE_UTILS_PATH = os.path.abspath(
    os.path.join(TESTS_DIR, "..", "src", "tenant", "api", "route", "route_utils.py")
)


def _ensure_module(name, module=None):
    if name in sys.modules:
        return sys.modules[name]
    sys.modules[name] = module or types.ModuleType(name)
    return sys.modules[name]


def _ensure_stubs():
    """Install minimal frappe/paas stubs (superset-compatible with the
    sibling stub harnesses so discovery order never matters)."""
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
        utils = getattr(frappe, "utils", None)
        if utils is None:
            utils = _ensure_module("frappe.utils")
            frappe.utils = utils
        if not hasattr(utils, "now_datetime"):
            utils.now_datetime = MagicMock()
        _ensure_module("frappe.utils", utils)
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
        frappe_mod.get_single = MagicMock()
        frappe_mod.get_traceback = MagicMock()
        frappe_mod.log_error = MagicMock()
        frappe_mod.make_get_request = MagicMock()
        frappe_mod.make_post_request = MagicMock()
        frappe_mod.session = MagicMock()
        frappe_mod.PermissionError = type(
            "PermissionError", (Exception,), {}
        )
        frappe_mod.AuthenticationError = type(
            "AuthenticationError", (Exception,), {}
        )
        sys.modules["frappe"] = frappe_mod
        sys.modules["frappe.utils"] = utils_mod

    # The endpoint imports the composed paas.delivery.api.route.route_utils;
    # load the REAL file under that name so the ordering logic under test is
    # the production one.
    _ensure_module("paas")
    _ensure_module("paas.delivery")
    _ensure_module("paas.delivery.tenant")
    _ensure_module("paas.delivery.tenant.api")
    _ensure_module("paas.delivery.tenant.api.route")
    if "paas.delivery.tenant.api.route.route_utils" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "paas.delivery.tenant.api.route.route_utils", ROUTE_UTILS_PATH
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["paas.delivery.tenant.api.route.route_utils"] = module
        spec.loader.exec_module(module)


def _exec_composed(alias, path):
    """Exec a src template exactly as the composer ships it: the composer
    copies these files substituting {app_name} with the target app package
    (paas), so the same substitution is applied before compiling."""
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read().replace("{app_name}", "paas")
    module = types.ModuleType(alias)
    module.__file__ = path
    sys.modules[alias] = module
    exec(compile(source, path, "exec"), module.__dict__)
    return module


def _load_dispatch_route():
    _ensure_stubs()
    if "dispatch_test_dispatch_route" in sys.modules:
        return sys.modules["dispatch_test_dispatch_route"]
    return _exec_composed("dispatch_test_dispatch_route", DISPATCH_ROUTE_PATH)


dispatch_route = _load_dispatch_route()

DRIVER = "driver@example.com"
NOW = datetime.datetime(2026, 8, 15, 9, 0, 0)

# Johannesburg landmarks (see test_route_utils.py).
SANDTON = (-26.1076, 28.0567)
ROSEBANK = (-26.1438, 28.0436)
CBD = (-26.2041, 28.0473)


class FakeStop:
    def __init__(self, **kwargs):
        defaults = {
            "name": None, "shop": None, "label": None,
            "latitude": None, "longitude": None, "quantity": None,
            "unit": None, "note": None, "status": "Pending",
            "completed_at": None,
        }
        defaults.update(kwargs)
        self.__dict__.update(defaults)

    def get(self, key, default=None):
        return getattr(self, key, default)


class FakeRoute:
    def __init__(self, **kwargs):
        defaults = {
            "name": "DR-0001", "deliveryman": DRIVER, "mode": "Delivery",
            "status": "Assigned", "optimize_order": 1, "notes": None,
            "stops": [],
        }
        defaults.update(kwargs)
        self.__dict__.update(defaults)
        self.saved = False

    def get(self, key, default=None):
        return getattr(self, key, default)

    def save(self, ignore_permissions=False):
        self.saved = True


class FakeDB:
    def __init__(self, fake):
        self.fake = fake

    def get_value(self, doctype, name, fieldname=None, as_dict=False):
        if doctype == "Shop":
            location = self.fake.shop_locations.get(name)
            return location
        if doctype == "Deliveryman Profile":
            return self.fake.driver_profile
        return None

    def exists(self, doctype, name):
        if doctype == "Dispatch Route":
            return name in self.fake.routes
        return False


class FakeFrappe:
    PermissionError = type("PermissionError", (Exception,), {})
    AuthenticationError = type("AuthenticationError", (Exception,), {})

    def __init__(self, user=DRIVER):
        self.session = types.SimpleNamespace(user=user)
        self.routes = {}
        self.shop_locations = {}
        self.driver_profile = None
        self.db = FakeDB(self)

    def throw(self, message, exc=None):
        raise (exc or Exception)(message)

    def get_all(self, doctype, filters=None, fields=None, order_by=None,
                limit=None):
        if doctype != "Dispatch Route":
            return []
        filters = filters or {}
        statuses = None
        if isinstance(filters.get("status"), list):
            statuses = filters["status"][1]
        rows = []
        for route in self.routes.values():
            if filters.get("deliveryman") and \
                    route.deliveryman != filters["deliveryman"]:
                continue
            if statuses and route.status not in statuses:
                continue
            rows.append({"name": route.name})
        return rows[:limit] if limit else rows

    def get_doc(self, doctype, name):
        return self.routes[name]


def _install(fake):
    dispatch_route.frappe = fake
    dispatch_route.now_datetime = lambda: NOW


class DispatchRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.fake = FakeFrappe()
        _install(self.fake)

    def _route(self, **kwargs):
        route = FakeRoute(**kwargs)
        self.fake.routes[route.name] = route
        return route


class TestGetMyDispatchRoute(DispatchRouteTestCase):
    def test_guest_is_rejected(self):
        self.fake.session.user = "Guest"
        with self.assertRaises(FakeFrappe.AuthenticationError):
            dispatch_route.get_my_dispatch_route()

    def test_no_active_route_returns_empty(self):
        self._route(status="Completed")
        result = dispatch_route.get_my_dispatch_route()
        self.assertIsNone(result["route"])
        self.assertEqual(result["stops"], [])

    def test_optimized_route_orders_pending_from_driver_position(self):
        self.fake.driver_profile = {
            "latitude": SANDTON[0], "longitude": SANDTON[1],
        }
        self._route(
            mode="Delivery",
            optimize_order=1,
            stops=[
                FakeStop(name="s-cbd", label="CBD",
                         latitude=CBD[0], longitude=CBD[1],
                         quantity=12, unit="bottles"),
                FakeStop(name="s-rosebank", label="Rosebank",
                         latitude=ROSEBANK[0], longitude=ROSEBANK[1],
                         quantity=6, unit="bottles"),
            ],
        )
        result = dispatch_route.get_my_dispatch_route()
        self.assertEqual(result["route"]["name"], "DR-0001")
        self.assertEqual(result["route"]["mode"], "Delivery")
        self.assertEqual(result["route"]["pending_stops"], 2)
        # Rosebank is nearer to Sandton than the CBD.
        self.assertEqual(
            [s["ref_name"] for s in result["stops"]],
            ["s-rosebank", "s-cbd"],
        )
        self.assertEqual(
            [s["sequence"] for s in result["stops"]], [1, 2]
        )
        self.assertEqual(result["stops"][0]["quantity"], 6)
        self.assertEqual(result["stops"][0]["unit"], "bottles")
        self.assertEqual(result["stops"][0]["stop_type"], "delivery")
        self.assertIsNotNone(
            result["stops"][0]["distance_from_previous_km"]
        )

    def test_unoptimized_route_keeps_admin_order(self):
        self.fake.driver_profile = {
            "latitude": SANDTON[0], "longitude": SANDTON[1],
        }
        self._route(
            optimize_order=0,
            stops=[
                FakeStop(name="s-cbd", latitude=CBD[0],
                         longitude=CBD[1]),
                FakeStop(name="s-rosebank", latitude=ROSEBANK[0],
                         longitude=ROSEBANK[1]),
            ],
        )
        result = dispatch_route.get_my_dispatch_route()
        self.assertEqual(
            [s["ref_name"] for s in result["stops"]],
            ["s-cbd", "s-rosebank"],
        )

    def test_shop_coordinates_resolved_from_location_json(self):
        self.fake.shop_locations["Water Depot"] = (
            '{"latitude": %s, "longitude": %s}' % SANDTON
        )
        self._route(
            mode="Pickup",
            stops=[FakeStop(name="s1", shop="Water Depot")],
        )
        result = dispatch_route.get_my_dispatch_route()
        stop = result["stops"][0]
        self.assertEqual(stop["latitude"], SANDTON[0])
        self.assertEqual(stop["longitude"], SANDTON[1])
        self.assertEqual(stop["label"], "Water Depot")
        self.assertEqual(stop["stop_type"], "pickup")

    def test_stop_without_any_coordinates_is_flagged(self):
        self._route(
            stops=[
                FakeStop(name="s1", label="Unknown place"),
                FakeStop(name="s2", latitude=CBD[0], longitude=CBD[1]),
            ],
        )
        result = dispatch_route.get_my_dispatch_route()
        self.assertEqual(
            [s["ref_name"] for s in result["stops"]], ["s2", "s1"]
        )
        self.assertTrue(result["stops"][1]["missing_coordinates"])

    def test_done_stops_come_first_pending_after(self):
        self._route(
            stops=[
                FakeStop(name="s1", latitude=CBD[0], longitude=CBD[1],
                         status="Done"),
                FakeStop(name="s2", latitude=ROSEBANK[0],
                         longitude=ROSEBANK[1]),
            ],
        )
        result = dispatch_route.get_my_dispatch_route()
        self.assertEqual(
            [s["ref_name"] for s in result["stops"]], ["s1", "s2"]
        )
        self.assertEqual(result["route"]["pending_stops"], 1)


class TestGetActiveDispatchStops(DispatchRouteTestCase):
    def test_returns_only_pending_stops(self):
        self._route(
            stops=[
                FakeStop(name="s1", latitude=CBD[0], longitude=CBD[1],
                         status="Done"),
                FakeStop(name="s2", latitude=ROSEBANK[0],
                         longitude=ROSEBANK[1]),
            ],
        )
        route, stops = dispatch_route.get_active_dispatch_stops(DRIVER)
        self.assertEqual(route.name, "DR-0001")
        self.assertEqual([s["ref_name"] for s in stops], ["s2"])
        self.assertEqual(stops[0]["meta"]["route_id"], "DR-0001")

    def test_no_route_returns_empty(self):
        route, stops = dispatch_route.get_active_dispatch_stops(DRIVER)
        self.assertIsNone(route)
        self.assertEqual(stops, [])


class TestCompleteDispatchStop(DispatchRouteTestCase):
    def _two_stop_route(self, **kwargs):
        return self._route(
            stops=[
                FakeStop(name="s1", latitude=CBD[0], longitude=CBD[1]),
                FakeStop(name="s2", latitude=ROSEBANK[0],
                         longitude=ROSEBANK[1]),
            ],
            **kwargs,
        )

    def test_marks_done_and_flips_route_in_progress(self):
        route = self._two_stop_route()
        result = dispatch_route.complete_dispatch_stop("DR-0001", "s1")
        self.assertEqual(result["stop_status"], "Done")
        self.assertEqual(result["route_status"], "In Progress")
        self.assertEqual(result["pending_stops"], 1)
        self.assertEqual(route.stops[0].status, "Done")
        self.assertEqual(route.stops[0].completed_at, NOW)
        self.assertTrue(route.saved)

    def test_last_completion_completes_the_route(self):
        self._two_stop_route()
        dispatch_route.complete_dispatch_stop("DR-0001", "s1")
        result = dispatch_route.complete_dispatch_stop(
            "DR-0001", "s2", status="skipped"
        )
        self.assertEqual(result["stop_status"], "Skipped")
        self.assertEqual(result["route_status"], "Completed")
        self.assertEqual(result["pending_stops"], 0)

    def test_repeat_completion_is_idempotent(self):
        route = self._two_stop_route()
        dispatch_route.complete_dispatch_stop("DR-0001", "s1")
        first_completed_at = route.stops[0].completed_at
        result = dispatch_route.complete_dispatch_stop("DR-0001", "s1")
        self.assertEqual(result["stop_status"], "Done")
        self.assertEqual(route.stops[0].completed_at, first_completed_at)
        self.assertEqual(result["route_status"], "In Progress")

    def test_other_drivers_route_is_forbidden(self):
        self._two_stop_route(deliveryman="someone@else.com")
        with self.assertRaises(FakeFrappe.PermissionError):
            dispatch_route.complete_dispatch_stop("DR-0001", "s1")

    def test_unknown_status_is_rejected(self):
        self._two_stop_route()
        with self.assertRaises(Exception):
            dispatch_route.complete_dispatch_stop(
                "DR-0001", "s1", status="bogus"
            )

    def test_unknown_stop_is_rejected(self):
        self._two_stop_route()
        with self.assertRaises(Exception):
            dispatch_route.complete_dispatch_stop("DR-0001", "nope")

    def test_missing_route_is_rejected(self):
        with self.assertRaises(Exception):
            dispatch_route.complete_dispatch_stop("DR-404", "s1")

    def test_inactive_route_is_rejected(self):
        self._two_stop_route(status="Cancelled")
        with self.assertRaises(Exception):
            dispatch_route.complete_dispatch_stop("DR-0001", "s1")

    def test_last_stop_replay_after_auto_complete_is_idempotent(self):
        # Completing the last pending stop flips the route to Completed;
        # a network retry of that same call must return the state, not
        # throw "route is not active".
        route = self._two_stop_route()
        dispatch_route.complete_dispatch_stop("DR-0001", "s1")
        dispatch_route.complete_dispatch_stop("DR-0001", "s2")
        self.assertEqual(route.status, "Completed")
        result = dispatch_route.complete_dispatch_stop("DR-0001", "s2")
        self.assertEqual(result["route_status"], "Completed")
        self.assertEqual(result["stop_status"], "Done")
        self.assertEqual(result["pending_stops"], 0)

    def test_completed_route_with_pending_stop_still_rejected(self):
        # A Completed route only replays for stops that already left
        # Pending — a fresh completion attempt is still an error.
        self._route(
            status="Completed",
            stops=[FakeStop(name="s1", latitude=CBD[0],
                            longitude=CBD[1])],
        )
        with self.assertRaises(Exception):
            dispatch_route.complete_dispatch_stop("DR-0001", "s1")


if __name__ == "__main__":
    unittest.main()
