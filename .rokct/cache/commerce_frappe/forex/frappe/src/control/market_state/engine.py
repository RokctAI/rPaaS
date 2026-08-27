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

"""Per-pair market state, computed control-side ONCE and shared.

The weather module's grid-cell pattern, transplanted: one evaluation per
pair per TTL window, cached control-side, with every tenant reading the
same cached verdict through a thin proxy
(src/tenant/rforex/api/market_state.py). A thousand users asking about
EURUSD cost one computation, not a thousand.

``get_market_state(pair, ts=None)`` composes four independent reads:

  - the session verdict (sessions.py — pure, fixed UTC windows),
  - the volatility buckets (volatility.py — pure, fed by the rates
    layer's cached daily history),
  - the cached rate itself, verbatim, from the rates layer,
  - a staleness judgement on that rate's timestamp.

RATES ARE NOT FETCHED HERE. The rates layer (src/control/rates/cache.py)
owns fetching, caching and honesty about its sources; this module only
calls its two accessors and passes their exceptions through untouched —
a rates-layer refusal (unknown pair, no data) surfaces to the caller as
itself, not repackaged into a half-filled state dict.

DEGRADED READS ARE LABELLED, NEVER PAPERED OVER. No composed rates layer,
or an accessor returning nothing, yields ``rate: None`` and a staleness
block whose ``reason`` says which absence it was — while the session
verdict, which needs no market data, stays fully populated. Nothing here
invents a bid to keep the dict pretty.

CACHING: ``frappe.cache()`` (Redis, shared across workers and — on the
usual bench layout — readable by the tenant proxy) with a short TTL when
frappe is importable; a plain in-process dict with the same TTL when it
is not, which is exactly the unit-test environment. An EXPLICIT ``ts``
bypasses the cache entirely in both directions: a historical or
hypothetical instant is a question, not the shared present, and caching
it would poison the answer everyone else shares.
"""

import time
from datetime import datetime, timezone

from . import sessions, volatility

#: How long one computed state is shared before recomputation. Session
#: flags change on hour boundaries and the underlying rates are daily
#: reference data, so 60 seconds is already generous.
CACHE_TTL_SECONDS = 60

#: A cached rate older than this is flagged stale. 36 hours = the daily
#: ECB reference cadence (one fix per business day, published mid
#: afternoon CET) plus a half-day of slack. MECHANICAL BY DESIGN: over a
#: weekend Friday's fix ages past 36h and IS flagged stale, because it
#: genuinely is that old — read ``stale`` together with ``market_open``
#: rather than expecting the flag to excuse weekends.
RATE_STALE_AFTER_SECONDS = 36 * 3600

#: Days of daily history requested from the rates layer per evaluation:
#: a ~3-trading-week baseline plus the latest candle. See volatility.py
#: for how few of these are actually required before "unknown".
VOLATILITY_WINDOW_DAYS = 15

#: Test seam and composition override: set to a
#: ``(get_cached_rate, get_cached_history)`` pair to bypass discovery.
#: Unit tests set this; composed deployments leave it None.
RATES_ACCESSOR_OVERRIDE = None

#: Composed dotted path of the rates accessors, for the frappe.get_attr
#: fallback ({app_name} is substituted by the backend composer — same
#: convention as the weather read paths in the orders module).
_RATES_CACHE_PATH = "{app_name}.rforex.control.rates.cache.{func}"

_local_cache = {}  # pair -> (expires_at_monotonic, state) — test/no-frappe fallback


def _rates_accessors():
    """(get_cached_rate, get_cached_history), or (None, None) when this
    shell composes no rates layer.

    Tried in order: the test/override seam, the composed sibling package
    (src/control/rates/cache.py lands beside this one), then
    ``frappe.get_attr`` on the composed dotted path.
    """
    if RATES_ACCESSOR_OVERRIDE is not None:
        return RATES_ACCESSOR_OVERRIDE
    try:
        from ..rates.cache import get_cached_history, get_cached_rate

        return get_cached_rate, get_cached_history
    except Exception:
        pass
    try:
        import frappe

        rate = frappe.get_attr(_RATES_CACHE_PATH.format(func="get_cached_rate"))
        history = frappe.get_attr(_RATES_CACHE_PATH.format(func="get_cached_history"))
        if callable(rate) and callable(history):
            return rate, history
    except Exception:
        pass
    return None, None


def _parse_rate_ts(value):
    """The rate's timestamp as aware-UTC, or None when unparseable.

    Accepts a datetime (naive taken as UTC) or an ISO-8601 string
    (trailing 'Z' tolerated). Anything else is None — and the staleness
    block then says so rather than guessing an age.
    """
    if isinstance(value, datetime):
        return sessions.as_utc(value)
    if isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        try:
            return sessions.as_utc(datetime.fromisoformat(text))
        except ValueError:
            return None
    return None


def rate_staleness(rate, now):
    """Age and stale-flag for one cached rate dict.

    ``{"age_seconds", "threshold_seconds", "stale", "reason"}`` —
    ``reason`` is None on a normal read, else one of
    ``no_cached_rate`` / ``rates_layer_unavailable`` /
    ``unparseable_rate_ts``. An unknowable age is stale by definition:
    a rate that cannot prove its freshness does not get presumed fresh.
    """
    block = {
        "age_seconds": None,
        "threshold_seconds": RATE_STALE_AFTER_SECONDS,
        "stale": True,
        "reason": None,
    }
    if rate is None:
        block["reason"] = "no_cached_rate"
        return block
    parsed = _parse_rate_ts(rate.get("ts")) if isinstance(rate, dict) else None
    if parsed is None:
        block["reason"] = "unparseable_rate_ts"
        return block
    age = (sessions.as_utc(now) - parsed).total_seconds()
    block["age_seconds"] = age
    block["stale"] = age > RATE_STALE_AFTER_SECONDS
    return block


def compute_market_state(pair, ts=None):
    """One uncached evaluation. ``get_market_state`` is the cached door;
    this is the arithmetic behind it."""
    now = sessions.as_utc(ts if ts is not None else datetime.now(timezone.utc))
    session_view = sessions.session_state(now)

    get_rate, get_history = _rates_accessors()

    rate = None
    history = None
    staleness = None
    if get_rate is None:
        staleness = dict(
            age_seconds=None,
            threshold_seconds=RATE_STALE_AFTER_SECONDS,
            stale=True,
            reason="rates_layer_unavailable",
        )
    else:
        # Accessor exceptions propagate deliberately — see module docstring.
        rate = get_rate(pair)
        history = get_history(pair, VOLATILITY_WINDOW_DAYS)
        staleness = rate_staleness(rate, now)

    return {
        "pair": pair,
        "ts": session_view["ts"],
        "market_open": session_view["market_open"],
        "sessions": {
            "active": session_view["active"],
            "overlaps": session_view["overlaps"],
        },
        "volatility": volatility.evaluate(history),
        "rate": rate,
        "rate_staleness": staleness,
        "computed_at": now.isoformat(),
    }


def _cache_key(pair):
    return "rforex:market_state:{0}".format(pair)


def _cache_read(pair):
    try:
        import frappe

        return frappe.cache().get_value(_cache_key(pair))
    except Exception:
        entry = _local_cache.get(pair)
        if entry is None:
            return None
        expires_at, state = entry
        if time.monotonic() >= expires_at:
            _local_cache.pop(pair, None)
            return None
        return state


def _cache_write(pair, state):
    try:
        import frappe

        frappe.cache().set_value(
            _cache_key(pair), state, expires_in_sec=CACHE_TTL_SECONDS
        )
    except Exception:
        _local_cache[pair] = (time.monotonic() + CACHE_TTL_SECONDS, state)


def clear_cache(pair=None):
    """Drop cached state for one pair, or all pairs. Test hygiene mostly;
    harmless anywhere."""
    if pair is None:
        _local_cache.clear()
    else:
        _local_cache.pop(_normalise_pair(pair), None)
    try:
        import frappe

        if pair is None:
            frappe.cache().delete_keys("rforex:market_state:")
        else:
            frappe.cache().delete_value(_cache_key(_normalise_pair(pair)))
    except Exception:
        pass


def _normalise_pair(pair):
    text = (pair or "").strip().upper()
    if not text:
        raise ValueError("market state needs a currency pair")
    return text


def get_market_state(pair, ts=None):
    """The market state for one pair — cached, shared, short-lived.

    ``ts`` accepts a datetime or an ISO-8601 string; naive values are
    taken as UTC. Omitted ``ts`` means "the shared present": the answer
    is served from cache within ``CACHE_TTL_SECONDS`` and every caller
    in the window gets the identical dict. An explicit ``ts`` bypasses
    the cache both ways (see module docstring).

    Returned shape::

        {
            "pair": "EURUSD",
            "ts": "...",                # ISO-8601 UTC instant judged
            "market_open": bool,
            "sessions": {"active": [...], "overlaps": {...}},
            "volatility": {...},        # volatility.evaluate shape
            "rate": {...} | None,       # rates-layer dict, verbatim
            "rate_staleness": {"age_seconds", "threshold_seconds",
                               "stale", "reason"},
            "computed_at": "...",       # ISO-8601 UTC of the evaluation
        }
    """
    pair = _normalise_pair(pair)

    if ts is not None:
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.strip().replace("Z", "+00:00"))
        return compute_market_state(pair, ts)

    cached = _cache_read(pair)
    if cached is not None:
        return cached

    state = compute_market_state(pair)
    _cache_write(pair, state)
    return state
