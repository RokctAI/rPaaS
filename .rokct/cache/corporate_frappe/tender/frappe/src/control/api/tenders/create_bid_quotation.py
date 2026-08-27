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

try:
	from {app_name}.tender.control.api.telemetry import log_api_call
except Exception:  # standalone verify-suite load: no composed package to import from

	def log_api_call(endpoint, trace_id=None, **fields):
		"""Legacy stderr fallback, format-identical to the old print lines."""
		extras = "".join(f" {key}={value}" for key, value in fields.items())
		print(f"[tender.api] {endpoint}{extras} trace_id={trace_id}", file=sys.stderr)


@frappe.whitelist()
def create_bid_quotation(bid: str) -> dict:
	"""
	Creates a DRAFT erp Quotation pre-linked to one of the caller's Tender
	Bids, so pricing happens in ERP and the pack generator picks the line
	items up from the bid. SOFT integration: the erp module (forked ERPNext
	in the pay repo) is optional at compose time - without its Quotation
	doctype this endpoint fails with a clear message and nothing else in the
	tender module depends on it. Idempotent: an existing linked quotation is
	returned instead of creating a duplicate.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("create_bid_quotation", trace_id, bid=bid)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)
	if frappe.session.user == "Guest":
		frappe.throw("Please log in to create a quotation.", frappe.PermissionError)

	from {app_name}.tender.control.api.tenders.tender_entitlement import get_owned_bid
	from {app_name}.tender.control.quotation_link import (
		ensure_quotation_tender_field,
		quotation_doctype_available,
	)

	if not quotation_doctype_available():
		frappe.throw(
			"The erp module is not installed on this site, so quotations cannot "
			"be created here - the pricing schedule stays a fill-by-hand section "
			"of the pack.",
			title="ERP Not Available",
		)

	bid_doc = get_owned_bid(bid)

	existing = bid_doc.get("quotation")
	if existing and frappe.db.exists("Quotation", existing):
		return {"quotation": existing, "created": False}

	# Make sure the reverse-link custom field exists before we set it.
	ensure_quotation_tender_field()

	quotation = frappe.new_doc("Quotation")
	if frappe.get_meta("Quotation").has_field("tender_bid"):
		quotation.set("tender_bid", bid_doc.name)
	if frappe.get_meta("Quotation").has_field("title") and bid_doc.get("tender_title"):
		quotation.set("title", bid_doc.tender_title)
	# Draft with no party/items yet - the user completes it in ERP. The erp
	# schema's mandatory fields only bind at submit, so skip them for a draft.
	quotation.flags.ignore_mandatory = True
	quotation.insert(ignore_permissions=True)

	bid_doc.db_set("quotation", quotation.name)
	frappe.db.commit()
	return {"quotation": quotation.name, "created": True}
