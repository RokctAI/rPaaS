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

"""The market-state engine, pinned standalone (no frappe, no site —
`python -m unittest`).

The rates layer is MOCKED through the engine's documented override seam
(``RATES_ACCESSOR_OVERRIDE``) — these tests own the engine's composition,
caching and staleness judgement, not the fetching, which belongs to
src/control/rates and its own tests.

The boundaries held here: one evaluation is shared within the TTL, an
explicit ``ts`` never touches the shared cache, rates-layer exceptions
pass through unrepackaged, and every degraded read is labelled with the
reason for its degradation.
"""

import importlib
import importlib.util
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

_PKG_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "control", "market_state"
    )
)

# The engine does `from . import sessions, volatility`, so it must be
# loaded as a real package rather than by bare file path.
_pkg_spec = importlib.util.spec_from_file_location(
    "rforex_market_state",
    os.path.join(_PKG_DIR, "__init__.py"),
    submodule_search_locations=[_PKG_DIR],
)
_pkg = importlib.util.module_from_spec(_pkg_spec)
sys.modules["rforex_market_state"] = _pkg
_pkg_spec.loader.exec_module(_pkg)
engine = importlib.import_module("rforex_market_state.engine")

WEDNESDAY_1400 = datetime(2026, 8, 19, 14, 0, tzinfo=timezone.utc)


class _Rates(object):
    """A scripted stand-in for the rates layer's two accessors."""

    def __init__(self, rate="default", history=None):
        self.rate = rate
        self.history = history if history is not None else self._history()
        self.rate_calls = []
        self.history_calls = []

    @staticmethod
    def _rate(ts):
        return {
            "pair": "EURUSD",
            "bid": 1.0864,
            "ask": 1.0868,
            "mid": 1.0866,
            "ts": ts,
            "source": "ecb_reference",
        }

    @staticmethod
    def _history(ranges=(0.005, 0.005, 0.005, 0.005, 0.0055)):
        return [
            {
                "date": "2026-08-{0:02d}".format(day + 10),
                "open": 1.08,
                "high": 1.08 + spread,
                "low": 1.08,
                "close": 1.08,
            }
            for day, spread in enumerate(ranges)
        ]

    def get_cached_rate(self, pair):
        self.rate_calls.append(pair)
        if isinstance(self.rate, Exception):
            raise self.rate
        if self.rate == "default":
            return self._rate((WEDNESDAY_1400 - timedelta(hours=1)).isoformat())
        return self.rate

    def get_cached_history(self, pair, days):
        self.history_calls.append((pair, days))
        if isinstance(self.history, Exception):
            raise self.history
        return self.history

    def install(self):
        engine.RATES_ACCESSOR_OVERRIDE = (self.get_cached_rate, self.get_cached_history)
        return self


class EngineCase(unittest.TestCase):
    def setUp(self):
        engine.clear_cache()
        engine.RATES_ACCESSOR_OVERRIDE = None
        self._ttl = engine.CACHE_TTL_SECONDS

    def tearDown(self):
        engine.RATES_ACCESSOR_OVERRIDE = None
        engine.CACHE_TTL_SECONDS = self._ttl
        engine.clear_cache()


class TestComposition(EngineCase):
    def test_the_documented_shape(self):
        _Rates().install()
        state = engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)
        self.assertEqual(
            set(state),
            {
                "pair",
                "ts",
                "market_open",
                "sessions",
                "volatility",
                "rate",
                "rate_staleness",
                "computed_at",
            },
        )
        self.assertEqual(set(state["sessions"]), {"active", "overlaps"})
        self.assertEqual(
            set(state["rate_staleness"]),
            {"age_seconds", "threshold_seconds", "stale", "reason"},
        )

    def test_sessions_and_rate_ride_along_verbatim(self):
        rates = _Rates().install()
        state = engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)
        self.assertTrue(state["market_open"])
        self.assertEqual(sorted(state["sessions"]["active"]), ["london", "new_york"])
        self.assertTrue(state["sessions"]["overlaps"]["london_new_york"])
        self.assertEqual(state["rate"]["source"], "ecb_reference")
        self.assertEqual(state["rate"]["mid"], 1.0866)
        self.assertEqual(rates.rate_calls, ["EURUSD"])

    def test_volatility_uses_the_requested_window(self):
        rates = _Rates().install()
        state = engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)
        self.assertEqual(rates.history_calls, [("EURUSD", engine.VOLATILITY_WINDOW_DAYS)])
        self.assertEqual(state["volatility"]["state"], "normal")
        self.assertEqual(state["volatility"]["basis"], "daily_reference")

    def test_pair_is_normalised_before_the_rates_layer_sees_it(self):
        rates = _Rates().install()
        state = engine.get_market_state("  eurusd ", ts=WEDNESDAY_1400)
        self.assertEqual(state["pair"], "EURUSD")
        self.assertEqual(rates.rate_calls, ["EURUSD"])

    def test_a_blank_pair_is_refused(self):
        _Rates().install()
        with self.assertRaises(ValueError):
            engine.get_market_state("   ")

    def test_iso_string_ts_with_zulu_suffix_is_accepted(self):
        _Rates().install()
        state = engine.get_market_state("EURUSD", ts="2026-08-19T14:00:00Z")
        self.assertEqual(state["ts"], "2026-08-19T14:00:00+00:00")

    def test_weekend_instant_composes_closed_market(self):
        _Rates().install()
        state = engine.get_market_state(
            "EURUSD", ts=datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
        )
        self.assertFalse(state["market_open"])
        self.assertEqual(state["sessions"]["active"], [])


class TestStaleness(EngineCase):
    def test_an_hour_old_rate_is_fresh(self):
        _Rates().install()
        block = engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)["rate_staleness"]
        self.assertFalse(block["stale"])
        self.assertAlmostEqual(block["age_seconds"], 3600.0)
        self.assertIsNone(block["reason"])
        self.assertEqual(block["threshold_seconds"], engine.RATE_STALE_AFTER_SECONDS)

    def test_a_rate_past_the_threshold_is_stale(self):
        old_ts = (WEDNESDAY_1400 - timedelta(hours=40)).isoformat()
        _Rates(rate=_Rates._rate(old_ts)).install()
        block = engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)["rate_staleness"]
        self.assertTrue(block["stale"])
        self.assertAlmostEqual(block["age_seconds"], 40 * 3600.0)

    def test_exactly_the_threshold_is_not_yet_stale(self):
        at_ts = (WEDNESDAY_1400 - timedelta(seconds=engine.RATE_STALE_AFTER_SECONDS)).isoformat()
        _Rates(rate=_Rates._rate(at_ts)).install()
        block = engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)["rate_staleness"]
        self.assertFalse(block["stale"])

    def test_a_datetime_rate_ts_is_accepted_too(self):
        _Rates(rate=_Rates._rate(WEDNESDAY_1400 - timedelta(hours=2))).install()
        block = engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)["rate_staleness"]
        self.assertAlmostEqual(block["age_seconds"], 7200.0)

    def test_no_cached_rate_is_stale_with_its_reason(self):
        _Rates(rate=None).install()
        state = engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)
        self.assertIsNone(state["rate"])
        self.assertTrue(state["rate_staleness"]["stale"])
        self.assertEqual(state["rate_staleness"]["reason"], "no_cached_rate")
        self.assertIsNone(state["rate_staleness"]["age_seconds"])

    def test_an_unparseable_rate_ts_is_stale_with_its_reason(self):
        _Rates(rate=_Rates._rate("not-a-timestamp")).install()
        block = engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)["rate_staleness"]
        self.assertTrue(block["stale"])
        self.assertEqual(block["reason"], "unparseable_rate_ts")

    def test_no_rates_layer_at_all_is_labelled_not_papered_over(self):
        # No override, no composed ..rates sibling, no frappe: the seam
        # resolves nothing and the state says exactly that — while the
        # session verdict stays fully populated.
        state = engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)
        self.assertIsNone(state["rate"])
        self.assertEqual(state["rate_staleness"]["reason"], "rates_layer_unavailable")
        self.assertTrue(state["rate_staleness"]["stale"])
        self.assertEqual(state["volatility"]["state"], "unknown")
        self.assertTrue(state["market_open"])
        self.assertEqual(sorted(state["sessions"]["active"]), ["london", "new_york"])


class TestRatesExceptionsPropagate(EngineCase):
    def test_a_rate_refusal_surfaces_as_itself(self):
        _Rates(rate=LookupError("unknown pair XXXYYY")).install()
        with self.assertRaises(LookupError):
            engine.get_market_state("XXXYYY", ts=WEDNESDAY_1400)

    def test_a_history_refusal_surfaces_as_itself(self):
        rates = _Rates()
        rates.history = LookupError("no history")
        rates.install()
        with self.assertRaises(LookupError):
            engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)


class TestCaching(EngineCase):
    def test_the_present_is_computed_once_and_shared(self):
        rates = _Rates().install()
        first = engine.get_market_state("EURUSD")
        second = engine.get_market_state("EURUSD")
        self.assertEqual(rates.rate_calls, ["EURUSD"])
        self.assertEqual(first, second)
        self.assertEqual(first["computed_at"], second["computed_at"])

    def test_pairs_are_cached_independently(self):
        rates = _Rates().install()
        engine.get_market_state("EURUSD")
        engine.get_market_state("GBPUSD")
        self.assertEqual(rates.rate_calls, ["EURUSD", "GBPUSD"])

    def test_expiry_forces_a_recomputation(self):
        rates = _Rates().install()
        engine.CACHE_TTL_SECONDS = 0  # everything written is already expired
        engine.get_market_state("EURUSD")
        engine.get_market_state("EURUSD")
        self.assertEqual(rates.rate_calls, ["EURUSD", "EURUSD"])

    def test_clear_cache_forgets_one_pair(self):
        rates = _Rates().install()
        engine.get_market_state("EURUSD")
        engine.clear_cache("eurusd")
        engine.get_market_state("EURUSD")
        self.assertEqual(rates.rate_calls, ["EURUSD", "EURUSD"])

    def test_an_explicit_ts_bypasses_the_cache_in_both_directions(self):
        rates = _Rates().install()
        engine.get_market_state("EURUSD")  # primes the shared cache
        engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)
        engine.get_market_state("EURUSD", ts=WEDNESDAY_1400)
        # Each explicit-ts call recomputed; none was served from or
        # written into the shared cache.
        self.assertEqual(len(rates.rate_calls), 3)
        engine.get_market_state("EURUSD")
        self.assertEqual(len(rates.rate_calls), 3)


if __name__ == "__main__":
    unittest.main()
