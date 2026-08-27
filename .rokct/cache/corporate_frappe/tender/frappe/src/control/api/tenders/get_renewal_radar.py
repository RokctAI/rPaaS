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


MAX_LIMIT = 500

# The research report's honesty layer (section 8), carried on every
# response so no client renders the radar as a certainty.
RADAR_CAVEATS = [
	"a predicted window is a LEAD CALENDAR entry ('prepare now'), never a "
	"certainty - match the successor by buyer + category when it appears",
	"duration text noise: regex extraction from free text mis-reads some "
	"durations despite the noise guards",
	"extensions delay returns: buyers routinely extend expiring contracts "
	"rather than re-advertise on time (the window reaches further late "
	"than early for exactly this reason)",
	"early re-advertisement happens: cancellations, budget cycles and "
	"scope changes bring tenders back before term",
	"'as and when required' panel appointments have no single return date "
	"at all",
]


@frappe.whitelist()
def get_renewal_radar(months_ahead: int = 12, limit: int = 100) -> dict:
	"""
	The renewal radar as a lead calendar: open Tender Renewal Watch
	records whose predicted re-advertisement date falls within the next
	``months_ahead`` months, soonest first, plus per-buyer trust counters
	(hit rate over resolved predictions - counts, never probabilities)
	and the ledger's honesty caveats.

	Everything served here was computed deterministically from the
	renewal ledger by the sync (Ray's design: "keep a ledger, not a
	model") - this endpoint only reads state, it never predicts.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("get_renewal_radar", trace_id)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)

	if frappe.session.user == "Guest":
		frappe.throw("Please log in to view the renewal radar.", frappe.PermissionError)

	from {app_name}.tender.control.compliance.renewal import (
		add_months,
		buyer_trust,
		parse_iso_date,
	)

	months_ahead = max(1, cint(months_ahead) or 12)
	limit = min(max(1, cint(limit) or 100), MAX_LIMIT)
	today = parse_iso_date(nowdate())
	horizon = add_months(today, months_ahead)

	fields = [
		"name", "buyer", "buyer_normalized", "category", "anchor_ocid",
		"anchor_date", "source", "stated_duration_months", "predicted_date",
		"predicted_window_start", "predicted_window_end", "status",
	]
	open_watches = frappe.get_all(
		"Tender Renewal Watch",
		filters={"status": "open"},
		fields=fields,
		order_by="predicted_date asc, name asc",
	)
	resolved = frappe.get_all(
		"Tender Renewal Watch",
		filters={"status": ("in", ("confirmed", "missed"))},
		fields=["buyer_normalized", "status", "error_days"],
	)
	trust = buyer_trust(resolved)

	watches = []
	for watch in open_watches:
		predicted = parse_iso_date(watch.get("predicted_date"))
		if predicted is None or predicted > horizon:
			continue
		row = {key: (str(watch.get(key)) if watch.get(key) is not None else None)
			for key in fields}
		row["stated_duration_months"] = cint(watch.get("stated_duration_months")) or None
		row["trust"] = trust.get(str(watch.get("buyer_normalized") or ""))
		watches.append(row)
		if len(watches) >= limit:
			break

	confirmed_total = sum(1 for w in resolved if w.get("status") == "confirmed")
	missed_total = len(resolved) - confirmed_total
	return {
		"watches": watches,
		"trust": trust,
		"summary": {
			"open_total": len(open_watches),
			"upcoming": len(watches),
			"months_ahead": months_ahead,
			"confirmed_total": confirmed_total,
			"missed_total": missed_total,
		},
		"semantics": (
			"deterministic lead calendar recomputed from the renewal ledger "
			"(observed adverts, stated durations, median cycles, counter-based "
			"trust) - no model, no probabilities, never a certainty"
		),
		"caveats": list(RADAR_CAVEATS),
		"generated_on": str(nowdate()),
	}
