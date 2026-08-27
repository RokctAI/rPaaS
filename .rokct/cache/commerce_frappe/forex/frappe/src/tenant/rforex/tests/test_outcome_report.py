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

"""The retraining report's arithmetic, pinned against hand-computed
fixtures (no frappe, no site — `python -m unittest`).

The boundaries these tests exist to hold: **every settled signal counts in
every denominator (expiries included)**, **outcomes are grouped per frozen
strategy version and never pooled across checksums**, and **below the
documented minimum the answer is `insufficient_data`, not a rate.**
"""

import datetime as dt
import importlib
import importlib.util
import os
import sys
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_OUTCOMES_DIR = os.path.abspath(
    os.path.join(_TESTS_DIR, "..", "..", "..", "control", "outcomes"))
_PKG = "rforex_control_outcomes"


def _load_outcomes_package():
    if _PKG in sys.modules:
        return sys.modules[_PKG]
    spec = importlib.util.spec_from_file_location(
        _PKG,
        os.path.join(_OUTCOMES_DIR, "__init__.py"),
        submodule_search_locations=[_OUTCOMES_DIR],
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[_PKG] = package
    spec.loader.exec_module(package)
    return package


_load_outcomes_package()
ledger = importlib.import_module(_PKG + ".ledger")
report = importlib.import_module(_PKG + ".report")

V1 = "a" * 64
V2 = "b" * 64
BASE = dt.datetime(2026, 6, 1, 8, 0)


def _row(index, outcome, pips, strategy_id="london_breakout", checksum=V1,
         hours_open=2):
    """One hand-built ledger-shaped row; entry times step one day per
    index so the entry order is exactly the index order."""
    entry = BASE + dt.timedelta(days=index)
    settled = outcome is not None
    return {
        "name": "SIG-{0:03d}".format(index),
        "strategy_id": strategy_id,
        "strategy_checksum": checksum,
        "pair": "GBPUSD",
        "direction": "long",
        "entry_ts": entry.isoformat(),
        "entry_price": 1.27,
        "risk_preset": "balanced",
        "signal_meta": None,
        "outcome": outcome,
        "exit_ts": ((entry + dt.timedelta(hours=hours_open)).isoformat()
                    if settled else None),
        "exit_price": 1.28 if settled and outcome != "expired" else None,
        "pips": pips,
        "outcome_meta": None,
        "recorded_at": entry.isoformat(),
        "settled_at": None,
    }


def _fixture_a():
    """25 settled + 2 open signals, one version. Hand-computed:

    12 wins at +20 pips           = +240
     8 losses at -10 pips         =  -80   (streaks of 1, 3, 2 by entry order)
     2 scratches at 0 pips        =    0
     3 expired (0, 0, pips=None)  =    0
                                    ----
    sum over settled              = +160

    win_rate        = 12 / 25            = 0.48   (expiries in denominator)
    average_pips    = 160 / 24           = 6.666… (24 rows carry a pips value)
    expectancy_pips = 160 / 25           = 6.4    (missing pips counts as 0)
    max_consecutive_losses               = 3
    period          = entry of index 0 .. exit of index 26
    """
    rows = []
    outcomes = (
        ["win", "loss"]                       # streak 1
        + ["win"] * 3
        + ["loss", "loss", "loss"]            # streak 3
        + ["win"] * 3 + ["scratch"]
        + ["loss", "loss"]                    # streak 2
        + ["win"] * 3 + ["scratch", "expired"]
        + ["win", "loss", "loss"]             # streak 2
        + ["expired", "expired", "win"]
    )
    assert len(outcomes) == 25
    pips_by_outcome = {"win": 20.0, "loss": -10.0, "scratch": 0.0}
    expired_pips = iter([0.0, 0.0, None])
    for index, outcome in enumerate(outcomes):
        if outcome == "expired":
            pips = next(expired_pips)
        else:
            pips = pips_by_outcome[outcome]
        rows.append(_row(index, outcome, pips))
    rows.append(_row(25, None, None))  # still open
    rows.append(_row(26, None, None))  # still open
    return rows


class TestSummarizeVersion(unittest.TestCase):
    def test_the_hand_computed_fixture(self):
        summary = report.summarize_version(_fixture_a())
        self.assertEqual(summary["counts"], {
            "signals": 27, "open": 2, "settled": 25,
            "win": 12, "loss": 8, "scratch": 2, "expired": 3,
        })
        self.assertEqual(summary["win_rate"], 0.48)
        self.assertEqual(summary["average_pips"], 6.7)     # 160/24 = 6.67
        self.assertEqual(summary["expectancy_pips"], 6.4)  # 160/25
        self.assertEqual(summary["max_consecutive_losses"], 3)
        self.assertEqual(summary["state"], report.STATE_REPORTED)
        self.assertEqual(summary["period"]["from"], BASE.isoformat())
        self.assertEqual(
            summary["period"]["to"],
            (BASE + dt.timedelta(days=26)).isoformat())  # open row's entry

    def test_entry_order_not_list_order_decides_the_streak(self):
        # Three losses adjacent in the list but split by entry time, and
        # two losses adjacent in entry time but split in the list.
        rows = [
            _row(0, "loss", -10),
            _row(4, "loss", -10),
            _row(5, "loss", -10),
            _row(1, "win", 20),
        ]
        summary = report.summarize_version(rows)
        self.assertEqual(summary["max_consecutive_losses"], 2)

    def test_expiries_drag_the_win_rate_down(self):
        # 10 wins + 10 expiries: an expiry is a settled signal, so the win
        # rate is 0.5, not 1.0 — leaving them out would inflate every rate.
        rows = [_row(i, "win", 10) for i in range(10)]
        rows += [_row(10 + i, "expired", 0) for i in range(10)]
        summary = report.summarize_version(rows)
        self.assertEqual(summary["win_rate"], 0.5)
        self.assertEqual(summary["state"], report.STATE_REPORTED)

    def test_below_the_minimum_the_state_is_insufficient(self):
        rows = [_row(i, "win", 10) for i in range(report.MIN_SETTLED_FOR_REPORT - 1)]
        rows.append(_row(99, None, None))  # open rows don't count
        summary = report.summarize_version(rows)
        self.assertEqual(summary["state"], report.STATE_INSUFFICIENT)
        self.assertIn("insufficient data", summary["detail"])
        self.assertIn(str(report.MIN_SETTLED_FOR_REPORT), summary["detail"])

    def test_the_empty_ledger_divides_nothing_by_zero(self):
        summary = report.summarize_version([])
        self.assertEqual(summary["counts"]["settled"], 0)
        self.assertIsNone(summary["win_rate"])
        self.assertIsNone(summary["average_pips"])
        self.assertIsNone(summary["expectancy_pips"])
        self.assertEqual(summary["max_consecutive_losses"], 0)
        self.assertEqual(summary["state"], report.STATE_INSUFFICIENT)
        self.assertEqual(summary["period"], {"from": None, "to": None})

    def test_no_smoothing_a_streak_of_losses_is_reported_as_is(self):
        rows = [_row(i, "loss", -10) for i in range(20)]
        summary = report.summarize_version(rows)
        self.assertEqual(summary["win_rate"], 0.0)
        self.assertEqual(summary["max_consecutive_losses"], 20)
        self.assertEqual(summary["expectancy_pips"], -10.0)
        self.assertEqual(summary["state"], report.STATE_REPORTED)


class TestGrouping(unittest.TestCase):
    def test_versions_are_never_pooled(self):
        rows = ([_row(i, "win", 10, checksum=V1) for i in range(3)]
                + [_row(10 + i, "loss", -10, checksum=V2) for i in range(2)])
        groups = report.group_by_version(rows)
        self.assertEqual(
            set(groups), {("london_breakout", V1), ("london_breakout", V2)})
        self.assertEqual(len(groups[("london_breakout", V1)]), 3)
        self.assertEqual(len(groups[("london_breakout", V2)]), 2)

    def test_rows_without_an_identity_are_counted_not_dropped(self):
        rows = [_row(0, "win", 10)]
        rows.append(dict(_row(1, "win", 10), strategy_checksum=None))
        rows.append(dict(_row(2, "win", 10), strategy_id=""))
        groups = report.group_by_version(rows)
        self.assertEqual(len(groups[("_unidentified", "")]), 2)

    def test_get_strategy_report_filters_and_keys_by_checksum(self):
        rows = ([_row(i, "win", 10, checksum=V1) for i in range(2)]
                + [_row(5, "loss", -5, checksum=V2)]
                + [_row(9, "win", 10, strategy_id="other", checksum=V1)])
        payload = report.get_strategy_report("london_breakout", rows=rows)
        self.assertEqual(payload["strategy_id"], "london_breakout")
        self.assertEqual(payload["total_signals"], 3)
        self.assertEqual(set(payload["versions"]), {V1, V2})
        self.assertEqual(payload["versions"][V1]["counts"]["win"], 2)
        self.assertEqual(payload["versions"][V2]["counts"]["loss"], 1)


class TestBuildReport(unittest.TestCase):
    def test_shape_and_summary_text(self):
        rows = _fixture_a() + [dict(_row(50, "win", 10), strategy_id=None)]
        payload = report.build_report(rows)
        self.assertTrue(payload["admin_only"])
        self.assertEqual(payload["total_signals"], 28)
        self.assertEqual(payload["unidentified_rows"], 1)
        self.assertIn("london_breakout", payload["strategies"])
        self.assertIn(V1, payload["strategies"]["london_breakout"])
        self.assertIn("london_breakout", payload["summary"])
        self.assertIn("48.0%", payload["summary"])
        self.assertIn("NEW strategy version", payload["summary"])

    def test_end_to_end_over_the_live_ledger(self):
        ledger.reset_memory_store()
        entry = dt.datetime(2026, 8, 3, 8, 15)
        signal_id = ledger.record_signal(
            "london_breakout", V1, "GBPUSD", "long", entry, 1.2754)
        ledger.record_outcome(signal_id, entry + dt.timedelta(hours=2),
                              1.2794, "win", 40)
        ledger.record_signal(
            "london_breakout", V1, "GBPUSD", "short",
            entry + dt.timedelta(days=1), 1.2701)
        payload = report.build_report(ledger.list_signals())
        summary = payload["strategies"]["london_breakout"][V1]
        self.assertEqual(summary["counts"]["signals"], 2)
        self.assertEqual(summary["counts"]["settled"], 1)
        self.assertEqual(summary["state"], report.STATE_INSUFFICIENT)
        ledger.reset_memory_store()


if __name__ == "__main__":
    unittest.main()
