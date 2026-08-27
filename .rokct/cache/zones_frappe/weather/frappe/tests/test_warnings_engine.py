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

"""Offline smoke tests for the severe-weather warnings engine.

Pure unit tests in the delivery module's style: frappe is stubbed when no
bench is available and no network is touched, so they run with
`python3 -m unittest` anywhere. They exercise the detector port (frozen
config integrity + state machine), the numpy feature port, the friendly-copy
rendering (including the legal wording constraint), and the evaluator's pure
mapping helpers.
"""

import datetime as dt
import hashlib
import importlib
import importlib.util
import json
import math
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FRAPPE_MODULE_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
COMMON_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "warnings_engine")
ENGINE_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "control", "warnings_engine")


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
detector = importlib.import_module("wmod.control.warnings_engine.detector")
features = importlib.import_module("wmod.control.warnings_engine.features")
messages = importlib.import_module("wmod.warnings_engine.messages")
evaluator = importlib.import_module("wmod.control.warnings_engine.evaluator")

import numpy as np  # noqa: E402  (after stub install, like the delivery tests)


class TestFrozenConfig(unittest.TestCase):
    def test_packaged_config_matches_frozen_sha256(self):
        with open(detector.config_path(), "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(digest, detector.CONFIG_SHA256)

    def test_load_rules_verifies_and_parses_all_classes(self):
        rules = detector.load_rules()
        self.assertEqual(
            set(rules), {"flash_flood", "flood", "destructive_wind", "tornado"})
        for rule in rules.values():
            self.assertGreater(len(rule.conditions), 0)

    def test_load_rules_refuses_tampered_config(self):
        with open(detector.config_path()) as f:
            raw = json.load(f)
        raw["classes"]["flood"]["conditions"][0]["on"] = 0.0  # loosen a gate
        tampered = os.path.join(TESTS_DIR, "_tampered_config.json")
        try:
            with open(tampered, "w") as f:
                json.dump(raw, f)
            with self.assertRaises(ValueError):
                detector.load_rules(tampered)
        finally:
            os.remove(tampered)

    def test_every_rule_feature_is_computed_by_the_feature_port(self):
        rules = detector.load_rules()
        computed = set(features.FEATURE_NAMES)
        for rule in rules.values():
            for name in rule.feature_names:
                self.assertIn(name, computed,
                              f"{rule.event_class} needs feature {name}")


class TestDetector(unittest.TestCase):
    def _times(self, n):
        t0 = dt.datetime(2026, 1, 1)
        return [t0 + dt.timedelta(hours=i) for i in range(n)]

    def test_synthetic_flood_episode_fires_and_releases(self):
        rules = detector.load_rules()
        rule = rules["flood"]
        n = 120
        feats = {}
        for cond in rule.conditions:
            v = [cond.on - 10.0 if cond.direction == "above" else cond.on + 10.0] * n
            # push every condition past its arming threshold for hours 40..80
            for i in range(40, 80):
                v[i] = cond.on + 5.0 if cond.direction == "above" else cond.on - 5.0
            feats[cond.feature] = v
        res = detector.run_class(self._times(n), feats, rule)
        self.assertEqual(len(res.alarms), 1)
        alarm = res.alarms[0]
        self.assertEqual(alarm.event_class, "flood")
        self.assertGreaterEqual(max(res.tier), detector.WARNING_TIER)
        self.assertEqual(res.tier[0], 0)
        self.assertEqual(res.tier[-1], 0)  # released after values fall back
        self.assertTrue(alarm.fired_conditions)

    def test_all_of_gate_blocks_partial_precursors(self):
        rules = detector.load_rules()
        rule = rules["flood"]  # all four conditions required
        n = 60
        feats = {}
        for k, cond in enumerate(rule.conditions):
            if k == 0:
                v = [cond.off - 1.0 if cond.direction == "above" else cond.off + 1.0] * n
            else:
                v = [cond.on + 5.0 if cond.direction == "above" else cond.on - 5.0] * n
            feats[cond.feature] = v
        res = detector.run_class(self._times(n), feats, rule)
        self.assertEqual(max(res.tier), 0)
        self.assertEqual(res.alarms, [])

    def test_nan_gap_within_tolerance_holds_state(self):
        rule = detector.rule_from_dict("t", {
            "conditions": [{"name": "c", "feature": "f", "direction": "above",
                            "on": 1.0, "off": 0.5, "weight": 1.0}],
            "required": ["c"],
            "severity_on": {"watch": 0.3, "warning": 0.5, "severe": 0.9},
            "nan_tolerance_h": 6,
        })
        n = 30
        v = [2.0] * n
        for i in range(10, 14):  # 4-hour gap, inside tolerance
            v[i] = float("nan")
        res = detector.run_class(self._times(n), {"f": v}, rule)
        self.assertTrue(all(t >= detector.WARNING_TIER for t in res.tier[5:20]))
        # numpy float NaN must also be treated as missing
        res2 = detector.run_class(
            self._times(n), {"f": np.array(v, dtype=np.float64)}, rule)
        self.assertEqual(res.tier, res2.tier)


class TestFeatures(unittest.TestCase):
    def _series(self, n, rng):
        return {
            "precipitation": rng.gamma(0.5, 1.0, n),
            "soil_moisture_0_to_7cm": 0.2 + 0.1 * rng.random(n),
            "pressure_msl": 101000.0 + 500.0 * rng.standard_normal(n),
            "wind_gusts_10m": 5.0 + 3.0 * rng.random(n),
            "wind_u_component_10m": rng.standard_normal(n) * 3.0,
            "wind_v_component_10m": rng.standard_normal(n) * 3.0,
            "wind_u_component_100m": rng.standard_normal(n) * 5.0,
            "wind_v_component_100m": rng.standard_normal(n) * 5.0,
            "temperature_2m": 20.0 + 5.0 * rng.standard_normal(n),
            "dew_point_2m": 15.0 + 4.0 * rng.standard_normal(n),
            "total_column_integrated_water_vapour": 30.0 + 5.0 * rng.random(n),
        }

    def test_rolling_sum_matches_naive(self):
        rng = np.random.default_rng(7)
        x = rng.random(100)
        x[20:25] = np.nan
        out = features.rolling_sum(x, 24, 18)
        for i in (0, 10, 23, 30, 60, 99):
            seg = x[max(0, i - 23): i + 1]
            finite = seg[np.isfinite(seg)]
            if finite.size >= 18:
                self.assertAlmostEqual(out[i], finite.sum(), places=9)
            else:
                self.assertTrue(math.isnan(out[i]))

    def test_backward_diff_and_rolling_max(self):
        x = np.arange(50, dtype=float)
        d = features.backward_diff(x, 24)
        self.assertTrue(np.isnan(d[:24]).all())
        self.assertTrue((d[24:] == 24.0).all())
        m = features.rolling_max(x, 24, 18)
        self.assertEqual(m[49], 49.0)
        self.assertTrue(math.isnan(m[10]))  # fewer than min_periods hours

    def test_causal_percentile_is_causal_and_bounded(self):
        x = np.arange(100, dtype=float)  # strictly increasing
        p = features.causal_percentile(x, min_history=48)
        self.assertTrue(np.isnan(p[:47]).all())
        valid = p[np.isfinite(p)]
        self.assertTrue((valid == 1.0).all())  # each value is its own running max

    def test_compute_features_emits_all_names(self):
        rng = np.random.default_rng(11)
        n = 408
        nbr = rng.gamma(0.5, 1.0, (n, 49))
        f = features.compute_features(self._series(n, rng), nbr)
        self.assertEqual(set(f), set(features.FEATURE_NAMES))
        for name, arr in f.items():
            self.assertEqual(len(arr), n, name)
        # late-window values must be defined once history suffices
        for name in ("precip_sum_24h", "tcwv_anom_7d", "mslp_tend_24h",
                     "gust_max_24h", "wspd_10m", "theta_e", "bulk_shear",
                     "nbr_max_sum_12h", "nbr_wet_frac"):
            self.assertTrue(np.isfinite(f[name][-1]), name)

    def test_missing_neighborhood_degrades_to_nan_not_crash(self):
        rng = np.random.default_rng(3)
        f = features.compute_features(self._series(408, rng), None)
        for name in ("nbr_max_sum_12h", "nbr_rain_on_sat_6h", "nbr_wet_frac"):
            self.assertTrue(np.isnan(f[name]).all(), name)

    def test_theta_e_plausible_magnitude(self):
        th = features.theta_e_proxy(np.array([25.0]), np.array([20.0]),
                                    np.array([1010.0]))
        self.assertTrue(320.0 < th[0] < 360.0)


class TestMessages(unittest.TestCase):
    def test_renders_every_allowed_pair_with_place(self):
        for event_class, max_sev in messages.CLASS_MAX_SEVERITY.items():
            sevs = {"heads_up": ["heads_up"],
                    "advisory": ["advisory"]}.get(max_sev,
                                                  ["heads_up", "warning"])
            for sev in sevs:
                out = messages.render(event_class, sev, "Messina")
                self.assertIn("Messina", out["headline"])
                self.assertIn("Messina", out["message"])
                self.assertEqual(out["severity"], sev)
                self.assertTrue(out["severity_label"])

    def test_missing_place_falls_back_to_your_area(self):
        out = messages.render("flood", "heads_up", None)
        self.assertIn("your area", out["message"])

    def test_tornado_is_capped_to_soft_heads_up(self):
        out = messages.render("tornado", "warning", "Messina")
        self.assertEqual(out["severity"], "heads_up")
        self.assertIn("Storms possible", out["headline"])

    def test_no_user_facing_string_uses_official_warning_taxonomy(self):
        # Legal constraint (ZA): only the national weather service issues
        # official warnings - user-facing text must never use the word
        # "warning" or official alert-level taxonomy.
        banned = ("warning", "warn ", "yellow", "orange level", "red level",
                  "level 1", "level 2", "alert level")
        strings = [messages.ATTRIBUTION] + list(messages.SEVERITY_LABELS.values())
        for event_class, max_sev in messages.CLASS_MAX_SEVERITY.items():
            sevs = {"heads_up": ["heads_up"],
                    "advisory": ["advisory"]}.get(max_sev,
                                                  ["heads_up", "warning"])
            for sev in sevs:
                out = messages.render(event_class, sev, "Messina")
                strings += [out["headline"], out["message"], out["severity_label"]]
        for s in strings:
            low = s.lower()
            for word in banned:
                self.assertNotIn(word, low, f"banned wording {word!r} in {s!r}")

    def test_attribution_exact(self):
        self.assertEqual(messages.ATTRIBUTION, "Weather data by Open-Meteo.com")


class TestEvaluatorHelpers(unittest.TestCase):
    def test_severity_mapping_is_calm(self):
        # below warning tier: nothing surfaces
        self.assertIsNone(evaluator.severity_for_tier("flood", 0))
        self.assertIsNone(evaluator.severity_for_tier("flood", 1))
        # detector "warning" tier -> heads_up; "severe" tier -> warning enum
        self.assertEqual(evaluator.severity_for_tier("flood", 2), "heads_up")
        self.assertEqual(evaluator.severity_for_tier("flood", 3), "warning")
        # tornado never escalates past heads_up
        self.assertEqual(evaluator.severity_for_tier("tornado", 3), "heads_up")

    def test_validity_window_per_class(self):
        horizon = dt.datetime(2026, 8, 19, 12)
        self.assertEqual(evaluator.validity_end("flood", horizon),
                         horizon + dt.timedelta(hours=48))
        self.assertEqual(evaluator.validity_end("flash_flood", horizon),
                         horizon + dt.timedelta(hours=24))

    def test_stale_horizon_never_reaches_users(self):
        # An episode computed from data older than its validity window must
        # not be issued: validity_end() <= now means "user sees nothing".
        now = dt.datetime(2026, 8, 19, 12)
        stale_horizon = now - dt.timedelta(hours=60)
        for event_class in ("flash_flood", "flood", "destructive_wind", "tornado"):
            self.assertLessEqual(evaluator.validity_end(event_class, stale_horizon), now)


if __name__ == "__main__":
    unittest.main()
