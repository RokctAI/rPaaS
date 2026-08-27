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
from frappe.utils import cint, nowdate

try:
	from {app_name}.tender.control.api.telemetry import log_api_call
except Exception:  # standalone verify-suite load: no composed package to import from

	def log_api_call(endpoint, trace_id=None, **fields):
		"""Legacy stderr fallback, format-identical to the old print lines."""
		extras = "".join(f" {key}={value}" for key, value in fields.items())
		print(f"[tender.api] {endpoint}{extras} trace_id={trace_id}", file=sys.stderr)


@frappe.whitelist()
def get_compliance_calendar(days_ahead: int = 90, limit: int = 200) -> dict:
	"""
	The unified compliance calendar (assessment plan #13): the four
	existing date streams - the caller's bid closing dates, their bids'
	briefing dates, their compliance-artifact expiries, and the renewal
	radar's expected-advertisement windows - merged into one dated feed,
	soonest first.

	Assembly, not new logic: each stream reuses its silo's existing
	query/parse path (get_my_bids' bid rows, the catalog card's briefing
	field with the placeholder-date discipline, the expiry sweep's
	``valid_until``, get_renewal_radar's open-watch rows). Per-user items
	(bids, briefings, artifacts) are scoped to the caller; the renewal
	stream is the same aggregate-public-data radar everyone sees, and its
	entries are WATCH items, never commitments (only 2 of 12 sampled due
	predictions validated - the caveat rides every payload).
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("get_compliance_calendar", trace_id)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)

	if frappe.session.user == "Guest":
		frappe.throw("Please log in to view your compliance calendar.", frappe.PermissionError)

	from {app_name}.tender.control.api.tenders.tender_entitlement import (
		find_tender_by_slug,
	)
	from {app_name}.tender.control.compliance.compliance_calendar import (
		DEFAULT_DAYS_AHEAD,
		DEFAULT_LIMIT,
		OPEN_BID_STATUSES,
		build_compliance_calendar,
	)

	days_ahead = cint(days_ahead) or DEFAULT_DAYS_AHEAD
	limit = cint(limit) or DEFAULT_LIMIT

	# -- per-user streams: the caller's bids and standing artifacts ------
	bids = frappe.get_all(
		"Tender Bid",
		filters={"user": frappe.session.user},
		fields=[
			"name", "tender_slug", "tender_title", "institution",
			"closing_date", "status",
		],
		order_by="closing_date asc, name asc",
	)
	artifacts = frappe.get_all(
		"Compliance Artifact",
		filters={"user": frappe.session.user},
		fields=[
			"name", "artifact_type", "reference", "valid_until", "status",
		],
		order_by="valid_until asc, name asc",
	)

	# Briefing dates live on the published catalog card of each OPEN bid -
	# reuse the existing slug lookup, guarded so a catalog hiccup serves
	# the other three streams untouched.
	cards_by_slug = {}
	for bid in bids:
		if bid.get("status") not in OPEN_BID_STATUSES:
			continue
		slug = bid.get("tender_slug")
		if not slug or slug in cards_by_slug:
			continue
		try:
			card = find_tender_by_slug(slug)
		except Exception:
			card = None
		if card:
			cards_by_slug[slug] = card

	# -- aggregate stream: the renewal radar's ledger state (public
	# award-record derivations only, same rows get_renewal_radar serves) -
	watch_fields = [
		"name", "buyer", "buyer_normalized", "category", "source",
		"predicted_date", "predicted_window_start", "predicted_window_end",
		"status",
	]
	open_watches = frappe.get_all(
		"Tender Renewal Watch",
		filters={"status": "open"},
		fields=watch_fields,
		order_by="predicted_date asc, name asc",
	)
	resolved_watches = frappe.get_all(
		"Tender Renewal Watch",
		filters={"status": ("in", ("confirmed", "missed"))},
		fields=["buyer_normalized", "status", "error_days"],
	)

	return build_compliance_calendar(
		bids,
		artifacts,
		cards_by_slug,
		open_watches,
		resolved_watches,
		nowdate(),
		days_ahead=days_ahead,
		limit=limit,
	)
