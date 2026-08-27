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

"""Offline tests for the basin-routing upstream-flood signal (wave 5).

Fixture basin maps only - no network, no bench. Frappe is stubbed exactly
like the sibling sw2 tests. Covers: artifact loading (fail-closed on
missing/corrupt files), grid-key math, upstream traversal on a synthetic
river chain, distance-banded sample selection, gap-tolerant accumulation
(incl. numpy scalars), area-weighted signal math, every tier arm and its
boundaries, validity clamping, the calm-copy legal constraint for the new
upstream_flood class, the evaluate_cell record lifecycle (create, refresh,
expire, fail-closed, never-raise), the propagation-pass class gate, and
the integrity of the committed real artifact (basin_map.json).
"""

import datetime as dt
import importlib
import importlib.util
import json
import math
import os
import sys
import tempfile
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
    _ensure_frappe_stub()
    for name in ("wmod", "wmod.control"):
        if name not in sys.modules:
            parent = types.ModuleType(name)
            parent.__path__ = []
            sys.modules[name] = parent
    _load_pkg("wmod.warnings_engine", COMMON_DIR)
    return _load_pkg("wmod.control.warnings_engine", ENGINE_DIR)


_load_engine()
basin = importlib.import_module("wmod.control.warnings_engine.basin")
messages = importlib.import_module("wmod.warnings_engine.messages")
propagation = importlib.import_module("wmod.control.warnings_engine.propagation")


# --------------------------------------------------------------------------- #
# fixture world: a three-link river chain plus an unrelated basin
#
#   A (dist 300 km) --> B (dist 150 km) --> C (dist 0, the watch cell's
#   sub-basin) ; X is another basin entirely.
# --------------------------------------------------------------------------- #

# subbasin row: [next_down, main_bas, dist_main_km, sub_area_km2,
#                up_area_km2, rep_lat_idx, rep_lon_idx]
FIXTURE = {
    "version": 1,
    "subbasins": {
        "1": [2, 3, 300.0, 2500.0, 2500.0, 362, 720],
        "2": [3, 3, 150.0, 3000.0, 5500.0, 361, 720],
        "3": [0, 3, 0.0, 1000.0, 6500.0, 360, 720],
        "9": [0, 9, 0.0, 4000.0, 4000.0, 350, 700],
    },
    "cells": {
        "362_720": 1,   # cell in A
        "361_720": 2,   # cell in B
        "360_720": 3,   # the watch cell (C)
        "350_700": 9,   # unrelated basin
    },
}


def fixture_map():
    """Write the fixture to a temp file and load it through load_map (so
    the index building and validation paths are exercised too)."""
    tmp = tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, newline="\n")
    json.dump(FIXTURE, tmp)
    tmp.close()
    art = basin.load_map(tmp.name)
    os.unlink(tmp.name)
    assert art is not None
    return art


def cfg_with(**over):
    cfg = dict(basin.DEFAULTS)
    cfg.update(over)
    return cfg


class FakeSource:
    """WarningsDataSource stand-in: rain at a constant rate over the LAST
    72 h only (so the 72 h and 168 h accumulations are equal and each tier
    arm can be exercised in isolation)."""

    name = "fake"

    def __init__(self, mm_per_h=1.0):
        self.mm_per_h = mm_per_h
        self.calls = []

    def hourly_series(self, lat, lon, variables, start, end):
        n = int((end - start).total_seconds() // 3600)
        self.calls.append((lat, lon, n))
        head = [0.0] * max(n - 72, 0)
        return {"precipitation": head + [self.mm_per_h] * min(n, 72)}


class RaisingSource:
    name = "raising"

    def hourly_series(self, *a, **k):
        raise RuntimeError("boom")


class Loc(dict):
    """frappe._dict-alike: attribute AND .get access."""

    __getattr__ = dict.__getitem__


def watch_loc():
    return Loc(name="360_720", latitude=0.0, longitude=0.0, label="Riverton")


class _CacheStub:
    def __init__(self):
        self.store = {}

    def get_value(self, key):
        return self.store.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.store[key] = value


def _fresh_frappe():
    """Reset the stubbed frappe module for one lifecycle test."""
    import frappe
    frappe.conf = {}
    frappe.db = MagicMock()
    frappe.db.get_value = MagicMock(return_value=None)
    cache = _CacheStub()
    frappe.cache = lambda: cache
    inserted = MagicMock()
    inserted.insert.return_value = MagicMock(name="rec")
    inserted.insert.return_value.name = "SWW-1"
    frappe.get_doc = MagicMock(return_value=inserted)
    frappe.log_error = MagicMock()
    return frappe


def _use_fixture_as_default(art):
    """Make load_map() (no args) serve the fixture."""
    basin._map_cache.update(path=basin.default_map_path(), map=art,
                            failed=False)


def _reset_map_cache():
    basin._map_cache.update(path=None, map=None, failed=False)


# --------------------------------------------------------------------------- #
# artifact loading
# --------------------------------------------------------------------------- #

class TestLoadMap(unittest.TestCase):
    def tearDown(self):
        _reset_map_cache()

    def test_missing_file_is_none_and_remembered(self):
        self.assertIsNone(basin.load_map("/nonexistent/basin_map.json"))
        # cached as failed - a second call must not re-raise or re-parse
        self.assertIsNone(basin.load_map("/nonexistent/basin_map.json"))

    def test_corrupt_file_is_none(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        tmp.write("{not json")
        tmp.close()
        self.assertIsNone(basin.load_map(tmp.name))
        os.unlink(tmp.name)

    def test_wrong_version_is_none(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump({"version": 99, "subbasins": {}, "cells": {}}, tmp)
        tmp.close()
        self.assertIsNone(basin.load_map(tmp.name))
        os.unlink(tmp.name)

    def test_fixture_loads_and_builds_upstream_index(self):
        art = fixture_map()
        self.assertIn("_upstream_index", art)
        self.assertEqual(sorted(art["_upstream_index"]["3"]), ["2"])
        self.assertEqual(art["_upstream_index"]["2"], ["1"])

    def test_committed_real_artifact_integrity(self):
        """The committed basin_map.json loads, and the Limpopo case-study
        cells are mapped with musina upstream of chokwe (the artifact's
        load-bearing fact for the 1977/2000 validation)."""
        art = basin.load_map()
        self.assertIsNotNone(art, "committed basin_map.json failed to load")
        self.assertEqual(art["version"], 1)
        self.assertIn("license", art["source"])
        self.assertIn("citation", art["source"])
        chokwe = basin.cell_key(-24.53, 32.98)
        musina = basin.cell_key(-22.35, 30.03)
        self.assertIn(chokwe, art["cells"])
        self.assertIn(musina, art["cells"])
        ups = basin.upstream_subbasins(art, chokwe, 1500.0)
        up_ids = {u["hybas_id"] for u in ups}
        self.assertIn(art["cells"][musina], up_ids)
        area = sum(u["sub_area_km2"] for u in ups)
        self.assertGreater(area, 100000.0)  # the Limpopo above Chokwe


class TestGridKeys(unittest.TestCase):
    def test_cell_key_join_discipline(self):
        self.assertEqual(basin.cell_key(0.0, 0.0), "360_720")
        self.assertEqual(basin.cell_key(-90.0, -180.0), "0_0")
        self.assertEqual(basin.cell_key(-24.53, 32.98), "262_852")

    def test_key_latlon_roundtrip(self):
        self.assertEqual(basin.key_latlon("360_720"), (0.0, 0.0))
        la, lo = basin.key_latlon(basin.cell_key(-22.35, 30.03))
        self.assertAlmostEqual(la, -22.25)
        self.assertAlmostEqual(lo, 30.0)


# --------------------------------------------------------------------------- #
# upstream traversal + selection
# --------------------------------------------------------------------------- #

class TestUpstream(unittest.TestCase):
    def setUp(self):
        self.art = fixture_map()

    def tearDown(self):
        _reset_map_cache()

    def test_chain_traversal_excludes_own_subbasin(self):
        ups = basin.upstream_subbasins(self.art, "360_720", 1500.0)
        self.assertEqual([u["hybas_id"] for u in ups], [2, 1])
        self.assertEqual([u["delta_km"] for u in ups], [150.0, 300.0])

    def test_unmapped_cell_is_empty(self):
        self.assertEqual(basin.upstream_subbasins(self.art, "0_0", 1500.0), [])

    def test_headwater_cell_has_no_upstream(self):
        self.assertEqual(
            basin.upstream_subbasins(self.art, "362_720", 1500.0), [])

    def test_unrelated_basin_is_not_upstream(self):
        ups = basin.upstream_subbasins(self.art, "360_720", 1500.0)
        self.assertNotIn(9, [u["hybas_id"] for u in ups])

    def test_max_dist_caps_traversal(self):
        ups = basin.upstream_subbasins(self.art, "360_720", 200.0)
        self.assertEqual([u["hybas_id"] for u in ups], [2])

    def test_select_points_merges_and_weights(self):
        ups = basin.upstream_subbasins(self.art, "360_720", 1500.0)
        pts = basin.select_points(ups, cfg_with())
        self.assertEqual(len(pts), 2)
        self.assertEqual(pts[0]["key"], "361_720")
        self.assertEqual(pts[0]["weight_km2"], 3000.0)
        self.assertEqual(pts[1]["delta_km"], 300.0)

    def test_select_points_respects_cap(self):
        many = [{"rep_key": f"3{i}_720", "delta_km": 10.0 * i,
                 "sub_area_km2": 100.0 + i, "up_area_km2": 0.0,
                 "hybas_id": i} for i in range(40)]
        pts = basin.select_points(many, cfg_with(max_points=5))
        self.assertLessEqual(len(pts), 5)


# --------------------------------------------------------------------------- #
# accumulation + signal + tiers
# --------------------------------------------------------------------------- #

class TestAccumulate(unittest.TestCase):
    def test_full_window(self):
        self.assertAlmostEqual(basin.accumulate([1.0] * 72, 72), 72.0)

    def test_short_series_is_none(self):
        self.assertIsNone(basin.accumulate([1.0] * 71, 72))

    def test_gap_scaling_and_floor(self):
        vals = [1.0] * 54 + [float("nan")] * 18   # exactly 75% finite
        self.assertAlmostEqual(basin.accumulate(vals, 72), 72.0)
        vals = [1.0] * 53 + [float("nan")] * 19   # below the floor
        self.assertIsNone(basin.accumulate(vals, 72))

    def test_numpy_scalars_are_accepted(self):
        import numpy as np
        vals = np.full(72, np.float32(0.5))
        self.assertAlmostEqual(basin.accumulate(vals, 72), 36.0, places=3)

    def test_none_entries_tolerated(self):
        vals = [1.0] * 60 + [None] * 12
        self.assertAlmostEqual(basin.accumulate(vals, 72), 72.0)


class TestSignal(unittest.TestCase):
    def points(self):
        return [
            {"key": "a", "lat": 0.0, "lon": 0.0, "weight_km2": 3000.0,
             "delta_km": 100.0},
            {"key": "b", "lat": 0.0, "lon": 0.25, "weight_km2": 1000.0,
             "delta_km": 500.0},
        ]

    def test_area_weighted_mean_and_lag(self):
        sig = basin.signal_from_accums(
            self.points(), {"a": (40.0, 80.0), "b": (80.0, 160.0)},
            9999.0, cfg_with())
        self.assertAlmostEqual(sig["rain_72h_mm"], 50.0)   # (3*40+1*80)/4
        self.assertAlmostEqual(sig["rain_168h_mm"], 100.0)
        # rain-weighted mean distance: (3000*40*100 + 1000*80*500) / (3000*40+1000*80)
        self.assertAlmostEqual(sig["mean_dist_km"], 260.0)
        self.assertAlmostEqual(sig["lag_hours"], 65.0)      # 260 / 4 km/h
        self.assertEqual(sig["upstream_area_km2"], 9999.0)
        self.assertEqual(len(sig["points"]), 2)

    def test_insufficient_coverage_is_none(self):
        # only the small point has data: 1000 of 4000 km2 < half the weight
        sig = basin.signal_from_accums(
            self.points(), {"b": (80.0, 160.0)}, 9999.0, cfg_with())
        self.assertIsNone(sig)

    def test_long_window_optional(self):
        sig = basin.signal_from_accums(
            self.points(), {"a": (40.0, None), "b": (80.0, None)},
            9999.0, cfg_with())
        self.assertIsNotNone(sig)
        self.assertIsNone(sig["rain_168h_mm"])


class TestTiers(unittest.TestCase):
    def sig(self, r72, r168=None):
        return {"rain_72h_mm": r72, "rain_168h_mm": r168}

    def test_none_signal(self):
        self.assertIsNone(basin.tier_for_signal(None, cfg_with()))
        self.assertIsNone(basin.tier_for_signal(self.sig(None), cfg_with()))

    def test_quiet(self):
        self.assertIsNone(basin.tier_for_signal(self.sig(10.0, 50.0), cfg_with()))

    def test_advisory_72h_arm(self):
        self.assertEqual(basin.tier_for_signal(self.sig(40.0), cfg_with()),
                         "advisory")

    def test_advisory_long_rain_arm(self):
        self.assertEqual(
            basin.tier_for_signal(self.sig(30.0, 100.0), cfg_with()),
            "advisory")
        self.assertIsNone(
            basin.tier_for_signal(self.sig(29.0, 100.0), cfg_with()))

    def test_heads_up(self):
        self.assertEqual(basin.tier_for_signal(self.sig(70.0), cfg_with()),
                         "heads_up")

    def test_warning_burst_arm(self):
        self.assertEqual(basin.tier_for_signal(self.sig(110.0), cfg_with()),
                         "warning")

    def test_warning_compound_arm(self):
        self.assertEqual(
            basin.tier_for_signal(self.sig(60.0, 120.0), cfg_with()),
            "warning")
        # either leg alone is not enough for warning (the long-rain arm
        # still yields the lower advisory tier for 60 mm on a wet basin)
        self.assertEqual(
            basin.tier_for_signal(self.sig(60.0, 119.0), cfg_with()),
            "advisory")
        self.assertEqual(
            basin.tier_for_signal(self.sig(75.0, 119.0), cfg_with()),
            "heads_up")

    def test_validity_clamps(self):
        self.assertEqual(basin.validity_hours({"lag_hours": 0}), 24)
        self.assertEqual(basin.validity_hours({"lag_hours": 60}), 84)
        self.assertEqual(basin.validity_hours({"lag_hours": 500}), 120)
        self.assertEqual(basin.validity_hours(None), 24)


# --------------------------------------------------------------------------- #
# copy (legal constraint)
# --------------------------------------------------------------------------- #

class TestCopy(unittest.TestCase):
    def test_renders_all_three_severities(self):
        for sev in ("advisory", "heads_up", "warning"):
            r = messages.render(basin.EVENT_CLASS, sev, "Chokwe")
            self.assertIn("Chokwe", r["headline"])
            self.assertTrue(r["message"])

    def test_no_user_facing_warning_word_or_taxonomy(self):
        for sev in ("advisory", "heads_up", "warning"):
            r = messages.render(basin.EVENT_CLASS, sev, "Chokwe")
            for text in (r["headline"], r["message"], r["severity_label"]):
                low = text.lower()
                self.assertNotIn("warning", low)
                for level in ("yellow", "orange", "red", "level "):
                    self.assertNotIn(level, low)

    def test_copy_says_dry_local_weather_is_possible(self):
        # the load-bearing product idea: the user may see NO rain at all
        for sev in ("advisory", "heads_up", "warning"):
            msg = messages.render(basin.EVENT_CLASS, sev, "X")["message"].lower()
            self.assertTrue("dry" in msg or "without rain" in msg, msg)

    def test_class_capped_at_warning(self):
        self.assertEqual(messages.cap_severity(basin.EVENT_CLASS, "warning"),
                         "warning")
        self.assertEqual(messages.cap_severity(basin.EVENT_CLASS, "advisory"),
                         "advisory")


# --------------------------------------------------------------------------- #
# evaluate_cell lifecycle (stubbed frappe)
# --------------------------------------------------------------------------- #

class TestEvaluateCell(unittest.TestCase):
    def setUp(self):
        self.frappe = _fresh_frappe()
        self.art = fixture_map()
        _use_fixture_as_default(self.art)
        self.horizon = dt.datetime(2026, 1, 10, 12)
        self.now = dt.datetime(2026, 1, 10, 14)

    def tearDown(self):
        _reset_map_cache()

    def test_heavy_upstream_rain_creates_record(self):
        # 1 mm/h everywhere -> 72 mm / 72 h upstream -> heads_up
        source = FakeSource(1.0)
        basin.evaluate_cell(source, watch_loc(), self.horizon, self.now)
        self.assertTrue(self.frappe.get_doc.called)
        doc = self.frappe.get_doc.call_args[0][0]
        self.assertEqual(doc["event_class"], "upstream_flood")
        self.assertEqual(doc["severity"], "heads_up")
        self.assertIn("Riverton", doc["headline"])
        pre = json.loads(doc["precursors"])
        self.assertEqual(pre["mode"], "basin_upstream")
        self.assertEqual(pre["tier"], "heads_up")
        self.assertAlmostEqual(pre["signal"]["rain_72h_mm"], 72.0)
        self.assertEqual(len(pre["signal"]["points"]), 2)

    def test_quiet_upstream_expires_existing_record(self):
        self.frappe.db.get_value = MagicMock(return_value="SWW-OLD")
        basin.evaluate_cell(FakeSource(0.0), watch_loc(), self.horizon, self.now)
        self.frappe.db.set_value.assert_called_with(
            "Severe Weather Warning", "SWW-OLD", {"status": "expired"})
        self.frappe.get_doc.assert_not_called()

    def test_refresh_updates_in_place(self):
        self.frappe.db.get_value = MagicMock(return_value="SWW-OLD")
        basin.evaluate_cell(FakeSource(1.0), watch_loc(), self.horizon, self.now)
        self.frappe.get_doc.assert_not_called()
        name, fields = self.frappe.db.set_value.call_args[0][1:3]
        self.assertEqual(name, "SWW-OLD")
        self.assertEqual(fields["status"], "active")
        self.assertEqual(fields["severity"], "heads_up")

    def test_no_map_is_a_silent_noop(self):
        basin._map_cache.update(path=basin.default_map_path(), map=None,
                                failed=True)
        basin.evaluate_cell(FakeSource(5.0), watch_loc(), self.horizon, self.now)
        self.frappe.get_doc.assert_not_called()
        self.frappe.db.set_value.assert_not_called()
        self.frappe.log_error.assert_not_called()

    def test_unmapped_cell_is_a_silent_noop(self):
        loc = Loc(name="0_0", latitude=-90.0, longitude=-180.0, label="Pole")
        basin.evaluate_cell(FakeSource(5.0), loc, self.horizon, self.now)
        self.frappe.get_doc.assert_not_called()

    def test_small_catchment_is_gated(self):
        art = json.loads(json.dumps(FIXTURE))
        for row in art["subbasins"].values():
            row[3] = 100.0  # every sub-basin tiny -> upstream area < gate
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(art, tmp)
        tmp.close()
        loaded = basin.load_map(tmp.name)
        os.unlink(tmp.name)
        _use_fixture_as_default(loaded)
        basin.evaluate_cell(FakeSource(5.0), watch_loc(), self.horizon, self.now)
        self.frappe.get_doc.assert_not_called()

    def test_master_switch_disables(self):
        self.frappe.conf = {"severe_weather_basin_enabled": "0"}
        basin.evaluate_cell(FakeSource(5.0), watch_loc(), self.horizon, self.now)
        self.frappe.get_doc.assert_not_called()

    def test_source_failure_never_raises_and_logs(self):
        basin.evaluate_cell(RaisingSource(), watch_loc(), self.horizon, self.now)
        self.assertTrue(self.frappe.log_error.called)
        self.frappe.get_doc.assert_not_called()

    def test_stale_horizon_expires_not_surfaces(self):
        # validity: lag ~ 1 day-ish -> horizon far in the past means the
        # episode may not surface as live
        old_horizon = self.now - dt.timedelta(days=30)
        self.frappe.db.get_value = MagicMock(return_value="SWW-OLD")
        basin.evaluate_cell(FakeSource(1.0), watch_loc(), old_horizon, self.now)
        self.frappe.db.set_value.assert_called_with(
            "Severe Weather Warning", "SWW-OLD", {"status": "expired"})

    def test_accum_cache_is_shared_across_calls(self):
        source = FakeSource(1.0)
        basin.evaluate_cell(source, watch_loc(), self.horizon, self.now)
        first = len(source.calls)
        self.frappe.db.get_value = MagicMock(return_value="SWW-1")
        basin.evaluate_cell(source, watch_loc(), self.horizon, self.now)
        self.assertEqual(len(source.calls), first)  # all served from cache

    def test_advisory_tier_is_not_pushed(self):
        push = importlib.import_module("wmod.warnings_engine.push")
        # 0.6 mm/h -> 43 mm/72h -> advisory
        called = []
        orig = push.notify_warning_upsert
        push.notify_warning_upsert = lambda *a, **k: called.append(a)
        try:
            basin.evaluate_cell(FakeSource(0.6), watch_loc(),
                                self.horizon, self.now)
        finally:
            push.notify_warning_upsert = orig
        self.assertTrue(self.frappe.get_doc.called)
        doc = self.frappe.get_doc.call_args[0][0]
        self.assertEqual(doc["severity"], "advisory")
        # the push module itself rank-gates advisory to a no-op; here we
        # only assert the hook was invoked with the advisory payload so the
        # gating stays push.py's single responsibility
        self.assertEqual(called[0][3]["severity"], "advisory")


# --------------------------------------------------------------------------- #
# propagation-pass class gate (fail-closed for unknown classes)
# --------------------------------------------------------------------------- #

class TestPropagationGate(unittest.TestCase):
    def test_upstream_flood_records_never_seed_or_crash_propagation(self):
        locs = [
            {"name": "L1", "latitude": 0.0, "longitude": 0.0, "label": "A"},
            {"name": "L2", "latitude": 0.5, "longitude": 0.0, "label": "B"},
        ]
        warnings = [{
            "name": "W1", "watch_location": "L1",
            "event_class": "upstream_flood", "severity": "heads_up",
            "status": "active", "onset": dt.datetime(2026, 1, 1),
            "valid_until": dt.datetime(2026, 1, 3), "headline": "h",
            "message": "m", "precursors": json.dumps({"mode": "basin_upstream"}),
        }]
        plan = propagation.plan_propagation(
            locs, warnings, {"enabled": 1, "consensus_k": 1})
        self.assertTrue(plan.is_empty())

    def test_known_classes_still_seed(self):
        locs = [
            {"name": "L1", "latitude": 0.0, "longitude": 0.0, "label": "A"},
            {"name": "L2", "latitude": 0.5, "longitude": 0.0, "label": "B"},
        ]
        warnings = [{
            "name": "W1", "watch_location": "L1", "event_class": "flood",
            "severity": "heads_up", "status": "active",
            "onset": dt.datetime(2026, 1, 1),
            "valid_until": dt.datetime(2026, 1, 3), "headline": "h",
            "message": "m", "precursors": json.dumps({}),
        }]
        plan = propagation.plan_propagation(locs, warnings, {"enabled": 1})
        self.assertEqual(len(plan.advisories), 1)


if __name__ == "__main__":
    unittest.main()
