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

"""The control-side retraining-report endpoint, pinned standalone (no
frappe, no site — `python -m unittest`, frappe stubbed for the role gate).

The boundaries these tests exist to hold: **the endpoint is admin
telemetry (System Manager only)**, **it is control-plane only — the tenant
manifest deliberately exposes no outcome/retraining surface**, and **an
internal failure answers in-band, never with a traceback.**
"""

import datetime as dt
import importlib.util
import json
import os
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_FRAPPE_ROOT = os.path.abspath(
    os.path.join(_TESTS_DIR, "..", "..", "..", ".."))
_CONTROL_DIR = os.path.join(_FRAPPE_ROOT, "src", "control")
_API_PATH = os.path.join(_CONTROL_DIR, "api", "get_forex_retraining_report",
                         "get_forex_retraining_report.py")

_spec = importlib.util.spec_from_file_location(
    "rforex_get_forex_retraining_report", _API_PATH)
api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(api)

with open(os.path.join(_FRAPPE_ROOT, "manifest.json")) as handle:
    MANIFEST = json.load(handle)

CONTROL_HOOKS = MANIFEST["app_type"]["control"]["hooks"]
CONTROL_TARGET_PREFIX = "{app_name}.rforex.control."


class _FrappeStub:
    """The two things the endpoint touches: roles and the error log."""

    class PermissionError(Exception):
        pass

    def __init__(self, roles):
        self._roles = list(roles)
        self.logged = []

    def get_roles(self):
        return list(self._roles)

    def log_error(self, title=None, message=None):
        self.logged.append(title)


class _BrokenReport:
    @staticmethod
    def build_report(rows):
        raise RuntimeError("boom")


class TestEndpoint(unittest.TestCase):
    def setUp(self):
        self._frappe = api.frappe
        self._report = api._report
        api._ledger.reset_memory_store()

    def tearDown(self):
        api.frappe = self._frappe
        api._report = self._report
        api._ledger.reset_memory_store()

    def test_standalone_load_falls_back_to_path_imports(self):
        # Loaded outside the composed package, the module must still have
        # working ledger/report halves — the offline-harness code path.
        self.assertTrue(hasattr(api._ledger, "record_signal"))
        self.assertTrue(hasattr(api._report, "build_report"))

    def test_without_system_manager_the_answer_is_a_refusal(self):
        api.frappe = _FrappeStub(roles=["All", "Forex User"])
        with self.assertRaises(_FrappeStub.PermissionError):
            api.get_forex_retraining_report()

    def test_with_system_manager_the_ledger_is_reported(self):
        api.frappe = _FrappeStub(roles=["All", "System Manager"])
        entry = dt.datetime(2026, 8, 3, 8, 15)
        signal_id = api._ledger.record_signal(
            "london_breakout", "a" * 64, "GBPUSD", "long", entry, 1.2754)
        api._ledger.record_outcome(signal_id, entry + dt.timedelta(hours=2),
                                   1.2794, "win", 40)
        payload = api.get_forex_retraining_report()
        self.assertTrue(payload["admin_only"])
        self.assertEqual(payload["total_signals"], 1)
        summary = payload["strategies"]["london_breakout"]["a" * 64]
        self.assertEqual(summary["counts"]["win"], 1)
        self.assertEqual(summary["state"], "insufficient_data")

    def test_internal_failures_answer_in_band_and_are_logged(self):
        stub = _FrappeStub(roles=["System Manager"])
        api.frappe = stub
        api._report = _BrokenReport
        payload = api.get_forex_retraining_report()
        self.assertTrue(payload["error"])
        self.assertTrue(payload["admin_only"])
        self.assertIn(api.ERROR_LOG_TITLE, payload["summary"])
        self.assertEqual(stub.logged, [api.ERROR_LOG_TITLE])


class TestManifestWiring(unittest.TestCase):
    def test_the_endpoint_is_declared_control_side(self):
        methods = CONTROL_HOOKS["whitelisted_methods"]
        alias = "{app_name}.api.forex.get_retraining_report"
        self.assertIn(alias, methods)
        self.assertEqual(
            methods[alias],
            "{app_name}.rforex.control.api.get_forex_retraining_report"
            ".get_forex_retraining_report")

    def test_every_control_target_resolves_to_a_real_function(self):
        import ast
        for alias, target in CONTROL_HOOKS["whitelisted_methods"].items():
            self.assertTrue(target.startswith(CONTROL_TARGET_PREFIX), target)
            tail = target[len(CONTROL_TARGET_PREFIX):]
            parts = tail.split(".")
            func_name = parts[-1]
            path = os.path.join(_CONTROL_DIR, *parts[:-1]) + ".py"
            if not os.path.isfile(path):
                # package target: api/<pkg>/<pkg>.py, function re-exported
                path = os.path.join(_CONTROL_DIR, *parts[:-1],
                                    parts[-2] + ".py")
            self.assertTrue(os.path.isfile(path),
                            "{0} -> missing {1}".format(alias, path))
            with open(path) as handle:
                tree = ast.parse(handle.read())
            top_level = {node.name for node in tree.body
                         if isinstance(node,
                                       (ast.FunctionDef, ast.AsyncFunctionDef))}
            self.assertIn(func_name, top_level,
                          "{0} -> {1} not defined in {2}".format(
                              alias, func_name, path))

    def test_the_target_is_whitelisted_when_frappe_is_present(self):
        # The decorator is the zones-style guarded wrapper: identity when
        # frappe is absent (standalone reuse), frappe.whitelist() when
        # composed. Pin both halves so neither can silently vanish.
        with open(_API_PATH) as handle:
            source = handle.read()
        self.assertIn("@_whitelist", source)
        self.assertIn("frappe.whitelist()(fn) if frappe is not None else fn",
                      source)

    def test_no_tenant_surface_exposes_the_ledger(self):
        # Deliberate: reports are operator/admin telemetry. Per-version win
        # rates over a thin ledger are noise, and noise shown to a paying
        # user becomes a promise. Any tenant-facing performance surface is
        # a new decision, not a drift.
        tenant_methods = MANIFEST["app_type"]["tenant"]["hooks"][
            "whitelisted_methods"]
        for alias, target in tenant_methods.items():
            for word in ("retraining", "outcome", "ledger"):
                self.assertNotIn(word, alias.lower(), alias)
                self.assertNotIn(word, target.lower(), target)

    def test_the_ledger_doctype_is_a_control_fixture(self):
        names = set()
        for fixture in CONTROL_HOOKS["fixtures"]:
            if fixture.get("dt") == "DocType":
                for condition in fixture["filters"]:
                    if condition[0] == "name" and condition[1] == "in":
                        names.update(condition[2])
        self.assertIn("Forex Signal Outcome", names)
        folder = os.path.join(_CONTROL_DIR, "doctype", "forex_signal_outcome")
        for filename in ("forex_signal_outcome.json",
                         "forex_signal_outcome.py", "__init__.py"):
            self.assertTrue(
                os.path.isfile(os.path.join(folder, filename)), filename)

    def test_the_ledger_doctype_is_admin_only_and_append_once(self):
        folder = os.path.join(_CONTROL_DIR, "doctype", "forex_signal_outcome")
        with open(os.path.join(folder, "forex_signal_outcome.json")) as handle:
            doc = json.load(handle)
        self.assertEqual({p["role"] for p in doc["permissions"]},
                         {"System Manager"})
        self.assertEqual(doc["module"], "{module_name}")
        fieldnames = {f["fieldname"] for f in doc["fields"]}
        self.assertIn("strategy_checksum", fieldnames)
        # The controller repeats the append-once refusal desk-side.
        with open(os.path.join(folder, "forex_signal_outcome.py")) as handle:
            source = handle.read()
        self.assertIn("_VERDICT_FIELDS", source)
        self.assertIn("on_trash", source)


if __name__ == "__main__":
    unittest.main()
