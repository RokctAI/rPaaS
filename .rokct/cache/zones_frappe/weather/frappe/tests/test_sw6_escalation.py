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

"""Offline tests for the sw6 human escalation ladder
(src/tenant/escalation.py + the tokened acknowledge endpoint).

No bench, no network (harness in sw6_harness.py). Exercises:

  * only TOP-severity notices escalate, only after the configured window,
    and only while genuinely unacked (any subscriber ack stops the ladder
    before it starts);
  * contacts fire strictly in priority order, one rung per step interval,
    scoped contacts only for their own cell;
  * the acknowledge link: a valid token acks the escalation row (recorded
    in the same ledger) and stops all further escalation; unknown tokens
    are log-and-200;
  * channels: email through the guarded comms seam, SMS only when the SMS
    channel is live, voice ONLY when a target is explicitly configured
    (the documented pluggable seam), and an unreachable contact consumes
    its rung so a broken rung cannot wedge the ladder;
  * no contacts configured = silent no-op; expired notices never page;
  * SAWS copy rules on every contact-facing string.
"""
import datetime as dt

from sw6_harness import (CELL, NOON, USER, WARNING_ID, Sw6TestCase,
                         active_warning)

import frappe  # noqa: E402  (stubbed by the harness)


class EscalationTestCase(Sw6TestCase):
    def setUp(self):
        super().setUp()
        self.emails, self.pushes, self.smses, self.calls = [], [], [], []
        frappe.conf["severe_weather_ack_base_url"] = "https://tenant.example"

        def email_sender(recipients=None, subject=None, message=None,
                         **kwargs):
            self.emails.append({"recipients": recipients, "subject": subject,
                                "message": message})

        def push_sender(user=None, title=None, body=None, data=None):
            self.pushes.append({"user": user, "title": title, "body": body,
                                "data": data})

        def sms_sender(receivers=None, msg=None, **kwargs):
            self.smses.append({"receivers": receivers, "msg": msg})

        def voice_sender(phone=None, message=None):
            self.calls.append({"phone": phone, "message": message})

        self.targets = {
            self.mods.escalation.DEFAULT_EMAIL_TARGET: email_sender,
            self.mods.push.DEFAULT_TARGET: push_sender,
            self.mods.sms_fallback.DEFAULT_TARGET: sms_sender,
            "acme.voice.place_call": voice_sender,
        }

        def get_attr(path):
            if path in self.targets:
                return self.targets[path]
            raise AttributeError(path)

        frappe.get_attr = get_attr
        self.db.singles[("SMS Settings", "sms_gateway_url")] = (
            "https://sms.example/send")
        self.active = {CELL: [active_warning(severity="warning")]}
        saved_fetch = self.mods.proxy.fetch_cell_warnings
        self.mods.proxy.fetch_cell_warnings = (
            lambda lat, lng, locale=None:
            {"warnings": list(self.active.get(f"{lat:.2f},{lng:.2f}", []))})
        self.addCleanup(
            setattr, self.mods.proxy, "fetch_cell_warnings", saved_fetch)

    def seed_push(self, minutes_ago=90, warning_id=WARNING_ID,
                  severity="warning", user=USER, **extra):
        return self.db.seed(
            "Weather Notice Delivery",
            kind="subscriber", warning_id=warning_id, user=user,
            watch_location=CELL, event_class="flash_flood",
            severity=severity,
            push_sent_at=NOON - dt.timedelta(minutes=minutes_ago), **extra)

    def seed_contact(self, name, priority, email=None, user=None, phone=None,
                     watch_location=None, enabled=1):
        return self.db.seed("Weather Escalation Contact", name=name,
                            contact_name=name, priority=priority,
                            enabled=enabled, email=email, user=user,
                            phone=phone, watch_location=watch_location)

    def run_job(self, now=NOON):
        return self.mods.escalation._run(now=now)

    def esc_rows(self):
        return [r for r in self.db.rows("Weather Notice Delivery")
                if r.get("kind") == "escalation"]


class TestLadderBasics(EscalationTestCase):
    def test_no_contacts_is_a_silent_no_op(self):
        self.seed_push()
        self.assertEqual(self.run_job(), {"status": "no_contacts"})
        self.assertEqual(self.admin_logs, [])

    def test_master_switch_off_disables_the_pass(self):
        frappe.conf["severe_weather_escalation_enabled"] = 0
        self.seed_push()
        self.seed_contact("Ray", 1, email="ray@example.com")
        self.assertEqual(self.run_job(), {"status": "disabled"})

    def test_unacked_top_severity_pages_the_first_contact_by_email(self):
        self.seed_push(minutes_ago=90)
        self.seed_contact("Ray", 1, email="ray@example.com")
        result = self.run_job()
        self.assertEqual(result["notified"], 1)
        self.assertEqual(self.emails[0]["recipients"], ["ray@example.com"])
        rows = self.esc_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["contact"], "Ray")
        self.assertEqual(rows[0]["channels"], "email")
        self.assertTrue(rows[0]["ack_token"])
        # the acknowledge link rides in the body and carries the token
        self.assertIn(rows[0]["ack_token"], self.emails[0]["message"])
        self.assertIn("https://tenant.example/api/method/",
                      self.emails[0]["message"])

    def test_heads_up_tier_never_escalates(self):
        self.seed_push(severity="heads_up")
        self.seed_contact("Ray", 1, email="ray@example.com")
        self.assertEqual(self.run_job()["warnings"], 0)

    def test_inside_the_window_nothing_happens(self):
        self.seed_push(minutes_ago=45)  # default window is 60
        self.seed_contact("Ray", 1, email="ray@example.com")
        self.assertEqual(self.run_job()["warnings"], 0)

    def test_any_subscriber_ack_stops_the_ladder_before_it_starts(self):
        self.seed_push(minutes_ago=90, acked_event="seen",
                       acked_at=NOON - dt.timedelta(minutes=80))
        self.seed_contact("Ray", 1, email="ray@example.com")
        self.assertEqual(self.run_job()["warnings"], 0)
        self.assertEqual(self.emails, [])

    def test_drill_flagged_warnings_never_page_anyone(self):
        # belt-and-braces: the proxy fetch already excludes drills, but a
        # drill-flagged payload must never reach a human contact.
        self.seed_push(minutes_ago=90)
        drill = active_warning(severity="warning")
        drill["is_drill"] = 1
        self.active[CELL] = [drill]
        self.seed_contact("Ray", 1, email="ray@example.com")
        self.assertEqual(self.run_job()["notified"], 0)
        self.assertEqual(self.emails, [])
        self.assertEqual(self.esc_rows(), [])

    def test_expired_notices_never_page_anyone(self):
        self.seed_push(minutes_ago=90)
        self.active[CELL] = []
        self.seed_contact("Ray", 1, email="ray@example.com")
        self.assertEqual(self.run_job()["notified"], 0)
        self.assertEqual(self.esc_rows(), [])


class TestLadderOrderAndPacing(EscalationTestCase):
    def setUp(self):
        super().setUp()
        self.seed_push(minutes_ago=180)
        self.seed_contact("Second", 2, email="second@example.com")
        self.seed_contact("First", 1, email="first@example.com")

    def test_contacts_fire_in_priority_order_one_rung_per_interval(self):
        self.run_job(now=NOON)
        self.assertEqual([e["recipients"] for e in self.emails],
                         [["first@example.com"]])
        # too soon for rung 2 (default step interval 30 min)
        self.run_job(now=NOON + dt.timedelta(minutes=10))
        self.assertEqual(len(self.emails), 1)
        # after the interval the ladder advances
        self.run_job(now=NOON + dt.timedelta(minutes=31))
        self.assertEqual(self.emails[1]["recipients"],
                         ["second@example.com"])
        # ladder exhausted: nobody left to page
        self.run_job(now=NOON + dt.timedelta(minutes=62))
        self.assertEqual(len(self.emails), 2)

    def test_a_contact_ack_via_the_token_stops_further_escalation(self):
        self.run_job(now=NOON)
        token = self.esc_rows()[0]["ack_token"]
        reply = self.mods.esc_ack_api.ack_weather_escalation(token=token)
        self.assertEqual(reply["status"], "ok")
        row = self.esc_rows()[0]
        self.assertEqual(row["acked_event"], "opened")
        self.assertIsNotNone(row["acked_at"])
        result = self.run_job(now=NOON + dt.timedelta(minutes=31))
        self.assertEqual(result["warnings"], 0)  # ladder stopped
        self.assertEqual(len(self.emails), 1)

    def test_the_ack_link_is_idempotent_and_unknown_tokens_are_200(self):
        self.run_job(now=NOON)
        token = self.esc_rows()[0]["ack_token"]
        self.mods.esc_ack_api.ack_weather_escalation(token=token)
        first_acked_at = self.esc_rows()[0]["acked_at"]
        replay = self.mods.esc_ack_api.ack_weather_escalation(token=token)
        self.assertEqual(replay["status"], "ok")
        self.assertEqual(self.esc_rows()[0]["acked_at"], first_acked_at)
        unknown = self.mods.esc_ack_api.ack_weather_escalation(
            token="not-a-token")
        self.assertEqual(unknown["status"], "ok")
        self.assertTrue(self.admin_logs)  # rate-limited log, never an error


class TestScopeAndChannels(EscalationTestCase):
    def test_contacts_scoped_to_another_cell_are_skipped(self):
        self.seed_push(minutes_ago=90)
        self.seed_contact("Elsewhere", 1, email="far@example.com",
                          watch_location="-30.00,20.00")
        self.seed_contact("Here", 2, email="near@example.com",
                          watch_location=CELL)
        self.run_job()
        self.assertEqual(self.emails[0]["recipients"], ["near@example.com"])

    def test_disabled_contacts_are_invisible(self):
        self.seed_push(minutes_ago=90)
        self.seed_contact("Off", 1, email="off@example.com", enabled=0)
        self.assertEqual(self.run_job(), {"status": "no_contacts"})

    def test_every_available_channel_fires_for_one_contact(self):
        self.seed_push(minutes_ago=90)
        frappe.conf["severe_weather_voice_target"] = "acme.voice.place_call"
        self.seed_contact("Ray", 1, email="ray@example.com",
                          user="ray@example.com", phone="+27820000009")
        self.run_job()
        row = self.esc_rows()[0]
        self.assertEqual(row["channels"], "push,email,sms,voice")
        self.assertEqual(self.pushes[0]["user"], "ray@example.com")
        self.assertEqual(self.smses[0]["receivers"], ["+27820000009"])
        self.assertIn(row["ack_token"], self.smses[0]["msg"])
        self.assertEqual(self.calls[0]["phone"], "+27820000009")

    def test_voice_stays_a_seam_until_explicitly_configured(self):
        self.seed_push(minutes_ago=90)
        self.seed_contact("Ray", 1, phone="+27820000009")
        self.run_job()
        self.assertEqual(self.calls, [])  # no config, no voice, no log
        self.assertEqual(self.esc_rows()[0]["channels"], "sms")

    def test_sms_channel_needs_the_gateway_like_the_fallback(self):
        self.seed_push(minutes_ago=90)
        self.db.singles[("SMS Settings", "sms_gateway_url")] = ""
        self.seed_contact("Ray", 1, phone="+27820000009",
                          email="ray@example.com")
        self.run_job()
        self.assertEqual(self.smses, [])
        self.assertEqual(self.esc_rows()[0]["channels"], "email")

    def test_an_unreachable_contact_consumes_its_rung(self):
        self.seed_push(minutes_ago=180)
        self.seed_contact("NoChannels", 1)  # no user, email, or phone
        self.seed_contact("Reachable", 2, email="ok@example.com")
        self.run_job(now=NOON)
        self.assertEqual(self.esc_rows()[0]["channels"], "")
        self.assertTrue(self.admin_logs)  # the broken rung is reported
        self.run_job(now=NOON + dt.timedelta(minutes=31))
        self.assertEqual(self.emails[0]["recipients"], ["ok@example.com"])

    def test_run_entrypoint_never_raises(self):
        # break the ledger entirely: the guarded reads degrade to "nothing
        # to escalate" and the entry point still returns a status dict.
        self.mods.escalation.delivery = None
        self.seed_push(minutes_ago=90)
        self.seed_contact("Ray", 1, email="ray@example.com")
        try:
            result = self.mods.escalation.run_escalation()
        finally:
            self.mods.escalation.delivery = self.mods.delivery
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["warnings"], 0)
        self.assertEqual(self.emails, [])


class TestEscalationCopy(EscalationTestCase):
    BANNED = ("warning", "warn ", "yellow", "orange level", "red level")

    def test_contact_facing_copy_is_saws_safe(self):
        messages = self.mods.messages
        rendered = messages.render("flash_flood", "warning", "Polokwane")
        copy = messages.render_escalation(
            rendered["headline"], rendered["message"],
            "https://tenant.example/api/method/x.tenant.api."
            "ack_weather_escalation?token=abc")
        for text in (copy["subject"].lower(), copy["body"].lower(),
                     messages.ESCALATION_NOTE.lower(),
                     self.mods.esc_ack_api.ACK_THANKS.lower(),
                     self.mods.esc_ack_api.ACK_ALREADY.lower()):
            for word in self.BANNED:
                self.assertNotIn(word, text)

    def test_escalation_sms_keeps_the_link_within_budget(self):
        messages = self.mods.messages
        link = ("https://tenant.example/api/method/shop.tenant.api."
                "ack_weather_escalation?token=" + "x" * 32)
        text = messages.escalation_sms_text(
            "Rising river water expected near Musina", link)
        self.assertIn(link, text)
        self.assertLessEqual(len(text), messages.ESCALATION_SMS_MAX_CHARS)

    def test_the_note_rides_in_every_body(self):
        self.seed_push(minutes_ago=90)
        self.seed_contact("Ray", 1, email="ray@example.com")
        self.run_job()
        self.assertIn(self.mods.messages.ESCALATION_NOTE,
                      self.emails[0]["message"])


if __name__ == "__main__":  # pragma: no cover
    import unittest
    unittest.main()
