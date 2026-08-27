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

"""Deterministic 80/20 - 90/10 preference-point arithmetic.

Constants live in the SCORE-SYSTEM / SCORE-PRICE-FORMULA fixture records
(Tender Compliance Rule.params), so procurement-threshold changes are data
edits, not code changes. Formulas (PPPFA regulations, guide section 4.3/6.3):

	Ps = X * (1 - (Pt - Pmin) / Pmin)   with X in {80, 90}

and, for disposal/leasing/income-generating tenders where the highest
acceptable offer scores full points, the inverted form:

	Ps = X * (1 + (Pt - Pmax) / Pmax)

Where functionality is scored it is an elimination gate applied before
price/preference; its threshold is per-tender data recorded on the bid
(corpus range roughly 40-83%), never a code constant.
"""

from frappe.utils import flt

DEFAULT_THRESHOLD_RAND = 50_000_000
DEFAULT_STRADDLE_BAND_PCT = 0.0


def preference_system_for_value(estimated_value, params=None):
	"""Classifies a bid value as '80/20', '90/10' or 'Straddling'.

	Empty value -> "" (not classified). Values within the configured straddle
	band around the threshold return 'Straddling' - some buyers fix the system
	only after opening, so a straddling price must survive both systems.
	"""
	if not estimated_value:
		return ""
	params = params or {}
	threshold = flt(params.get("threshold_rand")) or DEFAULT_THRESHOLD_RAND
	band_pct = flt(params.get("straddle_band_pct", DEFAULT_STRADDLE_BAND_PCT))
	value = flt(estimated_value)

	if band_pct > 0:
		band = threshold * band_pct / 100.0
		if abs(value - threshold) <= band:
			return "Straddling"

	return "80/20" if value <= threshold else "90/10"


def price_points(bid_price, lowest_price, points_base):
	"""Ps = X * (1 - (Pt - Pmin) / Pmin), clamped at >= 0. Pure arithmetic."""
	lowest = flt(lowest_price)
	if lowest <= 0:
		return 0.0
	points = flt(points_base) * (1 - (flt(bid_price) - lowest) / lowest)
	return max(points, 0.0)


def price_points_inverted(bid_price, highest_price, points_base):
	"""Ps = X * (1 + (Pt - Pmax) / Pmax), clamped at >= 0. Pure arithmetic.

	The disposal/leasing/income-generating variant: the highest acceptable
	offer takes the full base and lower offers score proportionally less.
	"""
	highest = flt(highest_price)
	if highest <= 0:
		return 0.0
	points = flt(points_base) * (1 + (flt(bid_price) - highest) / highest)
	return max(points, 0.0)


def passes_functionality(self_score, threshold):
	"""Elimination gate: True when no threshold is recorded, or score >= it."""
	if not threshold:
		return True
	if self_score is None:
		return False
	return flt(self_score) >= flt(threshold)


def failing_functionality_sections(sections):
	"""Labels of scored sections whose self-score misses their own threshold.

	Sectioned functionality (F-05): packs like VCW score sections separately
	(~335 pts and 165 pts, EACH with its own 75% kill), DFFE runs a
	6-criterion 100-pt rubric, RNM a 42/70 matrix - one failing section kills
	the whole bid. Each row: ``self_score_points / max_points * 100`` must
	reach ``threshold_pct``.

	Defensive on data (mirroring ``parse_json_field``): rows without a
	positive ``threshold_pct`` are informational and never fail; rows without
	a positive ``max_points`` are malformed and never fail a bid on bad data.
	A missing self-score counts as 0 - consistent with the single-pair
	``passes_functionality`` semantics, where no recorded score fails a
	recorded threshold. Rows may be dicts or child-table documents.
	"""
	failing = []
	for index, row in enumerate(sections or [], start=1):
		threshold = flt(row.get("threshold_pct"))
		max_points = flt(row.get("max_points"))
		if threshold <= 0 or max_points <= 0:
			continue
		score_pct = flt(row.get("self_score_points")) / max_points * 100.0
		if score_pct < threshold:
			failing.append(str(row.get("section_label") or f"Section {index}"))
	return failing


def passes_functionality_sections(sections):
	"""Sectioned elimination gate: True when no scored section fails."""
	return not failing_functionality_sections(sections)
