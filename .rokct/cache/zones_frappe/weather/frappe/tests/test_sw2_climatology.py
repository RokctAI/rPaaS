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

"""Offline tests for the seasonal-climatology baselines (wave 2).

Synthetic data only - no network, no bench. Frappe is stubbed exactly like
test_warnings_engine.py. Covers: calendar-week bucketing, weekly aggregation
with gaps, normals construction, the percentile / wetness-rank /
out-of-season-factor math, the bounded confidence annotation, the calm copy
note (legal wording constraint), the config flag, and the non-interference
contract (frozen detector rules byte-identical, seasonal context never an
input to the detector).
"""

import datetime as dt
import hashlib
import importlib
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

import numpy as np

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FRAPPE_MODULE_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
COMMON_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "warnings_engine")
ENGINE_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "control", "warnings_engine")


def _ensure_frappe_stub():
    try:
        import frappe  # noqa: F401
        return
    except ImportError:
        pass
    frappe_mod = types.ModuleType("frappe")
    utils_mod = types.ModuleType("frappe.utils")
    utils_mod.cint = lambda v: int(float(v or 0))
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
climatology = importlib.import_module("wmod.control.warnings_engine.climatology")
detector = importlib.import_module("wmod.control.warnings_engine.detector")


# --------------------------------------------------------------------------- #
# synthetic-world helpers
# --------------------------------------------------------------------------- #

def synthetic_year(year: int, wet_center_week: float = 2.0,
                   base_tcwv: float = 30.0, rng=None):
    """One year of hourly (precipitation, tcwv) with a sinusoidal wet season.

    Wet season peaks at `wet_center_week` (default ~mid-January, i.e. a
    southern-hemisphere summer-rain cell); driest weeks near week 28.
    """
    hours = 8784 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 8760
    week = np.minimum((np.arange(hours) // 24) // 7, 51)
    phase = 2.0 * np.pi * (week - wet_center_week) / 52.0
    seasonal = 0.5 * (1.0 + np.cos(phase))          # 1 at wet peak, 0 at dry
    rng = rng or np.random.default_rng(year)
    precip = seasonal * 0.12 * rng.random(hours)    # mm/h, wet-season heavy
    tcwv = base_tcwv + 15.0 * seasonal + rng.normal(0.0, 1.0, hours)
    return precip, tcwv


class SyntheticSource:
    """WarningsDataSource stand-in serving the synthetic world."""

    name = "synthetic"

    def __init__(self):
        self.calls = 0

    def hourly_series(self, latitude, longitude, variables, start_utc, end_utc):
        self.calls += 1
        year = start_utc.year
        precip, tcwv = synthetic_year(year)
        n = int((end_utc - start_utc).total_seconds() // 3600)
        return {
            "precipitation": precip[:n],
            "total_column_integrated_water_vapour": tcwv[:n],
        }


def synthetic_normals():
    src = SyntheticSource()
    return climatology.compute_cell_normals(
        src, -23.0, 30.5, years=tuple(range(1940, 2022, 3)))


def make_window(precip_mm_per_h: float, tcwv: float, hours: int = 408):
    return {
        "precipitation": np.full(hours, precip_mm_per_h),
        "total_column_integrated_water_vapour": np.full(hours, tcwv),
    }


# --------------------------------------------------------------------------- #
# calendar-week bucketing + aggregation
# --------------------------------------------------------------------------- #

class TestWeekOf(unittest.TestCase):
    def test_year_boundaries(self):
        self.assertEqual(climatology.week_of(dt.datetime(2025, 1, 1)), 0)
        self.assertEqual(climatology.week_of(dt.datetime(2025, 1, 7)), 0)
        self.assertEqual(climatology.week_of(dt.datetime(2025, 1, 8)), 1)
        self.assertEqual(climatology.week_of(dt.datetime(2025, 12, 31)), 51)

    def test_day_365_folds_into_week_51(self):
        # leap year day-of-year 365 (Dec 31) would be week 52 -> capped
        self.assertEqual(climatology.week_of(dt.datetime(2024, 12, 31)), 51)
        self.assertEqual(climatology.week_of(dt.datetime(2024, 12, 25)), 51)


class TestWeeklyMean(unittest.TestCase):
    def test_constant_series(self):
        m = climatology.weekly_mean(np.full(8760, 0.5))
        self.assertEqual(m.shape, (52,))
        self.assertTrue(np.allclose(m, 0.5))

    def test_gap_normalization(self):
        x = np.full(8760, 2.0)
        x[168:168 + 30] = np.nan          # 30 missing hours in week 1: kept
        m = climatology.weekly_mean(x)
        self.assertAlmostEqual(m[1], 2.0)

    def test_sparse_week_dropped(self):
        x = np.full(8760, 2.0)
        x[168:336 - 20] = np.nan          # week 1 has only 20/168 finite hours
        m = climatology.weekly_mean(x)
        self.assertTrue(np.isnan(m[1]))
        self.assertAlmostEqual(m[0], 2.0)

    def test_leap_year_length_accepted(self):
        m = climatology.weekly_mean(np.full(8784, 1.0))
        self.assertTrue(np.allclose(m, 1.0))


# --------------------------------------------------------------------------- #
# normals construction
# --------------------------------------------------------------------------- #

class TestNormals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.normals = synthetic_normals()

    def test_structure_and_schema(self):
        n = self.normals
        self.assertEqual(n["version"], climatology.SCHEMA_VERSION)
        self.assertEqual(len(n["weeks"]), 52)
        self.assertEqual(len(n["years_sampled"]), 28)
        for wk in n["weeks"]:
            self.assertIsNotNone(wk["precip_mm"])
            self.assertIsNotNone(wk["tcwv"])
            p = wk["precip_mm"]
            self.assertLessEqual(p["median"], p["p75"])
            self.assertLessEqual(p["p75"], p["p90"])
            self.assertLessEqual(p["p90"], p["p99"])
            self.assertGreaterEqual(p["n"], climatology.MIN_YEAR_SAMPLES)

    def test_seasonal_cycle_recovered(self):
        weeks = self.normals["weeks"]
        wet = weeks[2]["precip_mm"]["median"]     # wet-season peak week
        dry = weeks[28]["precip_mm"]["median"]    # driest week
        self.assertGreater(wet, 5.0 * max(dry, 0.01))
        self.assertGreater(weeks[2]["tcwv"]["mean"], weeks[28]["tcwv"]["mean"])

    def test_sparse_years_yield_null_week(self):
        p = np.full((10, 52), 100.0)              # only 10 year samples
        t = np.full((10, 52), 30.0)
        weeks = climatology.normals_from_samples(p, t)
        self.assertIsNone(weeks[0]["precip_mm"])
        self.assertIsNone(weeks[0]["tcwv"])


# --------------------------------------------------------------------------- #
# feature math
# --------------------------------------------------------------------------- #

class TestPercentile(unittest.TestCase):
    NORMAL = {"median": 20.0, "p75": 40.0, "p90": 80.0, "p99": 160.0}

    def test_anchor_points(self):
        f = climatology.precip_percentile
        self.assertEqual(f(0.0, self.NORMAL), 0.0)
        self.assertAlmostEqual(f(20.0, self.NORMAL), 0.50)
        self.assertAlmostEqual(f(40.0, self.NORMAL), 0.75)
        self.assertAlmostEqual(f(80.0, self.NORMAL), 0.90)
        self.assertAlmostEqual(f(160.0, self.NORMAL), 0.99)
        self.assertAlmostEqual(f(500.0, self.NORMAL), 0.99)  # flat beyond p99

    def test_monotone(self):
        vals = [climatology.precip_percentile(v, self.NORMAL)
                for v in np.linspace(0, 200, 100)]
        self.assertTrue(all(b >= a for a, b in zip(vals, vals[1:])))

    def test_bone_dry_week(self):
        dry = {"median": 0.0, "p75": 0.0, "p90": 0.0, "p99": 0.0}
        self.assertEqual(climatology.precip_percentile(0.0, dry), 0.0)
        self.assertEqual(climatology.precip_percentile(5.0, dry), 0.99)

    def test_zero_median_still_interpolates(self):
        n = {"median": 0.0, "p75": 10.0, "p90": 30.0, "p99": 90.0}
        self.assertAlmostEqual(climatology.precip_percentile(10.0, n), 0.75)
        self.assertGreater(climatology.precip_percentile(5.0, n), 0.0)


class TestWetnessAndOutOfSeason(unittest.TestCase):
    def test_ranks_span_0_to_1(self):
        weeks = synthetic_normals()["weeks"]
        ranks = climatology.week_wetness_ranks(weeks)
        self.assertEqual(len(ranks), 52)
        # wet-peak week ranks near 1, driest near 0
        self.assertGreater(ranks[2], 0.9)
        self.assertLess(ranks[28], 0.1)

    def test_all_tied_cell_midranks(self):
        weeks = [{"week": w, "precip_mm": {"median": 0.0, "p75": 0.0,
                                           "p90": 0.0, "p99": 0.0},
                  "tcwv": None} for w in range(52)]
        ranks = climatology.week_wetness_ranks(weeks)
        self.assertTrue(all(abs(r - 0.5) < 1e-9 for r in ranks))

    def test_same_rain_scores_higher_in_dry_week(self):
        f = climatology.out_of_season_factor
        self.assertGreater(f(0.95, 0.05, 60.0), f(0.95, 0.95, 60.0))
        self.assertAlmostEqual(f(0.95, 0.0, 60.0), 0.95)

    def test_drizzle_and_unknown_rank_are_zero(self):
        f = climatology.out_of_season_factor
        self.assertEqual(f(0.99, 0.0, climatology.MIN_RAIN_MM_7D - 1), 0.0)
        self.assertEqual(f(0.99, None, 60.0), 0.0)
        self.assertEqual(f(0.99, 0.0, float("nan")), 0.0)


class TestSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.normals = synthetic_normals()

    def test_wet_spell_in_dry_season(self):
        horizon = dt.datetime(2020, 7, 15)        # week 27: dry season
        snap = climatology.seasonal_snapshot(
            self.normals, make_window(0.5, 55.0), horizon)
        self.assertEqual(snap["week"], climatology.week_of(horizon))
        self.assertAlmostEqual(snap["precip_7d_mm"], 84.0)
        self.assertGreaterEqual(snap["precip_pctl"], 0.95)
        self.assertGreaterEqual(snap["out_of_season_factor"], 0.85)
        self.assertGreater(snap["tcwv_z"], 2.0)

    def test_same_spell_in_wet_season_scores_low_factor(self):
        snap = climatology.seasonal_snapshot(
            self.normals, make_window(0.5, 45.0), dt.datetime(2021, 1, 15))
        self.assertLessEqual(snap["out_of_season_factor"], 0.2)

    def test_calm_dry_week_is_all_zero(self):
        snap = climatology.seasonal_snapshot(
            self.normals, make_window(0.0, 30.0), dt.datetime(2020, 7, 15))
        self.assertEqual(snap["precip_pctl"], 0.0)
        self.assertEqual(snap["out_of_season_factor"], 0.0)

    def test_insufficient_current_data_degrades_to_none(self):
        window = {
            "precipitation": np.full(408, np.nan),
            "total_column_integrated_water_vapour": np.full(408, np.nan),
        }
        self.assertIsNone(climatology.seasonal_snapshot(
            self.normals, window, dt.datetime(2020, 7, 15)))


# --------------------------------------------------------------------------- #
# bounded fusion outputs
# --------------------------------------------------------------------------- #

class TestBoundedBoost(unittest.TestCase):
    def snap(self, oos, pctl):
        return {"out_of_season_factor": oos, "precip_pctl": pctl,
                "tcwv_z": 0.0}

    def test_bound_is_absolute(self):
        b = climatology.bounded_confidence_boost(0.60, self.snap(1.0, 0.99))
        self.assertAlmostEqual(b, 0.60 + climatology.MAX_CONFIDENCE_BOOST)
        self.assertEqual(
            climatology.bounded_confidence_boost(0.95, self.snap(1.0, 0.99)), 1.0)

    def test_no_snapshot_no_boost(self):
        self.assertEqual(climatology.bounded_confidence_boost(0.6, None), 0.6)

    def test_no_anomaly_no_boost(self):
        self.assertEqual(
            climatology.bounded_confidence_boost(0.6, self.snap(0.0, 0.5)), 0.6)

    def test_beyond_p90_exceedance_drives_boost(self):
        low = climatology.bounded_confidence_boost(0.6, self.snap(0.0, 0.90))
        high = climatology.bounded_confidence_boost(0.6, self.snap(0.0, 0.99))
        self.assertEqual(low, 0.6)
        self.assertGreater(high, low)


class TestSeasonalNote(unittest.TestCase):
    def test_note_selection(self):
        note = climatology.seasonal_note(
            {"out_of_season_factor": 0.7, "precip_pctl": 0.8})
        self.assertIn("unusual for this time of year", note)
        note2 = climatology.seasonal_note(
            {"out_of_season_factor": 0.1, "precip_pctl": 0.97})
        self.assertIsNotNone(note2)
        self.assertIsNone(climatology.seasonal_note(
            {"out_of_season_factor": 0.1, "precip_pctl": 0.5}))
        self.assertIsNone(climatology.seasonal_note(None))

    def test_legal_wording_constraint(self):
        for snap in ({"out_of_season_factor": 0.9, "precip_pctl": 0.99},
                     {"out_of_season_factor": 0.0, "precip_pctl": 0.99}):
            note = climatology.seasonal_note(snap)
            low = note.lower()
            self.assertNotIn("warning", low)
            for banned in ("yellow", "orange", "red", "level"):
                self.assertNotIn(banned, low)


# --------------------------------------------------------------------------- #
# config flag + non-interference contract
# --------------------------------------------------------------------------- #

class TestFlagAndNonInterference(unittest.TestCase):
    def test_flag_default_on_and_off_values(self):
        import frappe
        original = dict(frappe.conf) if isinstance(frappe.conf, dict) else {}
        try:
            frappe.conf = {}
            self.assertTrue(climatology.is_enabled())
            for off in ("0", "false", "No", " OFF "):
                frappe.conf = {climatology.CONFIG_FLAG: off}
                self.assertFalse(climatology.is_enabled())
            frappe.conf = {climatology.CONFIG_FLAG: "1"}
            self.assertTrue(climatology.is_enabled())
        finally:
            frappe.conf = original

    def test_frozen_config_untouched(self):
        with open(detector.config_path(), "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(digest, detector.CONFIG_SHA256)

    def test_frozen_rules_reference_no_seasonal_features(self):
        rules = detector.load_rules()
        seasonal_names = {"precip_pctl", "tcwv_z", "out_of_season_factor",
                          "seasonal", "climatology"}
        for rule in rules.values():
            for cond in rule.conditions:
                self.assertNotIn(cond.feature, seasonal_names)

    def test_seasonal_context_never_raises(self):
        class ExplodingSource:
            name = "boom"

            def hourly_series(self, *a, **k):
                raise RuntimeError("network down")

        loc = types.SimpleNamespace(name="-23.00,30.50",
                                    latitude=-23.0, longitude=30.5)
        result = climatology.seasonal_context(
            ExplodingSource(), loc, make_window(0.1, 30.0),
            dt.datetime(2020, 7, 15))
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
