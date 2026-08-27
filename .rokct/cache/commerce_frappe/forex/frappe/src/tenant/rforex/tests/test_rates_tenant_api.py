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

"""The tenant rates proxy, pinned standalone (no frappe, no site —
`python -m unittest`).

api/rates.py imports frappe at module level like every other api module,
so unlike the pure-module tests this one loads it under a STUB frappe —
just whitelist/throw/get_attr/_ — which is exactly the surface the proxy
is allowed to need. The boundaries held: **the proxy is a passthrough**
(the cache's dicts cross it unchanged), **it addresses the control layer
by its composed dotted path**, **a control-side ValueError becomes a
validation error**, and **an uncomposed rates layer raises instead of
returning something that looks like a quiet market.**
"""

import importlib.util
import os
import sys
import types
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_API_PATH = os.path.abspath(os.path.join(_HERE, "..", "api", "rates.py"))


class _Thrown(Exception):
    """What the stub frappe.throw raises; carries the frappe exc class."""

    def __init__(self, message, exc_class):
        super().__init__(message)
        self.exc_class = exc_class


def _make_stub_frappe():
    stub = types.ModuleType("frappe")
    stub.ValidationError = type("ValidationError", (Exception,), {})
    stub.DoesNotExistError = type("DoesNotExistError", (Exception,), {})
    stub._ = lambda text: text
    stub._attrs = {}
    stub._get_attr_calls = []
    stub._whitelisted = []

    def whitelist(*args, **kwargs):
        def decorator(fn):
            stub._whitelisted.append(fn.__name__)
            return fn

        return decorator

    def get_attr(path):
        stub._get_attr_calls.append(path)
        if path not in stub._attrs:
            raise AttributeError(path)
        return stub._attrs[path]

    def throw(message, exc=Exception):
        raise _Thrown(message, exc)

    stub.whitelist = whitelist
    stub.get_attr = get_attr
    stub.throw = throw
    return stub


def _load_api_under(stub):
    had = sys.modules.get("frappe")
    sys.modules["frappe"] = stub
    try:
        spec = importlib.util.spec_from_file_location(
            "rforex_api_rates_under_test", _API_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        # The loaded module keeps its own reference to the stub; nothing
        # else in this suite imports frappe.
        if had is None:
            sys.modules.pop("frappe", None)
        else:
            sys.modules["frappe"] = had


RATE = {
    "pair": "EURUSD",
    "bid": 1.1734,
    "ask": 1.1734,
    "mid": 1.1734,
    "ts": "2026-08-21T00:00:00+00:00",
    "source": "frankfurter",
}

HISTORY = [
    {"date": "2026-08-21", "open": 1.17, "high": 1.17, "low": 1.17, "close": 1.17}
]


class TenantProxyCase(unittest.TestCase):
    def setUp(self):
        self.frappe = _make_stub_frappe()
        self.rate_calls = []
        self.history_calls = []

        def cached_rate(pair):
            self.rate_calls.append(pair)
            return RATE

        def cached_history(pair, days):
            self.history_calls.append((pair, days))
            return HISTORY

        self.frappe._attrs = {
            "{app_name}.rforex.control.rates.cache.get_cached_rate": cached_rate,
            "{app_name}.rforex.control.rates.cache.get_cached_history": cached_history,
        }
        self.api = _load_api_under(self.frappe)


class TestWiring(TenantProxyCase):
    def test_both_endpoints_are_whitelisted(self):
        self.assertEqual(
            sorted(self.frappe._whitelisted),
            ["get_forex_history", "get_forex_rate"],
        )

    def test_the_proxy_addresses_the_composed_control_path(self):
        self.api.get_forex_rate("EURUSD")
        self.assertEqual(
            self.frappe._get_attr_calls,
            ["{app_name}.rforex.control.rates.cache.get_cached_rate"],
        )


class TestPassthrough(TenantProxyCase):
    def test_the_rate_dict_crosses_unchanged(self):
        response = self.api.get_forex_rate("EUR/USD")
        self.assertIs(response, RATE)
        self.assertEqual(set(response), {"pair", "bid", "ask", "mid", "ts", "source"})
        self.assertEqual(self.rate_calls, ["EUR/USD"])

    def test_history_rows_cross_unchanged(self):
        response = self.api.get_forex_history("EURUSD", 90)
        self.assertIs(response, HISTORY)
        self.assertEqual(set(response[0]), {"date", "open", "high", "low", "close"})
        self.assertEqual(self.history_calls, [("EURUSD", 90)])

    def test_the_default_history_window(self):
        self.api.get_forex_history("EURUSD")
        self.api.get_forex_history("EURUSD", "")
        self.assertEqual(
            self.history_calls,
            [("EURUSD", self.api.DEFAULT_HISTORY_DAYS), ("EURUSD", self.api.DEFAULT_HISTORY_DAYS)],
        )


class TestErrorTranslation(TenantProxyCase):
    def test_a_control_side_value_error_becomes_a_validation_error(self):
        def refusing(pair):
            raise ValueError("Not a currency pair: 'nope'.")

        self.frappe._attrs[
            "{app_name}.rforex.control.rates.cache.get_cached_rate"
        ] = refusing
        with self.assertRaises(_Thrown) as caught:
            self.api.get_forex_rate("nope")
        self.assertIs(caught.exception.exc_class, self.frappe.ValidationError)

    def test_a_provider_failure_is_not_swallowed(self):
        # Not a ValueError: an upstream outage must surface as the error
        # it is, never as a validation complaint or an empty answer.
        class Unavailable(Exception):
            pass

        def failing(pair):
            raise Unavailable("upstream down")

        self.frappe._attrs[
            "{app_name}.rforex.control.rates.cache.get_cached_rate"
        ] = failing
        with self.assertRaises(Unavailable):
            self.api.get_forex_rate("EURUSD")


class TestUncomposedShell(TenantProxyCase):
    def test_a_missing_rates_layer_raises_instead_of_faking_quiet(self):
        self.frappe._attrs = {}
        with self.assertRaises(_Thrown) as caught:
            self.api.get_forex_rate("EURUSD")
        self.assertIs(caught.exception.exc_class, self.frappe.DoesNotExistError)

    def test_history_is_gated_the_same_way(self):
        self.frappe._attrs = {}
        with self.assertRaises(_Thrown):
            self.api.get_forex_history("EURUSD", 30)


if __name__ == "__main__":
    unittest.main()
