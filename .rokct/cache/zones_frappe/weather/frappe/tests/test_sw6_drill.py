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

"""Offline tests for drill/replay mode (sw6).

Fixture series and in-memory record stores only - no network, no bench.
Frappe is stubbed exactly like the sibling engine test files. Covers: the
ReplaySource historical-cursor clamps (horizon and reads never pass the
cursor, cursor never passes the real archive), the cursor schedule and the
window clamps/caps, the replay runner (drill records created is_drill=1
with a run id, idempotent updates, expiry on episode end, per-step error
isolation, no push calls), the real production detection path wired at a
cursor, the record cleaner, the fail-closed drill fences (push refuses
drill and unreadable records; client API, outcome ledger, propagation, live
evaluator and basin upserts all exclude drill rows), and the run_drill /
clear_drill admin endpoints (System Manager gate, location resolution
without side effects, plain-language refusals).
"""

import datetime as dt
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
CONTROL_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "control")
ENGINE_DIR = os.path.join(CONTROL_DIR, "warnings_engine")


def _ensure_frappe_stub():
    try:
        import frappe  # noqa: F401
    except ImportError:
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
    import frappe
    if not hasattr(frappe, "get_roles"):
        frappe.get_roles = MagicMock(return_value=["System Manager"])
    if not hasattr(frappe, "PermissionError"):
        frappe.PermissionError = type("PermissionError", (Exception,), {})
    if not hasattr(frappe, "delete_doc"):
        frappe.delete_doc = MagicMock()
    if not hasattr(frappe, "session"):
        frappe.session = types.SimpleNamespace(user="Administrator")


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


def _load_modules():
    _ensure_frappe_stub()
    if "wmod" not in sys.modules:
        parent = types.ModuleType("wmod")
        parent.__path__ = []
        sys.modules["wmod"] = parent
    _load_pkg("wmod.warnings_engine", COMMON_DIR)
    control = sys.modules.get("wmod.control") or _load_pkg("wmod.control",
                                                           CONTROL_DIR)
    if CONTROL_DIR not in getattr(control, "__path__", []):
        control.__path__ = list(getattr(control, "__path__", [])) + [
            CONTROL_DIR]
    _load_pkg("wmod.control.warnings_engine", ENGINE_DIR)
    return (
        importlib.import_module("wmod.control.warnings_engine.drill"),
        importlib.import_module("wmod.control.api.run_drill.run_drill"),
        importlib.import_module(
            "wmod.control.api.get_weather_warnings.get_weather_warnings"),
    )


drill, run_drill_api, control_api = _load_modules()
push = importlib.import_module("wmod.warnings_engine.push")

import frappe  # noqa: E402  (the stub, after install)

HORIZON = dt.datetime(2024, 2, 20, 0, 0)
START = dt.datetime(2024, 2, 1, 0, 0)
END = dt.datetime(2024, 2, 5, 0, 0)
NOW = dt.datetime(2026, 8, 22, 9, 0)


class RecordingSource:
    """WarningsDataSource stand-in that records every read window."""

    name = "synthetic"

    def __init__(self, horizon=HORIZON):
        self.horizon = horizon
        self.reads = []

    def data_horizon_utc(self):
        return self.horizon

    #: calm, physical constants (ERA5 storage units) so the real feature
    #: port runs warning-free and the frozen detector fires nothing.
    CALM = {"pressure_msl": 101325.0, "temperature_2m": 20.0,
            "dew_point_2m": 10.0, "wind_gusts_10m": 4.0,
            "soil_moisture_0_to_7cm": 0.2,
            "total_column_integrated_water_vapour": 20.0}

    def hourly_series(self, latitude, longitude, variables, start, end):
        self.reads.append(("series", start, end))
        hours = int((end - start).total_seconds() // 3600)
        return {v: np.full(hours, self.CALM.get(v, 0.0)) for v in variables}

    def neighborhood_precipitation(self, latitude, longitude, start, end):
        self.reads.append(("nbr", start, end))
        return None


class FakeEpisode:
    fired_conditions = ("p72_wet",)
    max_confidence = 0.8
    first_fired_at = dt.datetime(2024, 2, 2, 4, 0)


class FakeResult:
    def __init__(self, tier=2, confidence=0.6):
        self.tier = [tier]
        self.confidence = [confidence]
        self.alarms = [FakeEpisode()]


def loc_row(name="-23.00,30.50", lat=-23.0, lng=30.5, label="Thohoyandou"):
    return types.SimpleNamespace(name=name, latitude=lat, longitude=lng,
                                 label=label)


class DrillDB:
    """In-memory Severe Weather Warning store for the runner tests."""

    def __init__(self):
        self.rows = {}   # name -> fields dict
        self.seq = 0

    def get_value(self, doctype, filters, fieldname):
        for name, row in self.rows.items():
            if all(row.get(k) == v for k, v in filters.items()):
                return name
        return None

    def set_value(self, doctype, name, values):
        self.rows[name].update(values)

    def get_doc(self, payload):
        db = self

        class Doc:
            def insert(self, ignore_permissions=False):
                db.seq += 1
                self.name = f"SWW-{db.seq:05d}"
                db.rows[self.name] = dict(payload)
                return self

        return Doc()

    def get_all(self, doctype, filters=None, fields=None,
                limit_page_length=None):
        out = []
        for name, row in self.rows.items():
            if all(row.get(k) == v for k, v in (filters or {}).items()):
                out.append(types.SimpleNamespace(name=name, **{
                    f: row.get(f) for f in (fields or []) if f != "name"}))
        return out


class RunnerHarness:
    """Installs the DrillDB + a fake configured source; restores on exit."""

    def __init__(self, source=None):
        self.db = DrillDB()
        self.source = source or RecordingSource()

    def __enter__(self):
        from wmod.control.warnings_engine.sources import base as sources_base
        self._saved = (frappe.db, frappe.get_doc, frappe.get_all,
                       frappe.conf, sources_base.get_data_source)
        self._sources_base = sources_base
        frappe.db = types.SimpleNamespace(get_value=self.db.get_value,
                                          set_value=self.db.set_value)
        frappe.get_doc = self.db.get_doc
        frappe.get_all = self.db.get_all
        frappe.conf = {}
        sources_base.get_data_source = lambda: self.source
        return self

    def __exit__(self, *exc):
        (frappe.db, frappe.get_doc, frappe.get_all, frappe.conf,
         self._sources_base.get_data_source) = self._saved
        return False


# --------------------------------------------------------------------------- #
# ReplaySource: the historical-cursor clamps
# --------------------------------------------------------------------------- #

class TestReplaySource(unittest.TestCase):
    def test_horizon_is_the_cursor_never_the_archive_frontier(self):
        src = drill.ReplaySource(RecordingSource(), START)
        self.assertEqual(src.data_horizon_utc(), START)
        src.set_cursor(END)
        self.assertEqual(src.data_horizon_utc(), END)

    def test_cursor_can_never_pass_the_real_archive(self):
        src = drill.ReplaySource(RecordingSource(),
                                 HORIZON + dt.timedelta(days=99))
        self.assertEqual(src.data_horizon_utc(), HORIZON)
        src.set_cursor(HORIZON + dt.timedelta(days=1))
        self.assertEqual(src.data_horizon_utc(), HORIZON)

    def test_reads_are_truncated_at_the_cursor(self):
        inner = RecordingSource()
        src = drill.ReplaySource(inner, START)
        src.hourly_series(-23.0, 30.5, ["precipitation"],
                          START - dt.timedelta(hours=48), END)
        src.neighborhood_precipitation(-23.0, 30.5,
                                       START - dt.timedelta(hours=48), END)
        for _, _, end in inner.reads:
            self.assertLessEqual(end, START)

    def test_name_marks_the_source_as_a_drill_view(self):
        self.assertEqual(drill.ReplaySource(RecordingSource(), START).name,
                         "drill:synthetic")


# --------------------------------------------------------------------------- #
# cursor schedule + window clamps
# --------------------------------------------------------------------------- #

class TestSchedule(unittest.TestCase):
    def test_cursors_step_and_always_include_the_end(self):
        cursors = list(drill.iter_cursors(START, START + dt.timedelta(hours=60),
                                          24))
        self.assertEqual(cursors, [
            START, START + dt.timedelta(hours=24),
            START + dt.timedelta(hours=48), START + dt.timedelta(hours=60)])

    def test_end_clamped_to_archive_and_empty_window_refused(self):
        start, end, step = drill.clamp_window(
            START, HORIZON + dt.timedelta(days=30), HORIZON, 24)
        self.assertEqual(end, HORIZON)
        with self.assertRaises(ValueError):
            drill.clamp_window(HORIZON + dt.timedelta(days=1),
                               HORIZON + dt.timedelta(days=2), HORIZON, 24)

    def test_span_step_and_step_count_caps(self):
        with self.assertRaises(ValueError):
            drill.clamp_window(START, START + dt.timedelta(
                days=drill.MAX_SPAN_DAYS + 1),
                START + dt.timedelta(days=drill.MAX_SPAN_DAYS + 9), 24)
        _, _, step = drill.clamp_window(START, END, HORIZON, None)
        self.assertEqual(step, drill.DEFAULT_STEP_HOURS)
        _, _, step = drill.clamp_window(START, END, HORIZON, "0")
        self.assertEqual(step, drill.MIN_STEP_HOURS)
        _, _, step = drill.clamp_window(START, END, HORIZON, 10_000)
        self.assertEqual(step, drill.MAX_STEP_HOURS)
        with self.assertRaises(ValueError):
            # 31 days at 1 h/step blows the step cap before the span cap
            drill.clamp_window(START, START + dt.timedelta(days=30),
                               HORIZON, "1")


# --------------------------------------------------------------------------- #
# the replay runner
# --------------------------------------------------------------------------- #

class TestRunner(unittest.TestCase):
    def test_replay_writes_flagged_records_and_never_pushes(self):
        push_calls = []
        saved = push.notify_warning_upsert
        push.notify_warning_upsert = lambda *a, **k: push_calls.append(a)
        try:
            with RunnerHarness() as h:
                def detect(source, rules, loc, cursor):
                    return {"flood": FakeResult()}
                summary = drill.run_drill_replay(
                    [loc_row()], START, END, step_hours=24,
                    run_id="drill-test-1", now=NOW, detect_fn=detect)
        finally:
            push.notify_warning_upsert = saved
        self.assertEqual(push_calls, [])
        self.assertEqual(summary["records"],
                         {"created": 1, "updated": 4, "expired": 0})
        self.assertEqual(summary["steps"], 5)
        self.assertEqual(len(h.db.rows), 1)
        row = next(iter(h.db.rows.values()))
        self.assertEqual(row["is_drill"], 1)
        self.assertEqual(row["drill_run_id"], "drill-test-1")
        self.assertEqual(row["status"], "active")
        self.assertEqual(row["valid_until"],
                         NOW + dt.timedelta(hours=drill.DRILL_TTL_HOURS))
        self.assertIn("Flooding possible", row["headline"])
        self.assertNotIn("warning", row["headline"].lower())
        self.assertIn('"run_id": "drill-test-1"', row["precursors"])

    def test_episode_end_expires_the_drill_record(self):
        firing = {"value": True}

        def detect(source, rules, loc, cursor):
            return {"flood": FakeResult(tier=2 if firing["value"] else 0)}

        with RunnerHarness() as h:
            drill.run_drill_replay([loc_row()], START,
                                   START + dt.timedelta(hours=24),
                                   step_hours=24, run_id="r1", now=NOW,
                                   detect_fn=detect)
            firing["value"] = False
            drill.run_drill_replay([loc_row()],
                                   START + dt.timedelta(hours=24), END,
                                   step_hours=24, run_id="r1", now=NOW,
                                   detect_fn=detect)
            row = next(iter(h.db.rows.values()))
        self.assertEqual(row["status"], "expired")

    def test_per_location_errors_are_isolated(self):
        def detect(source, rules, loc, cursor):
            if loc.name == "-23.00,30.50":
                raise RuntimeError("boom")
            return {"flood": FakeResult()}

        with RunnerHarness() as h:
            summary = drill.run_drill_replay(
                [loc_row(), loc_row(name="-24.00,30.50", lat=-24.0)],
                START, END, step_hours=48, run_id="r2", now=NOW,
                detect_fn=detect)
        self.assertEqual(summary["records"]["created"], 1)
        self.assertGreater(summary["step_errors"], 0)
        self.assertEqual(len(h.db.rows), 1)

    def test_default_detection_is_the_production_pipeline(self):
        """Zero weather through the REAL features + frozen detector at a
        cursor: runs end-to-end, fires nothing, writes nothing."""
        inner = RecordingSource()
        with RunnerHarness(source=inner) as h:
            summary = drill.run_drill_replay(
                [loc_row()], END - dt.timedelta(hours=1), END,
                step_hours=24, run_id="r3", now=NOW)
        self.assertEqual(h.db.rows, {})
        self.assertEqual(summary["records"]["created"], 0)
        # both replay steps read a full evaluator window up to the cursor
        evaluator = importlib.import_module(
            "wmod.control.warnings_engine.evaluator")
        series_reads = [r for r in inner.reads if r[0] == "series"]
        self.assertEqual(len(series_reads), 2)
        for _, start, end in series_reads:
            self.assertEqual(end - start,
                             dt.timedelta(hours=evaluator.WINDOW_HOURS))
            self.assertLessEqual(end, END)

    def test_clear_deletes_only_drill_rows(self):
        deleted = []
        with RunnerHarness() as h:
            h.db.rows["SWW-REAL"] = {"is_drill": 0}
            h.db.rows["SWW-D1"] = {"is_drill": 1, "drill_run_id": "r1"}
            h.db.rows["SWW-D2"] = {"is_drill": 1, "drill_run_id": "r2"}
            saved = frappe.delete_doc
            frappe.delete_doc = (
                lambda doctype, name, **kw: deleted.append(name))
            try:
                count = drill.clear_drill_records("r1")
                self.assertEqual((count, deleted), (1, ["SWW-D1"]))
                count = drill.clear_drill_records()
                self.assertEqual(count, 2)
                self.assertNotIn("SWW-REAL", deleted)
            finally:
                frappe.delete_doc = saved


# --------------------------------------------------------------------------- #
# the fail-closed drill fences
# --------------------------------------------------------------------------- #

class TestDrillFences(unittest.TestCase):
    def _notify(self, is_drill):
        saved = (frappe.conf, frappe.db)
        frappe.conf = {"severe_weather_push_enabled": 1}
        frappe.db = types.SimpleNamespace(
            get_value=lambda doctype, name, fieldname: is_drill)
        try:
            return push._notify("SWW-1", "-23.00,30.50", "flood",
                                {"severity": "heads_up", "headline": "h",
                                 "message": "m"})
        finally:
            frappe.conf, frappe.db = saved

    def test_push_refuses_drill_records(self):
        self.assertEqual(self._notify(1), "drill")

    def test_push_fails_closed_when_the_flag_is_unreadable(self):
        saved = (frappe.conf, frappe.db)
        frappe.conf = {"severe_weather_push_enabled": 1}

        def explode(doctype, name, fieldname):
            raise RuntimeError("db down")

        frappe.db = types.SimpleNamespace(get_value=explode)
        try:
            out = push._notify("SWW-1", "-23.00,30.50", "flood",
                               {"severity": "heads_up", "headline": "h",
                                "message": "m"})
        finally:
            frappe.conf, frappe.db = saved
        self.assertEqual(out, "drill_check_failed")

    def test_client_api_excludes_drills_unless_explicitly_asked(self):
        saved = frappe.get_all
        seen = {}

        def fake_get_all(doctype, filters=None, fields=None, order_by=None):
            seen["filters"], seen["fields"] = filters, fields
            return []

        frappe.get_all = fake_get_all
        try:
            control_api._active_warnings("-23.00,30.50")
            self.assertEqual(seen["filters"].get("is_drill"), ["!=", 1])
            self.assertNotIn("is_drill", seen["fields"])
            control_api._active_warnings("-23.00,30.50", include_drills=True)
            self.assertNotIn("is_drill", seen["filters"])
            self.assertIn("is_drill", seen["fields"])
        finally:
            frappe.get_all = saved

    def test_client_api_drill_flag_parses_fail_closed(self):
        for garbage in (None, "", "0", "false", "off", "definitely", 0):
            self.assertFalse(control_api._truthy(garbage), garbage)
        for yes in ("1", "true", "YES", "on", 1, True):
            self.assertTrue(control_api._truthy(yes), yes)

    def test_site_notice_generation_refuses_drill_records(self):
        """A drill must never name real assets: sites.sync_site_notices
        refuses is_drill records and fails closed on an unreadable flag,
        while a real record still generates its notice."""
        sites = importlib.import_module("wmod.control.warnings_engine.sites")
        saved = (frappe.conf, frappe.db, frappe.get_all, frappe.get_doc)
        frappe.conf = {}
        site_row = types.SimpleNamespace(
            name="WVS-1", site_name="Mutale low-water bridge",
            site_type="Bridge", route_label="R523")
        frappe.get_all = lambda doctype, **kw: [site_row]
        created = []

        class Doc:
            def insert(self, ignore_permissions=False):
                created.append(1)
                return self

        frappe.get_doc = lambda payload: Doc()

        def db_with_flag(flag):
            return types.SimpleNamespace(
                get_value=lambda doctype, name, fieldname=None, **kw:
                flag if fieldname == "is_drill" else None,
                set_value=lambda *a, **k: None)

        def explode(*a, **k):
            raise RuntimeError("db down")

        try:
            frappe.db = db_with_flag(1)  # drill record -> refused
            self.assertEqual(sites.sync_site_notices(
                "SWW-D", "-23.00,30.50", "flood", "warning"), 0)
            self.assertEqual(created, [])
            frappe.db = types.SimpleNamespace(  # unreadable -> fail closed
                get_value=explode, set_value=lambda *a, **k: None)
            self.assertEqual(sites.sync_site_notices(
                "SWW-D", "-23.00,30.50", "flood", "warning"), 0)
            self.assertEqual(created, [])
            frappe.db = db_with_flag(0)  # real record -> notice generated
            self.assertEqual(sites.sync_site_notices(
                "SWW-R", "-23.00,30.50", "flood", "warning"), 1)
            self.assertEqual(created, [1])
        finally:
            frappe.conf, frappe.db, frappe.get_all, frappe.get_doc = saved

    def test_ledger_propagation_and_live_upserts_exclude_drills(self):
        """The fence is a filter at every consumer - assert each one is in
        the committed source (the cheap tripwire the sibling suites use)."""
        checks = {
            "outcomes.py": 2,     # episode judgement + miss coverage
            "propagation.py": 2,  # seed fetch + advisory race guard
            "evaluator.py": 1,    # live upsert lookup
            "basin.py": 1,        # upstream_flood upsert lookup
        }
        for filename, expected in checks.items():
            with open(os.path.join(ENGINE_DIR, filename),
                      encoding="utf-8") as handle:
                source = handle.read()
            self.assertEqual(source.count('"is_drill": ["!=", 1]'), expected,
                             filename)


# --------------------------------------------------------------------------- #
# the admin endpoints
# --------------------------------------------------------------------------- #

class TestEndpoints(unittest.TestCase):
    def setUp(self):
        self._roles = frappe.get_roles
        frappe.get_roles = lambda *a: ["System Manager"]

    def tearDown(self):
        frappe.get_roles = self._roles

    def test_both_endpoints_require_system_manager(self):
        frappe.get_roles = lambda *a: ["Blogger"]
        with self.assertRaises(frappe.PermissionError):
            run_drill_api.run_drill("2024-02-01", "2024-02-05", "[]")
        with self.assertRaises(frappe.PermissionError):
            run_drill_api.clear_drill()

    def test_parse_locations_accepts_names_pairs_and_json(self):
        self.assertEqual(
            run_drill_api.parse_locations('["-23.00,30.50", [-24.0, 30.5]]'),
            ["-23.00,30.50", "-24.00,30.50"])
        self.assertEqual(
            run_drill_api.parse_locations("-22.987,30.462"),
            ["-23.00,30.50"])  # grid-rounded to the cell key
        with self.assertRaises(ValueError):
            run_drill_api.parse_locations("")
        with self.assertRaises(ValueError):
            run_drill_api.parse_locations("[]")

    def test_bad_dates_are_a_plain_language_refusal(self):
        out = run_drill_api.run_drill("not-a-date", "2024-02-05",
                                      '["-23.00,30.50"]')
        self.assertFalse(out["ok"])
        self.assertIn("start_date", out["error"])

    def test_unknown_locations_are_skipped_never_created(self):
        replayed = []
        saved_all, saved_run = frappe.get_all, drill.run_drill_replay
        # only the first requested cell is a registered watch location
        frappe.get_all = lambda doctype, **kw: [loc_row()]
        drill.run_drill_replay = (
            lambda rows, start, end, step_hours=None:
            replayed.extend(r.name for r in rows)
            or {"records": {"created": 0, "updated": 0, "expired": 0}})
        try:
            out = run_drill_api.run_drill(
                "2024-02-01", "2024-02-05",
                '["-23.00,30.50", "-99.00,99.00"]', speed=24)
        finally:
            frappe.get_all, drill.run_drill_replay = saved_all, saved_run
        self.assertTrue(out["ok"])
        self.assertEqual(out["skipped_locations"], ["-99.00,99.00"])
        self.assertEqual(replayed, ["-23.00,30.50"])  # never created

    def test_no_registered_locations_is_a_refusal(self):
        saved = frappe.get_all
        frappe.get_all = lambda doctype, **kw: []
        try:
            out = run_drill_api.run_drill("2024-02-01", "2024-02-05",
                                          '["-99.00,99.00"]')
        finally:
            frappe.get_all = saved
        self.assertFalse(out["ok"])
        self.assertIn("registered watch location", out["error"])

    def test_window_refusals_surface_verbatim(self):
        saved = frappe.get_all
        frappe.get_all = lambda doctype, **kw: [loc_row()]
        source = RecordingSource(horizon=dt.datetime(2024, 1, 1))
        with RunnerHarness(source=source):
            frappe.get_all = lambda doctype, **kw: [loc_row()]
            out = run_drill_api.run_drill("2024-02-01", "2024-02-05",
                                          '["-23.00,30.50"]')
        frappe.get_all = saved
        self.assertFalse(out["ok"])
        self.assertIn("archive horizon", out["error"])

    def test_clear_drill_reports_the_deleted_count(self):
        with RunnerHarness() as h:
            h.db.rows["SWW-D1"] = {"is_drill": 1, "drill_run_id": "r9"}
            saved = frappe.delete_doc
            frappe.delete_doc = lambda *a, **kw: None
            try:
                out = run_drill_api.clear_drill("r9")
            finally:
                frappe.delete_doc = saved
        self.assertEqual(out, {"ok": True, "deleted": 1, "run_id": "r9"})


if __name__ == "__main__":
    unittest.main()
