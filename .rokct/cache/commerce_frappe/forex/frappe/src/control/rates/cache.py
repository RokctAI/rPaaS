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

"""Per-pair rate caching: one upstream fetch shared by every consumer.

The same one-evaluation-shared-by-everyone pattern as the weather
module's grid cells: a pair is the unit of caching (canonicalized first,
so ``"EUR/USD"`` and ``"eurusd"`` share one entry), and whoever asks
within the TTL — tenant proxy, market-state engine, anything else —
reads the one stored answer instead of re-fetching.

**These two accessors are the layer's public surface.** Downstream code
(the tenant proxy here, the market-state engine, the outcome ledger)
imports these, never a provider:

- ``get_cached_rate(pair)`` → the [provider.RATE_KEYS]-shaped dict
- ``get_cached_history(pair, days)`` → list of
  [provider.HISTORY_KEYS]-shaped daily rows

Storage: ``frappe.cache()`` (Redis, shared across workers, real TTLs)
when a composed site provides it; a per-process dict with the same TTL
semantics otherwise, which is what the frappe-free unit tests exercise.
Failures are not cached and no stale value is served past its TTL — a
provider error surfaces to the caller (see the no-fabrication rule in
api/account.py) rather than being masked by yesterday's number.
"""

import time

from . import provider as _provider

#: Reference rates change at most once per business day upstream (see
#: frankfurter.py), so these TTLs bound staleness for FUTURE intraday
#: providers while keeping the default source to a handful of upstream
#: calls per day per pair.
RATE_TTL_SECONDS = 900
HISTORY_TTL_SECONDS = 3600

MAX_HISTORY_DAYS = 3650

_KEY_PREFIX = "rforex:rates:"  # compliance-ignore: py-hardcoded-secret (Redis cache-key prefix, not a credential)

# key -> (expires_at_epoch, value); the no-frappe fallback store.
_local_store = {}


def _frappe_cache():
    try:
        import frappe

        return frappe.cache()
    except Exception:
        return None


def _cache_get(key):
    cache = _frappe_cache()
    if cache is not None:
        try:
            return cache.get_value(key)
        except Exception:
            pass
    entry = _local_store.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if expires_at <= time.time():
        _local_store.pop(key, None)
        return None
    return value


def _cache_set(key, value, ttl_seconds):
    cache = _frappe_cache()
    if cache is not None:
        try:
            cache.set_value(key, value, expires_in_sec=ttl_seconds)
            return
        except Exception:
            pass
    _local_store[key] = (time.time() + ttl_seconds, value)


def clear_local_cache():
    """Drop the in-process fallback store (tests; harmless elsewhere)."""
    _local_store.clear()


def get_cached_rate(pair):
    """The latest rate for [pair], fetched at most once per
    [RATE_TTL_SECONDS] across all consumers.

    Returns the provider's rate dict — exactly the keys
    ``{"pair", "bid", "ask", "mid", "ts", "source"}``. Raises
    [provider.InvalidPair] (a ValueError) on a malformed pair and lets
    provider failures propagate."""
    canonical = _provider.normalize_pair(pair)
    key = "{0}rate:{1}".format(_KEY_PREFIX, canonical)
    hit = _cache_get(key)
    if hit is not None:
        return hit
    rate = _provider.get_rates_provider().get_rate(canonical)
    _cache_set(key, rate, RATE_TTL_SECONDS)
    return rate


def get_cached_history(pair, days):
    """Daily history rows for [pair] over the last [days] days, fetched
    at most once per [HISTORY_TTL_SECONDS] per (pair, days) window.

    Returns the provider's list of ``{"date", "open", "high", "low",
    "close"}`` rows, ascending; possibly fewer rows than days (business
    days only upstream). Raises [provider.InvalidRequest] (a ValueError)
    on a malformed pair or a window outside 1..[MAX_HISTORY_DAYS]."""
    canonical = _provider.normalize_pair(pair)
    try:
        window = int(days)
    except (TypeError, ValueError):
        raise _provider.InvalidRequest(
            "days must be a whole number, got {0!r}.".format(days)
        )
    if not 1 <= window <= MAX_HISTORY_DAYS:
        raise _provider.InvalidRequest(
            "days must be between 1 and {0}, got {1}.".format(MAX_HISTORY_DAYS, window)
        )
    key = "{0}history:{1}:{2}".format(_KEY_PREFIX, canonical, window)
    hit = _cache_get(key)
    if hit is not None:
        return hit
    history = _provider.get_rates_provider().get_history(canonical, window)
    _cache_set(key, history, HISTORY_TTL_SECONDS)
    return history
