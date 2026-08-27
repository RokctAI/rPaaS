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

"""The rates-provider seam: one abstract interface, a registry, and a
config-driven factory.

**This layer serves REFERENCE rates, not tradeable prices.** Every number
that crosses this seam is for display and analysis — a chart, a converted
figure, a market-state evaluation. It is never a price anyone can deal on:
live bid/ask for order sizing arrives later through the broker connector
(api/account.py's `_broker_snapshot` seam), not through here. Providers
that have no spread (the default ECB reference source) report
``bid == ask == mid`` rather than inventing one.

The seam itself is the same philosophy as the weather module's data
source: consumers depend on the dict shapes below and on `cache.py`'s
accessors, never on a concrete provider, so swapping the source is a
config edit (site config key ``forex_rates_provider``) plus a provider
module — no consumer changes.

Dict shapes (the contract downstream code may rely on):

- ``get_rate(pair)`` returns exactly the keys in [RATE_KEYS]:
  ``{"pair", "bid", "ask", "mid", "ts", "source"}`` — ``pair`` in the
  canonical 6-letter form, ``bid``/``ask``/``mid`` floats, ``ts`` an
  ISO-8601 UTC timestamp, ``source`` a short provider string.
- ``get_history(pair, days)`` returns a list of daily rows, each exactly
  the keys in [HISTORY_KEYS]: ``{"date", "open", "high", "low", "close"}``
  — ``date`` as ``YYYY-MM-DD``, ascending, floats elsewhere. Sources
  without intraday data report ``open == high == low == close``.

Pair convention: the strategy catalog does not pin a symbol list
(`Forex Strategy Version` specs carry a free-form ``symbol``), so
validation here is structural ISO-4217: two three-letter alphabetic
codes, written ``"EURUSD"`` or ``"EUR/USD"``. The canonical form is the
6-letter one — the cTrader symbol style the strategy specs inherit from
the bots in RokctAI/forex.
"""

import re
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Tuple

#: site-config key naming the provider; absent means [DEFAULT_PROVIDER].
CONF_PROVIDER_KEY = "forex_rates_provider"  # compliance-ignore: py-hardcoded-secret (site-config key NAME, not a credential)

DEFAULT_PROVIDER = "frankfurter"

#: exact key set of every dict `get_rate` returns.
RATE_KEYS = ("pair", "bid", "ask", "mid", "ts", "source")

#: exact key set of every row `get_history` returns.
HISTORY_KEYS = ("date", "open", "high", "low", "close")


class RatesError(Exception):
    """Base for everything this layer raises on purpose."""


class InvalidRequest(RatesError, ValueError):
    """The caller asked for something malformed (bad pair, bad window).

    Subclasses ValueError so the tenant proxy — which cannot import this
    class across the control/tenant composition boundary — can still
    catch it as a plain ValueError and answer with a validation error
    instead of a server fault.
    """


class InvalidPair(InvalidRequest):
    """The pair string is not a currency pair."""


class RatesUnavailable(RatesError):
    """The provider could not produce a real answer (network, upstream
    error, malformed payload). Deliberately NOT a ValueError: this is the
    provider's failure, not the caller's, and per the module rule nothing
    papers over it with a fabricated number."""


_PAIR_RE = re.compile(r"^[A-Z]{3}/?[A-Z]{3}$")


def normalize_pair(pair) -> str:
    """``"eur/usd"`` → ``"EURUSD"``. Raises [InvalidPair] on anything that
    is not two ISO-4217-shaped codes, including a pair of the same code —
    one canonical form so every cache consumer shares one entry."""
    if not isinstance(pair, str):
        raise InvalidPair("A currency pair must be a string, e.g. 'EURUSD'.")
    candidate = pair.strip().upper()
    if not _PAIR_RE.match(candidate):
        raise InvalidPair(
            "Not a currency pair: {0!r}. Use 'EURUSD' or 'EUR/USD'.".format(pair)
        )
    base, quote = candidate[:3], candidate[-3:]
    if base == quote:
        raise InvalidPair("A pair needs two different currencies; got {0!r}.".format(pair))
    return base + quote


def split_pair(pair) -> Tuple[str, str]:
    """``("EUR", "USD")`` for any accepted spelling of the pair."""
    canonical = normalize_pair(pair)
    return canonical[:3], canonical[3:]


class RatesProvider(ABC):
    """One rates source. Implementations own their transport and parsing;
    the shapes they return are the contract documented in the module
    docstring, and honesty about what the source actually is (reference vs
    tradeable, daily vs intraday) belongs in the implementation's own
    docstring."""

    #: short string every returned rate carries in its "source" field.
    source = "abstract"

    @abstractmethod
    def get_rate(self, pair: str) -> Dict:
        """The latest rate for [pair] as a [RATE_KEYS]-shaped dict."""

    @abstractmethod
    def get_history(self, pair: str, days: int) -> List[Dict]:
        """Daily [HISTORY_KEYS]-shaped rows covering the last [days] days,
        ascending by date. May return fewer rows than days — sources that
        publish business days only will."""


# name -> zero-arg callable returning a RatesProvider.
_REGISTRY: Dict[str, Callable[[], "RatesProvider"]] = {}


def register_provider(name: str, factory: Callable[[], "RatesProvider"]) -> None:
    """Make a provider selectable by config. Adding a source is: write the
    module, call this at its import, name it in site config."""
    _REGISTRY[str(name).strip().lower()] = factory


def registered_providers() -> Tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def _configured_provider_name() -> str:
    """The site-config choice, or the default. Import of frappe is lazy
    and guarded so this module stays importable (and testable) with no
    frappe installed; unreadable config falls back to the default rather
    than failing a rate read over a settings problem."""
    try:
        import frappe

        value = frappe.conf.get(CONF_PROVIDER_KEY)
        if value:
            return str(value)
    except Exception:
        pass
    return DEFAULT_PROVIDER


def get_rates_provider(name: Optional[str] = None) -> "RatesProvider":
    """The configured provider, constructed. [name] overrides config
    (tests, one-off tooling); unknown names raise rather than silently
    serving the default — a site that names a provider it does not have
    should hear about it, not chart different numbers than it asked for.
    """
    resolved = str(name or _configured_provider_name()).strip().lower()
    if resolved == DEFAULT_PROVIDER and resolved not in _REGISTRY:
        # The default registers itself on import; import it on demand so
        # a bare `import provider` needs no transport code loaded.
        from . import frankfurter  # noqa: F401

    factory = _REGISTRY.get(resolved)
    if factory is None:
        raise RatesError(
            "Unknown forex rates provider {0!r}; registered: {1}.".format(
                resolved, ", ".join(registered_providers()) or "(none)"
            )
        )
    return factory()
