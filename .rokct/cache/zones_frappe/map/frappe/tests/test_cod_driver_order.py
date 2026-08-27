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

"""Unit tests for the driver-order COD helpers.

Pure unit tests following delivery/frappe/tests/test_intercity_providers.py:
a minimal frappe (and paas) stub is installed when no bench is available,
so they run with `python3 -m unittest` both inside and outside a Frappe
bench. They cover the legacy-status normalization mapping and the
collected-amount validation.
"""

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


def _ensure_stubs():
    """Install minimal frappe/paas stubs when no bench is available.

    Kept attribute-compatible with test_intercity_providers.py's stub (a
    superset), so either test module can run first in the same discovery
    process without poisoning the other.
    """
    try:
        import frappe
        # A stub installed by a sibling test module may lack the attributes
        # this module's code needs at import time; top up defensively (a
        # real bench frappe already has all of these).
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

        def cint(value):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return 0

        utils_mod.cint = cint
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
        frappe_mod.PermissionError = type("PermissionError", (Exception,), {})
        frappe_mod.AuthenticationError = type(
            "AuthenticationError", (Exception,), {}
        )
        sys.modules["frappe"] = frappe_mod
        sys.modules["frappe.utils"] = utils_mod

    try:
        from paas.delivery.tenant.api.delivery_man import delivery_man  # noqa: F401
    except ImportError:
        paas_mod = types.ModuleType("paas")
        delivery_mod = types.ModuleType("paas.delivery")
        tenant_mod = types.ModuleType("paas.delivery.tenant")
        api_mod = types.ModuleType("paas.delivery.tenant.api")
        delivery_man_pkg = types.ModuleType("paas.delivery.tenant.api.delivery_man")
        delivery_man_mod = types.ModuleType(
            "paas.delivery.tenant.api.delivery_man.delivery_man"
        )
        delivery_man_mod.get_deliveryman_orders = MagicMock()
        delivery_man_mod.get_deliveryman_parcel_orders = MagicMock()
        sys.modules["paas"] = paas_mod
        sys.modules["paas.delivery"] = delivery_mod
        sys.modules["paas.delivery.tenant"] = tenant_mod
        sys.modules["paas.delivery.tenant.api"] = api_mod
        sys.modules["paas.delivery.tenant.api.delivery_man"] = delivery_man_pkg
        sys.modules["paas.delivery.tenant.api.delivery_man.delivery_man"] = (
            delivery_man_mod
        )


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


def _load_driver_order():
    _ensure_stubs()
    if "cod_test_driver_order" in sys.modules:
        return sys.modules["cod_test_driver_order"]
    return _exec_composed("cod_test_driver_order", DRIVER_ORDER_PATH)


driver_order = _load_driver_order()


class TestOrderStatusNormalization(unittest.TestCase):
    """Legacy lowercase driver statuses map onto real Select options."""

    def test_legacy_statuses_map_to_order_select_options(self):
        self.assertEqual(
            driver_order.normalize_order_status("delivered"), "Delivered"
        )
        self.assertEqual(
            driver_order.normalize_order_status("canceled"), "Cancelled"
        )
        self.assertEqual(
            driver_order.normalize_order_status("cancelled"), "Cancelled"
        )
        # Order has no "On a Way" option; Shipped is the in-transit state.
        self.assertEqual(
            driver_order.normalize_order_status("on_a_way"), "Shipped"
        )
        self.assertEqual(
            driver_order.normalize_order_status("accepted"), "Accepted"
        )
        self.assertEqual(driver_order.normalize_order_status("new"), "New")

    def test_normalization_is_case_and_whitespace_insensitive(self):
        self.assertEqual(
            driver_order.normalize_order_status(" DELIVERED "), "Delivered"
        )
        self.assertEqual(
            driver_order.normalize_order_status("On_A_Way".lower()), "Shipped"
        )
        self.assertEqual(
            driver_order.normalize_order_status("Shipped"), "Shipped"
        )

    def test_unknown_statuses_return_none(self):
        self.assertIsNone(driver_order.normalize_order_status("bogus"))
        self.assertIsNone(driver_order.normalize_order_status(""))
        self.assertIsNone(driver_order.normalize_order_status(None))

    def test_all_mapped_values_are_real_select_options(self):
        select_options = {
            "New", "Accepted", "Shipped", "Delivered", "Cancelled",
            "Paid", "Failed",
        }
        self.assertTrue(
            set(driver_order.ORDER_STATUS_MAP.values()) <= select_options
        )


class TestParseCodAmount(unittest.TestCase):
    """amount_received must parse to a non-negative finite float."""

    def test_accepts_numbers_and_numeric_strings(self):
        self.assertEqual(driver_order.parse_cod_amount(150), 150.0)
        self.assertEqual(driver_order.parse_cod_amount("99.90"), 99.9)
        self.assertEqual(driver_order.parse_cod_amount(0), 0.0)
        self.assertEqual(driver_order.parse_cod_amount("0"), 0.0)

    def test_rejects_negative_amounts(self):
        with self.assertRaises(ValueError):
            driver_order.parse_cod_amount(-1)
        with self.assertRaises(ValueError):
            driver_order.parse_cod_amount("-0.01")

    def test_rejects_non_numeric_input(self):
        with self.assertRaises(ValueError):
            driver_order.parse_cod_amount("abc")
        with self.assertRaises(ValueError):
            driver_order.parse_cod_amount(None)
        with self.assertRaises(ValueError):
            driver_order.parse_cod_amount("")

    def test_rejects_nan_and_infinity(self):
        with self.assertRaises(ValueError):
            driver_order.parse_cod_amount("nan")
        with self.assertRaises(ValueError):
            driver_order.parse_cod_amount("inf")
        with self.assertRaises(ValueError):
            driver_order.parse_cod_amount(float("-inf"))

    def test_full_collection_epsilon_comparison(self):
        # 3 * 33.33 style float noise must still count as full collection.
        amount = 0.1 + 0.2
        expected = 0.3
        self.assertGreaterEqual(
            amount + driver_order.COD_AMOUNT_EPSILON, expected
        )


class _Thrown(Exception):
    """Raised by the patched frappe.throw so tests can catch it."""


class _FakeOrder:
    """Minimal Order document stand-in for convert_cod_to_credit."""

    def __init__(self, shop="SHOP-0001", order_items=None):
        self.name = "ORD-0001"
        self.deliveryman = "driver@example.com"
        self.payment_status = "Unpaid"
        self.shop = shop
        # Order.order_items -> Order Item child rows; each row links a
        # Product via its "product" field.
        self.order_items = (
            [{"product": "PROD-0001"}] if order_items is None else order_items
        )
        self.saved = False

    def get(self, key, default=None):
        return getattr(self, key, default)

    def save(self, **kwargs):
        self.saved = True


class TestConvertCodToCreditShopGate(unittest.TestCase):
    """convert_cod_to_credit requires BOTH the driver capability and the
    order's shop having Shop.enable_credit checked (missing shop or unset
    field means the shop does not offer credit). Shops that do offer
    credit choose a Shop.credit_mode: "All Orders" (also the unset /
    unknown-value fallback) needs no per-product check, while
    "Selected Products" requires at least one order item whose Product
    has allow_credit checked."""

    DRIVER = "driver@example.com"

    def setUp(self):
        import frappe
        self.frappe = frappe
        self._saved = {
            attr: getattr(frappe, attr, None)
            for attr in ("session", "db", "get_doc", "get_all", "throw")
        }

        frappe.session = types.SimpleNamespace(user=self.DRIVER)
        frappe.get_all = MagicMock(return_value=[])  # no Transactions: a
        # transactionless Unpaid order still counts as cash-eligible.

        self.throw_messages = []

        def _throw(msg, *args, **kwargs):
            self.throw_messages.append(str(msg))
            raise _Thrown(str(msg))

        frappe.throw = _throw

    def tearDown(self):
        for attr, value in self._saved.items():
            setattr(self.frappe, attr, value)

    def _install_db(self, order, can_convert=1, shop_enable_credit=1,
                    shop_credit_mode="All Orders",
                    credit_products=frozenset()):
        """Wire frappe.db/get_doc for one convert_cod_to_credit call.

        credit_products is the set of Product names that have
        allow_credit checked (consulted only via the Product query the
        "Selected Products" mode issues).
        """
        frappe = self.frappe
        frappe.get_doc = MagicMock(return_value=order)
        db = MagicMock()
        db.exists = MagicMock(return_value=True)
        self.shop_lookups = []
        self.product_queries = []

        def _get_value(doctype, name_or_filters, fieldname, *a, **k):
            if doctype == "Deliveryman Profile":
                self.assertEqual(fieldname, "can_convert_cod_to_credit")
                return can_convert
            if doctype == "Shop":
                self.shop_lookups.append((name_or_filters, tuple(fieldname)))
                # Both shop fields are fetched in a single get_value call.
                self.assertEqual(
                    list(fieldname), ["enable_credit", "credit_mode"]
                )
                return (shop_enable_credit, shop_credit_mode)
            return None

        db.get_value = MagicMock(side_effect=_get_value)
        frappe.db = db

        def _get_all(doctype, *a, **k):
            if doctype == "Product":
                filters = k.get("filters") or {}
                self.product_queries.append(filters)
                self.assertEqual(filters.get("allow_credit"), 1)
                names = (filters.get("name") or [None, []])[1]
                return [
                    {"name": n} for n in names if n in credit_products
                ][:1]
            # Transaction lookups: a transactionless Unpaid order still
            # counts as cash-eligible.
            return []

        frappe.get_all = MagicMock(side_effect=_get_all)

    def test_shop_offering_credit_allows_conversion(self):
        order = _FakeOrder(shop="SHOP-0001")
        self._install_db(order, can_convert=1, shop_enable_credit=1)
        result = driver_order.convert_cod_to_credit("ORD-0001")
        self.assertEqual(result["payment_status"], "Credit")
        self.assertEqual(order.payment_status, "Credit")
        self.assertTrue(order.saved)
        # The shop opt-in was actually consulted, on the right doctype,
        # fetching both credit fields in one call.
        self.assertEqual(
            self.shop_lookups,
            [("SHOP-0001", ("enable_credit", "credit_mode"))],
        )

    def test_shop_not_offering_credit_throws_clear_error(self):
        order = _FakeOrder(shop="SHOP-0001")
        self._install_db(order, can_convert=1, shop_enable_credit=0)
        with self.assertRaises(_Thrown):
            driver_order.convert_cod_to_credit("ORD-0001")
        self.assertIn(
            "This shop does not offer credit.", self.throw_messages
        )
        self.assertEqual(order.payment_status, "Unpaid")
        self.assertFalse(order.saved)

    def test_unset_enable_credit_field_treated_as_not_offering(self):
        # A Shop created before the field existed reads back None.
        order = _FakeOrder(shop="SHOP-0001")
        self._install_db(order, can_convert=1, shop_enable_credit=None)
        with self.assertRaises(_Thrown):
            driver_order.convert_cod_to_credit("ORD-0001")
        self.assertIn(
            "This shop does not offer credit.", self.throw_messages
        )
        self.assertFalse(order.saved)

    def test_order_without_shop_treated_as_not_offering(self):
        order = _FakeOrder(shop=None)
        self._install_db(order, can_convert=1, shop_enable_credit=1)
        with self.assertRaises(_Thrown):
            driver_order.convert_cod_to_credit("ORD-0001")
        self.assertIn(
            "This shop does not offer credit.", self.throw_messages
        )
        # No shop link: the Shop table must not even be queried.
        self.assertEqual(self.shop_lookups, [])
        self.assertFalse(order.saved)

    def test_driver_capability_checked_before_shop_opt_in(self):
        order = _FakeOrder(shop="SHOP-0001")
        self._install_db(order, can_convert=0, shop_enable_credit=1)
        with self.assertRaises(_Thrown):
            driver_order.convert_cod_to_credit("ORD-0001")
        # The driver-capability error fired and the shop was never consulted.
        self.assertTrue(
            any("not allowed" in m for m in self.throw_messages)
        )
        self.assertEqual(self.shop_lookups, [])

    # ---- Shop.credit_mode: "All Orders" vs "Selected Products" ----

    def test_mode_all_orders_passes_without_product_check(self):
        order = _FakeOrder(shop="SHOP-0001")
        self._install_db(
            order, shop_credit_mode="All Orders", credit_products=frozenset()
        )
        result = driver_order.convert_cod_to_credit("ORD-0001")
        self.assertEqual(result["payment_status"], "Credit")
        self.assertTrue(order.saved)
        # All Orders mode must not consult Product.allow_credit at all.
        self.assertEqual(self.product_queries, [])

    def test_mode_unset_treated_as_all_orders(self):
        # A Shop saved before credit_mode existed reads back None.
        order = _FakeOrder(shop="SHOP-0001")
        self._install_db(
            order, shop_credit_mode=None, credit_products=frozenset()
        )
        result = driver_order.convert_cod_to_credit("ORD-0001")
        self.assertEqual(result["payment_status"], "Credit")
        self.assertTrue(order.saved)
        self.assertEqual(self.product_queries, [])

    def test_selected_products_with_one_qualifying_item_passes(self):
        # One allow_credit product among several makes the WHOLE order
        # eligible.
        order = _FakeOrder(
            shop="SHOP-0001",
            order_items=[
                {"product": "PROD-CASH"},
                {"product": "PROD-CREDIT"},
            ],
        )
        self._install_db(
            order,
            shop_credit_mode="Selected Products",
            credit_products=frozenset({"PROD-CREDIT"}),
        )
        result = driver_order.convert_cod_to_credit("ORD-0001")
        self.assertEqual(result["payment_status"], "Credit")
        self.assertTrue(order.saved)
        # The Product table was actually consulted, over the order's items.
        self.assertEqual(len(self.product_queries), 1)
        self.assertEqual(
            sorted((self.product_queries[0].get("name") or [None, []])[1]),
            ["PROD-CASH", "PROD-CREDIT"],
        )

    def test_selected_products_with_no_qualifying_item_throws(self):
        order = _FakeOrder(
            shop="SHOP-0001",
            order_items=[
                {"product": "PROD-CASH"},
                {"product": "PROD-ALSO-CASH"},
            ],
        )
        self._install_db(
            order,
            shop_credit_mode="Selected Products",
            credit_products=frozenset(),
        )
        with self.assertRaises(_Thrown):
            driver_order.convert_cod_to_credit("ORD-0001")
        self.assertIn(
            "No product in this order is allowed on credit.",
            self.throw_messages,
        )
        self.assertEqual(order.payment_status, "Unpaid")
        self.assertFalse(order.saved)

    def test_selected_products_with_no_items_throws(self):
        order = _FakeOrder(shop="SHOP-0001", order_items=[])
        self._install_db(
            order,
            shop_credit_mode="Selected Products",
            credit_products=frozenset({"PROD-CREDIT"}),
        )
        with self.assertRaises(_Thrown):
            driver_order.convert_cod_to_credit("ORD-0001")
        self.assertIn(
            "No product in this order is allowed on credit.",
            self.throw_messages,
        )
        # Nothing to look up: the Product table is never queried.
        self.assertEqual(self.product_queries, [])
        self.assertFalse(order.saved)

    def test_unknown_credit_mode_treated_as_all_orders(self):
        order = _FakeOrder(shop="SHOP-0001")
        self._install_db(
            order,
            shop_credit_mode="Something Else",
            credit_products=frozenset(),
        )
        result = driver_order.convert_cod_to_credit("ORD-0001")
        self.assertEqual(result["payment_status"], "Credit")
        self.assertEqual(self.product_queries, [])


class _FakeAdultOrder:
    """Minimal Order stand-in for the 18+ age-verification gate. Models
    a doctype that HAS the contains_adult_items / age_verified* fields."""

    def __init__(self, contains_adult_items=1, age_verified=0):
        self.name = "ORD-18"
        self.deliveryman = "driver@example.com"
        self.status = "Shipped"
        self.contains_adult_items = contains_adult_items
        self.age_verified = age_verified
        self.age_verified_at = None
        self.age_verified_by = None
        self.saved = False

    def get(self, key, default=None):
        return getattr(self, key, default)

    def save(self, **kwargs):
        self.saved = True

    def as_dict(self):
        return {"name": self.name, "status": self.status}


class _FakeLegacyOrder:
    """Order stand-in for a doctype that PREDATES the 18+ fields (the
    delivery_photo hasattr precedent): .get() finds nothing, hasattr is
    False, and the gate must skip entirely."""

    def __init__(self):
        self.name = "ORD-OLD"
        self.deliveryman = "driver@example.com"
        self.status = "Shipped"
        self.saved = False

    def get(self, key, default=None):
        return getattr(self, key, default)

    def save(self, **kwargs):
        self.saved = True

    def as_dict(self):
        return {"name": self.name, "status": self.status}


class TestParseBoolFlag(unittest.TestCase):
    def test_string_encodings(self):
        self.assertTrue(driver_order.parse_bool_flag("true"))
        self.assertTrue(driver_order.parse_bool_flag("1"))
        self.assertTrue(driver_order.parse_bool_flag(" TRUE "))
        self.assertFalse(driver_order.parse_bool_flag("false"))
        self.assertFalse(driver_order.parse_bool_flag("0"))
        self.assertFalse(driver_order.parse_bool_flag(""))
        self.assertFalse(driver_order.parse_bool_flag("bogus"))

    def test_native_types(self):
        self.assertTrue(driver_order.parse_bool_flag(True))
        self.assertTrue(driver_order.parse_bool_flag(1))
        self.assertFalse(driver_order.parse_bool_flag(False))
        self.assertFalse(driver_order.parse_bool_flag(0))
        self.assertFalse(driver_order.parse_bool_flag(None))


class TestAgeVerificationGate(unittest.TestCase):
    """update_driver_order_status: orders flagged contains_adult_items
    cannot move to Delivered without recipient_age_verified; confirming
    records age_verified / age_verified_at / age_verified_by. Non-adult
    and pre-18+-schema orders are entirely unaffected."""

    DRIVER = "driver@example.com"

    def setUp(self):
        import frappe
        self.frappe = frappe
        self._saved = {
            attr: getattr(frappe, attr, None)
            for attr in ("session", "db", "get_doc", "throw", "utils")
        }
        frappe.session = types.SimpleNamespace(user=self.DRIVER)
        frappe.utils = types.SimpleNamespace(
            now_datetime=lambda: "2026-08-24 12:00:00"
        )

        self.throw_messages = []

        def _throw(msg, *args, **kwargs):
            self.throw_messages.append(str(msg))
            raise _Thrown(str(msg))

        frappe.throw = _throw

    def tearDown(self):
        for attr, value in self._saved.items():
            setattr(self.frappe, attr, value)

    def _install(self, order):
        frappe = self.frappe
        db = MagicMock()
        db.exists = MagicMock(return_value=True)
        frappe.db = db
        frappe.get_doc = MagicMock(return_value=order)

    def test_flagged_order_without_confirmation_throws(self):
        order = _FakeAdultOrder()
        self._install(order)
        with self.assertRaises(_Thrown):
            driver_order.update_driver_order_status("ORD-18", "delivered")
        self.assertTrue(
            any("AGE_VERIFICATION_REQUIRED" in m
                for m in self.throw_messages)
        )
        self.assertFalse(order.saved)
        self.assertEqual(order.status, "Shipped")

    def test_flagged_order_with_falsy_confirmation_throws(self):
        order = _FakeAdultOrder()
        self._install(order)
        with self.assertRaises(_Thrown):
            driver_order.update_driver_order_status(
                "ORD-18", "delivered", recipient_age_verified="false"
            )
        self.assertFalse(order.saved)

    def test_flagged_order_with_confirmation_delivers_and_records(self):
        order = _FakeAdultOrder()
        self._install(order)
        result = driver_order.update_driver_order_status(
            "ORD-18", "delivered", recipient_age_verified=True
        )
        self.assertTrue(result["status"])
        self.assertTrue(order.saved)
        self.assertEqual(order.status, "Delivered")
        self.assertEqual(order.age_verified, 1)
        self.assertEqual(order.age_verified_at, "2026-08-24 12:00:00")
        self.assertEqual(order.age_verified_by, self.DRIVER)

    def test_string_true_counts_as_confirmation(self):
        # Form-encoded gateway calls deliver booleans as strings.
        order = _FakeAdultOrder()
        self._install(order)
        result = driver_order.update_driver_order_status(
            "ORD-18", "delivered", recipient_age_verified="true"
        )
        self.assertTrue(result["status"])
        self.assertEqual(order.age_verified, 1)

    def test_already_verified_order_redelivers_without_confirmation(self):
        # Idempotency (confirm_cod_collection precedent): a retried
        # Delivered call on an already-verified order passes.
        order = _FakeAdultOrder(age_verified=1)
        self._install(order)
        result = driver_order.update_driver_order_status(
            "ORD-18", "delivered"
        )
        self.assertTrue(result["status"])
        self.assertEqual(order.status, "Delivered")

    def test_non_adult_order_is_unaffected(self):
        order = _FakeAdultOrder(contains_adult_items=0)
        self._install(order)
        result = driver_order.update_driver_order_status(
            "ORD-18", "delivered"
        )
        self.assertTrue(result["status"])
        self.assertEqual(order.status, "Delivered")
        # Nothing recorded on an unflagged order.
        self.assertEqual(order.age_verified, 0)

    def test_legacy_order_schema_is_unaffected(self):
        # delivery_photo precedent: a doctype predating the 18+ fields
        # never gates and never grows attributes.
        order = _FakeLegacyOrder()
        self._install(order)
        result = driver_order.update_driver_order_status(
            "ORD-OLD", "delivered"
        )
        self.assertTrue(result["status"])
        self.assertEqual(order.status, "Delivered")
        self.assertFalse(hasattr(order, "age_verified"))

    def test_non_delivered_statuses_never_gate(self):
        order = _FakeAdultOrder()
        self._install(order)
        result = driver_order.update_driver_order_status(
            "ORD-18", "on_a_way"
        )
        self.assertTrue(result["status"])
        self.assertEqual(order.status, "Shipped")
        self.assertEqual(self.throw_messages, [])


if __name__ == "__main__":
    unittest.main()
