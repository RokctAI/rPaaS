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

"""Offline tests for the TENANT-side hourly push-sync (src/tenant/push_sync.py).

Same harness style as the sibling tests: frappe is stubbed when no bench is
available, no network is touched, runs with `python3 -m unittest` anywhere.
The proxy fetch is replaced by a fixture and the comms sender by a fake
resolved through the stubbed frappe.get_attr, exercising:

  * the master switch (default ON; "severe_weather_push_enabled": 0 is the
    off-switch) through the shared push.push_enabled();
  * send-once per episode with cache-backed state (refreshes never repush);
  * escalation (heads_up -> warning) pushes again and bypasses the cooldown;
  * per-(cell, class) cooldown for NEW episodes;
  * quiet hours defer (nothing recorded, sent on the next pass outside);
  * fan-out to fresh subscribers of the cell, via push._subscribers;
  * isolation: malformed grid keys, proxy failures, and absent senders are
    all silent no-ops that never raise out of run_push_sync().
"""

import datetime as dt
import importlib
import importlib.util
import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FRAPPE_MODULE_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
COMMON_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "warnings_engine")
TENANT_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "tenant")


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


def _load_tenant():
    _ensure_frappe_stub()
    if "wmod" not in sys.modules:
        parent = types.ModuleType("wmod")
        parent.__path__ = []
        sys.modules["wmod"] = parent
    _load_pkg("wmod.warnings_engine", COMMON_DIR)
    return _load_pkg("wmod.tenant", TENANT_DIR)


_load_tenant()
push_sync = importlib.import_module("wmod.tenant.push_sync")
proxy = importlib.import_module(
    "wmod.tenant.api.get_weather_warnings.get_weather_warnings")
push = importlib.import_module("wmod.warnings_engine.push")

import frappe  # noqa: E402  (after stub install, like the sibling tests)


# --------------------------------------------------------------------------- #
# fixtures + fakes
# --------------------------------------------------------------------------- #

CELL = "-25.75,28.25"
NOON = dt.datetime(2026, 8, 19, 12, 0, 0)


def _warning(warning_id="SWW-2026-00001", severity="heads_up",
             event_class="flash_flood"):
    return {
        "id": warning_id,
        "event_class": event_class,
        "severity": severity,
        "severity_label": "Heads-up",
        "headline": "Heavy rain possible near Pretoria",
        "message": "Heavy rain is possible in the next day or so.",
        "onset": "2026-08-19T06:00:00Z",
        "valid_until": "2026-08-20T06:00:00Z",
        "issued_at": "2026-08-19T07:00:00Z",
    }


class FakeCache:
    def __init__(self):
        self.store = {}
        self.expiries = {}

    def get_value(self, key):
        return self.store.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.store[key] = value
        self.expiries[key] = expires_in_sec


class FakeSender:
    def __init__(self):
        self.calls = []
        self.fail_for = set()

    def __call__(self, user=None, title=None, body=None, data=None):
        if user in self.fail_for:
            raise RuntimeError("FCM rejected the token")
        self.calls.append({"user": user, "title": title,
                           "body": body, "data": data})


class PushSyncTestCase(unittest.TestCase):
    def setUp(self):
        self.cache = FakeCache()
        self.sender = FakeSender()
        self.subscribers = [{
            "watch_location": CELL,
            "user": "farmer@example.com",
            "last_requested_at": NOON - dt.timedelta(days=1),
        }]
        self.cell_warnings = {CELL: [_warning()]}
        self.fetch_calls = []

        def get_all(doctype, filters=None, fields=None, **kwargs):
            rows = []
            for row in self.subscribers:
                keep = True
                for key, cond in (filters or {}).items():
                    value = row.get(key)
                    if isinstance(cond, list) and cond[0] == ">=":
                        keep = keep and value is not None and value >= cond[1]
                    else:
                        keep = keep and value == cond
                if keep:
                    rows.append({f: row.get(f) for f in (fields or row)})
            return rows

        def fetch_cell_warnings(grid_lat, grid_lng, locale=None):
            key = f"{grid_lat:.2f},{grid_lng:.2f}"
            self.fetch_calls.append(key)
            return {"warnings": list(self.cell_warnings.get(key, []))}

        self._saved = (frappe.conf, frappe.cache, frappe.get_all,
                       getattr(frappe, "get_attr", None))
        frappe.conf = {}  # default config: push is ON
        frappe.cache = lambda: self.cache
        frappe.get_all = get_all
        frappe.get_attr = lambda path: self.sender

        self._saved_fetch = proxy.fetch_cell_warnings
        proxy.fetch_cell_warnings = fetch_cell_warnings

        # count admin log lines without touching the (rate-limited) real one
        self.admin_logs = []
        self._saved_logs = (push_sync.log_admin_error, push.log_admin_error)
        log = lambda title, message=None: self.admin_logs.append(
            (title, message))
        push_sync.log_admin_error = log
        push.log_admin_error = log

    def tearDown(self):
        frappe.conf, frappe.cache, frappe.get_all, saved_get_attr = self._saved
        if saved_get_attr is None:
            if hasattr(frappe, "get_attr"):
                del frappe.get_attr
        else:
            frappe.get_attr = saved_get_attr
        proxy.fetch_cell_warnings = self._saved_fetch
        push_sync.log_admin_error, push.log_admin_error = self._saved_logs

    def sync(self, now=NOON):
        return push_sync._sync(now=now)


# --------------------------------------------------------------------------- #
# master switch + fan-out
# --------------------------------------------------------------------------- #

class TestMasterSwitchAndFanout(PushSyncTestCase):
    def test_default_is_on_and_the_subscriber_is_pushed(self):
        result = self.sync()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["sent"], 1)
        call = self.sender.calls[0]
        self.assertEqual(call["user"], "farmer@example.com")
        self.assertEqual(call["title"], _warning()["headline"])
        self.assertEqual(call["body"], _warning()["message"])
        self.assertEqual(call["data"]["type"], "severe_weather")
        self.assertEqual(call["data"]["watch_location"], CELL)
        self.assertEqual(call["data"]["warning_id"], "SWW-2026-00001")

    def test_explicit_zero_disables_the_whole_pass(self):
        frappe.conf = {"severe_weather_push_enabled": 0}
        self.assertEqual(self.sync(), {"status": "disabled"})
        self.assertEqual(self.sender.calls, [])
        self.assertEqual(self.fetch_calls, [])

    def test_every_fresh_subscriber_of_the_cell_is_pushed(self):
        self.subscribers.append({
            "watch_location": CELL,
            "user": "shopkeeper@example.com",
            "last_requested_at": NOON - dt.timedelta(days=2),
        })
        self.sync()
        users = sorted(c["user"] for c in self.sender.calls)
        self.assertEqual(users,
                         ["farmer@example.com", "shopkeeper@example.com"])

    def test_stale_subscribers_are_not_pushed_and_not_fetched_for(self):
        self.subscribers[0]["last_requested_at"] = (
            NOON - dt.timedelta(days=45))
        result = self.sync()
        self.assertEqual(result["cells"], 0)
        self.assertEqual(self.fetch_calls, [])
        self.assertEqual(self.sender.calls, [])

    def test_run_push_sync_never_raises(self):
        def exploding(*a, **k):
            raise RuntimeError("boom")
        frappe.get_all = exploding
        self.assertEqual(push_sync.run_push_sync()["status"], "ok")
        proxy.fetch_cell_warnings = exploding
        self.assertEqual(push_sync.run_push_sync()["status"], "ok")


# --------------------------------------------------------------------------- #
# send-once / escalation / cooldown / quiet hours (push.py semantics)
# --------------------------------------------------------------------------- #

class TestDecisionPipeline(PushSyncTestCase):
    def test_refresh_of_the_same_episode_never_repushes(self):
        self.sync()
        self.sync(now=NOON + dt.timedelta(hours=1))
        self.assertEqual(len(self.sender.calls), 1)

    def test_escalation_pushes_again_and_bypasses_the_cooldown(self):
        self.sync()
        self.cell_warnings[CELL] = [_warning(severity="warning")]
        self.sync(now=NOON + dt.timedelta(hours=2))  # inside 12 h cooldown
        self.assertEqual(len(self.sender.calls), 2)
        self.assertEqual(self.sender.calls[1]["data"]["severity"], "warning")

    def test_new_episode_inside_the_cooldown_is_skipped(self):
        self.sync()
        self.cell_warnings[CELL] = [_warning(warning_id="SWW-2026-00002")]
        self.sync(now=NOON + dt.timedelta(hours=2))
        self.assertEqual(len(self.sender.calls), 1)

    def test_new_episode_after_the_cooldown_is_pushed(self):
        self.sync()
        self.cell_warnings[CELL] = [_warning(warning_id="SWW-2026-00002")]
        self.sync(now=NOON + dt.timedelta(hours=13))
        self.assertEqual(len(self.sender.calls), 2)

    def test_other_event_classes_have_their_own_cooldown_state(self):
        self.sync()
        self.cell_warnings[CELL] = [
            _warning(warning_id="SWW-2026-00003",
                     event_class="destructive_wind")]
        self.sync(now=NOON + dt.timedelta(hours=1))
        self.assertEqual(len(self.sender.calls), 2)

    def test_quiet_hours_defer_and_retry_outside_the_window(self):
        frappe.conf = {"severe_weather_push_quiet_hours": "21-06"}
        self.sync(now=dt.datetime(2026, 8, 19, 22, 0, 0))
        self.assertEqual(self.sender.calls, [])
        # nothing was recorded, so the next pass outside the window sends
        self.sync(now=dt.datetime(2026, 8, 20, 7, 0, 0))
        self.assertEqual(len(self.sender.calls), 1)

    def test_absent_sender_is_a_silent_noop_and_state_is_not_recorded(self):
        def raising_get_attr(path):
            raise ImportError(path)
        frappe.get_attr = raising_get_attr
        self.sync()
        self.assertEqual(self.sender.calls, [])
        self.assertEqual(
            [k for k in self.cache.store if k.startswith("sw_push_sync_")],
            [])

    def test_partial_send_failure_still_records_state(self):
        self.subscribers.append({
            "watch_location": CELL,
            "user": "broken@example.com",
            "last_requested_at": NOON - dt.timedelta(days=1),
        })
        self.sender.fail_for.add("broken@example.com")
        self.sync()
        self.assertEqual(len(self.sender.calls), 1)
        self.sync(now=NOON + dt.timedelta(hours=1))
        self.assertEqual(len(self.sender.calls), 1)  # no repush spam
        self.assertTrue(self.admin_logs)


# --------------------------------------------------------------------------- #
# isolation
# --------------------------------------------------------------------------- #

class TestIsolation(PushSyncTestCase):
    def test_malformed_grid_keys_are_skipped_silently(self):
        self.subscribers.append({
            "watch_location": "not-a-grid-key",
            "user": "farmer@example.com",
            "last_requested_at": NOON - dt.timedelta(days=1),
        })
        result = self.sync()
        self.assertEqual(result["sent"], 1)
        self.assertEqual(self.fetch_calls, [CELL])

    def test_empty_or_failed_proxy_response_sends_nothing(self):
        self.cell_warnings[CELL] = []
        self.assertEqual(self.sync()["sent"], 0)

        def failing_fetch(*a, **k):
            raise RuntimeError("control plane unreachable")
        proxy.fetch_cell_warnings = failing_fetch
        result = self.sync(now=NOON + dt.timedelta(hours=1))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["sent"], 0)

    def test_unknown_severity_values_are_never_pushed(self):
        self.cell_warnings[CELL] = [_warning(severity="advisory")]
        self.assertEqual(self.sync()["sent"], 0)
        self.assertEqual(self.sender.calls, [])

    def test_cell_cap_bounds_one_run(self):
        self.assertLessEqual(len(self.fetch_calls),
                             push_sync.MAX_CELLS_PER_RUN)
        self.assertEqual(push_sync.MAX_CELLS_PER_RUN, 200)


if __name__ == "__main__":
    unittest.main()
