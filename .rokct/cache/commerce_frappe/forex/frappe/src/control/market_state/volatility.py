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

"""Coarse daily-range volatility buckets — frappe-free pure module.

Input is the rates layer's cached daily history — a list of
``{"date", "open", "high", "low", "close"}`` dicts, oldest first, built
from DAILY ECB REFERENCE DATA. That is one official fix per day, not tick
data, so a day's "range" here is the spread of daily reference values,
systematically NARROWER than the true intraday range. The measures are
still comparable with each other — which is all a bucket needs — but the
absolute numbers must never be quoted as intraday ranges.

Three honest measures and nothing more:

  - ``average_daily_range(history)``: mean of (high - low) over the
    BASELINE candles — every candle except the most recent.
  - the most recent candle's range, and its RATIO to that baseline.
  - a label from the ratio: quiet / normal / elevated (or ``unknown``).

THESE ARE DESCRIPTIVE BUCKETS, NOT PREDICTIONS. "Elevated" means "the
last daily range was noticeably wider than its own recent average" —
a statement about yesterday, carrying no implication about tomorrow.
Anything that smells of forecasting (ATR crossovers, regime models,
breakout probabilities) is deliberately absent.

The most recent candle is EXCLUDED from the baseline so the ratio
compares the newest day against the days before it; including it would
drag the average toward the very value being judged and mute every
bucket by construction.

Missing or unusable data yields ``state: "unknown"`` with ``ratio: None``
— never a made-up "normal". A pair with two days of history has no
baseline worth the name, and pretending otherwise is fabricating data.
"""

#: Bucket thresholds on ``latest_range / average_range``. Below QUIET_BELOW
#: the label is "quiet"; at or above ELEVATED_AT it is "elevated"; between
#: them, "normal". Half-open like everything else here: exactly 0.7 is
#: normal, exactly 1.3 is elevated. The values are round conventions — a
#: day at 70% or 130% of its own recent average is where a human eyeball
#: starts calling a chart quiet or busy — not fitted parameters, and moving
#: them re-labels history without changing any stored number.
QUIET_BELOW = 0.7
ELEVATED_AT = 1.3

#: Minimum candles for a verdict: the latest plus at least this many
#: baseline candles. Below it, everything is "unknown".
MIN_BASELINE_DAYS = 3

_STATES = ("quiet", "normal", "elevated", "unknown")


def _candle_range(candle):
    """(high - low) of one candle, or None when the candle is unusable.

    Unusable means: not a dict, missing/non-numeric high or low, or an
    inverted pair (high < low). Unusable candles are dropped, not
    repaired — a repaired candle is an invented one.
    """
    if not isinstance(candle, dict):
        return None
    try:
        high = float(candle["high"])
        low = float(candle["low"])
    except (KeyError, TypeError, ValueError):
        return None
    if high < low:
        return None
    return high - low


def average_daily_range(history):
    """Mean daily (high - low) over the baseline candles — every usable
    candle EXCEPT the most recent. None when fewer than
    ``MIN_BASELINE_DAYS`` usable baseline candles exist."""
    ranges = usable_ranges(history)
    baseline = ranges[:-1]
    if len(baseline) < MIN_BASELINE_DAYS:
        return None
    return sum(baseline) / len(baseline)


def usable_ranges(history):
    """The usable candle ranges, oldest first, unusable entries dropped."""
    if not isinstance(history, (list, tuple)):
        return []
    ranges = []
    for candle in history:
        value = _candle_range(candle)
        if value is not None:
            ranges.append(value)
    return ranges


def classify(ratio):
    """Ratio -> bucket label. None -> "unknown"."""
    if ratio is None:
        return "unknown"
    if ratio < QUIET_BELOW:
        return "quiet"
    if ratio >= ELEVATED_AT:
        return "elevated"
    return "normal"


def evaluate(history):
    """The whole volatility verdict for one pair's daily history.

    Returns::

        {
            "basis": "daily_reference",   # honesty marker: ECB daily fixes
            "sample_size": int,           # usable candles seen
            "average_daily_range": float | None,   # baseline mean
            "latest_daily_range": float | None,    # newest candle's range
            "ratio": float | None,        # latest / average
            "state": "quiet" | "normal" | "elevated" | "unknown",
        }

    ``unknown`` (with None numbers) whenever the baseline is too thin or
    degenerate — including a flat zero baseline, where the ratio would be
    a division by zero dressed up as a signal.
    """
    ranges = usable_ranges(history)
    latest = ranges[-1] if ranges else None
    average = average_daily_range(history)

    ratio = None
    if average is not None and latest is not None and average > 0:
        ratio = latest / average

    return {
        "basis": "daily_reference",
        "sample_size": len(ranges),
        "average_daily_range": average,
        "latest_daily_range": latest,
        "ratio": ratio,
        "state": classify(ratio),
    }
