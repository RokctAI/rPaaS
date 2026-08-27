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


MAX_LIMIT = 200

# The honesty layer, carried on every response so no client renders the
# finder as a win predictor.
FINDER_CAVEATS = [
	"field narrowness is computed deterministically from PUBLIC requirements "
	"only - it describes how many firms can qualify to bid, NEVER a win "
	"probability",
	"a narrow field can still contain an entrenched incumbent - narrowness "
	"says nothing about who wins among the firms that qualify",
	"advert-only cards can hide narrowing requirements that only the tender "
	"pack states - collect the pack before relying on the tier",
	"requirement checks here mirror the profile gates; run the full "
	"suitability check (get_tender_suitability) before committing to a bid",
]


@frappe.whitelist()
def get_low_competition_tenders(min_tier: str = "narrow", limit: int = 25) -> dict:
	"""
	Low-competition tender finder: iterates the published opportunities
	catalog, scores each card's FIELD NARROWNESS deterministically from
	public requirements (required CIDB grade, EME/QSE set-asides, B-BBEE
	prequalification, compulsory briefings - extra when non-metro, short
	submission windows, local-content demands), crosses the narrow ones
	with the caller's Tender Business Profile (the caller must actually
	CLEAR the narrowing requirements), and returns the caller's ranked
	opportunities with human-readable reasons.

	Enrichment-derived requirement lines feed the extraction ONLY for
	entitled subscribers (same never-leak rule as get_tender_suitability);
	everyone else is scored from the advert surface alone. Describes the
	field, never a win probability.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("get_low_competition_tenders", trace_id)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)

	if frappe.session.user == "Guest":
		frappe.throw("Please log in to find low-competition tenders.", frappe.PermissionError)

	from {app_name}.tender.control.api.opportunity_utils import get_cached_opportunities
	from {app_name}.tender.control.api.tenders.get_tender_suitability import profile_snapshot
	from {app_name}.tender.control.api.tenders.tender_entitlement import (
		get_enrichment_for_slug,
		get_tender_entitlement,
	)
	from {app_name}.tender.control.compliance.competition import (
		TIER_ORDER,
		assess_low_competition,
		enrichment_task_texts,
	)

	if min_tier not in TIER_ORDER:
		frappe.throw(
			"Unknown narrowness tier. Try one of: {0}.".format(", ".join(TIER_ORDER))
		)
	limit = min(max(1, cint(limit) or 25), MAX_LIMIT)
	min_rank = TIER_ORDER.index(min_tier)

	# ---- the caller's business profile (friendly error when missing) ----
	profile_name = frappe.db.get_value(
		"Tender Business Profile", {"user": frappe.session.user}, "name"
	)
	if not profile_name:
		log_api_call(
			"get_low_competition_tenders", trace_id,
			note=f"no Tender Business Profile for user={frappe.session.user}",
		)
		frappe.throw(
			"Set up your business profile first - the finder checks the narrowing "
			"requirements against it.",
			title="Business Profile Needed",
		)
	profile = profile_snapshot(frappe.get_doc("Tender Business Profile", profile_name))

	# ---- enrichment only for entitled callers (never leaks) ----
	entitlement = get_tender_entitlement()
	today = nowdate()

	opportunities = []
	scanned = 0
	for card in get_cached_opportunities("tenders") or []:
		scanned += 1
		slug = card.get("slug") or card.get("tender_number")
		enrichment_entry = None
		if entitlement["entitled"] and slug:
			enrichment_entry = get_enrichment_for_slug(slug)
		assessment = assess_low_competition(
			card,
			profile,
			task_texts=enrichment_task_texts(enrichment_entry),
			today=today,
		)
		if assessment["closed"]:
			continue
		tier_rank = TIER_ORDER.index(assessment["narrowness"]["tier"])
		if tier_rank < min_rank:
			continue
		if not assessment["requirements"]["meets_narrowing_requirements"]:
			continue
		assessment["enrichment_used"] = bool(enrichment_entry)
		opportunities.append(assessment)

	# Narrowest field first; ties break on soonest close, then slug -
	# fully deterministic ordering.
	opportunities.sort(
		key=lambda item: (
			-item["narrowness"]["score"],
			item["days_to_close"] if item["days_to_close"] is not None else 10**6,
			str(item["slug"] or ""),
		)
	)
	total_matching = len(opportunities)
	opportunities = opportunities[:limit]

	return {
		"opportunities": opportunities,
		"summary": {
			"scanned": scanned,
			"matching": total_matching,
			"returned": len(opportunities),
			"min_tier": min_tier,
		},
		"entitled": entitlement["entitled"],
		"entitlement_reason": entitlement["reason"],
		"semantics": (
			"deterministic field-narrowness ranking from public requirements "
			"crossed with the caller's own profile - describes how narrow the "
			"field of qualifying firms is, never who wins; no model, no "
			"probabilities"
		),
		"caveats": list(FINDER_CAVEATS),
		"generated_on": str(today),
	}
