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

"""Offline tests for wave 2: official-alert relay awareness + admin view.

Same harness style as test_warnings_engine.py: frappe is stubbed when no
bench is available, no network is touched, runs with `python3 -m unittest`
anywhere. Covers:

  * official_alerts.apply_official_alert_relay with fixture get_weather
    payloads (alerts present / absent / malformed / cold cache / cache
    errors), the ZA-default config gate (country field first, lat/lng
    bounding-box fallback), the coordinate-match guard, and the legal copy
    rule (no "warning" in end-user strings, before or after decoration);
  * the evaluator writing the queryable admin fields (detector_tier,
    confidence) on Severe Weather Warning;
  * the doctype JSONs carrying the admin list-view/filter configuration
    (the desk-list-view admin dashboard activates by fixture sync alone);
  * source-level wiring of the relay into get_weather_warnings.py.
"""

import copy
import datetime as dt
import importlib
import importlib.util
import json
import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FRAPPE_MODULE_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
COMMON_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "warnings_engine")
ENGINE_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "control", "warnings_engine")
DOCTYPE_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "control", "doctype")
API_FILE = os.path.join(FRAPPE_MODULE_DIR, "src", "control", "api",
                        "get_weather_warnings", "get_weather_warnings.py")


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


def _load_engine():
    """Load the split src/ trees exactly as they compose: wmod.warnings_engine
    (common: messages/push/admin_log) and wmod.control.warnings_engine (the
    engine), so the engine's relative imports into common resolve."""
    _ensure_frappe_stub()
    for name in ("wmod", "wmod.control"):
        if name not in sys.modules:
            parent = types.ModuleType(name)
            parent.__path__ = []
            sys.modules[name] = parent
    _load_pkg("wmod.warnings_engine", COMMON_DIR)
    return _load_pkg("wmod.control.warnings_engine", ENGINE_DIR)


_load_engine()
official_alerts = importlib.import_module("wmod.control.warnings_engine.official_alerts")
evaluator = importlib.import_module("wmod.control.warnings_engine.evaluator")
messages = importlib.import_module("wmod.warnings_engine.messages")
fusion = importlib.import_module("wmod.control.warnings_engine.fusion")
climatology = importlib.import_module("wmod.control.warnings_engine.climatology")

import frappe  # noqa: E402  (after stub install, like the sibling tests)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

GRID_LAT, GRID_LNG = -25.75, 28.25   # Pretoria-ish grid cell (inside ZA box)
LABEL = "Pretoria"
CACHE_KEY = "weather_proxy_pretoria"

OFFICIAL_ALERT = {
    "headline": "Severe Thunderstorm Warning",
    "event": "Severe Thunderstorm",
    "desc": "The South African Weather Service has issued ...",
    "effective": "2026-08-19T10:00:00+02:00",
    "expires": "2026-08-19T20:00:00+02:00",
}


def _payload(country="South Africa", lat=GRID_LAT, lon=GRID_LNG,
             alerts_present=True, alerts_value="default"):
    """A weatherapi.com-shaped get_weather proxy payload fixture."""
    payload = {
        "location": {"name": LABEL, "country": country, "lat": lat, "lon": lon},
        "current": {"temp_c": 21.0},
        "forecast": {"forecastday": []},
    }
    if country is None:
        del payload["location"]["country"]
    if alerts_value != "default":
        payload["alerts"] = alerts_value
    elif alerts_present:
        payload["alerts"] = {"alert": [dict(OFFICIAL_ALERT)]}
    else:
        payload["alerts"] = {"alert": []}
    return payload


def _response(n_warnings=1):
    rendered = messages.render("flash_flood", "heads_up", LABEL)
    warnings = [{
        "id": f"SWW-2026-0000{i + 1}",
        "event_class": "flash_flood",
        "severity": rendered["severity"],
        "severity_label": rendered["severity_label"],
        "headline": rendered["headline"],
        "message": rendered["message"],
        "onset": "2026-08-19T06:00:00Z",
        "valid_until": "2026-08-20T06:00:00Z",
        "issued_at": "2026-08-19T07:00:00Z",
    } for i in range(n_warnings)]
    return {
        "warnings": warnings,
        "attribution": messages.ATTRIBUTION,
        "generated_at": "2026-08-19T08:00:00Z",
    }


class _FakeCache:
    def __init__(self, store=None, raises=False):
        self.store = store or {}
        self.raises = raises

    def get_value(self, key):
        if self.raises:
            raise RuntimeError("cache backend down")
        return self.store.get(key)


class _RelayCase(unittest.TestCase):
    """Base: swap frappe.cache / frappe.conf per test, restore after."""

    def setUp(self):
        self._saved_cache = frappe.cache
        self._saved_conf = frappe.conf
        self.set_cache({})
        frappe.conf = {}

    def tearDown(self):
        frappe.cache = self._saved_cache
        frappe.conf = self._saved_conf

    def set_cache(self, store, raises=False):
        fake = _FakeCache(store, raises=raises)
        frappe.cache = lambda: fake

    def apply(self, response, grid_lat=GRID_LAT, grid_lng=GRID_LNG,
              label=LABEL):
        return official_alerts.apply_official_alert_relay(
            response, grid_lat, grid_lng, label)


# --------------------------------------------------------------------------- #
# relay behavior
# --------------------------------------------------------------------------- #

class TestRelayDecoration(_RelayCase):
    def test_alerts_present_za_default_on(self):
        self.set_cache({CACHE_KEY: _payload()})
        response = self.apply(_response(n_warnings=2))
        self.assertIs(response.get("official_alerts_present"), True)
        for item in response["warnings"]:
            self.assertIn(official_alerts.CROSS_REFERENCE_LINE,
                          item["message"])
            self.assertEqual(
                1, item["message"].count(official_alerts.CROSS_REFERENCE_LINE))
        # headline and structured fields untouched
        rendered = messages.render("flash_flood", "heads_up", LABEL)
        self.assertEqual(response["warnings"][0]["headline"],
                         rendered["headline"])
        self.assertEqual(response["warnings"][0]["severity"], "heads_up")

    def test_line_never_duplicated_on_reapply(self):
        self.set_cache({CACHE_KEY: _payload()})
        response = self.apply(self.apply(_response()))
        self.assertEqual(
            1,
            response["warnings"][0]["message"].count(
                official_alerts.CROSS_REFERENCE_LINE))

    def test_empty_warnings_still_flags_presence(self):
        self.set_cache({CACHE_KEY: _payload()})
        response = self.apply(_response(n_warnings=0))
        self.assertIs(response.get("official_alerts_present"), True)
        self.assertEqual(response["warnings"], [])

    def test_copy_rules_hold_after_decoration(self):
        """Legal copy rule: no end-user string may contain 'warning'."""
        self.set_cache({CACHE_KEY: _payload()})
        response = self.apply(_response())
        for item in response["warnings"]:
            for key in ("headline", "message", "severity_label"):
                self.assertNotIn("warning", item[key].lower())
        self.assertNotIn(
            "warning", official_alerts.CROSS_REFERENCE_LINE.lower())


class TestRelayUnchangedPaths(_RelayCase):
    def assert_unchanged(self, store=None, raises=False, **apply_kwargs):
        self.set_cache(store or {}, raises=raises)
        original = _response()
        response = self.apply(copy.deepcopy(original), **apply_kwargs)
        self.assertEqual(response, original)

    def test_alerts_absent(self):
        self.assert_unchanged({CACHE_KEY: _payload(alerts_present=False)})

    def test_alerts_key_missing(self):
        payload = _payload()
        del payload["alerts"]
        self.assert_unchanged({CACHE_KEY: payload})

    def test_cold_cache(self):
        self.assert_unchanged({})

    def test_cache_backend_error(self):
        self.assert_unchanged({CACHE_KEY: _payload()}, raises=True)

    def test_no_label(self):
        self.assert_unchanged({CACHE_KEY: _payload()}, label=None)
        self.assert_unchanged({CACHE_KEY: _payload()}, label="")

    def test_malformed_payloads(self):
        malformed = [
            "not a dict",
            ["not", "a", "dict"],
            _payload(alerts_value=None),
            _payload(alerts_value="storm coming"),
            _payload(alerts_value=["bare", "list"]),
            _payload(alerts_value={"alert": "not a list"}),
            _payload(alerts_value={"alert": None}),
            _payload(alerts_value={"alert": ["strings", 42, None]}),
            _payload(alerts_value={"alert": [{}]}),  # empty dict entries
        ]
        for payload in malformed:
            with self.subTest(payload=payload):
                self.assert_unchanged({CACHE_KEY: payload})

    def test_far_away_payload_coordinates_reject(self):
        # Durban payload cached under this label, cell is Pretoria: no relay.
        payload = _payload(lat=-29.85, lon=31.0)
        self.assert_unchanged({CACHE_KEY: payload})

    def test_missing_payload_coordinates_accepted(self):
        payload = _payload()
        del payload["location"]["lat"]
        del payload["location"]["lon"]
        self.set_cache({CACHE_KEY: payload})
        response = self.apply(_response())
        self.assertIs(response.get("official_alerts_present"), True)


class TestRelayConfigGate(_RelayCase):
    def test_default_off_outside_za_by_country(self):
        payload = _payload(country="Australia", lat=-33.75, lon=151.25)
        self.set_cache({"weather_proxy_pretoria": payload})
        original = _response()
        response = self.apply(copy.deepcopy(original),
                              grid_lat=-33.75, grid_lng=151.25)
        self.assertEqual(response, original)

    def test_country_field_is_authoritative_over_box(self):
        # ZA country in the payload, cell outside the ZA box: relay stays on.
        payload = _payload(country="South Africa", lat=51.5, lon=-0.25)
        self.set_cache({CACHE_KEY: payload})
        response = self.apply(_response(), grid_lat=51.5, grid_lng=-0.25)
        self.assertIs(response.get("official_alerts_present"), True)

    def test_bounding_box_fallback_when_country_missing(self):
        inside = _payload(country=None)
        self.set_cache({CACHE_KEY: inside})
        response = self.apply(_response())
        self.assertIs(response.get("official_alerts_present"), True)

        outside = _payload(country=None, lat=51.5, lon=-0.25)
        self.set_cache({CACHE_KEY: outside})
        original = _response()
        response = self.apply(copy.deepcopy(original),
                              grid_lat=51.5, grid_lng=-0.25)
        self.assertEqual(response, original)

    def test_flag_falsy_disables_everywhere(self):
        for flag in (0, False, "0", "off", "false", "no", ""):
            with self.subTest(flag=flag):
                frappe.conf = {official_alerts.CONFIG_FLAG: flag}
                self.set_cache({CACHE_KEY: _payload()})
                original = _response()
                response = self.apply(copy.deepcopy(original))
                self.assertEqual(response, original)

    def test_flag_truthy_enables_outside_za(self):
        for flag in (1, True, "1", "all", "on"):
            with self.subTest(flag=flag):
                frappe.conf = {official_alerts.CONFIG_FLAG: flag}
                payload = _payload(country="Australia",
                                   lat=-33.75, lon=151.25)
                self.set_cache({CACHE_KEY: payload})
                response = self.apply(_response(),
                                      grid_lat=-33.75, grid_lng=151.25)
                self.assertIs(response.get("official_alerts_present"), True)

    def test_conf_error_fails_silent(self):
        class _BadConf:
            def get(self, *a, **k):
                raise RuntimeError("no conf")
        frappe.conf = _BadConf()
        self.set_cache({CACHE_KEY: _payload()})
        original = _response()
        response = self.apply(copy.deepcopy(original))
        self.assertEqual(response, original)


class TestCacheKeyMirrorsGetWeather(unittest.TestCase):
    def test_key_normalisation(self):
        # must mirror get_weather.py: lower + spaces -> underscores
        self.assertEqual("weather_proxy_pretoria",
                         official_alerts.proxy_cache_key("Pretoria"))
        self.assertEqual("weather_proxy_cape_town,za",
                         official_alerts.proxy_cache_key("Cape Town,ZA"))


# --------------------------------------------------------------------------- #
# admin view: evaluator fields + doctype JSON configuration
# --------------------------------------------------------------------------- #

class TestEvaluatorAdminFields(unittest.TestCase):
    def test_upsert_writes_queryable_tier_and_confidence(self):
        saved_db = frappe.db
        try:
            frappe.db = MagicMock()
            frappe.db.get_value = MagicMock(return_value="SWW-2026-00001")
            now = dt.datetime(2026, 8, 19, 8, 0, 0)
            horizon = now  # validity_end keeps the episode live
            loc = SimpleNamespace(name="-25.75,28.25", label=LABEL)
            episode = SimpleNamespace(
                fired_conditions=("p72_wet", "sm_sat"),
                max_confidence=0.91,
                first_fired_at=dt.datetime(2026, 8, 18, 20, 0, 0),
            )
            result = SimpleNamespace(
                tier=[2, 3], confidence=[0.5, 0.874], alarms=[episode])
            source = SimpleNamespace(name="test_source")
            evaluator._upsert_warning(
                loc, "flash_flood", result, source, horizon, now)
            self.assertTrue(frappe.db.set_value.called)
            args, _ = frappe.db.set_value.call_args
            fields = args[2]
            self.assertEqual(3, fields["detector_tier"])
            self.assertEqual(0.874, fields["confidence"])
            self.assertEqual("warning", fields["severity"])  # internal enum
            precursors = json.loads(fields["precursors"])
            self.assertEqual(3, precursors["detector_tier"])
            self.assertEqual(0.874, precursors["confidence"])
        finally:
            frappe.db = saved_db


class TestDoctypeAdminView(unittest.TestCase):
    """The admin view is the desk list view, driven by the fixture JSONs."""

    @staticmethod
    def _fields(doctype_json):
        path = os.path.join(DOCTYPE_DIR, doctype_json, doctype_json + ".json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data, {field["fieldname"]: field for field in data["fields"]}

    def test_severe_weather_warning_admin_columns(self):
        data, fields = self._fields("severe_weather_warning")
        for name in ("detector_tier", "confidence"):
            self.assertIn(name, fields)
            self.assertEqual(1, fields[name].get("read_only"))
            self.assertEqual(1, fields[name].get("in_list_view"))
        # episode identity + timings visible in the list
        for name in ("watch_location", "event_class", "valid_until", "status"):
            self.assertEqual(1, fields[name].get("in_list_view"), name)
        for name in ("watch_location", "event_class", "severity", "status"):
            self.assertEqual(1, fields[name].get("in_standard_filter"), name)
        self.assertEqual("watch_location,event_class,status",
                         data.get("search_fields"))

    def test_watch_location_health_dashboard(self):
        _, fields = self._fields("weather_watch_location")
        # health fields the design doc calls for are present and read-only
        for name in ("last_evaluated_at", "last_evaluated_horizon",
                     "last_error", "consecutive_failures"):
            self.assertIn(name, fields)
            self.assertEqual(1, fields[name].get("read_only"), name)
        # last-evaluation health readable straight off the list view
        for name in ("grid_key", "active", "last_evaluated_at",
                     "consecutive_failures"):
            self.assertEqual(1, fields[name].get("in_list_view"), name)
        for name in ("grid_key", "active"):
            self.assertEqual(1, fields[name].get("in_standard_filter"), name)


class TestCombinedCopyCap(_RelayCase):
    """Wave-2 integration rule: at most TWO appended sentences per message,
    priority fusion > seasonal > relay - the relay's cross-reference is the
    lowest-priority extra and backs off once both others are present."""

    FUSION_SENTENCE = fusion.TIMING_MESSAGE_SUFFIX["rain"].format(
        when="on Thursday").strip()
    SEASONAL_SENTENCE = climatology.NOTE_SENTENCES[0]

    def _response_with(self, *extras):
        response = _response(n_warnings=1)
        message = response["warnings"][0]["message"]
        for extra in extras:
            message = f"{message} {extra}"
        response["warnings"][0]["message"] = message
        return response

    def test_relay_appends_after_one_fusion_sentence(self):
        self.set_cache({CACHE_KEY: _payload()})
        response = self.apply(self._response_with(self.FUSION_SENTENCE))
        self.assertIn(official_alerts.CROSS_REFERENCE_LINE,
                      response["warnings"][0]["message"])

    def test_relay_appends_after_one_seasonal_sentence(self):
        self.set_cache({CACHE_KEY: _payload()})
        response = self.apply(self._response_with(self.SEASONAL_SENTENCE))
        self.assertIn(official_alerts.CROSS_REFERENCE_LINE,
                      response["warnings"][0]["message"])

    def test_relay_backs_off_at_two_appended_sentences(self):
        self.set_cache({CACHE_KEY: _payload()})
        loaded = self._response_with(self.FUSION_SENTENCE,
                                     self.SEASONAL_SENTENCE)
        before = loaded["warnings"][0]["message"]
        response = self.apply(loaded)
        # the message is left alone at the cap...
        self.assertEqual(before, response["warnings"][0]["message"])
        self.assertNotIn(official_alerts.CROSS_REFERENCE_LINE,
                         response["warnings"][0]["message"])
        # ...but the structured flag still tells clients about the alert
        self.assertIs(response.get("official_alerts_present"), True)

    def test_extra_count_recognises_each_module_once(self):
        base = _response(n_warnings=1)["warnings"][0]["message"]
        count = official_alerts._appended_extra_count
        self.assertEqual(0, count(base))
        self.assertEqual(1, count(f"{base} {self.FUSION_SENTENCE}"))
        self.assertEqual(1, count(
            f"{base} {fusion.SOFTEN_MESSAGE_SUFFIX.strip()}"))
        self.assertEqual(1, count(f"{base} {self.SEASONAL_SENTENCE}"))
        self.assertEqual(2, count(
            f"{base} {self.FUSION_SENTENCE} {self.SEASONAL_SENTENCE}"))


class TestEndpointWiring(unittest.TestCase):
    def test_relay_wired_into_get_weather_warnings(self):
        with open(API_FILE, encoding="utf-8") as f:
            source = f.read()
        self.assertIn("apply_official_alert_relay", source)
        # the relay call is individually guarded (fail-silent contract)
        relay_at = source.index("apply_official_alert_relay(")
        guard_at = source.rindex("try:", 0, relay_at)
        self.assertIn("except Exception:", source[relay_at:relay_at + 400])
        self.assertGreater(relay_at, guard_at)


if __name__ == "__main__":
    unittest.main()
