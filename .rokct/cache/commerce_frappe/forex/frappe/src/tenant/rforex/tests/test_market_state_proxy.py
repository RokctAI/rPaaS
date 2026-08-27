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

"""The tenant market-state proxy, pinned standalone (no real frappe, no
site — `python -m unittest`, frappe stubbed just enough to import the
module).

The boundaries held here: the proxy is THIN (the engine's dict comes
back verbatim, the pair goes in normalised), it resolves the engine
through the composed dotted path, and a shell without the engine gets a
refusal — never an empty-but-200 response that would read as market
data.

Plus a wiring pin the manifest test cannot see: the proxy's candidate
path must actually land on src/control/market_state/engine.py's
``get_market_state`` — checked with ``ast`` against the file on disk, so
a control-side rename breaks loudly here instead of 404ing on a live
site.
"""

import ast
import importlib.util
import os
import sys
import types
import unittest

_HERE = os.path.dirname(__file__)
_PROXY_PATH = os.path.abspath(os.path.join(_HERE, "..", "api", "market_state.py"))
_CONTROL_DIR = os.path.abspath(
    os.path.join(_HERE, "..", "..", "..", "control", "market_state")
)


class _Thrown(Exception):
    """What the stub's frappe.throw raises."""


def _make_fake_frappe(attrs):
    """A frappe stub wide enough for the proxy module: whitelist, _,
    throw, and a get_attr backed by a plain dict of dotted paths."""
    fake = types.ModuleType("frappe")

    def whitelist(*args, **kwargs):
        def decorate(func):
            return func

        return decorate

    def get_attr(path):
        if path not in attrs:
            raise AttributeError(path)
        return attrs[path]

    def throw(message):
        raise _Thrown(message)

    fake.whitelist = whitelist
    fake.get_attr = get_attr
    fake.throw = throw
    fake._ = lambda text: text
    return fake


def _load_proxy(attrs):
    """Import the proxy module against a frappe stub, then remove the
    stub from sys.modules so no other test file can inherit it."""
    fake = _make_fake_frappe(attrs)
    previous = sys.modules.get("frappe")
    sys.modules["frappe"] = fake
    try:
        spec = importlib.util.spec_from_file_location(
            "rforex_ms_proxy_under_test", _PROXY_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            sys.modules.pop("frappe", None)
        else:
            sys.modules["frappe"] = previous


ENGINE_PATH = "{app_name}.rforex.control.market_state.engine.get_market_state"


class TestProxyIsThin(unittest.TestCase):
    def test_the_engines_dict_comes_back_verbatim(self):
        sentinel = {"pair": "EURUSD", "market_open": True, "anything": ["else"]}
        calls = []

        def engine(pair):
            calls.append(pair)
            return sentinel

        proxy = _load_proxy({ENGINE_PATH: engine})
        self.assertIs(proxy.get_market_state("EURUSD"), sentinel)
        self.assertEqual(calls, ["EURUSD"])

    def test_the_pair_is_normalised_on_the_way_in(self):
        calls = []
        proxy = _load_proxy({ENGINE_PATH: lambda pair: calls.append(pair) or {}})
        proxy.get_market_state("  gbpusd ")
        self.assertEqual(calls, ["GBPUSD"])

    def test_a_blank_pair_is_refused_before_the_engine_is_touched(self):
        calls = []
        proxy = _load_proxy({ENGINE_PATH: lambda pair: calls.append(pair) or {}})
        with self.assertRaises(_Thrown):
            proxy.get_market_state("   ")
        with self.assertRaises(_Thrown):
            proxy.get_market_state(None)
        self.assertEqual(calls, [])


class TestMissingEngineRefusesLoudly(unittest.TestCase):
    def test_no_resolvable_engine_throws_rather_than_degrading(self):
        proxy = _load_proxy({})
        with self.assertRaises(_Thrown):
            proxy.get_market_state("EURUSD")

    def test_a_non_callable_resolution_counts_as_missing(self):
        proxy = _load_proxy({ENGINE_PATH: "not-callable"})
        with self.assertRaises(_Thrown):
            proxy.get_market_state("EURUSD")


class TestCandidatePathMatchesTheControlLayout(unittest.TestCase):
    # src/control/market_state/engine.py lands at
    # {app_name}/rforex/control/market_state/engine.py when composed, so
    # each candidate's tail must name a real module and function there.
    _PREFIX = "{app_name}.rforex.control.market_state."

    def _functions(self, module_name):
        path = os.path.join(_CONTROL_DIR, module_name + ".py")
        self.assertTrue(os.path.isfile(path), path)
        with open(path) as handle:
            tree = ast.parse(handle.read())
        return {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def test_every_candidate_resolves_to_a_real_control_function(self):
        proxy = _load_proxy({ENGINE_PATH: lambda pair: {}})
        for candidate in proxy.ENGINE_CANDIDATES:
            self.assertTrue(candidate.startswith(self._PREFIX), candidate)
            module_name, _, func_name = candidate[len(self._PREFIX):].rpartition(".")
            self.assertIn(func_name, self._functions(module_name), candidate)


if __name__ == "__main__":
    unittest.main()
