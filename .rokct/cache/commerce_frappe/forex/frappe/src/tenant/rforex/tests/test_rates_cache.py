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

"""The shared per-pair rate cache, pinned standalone (no frappe, no site,
no network — `python -m unittest`).

The boundary these tests hold: **one fetch is shared by every consumer
and every spelling of a pair, until its TTL runs out** — and a malformed
request never reaches a provider at all.

The provider underneath is a counting stub, patched in at the factory
seam; the store exercised is the in-process fallback, which carries the
same TTL semantics as the frappe.cache() path.
"""

import importlib
import importlib.util
import os
import sys
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_RATES_DIR = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "control", "rates"))
_PKG = "rforex_control_rates"


def _load_rates_package():
    if _PKG not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            _PKG,
            os.path.join(_RATES_DIR, "__init__.py"),
            submodule_search_locations=[_RATES_DIR],
        )
        package = importlib.util.module_from_spec(spec)
        sys.modules[_PKG] = package
        spec.loader.exec_module(package)
    return sys.modules[_PKG]


_load_rates_package()
provider = importlib.import_module(_PKG + ".provider")
cache = importlib.import_module(_PKG + ".cache")


class _CountingProvider(provider.RatesProvider):
    source = "counting"

    def __init__(self):
        self.rate_calls = []
        self.history_calls = []

    def get_rate(self, pair):
        self.rate_calls.append(pair)
        return {
            "pair": pair,
            "bid": 1.1,
            "ask": 1.1,
            "mid": 1.1,
            "ts": "2026-08-22T00:00:00+00:00",
            "source": self.source,
        }

    def get_history(self, pair, days):
        self.history_calls.append((pair, days))
        return [
            {"date": "2026-08-21", "open": 1.1, "high": 1.1, "low": 1.1, "close": 1.1}
        ]


class RatesCacheCase(unittest.TestCase):
    def setUp(self):
        cache.clear_local_cache()
        self.provider = _CountingProvider()
        patcher = mock.patch.object(
            provider, "get_rates_provider", return_value=self.provider
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(cache.clear_local_cache)


class TestRateCaching(RatesCacheCase):
    def test_repeated_reads_share_one_fetch(self):
        first = cache.get_cached_rate("EURUSD")
        second = cache.get_cached_rate("EURUSD")
        self.assertEqual(self.provider.rate_calls, ["EURUSD"])
        self.assertEqual(first, second)

    def test_every_spelling_of_a_pair_shares_the_entry(self):
        cache.get_cached_rate("EUR/USD")
        cache.get_cached_rate("eurusd")
        cache.get_cached_rate(" EUR/usd ")
        self.assertEqual(self.provider.rate_calls, ["EURUSD"])

    def test_different_pairs_are_different_entries(self):
        cache.get_cached_rate("EURUSD")
        cache.get_cached_rate("GBPUSD")
        self.assertEqual(self.provider.rate_calls, ["EURUSD", "GBPUSD"])

    def test_the_provider_is_called_with_the_canonical_pair(self):
        rate = cache.get_cached_rate("eur/usd")
        self.assertEqual(rate["pair"], "EURUSD")

    def test_an_expired_entry_is_fetched_again(self):
        cache.get_cached_rate("EURUSD")
        # Reach into the fallback store and age the entry past its TTL —
        # the deterministic stand-in for waiting RATE_TTL_SECONDS.
        (key,) = list(cache._local_store)
        expires_at, value = cache._local_store[key]
        cache._local_store[key] = (expires_at - cache.RATE_TTL_SECONDS - 1, value)
        cache.get_cached_rate("EURUSD")
        self.assertEqual(self.provider.rate_calls, ["EURUSD", "EURUSD"])

    def test_a_malformed_pair_never_reaches_the_provider(self):
        with self.assertRaises(provider.InvalidPair):
            cache.get_cached_rate("not a pair")
        self.assertEqual(self.provider.rate_calls, [])


class TestHistoryCaching(RatesCacheCase):
    def test_repeated_reads_share_one_fetch_per_window(self):
        cache.get_cached_history("EURUSD", 30)
        cache.get_cached_history("EUR/USD", 30)
        self.assertEqual(self.provider.history_calls, [("EURUSD", 30)])

    def test_different_windows_are_different_entries(self):
        cache.get_cached_history("EURUSD", 30)
        cache.get_cached_history("EURUSD", 60)
        self.assertEqual(
            self.provider.history_calls, [("EURUSD", 30), ("EURUSD", 60)]
        )

    def test_a_stringly_typed_window_is_the_same_window(self):
        # Whitelisted endpoints receive form values as strings.
        cache.get_cached_history("EURUSD", "30")
        cache.get_cached_history("EURUSD", 30)
        self.assertEqual(self.provider.history_calls, [("EURUSD", 30)])

    def test_windows_outside_the_bounds_are_refused(self):
        for bad in (0, -5, cache.MAX_HISTORY_DAYS + 1, "abc", None):
            with self.assertRaises(provider.InvalidRequest):
                cache.get_cached_history("EURUSD", bad)
        self.assertEqual(self.provider.history_calls, [])

    def test_bad_windows_are_catchable_as_plain_value_errors(self):
        # The tenant proxy's handle on control-side validation failures.
        with self.assertRaises(ValueError):
            cache.get_cached_history("EURUSD", 0)


class TestFailureIsNotCached(RatesCacheCase):
    def test_a_provider_error_propagates_and_the_next_read_retries(self):
        boom = provider.RatesUnavailable("upstream down")
        with mock.patch.object(self.provider, "get_rate", side_effect=boom):
            with self.assertRaises(provider.RatesUnavailable):
                cache.get_cached_rate("EURUSD")
        # Nothing was stored for the failed read; the next call fetches.
        rate = cache.get_cached_rate("EURUSD")
        self.assertEqual(rate["pair"], "EURUSD")
        self.assertEqual(self.provider.rate_calls, ["EURUSD"])


if __name__ == "__main__":
    unittest.main()
