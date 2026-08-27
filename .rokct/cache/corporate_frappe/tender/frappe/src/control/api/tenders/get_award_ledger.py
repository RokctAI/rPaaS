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

import json
import sys

import frappe
from frappe.utils import nowdate

try:
	from {app_name}.tender.control.api.telemetry import log_api_call
except Exception:  # standalone verify-suite load: no composed package to import from

	def log_api_call(endpoint, trace_id=None, **fields):
		"""Legacy stderr fallback, format-identical to the old print lines."""
		extras = "".join(f" {key}={value}" for key, value in fields.items())
		print(f"[tender.api] {endpoint}{extras} trace_id={trace_id}", file=sys.stderr)


@frappe.whitelist()
def get_award_ledger() -> dict:
	"""
	The award-outcome ledger for the logged-in user (plan #12), two halves:

	(i) aggregate counters over their OWN Tender Bids - win rate over
	decided bids only, per-buyer counters, quoted-vs-awarded value deltas
	placed against the pricing bands they were shown. Per-subscriber
	PRIVATE data, scoped to the session user exactly like get_my_bids.

	(ii) published-award matches: the claimed tenders' ocids joined
	against the re-fetched compiled OCDS releases in Raw Tender Cache
	(tasks.py's ingester re-fetches a trailing id window because awards
	land on later re-fetch), recording who actually won even when the
	user never updates their bid. Non-empty awards[] is the ONLY award
	signal; "no award published" is NEVER served as "lost", and the bid
	status is never auto-flipped.

	All aggregation is deterministic and pure (compliance/award_ledger.py);
	this endpoint only scopes, reads state, and assembles. The research
	bounds ride every payload as caveats: winner-side feed, buyer-skewed
	publication, 72.01% usable values, no award dates (release date is
	the proxy) - market-context-style calibration and the user's own
	record, NEVER a win probability.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("get_award_ledger", trace_id)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)

	if frappe.session.user == "Guest":
		frappe.throw("Please log in to view your award ledger.", frappe.PermissionError)

	from {app_name}.tender.control.compliance.award_ledger import (
		build_award_ledger,
		card_index,
		resolve_bid_ocid,
	)

	# Own-bids scoping (get_my_bids doctrine): only the session user's
	# records ever feed the ledger, and the payload only goes back to them.
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
			"estimated_value",
			"submitted_on",
			"outcome_value",
		],
		order_by="closing_date asc, name asc",
	)

	# Catalog cards (slug -> ocid resolution + pricing-band context) and the
	# market tables - both guarded: a cache or fixture hiccup degrades the
	# enrichment, never the ledger itself.
	cards = []
	tables = None
	try:
		from {app_name}.tender.control.api.opportunity_utils import (
			get_cached_opportunities,
		)

		cards = get_cached_opportunities("tenders") or []
	except Exception:
		cards = []
	try:
		from {app_name}.tender.control.compliance.market_context import (
			load_market_tables,
		)

		tables = load_market_tables()
	except Exception:
		tables = None

	# Re-fetched releases for the claimed ocids only (never a table scan):
	# Raw Tender Cache holds compiled releases the ingester keeps current
	# via its trailing re-fetch window.
	cards_by_key = card_index(cards)
	releases_by_ocid = {}
	for bid in bids:
		ocid = resolve_bid_ocid(bid, cards_by_key)
		if not ocid or ocid in releases_by_ocid:
			continue
		try:
			data = frappe.db.get_value("Raw Tender Cache", {"ocid": ocid}, "data")
			if data:
				release = json.loads(data)
				if isinstance(release, dict):
					releases_by_ocid[ocid] = release
		except Exception:
			continue  # a corrupt cache row degrades to "no release cached"

	ledger = build_award_ledger(bids, releases_by_ocid, cards=cards, tables=tables)
	ledger["generated_on"] = str(nowdate())
	return ledger
