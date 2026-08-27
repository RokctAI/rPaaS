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

"""Offline tests for the CAP 1.2 feed endpoint (sw6).

Fixture warning records only - no network, no bench. Frappe is stubbed
exactly like the sibling engine test files. Covers: well-formed XML with the
required CAP 1.2 elements, the frozen internal-severity -> CAP
urgency/severity/certainty mapping, the record validity window on
effective/onset/expires (with the CAP-required explicit +00:00 offset), the
grid-cell circle area, the calm-copy wording rule in every end-user-facing
text field, the Open-Meteo attribution, deterministic identifiers/sent
values, drill records (excluded by default, CAP status Exercise on explicit
request), malformed-record skipping, the System Manager gate, and the
graceful empty/error feed.
"""

import datetime as dt
import importlib
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock
from xml.etree import ElementTree as ET

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
    import frappe
    if not hasattr(frappe, "get_roles"):
        frappe.get_roles = MagicMock(return_value=["System Manager"])
    if not hasattr(frappe, "PermissionError"):
        frappe.PermissionError = type("PermissionError", (Exception,), {})
    if not hasattr(frappe, "local"):
        frappe.local = types.SimpleNamespace(response={})


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
        "wmod.control.api.get_cap_feed.get_cap_feed")


cap = _load_endpoint()

import frappe  # noqa: E402  (after stub install, like the sibling tests)

CAP = "{urn:oasis:names:tc:emergency:cap:1.2}"
ATOM = "{http://www.w3.org/2005/Atom}"

ISSUED = dt.datetime(2026, 2, 10, 6, 0, 0)
ONSET = dt.datetime(2026, 2, 9, 20, 0, 0)
VALID = dt.datetime(2026, 2, 12, 6, 0, 0)


def record(name="SWW-2026-00001", event_class="flood", severity="heads_up",
           lat=-23.0, lon=30.5, label="Thohoyandou", is_drill=0,
           headline="Flooding possible near Thohoyandou",
           message=("Rivers and low ground around Thohoyandou are getting "
                    "very wet. Flooding is possible over the next few days.")):
    return {
        "name": name, "event_class": event_class, "severity": severity,
        "headline": headline, "message": message,
        "onset": ONSET, "valid_until": VALID, "issued_at": ISSUED,
        "latitude": lat, "longitude": lon, "label": label,
        "is_drill": is_drill,
    }


def alerts_of(xml: str):
    root = ET.fromstring(xml)
    return root, root.findall(f".//{ATOM}content/{CAP}alert")


# --------------------------------------------------------------------------- #
# structure
# --------------------------------------------------------------------------- #

class TestFeedStructure(unittest.TestCase):
    def test_feed_is_wellformed_atom_with_one_alert_per_record(self):
        xml = cap.build_cap_feed([record(), record(name="SWW-2026-00002",
                                                   severity="warning")])
        root, alerts = alerts_of(xml)
        self.assertEqual(root.tag, f"{ATOM}feed")
        self.assertEqual(len(alerts), 2)
        self.assertEqual(len(root.findall(f"{ATOM}entry")), 2)
        self.assertIsNotNone(root.find(f"{ATOM}id"))
        self.assertIsNotNone(root.find(f"{ATOM}title"))
        self.assertIsNotNone(root.find(f"{ATOM}updated"))

    def test_alert_carries_every_required_cap_element(self):
        _, (alert,) = alerts_of(cap.build_cap_feed([record()]))
        for tag in ("identifier", "sender", "sent", "status", "msgType",
                    "scope"):
            self.assertIsNotNone(alert.find(f"{CAP}{tag}"), tag)
        info = alert.find(f"{CAP}info")
        self.assertIsNotNone(info)
        for tag in ("category", "event", "urgency", "severity", "certainty",
                    "effective", "onset", "expires", "headline",
                    "description", "area"):
            self.assertIsNotNone(info.find(f"{CAP}{tag}"), tag)
        self.assertEqual(info.find(f"{CAP}category").text, "Met")
        self.assertEqual(alert.find(f"{CAP}status").text, "Actual")
        self.assertEqual(alert.find(f"{CAP}msgType").text, "Alert")
        self.assertEqual(alert.find(f"{CAP}scope").text, "Public")

    def test_empty_feed_is_still_valid_xml(self):
        xml = cap.build_cap_feed([], now=dt.datetime(2026, 2, 10, 6, 0, 0))
        root, alerts = alerts_of(xml)
        self.assertEqual(root.tag, f"{ATOM}feed")
        self.assertEqual(alerts, [])
        self.assertEqual(root.find(f"{ATOM}updated").text,
                         "2026-02-10T06:00:00+00:00")

    def test_malformed_record_is_skipped_not_fatal(self):
        broken = record(name="SWW-2026-00009")
        broken["issued_at"] = None  # no sent -> unrenderable
        xml = cap.build_cap_feed([record(), broken])
        _, alerts = alerts_of(xml)
        self.assertEqual(len(alerts), 1)


# --------------------------------------------------------------------------- #
# mapping + validity window
# --------------------------------------------------------------------------- #

class TestMapping(unittest.TestCase):
    def _info(self, severity):
        _, (alert,) = alerts_of(cap.build_cap_feed([record(severity=severity)]))
        info = alert.find(f"{CAP}info")
        return {tag: info.find(f"{CAP}{tag}").text
                for tag in ("urgency", "severity", "certainty")}

    def test_documented_tier_mapping(self):
        self.assertEqual(self._info("advisory"),
                         {"urgency": "Future", "severity": "Minor",
                          "certainty": "Possible"})
        self.assertEqual(self._info("heads_up"),
                         {"urgency": "Expected", "severity": "Moderate",
                          "certainty": "Possible"})
        self.assertEqual(self._info("warning"),
                         {"urgency": "Expected", "severity": "Severe",
                          "certainty": "Likely"})

    def test_unknown_internal_severity_is_skipped_fail_closed(self):
        xml = cap.build_cap_feed([record(severity="mystery")])
        _, alerts = alerts_of(xml)
        self.assertEqual(alerts, [])

    def test_validity_window_and_cap_offset_format(self):
        _, (alert,) = alerts_of(cap.build_cap_feed([record()]))
        info = alert.find(f"{CAP}info")
        self.assertEqual(alert.find(f"{CAP}sent").text,
                         "2026-02-10T06:00:00+00:00")
        self.assertEqual(info.find(f"{CAP}effective").text,
                         "2026-02-10T06:00:00+00:00")
        self.assertEqual(info.find(f"{CAP}onset").text,
                         "2026-02-09T20:00:00+00:00")
        self.assertEqual(info.find(f"{CAP}expires").text,
                         "2026-02-12T06:00:00+00:00")
        for el in alert.iter():
            if el.tag in (f"{CAP}sent", f"{CAP}effective", f"{CAP}onset",
                          f"{CAP}expires"):
                self.assertTrue(el.text.endswith("+00:00"))
                self.assertNotIn("Z", el.text)  # CAP 1.2 disallows Z

    def test_area_circle_covers_the_grid_cell(self):
        _, (alert,) = alerts_of(cap.build_cap_feed([record(lat=-23.0,
                                                           lon=30.5)]))
        area = alert.find(f"{CAP}info/{CAP}area")
        self.assertEqual(area.find(f"{CAP}areaDesc").text, "Thohoyandou")
        center, radius = area.find(f"{CAP}circle").text.split(" ")
        self.assertEqual(center, "-23.00,30.50")
        radius = float(radius)
        # half-diagonal of a 0.25 deg cell: >= the 13.9 km half-height,
        # <= the equatorial half-diagonal (~19.7 km)
        self.assertGreaterEqual(radius, 13.9)
        self.assertLessEqual(radius, 19.7)
        # latitude dependence: cells shrink east-west toward the poles
        _, (polar,) = alerts_of(cap.build_cap_feed([record(lat=-60.0)]))
        polar_r = float(polar.find(
            f"{CAP}info/{CAP}area/{CAP}circle").text.split(" ")[1])
        self.assertLess(polar_r, radius)


# --------------------------------------------------------------------------- #
# wording + attribution
# --------------------------------------------------------------------------- #

#: CAP elements whose text is protocol vocabulary, not end-user copy.
PROTOCOL_TAGS = {f"{CAP}{t}" for t in (
    "identifier", "sender", "sent", "status", "msgType", "scope",
    "language", "category", "urgency", "severity", "certainty",
    "effective", "onset", "expires", "circle", "valueName")}


class TestWording(unittest.TestCase):
    def test_no_forbidden_words_in_end_user_text_fields(self):
        records = [record(event_class=c, severity=s)
                   for c in cap.EVENT_NAMES
                   for s in ("advisory", "heads_up", "warning")]
        _, alerts = alerts_of(cap.build_cap_feed(records))
        self.assertTrue(alerts)
        for alert in alerts:
            for el in alert.iter():
                if el.tag in PROTOCOL_TAGS or not (el.text or "").strip():
                    continue
                text = el.text.lower()
                self.assertNotIn("warning", text, el.tag)
                for level in ("yellow level", "orange level", "red level",
                              "level 2", "level 5", "level 9"):
                    self.assertNotIn(level, text, el.tag)

    def test_headline_and_description_are_the_stored_calm_copy(self):
        rec = record()
        _, (alert,) = alerts_of(cap.build_cap_feed([rec]))
        info = alert.find(f"{CAP}info")
        self.assertEqual(info.find(f"{CAP}headline").text, rec["headline"])
        self.assertEqual(info.find(f"{CAP}description").text, rec["message"])

    def test_every_event_class_has_a_calm_event_name(self):
        messages = importlib.import_module("wmod.warnings_engine.messages")
        self.assertEqual(set(cap.EVENT_NAMES),
                         set(messages.CLASS_MAX_SEVERITY))

    def test_open_meteo_attribution_is_carried(self):
        messages = importlib.import_module("wmod.warnings_engine.messages")
        xml = cap.build_cap_feed([record()])
        root, (alert,) = alerts_of(xml)
        params = alert.findall(f"{CAP}info/{CAP}parameter")
        values = {p.find(f"{CAP}valueName").text: p.find(f"{CAP}value").text
                  for p in params}
        self.assertEqual(values.get("attribution"), messages.ATTRIBUTION)
        self.assertEqual(root.find(f"{ATOM}rights").text,
                         messages.ATTRIBUTION)


# --------------------------------------------------------------------------- #
# determinism + drills
# --------------------------------------------------------------------------- #

class TestDeterminismAndDrills(unittest.TestCase):
    def test_identical_records_render_byte_identical_feeds(self):
        records = [record(), record(name="SWW-2026-00002",
                                    severity="warning")]
        self.assertEqual(cap.build_cap_feed(records),
                         cap.build_cap_feed(list(reversed(records))))

    def test_identifier_and_sent_derive_from_record_data(self):
        _, (alert,) = alerts_of(cap.build_cap_feed([record()]))
        self.assertEqual(
            alert.find(f"{CAP}identifier").text,
            f"{cap.DEFAULT_SENDER}.SWW-2026-00001.20260210T060000")
        self.assertEqual(alert.find(f"{CAP}sent").text,
                         "2026-02-10T06:00:00+00:00")

    def test_drill_record_renders_as_exercise(self):
        _, (alert,) = alerts_of(cap.build_cap_feed([record(is_drill=1)]))
        self.assertEqual(alert.find(f"{CAP}status").text, "Exercise")


# --------------------------------------------------------------------------- #
# the endpoint (frappe-side)
# --------------------------------------------------------------------------- #

class _Row(dict):
    __getattr__ = dict.get


class TestEndpoint(unittest.TestCase):
    def setUp(self):
        self._saved = (frappe.get_all, frappe.get_roles, frappe.conf)
        frappe.conf = {}
        frappe.get_roles = lambda *a: ["System Manager"]
        self.filters_seen = {}

        def fake_get_all(doctype, filters=None, fields=None,
                         limit_page_length=None):
            self.filters_seen[doctype] = filters
            if doctype == cap.WARNING_DOCTYPE:
                rows = [_Row(record()), _Row(record(name="SWW-2026-00002",
                                                    is_drill=1))]
                if filters.get("is_drill") == ["!=", 1]:
                    rows = [r for r in rows if not r.get("is_drill")]
                for r in rows:
                    r["watch_location"] = "-23.00,30.50"
                return rows
            return [_Row(name="-23.00,30.50", latitude=-23.0,
                         longitude=30.5, label="Thohoyandou")]

        frappe.get_all = fake_get_all

    def tearDown(self):
        frappe.get_all, frappe.get_roles, frappe.conf = self._saved

    def test_requires_system_manager(self):
        frappe.get_roles = lambda *a: ["Blogger"]
        with self.assertRaises(frappe.PermissionError):
            cap.get_cap_feed()

    def test_default_feed_excludes_drills(self):
        xml = cap.get_cap_feed()
        _, alerts = alerts_of(xml)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].find(f"{CAP}status").text, "Actual")
        self.assertEqual(
            self.filters_seen[cap.WARNING_DOCTYPE].get("is_drill"),
            ["!=", 1])

    def test_explicit_flag_includes_drills_as_exercise(self):
        xml = cap.get_cap_feed(include_drills="1")
        _, alerts = alerts_of(xml)
        self.assertEqual(len(alerts), 2)
        statuses = {a.find(f"{CAP}status").text for a in alerts}
        self.assertEqual(statuses, {"Actual", "Exercise"})

    def test_garbage_flag_fails_closed(self):
        xml = cap.get_cap_feed(include_drills="definitely")
        _, alerts = alerts_of(xml)
        self.assertEqual(len(alerts), 1)

    def test_internal_error_yields_a_valid_empty_feed(self):
        def explode(*a, **k):
            raise RuntimeError("db down")
        frappe.get_all = explode
        root, alerts = alerts_of(cap.get_cap_feed())
        self.assertEqual(root.tag, f"{ATOM}feed")
        self.assertEqual(alerts, [])


if __name__ == "__main__":
    unittest.main()
