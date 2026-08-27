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

"""Unit tests for the hourly customer/shop weather order-notice job
(src/weather_notice/order_notices.py): expected-delivery-window derivation
from the Order doctype's real ETA fields (delivery_date + delivery_time,
orders module), overlap logic, warning-tier-only fan-out to both
audiences, the Weather Order Notice send-once ledger, guarded-absence
no-ops (comms/weather/orders missing), the master off-switch, and copy
compliance (never the word "warning" in anything a user sees).

Same packaged-loading stub harness as test_weather_stop_notice.py.
"""

import datetime as dt
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
ORDER_NOTICES_PATH = os.path.join(
    SRC_DIR, "weather_notice", "order_notices.py")
DELIVERY_MAN_PATH = os.path.join(
    SRC_DIR, "api", "delivery_man", "delivery_man.py")
ROUTE_UTILS_PATH = os.path.join(SRC_DIR, "api", "route", "route_utils.py")


def _ensure_stubs():
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
        mod.__path__ = []
        sys.modules[name] = mod
    return sys.modules[name]


def _load_packaged(dotted_name, path):
    # Reuse only a real prior load of the same file; replace placeholder
    # registrations (no __file__) from other harnesses - see the sibling
    # test_weather_stop_notice.py for the rationale.
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
                "paas.delivery.tenant.api.delivery_man"):
        _ensure_pkg(pkg)
    if "paas.delivery.tenant.api.route.route_utils" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "paas.delivery.tenant.api.route.route_utils", ROUTE_UTILS_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules["paas.delivery.tenant.api.route.route_utils"] = module
        spec.loader.exec_module(module)
    wn = _load_packaged(
        "paas.delivery.tenant.weather_notice.weather_notice", WEATHER_NOTICE_PATH)
    _load_packaged(
        "paas.delivery.tenant.api.delivery_man.delivery_man", DELIVERY_MAN_PATH)
    on = _load_packaged(
        "paas.delivery.tenant.weather_notice.order_notices", ORDER_NOTICES_PATH)
    return wn, on


weather_notice, order_notices = _load_modules()

NOW = dt.datetime(2026, 8, 19, 13, 0, 0)

TENANT_PATH = (
    "paas.weather.tenant.api.get_weather_warnings.fetch_cell_warnings")
COMMS_PATH = "paas.comms.tenant.api.notification.send_push_notification"

#: grid cell (-31.5, 28.75) - Umtata-ish drop-off; shop sits in the same
#: cell unless a test moves it.
DROPOFF_JSON = '{"latitude": -31.6, "longitude": 28.78}'
SHOP_JSON = '{"latitude": -31.55, "longitude": 28.7}'
FAR_SHOP_JSON = '{"latitude": -26.2, "longitude": 28.04}'  # another cell

WARNING_ENTRY = {
    "id": "SWW-100",
    "event_class": "flash_flood",
    "severity": "warning",
    "severity_label": "Please take care",
    "headline": "Flash flooding likely near Umtata",
    "message": "Flash flooding looks likely around Umtata.",
    "onset": "2026-08-19T12:00:00Z",
    "valid_until": "2026-08-20T12:00:00Z",
    "issued_at": "2026-08-19T09:00:00Z",
}

HEADS_UP_ENTRY = dict(
    WARNING_ENTRY, id="SWW-101", severity="heads_up",
    severity_label="Heads-up",
    headline="Very windy day ahead near Umtata")


class FakeConf:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


class FakeDB:
    def __init__(self, fake):
        self.fake = fake

    def get_value(self, doctype, filters, fieldname=None, as_dict=False):
        if doctype == "Shop":
            return self.fake.shops.get(filters)
        if doctype == "Weather Order Notice":
            key = (filters.get("order"), filters.get("notice"),
                   filters.get("audience"))
            for row in self.fake.ledger:
                if (row["order"], row["notice"], row["audience"]) == key:
                    return row.get("name", "WON-x")
            return None
        return None


class FakeLedgerDoc:
    def __init__(self, fake, payload):
        self.fake = fake
        self.payload = dict(payload)

    def insert(self, ignore_permissions=False):
        row = {k: v for k, v in self.payload.items() if k != "doctype"}
        row["name"] = f"WON-{len(self.fake.ledger) + 1}"
        self.fake.ledger.append(row)
        return self


class FakeFrappe:
    def __init__(self, conf=None, warnings_by_cell=None, with_comms=True,
                 orders=None):
        self.conf = FakeConf(conf)
        self.orders = orders if orders is not None else []
        self.orders_raise = False
        self.shops = {}
        self.ledger = []
        self.pushes = []
        self.db = FakeDB(self)
        self.warnings_by_cell = warnings_by_cell or {}
        self.with_comms = with_comms
        self.with_weather = True
        self.captured_order_filters = None

    # --- weather + comms dispatch ---------------------------------- #
    def get_attr(self, path):
        if path == TENANT_PATH and self.with_weather:
            return self._fetch_cell
        if path == COMMS_PATH and self.with_comms:
            return self._send_push
        raise ImportError(f"module not composed: {path}")

    def _fetch_cell(self, grid_lat, grid_lng):
        return {
            "warnings": self.warnings_by_cell.get(
                (grid_lat, grid_lng), []),
            "attribution": "Weather data by Open-Meteo.com",
            "generated_at": "2026-08-19T13:00:00Z",
        }

    def _send_push(self, user=None, title=None, body=None, data=None):
        self.pushes.append(
            {"user": user, "title": title, "body": body, "data": data})
        return {"status": "success"}

    # --- orm ------------------------------------------------------- #
    def get_all(self, doctype, filters=None, fields=None, **kwargs):
        if doctype == "Order":
            if self.orders_raise:
                raise Exception("DocType Order not found")
            self.captured_order_filters = filters
            return [dict(o) for o in self.orders]
        return []

    def get_doc(self, payload):
        return FakeLedgerDoc(self, payload)

    def log_error(self, *a, **k):
        pass

    def get_traceback(self):
        return "traceback"


CELL = (-31.5, 28.75)
FAR_CELL = (-26.25, 28.0)


def _order(**overrides):
    base = {
        "name": "ORD-1",
        "user": "customer@example.com",
        "shop": "Water Depot",
        "status": "Accepted",
        "location": DROPOFF_JSON,
        "delivery_date": "2026-08-19",
        "delivery_time": "15:00:00",
        "creation": "2026-08-19 09:00:00",
    }
    base.update(overrides)
    return base


class OrderNoticesCase(unittest.TestCase):
    def _install(self, **kwargs):
        fake = FakeFrappe(**kwargs)
        fake.shops["Water Depot"] = {
            "user": "shop-owner@example.com", "location": SHOP_JSON}
        order_notices.frappe = fake
        weather_notice.frappe = fake
        return fake

    def tearDown(self):
        order_notices.frappe = sys.modules["frappe"]
        weather_notice.frappe = sys.modules["frappe"]

    def _run(self):
        return order_notices._run(now=NOW)


class TestGuardsAndSwitches(OrderNoticesCase):
    def test_master_switch_off_is_a_no_op(self):
        fake = self._install(
            conf={"severe_weather_order_notices": 0},
            warnings_by_cell={CELL: [WARNING_ENTRY]},
            orders=[_order()])
        self.assertEqual(self._run(), "disabled")
        self.assertEqual(fake.pushes, [])

    def test_absent_comms_module_is_a_silent_no_op(self):
        fake = self._install(
            with_comms=False,
            warnings_by_cell={CELL: [WARNING_ENTRY]},
            orders=[_order()])
        self.assertEqual(self._run(), "no_sender")
        self.assertEqual(fake.ledger, [])

    def test_absent_order_doctype_is_a_silent_no_op(self):
        fake = self._install(warnings_by_cell={CELL: [WARNING_ENTRY]})
        fake.orders_raise = True
        self.assertEqual(self._run(), "no_orders")

    def test_absent_weather_module_sends_nothing(self):
        fake = self._install(orders=[_order()])
        fake.with_weather = False
        self.assertEqual(self._run(), "sent:0")
        self.assertEqual(fake.pushes, [])

    def test_scheduler_wrapper_never_raises(self):
        self._install()
        order_notices.frappe = None  # even the error logger is broken

        def boom():
            raise RuntimeError("internal problem")
        orig = order_notices.weather_notice
        order_notices.weather_notice = types.SimpleNamespace(
            notices_enabled=boom)
        try:
            self.assertEqual(
                order_notices.run_order_weather_notices(), "error")
        finally:
            order_notices.weather_notice = orig


class TestFanOutAndCopy(OrderNoticesCase):
    def test_both_audiences_notified_once_with_calm_copy(self):
        fake = self._install(
            warnings_by_cell={CELL: [WARNING_ENTRY]},
            orders=[_order()])
        self.assertEqual(self._run(), "sent:2")
        users = {p["user"] for p in fake.pushes}
        self.assertEqual(
            users, {"customer@example.com", "shop-owner@example.com"})
        customer = next(p for p in fake.pushes
                        if p["user"] == "customer@example.com")
        self.assertEqual(
            customer["body"],
            "Your delivery may be delayed - heavy rain is expected near "
            "the delivery area.")
        self.assertEqual(customer["data"]["type"], "weather_order_notice")
        self.assertEqual(customer["data"]["notice_id"], "SWW-100")
        shop = next(p for p in fake.pushes
                    if p["user"] == "shop-owner@example.com")
        self.assertIn("ORD-1", shop["body"])
        self.assertEqual(len(fake.ledger), 2)
        self.assertEqual(
            {row["audience"] for row in fake.ledger},
            {"Customer", "Shop"})

    def test_send_once_per_order_notice_audience(self):
        fake = self._install(
            warnings_by_cell={CELL: [WARNING_ENTRY]},
            orders=[_order()])
        self.assertEqual(self._run(), "sent:2")
        self.assertEqual(self._run(), "sent:0")  # hourly re-run: silence
        self.assertEqual(len(fake.pushes), 2)
        self.assertEqual(len(fake.ledger), 2)

    def test_heads_up_tier_never_notifies_customer_or_shop(self):
        fake = self._install(
            warnings_by_cell={CELL: [HEADS_UP_ENTRY]},
            orders=[_order()])
        self.assertEqual(self._run(), "sent:0")
        self.assertEqual(fake.pushes, [])

    def test_shop_cell_warning_alone_notifies_both(self):
        # Drop-off sits in a quiet cell; the shop's cell has the notice.
        fake = self._install(
            warnings_by_cell={FAR_CELL: [], CELL: [WARNING_ENTRY]},
            orders=[_order(location='{"latitude": -26.2, '
                                    '"longitude": 28.04}')])
        self.assertEqual(self._run(), "sent:2")
        self.assertEqual(len(fake.pushes), 2)

    def test_guest_or_missing_users_are_skipped(self):
        fake = self._install(
            warnings_by_cell={CELL: [WARNING_ENTRY]},
            orders=[_order(user="Guest")])
        fake.shops["Water Depot"]["user"] = None
        self.assertEqual(self._run(), "sent:0")
        self.assertEqual(fake.pushes, [])

    def test_copy_compliance_no_warning_word_for_any_class(self):
        # LEGAL CONSTRAINT (weather messages.py): nothing a user sees may
        # contain the word "warning" - including unknown event classes.
        classes = ["flash_flood", "flood", "destructive_wind",
                   "something_new"]
        entries = [
            dict(WARNING_ENTRY, id=f"SWW-{i}", event_class=cls)
            for i, cls in enumerate(classes)
        ]
        fake = self._install(
            warnings_by_cell={CELL: entries}, orders=[_order()])
        self._run()
        self.assertTrue(fake.pushes)
        for push in fake.pushes:
            self.assertNotIn("warning", push["title"].lower())
            self.assertNotIn("warning", push["body"].lower())
            self.assertIn("may be delayed", push["body"])


class TestExpectedWindowAndOverlap(OrderNoticesCase):
    def test_date_and_time_make_a_one_hour_slot(self):
        self._install()
        window = order_notices.expected_delivery_window(
            _order(), now=NOW)
        self.assertEqual(window[0], dt.datetime(2026, 8, 19, 15, 0, 0))
        self.assertEqual(window[1], dt.datetime(2026, 8, 19, 16, 0, 0))

    def test_time_as_timedelta_is_handled(self):
        # frappe loads Time fields as datetime.timedelta.
        self._install()
        window = order_notices.expected_delivery_window(
            _order(delivery_time=dt.timedelta(hours=15)), now=NOW)
        self.assertEqual(window[0], dt.datetime(2026, 8, 19, 15, 0, 0))

    def test_date_only_covers_the_whole_day(self):
        self._install()
        window = order_notices.expected_delivery_window(
            _order(delivery_time=None), now=NOW)
        self.assertEqual(window[0], dt.datetime(2026, 8, 19, 0, 0, 0))
        self.assertEqual(window[1], dt.datetime(2026, 8, 20, 0, 0, 0))

    def test_no_eta_falls_back_to_creation_plus_horizon(self):
        self._install()
        window = order_notices.expected_delivery_window(
            _order(delivery_date=None, delivery_time=None), now=NOW)
        self.assertEqual(window[0], dt.datetime(2026, 8, 19, 9, 0, 0))
        self.assertEqual(window[1], dt.datetime(2026, 8, 20, 9, 0, 0))

    def test_horizon_is_configurable(self):
        self._install(
            conf={"severe_weather_order_notices_horizon_hours": 6})
        window = order_notices.expected_delivery_window(
            _order(delivery_date=None, delivery_time=None), now=NOW)
        self.assertEqual(window[1], dt.datetime(2026, 8, 19, 15, 0, 0))

    def test_notice_expiring_before_the_slot_does_not_notify(self):
        # Delivery slot tomorrow evening; the notice ends tomorrow midday.
        fake = self._install(
            warnings_by_cell={CELL: [WARNING_ENTRY]},
            orders=[_order(delivery_date="2026-08-20",
                           delivery_time="18:00:00")])
        self.assertEqual(self._run(), "sent:0")
        self.assertEqual(fake.pushes, [])

    def test_notice_starting_after_the_slot_does_not_notify(self):
        entry = dict(WARNING_ENTRY, onset="2026-08-19T20:00:00Z")
        fake = self._install(
            warnings_by_cell={CELL: [entry]},
            orders=[_order()])  # slot 15:00-16:00
        self.assertEqual(self._run(), "sent:0")
        self.assertEqual(fake.pushes, [])

    def test_notice_with_no_onset_counts_as_under_way(self):
        entry = dict(WARNING_ENTRY, onset=None)
        fake = self._install(
            warnings_by_cell={CELL: [entry]}, orders=[_order()])
        self.assertEqual(self._run(), "sent:2")
        self.assertEqual(len(fake.pushes), 2)

    def test_window_fully_in_the_past_does_not_notify(self):
        fake = self._install(
            warnings_by_cell={CELL: [WARNING_ENTRY]},
            orders=[_order(delivery_date="2026-08-18",
                           delivery_time="09:00:00")])
        self.assertEqual(self._run(), "sent:0")
        self.assertEqual(fake.pushes, [])

    def test_only_active_statuses_are_scanned(self):
        fake = self._install(
            warnings_by_cell={CELL: [WARNING_ENTRY]},
            orders=[_order()])
        self._run()
        self.assertEqual(
            fake.captured_order_filters["status"],
            ["in", ["New", "Accepted", "Shipped"]])


if __name__ == "__main__":
    unittest.main()
