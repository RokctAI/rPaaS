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

"""The outcome ledger's rules, pinned standalone (no frappe, no site —
`python -m unittest`, in-memory storage backend).

The boundaries these tests exist to hold: **a signal is logged at emission
with its exact strategy-version identity**, **a half-described signal or
outcome is refused with every problem named**, and **a verdict is written
exactly once — never edited, never re-settled.**
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
    """Load src/control/outcomes as a real package so its intra-package
    imports bind every test file to the same module objects (and the same
    in-memory store)."""
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

CHECKSUM = "a" * 64
ENTRY = dt.datetime(2026, 8, 3, 8, 15)


def _signal(**overrides):
    kwargs = {
        "strategy_id": "london_breakout",
        "strategy_checksum": CHECKSUM,
        "pair": "GBPUSD",
        "direction": ledger.DIRECTION_LONG,
        "entry_ts": ENTRY,
        "entry_price": 1.27543,
    }
    kwargs.update(overrides)
    return ledger.record_signal(**kwargs)


class LedgerCase(unittest.TestCase):
    def setUp(self):
        ledger.reset_memory_store()


class TestRecordSignal(LedgerCase):
    def test_roundtrip_returns_the_stored_row(self):
        signal_id = _signal(pair="gbpusd ", risk_preset=" balanced ",
                            meta={"range_pips": 32})
        row = ledger.get_signal(signal_id)
        self.assertEqual(row["strategy_id"], "london_breakout")
        self.assertEqual(row["strategy_checksum"], CHECKSUM)
        self.assertEqual(row["pair"], "GBPUSD")  # normalised
        self.assertEqual(row["direction"], "long")
        self.assertEqual(row["entry_ts"], ENTRY.isoformat())
        self.assertEqual(row["entry_price"], 1.27543)
        self.assertEqual(row["risk_preset"], "balanced")
        self.assertEqual(row["signal_meta"], '{"range_pips": 32}')
        self.assertIsNone(row["outcome"])
        self.assertIsNone(row["settled_at"])
        self.assertTrue(row["recorded_at"])

    def test_ids_are_unique(self):
        ids = {_signal() for _ in range(5)}
        self.assertEqual(len(ids), 5)

    def test_iso_strings_are_accepted_for_entry_ts(self):
        signal_id = _signal(entry_ts="2026-08-03T08:15:00Z")
        row = ledger.get_signal(signal_id)
        self.assertEqual(row["entry_ts"], "2026-08-03T08:15:00+00:00")

    def test_every_problem_is_reported_at_once(self):
        with self.assertRaises(ledger.LedgerError) as caught:
            _signal(direction="up", entry_price=0)
        message = str(caught.exception)
        self.assertIn("direction", message)
        self.assertIn("entry_price", message)

    def test_missing_version_checksum_is_refused(self):
        # Outcomes are only meaningful per frozen parameter set; a signal
        # that cannot say which version emitted it is not evidence.
        for checksum in ("", "   ", None, 7):
            with self.assertRaises(ledger.LedgerError):
                _signal(strategy_checksum=checksum)

    def test_bad_fields_are_refused(self):
        bad = [
            {"strategy_id": ""},
            {"pair": "  "},
            {"direction": "buy"},
            {"entry_ts": "not-a-time"},
            {"entry_price": -1},
            {"entry_price": float("nan")},
            {"entry_price": True},
            {"meta": "not-a-dict"},
        ]
        for overrides in bad:
            with self.assertRaises(ledger.LedgerError, msg=overrides):
                _signal(**overrides)
        self.assertEqual(ledger.list_signals(), [])  # nothing half-written


class TestRecordOutcome(LedgerCase):
    def test_settling_a_win(self):
        signal_id = _signal()
        row = ledger.record_outcome(
            signal_id,
            exit_ts=ENTRY + dt.timedelta(hours=3),
            exit_price=1.27943,
            outcome=ledger.OUTCOME_WIN,
            pips=40.0,
            meta={"closed_by": "target"},
        )
        self.assertEqual(row["outcome"], "win")
        self.assertEqual(row["pips"], 40.0)
        self.assertEqual(row["exit_price"], 1.27943)
        self.assertEqual(row["outcome_meta"], '{"closed_by": "target"}')
        self.assertTrue(row["settled_at"])

    def test_a_verdict_is_written_once(self):
        signal_id = _signal()
        ledger.record_outcome(signal_id, ENTRY + dt.timedelta(hours=1),
                              1.2704, ledger.OUTCOME_LOSS, -50.3)
        with self.assertRaises(ledger.LedgerError) as caught:
            ledger.record_outcome(signal_id, ENTRY + dt.timedelta(hours=2),
                                  1.2804, ledger.OUTCOME_WIN, 49.7)
        self.assertIn("already settled", str(caught.exception))
        # And the first verdict still stands, untouched.
        self.assertEqual(ledger.get_signal(signal_id)["outcome"], "loss")
        self.assertEqual(ledger.get_signal(signal_id)["pips"], -50.3)

    def test_an_outcome_needs_its_signal(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.record_outcome("FXSO-MEM-99999", ENTRY, 1.28,
                                  ledger.OUTCOME_WIN, 10)

    def test_unknown_outcomes_are_refused(self):
        signal_id = _signal()
        with self.assertRaises(ledger.LedgerError):
            ledger.record_outcome(signal_id, ENTRY, 1.28, "breakeven", 0)

    def test_exit_before_entry_is_refused(self):
        signal_id = _signal()
        with self.assertRaises(ledger.LedgerError):
            ledger.record_outcome(signal_id, ENTRY - dt.timedelta(hours=1),
                                  1.28, ledger.OUTCOME_WIN, 10)

    def test_expired_needs_no_exit_price_but_still_needs_pips(self):
        signal_id = _signal()
        row = ledger.record_outcome(signal_id, ENTRY + dt.timedelta(hours=8),
                                    None, ledger.OUTCOME_EXPIRED, 0)
        self.assertEqual(row["outcome"], "expired")
        self.assertIsNone(row["exit_price"])
        self.assertEqual(row["pips"], 0.0)

        other = _signal()
        with self.assertRaises(ledger.LedgerError):
            ledger.record_outcome(other, ENTRY + dt.timedelta(hours=8),
                                  None, ledger.OUTCOME_EXPIRED, None)

    def test_non_expired_outcomes_need_an_exit_price(self):
        signal_id = _signal()
        with self.assertRaises(ledger.LedgerError):
            ledger.record_outcome(signal_id, ENTRY + dt.timedelta(hours=1),
                                  None, ledger.OUTCOME_WIN, 10)


class TestListSignals(LedgerCase):
    def _seed(self):
        a = _signal(entry_ts=ENTRY + dt.timedelta(days=1))
        b = _signal(entry_ts=ENTRY, pair="EURUSD")
        c = _signal(entry_ts=ENTRY + dt.timedelta(days=2),
                    strategy_id="other_strategy", strategy_checksum="b" * 64)
        ledger.record_outcome(a, ENTRY + dt.timedelta(days=1, hours=2),
                              1.28, ledger.OUTCOME_WIN, 25)
        return a, b, c

    def test_ordering_is_by_entry_time_not_insert_order(self):
        a, b, c = self._seed()
        self.assertEqual([r["name"] for r in ledger.list_signals()],
                         [b, a, c])

    def test_mixed_aware_and_naive_timestamps_still_sort(self):
        _signal(entry_ts="2026-08-01T00:00:00+00:00")
        _signal(entry_ts=dt.datetime(2026, 8, 2, 0, 0))
        self.assertEqual(len(ledger.list_signals()), 2)

    def test_filters(self):
        a, b, c = self._seed()
        self.assertEqual(
            [r["name"] for r in ledger.list_signals(strategy_id="london_breakout")],
            [b, a])
        self.assertEqual(
            [r["name"] for r in ledger.list_signals(pair="eurusd")], [b])
        self.assertEqual(
            [r["name"] for r in ledger.list_signals(outcome="win")], [a])
        self.assertEqual(
            [r["name"] for r in ledger.list_signals(settled=True)], [a])
        self.assertEqual(
            [r["name"] for r in ledger.list_signals(settled=False)], [b, c])
        self.assertEqual(
            [r["name"] for r in ledger.list_signals(
                strategy_checksum="b" * 64)], [c])

    def test_rows_are_copies_not_live_references(self):
        signal_id = _signal()
        ledger.list_signals()[0]["outcome"] = "win"
        self.assertIsNone(ledger.get_signal(signal_id)["outcome"])


if __name__ == "__main__":
    unittest.main()
