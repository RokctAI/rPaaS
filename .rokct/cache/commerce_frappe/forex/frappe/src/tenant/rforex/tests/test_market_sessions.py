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

"""The pure-UTC session model, pinned standalone (no frappe, no site —
`python -m unittest`).

The boundaries these tests hold are the documented ones exactly:
half-open [open, close) windows, the Friday 22:00 / Sunday 22:00 weekend
seam, and the rule that a closed market reports NO active sessions even
where the raw Sydney window covers early Saturday.
"""

import importlib.util
import os
import unittest
from datetime import datetime, timedelta, timezone

_MODULE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "control", "market_state", "sessions.py"
)
_spec = importlib.util.spec_from_file_location("rforex_ms_sessions", _MODULE_PATH)
sessions = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sessions)


def _wed(hour, minute=0):
    """Wednesday 2026-08-19, mid-week and far from any weekend seam."""
    return datetime(2026, 8, 19, hour, minute, tzinfo=timezone.utc)


class TestTimestampCoercion(unittest.TestCase):
    def test_naive_is_taken_as_utc(self):
        naive = datetime(2026, 8, 19, 10, 0)
        self.assertEqual(
            sessions.as_utc(naive), datetime(2026, 8, 19, 10, 0, tzinfo=timezone.utc)
        )

    def test_aware_is_converted_not_reinterpreted(self):
        # 12:00 at +02:00 is 10:00 UTC — London hours, not New York's.
        offset = timezone(timedelta(hours=2))
        moment = datetime(2026, 8, 19, 12, 0, tzinfo=offset)
        self.assertEqual(sessions.as_utc(moment).hour, 10)
        self.assertEqual(sessions.active_sessions(moment), ["london"])

    def test_non_datetime_raises(self):
        with self.assertRaises(TypeError):
            sessions.as_utc("2026-08-19T10:00:00")


class TestWeekdaySessionWindows(unittest.TestCase):
    def test_london_alone_mid_morning(self):
        self.assertEqual(sessions.active_sessions(_wed(10)), ["london"])

    def test_sydney_alone_late_evening(self):
        self.assertEqual(sessions.active_sessions(_wed(23)), ["sydney"])

    def test_sydney_and_tokyo_in_the_asian_night(self):
        self.assertEqual(sorted(sessions.active_sessions(_wed(3))), ["sydney", "tokyo"])

    def test_new_york_alone_in_the_late_us_afternoon(self):
        self.assertEqual(sessions.active_sessions(_wed(18)), ["new_york"])

    def test_open_boundary_is_inclusive(self):
        # 08:00 is London's first minute.
        self.assertIn("london", sessions.active_sessions(_wed(8, 0)))

    def test_close_boundary_is_exclusive(self):
        # 17:00 is London's first closed minute.
        self.assertNotIn("london", sessions.active_sessions(_wed(17, 0)))

    def test_tokyo_hands_over_to_london_at_nine(self):
        at_nine = sessions.active_sessions(_wed(9, 0))
        self.assertNotIn("tokyo", at_nine)
        self.assertIn("london", at_nine)

    def test_sydney_wraps_midnight(self):
        # 22:00 in, past midnight in, 07:00 out.
        self.assertIn("sydney", sessions.active_sessions(_wed(22, 0)))
        self.assertIn("sydney", sessions.active_sessions(_wed(1, 30)))
        self.assertNotIn("sydney", sessions.active_sessions(_wed(7, 0)))

    def test_new_york_close_meets_sydney_open_at_2200(self):
        at_seam = sessions.active_sessions(_wed(22, 0))
        self.assertEqual(at_seam, ["sydney"])

    def test_every_open_weekday_hour_has_at_least_one_session(self):
        # The chosen windows tile the weekday clock — no dead hour where
        # the market is open but "nothing" is trading.
        for hour in range(24):
            self.assertTrue(
                sessions.active_sessions(_wed(hour)),
                "hour {0:02d}:00 UTC has no active session".format(hour),
            )

    def test_determinism_same_ts_same_answer(self):
        moment = _wed(14, 30)
        self.assertEqual(
            sessions.session_state(moment), sessions.session_state(moment)
        )


class TestOverlaps(unittest.TestCase):
    def test_tokyo_london_overlap_window(self):
        flags = sessions.session_overlaps(_wed(8, 30))
        self.assertTrue(flags["tokyo_london"])
        self.assertFalse(flags["london_new_york"])

    def test_london_new_york_overlap_window(self):
        flags = sessions.session_overlaps(_wed(14, 0))
        self.assertTrue(flags["london_new_york"])
        self.assertFalse(flags["tokyo_london"])

    def test_no_overlap_flags_mid_morning(self):
        self.assertEqual(
            sessions.session_overlaps(_wed(10)),
            {"tokyo_london": False, "london_new_york": False},
        )

    def test_overlap_ends_when_the_earlier_session_closes(self):
        # London closes at 17:00; the London-NY overlap dies with it.
        self.assertTrue(sessions.session_overlaps(_wed(16, 59))["london_new_york"])
        self.assertFalse(sessions.session_overlaps(_wed(17, 0))["london_new_york"])

    def test_exactly_the_two_documented_flags(self):
        self.assertEqual(
            set(sessions.session_overlaps(_wed(10))), {"tokyo_london", "london_new_york"}
        )


class TestWeekendClosure(unittest.TestCase):
    # 2026-08-21 is a Friday, -22 a Saturday, -23 a Sunday.

    def test_friday_before_the_close_is_open(self):
        moment = datetime(2026, 8, 21, 21, 59, tzinfo=timezone.utc)
        self.assertTrue(sessions.is_market_open(moment))
        self.assertIn("new_york", sessions.active_sessions(moment))

    def test_friday_2200_is_the_first_closed_minute(self):
        moment = datetime(2026, 8, 21, 22, 0, tzinfo=timezone.utc)
        self.assertFalse(sessions.is_market_open(moment))

    def test_saturday_is_closed_all_day(self):
        for hour in (0, 3, 12, 23):
            moment = datetime(2026, 8, 22, hour, tzinfo=timezone.utc)
            self.assertFalse(sessions.is_market_open(moment), hour)

    def test_sunday_before_the_open_is_closed(self):
        moment = datetime(2026, 8, 23, 21, 59, tzinfo=timezone.utc)
        self.assertFalse(sessions.is_market_open(moment))

    def test_sunday_2200_is_the_first_open_minute(self):
        moment = datetime(2026, 8, 23, 22, 0, tzinfo=timezone.utc)
        self.assertTrue(sessions.is_market_open(moment))
        self.assertEqual(sessions.active_sessions(moment), ["sydney"])

    def test_monday_midnight_is_open(self):
        self.assertTrue(
            sessions.is_market_open(datetime(2026, 8, 24, 0, 0, tzinfo=timezone.utc))
        )

    def test_closed_market_reports_no_sessions_even_inside_a_raw_window(self):
        # Early Saturday sits inside the raw Sydney and Tokyo windows;
        # reporting them as trading would be fabricated liveliness.
        moment = datetime(2026, 8, 22, 2, 0, tzinfo=timezone.utc)
        self.assertTrue(sessions.raw_active_sessions(moment))
        self.assertEqual(sessions.active_sessions(moment), [])

    def test_closed_market_reports_no_overlaps(self):
        moment = datetime(2026, 8, 22, 8, 30, tzinfo=timezone.utc)
        self.assertEqual(
            sessions.session_overlaps(moment),
            {"tokyo_london": False, "london_new_york": False},
        )


class TestSessionStateShape(unittest.TestCase):
    def test_the_composed_dict(self):
        moment = _wed(14, 0)
        state = sessions.session_state(moment)
        self.assertEqual(
            set(state), {"ts", "market_open", "active", "overlaps"}
        )
        self.assertEqual(state["ts"], "2026-08-19T14:00:00+00:00")
        self.assertTrue(state["market_open"])
        self.assertEqual(sorted(state["active"]), ["london", "new_york"])
        self.assertTrue(state["overlaps"]["london_new_york"])

    def test_closed_instant_composes_consistently(self):
        moment = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
        state = sessions.session_state(moment)
        self.assertFalse(state["market_open"])
        self.assertEqual(state["active"], [])
        self.assertEqual(
            state["overlaps"], {"tokyo_london": False, "london_new_york": False}
        )


if __name__ == "__main__":
    unittest.main()
