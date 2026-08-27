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

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
"""
Bench-independent tests for get_shop_coords, the helper that parses shop
coordinates from the Shop.location Geolocation JSON field (the Shop doctype
has no latitude/longitude columns).

Runs directly with `python3 merchants/frappe/tests/test_shop_coords.py` --
frappe/paas are stubbed only when they are not already importable, so this
file is also safe to collect inside a real bench environment.
"""

import json
import sys
import types
import unittest
from pathlib import Path


def _stub_missing_modules():
    """Stub frappe/paas just enough to import shop.py outside a bench."""
    if "frappe" not in sys.modules:
        try:
            import frappe  # noqa: F401
        except ImportError:
            frappe = types.ModuleType("frappe")
            frappe.whitelist = lambda *a, **k: (lambda f: f)
            frappe.db = types.SimpleNamespace(get_value=lambda *a, **k: None)
            model = types.ModuleType("frappe.model")
            document = types.ModuleType("frappe.model.document")
            document.Document = type("Document", (), {})
            frappe.model = model
            sys.modules["frappe"] = frappe
            sys.modules["frappe.model"] = model
            sys.modules["frappe.model.document"] = document

    try:
        import paas.base.tenant.api.utils  # noqa: F401
        import paas.base.tenant.api.idempotency  # noqa: F401
    except ImportError:
        paas = types.ModuleType("paas")
        base = types.ModuleType("paas.base")
        tenant = types.ModuleType("paas.base.tenant")
        api = types.ModuleType("paas.base.tenant.api")
        utils = types.ModuleType("paas.base.tenant.api.utils")
        utils.api_response = lambda data=None, message=None, status_code=200: {
            "data": data
        }

        def _haversine(lat1, lon1, lat2, lon2):
            # Real great-circle distance (km) so behavior tests compute
            # the same result under the stub as under a real bench.
            import math

            r = 6371
            d_lat = math.radians(lat2 - lat1)
            d_lon = math.radians(lon2 - lon1)
            a = (
                math.sin(d_lat / 2) ** 2
                + math.cos(math.radians(lat1))
                * math.cos(math.radians(lat2))
                * math.sin(d_lon / 2) ** 2
            )
            return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        utils.haversine = _haversine
        idempotency = types.ModuleType("paas.base.tenant.api.idempotency")
        idempotency.idempotent = lambda f: f
        sys.modules.setdefault("paas", paas)
        sys.modules.setdefault("paas.base", base)
        sys.modules.setdefault("paas.base.tenant", tenant)
        sys.modules.setdefault("paas.base.tenant.api", api)
        sys.modules.setdefault("paas.base.tenant.api.utils", utils)
        sys.modules.setdefault("paas.base.tenant.api.idempotency", idempotency)


_stub_missing_modules()

_SHOP_PY = (
    Path(__file__).resolve().parents[1]
    / "src" / "tenant" / "api" / "shop" / "shop.py"
)
# src files are compose templates: the composer textually substitutes
# {app_name} with the target app's package name when copying them into an
# app, so mirror that substitution here before executing the template.
_shop_module = types.ModuleType("_shop_under_test")
_shop_module.__file__ = str(_SHOP_PY)
exec(
    compile(
        _SHOP_PY.read_text().replace("{app_name}", "paas"),
        str(_SHOP_PY),
        "exec",
    ),
    _shop_module.__dict__,
)
get_shop_coords = _shop_module.get_shop_coords


class TestGetShopCoords(unittest.TestCase):
    def test_latitude_longitude_keys(self):
        loc = json.dumps({"latitude": "-23.9045", "longitude": "29.4689"})
        self.assertEqual(
            get_shop_coords({"location": loc}), (-23.9045, 29.4689)
        )

    def test_lat_long_keys(self):
        loc = json.dumps({"lat": "-23.9", "long": "29.4"})
        self.assertEqual(get_shop_coords({"location": loc}), (-23.9, 29.4))

    def test_numeric_json_values(self):
        loc = json.dumps({"latitude": -23.9045, "longitude": 29.4689})
        self.assertEqual(
            get_shop_coords({"location": loc}), (-23.9045, 29.4689)
        )

    def test_already_parsed_dict_location(self):
        loc = {"latitude": "1.5", "longitude": "2.5"}
        self.assertEqual(get_shop_coords({"location": loc}), (1.5, 2.5))

    def test_garbage_json(self):
        self.assertEqual(
            get_shop_coords({"location": "not-json{"}), (None, None)
        )

    def test_json_but_not_object(self):
        self.assertEqual(get_shop_coords({"location": "[1, 2]"}), (None, None))

    def test_empty_location(self):
        self.assertEqual(get_shop_coords({"location": ""}), (None, None))
        self.assertEqual(get_shop_coords({"location": None}), (None, None))
        self.assertEqual(get_shop_coords({}), (None, None))

    def test_none_shop(self):
        self.assertEqual(get_shop_coords(None), (None, None))

    def test_missing_one_coordinate(self):
        loc = json.dumps({"latitude": "-23.9"})
        self.assertEqual(get_shop_coords({"location": loc}), (None, None))

    def test_non_numeric_coordinates(self):
        loc = json.dumps({"latitude": "abc", "longitude": "def"})
        self.assertEqual(get_shop_coords({"location": loc}), (None, None))

    def test_zero_coords_treated_as_missing(self):
        # Matches the existing truthiness behavior in get_shops, where
        # 0/"" coordinates fall back to the no-location branch.
        loc = json.dumps({"latitude": 0, "longitude": 0})
        self.assertEqual(get_shop_coords({"location": loc}), (None, None))

    def test_document_like_object(self):
        class FakeDoc:
            def get(self, key, default=None):
                if key == "location":
                    return json.dumps({"latitude": "3.5", "longitude": "4.5"})
                return default

        self.assertEqual(get_shop_coords(FakeDoc()), (3.5, 4.5))


class _FakeDB:
    def __init__(self, locations):
        self.locations = locations

    def get_value(self, doctype, name, fieldname=None, as_dict=False):
        if doctype == "Shop":
            return self.locations.get(name)
        return None


class _FakeFrappe:
    ValidationError = type("ValidationError", (Exception,), {})

    def __init__(self, locations):
        self.db = _FakeDB(locations)

    def throw(self, message, exc=None):
        raise (exc or Exception)(message)

    def whitelist(self, *args, **kwargs):
        return lambda fn: fn


class TestCheckDriverZone(unittest.TestCase):
    """check_driver_zone behavior around the coordinate fix: within/out
    of the 50km radius, missing location, garbage JSON. The module's
    `frappe` binding is swapped for a fake per test (only inside the
    module-under-test, so this is bench-safe)."""

    def setUp(self):
        self._orig_frappe = _shop_module.frappe

    def tearDown(self):
        _shop_module.frappe = self._orig_frappe

    def _call(self, locations, address):
        _shop_module.frappe = _FakeFrappe(locations)
        return _shop_module.check_driver_zone(
            shop_id="S1", address=address
        )

    def test_shop_with_good_coords_within_radius(self):
        result = self._call(
            {"S1": json.dumps({"latitude": -26.10, "longitude": 28.05})},
            {"latitude": -26.14, "longitude": 28.04},
        )
        self.assertTrue(result["data"]["status"])
        self.assertLess(result["data"]["distance"], 50)

    def test_shop_with_good_coords_out_of_radius(self):
        result = self._call(
            {"S1": json.dumps({"latitude": -26.10, "longitude": 28.05})},
            {"latitude": -33.92, "longitude": 18.42},  # Cape Town
        )
        self.assertFalse(result["data"]["status"])
        self.assertGreater(result["data"]["distance"], 50)

    def test_shop_without_location_is_graceful(self):
        result = self._call({}, {"latitude": -26.1, "longitude": 28.0})
        self.assertFalse(result["data"]["status"])
        self.assertIn("not found", result["data"]["message"])

    def test_shop_with_garbage_location_is_graceful(self):
        result = self._call(
            {"S1": "not-json{"}, {"latitude": -26.1, "longitude": 28.0}
        )
        self.assertFalse(result["data"]["status"])


if __name__ == "__main__":
    unittest.main()
