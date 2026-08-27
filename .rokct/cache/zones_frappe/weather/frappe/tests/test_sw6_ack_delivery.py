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

"""Offline tests for sw6 ack tracking: the Weather Notice Delivery ledger,
the PINNED ack_weather_notice contract, and the admin stats aggregates.

No bench, no network - runs with `python3 -m unittest` anywhere (harness in
sw6_harness.py). Exercises:

  * ledger writes from the push-sync fan-out (one row per warning x user);
  * the pinned client contract: payload {warning_id, event, client_ts},
    reply ALWAYS {"status": "ok"} - unknown ids, bad events, Guest sessions
    and internal errors are log-and-200, never an error to the client;
  * idempotent upgrade-only acks: opened beats seen beats delivered,
    replays and downgrades never write;
  * acked_at = first ack, seen_at = first at-least-seen (the metric input);
  * the stats math: sent counts, disjoint delivered/seen/opened buckets,
    ack %, median minutes to seen, and the System Manager gate.
"""
import datetime as dt

from sw6_harness import (CELL, NOON, USER, WARNING_ID, Sw6TestCase,
                         active_warning)

import frappe  # noqa: E402  (stubbed by the harness)


class AckLedgerTestCase(Sw6TestCase):
    def seed_push(self, warning_id=WARNING_ID, user=USER, severity="heads_up",
                  pushed_at=None, **extra):
        return self.db.seed(
            "Weather Notice Delivery",
            kind="subscriber", warning_id=warning_id, user=user,
            watch_location=CELL, event_class="flash_flood",
            severity=severity, push_sent_at=pushed_at or NOON, **extra)

    def ack(self, warning_id=WARNING_ID, event="seen", client_ts=None,
            user=USER):
        frappe.session.user = user
        return self.mods.ack_api.ack_weather_notice(
            warning_id=warning_id, event=event, client_ts=client_ts)


# --------------------------------------------------------------------------- #
# ledger writes
# --------------------------------------------------------------------------- #

class TestRecordPushSent(AckLedgerTestCase):
    def test_one_row_per_warning_and_user(self):
        name = self.mods.delivery.record_push_sent(
            WARNING_ID, USER, CELL, "flash_flood", "heads_up", NOON)
        self.assertIsNotNone(name)
        rows = self.db.rows("Weather Notice Delivery")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "subscriber")
        self.assertEqual(rows[0]["push_sent_at"], NOON)

    def test_repush_refreshes_timestamp_and_severity_but_keeps_the_ack(self):
        self.seed_push(acked_event="seen", acked_at=NOON, seen_at=NOON)
        later = NOON + dt.timedelta(hours=2)
        self.mods.delivery.record_push_sent(
            WARNING_ID, USER, CELL, "flash_flood", "warning", later)
        rows = self.db.rows("Weather Notice Delivery")
        self.assertEqual(len(rows), 1)  # upsert, never a duplicate
        self.assertEqual(rows[0]["push_sent_at"], later)
        self.assertEqual(rows[0]["severity"], "warning")
        self.assertEqual(rows[0]["acked_event"], "seen")

    def test_push_sync_records_a_ledger_row_per_successful_send(self):
        push_sync, proxy, push = (self.mods.push_sync, self.mods.proxy,
                                  self.mods.push)
        self.db.seed("Weather Watch Subscriber", watch_location=CELL,
                     user=USER, last_requested_at=NOON - dt.timedelta(days=1))
        sent_pushes = []
        frappe.get_attr = lambda path: (
            lambda user=None, title=None, body=None, data=None:
            sent_pushes.append(user))
        cache_store = {}
        frappe.cache = lambda: type("C", (), {
            "get_value": staticmethod(cache_store.get),
            "set_value": staticmethod(
                lambda k, v, expires_in_sec=None: cache_store.update({k: v})),
        })()
        saved_fetch = proxy.fetch_cell_warnings
        proxy.fetch_cell_warnings = (
            lambda lat, lng, locale=None: {"warnings": [active_warning()]})
        try:
            result = push_sync._sync(now=NOON)
        finally:
            proxy.fetch_cell_warnings = saved_fetch
        self.assertEqual(result["sent"], 1)
        self.assertEqual(sent_pushes, [USER])
        rows = self.db.rows("Weather Notice Delivery")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["warning_id"], WARNING_ID)
        self.assertEqual(rows[0]["user"], USER)
        self.assertEqual(rows[0]["watch_location"], CELL)
        self.assertEqual(rows[0]["push_sent_at"], NOON)
        self.assertFalse(rows[0].get("acked_event"))


# --------------------------------------------------------------------------- #
# the pinned ack contract
# --------------------------------------------------------------------------- #

class TestAckContract(AckLedgerTestCase):
    def test_the_exact_payload_upgrades_the_row_and_returns_ok(self):
        self.seed_push()
        reply = self.ack(warning_id=WARNING_ID, event="seen",
                         client_ts="2026-08-20T12:05:00Z")
        self.assertEqual(reply, {"status": "ok"})
        row = self.db.rows("Weather Notice Delivery")[0]
        self.assertEqual(row["acked_event"], "seen")
        self.assertIsNotNone(row["acked_at"])
        self.assertIsNotNone(row["seen_at"])
        self.assertEqual(row["ack_client_ts"],
                         dt.datetime(2026, 8, 20, 12, 5, 0))

    def test_upgrade_ladder_opened_beats_seen_beats_delivered(self):
        self.seed_push()
        self.ack(event="delivered")
        row = self.db.rows("Weather Notice Delivery")[0]
        self.assertEqual(row["acked_event"], "delivered")
        self.assertIsNone(row.get("seen_at"))
        self.ack(event="opened")
        self.assertEqual(row["acked_event"], "opened")
        self.assertIsNotNone(row.get("seen_at"))  # opened implies seen

    def test_replays_and_downgrades_never_write(self):
        self.seed_push()
        self.ack(event="opened")
        row = self.db.rows("Weather Notice Delivery")[0]
        first_acked_at = row["acked_at"]
        for replay in ("opened", "seen", "delivered"):
            self.assertEqual(self.ack(event=replay), {"status": "ok"})
        self.assertEqual(row["acked_event"], "opened")
        self.assertEqual(row["acked_at"], first_acked_at)

    def test_acked_at_is_the_first_ack_seen_at_the_first_at_least_seen(self):
        self.seed_push()
        early = NOON + dt.timedelta(minutes=1)
        late = NOON + dt.timedelta(minutes=30)
        self.mods.delivery.record_ack(WARNING_ID, USER, "delivered", now=early)
        self.mods.delivery.record_ack(WARNING_ID, USER, "seen", now=late)
        row = self.db.rows("Weather Notice Delivery")[0]
        self.assertEqual(row["acked_at"], early)
        self.assertEqual(row["seen_at"], late)

    def test_unknown_warning_id_is_log_and_200_and_inserts_nothing(self):
        reply = self.ack(warning_id="SWW-2026-99999", event="seen")
        self.assertEqual(reply, {"status": "ok"})
        self.assertEqual(self.db.rows("Weather Notice Delivery"), [])
        self.assertEqual(len(self.admin_logs), 1)

    def test_bad_event_and_missing_fields_are_still_200(self):
        self.seed_push()
        for bad in ({"event": "exploded"}, {"event": None},
                    {"warning_id": "", "event": "seen"},
                    {"warning_id": "x" * 500, "event": "seen"}):
            payload = {"warning_id": WARNING_ID, "event": "seen",
                       "client_ts": None}
            payload.update(bad)
            frappe.session.user = USER
            reply = self.mods.ack_api.ack_weather_notice(**payload)
            self.assertEqual(reply, {"status": "ok"})
        row = self.db.rows("Weather Notice Delivery")[0]
        self.assertFalse(row.get("acked_event"))  # nothing bad ever wrote

    def test_guest_sessions_are_a_silent_200_no_op(self):
        self.seed_push()
        frappe.session.user = "Guest"
        reply = self.mods.ack_api.ack_weather_notice(
            warning_id=WARNING_ID, event="seen")
        self.assertEqual(reply, {"status": "ok"})
        self.assertFalse(self.db.rows("Weather Notice Delivery")[0]
                         .get("acked_event"))
        self.assertEqual(self.admin_logs, [])

    def test_malformed_client_ts_is_dropped_not_an_error(self):
        self.seed_push()
        reply = self.ack(event="seen", client_ts="not-a-timestamp")
        self.assertEqual(reply, {"status": "ok"})
        row = self.db.rows("Weather Notice Delivery")[0]
        self.assertEqual(row["acked_event"], "seen")
        self.assertIsNone(row.get("ack_client_ts"))

    def test_internal_errors_are_log_and_200(self):
        self.seed_push()
        frappe.db.get_value = None  # simulate a broken shell
        frappe.session.user = USER
        reply = self.mods.ack_api.ack_weather_notice(
            warning_id=WARNING_ID, event="seen")
        self.assertEqual(reply, {"status": "ok"})
        self.assertEqual(len(self.admin_logs), 1)

    def test_acks_are_per_user_rows(self):
        self.seed_push(user="one@example.com")
        self.seed_push(user="two@example.com")
        self.ack(event="opened", user="one@example.com")
        rows = self.db.rows("Weather Notice Delivery")
        self.assertEqual(rows[0]["acked_event"], "opened")
        self.assertFalse(rows[1].get("acked_event"))


# --------------------------------------------------------------------------- #
# admin stats
# --------------------------------------------------------------------------- #

class TestNoticeStats(AckLedgerTestCase):
    def seed_cohort(self):
        """5 pushes: 1 opened (10 min to seen), 1 seen (30 min), 1 seen
        (20 min), 1 delivered-only, 1 silent."""
        minute = dt.timedelta(minutes=1)
        self.seed_push(user="u1@example.com", acked_event="opened",
                       acked_at=NOON + 10 * minute,
                       seen_at=NOON + 10 * minute)
        self.seed_push(user="u2@example.com", acked_event="seen",
                       acked_at=NOON + 30 * minute,
                       seen_at=NOON + 30 * minute)
        self.seed_push(user="u3@example.com", acked_event="seen",
                       acked_at=NOON + 20 * minute,
                       seen_at=NOON + 20 * minute)
        self.seed_push(user="u4@example.com", acked_event="delivered",
                       acked_at=NOON + 5 * minute)
        self.seed_push(user="u5@example.com")

    def test_sent_ack_pct_and_median_time_to_seen(self):
        self.seed_cohort()
        stats = self.mods.delivery.build_stats(
            self.db.get_all("Weather Notice Delivery"))
        self.assertEqual(len(stats), 1)
        agg = stats[0]
        self.assertEqual(agg["warning_id"], WARNING_ID)
        self.assertEqual(agg["sent"], 5)
        self.assertEqual(agg["acked"], 4)
        self.assertEqual(agg["ack_pct"], 80.0)
        self.assertEqual((agg["delivered"], agg["seen"], agg["opened"]),
                         (1, 2, 1))
        # median over 10/20/30 minutes-to-seen
        self.assertEqual(agg["median_minutes_to_seen"], 20.0)

    def test_even_count_medians_average_the_middle_pair(self):
        median = self.mods.delivery._median([10.0, 20.0, 40.0, 100.0])
        self.assertEqual(median, 30.0)
        self.assertIsNone(self.mods.delivery._median([]))

    def test_warnings_sort_newest_push_first(self):
        self.seed_push(warning_id="SWW-2026-00001",
                       pushed_at=NOON - dt.timedelta(hours=5))
        self.seed_push(warning_id="SWW-2026-00002", user="u2@example.com",
                       pushed_at=NOON)
        stats = self.mods.delivery.build_stats(
            self.db.get_all("Weather Notice Delivery"))
        self.assertEqual([s["warning_id"] for s in stats],
                         ["SWW-2026-00002", "SWW-2026-00001"])

    def test_endpoint_requires_system_manager(self):
        frappe.get_roles = lambda: ["Customer"]
        with self.assertRaises(frappe.PermissionError):
            self.mods.stats_api.get_weather_notice_stats()

    def test_endpoint_aggregates_for_admins(self):
        self.seed_cohort()
        frappe.get_roles = lambda: ["System Manager"]
        report = self.mods.stats_api.get_weather_notice_stats(
            warning_id=WARNING_ID)
        self.assertTrue(report["admin_only"])
        self.assertEqual(report["warnings"][0]["sent"], 5)
        self.assertEqual(report["warnings"][0]["ack_pct"], 80.0)

    def test_endpoint_reports_internal_errors_in_band(self):
        frappe.get_roles = lambda: ["System Manager"]
        frappe.get_all = None  # break the fetch
        report = self.mods.stats_api.get_weather_notice_stats()
        self.assertTrue(report["error"])
        self.assertEqual(report["warnings"], [])
        self.assertEqual(len(self.admin_logs), 1)

    def test_escalation_rows_never_pollute_subscriber_stats(self):
        self.seed_cohort()
        self.db.seed("Weather Notice Delivery", kind="escalation",
                     warning_id=WARNING_ID, contact="Ray",
                     escalation_priority=1, notified_at=NOON,
                     ack_token="tok")
        frappe.get_roles = lambda: ["System Manager"]
        report = self.mods.stats_api.get_weather_notice_stats()
        self.assertEqual(report["warnings"][0]["sent"], 5)


if __name__ == "__main__":  # pragma: no cover
    import unittest
    unittest.main()
