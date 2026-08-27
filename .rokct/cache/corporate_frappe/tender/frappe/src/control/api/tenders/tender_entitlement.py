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

import frappe
from frappe.utils import cint

ACTIVE_STATUSES = ("Active", "Trialing")


def get_tender_entitlement(user=None):
	"""
	Resolves whether the given (or session) user's subscription plan has tender
	access (Subscription Plan.enable_tenders). Mirrors the user -> subscription
	resolution used by control.control.api.subscription.get_my_subscription:
	Hosting Client by email first, then the user's first linked Company.

	Returns a dict: {"entitled": bool, "reason": str, "plan": str | None}.
	Never throws — callers decide whether a lack of entitlement is an error.
	"""
	user = user or frappe.session.user

	if user == "Guest":
		return {"entitled": False, "reason": "not_logged_in", "plan": None}

	roles = frappe.get_roles(user)
	if user == "Administrator" or "System Manager" in roles:
		return {"entitled": True, "reason": "admin", "plan": None}

	user_doc = frappe.get_doc("User", user)
	subscription = None

	hosting_client = frappe.db.get_value("Hosting Client", {"email": user_doc.email}, "client_name")
	if hosting_client:
		subscription = frappe.db.get_value(
			"Company Subscription",
			{"customer": hosting_client, "status": ["!=", "Canceled"]},
			["name", "plan", "status"],
			as_dict=True,
		)

	if not subscription and user_doc.get("user_companies"):
		company_name = user_doc.user_companies[0].company
		if company_name:
			subscription = frappe.db.get_value(
				"Company Subscription",
				{"company": company_name, "status": ["!=", "Canceled"]},
				["name", "plan", "status"],
				as_dict=True,
			)

	if not subscription:
		return {"entitled": False, "reason": "no_subscription", "plan": None}

	plan = frappe.get_doc("Subscription Plan", subscription.plan)
	enabled = cint(getattr(plan, "enable_tenders", 0))
	active = subscription.status in ACTIVE_STATUSES

	if not enabled:
		return {"entitled": False, "reason": "plan_excludes_tenders", "plan": subscription.plan}
	if not active:
		return {"entitled": False, "reason": "subscription_inactive", "plan": subscription.plan}

	return {"entitled": True, "reason": "plan", "plan": subscription.plan}


def parse_enrichment_task(raw):
	"""
	Enrichment tasks are published as "task text | N" (N = effort/priority
	weight); global defaults may be bare strings. Returns {task_text, weight}.
	"""
	text = raw if isinstance(raw, str) else str(raw)
	weight = 0
	head, sep, tail = text.rpartition("|")
	if sep and tail.strip().isdigit():
		text = head
		weight = int(tail.strip())
	return {"task_text": text.strip(), "weight": weight}


def get_enrichment_for_slug(slug):
	"""
	Returns the advanced_enrichment entry for a tender slug from the cached
	published meta.json, or None if the tender has no advanced enrichment.
	"""
	from {app_name}.tender.control.api.opportunity_utils import get_cached_opportunities

	meta = get_cached_opportunities("meta") or {}
	enrichment = meta.get("advanced_enrichment")
	if not isinstance(enrichment, dict):
		return None
	entry = enrichment.get(slug)
	if not isinstance(entry, dict) or not entry.get("tasks"):
		return None
	return entry


def get_generic_default_tasks():
	"""
	Returns the generic fallback task list from meta.json. Handles both
	published shapes: a flat list of strings (current), or the older
	{slug: {tasks: [...]}} dict plus generic_defaults.tasks.
	"""
	from {app_name}.tender.control.api.opportunity_utils import get_cached_opportunities

	meta = get_cached_opportunities("meta") or {}
	defaults = meta.get("global_defaults")
	if isinstance(defaults, list):
		return defaults
	generic = meta.get("generic_defaults") or {}
	if isinstance(generic, dict) and generic.get("tasks"):
		return generic["tasks"]
	return ["Review Tender Documents", "Prepare Initial Response"]


def find_tender_by_slug(slug):
	"""Finds a tender item in the cached published tenders.json by slug/tender_number."""
	from {app_name}.tender.control.api.opportunity_utils import get_cached_opportunities

	for item in get_cached_opportunities("tenders") or []:
		if item.get("slug") == slug or item.get("tender_number") == slug:
			return item
	return None


def get_owned_bid(bid_name):
	"""Loads a Tender Bid and asserts the session user owns it."""
	bid = frappe.get_doc("Tender Bid", bid_name)
	if bid.user != frappe.session.user:
		frappe.throw("You do not have access to this bid.", frappe.PermissionError)
	return bid
