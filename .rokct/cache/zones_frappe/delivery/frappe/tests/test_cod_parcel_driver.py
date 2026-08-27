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

"""Unit tests for the driver-parcel COD helpers.

Pure unit tests in the same spirit as test_intercity_providers.py: a
minimal frappe (and paas) stub is installed when no bench is available,
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
DRIVER_PARCEL_PATH = os.path.abspath(
    os.path.join(
        TESTS_DIR, "..", "src", "tenant", "api", "driver_parcel", "driver_parcel.py"
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


def _load_driver_parcel():
    _ensure_stubs()
    if "cod_test_driver_parcel" in sys.modules:
        return sys.modules["cod_test_driver_parcel"]
    return _exec_composed("cod_test_driver_parcel", DRIVER_PARCEL_PATH)


driver_parcel = _load_driver_parcel()


class TestParcelStatusNormalization(unittest.TestCase):
    """Legacy lowercase driver statuses map onto real Select options."""

    def test_legacy_statuses_map_to_parcel_select_options(self):
        self.assertEqual(
            driver_parcel.normalize_parcel_status("delivered"), "Delivered"
        )
        self.assertEqual(
            driver_parcel.normalize_parcel_status("canceled"), "Canceled"
        )
        self.assertEqual(
            driver_parcel.normalize_parcel_status("cancelled"), "Canceled"
        )
        self.assertEqual(
            driver_parcel.normalize_parcel_status("on_a_way"), "On a way"
        )
        self.assertEqual(
            driver_parcel.normalize_parcel_status("ready"), "Ready"
        )
        self.assertEqual(
            driver_parcel.normalize_parcel_status("accepted"), "Accepted"
        )
        self.assertEqual(driver_parcel.normalize_parcel_status("new"), "New")

    def test_normalization_is_case_and_whitespace_insensitive(self):
        self.assertEqual(
            driver_parcel.normalize_parcel_status(" Delivered "), "Delivered"
        )
        self.assertEqual(
            driver_parcel.normalize_parcel_status("ON_A_WAY"), "On a way"
        )
        self.assertEqual(
            driver_parcel.normalize_parcel_status("On a way"), "On a way"
        )

    def test_unknown_statuses_return_none(self):
        self.assertIsNone(driver_parcel.normalize_parcel_status("shipped"))
        self.assertIsNone(driver_parcel.normalize_parcel_status("bogus"))
        self.assertIsNone(driver_parcel.normalize_parcel_status(""))
        self.assertIsNone(driver_parcel.normalize_parcel_status(None))

    def test_all_mapped_values_are_real_select_options(self):
        select_options = {
            "New", "Accepted", "Ready", "On a way", "Delivered", "Canceled"
        }
        self.assertTrue(
            set(driver_parcel.PARCEL_STATUS_MAP.values()) <= select_options
        )


class TestParseCodAmount(unittest.TestCase):
    """amount_received must parse to a non-negative finite float."""

    def test_accepts_numbers_and_numeric_strings(self):
        self.assertEqual(driver_parcel.parse_cod_amount(150), 150.0)
        self.assertEqual(driver_parcel.parse_cod_amount("99.90"), 99.9)
        self.assertEqual(driver_parcel.parse_cod_amount(0), 0.0)
        self.assertEqual(driver_parcel.parse_cod_amount("0"), 0.0)

    def test_rejects_negative_amounts(self):
        with self.assertRaises(ValueError):
            driver_parcel.parse_cod_amount(-1)
        with self.assertRaises(ValueError):
            driver_parcel.parse_cod_amount("-0.01")

    def test_rejects_non_numeric_input(self):
        with self.assertRaises(ValueError):
            driver_parcel.parse_cod_amount("abc")
        with self.assertRaises(ValueError):
            driver_parcel.parse_cod_amount(None)
        with self.assertRaises(ValueError):
            driver_parcel.parse_cod_amount("")

    def test_rejects_nan_and_infinity(self):
        with self.assertRaises(ValueError):
            driver_parcel.parse_cod_amount("nan")
        with self.assertRaises(ValueError):
            driver_parcel.parse_cod_amount("inf")
        with self.assertRaises(ValueError):
            driver_parcel.parse_cod_amount(float("-inf"))


if __name__ == "__main__":
    unittest.main()
