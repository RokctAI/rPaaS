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
def get_my_bids() -> list:
	"""
	Lists the logged-in user's Tender Bids with checklist progress counts,
	soonest closing date first.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("get_my_bids", trace_id)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)

	if frappe.session.user == "Guest":
		frappe.throw("Please log in to view your bids.", frappe.PermissionError)

	bids = frappe.get_all(
		"Tender Bid",
		filters={"user": frappe.session.user},
		fields=[
			"name",
			"tender_slug",
			"tender_title",
			"institution",
			"closing_date",
			"status",
			"enrichment_level",
			"submitted_on",
			"outcome_value",
		],
		order_by="closing_date asc",
	)

	for bid in bids:
		total = frappe.db.count("Bid Checklist Item", {"parent": bid.name, "parenttype": "Tender Bid"})
		done = frappe.db.count(
			"Bid Checklist Item", {"parent": bid.name, "parenttype": "Tender Bid", "status": "Done"}
		)
		bid["tasks_total"] = total
		bid["tasks_done"] = done

	# Bid-time pricing bands (ADDITIVE enrichment): each bid also carries
	# the typical winning-price band for its tender's buyer / category /
	# province, compacted from PR #55's market-context tables (median/IQR
	# of published award amounts - aggregate PUBLIC data only, never
	# per-subscriber data; None when no comparable cell reached the
	# N >= 30 discipline). Guarded so any failure here serves the payload
	# exactly as it always was.
	try:
		from {app_name}.tender.control.api.opportunity_utils import (
			get_cached_opportunities,
		)
		from {app_name}.tender.control.compliance.pricing_bands import (
			attach_pricing_bands,
		)

		attach_pricing_bands(bids, get_cached_opportunities("tenders") or [])
	except Exception:
		pass

	return bids
