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

"""Unit tests for the per-stop severe-weather notice annotation:
src/weather_notice/weather_notice.py (guarded cross-module read of the
weather module's active heads-ups) and its wiring into
serialize_deliveryman_order / serialize_dispatch_stop.

Stub harness per test_cod_driver_order.py, extended with PACKAGED module
loading (helpers below): the src templates are loaded under their composed
dotted names ("paas.delivery. ...") with __package__ set, so the guarded
relative imports resolve exactly as they do in a composed shell. The
sibling standalone harnesses (test_deliveryman_orders.py,
test_dispatch_route.py) keep loading the same files WITHOUT a package -
there the guarded import falls back to None, which is itself an asserted
behavior here.
"""

import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", "src", "tenant"))
WEATHER_NOTICE_PATH = os.path.join(
    SRC_DIR, "weather_notice", "weather_notice.py")
DELIVERY_MAN_PATH = os.path.join(
    SRC_DIR, "api", "delivery_man", "delivery_man.py")
DISPATCH_ROUTE_PATH = os.path.join(
    SRC_DIR, "api", "dispatch_route", "dispatch_route.py")
ROUTE_UTILS_PATH = os.path.join(SRC_DIR, "api", "route", "route_utils.py")


def _ensure_stubs():
    """Minimal frappe stub, superset-compatible with the sibling harnesses
    so discovery order never matters."""
    try:
        import frappe  # noqa: F401
        if not hasattr(frappe, "whitelist"):
            frappe.whitelist = lambda *a, **k: (lambda fn: fn)
        for attr in ("throw", "db", "get_doc", "get_list", "get_all",
                     "get_attr", "conf", "cache", "session", "new_doc",
                     "qb", "log_error", "get_traceback"):
            if not hasattr(frappe, attr):
                setattr(frappe, attr, MagicMock())
        for exc in ("PermissionError", "AuthenticationError"):
            if not hasattr(frappe, exc):
                setattr(frappe, exc, type(exc, (Exception,), {}))
        utils = getattr(frappe, "utils", None)
        if utils is None:
            utils = types.ModuleType("frappe.utils")
            frappe.utils = utils
            sys.modules["frappe.utils"] = utils
        if not hasattr(utils, "cint"):
            utils.cint = lambda v: int(float(v or 0))
        if not hasattr(utils, "now_datetime"):
            utils.now_datetime = MagicMock()
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
        frappe_mod.get_attr = MagicMock(side_effect=ImportError("absent"))
        frappe_mod.conf = MagicMock()
        frappe_mod.cache = MagicMock()
        frappe_mod.new_doc = MagicMock()
        frappe_mod.qb = MagicMock()
        frappe_mod.session = MagicMock()
        frappe_mod.log_error = MagicMock()
        frappe_mod.get_traceback = MagicMock()
        frappe_mod.PermissionError = type(
            "PermissionError", (Exception,), {})
        frappe_mod.AuthenticationError = type(
            "AuthenticationError", (Exception,), {})
        sys.modules["frappe"] = frappe_mod
        sys.modules["frappe.utils"] = utils_mod


def _ensure_pkg(name):
    if name not in sys.modules:
        mod = types.ModuleType(name)
        mod.__path__ = []  # mark as package
        sys.modules[name] = mod
    return sys.modules[name]


def _load_packaged(dotted_name, path):
    """Exec a src template under its composed dotted name with __package__
    set, substituting {app_name} exactly as the backend composer does -
    so relative imports resolve like in a composed shell. An entry another
    harness registered as a bare MagicMock placeholder (no __file__ - e.g.
    test_cod_parcel_driver.py's import satisfier) is replaced with the
    real module; a real prior load of the same file is reused."""
    existing = sys.modules.get(dotted_name)
    if existing is not None and getattr(existing, "__file__", None) == path:
        return existing
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read().replace("{app_name}", "paas")
    package, leaf = dotted_name.rsplit(".", 1)
    module = types.ModuleType(dotted_name)
    module.__file__ = path
    module.__package__ = package
    sys.modules[dotted_name] = module
    exec(compile(source, path, "exec"), module.__dict__)
    setattr(sys.modules[package], leaf, module)
    return module


def _load_modules():
    _ensure_stubs()
    for pkg in ("paas", "paas.delivery", "paas.delivery.tenant",
                "paas.delivery.tenant.weather_notice",
                "paas.delivery.tenant.api", "paas.delivery.tenant.api.route",
                "paas.delivery.tenant.api.delivery_man",
                "paas.delivery.tenant.api.dispatch_route"):
        _ensure_pkg(pkg)
    if "paas.delivery.tenant.api.route.route_utils" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "paas.delivery.tenant.api.route.route_utils", ROUTE_UTILS_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules["paas.delivery.tenant.api.route.route_utils"] = module
        spec.loader.exec_module(module)
    wn = _load_packaged(
        "paas.delivery.tenant.weather_notice.weather_notice", WEATHER_NOTICE_PATH)
    dm = _load_packaged(
        "paas.delivery.tenant.api.delivery_man.delivery_man", DELIVERY_MAN_PATH)
    dr = _load_packaged(
        "paas.delivery.tenant.api.dispatch_route.dispatch_route",
        DISPATCH_ROUTE_PATH)
    return wn, dm, dr


weather_notice, delivery_man, dispatch_route = _load_modules()


SAMPLE_WARNING = {
    "id": "SWW-001",
    "event_class": "flash_flood",
    "severity": "warning",
    "severity_label": "Please take care",
    "headline": "Flash flooding likely near Umtata",
    "message": (
        "Flash flooding looks likely around Umtata in the coming hours. "
        "Please avoid low bridges and flooded roads."
    ),
    "onset": "2026-08-19T12:00:00Z",
    "valid_until": "2026-08-20T12:00:00Z",
    "issued_at": "2026-08-19T09:00:00Z",
}

SAMPLE_HEADS_UP = {
    "id": "SWW-002",
    "event_class": "destructive_wind",
    "severity": "heads_up",
    "severity_label": "Heads-up",
    "headline": "Very windy day ahead near Umtata",
    "message": "It may get very windy around Umtata tomorrow.",
    "onset": "2026-08-19T18:00:00Z",
    "valid_until": "2026-08-21T00:00:00Z",
    "issued_at": "2026-08-19T09:00:00Z",
}

SAMPLE_ADVISORY = {
    "id": "SWW-003",
    "event_class": "cold_front",
    "severity": "advisory",
    "severity_label": "Worth knowing",
    "headline": "A cool change near Umtata",
    "message": "A cool change is moving through Umtata.",
    "onset": None,
    "valid_until": "2026-08-20T00:00:00Z",
    "issued_at": "2026-08-19T09:00:00Z",
}


class FakeConf:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


class FakeFrappe:
    """Just what weather_notice.py touches: conf + get_attr."""

    def __init__(self, conf=None, sources=None):
        self.conf = FakeConf(conf)
        self.sources = sources or {}
        self.get_attr_calls = []

    def get_attr(self, path):
        self.get_attr_calls.append(path)
        if path in self.sources:
            return self.sources[path]
        raise ImportError(f"module not composed: {path}")


TENANT_PATH = (
    "paas.weather.tenant.api.get_weather_warnings.fetch_cell_warnings")
CONTROL_PATH = (
    "paas.weather.control.api.get_weather_warnings.get_weather_warnings")


def _source(entries, calls=None):
    def fetch(grid_lat, grid_lng):
        if calls is not None:
            calls.append((grid_lat, grid_lng))
        return {
            "warnings": entries,
            "attribution": "Weather data by Open-Meteo.com",
            "generated_at": "2026-08-19T13:00:00Z",
        }
    return fetch


class WeatherNoticeCase(unittest.TestCase):
    def _install(self, conf=None, sources=None):
        fake = FakeFrappe(conf=conf, sources=sources)
        weather_notice.frappe = fake
        return fake

    def tearDown(self):
        weather_notice.frappe = sys.modules["frappe"]


class TestActiveCellWarnings(WeatherNoticeCase):
    def test_absent_weather_module_yields_empty(self):
        self._install()
        self.assertEqual(
            weather_notice.active_cell_warnings(-31.6, 28.78), [])

    def test_filters_to_headsup_and_warning_and_adds_attribution(self):
        self._install(sources={TENANT_PATH: _source(
            [SAMPLE_WARNING, SAMPLE_HEADS_UP, SAMPLE_ADVISORY])})
        rows = weather_notice.active_cell_warnings(-31.6, 28.78)
        self.assertEqual([r["id"] for r in rows], ["SWW-001", "SWW-002"])
        self.assertEqual(
            rows[0]["attribution"], "Weather data by Open-Meteo.com")

    def test_grid_rounding_reaches_the_source(self):
        calls = []
        self._install(sources={TENANT_PATH: _source([], calls=calls)})
        weather_notice.active_cell_warnings(-31.61, 28.79)
        self.assertEqual(calls, [(-31.5, 28.75)])

    def test_control_path_is_the_fallback(self):
        self._install(sources={CONTROL_PATH: _source([SAMPLE_WARNING])})
        rows = weather_notice.active_cell_warnings(-31.6, 28.78)
        self.assertEqual([r["id"] for r in rows], ["SWW-001"])

    def test_invalid_coordinates_yield_empty(self):
        self._install(sources={TENANT_PATH: _source([SAMPLE_WARNING])})
        self.assertEqual(
            weather_notice.active_cell_warnings(None, 28.78), [])
        self.assertEqual(
            weather_notice.active_cell_warnings(999, 28.78), [])
        self.assertEqual(
            weather_notice.active_cell_warnings("x", "y"), [])

    def test_malformed_response_yields_empty(self):
        self._install(
            sources={TENANT_PATH: lambda lat, lng: {"warnings": "nope"}})
        self.assertEqual(
            weather_notice.active_cell_warnings(-31.6, 28.78), [])

    def test_raising_source_yields_empty(self):
        def boom(lat, lng):
            raise RuntimeError("control plane unreachable")
        self._install(sources={TENANT_PATH: boom})
        self.assertEqual(
            weather_notice.active_cell_warnings(-31.6, 28.78), [])


class TestStopWeatherNotice(WeatherNoticeCase):
    def test_absent_weather_module_yields_none(self):
        self._install()
        self.assertIsNone(weather_notice.stop_weather_notice(-31.6, 28.78))

    def test_master_switch_off_yields_none(self):
        self._install(conf={"severe_weather_order_notices": 0},
                      sources={TENANT_PATH: _source([SAMPLE_WARNING])})
        self.assertIsNone(weather_notice.stop_weather_notice(-31.6, 28.78))

    def test_master_switch_default_is_on(self):
        self._install(sources={TENANT_PATH: _source([SAMPLE_WARNING])})
        self.assertIsNotNone(
            weather_notice.stop_weather_notice(-31.6, 28.78))

    def test_shape_and_highest_severity_wins(self):
        self._install(sources={TENANT_PATH: _source(
            [SAMPLE_HEADS_UP, SAMPLE_WARNING])})
        notice = weather_notice.stop_weather_notice(-31.6, 28.78)
        self.assertEqual(notice["severity"], "warning")
        self.assertEqual(notice["severity_label"], "Please take care")
        self.assertEqual(
            notice["text"], "Flash flooding likely near Umtata")
        self.assertIn("coming hours", notice["detail"])
        self.assertEqual(notice["valid_until"], "2026-08-20T12:00:00Z")
        self.assertEqual(notice["onset"], "2026-08-19T12:00:00Z")
        self.assertEqual(notice["event_class"], "flash_flood")
        self.assertEqual(
            notice["attribution"], "Weather data by Open-Meteo.com")

    def test_severity_tie_keeps_first_entry(self):
        other = dict(SAMPLE_WARNING, id="SWW-009",
                     headline="Flooding expected near Umtata")
        self._install(sources={TENANT_PATH: _source(
            [SAMPLE_WARNING, other])})
        notice = weather_notice.stop_weather_notice(-31.6, 28.78)
        self.assertEqual(
            notice["text"], "Flash flooding likely near Umtata")

    def test_quiet_weather_yields_none(self):
        self._install(sources={TENANT_PATH: _source([])})
        self.assertIsNone(weather_notice.stop_weather_notice(-31.6, 28.78))

    def test_copy_compliance_no_warning_word_in_user_facing_fields(self):
        # LEGAL CONSTRAINT (weather messages.py): user-facing text never
        # contains the word "warning" - the enum severity is machine-only.
        self._install(sources={TENANT_PATH: _source(
            [SAMPLE_WARNING, SAMPLE_HEADS_UP])})
        notice = weather_notice.stop_weather_notice(-31.6, 28.78)
        for field in ("text", "detail", "severity_label"):
            self.assertNotIn("warning", (notice[field] or "").lower())


class TestSerializeDeliverymanOrderAnnotation(unittest.TestCase):
    def setUp(self):
        self._orig = delivery_man.stop_weather_notice
        self._orig_frappe = delivery_man.frappe
        fake = types.SimpleNamespace()
        fake.db = types.SimpleNamespace(
            get_value=lambda *a, **k: None)
        fake.get_all = lambda *a, **k: []
        delivery_man.frappe = fake

    def tearDown(self):
        delivery_man.stop_weather_notice = self._orig
        delivery_man.frappe = self._orig_frappe

    ORDER = {
        "name": "ORD-1",
        "status": "Accepted",
        "location": '{"latitude": -31.6, "longitude": 28.78}',
    }

    def test_notice_present_annotates_row(self):
        seen = []
        delivery_man.stop_weather_notice = (
            lambda lat, lng: seen.append((lat, lng)) or {
                "text": "Flash flooding likely near Umtata",
                "severity_label": "Please take care",
            })
        row = delivery_man.serialize_deliveryman_order(dict(self.ORDER))
        self.assertEqual(
            row["weather_notice"]["severity_label"], "Please take care")
        self.assertEqual(seen, [(-31.6, 28.78)])

    def test_quiet_weather_leaves_field_absent(self):
        delivery_man.stop_weather_notice = lambda lat, lng: None
        row = delivery_man.serialize_deliveryman_order(dict(self.ORDER))
        self.assertNotIn("weather_notice", row)

    def test_absent_weather_module_leaves_field_absent(self):
        # The standalone harnesses load this file without a package: the
        # guarded relative import leaves stop_weather_notice as None.
        delivery_man.stop_weather_notice = None
        row = delivery_man.serialize_deliveryman_order(dict(self.ORDER))
        self.assertNotIn("weather_notice", row)

    def test_no_coordinates_never_calls_the_notice_read(self):
        calls = []
        delivery_man.stop_weather_notice = (
            lambda lat, lng: calls.append(1) or None)
        row = delivery_man.serialize_deliveryman_order(
            {"name": "ORD-2", "status": "New", "location": "not-json"})
        self.assertNotIn("weather_notice", row)
        self.assertEqual(calls, [])

    def test_raising_notice_read_is_swallowed(self):
        def boom(lat, lng):
            raise RuntimeError("boom")
        delivery_man.stop_weather_notice = boom
        row = delivery_man.serialize_deliveryman_order(dict(self.ORDER))
        self.assertNotIn("weather_notice", row)
        self.assertEqual(row["name"], "ORD-1")


class TestSerializeDispatchStopAnnotation(unittest.TestCase):
    def setUp(self):
        self._orig = dispatch_route.stop_weather_notice

    def tearDown(self):
        dispatch_route.stop_weather_notice = self._orig

    ROUTE = types.SimpleNamespace(name="DR-1", mode="Delivery")
    STOP = {
        "name": "STOP-1", "shop": None, "label": "Depot",
        "latitude": -31.6, "longitude": 28.78, "quantity": None,
        "unit": None, "note": None, "status": "Pending",
        "completed_at": None,
    }

    def test_notice_present_annotates_stop(self):
        dispatch_route.stop_weather_notice = lambda lat, lng: {
            "text": "Damaging winds expected near Umtata",
            "severity_label": "Please take care",
        }
        data = dispatch_route.serialize_dispatch_stop(
            self.ROUTE, dict(self.STOP))
        self.assertEqual(
            data["weather_notice"]["text"],
            "Damaging winds expected near Umtata")

    def test_quiet_weather_leaves_field_absent(self):
        dispatch_route.stop_weather_notice = lambda lat, lng: None
        data = dispatch_route.serialize_dispatch_stop(
            self.ROUTE, dict(self.STOP))
        self.assertNotIn("weather_notice", data)

    def test_absent_weather_module_leaves_field_absent(self):
        dispatch_route.stop_weather_notice = None
        data = dispatch_route.serialize_dispatch_stop(
            self.ROUTE, dict(self.STOP))
        self.assertNotIn("weather_notice", data)

    def test_coordinate_less_stop_never_calls_the_notice_read(self):
        calls = []
        dispatch_route.stop_weather_notice = (
            lambda lat, lng: calls.append(1) or None)
        stop = dict(self.STOP, latitude=None, longitude=None)
        data = dispatch_route.serialize_dispatch_stop(self.ROUTE, stop)
        self.assertNotIn("weather_notice", data)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
