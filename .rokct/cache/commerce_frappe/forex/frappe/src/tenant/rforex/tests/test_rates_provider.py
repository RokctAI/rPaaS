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

"""The rates-provider seam, pinned standalone (no frappe, no site, no
network — `python -m unittest`).

The boundaries these tests hold: **the rate and history dict shapes are
exact**, **the default source reports no spread it does not have**,
**pair validation refuses everything that is not a currency pair**, and
**the factory serves exactly what config names — or refuses loudly.**

Every HTTP call is a injected fake; nothing here touches the network.
"""

import importlib
import importlib.util
import os
import sys
import types
import unittest
from datetime import date

_HERE = os.path.dirname(os.path.abspath(__file__))
_RATES_DIR = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "control", "rates"))
_PKG = "rforex_control_rates"


def _load_rates_package():
    """Load src/control/rates as a real package (relative imports intact)
    under a collision-proof name — the by-file-path counterpart of how the
    other tests here load their pure modules."""
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
frankfurter = importlib.import_module(_PKG + ".frankfurter")


LATEST_PAYLOAD = {
    "amount": 1.0,
    "base": "EUR",
    "date": "2026-08-21",
    "rates": {"USD": 1.1734},
}

HISTORY_PAYLOAD = {
    "amount": 1.0,
    "base": "EUR",
    "start_date": "2026-08-17",
    "end_date": "2026-08-21",
    "rates": {
        # deliberately unsorted: the provider must sort ascending
        "2026-08-19": {"USD": 1.17},
        "2026-08-17": {"USD": 1.15},
        "2026-08-18": {"USD": 1.16},
    },
}


def _fake_fetch(payload, seen_urls):
    def fetch(url):
        seen_urls.append(url)
        return payload

    return fetch


class TestPairValidation(unittest.TestCase):
    def test_both_accepted_spellings_normalize_to_the_six_letter_form(self):
        self.assertEqual(provider.normalize_pair("EURUSD"), "EURUSD")
        self.assertEqual(provider.normalize_pair("EUR/USD"), "EURUSD")
        self.assertEqual(provider.normalize_pair(" eur/usd "), "EURUSD")
        self.assertEqual(provider.normalize_pair("gbpjpy"), "GBPJPY")

    def test_split_pair(self):
        self.assertEqual(provider.split_pair("eur/usd"), ("EUR", "USD"))

    def test_garbage_is_refused(self):
        for bad in ("EURUS", "EUR-USD", "EUR/USD/JPY", "EU/RUSD", "E1RUSD", "", "   "):
            with self.assertRaises(provider.InvalidPair):
                provider.normalize_pair(bad)

    def test_non_strings_are_refused(self):
        for bad in (None, 6, 1.5, ["EUR", "USD"], {"pair": "EURUSD"}):
            with self.assertRaises(provider.InvalidPair):
                provider.normalize_pair(bad)

    def test_the_same_currency_twice_is_not_a_pair(self):
        with self.assertRaises(provider.InvalidPair):
            provider.normalize_pair("EUR/EUR")

    def test_invalid_pair_is_catchable_as_a_plain_value_error(self):
        # The tenant proxy cannot import InvalidPair across the composed
        # control/tenant boundary; ValueError is its handle on it.
        with self.assertRaises(ValueError):
            provider.normalize_pair("nonsense")


class TestFrankfurterGetRate(unittest.TestCase):
    def _rate(self, payload=LATEST_PAYLOAD, pair="EUR/USD"):
        urls = []
        source = frankfurter.FrankfurterProvider(fetch_json=_fake_fetch(payload, urls))
        return source.get_rate(pair), urls

    def test_the_rate_dict_carries_exactly_the_contract_keys(self):
        rate, _urls = self._rate()
        self.assertEqual(set(rate), set(provider.RATE_KEYS))

    def test_a_reference_rate_has_no_spread(self):
        rate, _urls = self._rate()
        self.assertEqual(rate["bid"], rate["mid"])
        self.assertEqual(rate["ask"], rate["mid"])
        self.assertEqual(rate["mid"], 1.1734)

    def test_pair_ts_and_source_are_canonical(self):
        rate, _urls = self._rate(pair="eur/usd")
        self.assertEqual(rate["pair"], "EURUSD")
        self.assertEqual(rate["ts"], "2026-08-21T00:00:00+00:00")
        self.assertEqual(rate["source"], "frankfurter")

    def test_the_request_names_base_and_quote(self):
        _rate, urls = self._rate()
        self.assertEqual(len(urls), 1)
        self.assertTrue(urls[0].startswith(frankfurter.API_BASE + "/latest?"), urls[0])
        self.assertIn("base=EUR", urls[0])
        self.assertIn("symbols=USD", urls[0])

    def test_a_pair_the_source_does_not_publish_is_unavailable_not_zero(self):
        with self.assertRaises(provider.RatesUnavailable):
            self._rate(payload={"date": "2026-08-21", "rates": {}})

    def test_a_shapeless_payload_is_unavailable(self):
        for payload in (None, [], "rates", {"rates": {"USD": True}}):
            with self.assertRaises(provider.RatesUnavailable):
                self._rate(payload=payload)

    def test_a_payload_without_a_date_is_unavailable(self):
        with self.assertRaises(provider.RatesUnavailable):
            self._rate(payload={"rates": {"USD": 1.17}})


class TestFrankfurterHistory(unittest.TestCase):
    def _history(self, payload=HISTORY_PAYLOAD, days=5):
        urls = []
        source = frankfurter.FrankfurterProvider(
            fetch_json=_fake_fetch(payload, urls),
            today=lambda: date(2026, 8, 22),
        )
        return source.get_history("EURUSD", days), urls

    def test_rows_carry_exactly_the_contract_keys_ascending(self):
        rows, _urls = self._history()
        self.assertEqual([r["date"] for r in rows], ["2026-08-17", "2026-08-18", "2026-08-19"])
        for row in rows:
            self.assertEqual(set(row), set(provider.HISTORY_KEYS))

    def test_one_reference_rate_per_day_makes_a_flat_candle(self):
        rows, _urls = self._history()
        for row in rows:
            self.assertEqual(row["open"], row["close"])
            self.assertEqual(row["high"], row["close"])
            self.assertEqual(row["low"], row["close"])
        self.assertEqual(rows[0]["close"], 1.15)

    def test_the_window_is_days_back_from_today(self):
        _rows, urls = self._history(days=5)
        self.assertIn("/2026-08-17..2026-08-22?", urls[0])

    def test_a_malformed_day_is_unavailable_not_skipped(self):
        payload = {"rates": {"2026-08-18": {"USD": "not-a-number"}}}
        with self.assertRaises(provider.RatesUnavailable):
            self._history(payload=payload)

    def test_a_shapeless_payload_is_unavailable(self):
        with self.assertRaises(provider.RatesUnavailable):
            self._history(payload={"nope": 1})


class _StubProvider(provider.RatesProvider):
    source = "stub"

    def get_rate(self, pair):
        return {
            "pair": pair,
            "bid": 1.0,
            "ask": 1.0,
            "mid": 1.0,
            "ts": "2026-08-22T00:00:00+00:00",
            "source": self.source,
        }

    def get_history(self, pair, days):
        return []


class TestFactory(unittest.TestCase):
    def test_the_default_is_frankfurter(self):
        source = provider.get_rates_provider()
        self.assertIsInstance(source, provider.RatesProvider)
        self.assertEqual(source.source, "frankfurter")

    def test_the_name_override_is_case_insensitive(self):
        self.assertEqual(provider.get_rates_provider("FRANKFURTER").source, "frankfurter")

    def test_an_unknown_provider_is_refused_not_defaulted(self):
        with self.assertRaises(provider.RatesError):
            provider.get_rates_provider("no_such_source")

    def test_a_registered_provider_is_selectable_by_name(self):
        provider.register_provider("stub_by_name", _StubProvider)
        self.addCleanup(provider._REGISTRY.pop, "stub_by_name", None)
        self.assertEqual(provider.get_rates_provider("stub_by_name").source, "stub")

    def test_site_config_switches_the_provider(self):
        # The swappable seam itself: a fake frappe whose conf names the
        # stub, and the zero-argument factory serves the stub.
        provider.register_provider("stub_conf", _StubProvider)
        self.addCleanup(provider._REGISTRY.pop, "stub_conf", None)

        fake = types.ModuleType("frappe")
        fake.conf = {provider.CONF_PROVIDER_KEY: "stub_conf"}
        had = sys.modules.get("frappe")
        sys.modules["frappe"] = fake
        self.addCleanup(
            lambda: sys.modules.pop("frappe", None)
            if had is None
            else sys.modules.__setitem__("frappe", had)
        )

        self.assertEqual(provider.get_rates_provider().source, "stub")

    def test_absent_config_means_the_default(self):
        fake = types.ModuleType("frappe")
        fake.conf = {}
        had = sys.modules.get("frappe")
        sys.modules["frappe"] = fake
        self.addCleanup(
            lambda: sys.modules.pop("frappe", None)
            if had is None
            else sys.modules.__setitem__("frappe", had)
        )
        self.assertEqual(provider.get_rates_provider().source, "frankfurter")


if __name__ == "__main__":
    unittest.main()
