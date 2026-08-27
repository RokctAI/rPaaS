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

"""Offline tests for the admin retraining report endpoint (sw5).

Fixture ledger rows only - no network, no bench. Frappe is stubbed exactly
like the sibling engine test files. Covers: the empty ledger (the common
early state - every class says insufficient_data, nothing divides by zero),
a thin ledger (counts reported, still insufficient), mixed outcomes with
exact observed POD / FAR / median-lead arithmetic and the per-class
meeting_bar / below_bar verdicts, the observed-lead proxy (class-relevant
peak, malformed evidence never raises), the frozen thresholds matching
PLAN.md verbatim, the System Manager gate, the graceful error payload, and
the human-readable summary string.
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

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FRAPPE_MODULE_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
COMMON_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "warnings_engine")
CONTROL_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "control")


def _ensure_frappe_stub():
    try:
        import frappe  # noqa: F401
    except ImportError:
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
    # attributes this endpoint needs, whichever sibling installed the stub
    import frappe
    if not hasattr(frappe, "get_roles"):
        frappe.get_roles = MagicMock(return_value=["System Manager"])
    if not hasattr(frappe, "PermissionError"):
        frappe.PermissionError = type("PermissionError", (Exception,), {})


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


def _load_endpoint():
    """Load the split src/ trees exactly as they compose: wmod.warnings_engine
    (common: admin_log) and wmod.control (the control persona folder), so the
    endpoint's relative import into common resolves. A sibling test file may
    already have registered wmod.control as a bare package (path-less); make
    sure its search path covers src/control either way."""
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
    return importlib.import_module(
        "wmod.control.api.get_retraining_report.get_retraining_report")


report = _load_endpoint()

import frappe  # noqa: E402  (after stub install, like the sibling tests)


# --------------------------------------------------------------------------- #
# fixture ledger rows
# --------------------------------------------------------------------------- #

def evidence_json(start="2026-02-01T00:00:00", precip_peak=None,
                  gust_peak=None):
    return json.dumps({
        "version": 1,
        "kind": "episode",
        "window": {"start": start, "end": "2026-02-05T00:00:00"},
        "observed": {"max_precip_24h_mm": 60.0,
                     "precip_peak_at": precip_peak,
                     "precip_weekly_pctl": 0.93,
                     "max_gust_ms": 24.0,
                     "gust_peak_at": gust_peak,
                     "gust_pctl": None},
    })


def rows_of(event_class, verdict, n, evidence=None):
    return [{"event_class": event_class, "verdict": verdict,
             "evidence": evidence} for _ in range(n)]


def wind_hit_rows(n, lead_h=18):
    peak = (dt.datetime(2026, 2, 1) + dt.timedelta(hours=lead_h)).isoformat()
    return rows_of("destructive_wind", "verified", n,
                   evidence_json(gust_peak=peak))


def flood_hit_rows(klass, n, lead_h):
    peak = (dt.datetime(2026, 2, 1) + dt.timedelta(hours=lead_h)).isoformat()
    return rows_of(klass, "verified", n, evidence_json(precip_peak=peak))


# --------------------------------------------------------------------------- #
# pure aggregation
# --------------------------------------------------------------------------- #

class TestEmptyLedger(unittest.TestCase):
    """The common early state: no rows at all."""

    def test_every_class_insufficient_and_nothing_divides_by_zero(self):
        payload = report.build_report([])
        self.assertEqual(payload["total_outcomes"], 0)
        for klass in report.EVENT_CLASSES:
            c = payload["classes"][klass]
            self.assertEqual(c["verdict"],
                             report.CLASS_VERDICT_INSUFFICIENT)
            self.assertEqual(c["counts"]["total"], 0)
            self.assertIsNone(c["observed"]["pod"])
            self.assertIsNone(c["observed"]["far"])
            self.assertIsNone(c["observed"]["median_lead_h"])
            self.assertIn("insufficient data", c["detail"])

    def test_summary_text_renders_for_empty_ledger(self):
        payload = report.build_report([])
        self.assertIn("INSUFFICIENT DATA", payload["summary"])
        self.assertIn("0 judged outcome(s)", payload["summary"])


class TestThinLedger(unittest.TestCase):
    """A handful of rows: counts reported, verdict stays insufficient."""

    def test_below_minimum_is_insufficient_with_counts(self):
        rows = (rows_of("flash_flood", "verified", 2)
                + rows_of("flash_flood", "unverified", 1)
                + rows_of("flash_flood", "candidate_miss", 1))
        c = report.build_report(rows)["classes"]["flash_flood"]
        self.assertEqual(c["verdict"], report.CLASS_VERDICT_INSUFFICIENT)
        self.assertEqual(c["counts"],
                         {"total": 4, "hits": 2, "false_alarms": 1,
                          "candidate_misses": 1})
        self.assertIn("2 hit(s)", c["detail"])
        self.assertIn("1 false alarm(s)", c["detail"])
        self.assertIn("1 candidate miss(es)", c["detail"])

    def test_exactly_minimum_earns_a_verdict(self):
        rows = wind_hit_rows(report.MIN_OUTCOMES_FOR_VERDICT)
        c = report.build_report(rows)["classes"]["destructive_wind"]
        self.assertNotEqual(c["verdict"], report.CLASS_VERDICT_INSUFFICIENT)

    def test_unknown_event_class_is_counted_not_dropped(self):
        rows = [{"event_class": "hail", "verdict": "verified"},
                {"event_class": None, "verdict": "verified"}]
        classes = report.build_report(rows)["classes"]
        self.assertEqual(classes["_unclassified"]["counts"]["total"], 2)


class TestMixedOutcomes(unittest.TestCase):
    """Enough evidence: exact arithmetic and per-class verdicts."""

    def test_meeting_bar_class(self):
        # 24 hits (18 h observed lead), 6 false alarms, no candidate misses:
        # POD 1.0 (>=0.70), FAR 6/30 = 0.2 (<=0.40), lead 18 h (>=12 h).
        rows = wind_hit_rows(24, lead_h=18) + rows_of(
            "destructive_wind", "unverified", 6)
        c = report.build_report(rows)["classes"]["destructive_wind"]
        self.assertEqual(c["observed"]["pod"], 1.0)
        self.assertEqual(c["observed"]["far"], 0.2)
        self.assertEqual(c["observed"]["median_lead_h"], 18.0)
        self.assertEqual(c["checks"], {"pod": "pass", "far": "pass",
                                       "median_lead": "pass"})
        self.assertEqual(c["verdict"], report.CLASS_VERDICT_MEETING)

    def test_below_bar_on_pod(self):
        # 10 hits, 5 false alarms, 15 candidate misses:
        # POD 10/25 = 0.4 < 0.60 (fail), FAR 5/15 = 0.333 <= 0.60 (pass).
        rows = (flood_hit_rows("flash_flood", 10, lead_h=8)
                + rows_of("flash_flood", "unverified", 5)
                + rows_of("flash_flood", "candidate_miss", 15))
        c = report.build_report(rows)["classes"]["flash_flood"]
        self.assertEqual(c["observed"]["pod"], 0.4)
        self.assertEqual(c["observed"]["far"], 0.333)
        self.assertEqual(c["checks"]["pod"], "fail")
        self.assertEqual(c["checks"]["far"], "pass")
        self.assertEqual(c["verdict"], report.CLASS_VERDICT_BELOW)
        self.assertIn("below bar on pod", c["detail"])

    def test_below_bar_on_lead(self):
        # flood needs median lead >= 24 h; hits peak after only 6 h.
        rows = (flood_hit_rows("flood", 20, lead_h=6)
                + rows_of("flood", "unverified", 2))
        c = report.build_report(rows)["classes"]["flood"]
        self.assertEqual(c["observed"]["median_lead_h"], 6.0)
        self.assertEqual(c["checks"]["median_lead"], "fail")
        self.assertEqual(c["verdict"], report.CLASS_VERDICT_BELOW)

    def test_all_misses_is_below_bar_not_a_crash(self):
        rows = rows_of("tornado", "candidate_miss", 25)
        c = report.build_report(rows)["classes"]["tornado"]
        self.assertEqual(c["observed"]["pod"], 0.0)
        self.assertIsNone(c["observed"]["far"])       # zero alarms judged
        self.assertEqual(c["checks"]["far"], "not_computable")
        self.assertEqual(c["verdict"], report.CLASS_VERDICT_BELOW)

    def test_missing_leads_noted_but_not_fatal(self):
        # verified rows without usable evidence: POD/FAR still computable,
        # median lead is not - verdict can still be meeting_bar, with a note.
        rows = (rows_of("destructive_wind", "verified", 24)
                + rows_of("destructive_wind", "unverified", 6))
        c = report.build_report(rows)["classes"]["destructive_wind"]
        self.assertIsNone(c["observed"]["median_lead_h"])
        self.assertEqual(c["checks"]["median_lead"], "not_computable")
        self.assertEqual(c["verdict"], report.CLASS_VERDICT_MEETING)
        self.assertIn("lead not yet computable", c["detail"])

    def test_summary_text_names_each_class_verdict(self):
        rows = wind_hit_rows(24) + rows_of("destructive_wind",
                                           "unverified", 6)
        summary = report.build_report(rows)["summary"]
        self.assertIn("destructive_wind: MEETING BAR", summary)
        self.assertIn("flood: INSUFFICIENT DATA", summary)
        self.assertIn("PLAN.md", summary)


class TestObservedLead(unittest.TestCase):
    def test_rain_class_uses_precip_peak(self):
        ev = evidence_json(precip_peak="2026-02-01T08:00:00",
                           gust_peak="2026-02-01T20:00:00")
        self.assertEqual(report.observed_lead_hours("flash_flood", ev), 8.0)

    def test_wind_class_uses_gust_peak(self):
        ev = evidence_json(precip_peak="2026-02-01T08:00:00",
                           gust_peak="2026-02-01T20:00:00")
        self.assertEqual(
            report.observed_lead_hours("destructive_wind", ev), 20.0)

    def test_malformed_evidence_never_raises(self):
        for bad in (None, "", "not json", "[]", json.dumps({"window": {}}),
                    json.dumps({"window": {"start": "junk"},
                                "observed": {"gust_peak_at": "junk"}})):
            self.assertIsNone(report.observed_lead_hours("tornado", bad))

    def test_peak_before_window_start_is_rejected(self):
        ev = evidence_json(start="2026-02-02T00:00:00",
                           gust_peak="2026-02-01T00:00:00")
        self.assertIsNone(report.observed_lead_hours("tornado", ev))


class TestFrozenThresholds(unittest.TestCase):
    def test_thresholds_match_plan_md_verbatim(self):
        self.assertEqual(report.FROZEN_THRESHOLDS, {
            "flash_flood":      {"pod": 0.60, "far": 0.60, "min_lead_h": 6},
            "flood":            {"pod": 0.65, "far": 0.50, "min_lead_h": 24},
            "destructive_wind": {"pod": 0.70, "far": 0.40, "min_lead_h": 12},
            "tornado":          {"pod": 0.40, "far": 0.75, "min_lead_h": 3},
        })


# --------------------------------------------------------------------------- #
# the whitelisted endpoint
# --------------------------------------------------------------------------- #

class TestEndpoint(unittest.TestCase):
    def setUp(self):
        frappe.get_roles = MagicMock(return_value=["System Manager", "All"])
        frappe.get_all = MagicMock(return_value=[])

    def test_admin_gets_a_report_over_the_full_ledger(self):
        frappe.get_all.return_value = (
            wind_hit_rows(24) + rows_of("destructive_wind", "unverified", 6))
        payload = report.get_retraining_report()
        self.assertTrue(payload["admin_only"])
        self.assertEqual(payload["total_outcomes"], 30)
        self.assertEqual(
            payload["classes"]["destructive_wind"]["verdict"],
            report.CLASS_VERDICT_MEETING)
        # the whole ledger, unpaginated
        _, kwargs = frappe.get_all.call_args
        self.assertEqual(kwargs.get("limit_page_length"), 0)

    def test_non_admin_is_refused(self):
        frappe.get_roles.return_value = ["All", "Guest"]
        with self.assertRaises(frappe.PermissionError):
            report.get_retraining_report()
        frappe.get_all.assert_not_called()

    def test_internal_error_yields_graceful_payload(self):
        frappe.get_all.side_effect = RuntimeError("db exploded")
        payload = report.get_retraining_report()
        self.assertTrue(payload["error"])
        self.assertEqual(payload["classes"], {})
        self.assertIn("Error Log", payload["summary"])


if __name__ == "__main__":
    unittest.main()
