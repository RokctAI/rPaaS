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
import json
from frappe.utils import cint

try:
	from {app_name}.tender.control.api.telemetry import log_api_call
except Exception:  # standalone verify-suite load: no composed package to import from

	def log_api_call(endpoint, trace_id=None, **fields):
		"""Legacy stderr fallback, format-identical to the old print lines."""
		extras = "".join(f" {key}={value}" for key, value in fields.items())
		print(f"[tender.api] {endpoint}{extras} trace_id={trace_id}", file=sys.stderr)


@frappe.whitelist(allow_guest=True)
def get_relevant_tenders(
	filters: str | dict | None = None,
	personalized: int | str = 0,
	profile_user: str | None = None,
) -> list:
	"""
	An internal API endpoint for tenant sites to fetch relevant tenders
	from the opportunities repository.

	:param filters: A JSON string of filters to apply (e.g., '{"category": "IT"}')
	:param personalized: OPT-IN preference-aware delivery. When truthy, the
		caller's Tender Business Profile (resolved from the authenticated
		session user, or - for tenant-secret guest calls - from the tenant
		site's Company Subscription -> company linkage) filters and ranks
		the passthrough: cards whose province explicitly mismatches the
		declared operating provinces are dropped (national / unspecified
		always kept), the rest rank by deterministic sector match and carry
		an additive ``preference_fit`` annotation. Callers that do not opt
		in get EXACTLY the legacy passthrough - byte-identical responses.
	:param profile_user: With ``personalized``, lets an ADMIN caller
		(Administrator / System Manager) personalize for a named profile
		user. Non-admin authenticated callers always get their own profile;
		guest (tenant-secret) callers may never name one - the tenant
		linkage is the only identity a tenant call has.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("get_relevant_tenders", trace_id)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)

	from {app_name}.tender.control.api.opportunity_utils import get_opportunities_from_json, validate_tenant_secret

	validate_tenant_secret()
	items = get_opportunities_from_json("tenders", filters)
	if not cint(personalized):
		# Legacy path: no profile involvement whatsoever - the pre-existing
		# passthrough, byte-identical (SDK backward-compat rule).
		return items

	profile = _resolve_caller_profile(profile_user)
	if profile is None:
		# Opted in but no resolvable profile: serve the legacy passthrough
		# rather than failing the daily sync - personalization is a layer,
		# never a gate on delivery.
		log_api_call(
			"get_relevant_tenders", trace_id,
			note="personalized=1 but no profile resolved - serving unpersonalized passthrough",
		)
		return items

	from {app_name}.tender.control.compliance.preference_delivery import personalize_tenders

	return personalize_tenders(items, profile)


def _resolve_caller_profile(profile_user=None):
	"""Resolves the caller's Tender Business Profile snapshot, or None.

	- Authenticated callers: their own profile (``user`` link). Only
	  Administrator / System Manager may name a different ``profile_user``.
	- Guest callers passed ``validate_tenant_secret``, so their identity IS
	  the tenant site: X-Rokct-Tenant (or host) -> Company Subscription
	  (``site_name``) -> ``company`` -> Tender Business Profile
	  (``company``). Naming ``profile_user`` from a tenant call is refused
	  outright - a tenant must never read another subscriber's preferences.
	"""
	from {app_name}.tender.control.api.tenders.get_tender_suitability import profile_snapshot

	user = frappe.session.user
	if user != "Guest":
		if profile_user and profile_user != user:
			roles = frappe.get_roles(user)
			if user != "Administrator" and "System Manager" not in roles:
				frappe.throw(
					"Only administrators may personalize for another profile user.",
					frappe.PermissionError,
				)
		else:
			profile_user = user
		profile_name = frappe.db.get_value(
			"Tender Business Profile", {"user": profile_user}, "name"
		)
		if not profile_name:
			return None
		return profile_snapshot(frappe.get_doc("Tender Business Profile", profile_name))

	if profile_user:
		frappe.throw(
			"Tenant calls cannot personalize for a named profile user.",
			frappe.PermissionError,
		)
	request = getattr(frappe.local, "request", None)
	tenant_site = None
	if request is not None:
		tenant_site = request.headers.get("X-Rokct-Tenant") or request.host
	if not tenant_site:
		return None
	company = frappe.db.get_value(
		"Company Subscription", {"site_name": tenant_site}, "company"
	)
	if not company:
		return None
	profiles = frappe.get_all(
		"Tender Business Profile",
		filters={"company": company},
		fields=["name"],
		order_by="name asc",
		limit=1,
	)
	if not profiles:
		return None
	return profile_snapshot(frappe.get_doc("Tender Business Profile", profiles[0]["name"]))
