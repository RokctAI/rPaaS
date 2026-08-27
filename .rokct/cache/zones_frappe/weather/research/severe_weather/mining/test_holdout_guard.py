"""Tests that the holdout guard in data.py refuses every route to holdout series.

Run directly (python3 test_holdout_guard.py) or via pytest. The tests read holdout
series_ids from manifest METADATA only (to name what must be refused); no holdout
series values are ever loaded.
"""
from __future__ import annotations

import pandas as pd

import data
from data import HoldoutAccessError


def _expect_refusal(fn, what):
    try:
        fn()
    except HoldoutAccessError:
        return
    raise AssertionError(f"{what} did NOT raise HoldoutAccessError")


def test_cohort_argument_refused():
    _expect_refusal(lambda: data.load_series("flood", cohort="holdout"),
                    "load_series(cohort='holdout')")
    _expect_refusal(lambda: data.load_series("tornado", cohort="all"),
                    "load_series(cohort='all')")


def test_manifest_is_dev_only():
    m = data.load_manifest()
    assert (m["cohort"] == "dev").all(), "load_manifest leaked non-dev rows"
    assert (m["onset_catalog"] < pd.Timestamp("2018-01-01")).all(), \
        "load_manifest leaked post-2018 onsets"


def test_holdout_series_id_refused():
    raw = data._read_manifest_raw()
    hold = raw[raw["cohort"] == "holdout"]
    assert len(hold) > 0, "manifest has no holdout rows to test against"
    for klass in hold["event_class"].unique():
        sid = hold.loc[hold["event_class"] == klass, "series_id"].iloc[0]
        _expect_refusal(lambda s=sid, k=klass: data.load_series(k, series_ids=[s]),
                        f"load_series({klass!r}, series_ids=[holdout id])")


def test_loaded_data_is_dev_only():
    holdout = set(data._read_manifest_raw()
                  .loc[lambda d: d["cohort"] != "dev", "series_id"])
    any_loaded = False
    for klass in data.CLASSES:
        series = data.load_series(klass, max_events=3)
        leaked = set(series) & holdout
        assert not leaked, f"{klass}: holdout series leaked into load: {sorted(leaked)}"
        any_loaded = any_loaded or bool(series)
    assert any_loaded, "no series loadable at all - cannot verify data path"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("holdout guard: all tests passed")
