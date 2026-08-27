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


@frappe.whitelist(allow_guest=True)
def get_tender_detail(slug: str) -> dict:
	"""
	Returns one tender from the published catalog plus its task checklist,
	gated by the caller's subscription:
	- entitled users (Subscription Plan.enable_tenders) get the real
	  per-tender advanced_enrichment tasks;
	- guests / free users get the generic default tasks as a teaser, with
	  advanced_available signalling whether there is a real checklist to unlock.

	Never leaks enrichment content to non-entitled callers.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("get_tender_detail", trace_id)
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

	tender = find_tender_by_slug(slug)
	if not tender:
		frappe.throw(f"Tender not found: {slug}", frappe.DoesNotExistError)

	tender = tender.copy()
	tender.pop("advanced_enrichment", None)

	entitlement = get_tender_entitlement()
	enrichment = get_enrichment_for_slug(slug)

	if entitlement["entitled"] and enrichment:
		tasks = [parse_enrichment_task(t) for t in enrichment["tasks"]]
		enrichment_level = "ADVANCED"
	else:
		tasks = [parse_enrichment_task(t) for t in get_generic_default_tasks()]
		enrichment_level = "GENERIC"

	bid = None
	if frappe.session.user != "Guest":
		bid = frappe.db.get_value(
			"Tender Bid",
			{"user": frappe.session.user, "tender_slug": slug},
			["name", "status"],
			as_dict=True,
		)

	return {
		"tender": tender,
		"tasks": tasks,
		"enrichment_level": enrichment_level,
		"advanced_available": bool(enrichment),
		"entitled": entitlement["entitled"],
		"entitlement_reason": entitlement["reason"],
		"bid": bid,
	}
