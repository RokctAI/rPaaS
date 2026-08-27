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

"""Unit tests for the intercity provider layer.

These are pure unit tests: settings are injected as plain objects and
HTTP calls are patched, so they run with `python3 -m unittest` both
inside and outside a Frappe bench. They cover the gating behaviour
(flag off by default, explicit not-configured errors), the compliance
gates, status mapping and the pickup-location reference logic.
"""

import importlib
import importlib.util
import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FRAPPE_MODULE_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
PROVIDERS_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "tenant", "providers")


def _ensure_frappe_stub():
    """Install a minimal frappe stub when no bench is available."""
    try:
        import frappe  # noqa: F401
        return
    except ImportError:
        pass

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
    frappe_mod.db = MagicMock()
    frappe_mod.get_single = MagicMock()
    frappe_mod.get_doc = MagicMock()
    frappe_mod.get_all = MagicMock()
    frappe_mod.get_traceback = MagicMock()
    frappe_mod.log_error = MagicMock()
    frappe_mod.make_get_request = MagicMock()
    frappe_mod.make_post_request = MagicMock()
    sys.modules["frappe"] = frappe_mod
    sys.modules["frappe.utils"] = utils_mod


def _load_providers_package():
    _ensure_frappe_stub()
    if "delivery_providers" in sys.modules:
        return sys.modules["delivery_providers"]
    spec = importlib.util.spec_from_file_location(
        "delivery_providers",
        os.path.join(PROVIDERS_DIR, "__init__.py"),
        submodule_search_locations=[PROVIDERS_DIR],
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules["delivery_providers"] = package
    spec.loader.exec_module(package)
    return package


_load_providers_package()
base = importlib.import_module("delivery_providers.base")
registry = importlib.import_module("delivery_providers.registry")
shiprazor = importlib.import_module("delivery_providers.shiprazor")
lifecycle = importlib.import_module("delivery_providers.lifecycle")


class FakeSettings:
    """Stands in for the Delivery Provider Settings document."""

    def __init__(self, **values):
        self._values = dict(values)

    def get(self, key, default=None):
        return self._values.get(key, default)

    def get_password(self, key, raise_exception=True):
        return self._values.get(key)


def configured_settings(**overrides):
    values = {
        "enable_intercity": 1,
        "active_provider": "ShipRazor",
        "shiprazor_api_key": "test-key",
        "shiprazor_base_url": "https://api.example.test",
        "pickup_location_grace_hours": 24,
    }
    values.update(overrides)
    return FakeSettings(**values)


def valid_parcel(**overrides):
    parcel = {
        "description": "Books and stationery",
        "category": "Documents",
        "declared_value": 1500,
        "address_from": "12 Main Road, Cape Town",
        "address_to": "8 Church Street, Johannesburg",
    }
    parcel.update(overrides)
    return parcel


class TestGatingDefaults(unittest.TestCase):
    """Everything is inert by default: flag off, no fake fallbacks."""

    def test_doctype_default_is_off(self):
        # The shipped Delivery Provider Settings doctype defaults the
        # master switch to off.
        path = os.path.join(
            FRAPPE_MODULE_DIR,
            "src",
            "tenant",
            "doctype",
            "delivery_provider_settings",
            "delivery_provider_settings.json",
        )
        with open(path) as fh:
            schema = json.load(fh)
        field = next(
            f for f in schema["fields"]
            if f["fieldname"] == "enable_intercity"
        )
        self.assertEqual(field["default"], "0")

    def test_disabled_when_flag_missing(self):
        self.assertFalse(registry.is_intercity_enabled(FakeSettings()))

    def test_disabled_when_flag_off(self):
        settings = FakeSettings(enable_intercity=0)
        self.assertFalse(registry.is_intercity_enabled(settings))
        with self.assertRaises(base.IntercityDisabledError):
            registry.get_provider(settings=settings)

    def test_flag_on_without_provider_raises_not_configured(self):
        settings = FakeSettings(enable_intercity=1)
        with self.assertRaises(base.ProviderNotConfiguredError) as ctx:
            registry.get_provider(settings=settings)
        self.assertIn("Delivery Provider Settings", str(ctx.exception))

    def test_unknown_provider_raises_not_configured(self):
        settings = FakeSettings(
            enable_intercity=1, active_provider="AcmePost"
        )
        with self.assertRaises(base.ProviderNotConfiguredError) as ctx:
            registry.get_provider(settings=settings)
        self.assertIn("AcmePost", str(ctx.exception))

    def test_missing_credentials_raise_not_configured(self):
        for missing in ("shiprazor_api_key", "shiprazor_base_url"):
            settings = configured_settings(**{missing: None})
            with self.assertRaises(base.ProviderNotConfiguredError):
                registry.get_provider(settings=settings)

    def test_fully_configured_resolves_shiprazor(self):
        provider = registry.get_provider(settings=configured_settings())
        self.assertIsInstance(provider, shiprazor.ShipRazorProvider)
        self.assertEqual(provider.name, "ShipRazor")


class TestShipRazorAdapter(unittest.TestCase):
    def setUp(self):
        self.provider = shiprazor.ShipRazorProvider(configured_settings())

    def test_quote_requires_declared_value(self):
        with patch.object(shiprazor.frappe, "make_post_request") as post:
            with self.assertRaises(base.ProviderError):
                self.provider.get_quote(valid_parcel(declared_value=None))
            post.assert_not_called()

    def test_quote_blocks_prohibited_items(self):
        parcel = valid_parcel(description="Lithium battery power bank")
        with patch.object(shiprazor.frappe, "make_post_request") as post:
            with self.assertRaises(base.ProhibitedItemError):
                self.provider.get_quote(parcel)
            post.assert_not_called()

    def test_prohibited_gate_checks_items_and_category(self):
        parcel = valid_parcel(items=["Fireworks pack"])
        with self.assertRaises(base.ProhibitedItemError):
            self.provider.validate_parcel(parcel)
        # word-boundary match: no false positive on substrings
        self.provider.validate_parcel(
            valid_parcel(description="Gemsbok figurine artwork")
        )

    def test_quote_is_provider_passthrough(self):
        provider_response = {"rates": [{"service": "economy", "amount": 123}]}
        with patch.object(
            shiprazor.frappe, "make_post_request",
            return_value=provider_response,
        ) as post:
            quote = self.provider.get_quote(valid_parcel())
        self.assertIs(quote, provider_response)
        post.assert_called_once()
        url = post.call_args[0][0]
        self.assertTrue(url.startswith("https://api.example.test/"))

    def test_create_shipment_extracts_references(self):
        provider_response = {
            "shipment_id": "SR-001",
            "waybill": "WB-9",
            "tracking_url": "https://track.example.test/WB-9",
        }
        with patch.object(
            shiprazor.frappe, "make_post_request",
            return_value=provider_response,
        ):
            booking = self.provider.create_shipment(
                valid_parcel(pickup_location_ref="WH-1")
            )
        self.assertEqual(booking["provider_shipment_ref"], "SR-001")
        self.assertEqual(booking["waybill_no"], "WB-9")
        self.assertEqual(
            booking["tracking_url"], "https://track.example.test/WB-9"
        )

    def test_create_shipment_without_references_raises(self):
        with patch.object(
            shiprazor.frappe, "make_post_request", return_value={}
        ):
            with self.assertRaises(base.ProviderError):
                self.provider.create_shipment(valid_parcel())

    def test_webhook_maps_provider_statuses(self):
        event = self.provider.handle_webhook(
            {"shipment_id": "SR-001", "status": "delivered"}
        )
        self.assertEqual(event["provider_shipment_ref"], "SR-001")
        self.assertEqual(event["status"], "delivered")

        event = self.provider.handle_webhook(
            {"shipment_id": "SR-001", "status": "rto_delivered"}
        )
        self.assertEqual(event["status"], "rto_complete")

    def test_webhook_unknown_status_raises(self):
        with self.assertRaises(base.ProviderError):
            self.provider.handle_webhook(
                {"shipment_id": "SR-001", "status": "teleported"}
            )

    def test_webhook_without_reference_raises(self):
        with self.assertRaises(base.ProviderError):
            self.provider.handle_webhook({"status": "delivered"})


class TestStatusMapping(unittest.TestCase):
    def test_normalized_to_parcel_status(self):
        self.assertEqual(base.map_to_parcel_status("booked"), "Accepted")
        self.assertEqual(base.map_to_parcel_status("collected"), "On a way")
        self.assertEqual(base.map_to_parcel_status("delivered"), "Delivered")
        self.assertEqual(base.map_to_parcel_status("cancelled"), "Canceled")
        self.assertEqual(base.map_to_parcel_status("rto_complete"), "Canceled")

    def test_unknown_status_raises(self):
        with self.assertRaises(base.ProviderError):
            base.map_to_parcel_status("nonsense")


class TestPickupLifecycle(unittest.TestCase):
    def test_reference_is_deterministic_across_formatting(self):
        ref_a = lifecycle.pickup_reference(
            "user1", "12 Main Road, Cape Town"
        )
        ref_b = lifecycle.pickup_reference(
            "user1", "  12 MAIN road,,  Cape Town "
        )
        self.assertEqual(ref_a, ref_b)
        self.assertRegex(ref_a, r"^RKT-user1-[0-9a-f]{8}$")

    def test_reference_differs_per_user_and_address(self):
        address = "12 Main Road, Cape Town"
        self.assertNotEqual(
            lifecycle.pickup_reference("user1", address),
            lifecycle.pickup_reference("user2", address),
        )
        self.assertNotEqual(
            lifecycle.pickup_reference("user1", address),
            lifecycle.pickup_reference("user1", "8 Church Street"),
        )

    def test_terminal_statuses_release_refcount(self):
        for status in ("delivered", "cancelled", "rto_complete"):
            self.assertTrue(lifecycle.should_release_refcount(status))

    def test_rto_and_transit_statuses_hold_refcount(self):
        for status in (
            "rto_initiated", "rto_in_transit", "in_transit", "booked"
        ):
            self.assertFalse(lifecycle.should_release_refcount(status))


if __name__ == "__main__":
    unittest.main()
