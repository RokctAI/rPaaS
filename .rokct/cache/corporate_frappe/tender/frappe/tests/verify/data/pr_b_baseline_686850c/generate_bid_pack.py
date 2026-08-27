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


@frappe.whitelist()
def generate_bid_pack(bid: str, sign: int = 0) -> dict:
	"""
	Builds the ready-to-print document pack for one of the caller's Tender
	Bids: the bid's form regime selects the returnable forms, each form is
	pre-filled from the caller's Tender Business Profile and the bid's cached
	tender data, and every tender-specific field renders as a clearly marked
	blank with kill-note guidance. Deterministic - fixtures and stored data
	in, HTML out, no AI.

	``sign=1`` stamps the profile's background-stripped signature/initials
	images into the placement slots (the deliberate second step of the
	review-then-sign flow); the default output is the unsigned review pack
	with "Sign here" / "Initial here" markers. Commissioner-of-oaths slots
	are never stamped.

	Returns {"manifest": {...}, "html": "<!DOCTYPE html>..."} - the manifest
	carries fill coverage, unresolved fields and any open fatal gates (a bid
	with open fatal gates gets a prominent warning page, never a silent pass).
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	print(f"[tender.api] generate_bid_pack bid={bid} trace_id={trace_id}", file=sys.stderr)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)
	if frappe.session.user == "Guest":
		frappe.throw("Please log in to generate a bid pack.", frappe.PermissionError)

	from {app_name}.tender.control.api.tenders.tender_entitlement import get_owned_bid
	from {app_name}.tender.control.pack_builder import build_pack, render_pack_html
	from {app_name}.tender.control.compliance.submission_gate import validate_submission_readiness

	bid_doc = get_owned_bid(bid)
	regime = load_regime(bid_doc)
	profile_doc, profile_values = load_profile(bid_doc.user)
	bid_ctx = build_bid_context(bid_doc)
	templates = load_templates()
	gate_failures = validate_submission_readiness(bid_doc)
	signing = build_signing_payload(profile_doc, cint(sign), bid_doc.get("institution"))

	pack = build_pack(regime, templates, profile_values, bid_ctx, gate_failures, signing)
	html = render_pack_html(pack, bid_ctx, signing)
	return {"manifest": pack["manifest"], "html": html}


def load_regime(bid_doc) -> dict:
	"""Loads the bid's Tender Form Regime (with its ordered form rows).

	When the bid also carries an ``overlay_regime`` (F-01: e.g. RNM's Mgodlwa
	Bridge pack demands the MBD declaration spread AND the CIDB C1.1/T2.x/H&S
	overlay in ONE submission), the two regimes merge into one pack: forms are
	the base rows followed by the overlay rows, deduped by form_code with the
	BASE row winning (stable, deterministic order), and the regime code/name
	join with "+" so the cover and manifest show both. A bid without an
	overlay returns exactly what it always did.
	"""
	if not bid_doc.get("regime"):
		frappe.throw(
			"Set the Form Regime on this bid first (SBD, MBD, SOE, CIDB or RFQ) - "
			"the regime decides which returnable forms the pack contains. It is a "
			"manual selection read from the tender pack, never inferred.",
			title="No Form Regime",
		)
	regime_doc = frappe.get_doc("Tender Form Regime", bid_doc.regime)
	regime = {
		"regime_code": regime_doc.regime_code,
		"regime_name": regime_doc.regime_name,
		"forms": [_form_row(row) for row in regime_doc.forms],
	}
	if not bid_doc.get("overlay_regime"):
		return regime

	overlay_doc = frappe.get_doc("Tender Form Regime", bid_doc.overlay_regime)
	seen_codes = {form["form_code"] for form in regime["forms"]}
	for row in overlay_doc.forms:
		if row.form_code in seen_codes:
			continue  # dedupe by form_code - the base regime's row wins
		seen_codes.add(row.form_code)
		regime["forms"].append(_form_row(row))
	regime["base_regime_code"] = regime_doc.regime_code
	regime["overlay_regime_code"] = overlay_doc.regime_code
	regime["regime_code"] = f"{regime_doc.regime_code}+{overlay_doc.regime_code}"
	regime["regime_name"] = f"{regime_doc.regime_name} + {overlay_doc.regime_name}"
	return regime


def _form_row(row) -> dict:
	"""One Tender Form Requirement child row as the builder's plain dict."""
	return {
		"form_code": row.form_code,
		"form_name": row.form_name,
		"mandatory": row.mandatory,
		"kill_note": row.kill_note,
	}


def load_profile(user):
	"""Loads the user's Tender Business Profile as (doc, fill-value dict).

	No profile yet -> (None, {}): the pack still generates, with every
	profile-sourced field marked as a gap pointing the user at the profile.
	"""
	name = frappe.db.get_value("Tender Business Profile", {"user": user}, "name")
	if not name:
		return None, {}
	doc = frappe.get_doc("Tender Business Profile", name)

	from {app_name}.tender.doctype.tender_business_profile.tender_business_profile import (
		FILL_FIELDS,
	)

	values = {}
	for fieldname in FILL_FIELDS:
		if fieldname == "directors":
			values[fieldname] = [
				{
					"full_name": row.full_name,
					"id_number": row.id_number,
					"position": row.position,
					"tax_reference_no": row.tax_reference_no,
					"in_state_service": row.in_state_service,
					"persal_number": row.persal_number,
				}
				for row in (doc.get("directors") or [])
			]
		else:
			value = doc.get(fieldname)
			values[fieldname] = str(value) if value not in (None, "") else None
	return doc, values


def build_bid_context(bid_doc) -> dict:
	"""Bid + cached-tender values the templates can auto-fill from."""
	from {app_name}.tender.control.api.tenders.tender_entitlement import find_tender_by_slug

	tender = None
	try:
		tender = find_tender_by_slug(bid_doc.tender_slug)
	except Exception:
		tender = None  # catalog cache unavailable - bid fields still fill
	tender = tender or {}

	def first(*values):
		for value in values:
			if value not in (None, ""):
				return str(value)
		return None

	pricing = load_quotation_pricing(bid_doc)

	return {
		"quotation": (pricing or {}).get("reference"),
		"pricing_lines": (pricing or {}).get("lines"),
		"pricing_total": (pricing or {}).get("total"),
		"bid_name": bid_doc.name,
		"tender_slug": bid_doc.tender_slug,
		"tender_title": first(bid_doc.get("tender_title"), tender.get("title")),
		"institution": first(bid_doc.get("institution"), tender.get("institution")),
		"closing_date": first(bid_doc.get("closing_date"), tender.get("closing_date")),
		"tender_number": first(
			tender.get("tender_number"), tender.get("ocid"), bid_doc.tender_slug
		),
		"ocid": first(tender.get("ocid")),
		"estimated_value": first(bid_doc.get("estimated_value")),
		"preference_system": first(bid_doc.get("preference_system")),
		"regime": first(bid_doc.get("regime")),
		"overlay_regime": first(bid_doc.get("overlay_regime")),
		"generated_on": nowdate(),
	}


def load_quotation_pricing(bid_doc):
	"""Deterministic pricing fill from a linked erp Quotation - SOFT link.

	The erp module (forked ERPNext in the pay repo) is optional at compose
	time, so every step is guarded: no Quotation doctype on this bench, no
	linked name, or a dangling name all return None and the pricing schedule
	falls back to its marked USER INPUT blanks. Never a hard dependency.
	"""
	name = bid_doc.get("quotation")
	if not name:
		return None
	if not frappe.db.exists("DocType", "Quotation"):
		return None
	if not frappe.db.exists("Quotation", name):
		return None

	doc = frappe.get_doc("Quotation", name)
	lines = []
	for row in doc.get("items") or []:
		lines.append(
			{
				"item": row.get("item_code") or row.get("item_name"),
				"description": row.get("item_name") or row.get("description"),
				"qty": row.get("qty"),
				"uom": row.get("uom"),
				"rate": row.get("rate"),
				"amount": row.get("amount"),
			}
		)
	total = doc.get("grand_total") or doc.get("total")
	return {
		"reference": name,
		"lines": lines or None,
		"total": str(total) if total not in (None, "") else None,
	}


def load_templates() -> dict:
	"""All Tender Form Templates keyed by template_code, with field rows."""
	templates = {}
	for name in frappe.get_all("Tender Form Template", pluck="name"):
		doc = frappe.get_doc("Tender Form Template", name)
		templates[doc.template_code] = {
			"template_code": doc.template_code,
			"form_title": doc.form_title,
			"guide_ref": doc.guide_ref,
			"instructions": doc.instructions,
			"initial_every_page": doc.initial_every_page,
			"fields_table": [
				{
					"section": row.section,
					"field_label": row.field_label,
					"source_type": row.source_type,
					"source_field": row.source_field,
					"signature_role": row.get("signature_role"),
					"multiline": row.multiline,
					"guidance": row.guidance,
				}
				for row in doc.fields_table
			],
		}
	return templates


def build_signing_payload(profile_doc, sign, institution) -> dict:
	"""Signing data for the renderer; stamping only on an explicit sign=1.

	The stamped scan is equivalent to sign-then-scan for any ONLINE
	submission. The wet-ink warning fires ONLY from buyer data: buyers whose
	packs are hard-copy(-governs) AND demand original ink signatures on the
	physical pack (KILL-25 params.wet_ink_hard_copy_patterns - both facts
	hold for every listed buyer). Unknown buyer -> no warning.
	"""
	if not sign:
		return {"sign": False}
	if not profile_doc:
		frappe.throw(
			"Create your Tender Business Profile (with a signature image) before "
			"generating a signed pack.",
			title="No Business Profile",
		)
	if not profile_doc.get("signature_image_processed") and not profile_doc.get("signature_image"):
		frappe.throw(
			"Upload a signature image on your Tender Business Profile first - "
			"sign in dark ink on plain WHITE paper and photograph/scan squarely.",
			title="No Signature Image",
		)

	return {
		"sign": True,
		"signatory_name": profile_doc.get("authorized_signatory_name"),
		"signatory_capacity": profile_doc.get("authorized_signatory_capacity"),
		"signatory_id": profile_doc.get("authorized_signatory_id_number"),
		"signature_url": profile_doc.get("signature_image_processed")
		or profile_doc.get("signature_image"),
		"initials_url": profile_doc.get("initials_image_processed")
		or profile_doc.get("initials_image"),
		"witnesses": [
			{
				"full_name": row.full_name,
				"id_number": row.id_number,
				"capacity": row.capacity,
				"signature_url": row.signature_image_processed or row.signature_image,
			}
			for row in (profile_doc.get("witnesses") or [])
		],
		"ink_warning": get_ink_warning(institution),
	}


def get_ink_warning(institution):
	"""Wet-ink instruction when buyer data says hard copy + original ink."""
	if not institution:
		return None

	from {app_name}.tender.control.compliance.rules import parse_json_field, text_matches_any

	if not frappe.db.exists("Tender Compliance Rule", "KILL-25"):
		return None
	params = parse_json_field(frappe.db.get_value("Tender Compliance Rule", "KILL-25", "params"))
	patterns = params.get("wet_ink_hard_copy_patterns") or []
	if text_matches_any(institution, patterns):
		return (
			"This buyer requires the physical pack signed in ORIGINAL INK "
			"(hard-copy submission governs) - print this pack and sign/initial "
			"by hand before delivering; the stamped scan is not acceptable on "
			"the physical pack."
		)
	return None
