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

"""Offline tests for the vulnerable-site registry (wave 6).

Frappe is stubbed exactly like the sibling sw2-sw5 tests - no bench, no
network. Covers: the type-aware site copy (passability vs access phrasing,
route labels, tornado cap, the calm-copy legal constraint over every pair),
grid-cell auto-coverage on registration (the get_weather_warnings watch-
location pattern, throttled refresh, fail-closed on bad input), the hourly
coverage sweep, notice generation on active warning upserts (create,
escalation refresh, disabled-site silence, advisory/cold-front skip,
never-raise), the serve-time join that attaches marked site notices to the
warning payload (fail-closed: no site means the byte-identical pre-sw6
response), the evaluator's upsert hook, the System-Manager-only admin query
endpoint, and the manifest/doctype artifact registrations.
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
    # attributes this wave needs, whichever sibling installed the stub
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


def _load_modules():
    """Load the split src/ trees exactly as they compose (the sw5 pattern):
    wmod.warnings_engine (common) plus wmod.control with a real search path,
    so both the engine modules and the api endpoints import."""
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


_load_modules()
messages = importlib.import_module("wmod.warnings_engine.messages")
sites = importlib.import_module("wmod.control.warnings_engine.sites")
evaluator = importlib.import_module("wmod.control.warnings_engine.evaluator")
serve_ep = importlib.import_module(
    "wmod.control.api.get_weather_warnings.get_weather_warnings")
admin_ep = importlib.import_module(
    "wmod.control.api.get_site_notices.get_site_notices")

import frappe  # noqa: E402  (after stub install, like the sibling tests)


class Row(dict):
    """frappe._dict-alike: attribute AND .get access (None when missing)."""

    __getattr__ = dict.get


def _get_all_for(tables):
    """A frappe.get_all stand-in over in-memory tables, honoring plain
    equality filters and ["in", ...] filters (enough for this wave)."""

    def get_all(doctype, filters=None, fields=None, **kw):
        rows = list(tables.get(doctype, []))
        for key, val in (filters or {}).items():
            if isinstance(val, (list, tuple)):
                if val and val[0] == "in":
                    rows = [r for r in rows if r.get(key) in val[1]]
                # comparison operators: not needed by these fixtures
            else:
                rows = [r for r in rows if r.get(key) == val]
        return rows

    return get_all


def _fresh_frappe(tables=None):
    """Reset the shared frappe stub for one test."""
    frappe.conf = {}
    frappe.db = MagicMock()
    frappe.db.get_value = MagicMock(return_value=None)
    inserted = MagicMock()
    inserted.insert.return_value = None
    inserted.name = "NEW-1"
    frappe.get_doc = MagicMock(return_value=inserted)
    frappe.get_all = (_get_all_for(tables) if tables is not None
                      else MagicMock(return_value=[]))
    frappe.log_error = MagicMock()
    cache = MagicMock()
    cache.get_value = MagicMock(return_value=None)
    frappe.cache = MagicMock(return_value=cache)
    return inserted


NOW = dt.datetime(2026, 8, 22, 6, 0)

BRIDGE = Row(name="WVS-00001", site_name="Mutale low-water bridge",
             site_type="River Crossing", route_label="R523",
             latitude=-22.75, longitude=30.5, enabled=1,
             watch_location="-22.75,30.50")
SCHOOL = Row(name="WVS-00002", site_name="Tshakhuma Primary School",
             site_type="School", route_label=None,
             latitude=-22.76, longitude=30.51, enabled=1,
             watch_location="-22.75,30.50")
DISABLED = Row(name="WVS-00003", site_name="Old clinic",
               site_type="Clinic", route_label=None,
               latitude=-22.74, longitude=30.49, enabled=0,
               watch_location="-22.75,30.50")


# --------------------------------------------------------------------------- #
# site copy (messages.render_site_notice)
# --------------------------------------------------------------------------- #

class TestSiteCopy(unittest.TestCase):
    def test_every_pair_renders_and_names_the_site(self):
        for event_class in messages.SITE_CLASS_FAMILY:
            for severity in ("heads_up", "warning"):
                for site_type in messages.SITE_TYPES:
                    out = messages.render_site_notice(
                        event_class, severity, "Mutale bridge", site_type)
                    self.assertEqual(out["kind"], "site_notice")
                    self.assertIn("Mutale bridge", out["headline"])
                    self.assertIn("Mutale bridge", out["message"])
                    self.assertTrue(out["severity_label"])
                    self.assertIn(out["severity"], ("heads_up", "warning"))

    def test_passability_vs_access_phrasing(self):
        crossing = messages.render_site_notice(
            "flood", "warning", "Mutale low-water bridge", "River Crossing")
        self.assertIn("passable", crossing["headline"])
        self.assertIn("another route", crossing["message"])
        school = messages.render_site_notice(
            "flood", "warning", "Tshakhuma Primary School", "School")
        self.assertNotIn("passable", school["headline"])
        self.assertIn("plan ahead", school["message"])

    def test_route_label_is_rendered_with_the_site_name(self):
        out = messages.render_site_notice(
            "flash_flood", "warning", "the low-water crossing",
            "River Crossing", "R523")
        self.assertIn("the low-water crossing (R523)", out["message"])

    def test_tornado_site_notice_is_capped_to_heads_up(self):
        out = messages.render_site_notice(
            "tornado", "warning", "Mutale bridge", "Bridge")
        self.assertEqual(out["severity"], "heads_up")
        self.assertIn("Storms", out["headline"])

    def test_cold_front_and_advisory_never_surface(self):
        with self.assertRaises(KeyError):
            messages.render_site_notice(
                "cold_front", "advisory", "Mutale bridge", "Bridge")
        with self.assertRaises(KeyError):
            messages.render_site_notice(
                "upstream_flood", "advisory", "Mutale bridge", "Bridge")

    def test_no_site_string_uses_official_warning_taxonomy(self):
        # The house legal constraint (see test_warnings_engine.py): no
        # user-facing string may use "warning" or official taxonomy.
        banned = ("warning", "warn ", "yellow", "orange level", "red level",
                  "level 1", "level 2", "alert level")
        strings = []
        for event_class in messages.SITE_CLASS_FAMILY:
            for severity in ("heads_up", "warning"):
                for site_type in messages.SITE_TYPES:
                    out = messages.render_site_notice(
                        event_class, severity, "Messina crossing", site_type,
                        "R523")
                    strings += [out["headline"], out["message"],
                                out["severity_label"]]
        for s in strings:
            low = s.lower()
            for word in banned:
                self.assertNotIn(word, low, f"banned wording {word!r} in {s!r}")


# --------------------------------------------------------------------------- #
# grid coverage (registration auto-covers the cell)
# --------------------------------------------------------------------------- #

class TestCoverage(unittest.TestCase):
    def test_grid_key_matches_the_serving_endpoint_rounding(self):
        self.assertEqual(sites.grid_key_for(-22.98, 30.62), "-23.00,30.50")
        self.assertEqual(sites.grid_key_for(-22.75, 30.5), "-22.75,30.50")
        self.assertIsNone(sites.grid_key_for(None, 30.5))
        self.assertIsNone(sites.grid_key_for("x", 30.5))
        self.assertIsNone(sites.grid_key_for(-95.0, 30.5))

    def test_new_cell_is_registered_as_a_watch_location(self):
        inserted = _fresh_frappe()
        inserted.name = "-22.75,30.50"
        name = sites.ensure_site_cell_covered(-22.76, 30.51, NOW)
        self.assertEqual(name, "-22.75,30.50")
        doc = frappe.get_doc.call_args[0][0]
        self.assertEqual(doc["doctype"], "Weather Watch Location")
        self.assertEqual(doc["grid_key"], "-22.75,30.50")
        self.assertEqual(doc["latitude"], -22.75)
        self.assertEqual(doc["longitude"], 30.50)
        self.assertEqual(doc["active"], 1)
        self.assertEqual(doc["last_requested_at"], NOW)

    def test_existing_cell_is_refreshed_not_duplicated(self):
        _fresh_frappe()
        frappe.db.get_value = MagicMock(return_value=Row(
            name="-22.75,30.50", last_requested_at=NOW - dt.timedelta(days=2)))
        name = sites.ensure_site_cell_covered(-22.76, 30.51, NOW)
        self.assertEqual(name, "-22.75,30.50")
        frappe.get_doc.assert_not_called()
        frappe.db.set_value.assert_called_once_with(
            "Weather Watch Location", "-22.75,30.50",
            {"last_requested_at": NOW})

    def test_throttled_refresh_skips_the_write_when_fresh(self):
        _fresh_frappe()
        frappe.db.get_value = MagicMock(return_value=Row(
            name="-22.75,30.50", last_requested_at=NOW - dt.timedelta(hours=1)))
        name = sites.ensure_site_cell_covered(-22.76, 30.51, NOW,
                                              refresh_hours=6)
        self.assertEqual(name, "-22.75,30.50")
        frappe.db.set_value.assert_not_called()

    def test_failure_is_none_never_a_raise(self):
        _fresh_frappe()
        frappe.db.get_value = MagicMock(side_effect=RuntimeError("boom"))
        self.assertIsNone(sites.ensure_site_cell_covered(-22.76, 30.51, NOW))

    def test_hourly_pass_covers_enabled_sites_and_heals_the_link(self):
        moved = Row(BRIDGE, name="WVS-00009", watch_location="0.00,0.00")
        _fresh_frappe({"Weather Vulnerable Site": [moved, DISABLED]})
        frappe.db.get_value = MagicMock(return_value=Row(
            name="-22.75,30.50", last_requested_at=None))
        covered = sites.ensure_sites_covered(NOW)
        self.assertEqual(covered, 1)  # the disabled site is not swept
        frappe.db.set_value.assert_any_call(
            "Weather Vulnerable Site", "WVS-00009",
            {"watch_location": "-22.75,30.50"})

    def test_absent_registry_is_a_fail_closed_noop(self):
        _fresh_frappe()
        frappe.get_all = MagicMock(side_effect=RuntimeError("no such table"))
        self.assertEqual(sites.ensure_sites_covered(NOW), 0)

    def test_master_switch_disables_the_pass(self):
        _fresh_frappe({"Weather Vulnerable Site": [BRIDGE]})
        frappe.conf = {"severe_weather_sites_enabled": "0"}
        self.assertEqual(sites.ensure_sites_covered(NOW), 0)


# --------------------------------------------------------------------------- #
# notice generation on active warning upserts
# --------------------------------------------------------------------------- #

class TestSyncSiteNotices(unittest.TestCase):
    CELL = "-22.75,30.50"

    def test_no_sites_means_no_writes_at_all(self):
        _fresh_frappe({"Weather Vulnerable Site": []})
        n = sites.sync_site_notices("SWW-1", self.CELL, "flood", "warning", NOW)
        self.assertEqual(n, 0)
        frappe.get_doc.assert_not_called()
        frappe.db.set_value.assert_not_called()

    def test_absent_registry_is_a_fail_closed_noop(self):
        _fresh_frappe()
        frappe.get_all = MagicMock(side_effect=RuntimeError("no such table"))
        n = sites.sync_site_notices("SWW-1", self.CELL, "flood", "warning", NOW)
        self.assertEqual(n, 0)

    def test_enabled_site_gets_a_notice_disabled_site_stays_silent(self):
        _fresh_frappe({"Weather Vulnerable Site": [BRIDGE, DISABLED]})
        n = sites.sync_site_notices("SWW-1", self.CELL, "flash_flood",
                                    "warning", NOW)
        self.assertEqual(n, 1)
        self.assertEqual(frappe.get_doc.call_count, 1)
        doc = frappe.get_doc.call_args[0][0]
        self.assertEqual(doc["doctype"], "Weather Site Notice")
        self.assertEqual(doc["warning"], "SWW-1")
        self.assertEqual(doc["vulnerable_site"], "WVS-00001")
        self.assertEqual(doc["watch_location"], self.CELL)
        self.assertEqual(doc["event_class"], "flash_flood")
        self.assertEqual(doc["severity"], "warning")
        self.assertIn("Mutale low-water bridge (R523)", doc["message"])
        self.assertIn("passable", doc["headline"])
        self.assertNotIn("warning", doc["headline"].lower())
        self.assertNotIn("warning", doc["message"].lower())

    def test_refresh_same_severity_writes_nothing(self):
        _fresh_frappe({"Weather Vulnerable Site": [BRIDGE]})
        frappe.db.get_value = MagicMock(return_value=Row(
            name="WSN-1", severity="warning"))
        n = sites.sync_site_notices("SWW-1", self.CELL, "flood", "warning", NOW)
        self.assertEqual(n, 1)
        frappe.get_doc.assert_not_called()
        frappe.db.set_value.assert_not_called()

    def test_escalation_rewrites_the_copy(self):
        _fresh_frappe({"Weather Vulnerable Site": [BRIDGE]})
        frappe.db.get_value = MagicMock(return_value=Row(
            name="WSN-1", severity="heads_up"))
        n = sites.sync_site_notices("SWW-1", self.CELL, "flood", "warning", NOW)
        self.assertEqual(n, 1)
        frappe.get_doc.assert_not_called()
        fields = frappe.db.set_value.call_args[0][2]
        self.assertEqual(fields["severity"], "warning")
        self.assertIn("passable", fields["headline"])

    def test_advisory_and_cold_front_generate_nothing(self):
        _fresh_frappe({"Weather Vulnerable Site": [BRIDGE]})
        self.assertEqual(sites.sync_site_notices(
            "SWW-1", self.CELL, "upstream_flood", "advisory", NOW), 0)
        self.assertEqual(sites.sync_site_notices(
            "SWW-1", self.CELL, "cold_front", "advisory", NOW), 0)
        frappe.get_doc.assert_not_called()

    def test_master_switch_disables_generation(self):
        _fresh_frappe({"Weather Vulnerable Site": [BRIDGE]})
        frappe.conf = {"severe_weather_sites_enabled": "off"}
        self.assertEqual(sites.sync_site_notices(
            "SWW-1", self.CELL, "flood", "warning", NOW), 0)

    def test_never_raises_even_when_the_insert_does(self):
        _fresh_frappe({"Weather Vulnerable Site": [BRIDGE, SCHOOL]})
        frappe.get_doc = MagicMock(side_effect=RuntimeError("boom"))
        n = sites.sync_site_notices("SWW-1", self.CELL, "flood", "warning", NOW)
        self.assertEqual(n, 0)  # per-site isolation: counted only on success


# --------------------------------------------------------------------------- #
# serve-time join (the tenant proxy + push-sync fetch ride this payload)
# --------------------------------------------------------------------------- #

def _notice_row(warning, site, name="WSN-1"):
    return Row(name=name, warning=warning, vulnerable_site=site.name,
               site_name=site.site_name, site_type=site.site_type,
               severity="warning",
               headline=f"{site.site_name} may not be passable",
               message="Flooding is expected in this area.")


class TestServeJoin(unittest.TestCase):
    def test_notices_come_back_keyed_and_marked(self):
        _fresh_frappe({
            "Weather Site Notice": [_notice_row("SWW-1", BRIDGE)],
            "Weather Vulnerable Site": [BRIDGE],
        })
        out = sites.active_site_notices(["SWW-1", "SWW-2"])
        self.assertEqual(set(out), {"SWW-1"})
        notice = out["SWW-1"][0]
        self.assertEqual(notice["kind"], "site_notice")
        self.assertEqual(notice["site"], "WVS-00001")
        self.assertEqual(notice["site_type"], "River Crossing")
        self.assertEqual(notice["severity_label"], "Please take care")

    def test_notices_of_since_disabled_sites_are_filtered_out(self):
        _fresh_frappe({
            "Weather Site Notice": [_notice_row("SWW-1", DISABLED)],
            "Weather Vulnerable Site": [DISABLED],
        })
        self.assertEqual(sites.active_site_notices(["SWW-1"]), {})

    def test_fail_closed_on_any_problem(self):
        _fresh_frappe()
        frappe.get_all = MagicMock(side_effect=RuntimeError("boom"))
        self.assertEqual(sites.active_site_notices(["SWW-1"]), {})
        self.assertEqual(sites.active_site_notices([]), {})

    def test_endpoint_attaches_site_notices_to_their_warning(self):
        warning_rows = [
            Row(name="SWW-1", event_class="flood", severity="warning",
                headline="Flooding expected near Riverton",
                message="m", onset=None, valid_until=None, issued_at=None,
                status="active", watch_location="-22.75,30.50"),
            Row(name="SWW-2", event_class="tornado", severity="heads_up",
                headline="Storms possible near Riverton",
                message="m", onset=None, valid_until=None, issued_at=None,
                status="active", watch_location="-22.75,30.50"),
        ]
        _fresh_frappe({
            "Severe Weather Warning": warning_rows,
            "Weather Site Notice": [_notice_row("SWW-1", BRIDGE)],
            "Weather Vulnerable Site": [BRIDGE],
        })
        out = serve_ep._active_warnings("-22.75,30.50")
        self.assertEqual(len(out), 2)
        by_id = {w["id"]: w for w in out}
        self.assertEqual(by_id["SWW-1"]["site_notices"][0]["kind"],
                         "site_notice")
        self.assertNotIn("site_notices", by_id["SWW-2"])

    def test_endpoint_response_is_unchanged_without_sites(self):
        warning_rows = [
            Row(name="SWW-1", event_class="flood", severity="warning",
                headline="h", message="m", onset=None, valid_until=None,
                issued_at=None, status="active",
                watch_location="-22.75,30.50"),
        ]
        _fresh_frappe({
            "Severe Weather Warning": warning_rows,
            "Weather Site Notice": [],
            "Weather Vulnerable Site": [],
        })
        out = serve_ep._active_warnings("-22.75,30.50")
        self.assertEqual(set(out[0]), {
            "id", "event_class", "severity", "severity_label", "headline",
            "message", "onset", "valid_until", "issued_at"})

    def test_endpoint_join_failure_leaves_the_response_untouched(self):
        warning_rows = [
            Row(name="SWW-1", event_class="flood", severity="warning",
                headline="h", message="m", onset=None, valid_until=None,
                issued_at=None, status="active",
                watch_location="-22.75,30.50"),
        ]
        _fresh_frappe({"Severe Weather Warning": warning_rows})
        real = frappe.get_all

        def flaky(doctype, *a, **k):
            if doctype == "Weather Site Notice":
                raise RuntimeError("boom")
            return real(doctype, *a, **k)

        frappe.get_all = flaky
        out = serve_ep._active_warnings("-22.75,30.50")
        self.assertEqual(len(out), 1)
        self.assertNotIn("site_notices", out[0])


# --------------------------------------------------------------------------- #
# the evaluator hook: notices ride every active upsert
# --------------------------------------------------------------------------- #

class TestEvaluatorHook(unittest.TestCase):
    def setUp(self):
        self._fusion = evaluator.fusion.fuse_warning
        self._push = evaluator.push.notify_warning_upsert
        self._sync = sites.sync_site_notices

    def tearDown(self):
        evaluator.fusion.fuse_warning = self._fusion
        evaluator.push.notify_warning_upsert = self._push
        sites.sync_site_notices = self._sync

    def test_upsert_warning_syncs_site_notices_after_push(self):
        inserted = _fresh_frappe()
        inserted.insert.return_value = inserted
        inserted.name = "SWW-42"
        evaluator.fusion.fuse_warning = lambda loc, ec, sev, conf, now: (
            sev, {"severity": sev, "headline": "h", "message": "m"}, {})
        evaluator.push.notify_warning_upsert = MagicMock()
        sites.sync_site_notices = MagicMock(return_value=1)

        episode = types.SimpleNamespace(
            fired_conditions=("precip",), max_confidence=0.9,
            first_fired_at=dt.datetime(2026, 8, 21, 18))
        result = types.SimpleNamespace(tier=[3], alarms=[episode],
                                       confidence=[0.9])
        loc = Row(name="-22.75,30.50", label="Riverton")
        source = types.SimpleNamespace(name="src")
        horizon = NOW

        evaluator._upsert_warning(loc, "flood", result, source, horizon, NOW)

        evaluator.push.notify_warning_upsert.assert_called_once()
        sites.sync_site_notices.assert_called_once_with(
            "SWW-42", "-22.75,30.50", "flood", "warning", NOW)


# --------------------------------------------------------------------------- #
# the admin query endpoint
# --------------------------------------------------------------------------- #

class TestAdminEndpoint(unittest.TestCase):
    def _tables(self):
        notice = Row(name="WSN-1", warning="SWW-1",
                     vulnerable_site="WVS-00001",
                     watch_location="-22.75,30.50", event_class="flood",
                     site_name=BRIDGE.site_name, site_type=BRIDGE.site_type,
                     severity="warning", headline="h", message="m",
                     generated_at=NOW)
        stale = Row(notice, name="WSN-2", warning="SWW-9")
        return {
            "Weather Site Notice": [notice, stale],
            "Severe Weather Warning": [
                # _build compares valid_until against the REAL utcnow, so the
                # live fixture must be anchored to the wall clock - a fixed
                # date here rots the moment it passes
                Row(name="SWW-1", status="active",
                    valid_until=dt.datetime.utcnow() + dt.timedelta(hours=24)),
                Row(name="SWW-9", status="expired",
                    valid_until=NOW - dt.timedelta(hours=24)),
            ],
        }

    def test_requires_system_manager(self):
        _fresh_frappe(self._tables())
        frappe.get_roles = MagicMock(return_value=["Accounts User"])
        with self.assertRaises(frappe.PermissionError):
            admin_ep.get_site_notices()

    def test_active_filter_serves_only_live_notices(self):
        _fresh_frappe(self._tables())
        frappe.get_roles = MagicMock(return_value=["System Manager"])
        out = admin_ep._build(None, "active", None)
        self.assertEqual([n["id"] for n in out["notices"]], ["WSN-1"])
        notice = out["notices"][0]
        self.assertTrue(notice["live"])
        self.assertEqual(notice["kind"], "site_notice")
        self.assertEqual(notice["warning_status"], "active")
        self.assertEqual(notice["severity_label"], "Please take care")

    def test_all_filter_includes_history(self):
        _fresh_frappe(self._tables())
        frappe.get_roles = MagicMock(return_value=["System Manager"])
        out = admin_ep._build(None, "all", None)
        self.assertEqual({n["id"] for n in out["notices"]},
                         {"WSN-1", "WSN-2"})
        by_id = {n["id"]: n for n in out["notices"]}
        self.assertFalse(by_id["WSN-2"]["live"])

    def test_site_filter_and_error_containment(self):
        _fresh_frappe(self._tables())
        frappe.get_roles = MagicMock(return_value=["System Manager"])
        out = admin_ep._build("WVS-77777", "all", None)
        self.assertEqual(out["notices"], [])
        frappe.get_all = MagicMock(side_effect=RuntimeError("boom"))
        out = admin_ep.get_site_notices()
        self.assertTrue(out["error"])
        self.assertEqual(out["notices"], [])


# --------------------------------------------------------------------------- #
# artifact registrations
# --------------------------------------------------------------------------- #

class TestArtifacts(unittest.TestCase):
    def _read(self, *parts):
        path = os.path.join(FRAPPE_MODULE_DIR, *parts)
        with open(path, newline="") as f:
            raw = f.read()
        self.assertNotIn("\r", raw, f"{path} must use LF endings")
        return json.loads(raw)

    def test_doctype_jsons_are_valid_and_consistent(self):
        site = self._read("src", "control", "doctype",
                          "weather_vulnerable_site",
                          "weather_vulnerable_site.json")
        self.assertEqual(site["name"], "Weather Vulnerable Site")
        fieldnames = {f["fieldname"] for f in site["fields"]}
        self.assertLessEqual(
            {"site_name", "site_type", "latitude", "longitude",
             "route_label", "enabled", "watch_location", "tenant_site"},
            fieldnames)
        types_field = next(f for f in site["fields"]
                           if f["fieldname"] == "site_type")
        self.assertEqual(tuple(types_field["options"].split("\n")),
                         messages.SITE_TYPES)
        notice = self._read("src", "control", "doctype",
                            "weather_site_notice", "weather_site_notice.json")
        self.assertEqual(notice["name"], "Weather Site Notice")
        fieldnames = {f["fieldname"] for f in notice["fields"]}
        self.assertLessEqual(
            {"warning", "vulnerable_site", "severity", "headline", "message"},
            fieldnames)

    def test_manifest_registers_the_wave(self):
        manifest = self._read("manifest.json")
        control = manifest["app_type"]["control"]["hooks"]
        fixture_names = {f["filters"][0][2] for f in control["fixtures"]}
        self.assertIn("Weather Vulnerable Site", fixture_names)
        self.assertIn("Weather Site Notice", fixture_names)
        self.assertIn("{app_name}.api.get_site_notices",
                      control["whitelisted_methods"])


if __name__ == "__main__":
    unittest.main()
