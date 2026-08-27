"""Prove the backtest's holdout gate refuses everything it must refuse.

Checks (none of them touches real holdout data):
  1. CLI: --cohort holdout without the flags -> non-zero exit, refusal message,
     no marker file created.
  2. CLI: --cohort holdout --holdout (missing --i-understand-single-use) ->
     refused, no marker.
  3. API: holdout_gate with both flags but an existing marker -> refused
     (single use), using a temp marker path so the real one is never written.
  4. API: the holdout loader raises HoldoutAccessError when the gate has not
     been passed.
  5. tune.py / dev path: mining/data.py refuses cohort="holdout" outright.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import backtest
import data

MARKER = backtest.MARKER_PATH
FAILS = []


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def cli(args):
    return subprocess.run([sys.executable, os.path.join(HERE, "backtest.py"), *args],
                          capture_output=True, text=True)


def main():
    assert not os.path.exists(MARKER), (
        "real HOLDOUT_RUN_MARKER.json already exists - refusing to run tests "
        "that could be confused with the real single-use record")

    print("1. CLI refusal without flags")
    r = cli(["--cohort", "holdout"])
    check("non-zero exit", r.returncode != 0)
    check("refusal message", "REFUSED" in (r.stderr + r.stdout))
    check("no marker written", not os.path.exists(MARKER))

    print("2. CLI refusal with only --holdout")
    r = cli(["--cohort", "holdout", "--holdout"])
    check("non-zero exit", r.returncode != 0)
    check("no marker written", not os.path.exists(MARKER))

    print("3. single-use: existing marker refuses even with both flags")
    with tempfile.TemporaryDirectory() as td:
        tmp_marker = os.path.join(td, "marker.json")
        with open(tmp_marker, "w") as f:
            f.write("{}")
        try:
            backtest.holdout_gate(True, True, backtest.DEFAULT_CONFIG,
                                  marker_path=tmp_marker)
            check("refused on existing marker", False)
        except SystemExit as e:
            check("refused on existing marker", "REFUSED" in str(e))
        backtest._HOLDOUT_UNLOCKED = False   # undo any state, belt and braces

    print("4. holdout loader refuses when not gated")
    try:
        backtest._load_holdout_series("flood")
        check("loader raises", False)
    except data.HoldoutAccessError:
        check("loader raises HoldoutAccessError", True)

    print("5. dev data layer refuses holdout cohort")
    try:
        data.load_series("flood", cohort="holdout")
        check("data.load_series refuses", False)
    except data.HoldoutAccessError:
        check("data.load_series refuses", True)

    check("real marker still absent at end", not os.path.exists(MARKER))
    if FAILS:
        print(f"\n{len(FAILS)} FAILURES: {FAILS}")
        sys.exit(1)
    print("\nall holdout-gate checks passed")


if __name__ == "__main__":
    main()
