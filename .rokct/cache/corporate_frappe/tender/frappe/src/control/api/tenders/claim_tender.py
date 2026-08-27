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
def claim_tender(slug: str) -> dict:
	"""
	Claims a tender for the logged-in, entitled user: creates a Tender Bid
	seeded with a checklist COPIED from the tender's advanced enrichment
	(falling back to the generic defaults), so the bid survives catalog
	resyncs, then appended with the applicable deterministic compliance
	gates (Tender Compliance Rule fixtures). Idempotent: returns the
	existing bid if already claimed.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("claim_tender", trace_id, slug=slug)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)

	from {app_name}.tender.control.api.tenders.tender_entitlement import (
		find_tender_by_slug,
		get_enrichment_for_slug,
		get_generic_default_tasks,
		get_tender_entitlement,
		parse_enrichment_task,
	)

	if frappe.session.user == "Guest":
		frappe.throw("Please log in to claim a tender.", frappe.PermissionError)

	entitlement = get_tender_entitlement()
	if not entitlement["entitled"]:
		frappe.throw(
			"Your subscription plan does not include tender management.",
			frappe.PermissionError,
		)

	existing = frappe.db.get_value(
		"Tender Bid", {"user": frappe.session.user, "tender_slug": slug}, "name"
	)
	if existing:
		return frappe.get_doc("Tender Bid", existing).as_dict()

	tender = find_tender_by_slug(slug)
	if not tender:
		frappe.throw(f"Tender not found: {slug}", frappe.DoesNotExistError)

	enrichment = get_enrichment_for_slug(slug)
	raw_tasks = enrichment["tasks"] if enrichment else get_generic_default_tasks()

	# F-08: classify the source record deterministically - an advert-only
	# record (no pack content the catalog layer can serve) auto-attaches the
	# GATE-PACK-COLLECT fatal gate through the normal rule sync below.
	from {app_name}.tender.control.compliance.enrichment_gate import (
		classify_source_record,
		load_gate_params,
	)

	source_record_class = classify_source_record(tender, enrichment, load_gate_params())

	bid = frappe.get_doc(
		{
			"doctype": "Tender Bid",
			"user": frappe.session.user,
			"tender_slug": slug,
			"tender_title": tender.get("title"),
			"institution": tender.get("institution"),
			"closing_date": tender.get("closing_date") or None,
			"status": "Watching",
			"enrichment_level": "ADVANCED" if enrichment else "GENERIC",
			"source_record_class": source_record_class,
			# F-13: the registry record's named contact - displayed on the
			# opportunity page today, now also carried onto the bid so the
			# dispatch endpoint has a stored destination the desk can edit.
			# submission_channel is NOT seeded: it is a manual read from the
			# pack (blank = unknown = full-pack dispatch refused).
			"buyer_contact_person": tender.get("contact_person") or None,
			"buyer_contact_email": tender.get("email") or None,
			"checklist": [parse_enrichment_task(t) for t in raw_tasks],
		}
	)
	# Append the deterministic compliance checklist: universal registration
	# gates and disqualification causes always, conditional rules when the
	# bid's regime/value triggers match. Rules are fixture data - updating a
	# rule changes future checklists with zero code changes.
	from {app_name}.tender.control.compliance.checklist import sync_compliance_checklist

	sync_compliance_checklist(bid)

	bid.insert(ignore_permissions=True)
	frappe.db.commit()
	return bid.as_dict()
