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

"""Bid-time pricing bands for the bid workspace.

Compacts the market-context typical winning-price band (PR #55's
``market_context.py`` - median/IQR of flag-clean published award amounts
down the fixed fallback chain buyer -> category x province -> category ->
province) into one display-ready block per tracked bid:

- band SELECTION is delegated verbatim to
  ``market_context.resolve_market_context`` (single source of truth -
  this module never re-implements the fallback chain, the N >= 30
  discipline or the buyer alias matching);
- FORMATTING happens here, deterministically, mirroring the frontend's
  ``formatRand`` convention (tender-suitability.tsx) so every surface
  prints the same "R14.4m" for the same amount;
- the block is ABSENT (None) whenever no comparable cell reached the
  N >= 30 discipline - clients render nothing, never a guess.

Aggregate PUBLIC award data only (the committed eTenders-derived
tables); nothing here reads or serves per-subscriber data. Frappe-free
and stdlib-only, standalone-testable like the sibling compliance
modules (suitability.py / renewal.py doctrine).

Honesty caveat carried on every block, mirroring PR #55's wording: the
award feed publishes winner-side successes only, with severe per-buyer
publication bias - the band prices the market the bid lives in, it
NEVER predicts winning.
"""

import math

# Same-package imports (F-09 pattern): relative on a composed bench,
# importlib fallback keeps this module importable standalone by file path.
try:
	from .market_context import resolve_market_context
except ImportError:  # standalone by-path import - load the sibling directly
	import importlib.util as _importlib_util
	import os as _os

	_spec = _importlib_util.spec_from_file_location(
		"tender_pricing_bands_market_context",
		_os.path.join(
			_os.path.dirname(_os.path.abspath(__file__)), "market_context.py"
		),
	)
	_market_context = _importlib_util.module_from_spec(_spec)
	_spec.loader.exec_module(_market_context)
	resolve_market_context = _market_context.resolve_market_context


# Human scope line per band level (the fallback chain's levels, most
# comparable first - same set as market_context.PRICE_BAND_LEVELS).
BAND_SCOPE_LABELS = {
	"buyer": "Published awards for this buyer",
	"category_province": "Published awards for this category in this province",
	"category": "Published awards for this category (all provinces)",
	"province": "Published awards in this province (all categories)",
}

# PR #55's honesty caveat, one line, carried on every band block:
# winner-side only + publication-discipline bias, prices the market,
# never predicts winning.
BAND_CAVEAT = (
	"Based on the public eTenders award record, which only shows published "
	"successes (winner-side amounts, severe per-buyer publication bias) - "
	"it prices the market and never predicts whether a bid will win."
)


def format_rand(amount):
	"""Deterministic compact rand label, mirroring the frontend's
	``formatRand`` (tender-suitability.tsx): R14.4m / R1.20bn / R850k /
	R950. Returns None for a missing/non-numeric amount (never guesses)."""
	if amount is None:
		return None
	try:
		value = float(amount)
	except (TypeError, ValueError):
		return None
	if math.isnan(value):
		return None
	magnitude = abs(value)
	if magnitude >= 1e9:
		return "R{0:.2f}bn".format(value / 1e9)
	if magnitude >= 1e6:
		return "R{0:.1f}m".format(value / 1e6)
	# JS Math.round semantics (half away from zero on positives) so the
	# two renderers can never disagree on the same amount.
	if magnitude >= 1e3:
		return "R{0}k".format(int(math.floor(value / 1e3 + 0.5)))
	return "R{0}".format(int(math.floor(value + 0.5)))


def bid_pricing_band(card, tables=None):
	"""Display-ready pricing-band block for one tender card, or None.

	None whenever the market tables are absent, the card resolved to no
	band (no cell reached the N >= 30 discipline down the fallback
	chain), or the band carries no median - the client renders NOTHING
	then (renewal-radar doctrine), never a placeholder number.
	"""
	context = resolve_market_context(card or {}, tables=tables)
	if not context or not context.get("available"):
		return None
	band = context.get("price_band")
	if not band or band.get("median_rand") is None:
		return None
	iqr = band.get("iqr_rand") or (None, None)
	median_label = format_rand(band.get("median_rand"))
	iqr_label = None
	if iqr[0] is not None and iqr[1] is not None:
		iqr_label = "{0} - {1}".format(format_rand(iqr[0]), format_rand(iqr[1]))
	scope = BAND_SCOPE_LABELS.get(band.get("level")) or "Published awards"
	headline = "{0}: median {1}".format(scope, median_label)
	if iqr_label:
		headline += ", IQR {0}".format(iqr_label)
	dataset = context.get("dataset") or {}
	return {
		"level": band.get("level"),
		"basis": band.get("basis"),
		"scope": scope,
		"median_rand": band.get("median_rand"),
		"iqr_rand": band.get("iqr_rand"),
		"n": band.get("n"),
		"median_label": median_label,
		"iqr_label": iqr_label,
		"headline": headline,
		"semantics": band.get("semantics"),
		"caveat": BAND_CAVEAT,
		"caveats": list(context.get("caveats") or []),
		"dataset": {
			"source": dataset.get("source"),
			"snapshot_date": dataset.get("snapshot_date"),
			"awards": dataset.get("awards"),
		},
	}


def card_index(cards):
	"""slug/tender_number -> card map over the cached published catalog
	(both keys, matching find_tender_by_slug's lookup contract). First
	card wins on a duplicate key (catalog order is stable)."""
	index = {}
	for card in cards or []:
		for key in (card.get("slug"), card.get("tender_number")):
			if key:
				index.setdefault(str(key), card)
	return index


def attach_pricing_bands(bids, cards, tables=None):
	"""Attaches ``pricing_band`` to every bid row, in place (additive:
	no existing field is read differently or rewritten). Bids whose
	tender is no longer in the published catalog, or whose card resolves
	to no honest band, carry None. Returns the same list."""
	index = card_index(cards)
	for bid in bids or []:
		card = index.get(str(bid.get("tender_slug") or ""))
		bid["pricing_band"] = (
			bid_pricing_band(card, tables=tables) if card else None
		)
	return bids
