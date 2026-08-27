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

# compliance-ignore-file: obs-python-trace
# The only outgoing calls here go to the third-party public frankfurter.app
# API (keyless ECB reference rates). Internal x-trace-id / x-request-id
# correlation ids are deliberately NOT forwarded across the org boundary to
# an external service; there is no internal hop to trace.

"""The default rates provider: frankfurter.app, serving ECB reference
rates. Free, keyless, no account.

**What this source actually is — read before charting anything.** The ECB
publishes ONE reference rate per currency per business day (around 16:00
CET), for reference purposes. So:

- ``get_rate`` returns the latest published DAILY reference, not a live
  quote. ``bid == ask == mid`` because the source has no spread to
  report, and ``ts`` carries the reference DATE (rendered as midnight
  UTC) because there is no quote time to carry.
- ``get_history`` rows have ``open == high == low == close`` — one rate
  per day is all that exists here, and fabricating an intraday range
  around it would be lying in candle form. Weekends and ECB holidays are
  simply absent, so a [days]-day window returns fewer than [days] rows.

That makes this a display/analysis layer: conversions, charts, market
state over daily closes. It is NOT tick data and NOT tradeable pricing —
live broker bid/ask arrives through the broker connector seam
(api/account.py `_broker_snapshot`), and nothing here pretends otherwise.

Coverage is the ECB reference list (~30 currencies). A pair the ECB does
not publish raises [RatesUnavailable]; per the module rule in
api/account.py, no fallback number is invented.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from .provider import (
    RatesProvider,
    RatesUnavailable,
    register_provider,
    split_pair,
)

API_BASE = "https://api.frankfurter.app"

_TIMEOUT_SECONDS = 10


def _http_get_json(url):
    """GET [url], parsed as JSON. Every transport or parse failure
    becomes [RatesUnavailable] — the caller's contract is 'a real answer
    or an honest error', never a stack trace from urllib internals."""
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT_SECONDS) as response:
            body = response.read()
        return json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise RatesUnavailable(
            "frankfurter.app request failed ({0}): {1}".format(url, exc)
        )


class FrankfurterProvider(RatesProvider):
    """ECB daily reference rates via frankfurter.app. See the module
    docstring for what that does and does not mean."""

    source = "frankfurter"

    def __init__(self, fetch_json=None, today=None):
        # Both seams exist for tests: no test performs a live HTTP call.
        self._fetch_json = fetch_json or _http_get_json
        self._today = today or (lambda: datetime.now(timezone.utc).date())

    def get_rate(self, pair):
        base, quote = split_pair(pair)
        url = "{0}/latest?{1}".format(
            API_BASE, urllib.parse.urlencode({"base": base, "symbols": quote})
        )
        payload = self._fetch_json(url)
        rates = payload.get("rates") if isinstance(payload, dict) else None
        value = rates.get(quote) if isinstance(rates, dict) else None
        date = payload.get("date") if isinstance(payload, dict) else None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RatesUnavailable(
                "frankfurter.app returned no {0}{1} rate — the ECB does not "
                "publish this pair, or the payload changed shape.".format(base, quote)
            )
        if not isinstance(date, str) or not date:
            raise RatesUnavailable("frankfurter.app payload carried no date.")
        mid = float(value)
        return {
            "pair": base + quote,
            "bid": mid,  # reference rate: no spread exists to report
            "ask": mid,
            "mid": mid,
            "ts": "{0}T00:00:00+00:00".format(date),
            "source": self.source,
        }

    def get_history(self, pair, days):
        base, quote = split_pair(pair)
        window = int(days)
        end = self._today()
        start = end - timedelta(days=window)
        url = "{0}/{1}..{2}?{3}".format(
            API_BASE,
            start.isoformat(),
            end.isoformat(),
            urllib.parse.urlencode({"base": base, "symbols": quote}),
        )
        payload = self._fetch_json(url)
        rates = payload.get("rates") if isinstance(payload, dict) else None
        if not isinstance(rates, dict):
            raise RatesUnavailable(
                "frankfurter.app returned no {0}{1} history.".format(base, quote)
            )
        rows = []
        for date in sorted(rates):
            entry = rates[date]
            value = entry.get(quote) if isinstance(entry, dict) else None
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                # A day present but unreadable is a malformed payload, not
                # a market holiday — holidays are absent keys.
                raise RatesUnavailable(
                    "frankfurter.app history for {0}{1} is malformed on "
                    "{2}.".format(base, quote, date)
                )
            close = float(value)
            rows.append(
                {
                    # One reference rate per day is all the ECB publishes;
                    # a flat candle is the honest rendering of that.
                    "date": date,
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                }
            )
        return rows


register_provider("frankfurter", FrankfurterProvider)
