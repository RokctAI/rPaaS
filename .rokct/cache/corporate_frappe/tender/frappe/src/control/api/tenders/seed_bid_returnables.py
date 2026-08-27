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

# This file uses the composer's literal {app_name} template placeholder in
# imports (fleet SDK convention, cf. polaris) - it only parses after
# composition substitutes the real app package name.
# compliance-ignore-file: syntax-error

import sys

import frappe
from frappe.utils import cint

try:
	from {app_name}.tender.control.api.telemetry import log_api_call
except Exception:  # standalone verify-suite load: no composed package to import from

	def log_api_call(endpoint, trace_id=None, **fields):
		"""Legacy stderr fallback, format-identical to the old print lines."""
		extras = "".join(f" {key}={value}" for key, value in fields.items())
		print(f"[tender.api] {endpoint}{extras} trace_id={trace_id}", file=sys.stderr)

# Deliberately a whitelist: the F-15 studio-hook / artifact-state fields
# (studio_scope, generated_artifact, artifact_attested, artifact_attached_on)
# are EXCLUDED - one bid's generated artifact (or its attestation) must never
# seed another bid's returnable as already satisfied.
RETURNABLE_FIELDS = (
	"ref_code",
	"title",
	"mandatory",
	"category",
	"kill_note",
	"template_code",
	"guidance",
)


def serialize_returnable_rows(rows):
	"""Tender Bid Returnable child rows as plain dicts, in captured order.

	Pure data transformation (standalone-testable): only the desk-captured
	fields travel - never child-row identity (name/parent), so seeded rows
	are NEW rows on the target bid, not references to the source bid's.
	"""
	serialized = []
	for row in rows or []:
		get = row.get if hasattr(row, "get") else lambda key, _row=row: getattr(_row, key, None)
		serialized.append({field: get(field) for field in RETURNABLE_FIELDS})
	return serialized


def pick_seed_rows(prior_rows, existing_rows):
	"""The prior bid's rows that the target bid does not already carry.

	Deterministic dedupe by normalized ref_code (the pack's own reference is
	the row identity everywhere else in the SDK - the pack index, the
	form_code dedupe in apply_custom_returnables); prior order is preserved.
	Pure function.
	"""
	def norm(value):
		return " ".join(str(value or "").lower().split())

	existing_codes = {
		norm(row.get("ref_code") if hasattr(row, "get") else getattr(row, "ref_code", None))
		for row in existing_rows or []
	} - {""}
	picked = []
	for row in prior_rows or []:
		code = norm(row.get("ref_code"))
		if not code or code in existing_codes:
			continue
		existing_codes.add(code)
		picked.append(row)
	return picked


@frappe.whitelist()
def seed_bid_returnables(bid: str, apply: int = 0) -> dict:
	"""
	Per-buyer returnable reuse: when the caller has ALREADY captured custom
	returnables on a prior bid to the same buyer (institution), this returns
	that most recent prior bid's list so a new bid to the buyer can start
	from it instead of a blank table. Deterministic and strictly opt-in:

	- ``apply=0`` (default) only RETURNS the prior list (a preview) - the
	  bid is never modified;
	- ``apply=1`` copies the prior rows onto this bid's custom_returnables,
	  appending in captured order and skipping ref_codes the bid already
	  carries (never overwriting or deleting a captured row).

	Nothing is ever copied silently on claim/save - the frontend must call
	this explicitly with apply=1 after the user opts in. Buyer forms change
	between packs, so seeded rows are a starting point the desk must still
	verify against THIS pack (the response says so).
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("seed_bid_returnables", trace_id, bid=bid, apply=apply)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)
	if frappe.session.user == "Guest":
		frappe.throw("Please log in to seed bid returnables.", frappe.PermissionError)

	from {app_name}.tender.control.api.tenders.tender_entitlement import get_owned_bid

	bid_doc = get_owned_bid(bid)
	institution = (bid_doc.get("institution") or "").strip()
	if not institution:
		frappe.throw(
			"This bid has no institution (buyer) recorded - per-buyer seeding "
			"needs the buyer name to find your prior bids.",
			title="No Buyer On Bid",
		)

	source = find_prior_returnables_source(bid_doc)
	if not source:
		return {
			"institution": institution,
			"source_bid": None,
			"rows": [],
			"applied": 0,
			"note": "No prior bid to this buyer carries captured custom returnables.",
		}

	prior_rows = serialize_returnable_rows(source.get("custom_returnables"))
	result = {
		"institution": institution,
		"source_bid": source.name,
		"source_tender_title": source.get("tender_title"),
		"rows": prior_rows,
		"applied": 0,
		"note": (
			"Seeded rows are a STARTING POINT captured from a different pack - "
			"verify every row against THIS tender document before relying on it."
		),
	}
	if not cint(apply):
		return result

	appended = 0
	for row in pick_seed_rows(prior_rows, bid_doc.get("custom_returnables")):
		bid_doc.append("custom_returnables", row)
		appended += 1
	if appended:
		bid_doc.save(ignore_permissions=True)
		frappe.db.commit()
	result["applied"] = appended
	return result


def find_prior_returnables_source(bid_doc):
	"""The caller's most recently modified OTHER bid to the same buyer that
	carries captured custom returnables, or None. Deterministic: modified-desc
	order, first bid with a non-empty custom_returnables table wins."""
	candidates = frappe.get_all(
		"Tender Bid",
		filters={
			"user": bid_doc.user,
			"institution": bid_doc.institution,
			"name": ["!=", bid_doc.name],
		},
		fields=["name"],
		order_by="modified desc",
	)
	for candidate in candidates:
		doc = frappe.get_doc("Tender Bid", candidate["name"])
		if doc.get("custom_returnables"):
			return doc
	return None
