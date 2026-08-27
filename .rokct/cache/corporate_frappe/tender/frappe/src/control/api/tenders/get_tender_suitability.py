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


OPPORTUNITY_TYPES = ("tenders", "grants", "equity")

# Profile fields snapshotted for the pure scorer (a plain dict, so the
# scoring engine stays frappe-free and standalone-testable).
PROFILE_SNAPSHOT_FIELDS = (
	"csd_maaa_number",
	"tcs_pin",
	"company_registration_no",
	"vat_number",
	"enterprise_type",
	"bbbee_level",
	"bbbee_certificate_expiry",
	"cidb_grade",
	"operating_sectors",
	"operating_provinces",
	"briefing_travel_radius",
)

# Check-field readiness evidence (merged suitability model): snapshotted as
# "1"/"" so the pure scorer's _has_evidence never mistakes 0 for evidence.
PROFILE_SNAPSHOT_CHECK_FIELDS = (
	"coida_good_standing",
	"municipal_rates_current",
	"psira_registered",
	"nhbrc_registered",
	"track_record_evidence",
)


def profile_snapshot(doc):
	"""Flattens a Tender Business Profile doc for the pure scorer."""
	snapshot = {}
	for fieldname in PROFILE_SNAPSHOT_FIELDS:
		value = doc.get(fieldname)
		snapshot[fieldname] = str(value) if value not in (None, "") else ""
	for fieldname in PROFILE_SNAPSHOT_CHECK_FIELDS:
		snapshot[fieldname] = "1" if cint(doc.get(fieldname)) else ""
	snapshot["capability_texts"] = [
		" ".join(str(part) for part in (row.get("label"), row.get("detail")) if part)
		for row in (doc.get("capabilities") or [])
	]
	return snapshot


@frappe.whitelist()
def get_tender_suitability(slug: str, opportunity_type: str = "tenders") -> dict:
	"""
	Rates one opportunity (tender / grant / equity card) against the caller's
	Tender Business Profile: two-stage worth-bidding triage - hard gates
	(band no_bid, no numeric score, all firing reasons) then a deterministic
	0-100 fit score renormalised over known factors, with a band
	(strong / review / marginal / poor / no_bid), a confidence flag
	(pack_verified / advert_only) and machine-readable reasons per factor
	(FEEDBACK.md section 1.2 - automated suitability scoring).

	Enrichment-derived requirement lines feed the scorer ONLY for entitled
	subscribers (same never-leak rule as get_tender_detail); everyone else
	gets an advert-level score with enrichment_used=False.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("get_tender_suitability", trace_id)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)

	if frappe.session.user == "Guest":
		frappe.throw("Please log in to check your fit for this opportunity.", frappe.PermissionError)

	if opportunity_type not in OPPORTUNITY_TYPES:
		log_api_call(
			"get_tender_suitability", trace_id,
			note=f"bad opportunity_type={opportunity_type!r}",
		)
		frappe.throw("Unknown opportunity type. Try tenders, grants or equity.")

	from {app_name}.tender.control.api.opportunity_utils import get_cached_opportunities
	from {app_name}.tender.control.api.tenders.tender_entitlement import (
		find_tender_by_slug,
		get_enrichment_for_slug,
		get_tender_entitlement,
	)
	from {app_name}.tender.control.compliance.rules import get_scoring_rule, load_rules
	from {app_name}.tender.control.compliance.suitability import score_suitability

	# ---- the caller's business profile (friendly error when missing) ----
	profile_name = frappe.db.get_value(
		"Tender Business Profile", {"user": frappe.session.user}, "name"
	)
	if not profile_name:
		log_api_call(
			"get_tender_suitability", trace_id,
			note=f"no Tender Business Profile for user={frappe.session.user}",
		)
		frappe.throw(
			"Set up your business profile first - it holds the registration details "
			"this check scores against.",
			title="Business Profile Needed",
		)
	profile = profile_snapshot(frappe.get_doc("Tender Business Profile", profile_name))

	# ---- the opportunity card ----
	if opportunity_type == "tenders":
		card = find_tender_by_slug(slug)
	else:
		card = None
		for item in get_cached_opportunities(opportunity_type) or []:
			if item.get("slug") == slug:
				card = item
				break
	if not card:
		frappe.throw(f"Opportunity not found: {slug}", frappe.DoesNotExistError)
	card = card.copy()
	card.pop("advanced_enrichment", None)

	# ---- enrichment only for entitled callers (never leaks) ----
	entitlement = get_tender_entitlement()
	enrichment_entry = None
	if opportunity_type == "tenders" and entitlement["entitled"]:
		enrichment_entry = get_enrichment_for_slug(slug)

	rules_list = load_rules() if opportunity_type == "tenders" else []
	functionality_params = get_scoring_rule("SCORE-FUNCTIONALITY")

	result = score_suitability(
		card,
		profile,
		rules_list=rules_list,
		enrichment_entry=enrichment_entry,
		functionality_params=functionality_params,
		opportunity_type=opportunity_type,
		today=nowdate(),
	)

	result.update(
		{
			"slug": card.get("slug") or slug,
			"title": card.get("title"),
			"institution": card.get("institution") or card.get("organization"),
			"closing_date": card.get("closing_date") or card.get("deadline"),
			"enrichment_used": bool(enrichment_entry),
			"entitled": entitlement["entitled"],
			"entitlement_reason": entitlement["reason"],
		}
	)
	return result
