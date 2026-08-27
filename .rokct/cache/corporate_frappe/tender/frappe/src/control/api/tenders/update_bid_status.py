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


VALID_STATUSES = ("Watching", "Preparing", "Submitted", "Awarded", "Lost", "Withdrawn")


@frappe.whitelist()
def update_bid_status(
	bid: str,
	status: str,
	submitted_on: str | None = None,
	outcome_value: float | None = None,
	outcome_notes: str | None = None,
) -> dict:
	"""
	Updates the lifecycle status (and optional submission/outcome fields) of a
	Tender Bid owned by the logged-in user. A transition to Submitted runs the
	deterministic pre-submission validator (open Fatal gates, expired
	compliance artifacts, functionality threshold); whether failures block or
	only warn is controlled by Tender Control Settings.enforce_submission_gates.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("update_bid_status", trace_id, bid=bid, status=status)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)

	from {app_name}.tender.control.api.tenders.tender_entitlement import get_owned_bid
	from {app_name}.tender.control.compliance.submission_gate import enforce_submission_gates

	if status not in VALID_STATUSES:
		frappe.throw(f"Invalid status: {status}")

	doc = get_owned_bid(bid)

	if status == "Submitted" and doc.status != "Submitted":
		enforce_submission_gates(doc)

	doc.status = status
	if status == "Submitted" and not (submitted_on or doc.submitted_on):
		submitted_on = frappe.utils.nowdate()
	if submitted_on:
		doc.submitted_on = submitted_on
	if outcome_value is not None:
		doc.outcome_value = outcome_value
	if outcome_notes is not None:
		doc.outcome_notes = outcome_notes
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.as_dict()
