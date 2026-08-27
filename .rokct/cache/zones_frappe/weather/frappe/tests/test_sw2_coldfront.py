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

"""Offline synthetic tests for the sw2.1 cold-front pass (cold_front.py).

Covers: the four-signature detection core and its causality, per-threshold
config overrides, coalescing, the advisory-tier hard cap, the per-cell
cooldown, neighbor projection through propagation.py (cone gating, timing
words, no chain propagation, no consensus escalation, outranking), push
exclusion, fusion/climatology ignoring the class, and the calm-copy rule
(no user-facing "warning").

REAL-DATA REPLAY (fixture provenance; also in the PR notes): the detection
core with the shipped DEFAULTS was replayed over ERA5 hourly series
(open-meteo S3 archive, 2017-05-25..2017-06-12) for the documented
6-7 June 2017 "Cape storm" cold front (SAWS orange level 8; gusts to
~120 km/h; 8 deaths) at Western Cape 0.25-degree cells. Detected passages,
west-to-east exactly as the front moved:

  Cape Town coast   (-34.00, 18.50)  2017-06-07 03Z  (drop 5.5 degC,
                    shift 33 deg, trough -9.9/+1.9 hPa, gust bump +18.1 m/s)
  Swellendam area   (-34.00, 20.25)  2017-06-07 04Z  (drop 7.3, shift 117,
                    trough -10.0/+1.2, bump +10.1)
  Beaufort West     (-32.25, 22.50)  2017-06-07 08Z  (far inland, +5 h;
                    drop 8.8, shift 33, trough -10.9/+5.1, bump +6.8)

The preceding weaker front of 3 June 2017 is detected too (Worcester 15Z,
Swellendam 16Z, Beaufort West 18Z), and no cell fires on ordinary diurnal
cooling anywhere in the window (the trough-rise + gust-bump conjunction
gates it out). The synthetic profile
below (_front_series) mirrors the shape of those series: pre-frontal warm
NW flow, MSLP falling to a trough, then an abrupt temperature drop, wind
veer, pressure rise and gust surge.
"""

import datetime as dt
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
    try:
        import frappe  # noqa: F401
        if not hasattr(frappe.utils, "flt"):
            def flt(value):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return 0.0
            frappe.utils.flt = flt
            sys.modules["frappe.utils"].flt = flt
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

    def flt(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    utils_mod.cint = cint
    utils_mod.flt = flt
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
cold_front = importlib.import_module("wmod.control.warnings_engine.cold_front")
propagation = importlib.import_module("wmod.control.warnings_engine.propagation")
messages = importlib.import_module("wmod.warnings_engine.messages")
push = importlib.import_module("wmod.warnings_engine.push")
fusion = importlib.import_module("wmod.control.warnings_engine.fusion")

KM_PER_DEG_LAT = 111.19

T0 = dt.datetime(2017, 6, 1, 0)


# --------------------------------------------------------------------------- #
# synthetic series builder
# --------------------------------------------------------------------------- #

def _front_series(n=72, passage=60, temp_drop=8.0, veer_to=45.0,
                  trough_depth=6.0, rise=4.0, gust_peak=22.0):
    """Hourly series with a textbook cold-frontal passage at hour `passage`.

    Pre-front: 18 degC, NW-erly flow (u=3, v=-3: blowing toward the SE at
    135 deg), steady 1015 hPa, gusts ~8 m/s. Approach (12 h before passage):
    MSLP falls linearly to (1015 - trough_depth). At passage: temperature
    steps down by temp_drop over 3 h, wind swings to `veer_to` deg
    (toward-north-east for the default: u=v>0), pressure rises by `rise`
    over 6 h, gusts jump to gust_peak.
    """
    times = [T0 + dt.timedelta(hours=i) for i in range(n)]
    temp, mslp, gust, u, v = [], [], [], [], []
    for i in range(n):
        if i < passage:
            temp.append(18.0)
            gust.append(8.0)
            u.append(3.0)
            v.append(-3.0)          # toward 135 deg (SE)
        else:
            k = i - passage
            temp.append(18.0 - min(1.0, (k + 1) / 3.0) * temp_drop)
            gust.append(gust_peak)
            rad = math.radians(veer_to)
            u.append(6.0 * math.sin(rad))
            v.append(6.0 * math.cos(rad))  # toward `veer_to` deg
        # pressure: steady -> fall into trough at `passage` -> rise after
        if i < passage - 12:
            p = 1015.0
        elif i < passage:
            p = 1015.0 - trough_depth * (i - (passage - 12)) / 12.0
        else:
            p = (1015.0 - trough_depth) + min(1.0, (i - passage) / 6.0) * rise
        mslp.append(p * 100.0)      # store Pa like ERA5
    return times, {
        "temperature_2m": temp,
        "pressure_msl": mslp,
        "wind_gusts_10m": gust,
        "wind_u_component_10m": u,
        "wind_v_component_10m": v,
        # 100 m winds, only used by steering_speed_ms
        "wind_u_component_100m": u,
        "wind_v_component_100m": v,
    }


def loc(name, north_km=0.0, east_km=0.0, label=None):
    return {
        "name": name,
        "latitude": north_km / KM_PER_DEG_LAT,
        "longitude": east_km / KM_PER_DEG_LAT,
        "label": label or name.capitalize(),
    }


def front_record(name, location, steering=90.0, speed=15.0,
                 onset=None, valid_until=None, status="active",
                 mode=None):
    precursors = {"mode": mode or propagation.FRONT_DETECTION_MODE,
                  "steering_deg": steering,
                  "steering_speed_ms": speed}
    return {
        "name": name,
        "watch_location": location,
        "event_class": propagation.FRONT_CLASS,
        "severity": "advisory",
        "status": status,
        "onset": onset or dt.datetime(2017, 6, 7, 0),
        "valid_until": valid_until or dt.datetime(2017, 6, 8, 12),
        "headline": "hl",
        "message": "msg",
        "precursors": json.dumps(precursors),
    }


# --------------------------------------------------------------------------- #
# detection core
# --------------------------------------------------------------------------- #

class TestDetection(unittest.TestCase):
    def test_textbook_front_is_detected_once_at_passage(self):
        times, series = _front_series()
        passages = cold_front.detect_passages(times, series)
        self.assertEqual(len(passages), 1)
        p = passages[0]
        # first qualifying hour: within a few hours after the passage step
        self.assertGreaterEqual(p.index, 60)
        self.assertLessEqual(p.index, 66)
        self.assertGreaterEqual(p.temp_drop_c, 6.0)
        self.assertGreaterEqual(p.shift_deg, 45.0)
        self.assertGreaterEqual(p.trough_fall_hpa, 2.0)
        self.assertGreaterEqual(p.trough_rise_hpa, 1.0)
        self.assertGreaterEqual(p.gust_bump_ms, 5.0)

    def test_causal_no_detection_before_the_front_arrives(self):
        times, series = _front_series()
        cut = 60  # series truncated just before the passage hour
        truncated = {k: list(vals)[:cut] for k, vals in series.items()}
        self.assertEqual(
            cold_front.detect_passages(times[:cut], truncated), [])

    def test_temperature_drop_alone_is_not_a_front(self):
        # temperature falls but wind, pressure and gusts stay pre-frontal
        times, series = _front_series()
        n = len(times)
        flat = _front_series(n=n, passage=n + 1)[1]  # no front at all
        series = dict(flat)
        series["temperature_2m"] = _front_series()[1]["temperature_2m"]
        self.assertEqual(cold_front.detect_passages(times, series), [])

    def test_no_wind_shift_no_detection(self):
        times, series = _front_series()
        # keep the pre-frontal direction throughout (magnitude may grow)
        series = dict(series)
        series["wind_u_component_10m"] = [3.0] * len(times)
        series["wind_v_component_10m"] = [-3.0] * len(times)
        self.assertEqual(cold_front.detect_passages(times, series), [])

    def test_no_pressure_rise_after_trough_no_detection(self):
        # monotonic fall (deepening low, not a frontal trough passage)
        times, series = _front_series(rise=0.0)
        self.assertEqual(cold_front.detect_passages(times, series), [])

    def test_no_gust_bump_no_detection(self):
        times, series = _front_series(gust_peak=8.0)
        self.assertEqual(cold_front.detect_passages(times, series), [])

    def test_thresholds_are_config_overridable(self):
        times, series = _front_series(temp_drop=8.0)
        # tighten the temperature threshold past the synthetic drop
        self.assertEqual(
            cold_front.detect_passages(times, series, {"temp_drop_c": 9.5}),
            [])
        # loosen it back: detected again
        self.assertEqual(
            len(cold_front.detect_passages(times, series,
                                           {"temp_drop_c": 5.0})), 1)

    def test_defaults_constants_block(self):
        # the reviewed detection surface, calibrated on the 6-7 Jun 2017
        # Cape storm ERA5 replay - move deliberately
        d = cold_front.DEFAULTS
        self.assertEqual(d["temp_drop_c"], 5.0)
        self.assertEqual(d["temp_drop_window_h"], 12)
        self.assertEqual(d["shift_min_deg"], 30.0)
        self.assertEqual(d["shift_window_h"], 12)
        self.assertEqual(d["trough_window_h"], 24)
        self.assertEqual(d["trough_fall_hpa"], 3.0)
        self.assertEqual(d["trough_rise_hpa"], 1.0)
        self.assertEqual(d["gust_bump_ms"], 5.0)
        self.assertEqual(d["cooldown_h"], 72)
        self.assertEqual(d["recent_h"], 24)


# --------------------------------------------------------------------------- #
# advisory hard cap + copy
# --------------------------------------------------------------------------- #

class TestAdvisoryCap(unittest.TestCase):
    def test_class_is_hard_capped_at_advisory(self):
        for word in ("advisory", "heads_up", "warning", "severe", "junk"):
            self.assertEqual(
                messages.cap_severity(cold_front.FRONT_CLASS, word),
                "advisory")

    def test_severe_class_caps_are_unchanged(self):
        self.assertEqual(messages.cap_severity("flood", "warning"), "warning")
        self.assertEqual(messages.cap_severity("tornado", "warning"),
                         "heads_up")
        self.assertEqual(messages.cap_severity("flood", "advisory"),
                         "advisory")

    def test_render_serves_calm_advisory_copy(self):
        out = messages.render(cold_front.FRONT_CLASS, "warning", "Ceres")
        self.assertEqual(out["severity"], "advisory")
        self.assertEqual(out["severity_label"], "Worth knowing")
        self.assertIn("Ceres", out["headline"])
        self.assertIn("cool change", out["headline"].lower())

    def test_no_cold_front_copy_contains_the_word_warning(self):
        strings = [
            messages.render(cold_front.FRONT_CLASS, "advisory", "Ceres")[k]
            for k in ("headline", "message", "severity_label")]
        rendered = propagation.render_advisory(
            cold_front.FRONT_CLASS, "Ceres", "later today")
        strings += [rendered["headline"], rendered["message"],
                    rendered["severity_label"]]
        for s in strings:
            self.assertNotIn("warning", s.lower(), s)

    def test_severity_words_still_exclude_advisory(self):
        # keeps detector tier mapping and push ranking blind to advisories
        self.assertEqual(messages.SEVERITY_WORDS, ("heads_up", "warning"))


# --------------------------------------------------------------------------- #
# copy scaling: unusual-for-here variant + data-gated rain mention
# --------------------------------------------------------------------------- #

class _Passage:
    def __init__(self, drop, index=60):
        self.temp_drop_c = drop
        self.index = index
        self.time = T0 + dt.timedelta(hours=index)


class TestCopyScaling(unittest.TestCase):
    def test_ordinary_passage_keeps_the_plain_line(self):
        out = cold_front.render_detection("Ceres", unusual=False, rain=False)
        self.assertIn("cool change", out["message"].lower())
        self.assertNotIn("unusual", out["message"].lower())
        self.assertNotIn("rain", out["message"].lower())
        self.assertEqual(out["severity"], "advisory")

    def test_unusual_passage_gets_the_unusual_variant(self):
        out = cold_front.render_detection("Musina", unusual=True, rain=False)
        self.assertIn("unusual for this area", out["message"])
        self.assertIn("Noticeably colder", out["message"])
        self.assertIn("Musina", out["message"])
        self.assertEqual(out["severity"], "advisory")
        self.assertNotIn("warning", (out["headline"] + out["message"]).lower())

    def test_rain_sentence_only_when_gated(self):
        dry = cold_front.render_detection("Musina", unusual=True, rain=False)
        wet = cold_front.render_detection("Musina", unusual=True, rain=True)
        self.assertNotIn("rain", dry["message"].lower())
        self.assertTrue(wet["message"].endswith("Some rain may follow."))

    def test_absolute_unusual_gate(self):
        _, series = _front_series()
        cfg = dict(cold_front.DEFAULTS)
        unusual, _ = cold_front.is_unusual(_Passage(9.5), series, cfg)
        self.assertTrue(unusual)
        unusual, _ = cold_front.is_unusual(_Passage(5.0), series, cfg)
        self.assertFalse(unusual)   # flat pre-front series: spread ~0 is
                                    # ignored (falsy), absolute gate not met

    def test_adaptive_sigma_gate_flags_unusual_for_here(self):
        # a cell with a small diurnal wobble (spread ~1 degC): a 5 degC drop
        # is >> 3 sigma there, so it flags even below the absolute gate
        times, series = _front_series(temp_drop=5.0)
        series = dict(series)
        series["temperature_2m"] = [
            t + (1.4 if i % 24 in range(10, 16) else 0.0)
            for i, t in enumerate(series["temperature_2m"])]
        cfg = dict(cold_front.DEFAULTS)
        p = _Passage(5.0)
        unusual, spread = cold_front.is_unusual(p, series, cfg)
        self.assertIsNotNone(spread)
        self.assertTrue(unusual)
        # disabling the adaptive gate reverts to the absolute gate only
        cfg["unusual_drop_sigma"] = 0
        unusual, _ = cold_front.is_unusual(p, series, cfg)
        self.assertFalse(unusual)

    def test_rain_signal_from_post_frontal_precip(self):
        _, series = _front_series()
        series = dict(series)
        n = len(series["temperature_2m"])
        precip = [0.0] * n
        self.assertEqual(cold_front.rain_signal_mm(
            {**series, "precipitation": precip}, 60), 0.0)
        for j in range(62, 68):
            precip[j] = 0.4
        self.assertAlmostEqual(cold_front.rain_signal_mm(
            {**series, "precipitation": precip}, 60), 2.4)
        # pre-frontal rain does not count
        self.assertEqual(cold_front.rain_signal_mm(
            {**series, "precipitation": [1.0] * 60 + [0.0] * (n - 60)}, 60),
            0.0)
        # missing variable: gate closed, never an error
        self.assertEqual(cold_front.rain_signal_mm(series, 60), 0.0)


# --------------------------------------------------------------------------- #
# evaluator hook: flag, cooldown, record shape
# --------------------------------------------------------------------------- #

class _Loc:
    name = "LOC-CT"
    label = "Cape Town"
    latitude = -33.9
    longitude = 18.5


class TestEvaluateCell(unittest.TestCase):
    def setUp(self):
        import frappe
        self.frappe = frappe
        frappe.conf = {}
        frappe.get_all = MagicMock(return_value=[])
        self.inserted = []

        def get_doc(doc):
            self.inserted.append(doc)
            m = MagicMock()
            m.insert.return_value = types.SimpleNamespace(name="SWW-2017-1")
            return m

        frappe.get_doc = MagicMock(side_effect=get_doc)
        frappe.cache = MagicMock()
        frappe.cache.return_value.get_value.return_value = None
        frappe.log_error = MagicMock()
        self.times, self.series = _front_series()
        self.horizon = self.times[-1]
        self.now = self.horizon + dt.timedelta(hours=2)

    def test_issues_one_advisory_record(self):
        out = cold_front.evaluate_cell(_Loc(), self.series, self.times,
                                       self.horizon, self.now, 45.0)
        self.assertTrue(out.startswith("issued:"), out)
        self.assertEqual(len(self.inserted), 1)
        doc = self.inserted[0]
        self.assertEqual(doc["event_class"], "cold_front")
        self.assertEqual(doc["severity"], "advisory")
        self.assertEqual(doc["status"], "active")
        self.assertNotIn("warning", doc["headline"].lower())
        self.assertNotIn("warning", doc["message"].lower())
        pre = json.loads(doc["precursors"])
        self.assertEqual(pre["mode"], propagation.FRONT_DETECTION_MODE)
        self.assertEqual(pre["steering_deg"], 45.0)
        self.assertIsNotNone(pre["steering_speed_ms"])
        self.assertIn("unusual", pre)
        self.assertIn("rain_signal", pre)

    def test_wet_unusual_front_issues_scaled_copy(self):
        series = dict(self.series)
        n = len(series["temperature_2m"])
        # sharper drop than the absolute gate + post-frontal rain
        series["temperature_2m"] = [
            t if i < 60 else 18.0 - 10.0 for i, t in
            enumerate(series["temperature_2m"])]
        series["precipitation"] = [0.0] * 62 + [0.5] * (n - 62)
        out = cold_front.evaluate_cell(_Loc(), series, self.times,
                                       self.horizon, self.now, 45.0)
        self.assertTrue(out.startswith("issued:"), out)
        doc = self.inserted[0]
        self.assertIn("unusual for this area", doc["message"])
        self.assertTrue(doc["message"].endswith("Some rain may follow."))
        self.assertEqual(doc["severity"], "advisory")
        pre = json.loads(doc["precursors"])
        self.assertTrue(pre["unusual"])
        self.assertTrue(pre["rain_signal"])
        self.assertGreater(pre["post_precip_mm"], 1.0)

    def test_master_flag_disables(self):
        self.frappe.conf = {"severe_weather_cold_front": "off"}
        out = cold_front.evaluate_cell(_Loc(), self.series, self.times,
                                       self.horizon, self.now)
        self.assertEqual(out, "disabled")
        self.assertEqual(self.inserted, [])

    def test_default_is_on(self):
        self.assertTrue(cold_front.cold_front_enabled())

    def test_cooldown_blocks_reissue(self):
        self.frappe.get_all = MagicMock(return_value=[{"name": "SWW-2017-1"}])
        out = cold_front.evaluate_cell(_Loc(), self.series, self.times,
                                       self.horizon, self.now)
        self.assertEqual(out, "cooldown")
        self.assertEqual(self.inserted, [])
        # cooldown window is the config default (72 h)
        kwargs = self.frappe.get_all.call_args.kwargs
        cutoff = kwargs["filters"]["issued_at"][1]
        self.assertEqual(self.now - cutoff, dt.timedelta(hours=72))

    def test_stale_passage_is_not_issued(self):
        # pretend the horizon is 3 days past the passage
        horizon = self.times[-1] + dt.timedelta(hours=72)
        out = cold_front.evaluate_cell(_Loc(), self.series, self.times,
                                       horizon, self.now)
        self.assertEqual(out, "stale")

    def test_no_front_no_record(self):
        times, series = _front_series(passage=10 ** 6)  # never fronts
        out = cold_front.evaluate_cell(_Loc(), series, times,
                                       times[-1], self.now)
        self.assertEqual(out, "no_passage")
        self.assertEqual(self.inserted, [])

    def test_never_raises(self):
        out = cold_front.evaluate_cell(_Loc(), {}, [], None, self.now)
        self.assertEqual(out, "error")


# --------------------------------------------------------------------------- #
# propagation: projection, timing, cone, no-consensus, no chains
# --------------------------------------------------------------------------- #

class TestFrontPropagation(unittest.TestCase):
    def _grid(self):
        return [loc("coast", 0, 0, "Cape Town"),
                loc("downwind", 0, 100, "Worcester"),
                loc("upwind", 0, -100, "Atlantic")]

    def test_projects_only_into_the_downwind_cone(self):
        plan = propagation.plan_propagation(
            self._grid(), [front_record("F1", "coast", steering=90.0)])
        targets = {a.target for a in plan.advisories}
        self.assertEqual(targets, {"downwind"})
        adv = plan.advisories[0]
        self.assertEqual(adv.event_class, "cold_front")
        self.assertEqual(adv.gating, "directional")
        self.assertNotIn("warning", adv.message.lower())
        self.assertIn("Cooler, windier weather", adv.message)

    def test_timing_word_from_speed_and_distance(self):
        # 100 km at 15 m/s (54 km/h) -> ~1.9 h -> "in the next few hours"
        plan = propagation.plan_propagation(
            self._grid(), [front_record("F1", "coast", speed=15.0)])
        self.assertIn("in the next few hours", plan.advisories[0].message)
        # 100 km at 2 m/s (7.2 km/h) -> ~14 h -> "later today"
        plan = propagation.plan_propagation(
            self._grid(), [front_record("F1", "coast", speed=2.0)])
        self.assertIn("later today", plan.advisories[0].message)

    def test_timing_falls_back_to_soon_without_speed(self):
        plan = propagation.plan_propagation(
            self._grid(), [front_record("F1", "coast", speed=None)])
        self.assertIn("may reach you soon", plan.advisories[0].message)

    def test_timing_phrase_buckets(self):
        self.assertEqual(propagation.front_timing_phrase(100, None), "soon")
        self.assertEqual(propagation.front_timing_phrase(100, 0.5), "soon")
        self.assertEqual(propagation.front_timing_phrase(100, 15.0),
                         "in the next few hours")
        self.assertEqual(propagation.front_timing_phrase(500, 10.0),
                         "later today")
        self.assertEqual(propagation.front_timing_phrase(1000, 10.0),
                         "tomorrow")
        self.assertEqual(propagation.front_timing_phrase(4000, 10.0),
                         "in the coming days")

    def test_projected_advisories_never_chain(self):
        # apply the plan, then plan again: the projected advisory at
        # "downwind" must not seed a further advisory at a cell beyond it
        grid = self._grid() + [loc("far", 0, 200, "Robertson")]
        warnings = [front_record("F1", "coast", steering=90.0)]
        plan = propagation.plan_propagation(grid, warnings)
        state = propagation.apply_plan(warnings, plan)
        plan2 = propagation.plan_propagation(grid, state)
        self.assertTrue(plan2.is_empty(),
                        (plan2.advisories, plan2.expiries, plan2.escalations))

    def test_own_detection_outranks_projected_advisory(self):
        warnings = [front_record("F1", "coast", steering=90.0)]
        grid = self._grid()
        state = propagation.apply_plan(
            warnings, propagation.plan_propagation(grid, warnings))
        # the front then arrives at "downwind": its own detection appears
        state.append(front_record("F2", "downwind", steering=90.0))
        plan = propagation.plan_propagation(grid, state)
        expired = {e.name for e in plan.expiries}
        self.assertIn("ADV-downwind-cold_front", expired)

    def test_cold_front_never_counts_toward_consensus(self):
        # 5 cells all holding first-hand cold-front detections within the
        # basin radius: no escalation may be planned
        grid = [loc(f"c{i}", 0, i * 50) for i in range(5)]
        warnings = [front_record(f"F{i}", f"c{i}") for i in range(5)]
        plan = propagation.plan_propagation(grid, warnings,
                                            {"consensus_k": 2})
        self.assertEqual(plan.escalations, [])

    def test_projection_mirrors_unusual_and_rain_flags(self):
        rec = front_record("F1", "coast", steering=90.0, speed=15.0)
        pre = json.loads(rec["precursors"])
        pre.update({"unusual": True, "rain_signal": True})
        rec["precursors"] = json.dumps(pre)
        plan = propagation.plan_propagation(self._grid(), [rec])
        msg = plan.advisories[0].message
        self.assertIn("unusual for this time of year", msg)
        self.assertIn("Noticeably colder", msg)
        self.assertTrue(msg.endswith("Some rain may follow."))
        self.assertNotIn("warning", msg.lower())
        adv_pre = json.loads(plan.advisories[0].precursors)
        self.assertTrue(adv_pre["unusual"])
        self.assertTrue(adv_pre["rain_signal"])

    def test_projection_ordinary_source_keeps_plain_line_no_rain(self):
        plan = propagation.plan_propagation(
            self._grid(), [front_record("F1", "coast")])
        msg = plan.advisories[0].message
        self.assertIn("Cooler, windier weather", msg)
        self.assertNotIn("unusual", msg.lower())
        self.assertNotIn("rain", msg.lower())

    def test_storm_advisory_behavior_is_unchanged(self):
        # a real heads_up storm still projects exactly as before
        storm = {
            "name": "W1", "watch_location": "coast",
            "event_class": "destructive_wind", "severity": "heads_up",
            "status": "active", "onset": dt.datetime(2017, 6, 7, 0),
            "valid_until": dt.datetime(2017, 6, 8, 0), "headline": "hl",
            "message": "msg",
            "precursors": json.dumps({"steering_deg": 90.0,
                                      "confidence": 0.6}),
        }
        plan = propagation.plan_propagation(self._grid(), [storm])
        self.assertEqual({a.target for a in plan.advisories}, {"downwind"})
        self.assertEqual(plan.advisories[0].event_class, "destructive_wind")


# --------------------------------------------------------------------------- #
# exclusions: push, fusion
# --------------------------------------------------------------------------- #

class TestExclusions(unittest.TestCase):
    def test_push_refuses_the_advisory_severity(self):
        import frappe
        frappe.conf = {"severe_weather_push_enabled": 1}
        out = push._notify("SWW-1", "LOC-CT", "cold_front",
                           {"severity": "advisory", "headline": "h",
                            "message": "m"})
        self.assertEqual(out, "no_severity")

    def test_push_rank_of_advisory_is_zero(self):
        self.assertEqual(push._SEVERITY_RANK.get("advisory", 0), 0)

    def test_fusion_ignores_the_class(self):
        import frappe
        frappe.conf = {}
        sev, rendered, meta = fusion.fuse_warning(
            _Loc(), "cold_front", "advisory", 0.9,
            dt.datetime(2017, 6, 7, 12))
        self.assertEqual(sev, "advisory")
        self.assertIsNone(meta)
        self.assertNotIn("cold_front", fusion.RAIN_CLASSES)
        self.assertNotIn("cold_front", fusion.WIND_CLASSES)

    def test_climatology_ignores_the_class(self):
        climatology = importlib.import_module("wmod.control.warnings_engine.climatology")
        self.assertNotIn("cold_front", climatology.RAIN_CLASSES)


if __name__ == "__main__":
    unittest.main()
