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

"""Advisory pack lints - pure, deterministic, frappe-free (review-note rows).

Two lint families, both surfaced exactly like the wave-2 SECTIONED-NO-
SECTIONS lint: appended to ``submission_readiness_warnings`` (visible,
never blocking) and printed on the generated pack's cover via the
builder's ``extra_warnings``.

1. ``unmatched_template_code_warnings`` - a captured returnable whose
   ``template_code`` matches no Tender Form Template used to fall back to
   the template-less worksheet SILENTLY; the worksheet still renders
   (behaviour unchanged), but the unmatched code is now named so a typo
   ("MBD61", "ICT-CAPABILTY") is caught before print day.

2. ``pricing_reconciliation_warnings`` - arithmetic cross-checks over the
   F-06 pricing grid: annual_total vs monthly x 12 per row, the fixed-
   portion grid total vs the bid's cover price (linked-quotation total),
   and an escalation rate that is recorded but visibly not applied
   (every priced column flat across periods). The cover-price check is
   explicit about its comparison basis and tolerant of BOTH conventions
   the desk actually uses (review follow-up): a quotation totalled over
   the whole term (Musina's 3-year R2,573,750.00) OR priced year-1-only
   (a first-period quotation against a multi-year grid). Matching either
   basis is silent; only a cover that reconciles to NEITHER warns, and
   the warning names both grid totals so the desk sees exactly what was
   compared.

3. ``unattested_artifact_failures`` - the F-15(b) hard-gate helper: a
   returnable row carrying a satisfying generated artifact that has NOT
   been attested (generated-and-attested is the F-13-style discipline
   before anything counts as satisfied or dispatches).

Everything here is plain data comparison - no frappe import, no AI, no
network - so the functions are unit-testable standalone (F-09 style).
"""

# Rounding tolerance in rand for grid arithmetic: differences at or below
# this are treated as legitimate rounding, anything above is flagged.
RAND_TOLERANCE = 1.0

UNMATCHED_TEMPLATE_TAG = "[RETURNABLE-TEMPLATE-UNMATCHED]"
ANNUAL_MISMATCH_TAG = "[PRICE-ANNUAL-MISMATCH]"
COVER_MISMATCH_TAG = "[PRICE-COVER-MISMATCH]"
ESCALATION_FLAT_TAG = "[PRICE-ESC-FLAT]"


def _get(row, key):
	"""Reads a key from a dict-like or attribute-carrying child row."""
	if hasattr(row, "get"):
		return row.get(key)
	return getattr(row, key, None)


def _num(value):
	"""Parses a numeric field defensively; None when absent/unparsable."""
	if value in (None, ""):
		return None
	try:
		return float(value)
	except (TypeError, ValueError):
		return None


def unmatched_template_code_warnings(returnable_rows, known_template_codes):
	"""Warnings for captured returnables whose template_code matches nothing.

	``known_template_codes`` is the iterable of existing Tender Form Template
	codes (the caller loads them; this function stays db-free). Pass ``None``
	when the template list could not be established - the lint then stays
	silent rather than mass-flagging every coded row on missing data.
	Matching is case-insensitive on the stripped code, mirroring nothing
	fancier than what a desk typo needs.
	"""
	if known_template_codes is None:
		return []
	known = {
		str(code).strip().upper()
		for code in known_template_codes
		if str(code or "").strip()
	}
	warnings = []
	for row in returnable_rows or []:
		code = str(_get(row, "template_code") or "").strip()
		if not code or code.upper() in known:
			continue
		ref = str(_get(row, "ref_code") or _get(row, "form_code") or "").strip() or "?"
		warnings.append(
			f"Custom returnable '{ref}' names template_code '{code}' but no "
			"Tender Form Template with that code exists - the page renders as "
			"the guided template-less worksheet; fix the code (or clear it) to "
			f"get the pre-filled template. {UNMATCHED_TEMPLATE_TAG}"
		)
	return warnings


def pricing_reconciliation_warnings(
	pricing_periods, cover_price=None, escalation_rate_pct=None
):
	"""Arithmetic lints over the multi-year pricing grid (F-06 rows).

	- annual_total deviating from monthly x 12 beyond RAND_TOLERANCE, per row;
	- the grid's fixed portion (once_off + annual_total; per-unit tariff
	  lines are variable by nature and excluded) deviating from
	  ``cover_price`` on BOTH accepted bases (review follow-up - the basis
	  is explicit and tolerant, not a single silent assumption):
	  the FULL-TERM basis (fixed amounts summed across every period) and
	  the FIRST-PERIOD basis (the first row carrying any fixed amount - a
	  quotation legitimately priced year-1-only). Either basis reconciling
	  keeps the lint silent; the warning names both grid totals;
	- ``escalation_rate_pct`` recorded but visibly not applied: two or more
	  priced rows and every priced column (monthly / annual_total) flat.
	All advisory - a grid can be legitimately unusual, so these warn, never
	block, exactly like the existing lints.
	"""
	warnings = []
	rows = list(pricing_periods or [])

	fixed_total = 0.0
	has_fixed_amount = False
	first_period_total = None
	monthly_series = []
	annual_series = []
	for row in rows:
		label = str(_get(row, "period_label") or "").strip() or "?"
		monthly = _num(_get(row, "monthly"))
		annual = _num(_get(row, "annual_total"))
		once_off = _num(_get(row, "once_off"))
		if monthly is not None:
			monthly_series.append(monthly)
		if annual is not None:
			annual_series.append(annual)
		row_fixed = None
		for amount in (once_off, annual):
			if amount is not None:
				fixed_total += amount
				has_fixed_amount = True
				row_fixed = (row_fixed or 0.0) + amount
		if row_fixed is not None and first_period_total is None:
			first_period_total = row_fixed
		if (
			monthly is not None
			and annual is not None
			and abs(monthly * 12.0 - annual) > RAND_TOLERANCE
		):
			warnings.append(
				f"Pricing period '{label}': annual_total R{annual:,.2f} does not "
				f"reconcile with monthly x 12 = R{monthly * 12.0:,.2f} - re-check "
				"the grid arithmetic before transcribing it onto the official "
				f"schedule. {ANNUAL_MISMATCH_TAG}"
			)

	cover = _num(cover_price)
	if cover is not None and has_fixed_amount:
		full_term_matches = abs(fixed_total - cover) <= RAND_TOLERANCE
		first_period_matches = (
			first_period_total is not None
			and abs(first_period_total - cover) <= RAND_TOLERANCE
		)
		if not full_term_matches and not first_period_matches:
			first_period_text = (
				f"R{first_period_total:,.2f}" if first_period_total is not None
				else "n/a"
			)
			warnings.append(
				f"The pricing grid's fixed portion totals R{fixed_total:,.2f} "
				f"across all periods (first period: {first_period_text}; "
				"once-off + annual amounts; per-unit tariff lines excluded as "
				f"variable) but the bid's cover price is R{cover:,.2f} - it "
				"reconciles to neither the full-term nor the first-period "
				"(year-1-only quotation) basis; reconcile the grid to the "
				"cover form before submission: the cover price governs. "
				f"{COVER_MISMATCH_TAG}"
			)

	rate = _num(escalation_rate_pct)
	if rate:
		priced_columns = [s for s in (monthly_series, annual_series) if len(s) >= 2]
		if priced_columns and all(min(s) == max(s) for s in priced_columns):
			warnings.append(
				f"escalation_rate_pct is set ({rate:g}% p.a.) but the period "
				"amounts are flat across the grid - escalation is recorded but "
				"not applied; either escalate the later periods or clear the "
				f"rate if the pack really prices firm. {ESCALATION_FLAT_TAG}"
			)

	return warnings


UNATTESTED_ARTIFACT_TAG = "[RETURNABLE-ARTIFACT-UNATTESTED]"


def unattested_artifact_failures(returnable_rows):
	"""HARD-gate failures for satisfying artifacts attached but not attested.

	F-15(b): a captured returnable (the "Company Profile" class) can be
	satisfied by a generated artifact attached to the bid. The same
	discipline as the F-13 dispatch outputs applies: the artifact counts
	ONLY when generated-and-attested, and a pack carrying an unattested
	artifact never dispatches (dispatch gates on
	``validate_submission_readiness``, which includes these failures).

	Rows without a ``generated_artifact`` are untouched - the hand-fill
	worksheet path behaves exactly as before (additive gate: it can only
	fire on rows that opted into the artifact hook). Pure function.
	"""
	failures = []
	for row in returnable_rows or []:
		artifact = str(_get(row, "generated_artifact") or "").strip()
		if not artifact:
			continue
		if _get(row, "artifact_attested"):
			continue
		ref = str(_get(row, "ref_code") or "").strip() or "?"
		failures.append(
			f"Returnable '{ref}' carries a generated satisfying artifact "
			f"({artifact}) that has not been attested - review the generated "
			"document and attest it (attach_returnable_artifact with "
			"attest=1), or detach it; an unattested artifact does not count "
			f"as satisfying the returnable. {UNATTESTED_ARTIFACT_TAG}"
		)
	return failures
