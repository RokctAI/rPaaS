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

"""Offline tests for the TENANT-side get_weather_warnings proxy.

Same harness style as the sibling tests: frappe is stubbed when no bench is
available, no network is touched, runs with `python3 -m unittest` anywhere.
Covers the thin cached proxy (src/tenant/api/get_weather_warnings/):

  * the control-plane envelope: the get_weather mechanism verbatim
    (control_plane_url / api_secret site config, X-Rokct-Secret /
    X-Rokct-Tenant headers, /api/method/control.api.get_weather_warnings),
    grid-rounded coordinates as params, {"message": ...} unwrapping;
  * the 600 s per-grid-cell response cache (one upstream call per TTL);
  * the fail-silent contract: unconfigured tenant, upstream error, or a
    malformed reply all return the empty envelope - never an exception;
  * tenant-local subscriber registration (logged-in callers only; the
    scheduler-facing fetch_cell_warnings never self-subscribes).
"""

import datetime as dt
import importlib
import importlib.util
import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FRAPPE_MODULE_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
COMMON_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "warnings_engine")
TENANT_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "tenant")


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
    utils_mod.get_datetime = lambda v: v
    utils_mod.now_datetime = MagicMock()
    frappe_mod.utils = utils_mod
    frappe_mod.conf = {}
    frappe_mod.db = MagicMock()
    frappe_mod.cache = MagicMock()
    frappe_mod.get_doc = MagicMock()
    frappe_mod.get_all = MagicMock()
    frappe_mod.get_traceback = MagicMock(return_value="traceback")
    frappe_mod.log_error = MagicMock()
    frappe_mod.make_get_request = MagicMock()
    frappe_mod.whitelist = lambda *a, **k: (lambda f: f)
    sys.modules["frappe"] = frappe_mod
    sys.modules["frappe.utils"] = utils_mod


def _load_pkg(name, pkg_dir):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name,
        os.path.join(pkg_dir, "__init__.py"),
        submodule_search_locations=[pkg_dir],
    )
    pkg = importlib.util.module_from_spec(spec)
    sys.modules[name] = pkg
    spec.loader.exec_module(pkg)
    return pkg


def _load_tenant():
    """Load the split src/ trees exactly as they compose: wmod.warnings_engine
    (common) and wmod.tenant (the tenant persona folder), so the proxy's
    relative imports into common resolve."""
    _ensure_frappe_stub()
    if "wmod" not in sys.modules:
        parent = types.ModuleType("wmod")
        parent.__path__ = []
        sys.modules["wmod"] = parent
    _load_pkg("wmod.warnings_engine", COMMON_DIR)
    return _load_pkg("wmod.tenant", TENANT_DIR)


_load_tenant()
proxy = importlib.import_module(
    "wmod.tenant.api.get_weather_warnings.get_weather_warnings")
messages = importlib.import_module("wmod.warnings_engine.messages")

import frappe  # noqa: E402  (after stub install, like the sibling tests)


# --------------------------------------------------------------------------- #
# fakes
# --------------------------------------------------------------------------- #

GRID_KEY = "-25.75,28.25"  # compliance-ignore: py-hardcoded-secret (test-fixture grid coordinate, not a credential)
TENANT_SITE = "shop.tenant.example"

CONTROL_RESPONSE = {
    "warnings": [{
        "id": "SWW-2026-00001",
        "event_class": "flash_flood",
        "severity": "heads_up",
        "severity_label": "Heads-up",
        "headline": "Heavy rain possible near Pretoria",
        "message": "Heavy rain is possible in the next day or so.",
        "onset": "2026-08-19T06:00:00Z",
        "valid_until": "2026-08-20T06:00:00Z",
        "issued_at": "2026-08-19T07:00:00Z",
    }],
    "attribution": messages.ATTRIBUTION,
    "generated_at": "2026-08-19T08:00:00Z",
}


class FakeCache:
    def __init__(self):
        self.store = {}
        self.expiries = {}
        self.raises = False

    def get_value(self, key):
        if self.raises:
            raise RuntimeError("cache backend down")
        return self.store.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        if self.raises:
            raise RuntimeError("cache backend down")
        self.store[key] = value
        self.expiries[key] = expires_in_sec


class FakeDB:
    """Just enough of frappe.db for the subscriber upsert."""

    def __init__(self):
        self.rows = {}   # name -> values dict
        self._seq = 0

    def get_value(self, doctype, filters, fieldnames, as_dict=False):
        for name, values in self.rows.items():
            if all(values.get(k) == v for k, v in filters.items()):
                return SimpleNamespace(
                    name=name,
                    **{f: values.get(f) for f in fieldnames if f != "name"})
        return None

    def set_value(self, doctype, name, values):
        self.rows.setdefault(name, {}).update(values)

    def insert_stub(self, payload):
        self._seq += 1
        name = f"WWS-{self._seq:05d}"
        values = dict(payload)
        values.pop("doctype", None)
        self.rows[name] = values
        return SimpleNamespace(name=name)


class ProxyTestCase(unittest.TestCase):
    def setUp(self):
        self.cache = FakeCache()
        self.db = FakeDB()
        self.upstream_calls = []
        self.upstream_response = {"message": dict(CONTROL_RESPONSE)}
        self.upstream_error = None

        def make_get_request(url, headers=None, params=None):
            self.upstream_calls.append(
                {"url": url, "headers": headers, "params": params})
            if self.upstream_error is not None:
                raise self.upstream_error
            return self.upstream_response

        def get_doc(payload):
            doc = self.db.insert_stub(payload)
            return SimpleNamespace(
                name=doc.name, insert=lambda ignore_permissions=False: doc)

        self._saved = (frappe.conf, frappe.cache, frappe.db,
                       frappe.make_get_request, frappe.get_doc,
                       getattr(frappe, "local", None),
                       getattr(frappe, "session", None))
        frappe.conf = {"control_plane_url": "control.example",
                       "api_secret": "s3cret"}
        frappe.cache = lambda: self.cache
        frappe.db = self.db
        frappe.make_get_request = make_get_request
        frappe.get_doc = get_doc
        frappe.local = SimpleNamespace(site=TENANT_SITE)
        frappe.session = SimpleNamespace(user="farmer@example.com")

        # count admin log lines without touching the (rate-limited) real one
        self.admin_logs = []
        self._saved_log = proxy.log_admin_error
        proxy.log_admin_error = lambda title, message=None: self.admin_logs.append(
            (title, message))

    def tearDown(self):
        (frappe.conf, frappe.cache, frappe.db, frappe.make_get_request,
         frappe.get_doc, frappe.local, frappe.session) = self._saved
        proxy.log_admin_error = self._saved_log

    def call(self, latitude=-25.7, longitude=28.2, **kwargs):
        return proxy.get_weather_warnings(
            latitude=latitude, longitude=longitude, **kwargs)


# --------------------------------------------------------------------------- #
# the control-plane envelope (the get_weather mechanism)
# --------------------------------------------------------------------------- #

class TestControlEnvelope(ProxyTestCase):
    def test_calls_the_control_alias_with_secret_headers(self):
        self.call()
        self.assertEqual(len(self.upstream_calls), 1)
        call = self.upstream_calls[0]
        self.assertEqual(
            call["url"],
            "https://control.example/api/method/control.api.get_weather_warnings")
        self.assertEqual(call["headers"]["X-Rokct-Secret"], "s3cret")
        self.assertEqual(call["headers"]["X-Rokct-Tenant"], TENANT_SITE)

    def test_coordinates_are_grid_rounded_before_forwarding(self):
        self.call(latitude=-25.7, longitude=28.2)
        params = self.upstream_calls[0]["params"]
        self.assertEqual(params["latitude"], -25.75)
        self.assertEqual(params["longitude"], 28.25)

    def test_scheme_override_is_honored(self):
        frappe.conf["control_plane_scheme"] = "http"
        self.call()
        self.assertTrue(
            self.upstream_calls[0]["url"].startswith("http://control.example/"))

    def test_message_envelope_is_unwrapped(self):
        response = self.call()
        self.assertEqual(response, CONTROL_RESPONSE)

    def test_bare_payload_without_envelope_is_accepted(self):
        self.upstream_response = dict(CONTROL_RESPONSE)
        response = self.call()
        self.assertEqual(response, CONTROL_RESPONSE)

    def test_locale_is_forwarded_when_given(self):
        self.call(locale="en-ZA")
        self.assertEqual(self.upstream_calls[0]["params"].get("locale"),
                         "en-ZA")


# --------------------------------------------------------------------------- #
# caching (the 600 s get_weather pattern)
# --------------------------------------------------------------------------- #

class TestResponseCache(ProxyTestCase):
    def test_second_call_is_served_from_cache(self):
        self.call()
        self.call()
        self.assertEqual(len(self.upstream_calls), 1)

    def test_cache_ttl_is_600_seconds(self):
        self.call()
        self.assertEqual(
            self.cache.expiries.get(f"weather_warnings_{GRID_KEY}"), 600)

    def test_different_cells_cache_separately(self):
        self.call(latitude=-25.7, longitude=28.2)
        self.call(latitude=-26.2, longitude=27.9)
        self.assertEqual(len(self.upstream_calls), 2)

    def test_cache_backend_trouble_does_not_break_the_endpoint(self):
        self.cache.raises = True
        response = self.call()
        self.assertEqual(response, CONTROL_RESPONSE)

    def test_failures_are_not_cached(self):
        self.upstream_error = RuntimeError("control plane unreachable")
        self.call()
        self.assertNotIn(f"weather_warnings_{GRID_KEY}", self.cache.store)


# --------------------------------------------------------------------------- #
# the fail-silent contract
# --------------------------------------------------------------------------- #

class TestFailSilent(ProxyTestCase):
    def assert_empty(self, response):
        self.assertEqual(response["warnings"], [])
        self.assertEqual(response["attribution"], messages.ATTRIBUTION)
        self.assertIn("generated_at", response)

    def test_unconfigured_tenant_returns_empty_after_admin_log(self):
        frappe.conf = {}
        self.assert_empty(self.call())
        self.assertEqual(self.upstream_calls, [])
        self.assertTrue(self.admin_logs)

    def test_upstream_error_returns_empty(self):
        self.upstream_error = RuntimeError("control plane unreachable")
        self.assert_empty(self.call())
        self.assertTrue(self.admin_logs)

    def test_malformed_reply_returns_empty(self):
        self.upstream_response = {"message": {"unexpected": True}}
        self.assert_empty(self.call())

    def test_non_dict_reply_returns_empty(self):
        self.upstream_response = "<html>proxy error</html>"
        self.assert_empty(self.call())

    def test_invalid_coordinates_return_empty_without_a_control_call(self):
        self.assert_empty(self.call(latitude=None, longitude=None))
        self.assert_empty(self.call(latitude="x", longitude="y"))
        self.assert_empty(self.call(latitude=123.0, longitude=456.0))
        self.assertEqual(self.upstream_calls, [])


# --------------------------------------------------------------------------- #
# tenant-local subscriber registration
# --------------------------------------------------------------------------- #

class TestSubscriberRegistration(ProxyTestCase):
    def test_logged_in_caller_is_registered_for_the_grid_cell(self):
        self.call()
        rows = list(self.db.rows.values())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["watch_location"], GRID_KEY)
        self.assertEqual(rows[0]["user"], "farmer@example.com")

    def test_cache_hit_still_registers_the_subscriber(self):
        self.call()
        frappe.session = SimpleNamespace(user="second@example.com")
        self.call()
        users = sorted(v["user"] for v in self.db.rows.values())
        self.assertEqual(users, ["farmer@example.com", "second@example.com"])
        self.assertEqual(len(self.upstream_calls), 1)

    def test_guest_and_anonymous_sessions_are_not_registered(self):
        frappe.session = SimpleNamespace(user="Guest")
        self.call()
        frappe.session = None
        self.call()
        self.assertEqual(self.db.rows, {})

    def test_fresh_row_is_not_rewritten_within_refresh_window(self):
        self.call()
        (name, values), = self.db.rows.items()
        stamp = values["last_requested_at"]
        self.call()
        self.assertEqual(self.db.rows[name]["last_requested_at"], stamp)
        self.assertEqual(len(self.db.rows), 1)

    def test_stale_row_gets_its_timestamp_refreshed(self):
        self.call()
        (name, values), = self.db.rows.items()
        old = dt.datetime.utcnow() - dt.timedelta(hours=12)
        self.db.rows[name]["last_requested_at"] = old
        self.call()
        self.assertGreater(self.db.rows[name]["last_requested_at"], old)

    def test_registration_failure_never_breaks_the_endpoint(self):
        def broken_get_doc(payload):
            raise RuntimeError("db write refused")
        frappe.get_doc = broken_get_doc
        response = self.call()
        self.assertEqual(response, CONTROL_RESPONSE)

    def test_fetch_cell_warnings_never_registers_a_subscriber(self):
        proxy.fetch_cell_warnings(-25.75, 28.25)
        self.assertEqual(self.db.rows, {})
        self.assertEqual(len(self.upstream_calls), 1)


if __name__ == "__main__":
    unittest.main()
