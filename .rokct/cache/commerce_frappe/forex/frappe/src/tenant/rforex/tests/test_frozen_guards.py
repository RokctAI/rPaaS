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

"""The frozen-parameters and holdout-era guards, pinned standalone (no
frappe, no site — `python -m unittest`).

The boundaries these tests exist to hold: **a non-draft version's spec
never changes (retuning = a NEW version)**, **tuning never reads holdout
data**, and **a holdout is evaluated once, then it is spent forever.**
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
frozen = importlib.import_module(_PKG + ".frozen")

SPEC = {"kind": "session_breakout", "symbol": "GBPUSD", "target_r": 2}
_STRATEGY_SPEC_PATH = os.path.abspath(
    os.path.join(_TESTS_DIR, "..", "strategy_spec.py"))
_DOCTYPE_PATH = os.path.abspath(os.path.join(
    _TESTS_DIR, "..", "..", "..", "tenant", "doctype",
    "forex_strategy_version", "forex_strategy_version.py"))


class TestSpecChecksum(unittest.TestCase):
    def test_checksum_is_of_meaning_not_formatting(self):
        reordered = {"target_r": 2, "symbol": "GBPUSD",
                     "kind": "session_breakout"}
        self.assertEqual(frozen.spec_checksum(SPEC),
                         frozen.spec_checksum(reordered))

    def test_any_value_change_moves_the_checksum(self):
        changed = dict(SPEC, target_r=2.5)
        self.assertNotEqual(frozen.spec_checksum(SPEC),
                            frozen.spec_checksum(changed))

    def test_canonicalisation_matches_the_catalog_doctype(self):
        # frozen._canonical must be byte-for-byte the doctype's _canonical
        # (that module imports frappe and cannot be loaded here), or the
        # control plane and the catalog would compute different identities
        # for the same spec. Pinned against the doctype's source text.
        canonical_expr = 'json.dumps(spec, sort_keys=True, separators=(",", ":"))'
        with open(_DOCTYPE_PATH) as handle:
            self.assertIn(canonical_expr, handle.read())
        with open(os.path.join(_OUTCOMES_DIR, "frozen.py")) as handle:
            self.assertIn(canonical_expr, handle.read())

    def test_editable_status_matches_the_tenant_rules_module(self):
        spec = importlib.util.spec_from_file_location(
            "rforex_strategy_spec_for_frozen_test", _STRATEGY_SPEC_PATH)
        strategy_spec = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(strategy_spec)
        self.assertEqual((frozen.EDITABLE_STATUS,),
                         strategy_spec._EDITABLE_STATUSES)


class TestGuardSpecMutation(unittest.TestCase):
    def test_a_draft_may_still_be_written(self):
        checksum = frozen.guard_spec_mutation("draft", None,
                                              dict(SPEC, target_r=3))
        self.assertEqual(checksum,
                         frozen.spec_checksum(dict(SPEC, target_r=3)))

    def test_a_reformat_of_a_published_spec_is_not_a_change(self):
        stored = frozen.spec_checksum(SPEC)
        reordered = {"target_r": 2, "symbol": "GBPUSD",
                     "kind": "session_breakout"}
        self.assertEqual(frozen.guard_spec_mutation("published", stored,
                                                    reordered), stored)

    def test_every_non_draft_status_is_frozen(self):
        stored = frozen.spec_checksum(SPEC)
        changed = dict(SPEC, target_r=99)
        for status in ("published", "retired", "blocked", None, "",
                       "something_new"):
            with self.assertRaises(frozen.FrozenConfigError, msg=status):
                frozen.guard_spec_mutation(status, stored, changed)

    def test_a_frozen_version_without_a_checksum_is_refused_not_guessed(self):
        with self.assertRaises(frozen.FrozenConfigError):
            frozen.guard_spec_mutation("published", None, SPEC)

    def test_the_error_names_the_new_version_path(self):
        with self.assertRaises(frozen.FrozenConfigError) as caught:
            frozen.guard_spec_mutation("published",
                                       frozen.spec_checksum(SPEC),
                                       dict(SPEC, target_r=9))
        self.assertIn("NEW strategy version", str(caught.exception))


def _guard():
    return frozen.BacktestEraGuard(
        tune_start="2022-01-01", tune_end="2025-01-01",
        holdout_start="2025-01-01", holdout_end="2026-01-01")


class TestBacktestEraGuard(unittest.TestCase):
    def test_misordered_or_overlapping_eras_are_refused_at_construction(self):
        cases = [
            # tune era runs backwards
            ("2025-01-01", "2022-01-01", "2025-01-01", "2026-01-01"),
            # holdout era runs backwards
            ("2022-01-01", "2025-01-01", "2026-01-01", "2025-01-01"),
            # tune era reaches into the holdout
            ("2022-01-01", "2025-06-01", "2025-01-01", "2026-01-01"),
        ]
        for eras in cases:
            with self.assertRaises(frozen.HoldoutAccessError, msg=eras):
                frozen.BacktestEraGuard(*eras)

    def test_tuning_reads_inside_the_tune_era_pass(self):
        guard = _guard()
        parsed = guard.assert_tuning_read("2023-06-15T08:00:00Z")
        self.assertEqual(parsed, dt.datetime(2023, 6, 15, 8, 0))

    def test_tuning_never_reads_the_holdout(self):
        guard = _guard()
        for ts in ("2025-01-01", "2025-06-01T00:00:00", "2026-05-01"):
            with self.assertRaises(frozen.HoldoutAccessError, msg=ts):
                guard.assert_tuning_read(ts)

    def test_tuning_stays_inside_its_declared_era_on_both_sides(self):
        with self.assertRaises(frozen.HoldoutAccessError):
            _guard().assert_tuning_read("2019-03-01")

    def test_unparseable_timestamps_are_refused_not_guessed(self):
        with self.assertRaises(frozen.HoldoutAccessError):
            _guard().assert_tuning_read("last tuesday")

    def test_the_holdout_is_evaluated_once_then_spent(self):
        guard = _guard()
        self.assertFalse(guard.holdout_spent)
        receipt = guard.begin_holdout_evaluation()
        self.assertTrue(guard.holdout_spent)
        self.assertEqual(receipt["holdout_start"], "2025-01-01T00:00:00")
        with self.assertRaises(frozen.HoldoutAccessError) as caught:
            guard.begin_holdout_evaluation()
        self.assertIn("SPENT", str(caught.exception))

    def test_no_quick_look_before_the_declared_evaluation(self):
        guard = _guard()
        with self.assertRaises(frozen.HoldoutAccessError):
            guard.assert_holdout_read("2025-06-01")

    def test_holdout_reads_stay_inside_the_holdout_era(self):
        guard = _guard()
        guard.begin_holdout_evaluation()
        guard.assert_holdout_read("2025-06-01")  # fine
        for ts in ("2024-12-31", "2026-01-01"):
            with self.assertRaises(frozen.HoldoutAccessError, msg=ts):
                guard.assert_holdout_read(ts)

    def test_tuning_is_still_refused_after_the_holdout_is_spent(self):
        # Spending the holdout does not open it to tuning reads.
        guard = _guard()
        guard.begin_holdout_evaluation()
        with self.assertRaises(frozen.HoldoutAccessError):
            guard.assert_tuning_read("2025-06-01")


if __name__ == "__main__":
    unittest.main()
