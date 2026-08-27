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

"""Pre-submission validator - runs when a Tender Bid moves to Submitted.

Deterministic gates only (guide section 2, "how bids die"):

1. every Fatal checklist item must be Done;
2. every applicable Fatal rule that names a required artifact type must be
   backed by an unexpired Compliance Artifact for the bidding user
   (valid_until >= closing_date, or >= today when the bid has no closing
   date);
3. the functionality elimination gate, per the bid's ``functionality_mode``
   (F-05): blank / "Single threshold" keeps the original single-pair check
   (self-score must reach the recorded threshold); "Sectioned" checks every
   scored row of ``functionality_sections`` and reports each failing section
   by label (e.g. VCW's two sections each carry their own 75% kill);
   "No scored functionality" skips the gate entirely (the Musina case - an
   explicit state, not an ambiguous zero);
4. the F-15(b) attestation gate: a returnable row carrying a generated
   satisfying artifact that is not attested fails readiness (rows without
   an artifact are untouched - additive only).

Enforcement is opt-in: Tender Control Settings.enforce_submission_gates
(default off for rollout safety) decides whether failures block the
transition or only surface as a warning.
"""

import frappe
from frappe.utils import cint, getdate, nowdate

# Same-package imports (F-09): the relative import works on a composed bench;
# the importlib fallback keeps this module importable standalone by file path,
# matching the proven pack_builder.py pattern. Zero behaviour change composed.
try:
	from .pack_lints import (
		pricing_reconciliation_warnings,
		unattested_artifact_failures,
		unmatched_template_code_warnings,
	)
	from .rules import get_applicable_rules
	from .scoring import failing_functionality_sections, passes_functionality
	from ..parsing.pack_ingest import parse_pack_suggestion_warning
except ImportError:  # standalone by-path import - load the siblings directly
	import importlib.util as _importlib_util
	import os as _os

	def _load_sibling(_module_name, _filename):
		_spec = _importlib_util.spec_from_file_location(
			_module_name,
			_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), _filename),
		)
		_module = _importlib_util.module_from_spec(_spec)
		_spec.loader.exec_module(_module)
		return _module

	_rules = _load_sibling("tender_submission_gate_rules", "rules.py")
	_scoring = _load_sibling("tender_submission_gate_scoring", "scoring.py")
	_pack_lints = _load_sibling("tender_submission_gate_pack_lints", "pack_lints.py")
	_pack_ingest = _load_sibling(
		"tender_submission_gate_pack_ingest", _os.path.join("..", "parsing", "pack_ingest.py")
	)
	get_applicable_rules = _rules.get_applicable_rules
	failing_functionality_sections = _scoring.failing_functionality_sections
	passes_functionality = _scoring.passes_functionality
	pricing_reconciliation_warnings = _pack_lints.pricing_reconciliation_warnings
	unattested_artifact_failures = _pack_lints.unattested_artifact_failures
	unmatched_template_code_warnings = _pack_lints.unmatched_template_code_warnings
	parse_pack_suggestion_warning = _pack_ingest.parse_pack_suggestion_warning


def gates_enforced():
	"""Whether submission gates block (Tender Control Settings check field)."""
	if not frappe.db.exists("DocType", "Tender Control Settings"):
		return False
	return cint(
		frappe.db.get_single_value("Tender Control Settings", "enforce_submission_gates")
	)


SECTIONED_NO_SECTIONS_WARNING = (
	"Sectioned functionality selected but no sections captured - the "
	"functionality gate has nothing to check, so it passes by default. "
	"Capture the pack's sections (each with its max points and threshold) "
	"in the Functionality Sections table, or switch the mode if the pack "
	"really has no scored functionality. [SECTIONED-NO-SECTIONS]"
)


def submission_readiness_warnings(bid, template_codes=None):
	"""Advisory findings that must be VISIBLE but never block submission.

	Wave-1's preference-conflict lint style: deterministic, data-only, and
	separate from the hard gate list ``validate_submission_readiness``
	returns. Cases:

	- ``functionality_mode = "Sectioned"`` with an EMPTY sections table -
	  defensible to pass (the desk may still be reading the evaluation pages
	  in), but silently passing an unscored sectioned matrix hides that the
	  elimination gate checked nothing;
	- a captured returnable's ``template_code`` matching no Tender Form
	  Template (the worksheet still renders template-less - unchanged - but
	  the typo'd code is now named instead of silently ignored);
	- pricing-grid reconciliation: annual vs monthly x 12, fixed-portion
	  grid total vs the bid's cover price, and a recorded-but-not-applied
	  escalation rate (compliance/pack_lints.py, pure functions);
	- PR-D (F-02): an open GATE-PACK-COLLECT row while a pack file IS
	  attached to the bid - suggests running the deterministic pack parser
	  (parsing/pack_ingest.py, pure function; the File lookup is guarded).

	``template_codes`` lets a caller that already loaded the templates pass
	their codes in; when omitted they are read from the db, and when neither
	is possible the template-code lint stays silent rather than guessing.
	"""
	warnings = []
	if bid.get("functionality_mode") == "Sectioned" and not (
		bid.get("functionality_sections") or []
	):
		warnings.append(SECTIONED_NO_SECTIONS_WARNING)
	warnings.extend(
		unmatched_template_code_warnings(
			bid.get("custom_returnables") or [],
			_known_template_codes(template_codes),
		)
	)
	warnings.extend(
		pricing_reconciliation_warnings(
			bid.get("pricing_periods") or [],
			cover_price=_bid_cover_price(bid),
			escalation_rate_pct=bid.get("escalation_rate_pct"),
		)
	)
	# PR-D (F-02): when the bid started advert-only (open GATE-PACK-COLLECT
	# row) but a pack file has since been attached, suggest running the
	# deterministic pack parser. Advisory only - pure check, guarded db read.
	suggestion = parse_pack_suggestion_warning(
		bid.get("checklist") or [], _has_attached_pack_file(bid)
	)
	if suggestion:
		warnings.append(suggestion)
	return warnings


PACK_FILE_EXTENSIONS = (".pdf", ".txt", ".md", ".html")


def _has_attached_pack_file(bid):
	"""Whether a pack-shaped file is attached to this bid. Guarded: any
	failure (standalone import, no File doctype, dict-shaped bid without a
	name) returns False and the suggestion simply stays silent."""
	name = bid.get("name")
	if not name:
		return False
	try:
		attached = frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Tender Bid", "attached_to_name": name},
			pluck="file_name",
		)
	except Exception:
		return False
	return any(
		str(file_name or "").lower().endswith(PACK_FILE_EXTENSIONS)
		for file_name in attached or []
	)


def _known_template_codes(template_codes=None):
	"""The existing Tender Form Template codes, or None when unknowable.

	None (rather than an empty set) keeps the unmatched-template lint silent
	when the template list genuinely cannot be established - flagging every
	coded row on missing data would be noise, not signal.
	"""
	if template_codes is not None:
		return template_codes
	try:
		return frappe.get_all("Tender Form Template", pluck="template_code")
	except Exception:
		return None


def _bid_cover_price(bid):
	"""The bid's cover price from its soft-linked erp Quotation, or None.

	Mirrors load_quotation_pricing's guards (the erp module is optional at
	compose time): no linked name, no Quotation doctype on the bench, or a
	dangling name all return None and the cover-price lint stays silent.
	"""
	name = bid.get("quotation")
	if not name:
		return None
	try:
		if not frappe.db.exists("DocType", "Quotation"):
			return None
		if not frappe.db.exists("Quotation", name):
			return None
		total = frappe.db.get_value("Quotation", name, "grand_total")
	except Exception:
		return None
	return total if total not in (None, "") else None


def validate_submission_readiness(bid):
	"""Returns the list of open-gate failure messages for a Tender Bid.

	Includes the F-15(b) attestation gate: a returnable row carrying a
	generated satisfying artifact that is NOT attested fails readiness
	(generated-and-attested discipline; rows without an artifact are
	untouched, so pre-existing bids behave exactly as before). Dispatch
	gates on this list, so an unattested artifact never dispatches.
	"""
	failures = []

	failures.extend(unattested_artifact_failures(bid.get("custom_returnables") or []))

	for row in bid.get("checklist") or []:
		if row.get("severity") == "Fatal" and row.get("status") != "Done":
			failures.append(
				f"Fatal checklist item still open: {row.get('task_text')} "
				f"[{row.get('rule_code') or 'manual'}]"
			)

	reference_date = getdate(bid.get("closing_date") or nowdate())
	for rule in get_applicable_rules(bid):
		if rule.get("severity") != "Fatal" or not rule.get("artifact_type"):
			continue
		if not _has_valid_artifact(bid.get("user"), rule["artifact_type"], reference_date):
			failures.append(
				f"Missing or expired compliance artifact: {rule['artifact_type']} "
				f"(required by {rule['rule_code']} - {rule['title']})"
			)

	mode = bid.get("functionality_mode")
	if mode == "Sectioned":
		for label in failing_functionality_sections(bid.get("functionality_sections")):
			failures.append(
				f"Functionality section below its threshold: {label} - "
				"one failing section eliminates the whole bid before price "
				"and preference."
			)
	elif mode != "No scored functionality":
		# Blank / "Single threshold": the original single-pair gate, verbatim.
		if not passes_functionality(
			bid.get("functionality_self_score"), bid.get("functionality_threshold")
		):
			failures.append(
				"Functionality self-score is below the pack's threshold - "
				"functionality is an elimination gate before price and preference."
			)

	return failures


def _has_valid_artifact(user, artifact_type, reference_date):
	"""True when the user holds an artifact of this type valid on the date."""
	if not user:
		return False
	rows = frappe.get_all(
		"Compliance Artifact",
		filters={"user": user, "artifact_type": artifact_type},
		fields=["valid_until"],
	)
	for row in rows:
		if not row.valid_until or getdate(row.valid_until) >= reference_date:
			return True
	return False


def enforce_submission_gates(bid):
	"""Throws (or warns, per settings) when a bid is not submission-ready."""
	warnings = submission_readiness_warnings(bid)
	if warnings:
		# Advisory only - always msgprint, never throw, regardless of the
		# enforcement setting.
		frappe.msgprint(
			"Submission warnings (not blocking):\n- " + "\n- ".join(warnings),
			title="Submission Warnings",
			indicator="orange",
		)

	failures = validate_submission_readiness(bid)
	if not failures:
		return

	message = "This bid is not submission-ready:\n- " + "\n- ".join(failures)
	if gates_enforced():
		frappe.throw(message, title="Submission Gates Open")
	else:
		frappe.msgprint(message, title="Submission Gates Open", indicator="orange")
