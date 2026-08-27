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

"""The volatility buckets, pinned standalone (no frappe, no site —
`python -m unittest`).

The boundary these tests hold: **thin or broken history yields
"unknown", never a fabricated "normal"** — and the latest candle never
judges itself by being averaged into its own baseline.
"""

import importlib.util
import os
import unittest

_MODULE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "control", "market_state", "volatility.py",
)
_spec = importlib.util.spec_from_file_location("rforex_ms_volatility", _MODULE_PATH)
volatility = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(volatility)


def _candles(*ranges):
    """Daily candles with the given (high - low) ranges, oldest first."""
    return [
        {"date": "2026-08-{0:02d}".format(day + 1), "open": 1.0, "high": 1.0 + spread, "low": 1.0, "close": 1.0}
        for day, spread in enumerate(ranges)
    ]


class TestAverageDailyRange(unittest.TestCase):
    def test_average_excludes_the_latest_candle(self):
        # Baseline is [1, 1, 1]; the wide latest candle must not drag it.
        self.assertAlmostEqual(
            volatility.average_daily_range(_candles(1.0, 1.0, 1.0, 4.0)), 1.0
        )

    def test_average_is_the_baseline_mean(self):
        self.assertAlmostEqual(
            volatility.average_daily_range(_candles(1.0, 2.0, 3.0, 9.9)), 2.0
        )

    def test_too_few_baseline_candles_is_none(self):
        # Three candles = two baseline candles < MIN_BASELINE_DAYS.
        self.assertIsNone(volatility.average_daily_range(_candles(1.0, 1.0, 1.0)))

    def test_minimum_baseline_is_exactly_min_baseline_days(self):
        history = _candles(*([1.0] * volatility.MIN_BASELINE_DAYS + [2.0]))
        self.assertAlmostEqual(volatility.average_daily_range(history), 1.0)


class TestUnusableCandlesAreDroppedNotRepaired(unittest.TestCase):
    def test_malformed_entries_are_skipped(self):
        history = _candles(1.0, 1.0, 1.0, 1.0)
        history.insert(1, {"date": "x", "high": "n/a", "low": 1.0})  # non-numeric
        history.insert(2, {"date": "x", "low": 1.0})  # missing high
        history.insert(3, "not-a-candle")  # not a dict
        history.insert(4, {"date": "x", "high": 1.0, "low": 2.0})  # inverted
        self.assertEqual(volatility.usable_ranges(history), [1.0, 1.0, 1.0, 1.0])

    def test_non_list_history_is_empty(self):
        self.assertEqual(volatility.usable_ranges(None), [])
        self.assertEqual(volatility.usable_ranges({"high": 1, "low": 0}), [])


class TestClassify(unittest.TestCase):
    def test_quiet_below_the_lower_threshold(self):
        self.assertEqual(volatility.classify(0.69), "quiet")

    def test_lower_threshold_itself_is_normal(self):
        self.assertEqual(volatility.classify(volatility.QUIET_BELOW), "normal")

    def test_normal_between_the_thresholds(self):
        self.assertEqual(volatility.classify(1.0), "normal")
        self.assertEqual(volatility.classify(1.29), "normal")

    def test_upper_threshold_itself_is_elevated(self):
        self.assertEqual(volatility.classify(volatility.ELEVATED_AT), "elevated")

    def test_none_is_unknown(self):
        self.assertEqual(volatility.classify(None), "unknown")


class TestEvaluate(unittest.TestCase):
    def test_shape_and_honesty_marker(self):
        verdict = volatility.evaluate(_candles(1.0, 1.0, 1.0, 1.0))
        self.assertEqual(
            set(verdict),
            {
                "basis",
                "sample_size",
                "average_daily_range",
                "latest_daily_range",
                "ratio",
                "state",
            },
        )
        self.assertEqual(verdict["basis"], "daily_reference")

    def test_a_wide_latest_day_is_elevated(self):
        verdict = volatility.evaluate(_candles(1.0, 1.0, 1.0, 2.0))
        self.assertAlmostEqual(verdict["ratio"], 2.0)
        self.assertEqual(verdict["state"], "elevated")

    def test_a_narrow_latest_day_is_quiet(self):
        verdict = volatility.evaluate(_candles(1.0, 1.0, 1.0, 0.5))
        self.assertAlmostEqual(verdict["ratio"], 0.5)
        self.assertEqual(verdict["state"], "quiet")

    def test_an_ordinary_latest_day_is_normal(self):
        verdict = volatility.evaluate(_candles(1.0, 1.0, 1.0, 1.1))
        self.assertEqual(verdict["state"], "normal")

    def test_thin_history_is_unknown_not_normal(self):
        verdict = volatility.evaluate(_candles(1.0, 1.0))
        self.assertEqual(verdict["state"], "unknown")
        self.assertIsNone(verdict["ratio"])
        self.assertIsNone(verdict["average_daily_range"])
        self.assertEqual(verdict["sample_size"], 2)

    def test_empty_and_absent_history_are_unknown(self):
        for history in ([], None):
            verdict = volatility.evaluate(history)
            self.assertEqual(verdict["state"], "unknown", history)
            self.assertIsNone(verdict["latest_daily_range"], history)
            self.assertEqual(verdict["sample_size"], 0, history)

    def test_a_flat_zero_baseline_is_unknown_not_a_division(self):
        verdict = volatility.evaluate(_candles(0.0, 0.0, 0.0, 0.5))
        self.assertIsNone(verdict["ratio"])
        self.assertEqual(verdict["state"], "unknown")
        self.assertEqual(verdict["average_daily_range"], 0.0)

    def test_latest_range_is_reported_even_when_baseline_is_thin(self):
        verdict = volatility.evaluate(_candles(1.0, 2.0))
        self.assertAlmostEqual(verdict["latest_daily_range"], 2.0)


if __name__ == "__main__":
    unittest.main()
