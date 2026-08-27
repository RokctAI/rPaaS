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

"""Offline tests for the sw6 SMS fallback (src/tenant/sms_fallback.py).

No bench, no network (harness in sw6_harness.py). Exercises:

  * window math: unacked pushes older than the (configurable, default 30
    minute) window get exactly ONE SMS; acked, advisory, too-young and
    aged-out rows never do;
  * send-once: sms_sent_at is stamped BEFORE the gateway call, so no
    failure mode (including a raising gateway) can double-send;
  * the inert-by-default posture: no resolvable sender OR no configured
    gateway is a guarded no-op with one rate-limited admin log line -
    merging costs nothing until a gateway exists;
  * copy: the SMS is the warning's own calm rendered copy trimmed by
    messages.sms_text - at most 160 chars, removal-only, and free of the
    legally forbidden words on every approved class/severity pair.
"""
import datetime as dt

from sw6_harness import (CELL, NOON, USER, WARNING_ID, Sw6TestCase,
                         active_warning)

import frappe  # noqa: E402  (stubbed by the harness)


class SmsFallbackTestCase(Sw6TestCase):
    def setUp(self):
        super().setUp()
        self.sms_calls = []
        self.sms_fail = False

        def send_sms(receivers=None, msg=None, **kwargs):
            if self.sms_fail:
                raise RuntimeError("gateway rejected the message")
            self.sms_calls.append({"receivers": receivers, "msg": msg})

        self.sms_sender = send_sms
        frappe.get_attr = lambda path: self.sms_sender
        self.db.singles[("SMS Settings", "sms_gateway_url")] = (
            "https://sms.example/send")
        self.db.seed("User", name=USER, mobile_no="+27820000001", phone="")
        self.active = {CELL: [active_warning()]}

        saved_fetch = self.mods.proxy.fetch_cell_warnings
        self.mods.proxy.fetch_cell_warnings = (
            lambda lat, lng, locale=None:
            {"warnings": list(self.active.get(f"{lat:.2f},{lng:.2f}", []))})
        self.addCleanup(
            setattr, self.mods.proxy, "fetch_cell_warnings", saved_fetch)

    def seed_push(self, minutes_ago=45, warning_id=WARNING_ID, user=USER,
                  severity="heads_up", **extra):
        return self.db.seed(
            "Weather Notice Delivery",
            kind="subscriber", warning_id=warning_id, user=user,
            watch_location=CELL, event_class="flash_flood",
            severity=severity,
            push_sent_at=NOON - dt.timedelta(minutes=minutes_ago), **extra)

    def run_job(self, now=NOON):
        return self.mods.sms_fallback._run(now=now)


class TestWindowMath(SmsFallbackTestCase):
    def test_unacked_past_the_default_window_gets_one_sms(self):
        row = self.seed_push(minutes_ago=31)
        result = self.run_job()
        self.assertEqual(result, {"status": "ok", "candidates": 1, "sent": 1})
        self.assertEqual(self.sms_calls[0]["receivers"], ["+27820000001"])
        self.assertEqual(row["sms_sent_at"], NOON)

    def test_too_young_rows_wait(self):
        self.seed_push(minutes_ago=29)
        result = self.run_job()
        self.assertEqual(result["candidates"], 0)
        self.assertEqual(self.sms_calls, [])

    def test_the_window_is_configurable(self):
        frappe.conf["severe_weather_sms_fallback_minutes"] = 90
        self.seed_push(minutes_ago=60)
        self.assertEqual(self.run_job()["candidates"], 0)
        frappe.conf["severe_weather_sms_fallback_minutes"] = 45
        self.assertEqual(self.run_job()["sent"], 1)

    def test_acked_rows_never_get_an_sms(self):
        self.seed_push(minutes_ago=45, acked_event="delivered",
                       acked_at=NOON - dt.timedelta(minutes=40))
        self.assertEqual(self.run_job()["candidates"], 0)

    def test_advisory_rows_never_get_an_sms(self):
        self.seed_push(minutes_ago=45, severity="advisory")
        self.assertEqual(self.run_job()["candidates"], 0)

    def test_rows_age_out_of_the_scan(self):
        self.seed_push(minutes_ago=49 * 60)  # past MAX_AGE_HOURS
        self.assertEqual(self.run_job()["candidates"], 0)

    def test_send_once_per_warning_and_subscriber(self):
        self.seed_push(minutes_ago=45)
        self.assertEqual(self.run_job()["sent"], 1)
        result = self.run_job(now=NOON + dt.timedelta(hours=1))
        self.assertEqual((result["candidates"], result["sent"]), (0, 0))
        self.assertEqual(len(self.sms_calls), 1)

    def test_a_failing_gateway_still_consumes_the_send_once_mark(self):
        row = self.seed_push(minutes_ago=45)
        self.sms_fail = True
        result = self.run_job()
        self.assertEqual(result["sent"], 0)
        self.assertIsNotNone(row["sms_sent_at"])  # stamped before the call
        self.assertEqual(len(self.admin_logs), 1)
        self.assertEqual(self.run_job(now=NOON + dt.timedelta(hours=1))
                         ["candidates"], 0)  # never re-sent


class TestGuards(SmsFallbackTestCase):
    def test_master_switch_off_disables_the_pass(self):
        frappe.conf["severe_weather_sms_fallback_enabled"] = 0
        self.seed_push(minutes_ago=45)
        self.assertEqual(self.run_job(), {"status": "disabled"})

    def test_no_resolvable_sender_is_a_logged_no_op(self):
        def raise_attr(path):
            raise AttributeError(path)
        frappe.get_attr = raise_attr
        self.seed_push(minutes_ago=45)
        result = self.run_job()
        self.assertEqual(result["status"], "no_channel")
        self.assertEqual(result["sent"], 0)
        self.assertEqual(len(self.admin_logs), 1)
        self.assertIn("no sms sender", self.admin_logs[0][1])

    def test_no_gateway_credentials_is_a_logged_no_op(self):
        self.db.singles[("SMS Settings", "sms_gateway_url")] = "  "
        self.seed_push(minutes_ago=45)
        result = self.run_job()
        self.assertEqual(result["status"], "no_gateway")
        self.assertEqual(self.sms_calls, [])
        self.assertEqual(len(self.admin_logs), 1)

    def test_an_idle_tenant_never_even_logs(self):
        frappe.get_attr = None  # would log if touched
        self.assertEqual(self.run_job()["candidates"], 0)
        self.assertEqual(self.admin_logs, [])

    def test_drill_flagged_warnings_never_trigger_the_fallback(self):
        # belt-and-braces: the proxy fetch already excludes drills, but a
        # drill-flagged payload reaching the loop must never cost an SMS.
        self.seed_push(minutes_ago=45)
        drill = active_warning()
        drill["is_drill"] = 1
        self.active[CELL] = [drill]
        result = self.run_job()
        self.assertEqual(result["sent"], 0)
        self.assertEqual(self.sms_calls, [])

    def test_expired_warnings_send_nothing(self):
        self.seed_push(minutes_ago=45)
        self.active[CELL] = []  # no longer active at the cell
        result = self.run_job()
        self.assertEqual(result["sent"], 0)
        self.assertEqual(self.sms_calls, [])

    def test_subscribers_without_a_phone_are_skipped(self):
        self.db.rows("User")[0]["mobile_no"] = ""
        self.seed_push(minutes_ago=45)
        self.assertEqual(self.run_job()["sent"], 0)
        self.assertEqual(self.sms_calls, [])

    def test_run_entrypoint_never_raises(self):
        self.mods.sms_fallback.delivery = None  # break everything
        try:
            result = self.mods.sms_fallback.run_sms_fallback()
        finally:
            self.mods.sms_fallback.delivery = self.mods.delivery
        self.assertEqual(result, {"status": "error"})
        self.assertEqual(len(self.admin_logs), 1)


class TestSmsCopy(SmsFallbackTestCase):
    def test_the_sms_is_the_calm_copy_trimmed_to_sms_length(self):
        self.seed_push(minutes_ago=45)
        self.run_job()
        text = self.sms_calls[0]["msg"]
        warning = active_warning()
        self.assertLessEqual(len(text), self.mods.messages.SMS_MAX_CHARS)
        self.assertTrue(text.startswith(warning["headline"]))

    def test_sms_text_trims_at_a_word_boundary(self):
        messages = self.mods.messages
        headline = "Flash flooding possible near Thohoyandou"
        long_message = "Heavy rain could cause fast-rising water " * 8
        text = messages.sms_text(headline, long_message)
        self.assertLessEqual(len(text), messages.SMS_MAX_CHARS)
        self.assertTrue(text.endswith("..."))
        self.assertNotIn("  ", text)

    def test_sms_copy_never_contains_forbidden_words_for_any_pair(self):
        messages = self.mods.messages
        banned = ("warning", "warn ", "yellow", "orange level", "red level")
        for (event_class, severity) in messages._HEADLINES:
            rendered = messages.render(event_class, severity, "Polokwane")
            text = messages.sms_text(rendered["headline"],
                                     rendered["message"]).lower()
            for word in banned:
                self.assertNotIn(word, text,
                                 f"{word!r} leaked into the SMS for "
                                 f"{event_class}/{severity}")


if __name__ == "__main__":  # pragma: no cover
    import unittest
    unittest.main()
