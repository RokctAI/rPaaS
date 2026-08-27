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

"""Offline unit tests for severe-weather push notifications (push.py).

Same conventions as test_warnings_engine.py: frappe is stubbed when no bench
is available, no network is touched, and everything runs with
`python3 -m unittest` anywhere. The comms module is replaced by a fake
sender callable resolved through the stubbed frappe.get_attr, exercising:

  - default ON master switch (severe_weather_push_enabled is an off-switch)
  - send-once per episode (refreshes never push again)
  - per-(location, class) cooldown across episodes
  - escalation pushes immediately and bypasses the cooldown
  - silent no-op when the comms module is absent
  - quiet hours defer (nothing recorded, retried outside the window)
  - calm copy only (never the word "warning" in title/body)
"""

import datetime as dt
import importlib
import importlib.util
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
messages = importlib.import_module("wmod.warnings_engine.messages")
push = importlib.import_module("wmod.warnings_engine.push")

import frappe  # noqa: E402  (the stub, after install)

NOON = dt.datetime(2026, 3, 1, 12, 0)  # outside any quiet window under test


class FakeDB:
    """Warning-record store implementing the get/set_value + get_all calls
    push.py makes."""

    def __init__(self):
        self.warnings = {}     # name -> fields dict
        self.subscribers = []  # dicts: watch_location, user, last_requested_at

    # -- frappe.db surface -------------------------------------------------- #
    def get_value(self, doctype, name, fieldname):
        assert doctype == push.WARNING_DOCTYPE
        row = self.warnings.get(name)
        return row.get(fieldname) if row else None

    def set_value(self, doctype, name, values):
        assert doctype == push.WARNING_DOCTYPE
        self.warnings.setdefault(name, {}).update(values)

    # -- frappe.get_all surface --------------------------------------------- #
    def get_all(self, doctype, filters=None, fields=None, limit=None, **kw):
        filters = filters or {}
        if doctype == push.SUBSCRIBER_DOCTYPE:
            rows = [dict(r) for r in self.subscribers
                    if self._matches(r, filters)]
        elif doctype == push.WARNING_DOCTYPE:
            rows = [dict(r, name=name) for name, r in self.warnings.items()
                    if self._matches(dict(r, name=name), filters)]
        else:
            raise AssertionError(f"unexpected doctype {doctype}")
        return rows[:limit] if limit else rows

    @staticmethod
    def _matches(row, filters):
        for key, cond in filters.items():
            value = row.get(key)
            if isinstance(cond, (list, tuple)):
                op, operand = cond
                if value is None:
                    return False
                if op == ">=":
                    if not value >= operand:
                        return False
                else:
                    raise AssertionError(f"unexpected operator {op}")
            elif value != cond:
                return False
        return True


class FakeSender:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def __call__(self, user, title, body, data):
        self.calls.append({"user": user, "title": title,
                           "body": body, "data": data})
        if self.fail:
            raise RuntimeError("boom")
        return {"status": "success"}


class PushTestCase(unittest.TestCase):
    """Common fixture: enabled switch, one subscriber, fake comms sender."""

    def setUp(self):
        self.db = FakeDB()
        self.sender = FakeSender()
        self.db.subscribers.append({
            "watch_location": "-26.25,28.00",
            "user": "farmer@example.com",
            "last_requested_at": NOON - dt.timedelta(days=1),
        })
        self._saved = (frappe.conf, frappe.db, frappe.get_all,
                       getattr(frappe, "get_attr", None))
        frappe.conf = {"severe_weather_push_enabled": 1}
        frappe.db = types.SimpleNamespace(get_value=self.db.get_value,
                                          set_value=self.db.set_value)
        frappe.get_all = self.db.get_all
        frappe.get_attr = lambda path: self.sender
        # count admin log lines without touching the (rate-limited) real one
        self.admin_logs = []
        self._saved_log = push.log_admin_error
        push.log_admin_error = lambda title, message=None: self.admin_logs.append(
            (title, message))

    def tearDown(self):
        frappe.conf, frappe.db, frappe.get_all, saved_get_attr = self._saved
        if saved_get_attr is None:
            if hasattr(frappe, "get_attr"):
                del frappe.get_attr
        else:
            frappe.get_attr = saved_get_attr
        push.log_admin_error = self._saved_log

    # -- helpers ------------------------------------------------------------ #
    def notify(self, name="SWW-1", severity="heads_up", event_class="flood",
               location="-26.25,28.00", now=NOON):
        # mirror the evaluator: the warning record exists (with its location
        # and class) before push is consulted
        self.db.warnings.setdefault(name, {}).update(
            {"watch_location": location, "event_class": event_class})
        rendered = messages.render(event_class, severity, "Bethlehem")
        return push._notify(name, location, event_class, rendered, now=now)


class TestMasterSwitch(PushTestCase):
    def test_default_is_on_and_pushes_are_sent(self):
        frappe.conf = {}  # a shell with no site config at all: enabled
        self.assertEqual(self.notify(), "sent:1")
        self.assertEqual(len(self.sender.calls), 1)

    def test_explicit_zero_is_off_and_nothing_is_sent_or_logged(self):
        # the flag remains the OFF-switch
        frappe.conf = {"severe_weather_push_enabled": 0}
        self.assertEqual(self.notify(), "disabled")
        self.assertEqual(self.sender.calls, [])
        self.assertEqual(self.admin_logs, [])
        self.assertNotIn("last_push_severity", self.db.warnings.get("SWW-1", {}))

    def test_falsy_string_is_off(self):
        frappe.conf = {"severe_weather_push_enabled": "0"}
        self.assertEqual(self.notify(), "disabled")
        self.assertEqual(self.sender.calls, [])

    def test_missing_subscriber_registry_is_a_silent_noop(self):
        # the control shell runs the engine but has no tenant-side
        # Weather Watch Subscriber table: the guarded query yields nobody
        real_get_all = frappe.get_all

        def raising_get_all(doctype, *a, **k):
            if doctype == push.SUBSCRIBER_DOCTYPE:
                raise RuntimeError(
                    "no such table: tabWeather Watch Subscriber")
            return real_get_all(doctype, *a, **k)
        frappe.get_all = raising_get_all
        self.assertEqual(self.notify(), "no_subscribers")
        self.assertEqual(self.sender.calls, [])


class TestSendOnce(PushTestCase):
    def test_new_episode_pushes_once_then_refreshes_are_silent(self):
        self.assertEqual(self.notify(), "sent:1")
        self.assertEqual(len(self.sender.calls), 1)
        call = self.sender.calls[0]
        self.assertEqual(call["user"], "farmer@example.com")
        self.assertIn("Bethlehem", call["title"])
        self.assertEqual(call["data"]["event_class"], "flood")
        self.assertEqual(call["data"]["type"], "severe_weather")
        # the episode remembers what was pushed
        self.assertEqual(
            self.db.warnings["SWW-1"]["last_push_severity"], "heads_up")
        self.assertEqual(self.db.warnings["SWW-1"]["last_pushed_at"], NOON)
        # hourly refreshes of the same active episode: no more pushes
        for hours in (1, 2, 3):
            result = self.notify(now=NOON + dt.timedelta(hours=hours))
            self.assertEqual(result, "already_notified")
        self.assertEqual(len(self.sender.calls), 1)

    def test_copy_is_calm_and_never_says_warning(self):
        self.notify(severity="warning")  # internal enum may say "warning"...
        call = self.sender.calls[0]
        text = (call["title"] + " " + call["body"]).lower()
        self.assertNotIn("warning", text)  # ...user-facing text never does

    def test_no_subscribers_means_no_send_and_no_state(self):
        self.db.subscribers.clear()
        self.assertEqual(self.notify(), "no_subscribers")
        self.assertNotIn("last_push_severity", self.db.warnings["SWW-1"])

    def test_stale_subscribers_are_not_pushed(self):
        self.db.subscribers[0]["last_requested_at"] = (
            NOON - dt.timedelta(days=push.SUBSCRIBER_FRESH_DAYS + 1))
        self.assertEqual(self.notify(), "no_subscribers")

    def test_multiple_subscribers_all_receive_deduplicated(self):
        self.db.subscribers.append({
            "watch_location": "-26.25,28.00",
            "user": "shop@example.com",
            "last_requested_at": NOON - dt.timedelta(hours=2),
        })
        self.db.subscribers.append({  # duplicate row: pushed only once
            "watch_location": "-26.25,28.00",
            "user": "farmer@example.com",
            "last_requested_at": NOON - dt.timedelta(hours=1),
        })
        self.assertEqual(self.notify(), "sent:2")
        self.assertEqual(
            sorted(c["user"] for c in self.sender.calls),
            ["farmer@example.com", "shop@example.com"])


class TestCooldown(PushTestCase):
    def test_new_episode_within_cooldown_is_suppressed(self):
        self.assertEqual(self.notify(name="SWW-1"), "sent:1")
        # first episode expires; a new one for the same (location, class)
        # is detected two hours later - inside the default 12 h cooldown
        result = self.notify(name="SWW-2", now=NOON + dt.timedelta(hours=2))
        self.assertEqual(result, "cooldown")
        self.assertEqual(len(self.sender.calls), 1)

    def test_new_episode_after_cooldown_sends(self):
        self.notify(name="SWW-1")
        result = self.notify(name="SWW-2", now=NOON + dt.timedelta(hours=13))
        self.assertEqual(result, "sent:1")
        self.assertEqual(len(self.sender.calls), 2)

    def test_cooldown_is_per_event_class(self):
        self.notify(name="SWW-1", event_class="flood")
        result = self.notify(name="SWW-2", event_class="destructive_wind",
                             now=NOON + dt.timedelta(hours=1))
        self.assertEqual(result, "sent:1")

    def test_cooldown_zero_disables_the_window(self):
        frappe.conf["severe_weather_push_cooldown_hours"] = 0
        self.notify(name="SWW-1")
        result = self.notify(name="SWW-2", now=NOON + dt.timedelta(hours=1))
        self.assertEqual(result, "sent:1")


class TestEscalation(PushTestCase):
    def test_escalation_pushes_again_even_within_cooldown(self):
        self.assertEqual(self.notify(severity="heads_up"), "sent:1")
        # one hour later the same episode escalates to "warning" severity
        result = self.notify(severity="warning",
                             now=NOON + dt.timedelta(hours=1))
        self.assertEqual(result, "sent:1")
        self.assertEqual(len(self.sender.calls), 2)
        self.assertEqual(
            self.db.warnings["SWW-1"]["last_push_severity"], "warning")
        # further refreshes at the escalated level stay silent
        result = self.notify(severity="warning",
                             now=NOON + dt.timedelta(hours=2))
        self.assertEqual(result, "already_notified")

    def test_deescalation_never_pushes(self):
        self.notify(severity="warning")
        result = self.notify(severity="heads_up",
                             now=NOON + dt.timedelta(hours=1))
        self.assertEqual(result, "already_notified")
        self.assertEqual(len(self.sender.calls), 1)


class TestSilentAbsence(PushTestCase):
    def test_missing_comms_module_is_a_silent_noop_with_one_log(self):
        def raise_import_error(path):
            raise ImportError(f"No module named {path}")

        frappe.get_attr = raise_import_error
        result = push.notify_warning_upsert(
            "SWW-1", "-26.25,28.00", "flood",
            messages.render("flood", "heads_up", "Bethlehem"))
        self.assertEqual(result, "no_sender")
        self.assertEqual(self.sender.calls, [])
        self.assertEqual(self.db.warnings, {})  # nothing recorded
        self.assertEqual(len(self.admin_logs), 1)
        self.assertEqual(self.admin_logs[0][0], push.TITLE_PUSH)

    def test_default_target_is_the_comms_module_send_path(self):
        # tokenized in source; the composer substitutes {app_name}
        self.assertEqual(
            push.DEFAULT_TARGET,
            "{app_name}.comms.tenant.api.notification.send_push_notification")

    def test_config_can_override_the_target_path(self):
        seen = []

        def get_attr(path):
            seen.append(path)
            return self.sender

        frappe.get_attr = get_attr
        frappe.conf["severe_weather_push_target"] = "myapp.custom.sender"
        self.assertEqual(self.notify(), "sent:1")
        self.assertEqual(seen, ["myapp.custom.sender"])

    def test_send_failure_is_swallowed_and_logged_not_raised(self):
        self.sender.fail = True
        # notify_warning_upsert uses wall-clock now: keep the subscriber fresh
        self.db.subscribers[0]["last_requested_at"] = dt.datetime.utcnow()
        result = push.notify_warning_upsert(
            "SWW-1", "-26.25,28.00", "flood",
            messages.render("flood", "heads_up", "Bethlehem"))
        self.assertEqual(result, "sent:0")
        self.assertEqual(len(self.admin_logs), 1)
        # state is still recorded so a broken sender cannot spam retries
        self.assertEqual(
            self.db.warnings["SWW-1"]["last_push_severity"], "heads_up")


class TestQuietHours(PushTestCase):
    def setUp(self):
        super().setUp()
        frappe.conf["severe_weather_push_quiet_hours"] = "21-06"

    def test_suppressed_inside_the_window_nothing_recorded(self):
        for hour in (21, 23, 0, 5):
            result = self.notify(now=NOON.replace(hour=hour))
            self.assertEqual(result, "quiet_hours")
        self.assertEqual(self.sender.calls, [])
        self.assertNotIn("last_push_severity", self.db.warnings["SWW-1"])

    def test_deferred_push_goes_out_after_the_window(self):
        self.assertEqual(self.notify(now=NOON.replace(hour=23)), "quiet_hours")
        # next evaluator pass outside the window: same episode, still unsent
        result = self.notify(now=(NOON + dt.timedelta(days=1)).replace(hour=7))
        self.assertEqual(result, "sent:1")

    def test_non_wrapping_window(self):
        frappe.conf["severe_weather_push_quiet_hours"] = "09-17"
        self.assertEqual(self.notify(now=NOON.replace(hour=12)), "quiet_hours")
        self.assertEqual(self.notify(now=NOON.replace(hour=18)), "sent:1")

    def test_bad_config_means_no_quiet_hours(self):
        for bad in ("nonsense", "1-2-3", "", None, "aa-bb"):
            frappe.conf["severe_weather_push_quiet_hours"] = bad
            self.assertIsNone(push.parse_quiet_hours(bad))
        frappe.conf["severe_weather_push_quiet_hours"] = "nonsense"
        self.assertEqual(self.notify(now=NOON.replace(hour=23)), "sent:1")


class TestAdvisoryNeverPushes(PushTestCase):
    def test_advisory_severity_is_never_push_worthy(self):
        # Advisory records are propagation-owned soft notices, strictly
        # below heads_up; the evaluator never routes them here, but even if
        # one reached the pipeline it must rank as no-severity and never
        # notify (messages.SEVERITY_WORDS deliberately excludes advisory).
        rendered = {
            "severity": "advisory",
            "headline": "Very wet conditions in the wider area",
            "message": "Heavy rain is affecting areas nearby.",
        }
        self.db.warnings.setdefault("SWW-ADV", {}).update(
            {"watch_location": "-26.25,28.00", "event_class": "flood"})
        self.assertEqual(
            "no_severity",
            push._notify("SWW-ADV", "-26.25,28.00", "flood", rendered,
                         now=NOON))
        self.assertEqual(self.sender.calls, [])
        self.assertNotIn("last_push_severity",
                         self.db.warnings.get("SWW-ADV", {}))


class TestEntryPointNeverRaises(PushTestCase):
    def test_internal_error_becomes_admin_log_not_exception(self):
        frappe.get_all = MagicMock(side_effect=RuntimeError("db down"))
        result = push.notify_warning_upsert(
            "SWW-1", "-26.25,28.00", "flood",
            messages.render("flood", "heads_up", "Bethlehem"))
        self.assertEqual(result, "error")
        self.assertEqual(len(self.admin_logs), 1)


if __name__ == "__main__":
    unittest.main()
