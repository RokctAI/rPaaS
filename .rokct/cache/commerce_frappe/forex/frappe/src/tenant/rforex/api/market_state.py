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

"""Tenant proxy for the control-side market-state engine.

Deliberately THIN: normalise the pair, resolve the engine, return its
dict verbatim. All judgement — session windows, volatility buckets,
staleness — lives control-side in src/control/market_state/, computed
once per pair per TTL window and shared by every tenant that asks (the
weather module's grid-cell serving pattern). Adding tenant-side logic
here would fork the verdict per tenant, which is the one thing the
pattern exists to prevent.

The engine is resolved by ``frappe.get_attr`` over its composed dotted
path ({app_name} substituted by the backend composer — same guarded
dynamic dispatch as the orders module's weather_notice read paths),
because tenant shells may or may not compose the control persona's code.

When no engine resolves this THROWS rather than degrading. The weather
proxy fails silent because its payload is an optional annotation; market
state is the payload — an empty-but-200 response here would read as "no
sessions active, no volatility", which is fabricated market data, and
this SDK does not fabricate market data anywhere.

No ``ts`` parameter is exposed. Tenants ask about the shared present —
that is what makes the cache one-evaluation-for-everyone. Historical
what-ifs are a control-side/analyst question (engine.get_market_state
accepts ts directly there).
"""

import frappe
from frappe import _

#: Composed dotted paths of the control engine, in preference order.
ENGINE_CANDIDATES = (
    "{app_name}.rforex.control.market_state.engine.get_market_state",
)


def _resolve_engine():
    """The first resolvable engine callable, or None on a shell that
    composes no control-side market_state package."""
    for path in ENGINE_CANDIDATES:
        try:
            target = frappe.get_attr(path)
            if callable(target):
                return target
        except Exception:
            continue
    return None


@frappe.whitelist()
def get_market_state(pair):
    """The cached market state for one pair — see
    src/control/market_state/MARKET_STATE.md for every field.

    Descriptive, not predictive: sessions are fixed-UTC approximations,
    volatility buckets describe the recent past, and the staleness flag
    is mechanical. The doc says so at length; clients should too.
    """
    pair = (pair or "").strip().upper()
    if not pair:
        frappe.throw(_("A currency pair is required, e.g. EURUSD."))

    engine = _resolve_engine()
    if engine is None:
        frappe.throw(
            _(
                "Market state is unavailable: this deployment composes no "
                "market-state engine."
            )
        )

    return engine(pair)
