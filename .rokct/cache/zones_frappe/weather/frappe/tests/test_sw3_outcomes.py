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

"""Offline tests for the automatic outcome ledger (sw3, outcomes.py).

Synthetic data only - no network, no bench. Frappe is stubbed exactly like
the other engine test files, with a small in-memory DB fake for the pass
integration tests. Covers: peak extraction, the climatology-percentile /
absolute-fallback verdict rules, the verified / unverified (false-alarm
"shell") / candidate_miss paths end to end, the per-(cell, class) weekly
rate limit, exclusions (advisory tier, informational classes), the master
flag, the horizon short-circuit, single-judgement idempotency, data-gap
skipping, admin-log discipline (candidate_miss only), and the never-raises
contract.
"""

import datetime as dt
import importlib
import importlib.util
import json
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
outcomes = importlib.import_module("wmod.control.warnings_engine.outcomes")
sources_base = importlib.import_module("wmod.control.warnings_engine.sources.base")


# --------------------------------------------------------------------------- #
# synthetic world
# --------------------------------------------------------------------------- #

NOW = dt.datetime.utcnow().replace(microsecond=0)
HORIZON = NOW - dt.timedelta(hours=6)     # ERA5-ish observation lag

#: flat synthetic weekly normals: median 20 / p75 40 / p90 80 / p99 160 mm.
WEEK_NORMAL = {"n": 28, "median": 20.0, "p75": 40.0, "p90": 80.0, "p99": 160.0}


def flat_normals():
    return {
        "version": 1,
        "weeks": [{"week": w, "precip_mm": dict(WEEK_NORMAL), "tcwv": None}
                  for w in range(52)],
    }


def series_of(hours, precip_mm_h=0.0, gust_ms=5.0):
    return {
        "precipitation": np.full(hours, float(precip_mm_h)),
        "wind_gusts_10m": np.full(hours, float(gust_ms)),
    }


class FakeSource:
    """WarningsDataSource stand-in serving constant synthetic weather."""

    name = "synthetic"

    def __init__(self, precip_mm_h=0.0, gust_ms=5.0, horizon=HORIZON,
                 explode=False):
        self.precip_mm_h = precip_mm_h
        self.gust_ms = gust_ms
        self.horizon = horizon
        self.explode = explode
        self.series_calls = 0

    def data_horizon_utc(self):
        return self.horizon

    def hourly_series(self, latitude, longitude, variables, start, end):
        if self.explode:
            raise RuntimeError("network down")
        self.series_calls += 1
        hours = int((end - start).total_seconds() // 3600)
        return series_of(hours, self.precip_mm_h, self.gust_ms)


class FakeCache:
    def __init__(self):
        self.store = {}

    def get_value(self, key):
        return self.store.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.store[key] = value


class InsertedDoc:
    def __init__(self, payload, sink):
        self.payload = payload
        self.sink = sink
        self.name = "OUT-%04d" % (len(sink) + 1)

    def insert(self, ignore_permissions=False):
        self.sink.append(self.payload)
        return self


def _match(row, filters):
    for field, cond in (filters or {}).items():
        val = row.get(field)
        if isinstance(cond, (list, tuple)):
            op, arg = cond[0], cond[1]
            if op == "in":
                ok = val in arg
            elif op == "not in":
                ok = val not in arg
            elif op == "between":
                ok = val is not None and arg[0] <= val <= arg[1]
            elif op == "<=":
                ok = val is not None and val <= arg
            elif op == ">=":
                ok = val is not None and val >= arg
            elif op == "!=":
                ok = val != arg
            else:
                raise AssertionError("unsupported operator %r" % op)
        else:
            ok = val == cond
        if not ok:
            return False
    return True


class FakeFrappeWorld:
    """In-memory DB behind the stubbed frappe module, restored on exit."""

    def __init__(self, conf=None, warnings=(), locations=(), outcomes_rows=(),
                 normals=None):
        self.conf = conf if conf is not None else {}
        self.warnings = [dict(w) for w in warnings]
        self.locations = [dict(l) for l in locations]
        self.outcomes = [dict(o) for o in outcomes_rows]
        self.normals = normals            # dict | None: every cell shares it
        self.cache = FakeCache()
        self.log_calls = []               # (message, title)
        self.get_all_calls = []

    # -- frappe API surface -------------------------------------------------
    def get_all(self, doctype, filters=None, fields=None, order_by=None,
                limit_page_length=None):
        self.get_all_calls.append((doctype, filters))
        table = {
            outcomes.WARNING_DOCTYPE: self.warnings,
            outcomes.WATCH_DOCTYPE: self.locations,
            outcomes.OUTCOME_DOCTYPE: self.outcomes,
        }[doctype]
        rows = [r for r in table if _match(r, filters)]
        if limit_page_length:
            rows = rows[:limit_page_length]
        out = []
        for r in rows:
            names = fields or list(r.keys())
            out.append(types.SimpleNamespace(
                **{f: r.get(f) for f in names}))
        return out

    def db_get_value(self, doctype, name_or_filters, fieldname,
                     as_dict=False):
        if doctype == outcomes.WATCH_DOCTYPE:
            for r in self.locations:
                if r["name"] == name_or_filters:
                    return types.SimpleNamespace(
                        latitude=r["latitude"], longitude=r["longitude"])
            return None
        if doctype == outcomes.CLIMO_DOCTYPE:
            return json.dumps(self.normals) if self.normals else None
        raise AssertionError("unexpected doctype %r" % doctype)

    def get_doc(self, payload):
        return InsertedDoc(payload, self.outcomes_sink)

    @property
    def outcomes_sink(self):
        return self._sink

    # -- install / restore --------------------------------------------------
    def __enter__(self):
        import frappe
        self._sink = []
        self._saved = {
            "conf": frappe.conf, "get_all": frappe.get_all,
            "get_doc": frappe.get_doc, "db": frappe.db,
            "cache": frappe.cache, "log_error": frappe.log_error,
            "get_datetime": frappe.utils.get_datetime,
            "get_source": sources_base.get_data_source,
        }
        frappe.conf = self.conf
        frappe.get_all = self.get_all
        frappe.get_doc = self.get_doc
        frappe.db = types.SimpleNamespace(get_value=self.db_get_value)
        frappe.cache = lambda: self.cache
        frappe.log_error = lambda message, title: self.log_calls.append(
            (message, title))

        def _parse(v):
            if isinstance(v, str):
                return dt.datetime.fromisoformat(v)
            return v

        frappe.utils.get_datetime = _parse
        return self

    def __exit__(self, *exc):
        import frappe
        frappe.conf = self._saved["conf"]
        frappe.get_all = self._saved["get_all"]
        frappe.get_doc = self._saved["get_doc"]
        frappe.db = self._saved["db"]
        frappe.cache = self._saved["cache"]
        frappe.log_error = self._saved["log_error"]
        frappe.utils.get_datetime = self._saved["get_datetime"]
        sources_base.get_data_source = self._saved["get_source"]
        return False

    def use_source(self, source):
        sources_base.get_data_source = lambda: source
        return source

    @property
    def inserted(self):
        return self._sink


def watch_cell(name="-23.00,30.50", lat=-23.0, lng=30.5, requested=None):
    return {"name": name, "latitude": lat, "longitude": lng,
            "active": 1,
            "last_requested_at": requested or NOW - dt.timedelta(hours=2)}


def episode(name="SWW-1", cell="-23.00,30.50", event_class="flood",
            severity="heads_up", status="expired", ended_hours_ago=80,
            duration_hours=24, tier=2, confidence=0.7):
    valid_until = NOW - dt.timedelta(hours=ended_hours_ago)
    return {
        "name": name, "watch_location": cell, "event_class": event_class,
        "severity": severity, "status": status,
        "onset": valid_until - dt.timedelta(hours=duration_hours),
        "valid_until": valid_until,
        "detector_tier": tier, "confidence": confidence,
    }


# --------------------------------------------------------------------------- #
# pure computation
# --------------------------------------------------------------------------- #

class TestObservedPeaks(unittest.TestCase):
    def test_peaks_of_constant_series(self):
        start = dt.datetime(2026, 1, 1)
        peaks = outcomes.observed_peaks(series_of(72, 2.0, 18.0), start)
        self.assertAlmostEqual(peaks["max_precip_24h_mm"], 48.0)
        self.assertAlmostEqual(peaks["max_gust_ms"], 18.0)
        self.assertEqual(peaks["precip_peak_at"].year, 2026)

    def test_peak_hour_located(self):
        start = dt.datetime(2026, 1, 1)
        series = series_of(72, 0.0, 5.0)
        series["precipitation"][30:40] = 12.0     # one 120 mm burst
        series["wind_gusts_10m"][50] = 33.0
        peaks = outcomes.observed_peaks(series, start)
        self.assertAlmostEqual(peaks["max_precip_24h_mm"], 120.0)
        self.assertAlmostEqual(peaks["max_gust_ms"], 33.0)
        self.assertEqual(peaks["gust_peak_at"], start + dt.timedelta(hours=50))
        self.assertGreaterEqual(peaks["precip_peak_at"],
                                start + dt.timedelta(hours=39))

    def test_all_nan_series_yields_none_peaks(self):
        series = {"precipitation": np.full(72, np.nan),
                  "wind_gusts_10m": np.full(72, np.nan)}
        peaks = outcomes.observed_peaks(series, dt.datetime(2026, 1, 1))
        self.assertIsNone(peaks["max_precip_24h_mm"])
        self.assertIsNone(peaks["max_gust_ms"])

    def test_missing_variables_yield_none_peaks(self):
        peaks = outcomes.observed_peaks({}, dt.datetime(2026, 1, 1))
        self.assertIsNone(peaks["max_precip_24h_mm"])
        self.assertIsNone(peaks["max_gust_ms"])


class TestWeeklyPercentile(unittest.TestCase):
    def peaks(self, mm):
        return {"max_precip_24h_mm": mm,
                "precip_peak_at": dt.datetime(2026, 1, 10)}

    def test_percentile_anchors(self):
        normals = flat_normals()
        self.assertAlmostEqual(
            outcomes.precip_weekly_pctl(self.peaks(80.0), normals), 0.90)
        self.assertAlmostEqual(
            outcomes.precip_weekly_pctl(self.peaks(160.0), normals), 0.99)

    def test_none_without_normals_or_peak(self):
        self.assertIsNone(outcomes.precip_weekly_pctl(self.peaks(80.0), None))
        self.assertIsNone(outcomes.precip_weekly_pctl(
            {"max_precip_24h_mm": None}, flat_normals()))

    def test_none_when_week_has_no_precip_normals(self):
        normals = flat_normals()
        for wk in normals["weeks"]:
            wk["precip_mm"] = None
        self.assertIsNone(outcomes.precip_weekly_pctl(
            self.peaks(80.0), normals))


class TestEpisodeVerdict(unittest.TestCase):
    def test_rain_class_climatology_percentile_rule(self):
        peaks = {"max_precip_24h_mm": 96.0, "max_gust_ms": 5.0}
        self.assertEqual(
            outcomes.episode_verdict("flood", peaks, 0.92), "verified")
        self.assertEqual(
            outcomes.episode_verdict("flash_flood", peaks, 0.50),
            "unverified")

    def test_rain_class_absolute_fallback(self):
        wet = {"max_precip_24h_mm": outcomes.VERIFY_PRECIP_24H_MM,
               "max_gust_ms": None}
        dry = {"max_precip_24h_mm": 5.0, "max_gust_ms": None}
        self.assertEqual(
            outcomes.episode_verdict("flood", wet, None), "verified")
        self.assertEqual(
            outcomes.episode_verdict("flood", dry, None), "unverified")

    def test_wind_class_absolute_rule(self):
        windy = {"max_precip_24h_mm": None,
                 "max_gust_ms": outcomes.VERIFY_GUST_MS + 1}
        calm = {"max_precip_24h_mm": None, "max_gust_ms": 8.0}
        self.assertEqual(
            outcomes.episode_verdict("destructive_wind", windy, None),
            "verified")
        self.assertEqual(
            outcomes.episode_verdict("tornado", calm, None), "unverified")

    def test_data_gap_is_never_judged(self):
        gap = {"max_precip_24h_mm": None, "max_gust_ms": None}
        self.assertIsNone(outcomes.episode_verdict("flood", gap, None))
        self.assertIsNone(
            outcomes.episode_verdict("destructive_wind", gap, None))

    def test_informational_classes_are_never_judged(self):
        peaks = {"max_precip_24h_mm": 500.0, "max_gust_ms": 50.0}
        self.assertIsNone(outcomes.episode_verdict("cold_front", peaks, 0.99))
        self.assertNotIn("cold_front", outcomes.VERIFIABLE_CLASSES)
        self.assertIn("advisory", outcomes.EXCLUDED_SEVERITIES)


class TestMissFindings(unittest.TestCase):
    def test_disaster_grade_precip_via_percentile(self):
        peaks = {"max_precip_24h_mm": 192.0, "max_gust_ms": 5.0}
        found = outcomes.miss_findings(peaks, 0.99)
        self.assertEqual(found, [(outcomes.MISS_CLASS_FOR_PRECIP, "precip")])

    def test_verify_grade_is_not_miss_grade(self):
        # verified-level rain (p90-ish) must NOT create a candidate miss
        peaks = {"max_precip_24h_mm": 96.0, "max_gust_ms": 5.0}
        self.assertEqual(outcomes.miss_findings(peaks, 0.92), [])

    def test_absolute_fallback_and_gust(self):
        peaks = {"max_precip_24h_mm": outcomes.MISS_PRECIP_24H_MM,
                 "max_gust_ms": outcomes.MISS_GUST_MS}
        found = outcomes.miss_findings(peaks, None)
        self.assertIn((outcomes.MISS_CLASS_FOR_PRECIP, "precip"), found)
        self.assertIn((outcomes.MISS_CLASS_FOR_GUST, "gust"), found)

    def test_quiet_window_has_no_findings(self):
        peaks = {"max_precip_24h_mm": 4.0, "max_gust_ms": 9.0}
        self.assertEqual(outcomes.miss_findings(peaks, 0.10), [])
        self.assertEqual(
            outcomes.miss_findings(
                {"max_precip_24h_mm": None, "max_gust_ms": None}, None), [])


class TestEvidence(unittest.TestCase):
    def test_evidence_is_json_ready_and_complete(self):
        start = dt.datetime(2026, 1, 1)
        end = dt.datetime(2026, 1, 4)
        peaks = outcomes.observed_peaks(series_of(72, 4.0, 21.0), start)
        ev = outcomes.build_evidence(
            "episode", start, end, peaks, 0.92, True, "synthetic", HORIZON,
            extra={"episode": {"warning": "SWW-1"}})
        parsed = json.loads(json.dumps(ev))
        self.assertEqual(parsed["version"], outcomes.SCHEMA_VERSION)
        self.assertEqual(parsed["kind"], "episode")
        self.assertAlmostEqual(parsed["observed"]["max_precip_24h_mm"], 96.0)
        self.assertAlmostEqual(parsed["observed"]["precip_weekly_pctl"], 0.92)
        self.assertAlmostEqual(parsed["observed"]["max_gust_ms"], 21.0)
        self.assertTrue(parsed["climatology_available"])
        self.assertIn("thresholds", parsed)
        self.assertEqual(parsed["episode"]["warning"], "SWW-1")


# --------------------------------------------------------------------------- #
# the daily pass, end to end (in-memory frappe world)
# --------------------------------------------------------------------------- #

class TestVerificationPass(unittest.TestCase):
    def test_hit_is_recorded_verified(self):
        world = FakeFrappeWorld(
            warnings=[episode(event_class="flood")],
            locations=[watch_cell()], normals=flat_normals())
        with world:
            world.use_source(FakeSource(precip_mm_h=4.0))   # 96 mm/24h ~p92
            outcomes.run_outcome_pass()
        rows = [r for r in world.inserted if r["warning"] == "SWW-1"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["verdict"], "verified")
        self.assertEqual(row["event_class"], "flood")
        self.assertEqual(row["watch_location"], "-23.00,30.50")
        self.assertAlmostEqual(row["peak_precip_24h_mm"], 96.0)
        self.assertGreaterEqual(row["peak_precip_pctl"], 0.90)
        ev = json.loads(row["evidence"])
        self.assertEqual(ev["kind"], "episode")
        self.assertEqual(ev["episode"]["warning"], "SWW-1")

    def test_false_alarm_leaves_an_unverified_shell(self):
        world = FakeFrappeWorld(
            warnings=[episode(event_class="flash_flood")],
            locations=[watch_cell()], normals=flat_normals())
        with world:
            world.use_source(FakeSource(precip_mm_h=0.1))   # 2.4 mm/24h
            outcomes.run_outcome_pass()
        self.assertEqual(len(world.inserted), 1)
        row = world.inserted[0]
        self.assertEqual(row["verdict"], "unverified")
        self.assertEqual(row["warning"], "SWW-1")
        # the quiet aftermath must NOT hit the candidate-miss admin log
        titles = [t for _, t in world.log_calls]
        self.assertNotIn(outcomes.TITLE_OUTCOME, titles)

    def test_wind_episode_verified_by_gust(self):
        world = FakeFrappeWorld(
            warnings=[episode(event_class="destructive_wind")],
            locations=[watch_cell()])
        with world:
            world.use_source(FakeSource(precip_mm_h=0.0, gust_ms=23.0))
            outcomes.run_outcome_pass()
        self.assertEqual(world.inserted[0]["verdict"], "verified")
        self.assertAlmostEqual(world.inserted[0]["peak_gust_ms"], 23.0)

    def test_absolute_fallback_without_climatology(self):
        world = FakeFrappeWorld(
            warnings=[episode(event_class="flood")],
            locations=[watch_cell()], normals=None)
        with world:
            world.use_source(FakeSource(precip_mm_h=2.5))   # 60 mm/24h >= 50
            outcomes.run_outcome_pass()
        row = world.inserted[0]
        self.assertEqual(row["verdict"], "verified")
        self.assertIsNone(row["peak_precip_pctl"])
        self.assertFalse(json.loads(row["evidence"])["climatology_available"])

    def test_each_episode_judged_exactly_once(self):
        world = FakeFrappeWorld(
            warnings=[episode(event_class="flood")],
            locations=[watch_cell()],
            outcomes_rows=[{"name": "OUT-old", "warning": "SWW-1",
                            "watch_location": "-23.00,30.50",
                            "event_class": "flood", "verdict": "verified",
                            "recorded_at": NOW - dt.timedelta(days=1)}],
            normals=flat_normals())
        with world:
            world.use_source(FakeSource(precip_mm_h=4.0))
            outcomes.run_outcome_pass()
        self.assertEqual(world.inserted, [])

    def test_advisory_and_informational_classes_excluded(self):
        world = FakeFrappeWorld(
            warnings=[
                episode(name="SWW-adv", severity="advisory"),
                episode(name="SWW-cf", event_class="cold_front"),
                episode(name="SWW-active", status="active"),
            ],
            locations=[watch_cell()], normals=flat_normals())
        with world:
            world.use_source(FakeSource(precip_mm_h=4.0))
            outcomes.run_outcome_pass()
        self.assertEqual(world.inserted, [])

    def test_too_recent_episode_waits(self):
        world = FakeFrappeWorld(
            warnings=[episode(ended_hours_ago=6)],   # ended only 6 h ago
            locations=[watch_cell()], normals=flat_normals())
        with world:
            world.use_source(FakeSource(precip_mm_h=4.0))
            outcomes.run_outcome_pass()
        self.assertEqual(world.inserted, [])

    def test_data_gap_skips_judgement(self):
        world = FakeFrappeWorld(
            warnings=[episode(event_class="flood")],
            locations=[watch_cell()], normals=flat_normals())

        class GapSource(FakeSource):
            def hourly_series(self, latitude, longitude, variables,
                              start, end):
                hours = int((end - start).total_seconds() // 3600)
                return {"precipitation": np.full(hours, np.nan),
                        "wind_gusts_10m": np.full(hours, np.nan)}

        with world:
            world.use_source(GapSource())
            outcomes.run_outcome_pass()
        self.assertEqual(world.inserted, [])


class TestCandidateMissPass(unittest.TestCase):
    def test_unwarned_extreme_becomes_candidate_miss(self):
        world = FakeFrappeWorld(
            locations=[watch_cell()], normals=flat_normals())
        with world:
            world.use_source(FakeSource(precip_mm_h=8.0))   # 192 mm/24h ~p99
            outcomes.run_outcome_pass()
        self.assertEqual(len(world.inserted), 1)
        row = world.inserted[0]
        self.assertEqual(row["verdict"], "candidate_miss")
        self.assertIsNone(row["warning"])
        self.assertEqual(row["event_class"], outcomes.MISS_CLASS_FOR_PRECIP)
        self.assertEqual(json.loads(row["evidence"])["kind"], "quiet_scan")
        titles = [t for _, t in world.log_calls]
        self.assertIn(outcomes.TITLE_OUTCOME, titles)

    def test_unwarned_gust_extreme_flagged_for_wind_class(self):
        world = FakeFrappeWorld(locations=[watch_cell()])
        with world:
            world.use_source(FakeSource(precip_mm_h=0.0, gust_ms=27.0))
            outcomes.run_outcome_pass()
        self.assertEqual(len(world.inserted), 1)
        self.assertEqual(world.inserted[0]["event_class"],
                         outcomes.MISS_CLASS_FOR_GUST)
        self.assertEqual(world.inserted[0]["verdict"], "candidate_miss")

    def test_a_live_episode_of_the_family_suppresses_the_miss(self):
        world = FakeFrappeWorld(
            warnings=[episode(name="SWW-live", event_class="flash_flood",
                              status="active", ended_hours_ago=-24,
                              duration_hours=96)],
            locations=[watch_cell()], normals=flat_normals())
        with world:
            world.use_source(FakeSource(precip_mm_h=8.0))
            outcomes.run_outcome_pass()
        misses = [r for r in world.inserted
                  if r["verdict"] == "candidate_miss"]
        self.assertEqual(misses, [])

    def test_an_advisory_does_not_count_as_warned(self):
        world = FakeFrappeWorld(
            warnings=[episode(name="SWW-adv", event_class="flash_flood",
                              severity="advisory", status="active",
                              ended_hours_ago=-24, duration_hours=96)],
            locations=[watch_cell()], normals=flat_normals())
        with world:
            world.use_source(FakeSource(precip_mm_h=8.0))
            outcomes.run_outcome_pass()
        misses = [r for r in world.inserted
                  if r["verdict"] == "candidate_miss"]
        self.assertEqual(len(misses), 1)

    def test_rate_limit_one_per_cell_class_week(self):
        recent = {"name": "OUT-old", "warning": None,
                  "watch_location": "-23.00,30.50",
                  "event_class": outcomes.MISS_CLASS_FOR_PRECIP,
                  "verdict": "candidate_miss",
                  "recorded_at": NOW - dt.timedelta(days=2)}
        world = FakeFrappeWorld(
            locations=[watch_cell()], outcomes_rows=[recent],
            normals=flat_normals())
        with world:
            world.use_source(FakeSource(precip_mm_h=8.0))
            outcomes.run_outcome_pass()
        self.assertEqual(world.inserted, [])

    def test_rate_limit_lapses_after_a_week(self):
        old = {"name": "OUT-old", "warning": None,
               "watch_location": "-23.00,30.50",
               "event_class": outcomes.MISS_CLASS_FOR_PRECIP,
               "verdict": "candidate_miss",
               "recorded_at": NOW - dt.timedelta(
                   days=outcomes.MISS_RATE_LIMIT_DAYS + 1)}
        world = FakeFrappeWorld(
            locations=[watch_cell()], outcomes_rows=[old],
            normals=flat_normals())
        with world:
            world.use_source(FakeSource(precip_mm_h=8.0))
            outcomes.run_outcome_pass()
        self.assertEqual(len(world.inserted), 1)

    def test_stale_cells_are_not_scanned(self):
        world = FakeFrappeWorld(
            locations=[watch_cell(
                requested=NOW - dt.timedelta(days=outcomes.STALE_DAYS + 1))],
            normals=flat_normals())
        with world:
            src = world.use_source(FakeSource(precip_mm_h=8.0))
            outcomes.run_outcome_pass()
        self.assertEqual(world.inserted, [])
        self.assertEqual(src.series_calls, 0)


class TestPassSafety(unittest.TestCase):
    def test_master_flag_off_is_a_total_noop(self):
        world = FakeFrappeWorld(
            conf={outcomes.CONFIG_FLAG: "0"},
            warnings=[episode()], locations=[watch_cell()])
        with world:
            src = world.use_source(FakeSource(precip_mm_h=8.0))
            outcomes.run_outcome_pass()
        self.assertEqual(world.get_all_calls, [])
        self.assertEqual(world.inserted, [])
        self.assertEqual(src.series_calls, 0)

    def test_flag_default_on(self):
        import frappe
        original = frappe.conf
        try:
            frappe.conf = {}
            self.assertTrue(outcomes.is_enabled())
            frappe.conf = {outcomes.CONFIG_FLAG: "off"}
            self.assertFalse(outcomes.is_enabled())
            frappe.conf = {outcomes.CONFIG_FLAG: "1"}
            self.assertTrue(outcomes.is_enabled())
        finally:
            frappe.conf = original

    def test_horizon_short_circuit(self):
        world = FakeFrappeWorld(
            warnings=[episode()], locations=[watch_cell()])
        world.cache.store[outcomes.HORIZON_CACHE_KEY] = HORIZON.isoformat()
        with world:
            src = world.use_source(FakeSource(precip_mm_h=8.0))
            outcomes.run_outcome_pass()
        self.assertEqual(world.get_all_calls, [])
        self.assertEqual(src.series_calls, 0)
        self.assertEqual(world.inserted, [])

    def test_pass_runs_once_horizon_advances(self):
        world = FakeFrappeWorld(locations=[watch_cell()])
        world.cache.store[outcomes.HORIZON_CACHE_KEY] = (
            HORIZON - dt.timedelta(hours=24)).isoformat()
        with world:
            world.use_source(FakeSource(precip_mm_h=8.0))
            outcomes.run_outcome_pass()
        self.assertEqual(len(world.inserted), 1)
        self.assertEqual(world.cache.store[outcomes.HORIZON_CACHE_KEY],
                         HORIZON.isoformat())

    def test_source_failure_never_raises(self):
        world = FakeFrappeWorld(warnings=[episode()],
                                locations=[watch_cell()])
        with world:
            def boom():
                raise RuntimeError("source down")
            sources_base.get_data_source = boom
            outcomes.run_outcome_pass()          # must not raise
        titles = [t for _, t in world.log_calls]
        self.assertIn(outcomes.TITLE_OUTCOME_PASS, titles)
        self.assertEqual(world.inserted, [])

    def test_per_cell_error_isolation(self):
        cells = [watch_cell(), watch_cell(name="-24.00,31.00", lat=-24.0,
                                          lng=31.0)]
        world = FakeFrappeWorld(locations=cells, normals=flat_normals())

        class HalfBrokenSource(FakeSource):
            def hourly_series(self, latitude, longitude, variables,
                              start, end):
                if latitude == -23.0:
                    raise RuntimeError("bad cell")
                return super().hourly_series(
                    latitude, longitude, variables, start, end)

        with world:
            world.use_source(HalfBrokenSource(precip_mm_h=8.0))
            outcomes.run_outcome_pass()          # must not raise
        # the healthy cell still got its candidate miss
        self.assertEqual(len(world.inserted), 1)
        self.assertEqual(world.inserted[0]["watch_location"], "-24.00,31.00")
        titles = [t for _, t in world.log_calls]
        self.assertIn(outcomes.TITLE_OUTCOME_PASS, titles)

    def test_series_memo_fetches_once_per_window(self):
        world = FakeFrappeWorld(locations=[watch_cell()])
        with world:
            src = world.use_source(FakeSource(precip_mm_h=0.0))
            memo = outcomes._SeriesMemo(src)
            start = HORIZON - dt.timedelta(hours=72)
            memo.get(-23.0, 30.5, start, HORIZON)
            memo.get(-23.0, 30.5, start, HORIZON)
        self.assertEqual(src.series_calls, 1)

    def test_nothing_user_facing_in_the_module(self):
        # the ledger writes admin records only: no messages/copy imports,
        # no push, no endpoint surface
        import wmod.control.warnings_engine.outcomes as mod
        with open(mod.__file__, encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("messages.render", src)
        self.assertNotIn("push.notify", src)
        self.assertNotIn("@frappe.whitelist", src)


if __name__ == "__main__":
    unittest.main()
