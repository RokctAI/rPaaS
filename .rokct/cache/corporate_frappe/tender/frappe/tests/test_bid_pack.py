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

"""Bid-pack generator tests: fill mapping, USER_INPUT marking, fatal-gate
warning inclusion, regime -> form selection, signing/stamping behavior, the
signature background-strip pipeline, and form-template fixture integrity.
Pure-builder tests use plain dicts (the builder never touches frappe);
imports use the `{app_name}` template placeholder, so this suite runs on a
composed bench like the other suites.
"""

import io
import json
import os

from frappe.tests.utils import FrappeTestCase

from {app_name}.tender.control.pack_builder import (
	OFFICIAL_FORMS_WARNING,
	build_form,
	build_pack,
	is_filled,
	render_pack_html,
	resolve_field,
)
from {app_name}.tender.doctype.tender_business_profile.tender_business_profile import (
	FILL_FIELDS,
)
from {app_name}.tender.control.imaging.signature_stamp import strip_background

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")

# Keys build_bid_context() in generate_bid_pack.py exposes to templates -
# the fixture-integrity test pins every "Bid Field" mapping to this set.
BID_CONTEXT_KEYS = {
	"bid_name",
	"tender_slug",
	"tender_title",
	"institution",
	"closing_date",
	"tender_number",
	"ocid",
	"estimated_value",
	"preference_system",
	"regime",
	# wave-2 (findings F-01): the optional second form-set overlay
	"overlay_regime",
	# wave-2 (findings F-06): multi-year term, escalation and the
	# year-by-year pricing grid (a list; renders only when rows exist)
	"contract_term_months",
	"escalation_provision",
	"escalation_rate_pct",
	"pricing_periods",
	"generated_on",
	# soft erp-quotation pricing (None when the erp module is not composed)
	"quotation",
	"pricing_lines",
	"pricing_total",
}

SIGNATURE_ROLES = {"", "Signatory", "Witness 1", "Witness 2", "Commissioner of Oaths"}


def load_fixture(filename):
	with open(os.path.join(FIXTURES_DIR, filename), encoding="utf-8") as f:
		return json.load(f)


def stub_profile():
	return {
		"trading_name": "Sinyage Trading",
		"registered_name": "Sinyage Trading (Pty) Ltd",
		"company_registration_no": "2020/123456/07",
		"vat_number": None,  # deliberately missing -> profile gap
		"csd_maaa_number": "MAAA0123456",
		"tcs_pin": "ABCD1234",
		"enterprise_type": "EME (turnover under R10m - sworn affidavit)",
		"bbbee_level": "1",
		"bbbee_certificate_expiry": "2027-01-31",
		"cidb_grade": None,
		"physical_address": "12 Main Road, Polokwane",
		"postal_address": "PO Box 1, Polokwane",
		"contact_person": "R. Sinyage",
		"contact_phone": "015 000 0000",
		"contact_email": "bids@example.co.za",
		"authorized_signatory_name": "R. Sinyage",
		"authorized_signatory_capacity": "Director",
		"authorized_signatory_id_number": "8001015009087",
		"directors": [
			{
				"full_name": "R. Sinyage",
				"id_number": "8001015009087",
				"position": "Director",
				"tax_reference_no": "0123456789",
				"in_state_service": 0,
				"persal_number": None,
			}
		],
	}


def stub_bid_ctx():
	return {
		"bid_name": "BID-00001",
		"tender_slug": "ocds-test-1",
		"tender_title": "Supply of widgets",
		"institution": "Mogale City Local Municipality",
		"closing_date": "2026-09-30",
		"tender_number": "MC-2026-17",
		"ocid": "ocds-test-1",
		"estimated_value": "1200000",
		"preference_system": "80/20",
		"regime": "MBD",
		"generated_on": "2026-08-19",
		"quotation": None,
		"pricing_lines": None,
		"pricing_total": None,
	}


def stub_regime(codes=("F1", "F2")):
	return {
		"regime_code": "MBD",
		"regime_name": "Municipal (MBD forms)",
		"forms": [
			{"form_code": code, "form_name": f"Form {code}", "mandatory": 1, "kill_note": f"kill {code}"}
			for code in codes
		],
	}


def stub_template(code="F1", extra_fields=None):
	fields = [
		{"section": "Identity", "field_label": "Name of bidder", "source_type": "Profile Field",
		 "source_field": "trading_name", "signature_role": "", "multiline": 0, "guidance": ""},
		{"section": "Identity", "field_label": "VAT number", "source_type": "Profile Field",
		 "source_field": "vat_number", "signature_role": "", "multiline": 0, "guidance": ""},
		{"section": "Tender", "field_label": "Closing date", "source_type": "Bid Field",
		 "source_field": "closing_date", "signature_role": "", "multiline": 0, "guidance": ""},
		{"section": "Price", "field_label": "TOTAL BID PRICE", "source_type": "User Input",
		 "source_field": "", "signature_role": "", "multiline": 0, "guidance": "carry over exactly"},
		{"section": "Signature", "field_label": "Signature", "source_type": "Signature",
		 "source_field": "", "signature_role": "Signatory", "multiline": 0, "guidance": ""},
	]
	return {
		"template_code": code,
		"form_title": f"Template {code}",
		"guide_ref": "Guide 4.x",
		"instructions": "Fill every field.",
		"initial_every_page": 1,
		"fields_table": fields + (extra_fields or []),
	}


class TestFillMapping(FrappeTestCase):
	def test_profile_and_bid_resolution(self):
		profile, ctx = stub_profile(), stub_bid_ctx()
		row = resolve_field(
			{"field_label": "Name", "source_type": "Profile Field", "source_field": "trading_name"},
			profile, ctx,
		)
		self.assertEqual(row["value"], "Sinyage Trading")
		self.assertTrue(row["filled"])

		row = resolve_field(
			{"field_label": "Closing", "source_type": "Bid Field", "source_field": "closing_date"},
			profile, ctx,
		)
		self.assertEqual(row["value"], "2026-09-30")
		self.assertTrue(row["filled"])

		# missing profile value stays unfilled (a "profile gap")
		row = resolve_field(
			{"field_label": "VAT", "source_type": "Profile Field", "source_field": "vat_number"},
			profile, ctx,
		)
		self.assertFalse(row["filled"])

		# USER INPUT never auto-fills
		row = resolve_field({"field_label": "Price", "source_type": "User Input"}, profile, ctx)
		self.assertFalse(row["filled"])
		self.assertIsNone(row["value"])

	def test_is_filled_semantics(self):
		self.assertTrue(is_filled("x"))
		self.assertTrue(is_filled([{"a": 1}]))
		self.assertFalse(is_filled(""))
		self.assertFalse(is_filled("   "))
		self.assertFalse(is_filled(None))
		self.assertFalse(is_filled([]))

	def test_form_coverage_arithmetic(self):
		form = build_form(
			{"form_code": "F1", "form_name": "Form F1", "mandatory": 1, "kill_note": "k"},
			stub_template(), stub_profile(), stub_bid_ctx(),
		)
		# 3 auto fields (2 profile + 1 bid), of which vat_number is unfilled
		self.assertEqual(form["auto_total"], 3)
		self.assertEqual(form["auto_filled"], 2)
		self.assertEqual(form["user_input"], ["TOTAL BID PRICE"])
		self.assertEqual(form["missing_auto"], ["VAT number"])

	def test_missing_template_still_produces_a_page(self):
		form = build_form(
			{"form_code": "NEW", "form_name": "New Form", "mandatory": 0, "kill_note": "sign it"},
			None, stub_profile(), stub_bid_ctx(),
		)
		self.assertFalse(form["has_template"])
		self.assertEqual(form["auto_total"], 0)
		pack = build_pack(stub_regime(codes=("NEW",)), {}, stub_profile(), stub_bid_ctx(), [])
		html = render_pack_html(pack, stub_bid_ctx())
		self.assertIn("No field template exists", html)
		# the regime row's kill note still prints on the fallback page
		self.assertIn("kill NEW", html)


class TestPackAssembly(FrappeTestCase):
	def _pack(self, gate_failures=None, signing=None, regime=None, templates=None):
		regime = regime or stub_regime()
		templates = templates if templates is not None else {"F1": stub_template("F1"), "F2": stub_template("F2")}
		return build_pack(
			regime, templates, stub_profile(), stub_bid_ctx(), gate_failures or [], signing
		)

	def test_regime_selects_forms_in_order(self):
		pack = self._pack(regime=stub_regime(codes=("F2", "F1")))
		self.assertEqual([f["form_code"] for f in pack["forms"]], ["F2", "F1"])
		self.assertEqual(pack["manifest"]["form_count"], 2)

	def test_manifest_coverage_totals(self):
		manifest = self._pack()["manifest"]
		self.assertEqual(manifest["fill"]["auto_total"], 6)
		self.assertEqual(manifest["fill"]["auto_filled"], 4)
		self.assertEqual(manifest["fill"]["coverage_pct"], round(4 / 6 * 100.0, 1))
		self.assertEqual(manifest["fill"]["user_input_total"], 2)
		self.assertEqual(manifest["fill"]["missing_auto"], ["VAT number"])
		self.assertIn(OFFICIAL_FORMS_WARNING, manifest["warnings"])
		self.assertFalse(manifest["signed"])

	def test_user_input_marked_in_html(self):
		pack = self._pack()
		html = render_pack_html(pack, stub_bid_ctx())
		self.assertIn("To complete - tender-specific", html)
		self.assertIn("userinput", html)
		self.assertIn("carry over exactly", html)
		# auto-filled values land in the page
		self.assertIn("Sinyage Trading", html)
		self.assertIn("2026-09-30", html)
		# missing profile value is flagged, not silently blank
		self.assertIn("Not in your Business Profile", html)

	def test_fatal_gates_produce_warning_page_never_silent(self):
		failures = ["Fatal checklist item still open: CSD registration [GATE-CSD]"]
		pack = self._pack(gate_failures=failures)
		self.assertEqual(pack["manifest"]["open_fatal_gates"], failures)
		self.assertTrue(any("FATAL" in w for w in pack["manifest"]["warnings"]))
		html = render_pack_html(pack, stub_bid_ctx())
		self.assertIn("OPEN FATAL COMPLIANCE GATES", html)
		self.assertIn("GATE-CSD", html)

		clean = self._pack()
		self.assertNotIn("OPEN FATAL COMPLIANCE GATES", render_pack_html(clean, stub_bid_ctx()))

	def test_quotation_pricing_fills_when_linked_and_blanks_when_not(self):
		pricing_fields = [
			{"section": "Pricing", "field_label": "Priced line items", "source_type": "Bid Field",
			 "source_field": "pricing_lines", "signature_role": "", "multiline": 0, "guidance": ""},
			{"section": "Pricing", "field_label": "Quotation total", "source_type": "Bid Field",
			 "source_field": "pricing_total", "signature_role": "", "multiline": 0, "guidance": ""},
		]
		template = {"template_code": "PS", "form_title": "Pricing Schedule", "guide_ref": "",
			"instructions": "", "initial_every_page": 0, "fields_table": pricing_fields}
		regime = stub_regime(codes=("PS",))

		# no erp quotation linked/composed -> marked complete-by-hand, never an error
		ctx = stub_bid_ctx()
		pack = build_pack(regime, {"PS": template}, stub_profile(), ctx, [])
		html = render_pack_html(pack, ctx)
		self.assertIn("Not auto-filled - complete by hand", html)
		self.assertEqual(pack["manifest"]["fill"]["auto_filled"], 0)

		# linked quotation -> deterministic line-item table + total
		ctx = stub_bid_ctx()
		ctx["quotation"] = "SAL-QTN-0001"
		ctx["pricing_lines"] = [
			{"item": "WID-01", "description": "Widget", "qty": 10, "uom": "Nos",
			 "rate": 100.0, "amount": 1000.0},
		]
		ctx["pricing_total"] = "1000.0"
		pack = build_pack(regime, {"PS": template}, stub_profile(), ctx, [])
		self.assertEqual(pack["manifest"]["fill"]["auto_filled"], 2)
		html = render_pack_html(pack, ctx)
		self.assertIn("WID-01", html)
		self.assertIn("Rate (R)", html)
		self.assertIn("1000.0", html)

	def test_pricing_lines_render_on_mbd_and_cidb_fixture_packs(self):
		# wave-1 (findings F-10): pricing_lines is no longer SBD3.x-only -
		# the MBD regime carries its own Pricing Schedules worksheet and the
		# CIDB regime a priced C2.2 variant, both sourcing pricing_lines
		templates = {t["template_code"]: t for t in load_fixture("tender_form_templates.json")}
		for code in ("SBD3.x", "MBD3.x", "T2.x-PRICE"):
			sources = {f["source_field"] for f in templates[code]["fields_table"]}
			self.assertIn("pricing_lines", sources, code)
			self.assertIn("pricing_total", sources, code)

		regimes = {r["regime_code"]: r for r in load_fixture("tender_form_regimes.json")}
		ctx = stub_bid_ctx()
		ctx["quotation"] = "SAL-QTN-0002"
		ctx["pricing_lines"] = [
			{"item": "WEB-01", "description": "Website maintenance - Year 1", "qty": 12,
			 "uom": "Month", "rate": 36317.60, "amount": 435811.20},
		]
		ctx["pricing_total"] = "435811.20"
		for regime_code in ("MBD", "CIDB"):
			pack = build_pack(regimes[regime_code], templates, stub_profile(), ctx, [])
			html = render_pack_html(pack, ctx)
			self.assertIn("WEB-01", html, regime_code)
			self.assertIn("Rate (R)", html, regime_code)
			self.assertIn("435811.2", html, regime_code)

	def test_overlay_regime_union_renders_one_combined_pack(self):
		# wave-2 (findings F-01): an MBD bid with a CIDB overlay renders ONE
		# pack whose form set is the union - base rows first, overlay rows
		# appended, deduped by form_code with the base row winning (this
		# mirrors load_regime's merge, which feeds the builder a plain dict)
		regimes = {r["regime_code"]: r for r in load_fixture("tender_form_regimes.json")}
		templates = {t["template_code"]: t for t in load_fixture("tender_form_templates.json")}
		base, overlay = regimes["MBD"], regimes["CIDB"]
		merged = {
			"regime_code": "MBD+CIDB",
			"regime_name": f"{base['regime_name']} + {overlay['regime_name']}",
			"base_regime_code": "MBD",
			"overlay_regime_code": "CIDB",
			"forms": list(base["forms"]),
		}
		seen = {f["form_code"] for f in merged["forms"]}
		merged["forms"] += [f for f in overlay["forms"] if f["form_code"] not in seen]

		pack = build_pack(merged, templates, stub_profile(), stub_bid_ctx(), [])
		codes = [f["form_code"] for f in pack["forms"]]
		self.assertEqual(len(codes), len(set(codes)), "dedupe by form_code")
		self.assertEqual(len(codes), len(base["forms"]) + len(overlay["forms"]))
		for code in ("MBD4", "MBD6.1", "MBD8", "MBD9", "C1.1", "T2.x", "HS-PLAN"):
			self.assertIn(code, codes)
		# both pricing worksheets are genuinely returnable (RNM: Schedule A10
		# firm-price schedule AND the C2 BoQ) - no dedup of pricing pages
		self.assertIn("MBD3.x", codes)
		self.assertIn("T2.x-PRICE", codes)
		html = render_pack_html(pack, stub_bid_ctx())
		self.assertIn("MBD+CIDB", html)

	def test_preference_framework_conflict_warning_in_manifest(self):
		# wave-1 (findings F-12): a pack whose form set signals more than one
		# preference framework gets a manifest warning; the fixture regimes
		# (single-framework) never trip it
		conflicted = stub_regime(codes=("F1",))
		conflicted["forms"] = [
			{"form_code": "MBD6.1", "form_name": "Preference Points Claim Form (PPR 2022 specific goals)",
			 "mandatory": 1, "kill_note": ""},
			{"form_code": "FORM-C", "form_name": "Form C - HDI Equity Ownership claim (Points out of 20)",
			 "mandatory": 1, "kill_note": "Non-completion forfeits the preference."},
			{"form_code": "FORM-D", "form_name": "Form D - Local Content / SABS mark certificate (Local Government Ordinance, 1939)",
			 "mandatory": 1, "kill_note": "Non-completion forfeits the preference."},
		]
		pack = build_pack(conflicted, {}, stub_profile(), stub_bid_ctx(), [])
		self.assertTrue(
			any("conflicting preference frameworks" in w for w in pack["manifest"]["warnings"])
		)

		regimes = {r["regime_code"]: r for r in load_fixture("tender_form_regimes.json")}
		templates = {t["template_code"]: t for t in load_fixture("tender_form_templates.json")}
		for regime in regimes.values():
			pack = build_pack(regime, templates, stub_profile(), stub_bid_ctx(), [])
			self.assertFalse(
				any("conflicting preference frameworks" in w for w in pack["manifest"]["warnings"]),
				regime["regime_code"],
			)

	def test_multi_year_pricing_grid_renders_only_when_captured(self):
		# wave-2 (findings F-06): the pricing worksheets carry a
		# pricing_periods overlay row - a Musina-shaped 36-month bid renders
		# the Year 1/2/3 grid; a bid without periods skips the row entirely,
		# so single-year packs stay byte-identical to before the row existed
		templates = {t["template_code"]: t for t in load_fixture("tender_form_templates.json")}
		for code in ("SBD3.x", "MBD3.x", "T2.x-PRICE"):
			sources = {f["source_field"] for f in templates[code]["fields_table"]}
			self.assertIn("pricing_periods", sources, code)

		regimes = {r["regime_code"]: r for r in load_fixture("tender_form_regimes.json")}
		ctx = stub_bid_ctx()
		ctx["contract_term_months"] = "36"
		ctx["pricing_periods"] = [
			{"period_label": "Year 1", "once_off": 250000.0, "monthly": 55000.0,
			 "annual_total": 910000.0, "unit_tariff": None, "unit_label": None,
			 "escalation_applied_pct": None, "notes": None},
			{"period_label": "Per-unit call tariff", "once_off": None, "monthly": None,
			 "annual_total": None, "unit_tariff": 85.0, "unit_label": "per logged call",
			 "escalation_applied_pct": None, "notes": "variable - dependent on call activity"},
		]
		pack = build_pack(regimes["MBD"], templates, stub_profile(), ctx, [])
		html = render_pack_html(pack, ctx)
		self.assertIn("Year 1", html)
		self.assertIn("Once-Off (R)", html)
		self.assertIn("per logged call", html)

		# no periods captured -> the overlay row is skipped, output identical
		plain_ctx = stub_bid_ctx()
		plain_ctx["pricing_periods"] = None
		with_row = render_pack_html(
			build_pack(regimes["MBD"], templates, stub_profile(), plain_ctx, []), plain_ctx
		)
		stripped = {
			code: dict(t, fields_table=[
				f for f in t["fields_table"] if f["source_field"] != "pricing_periods"
			])
			for code, t in templates.items()
		}
		without_row = render_pack_html(
			build_pack(regimes["MBD"], stripped, stub_profile(), plain_ctx, []), plain_ctx
		)
		self.assertEqual(with_row, without_row)

	def test_custom_returnables_render_worksheets_and_resolve_template_codes(self):
		# wave-2 (findings F-02): buyer-authored returnables - rows without a
		# template render the guided template-less worksheet page (with the
		# desk's guidance as its instruction notice); rows naming a
		# template_code render that template's pre-filled worksheet
		templates = {t["template_code"]: t for t in load_fixture("tender_form_templates.json")}
		regime = {
			"regime_code": "MBD",
			"regime_name": "Municipal (MBD forms)",
			"forms": [
				{"form_code": "Form A", "form_name": "Form A - Certificate of Acquaintance",
				 "mandatory": 1, "kill_note": "Failure to complete will invalidate the bid.",
				 "template_code": None, "guidance": "Initial every page of the ToR.",
				 "category": "Buyer Form"},
				{"form_code": "Form B", "form_name": "Form B - Preference claim",
				 "mandatory": 1, "kill_note": "", "template_code": "MBD6.1",
				 "guidance": "", "category": "Buyer Form"},
				{"form_code": "5.1(i)", "form_name": "Company profile and organogram",
				 "mandatory": 1, "kill_note": "", "template_code": "ICT-CAPABILITY",
				 "guidance": "", "category": "Technical Returnable"},
			],
		}
		pack = build_pack(regime, templates, stub_profile(), stub_bid_ctx(), [])
		by_code = {f["form_code"]: f for f in pack["forms"]}
		self.assertFalse(by_code["Form A"]["has_template"])
		self.assertEqual(by_code["Form A"]["instructions"], "Initial every page of the ToR.")
		self.assertTrue(by_code["Form B"]["has_template"])
		self.assertEqual(by_code["Form B"]["form_name"], templates["MBD6.1"]["form_title"])
		self.assertTrue(by_code["5.1(i)"]["has_template"])
		html = render_pack_html(pack, stub_bid_ctx())
		self.assertIn("No field template exists", html)
		self.assertIn("Failure to complete will invalidate the bid.", html)
		self.assertIn("Capability Register", html)

	def test_studio_generated_returnable_renders_provenance(self):
		# findings F-15: the studio hook on captured returnables. A row naming
		# only its studio document scope renders the generate-via-studio
		# pointer (the hand-fill placeholder stays); a row carrying a
		# generated artifact renders SATISFIED provenance and drops the
		# placeholder; rows with neither stay byte-identical to before.
		def profile_regime(extra):
			row = {"form_code": "16", "form_name": "Company Profile", "mandatory": 1,
			       "kill_note": "", "template_code": None, "guidance": "",
			       "category": "Technical Returnable"}
			row.update(extra)
			return {"regime_code": "MBD", "regime_name": "Municipal (MBD forms)",
			        "forms": [row]}

		plain = render_pack_html(
			build_pack(profile_regime({}), {}, stub_profile(), stub_bid_ctx(), []),
			stub_bid_ctx(),
		)
		explicit_none = render_pack_html(
			build_pack(
				profile_regime({"studio_scope": None, "generated_artifact": None}),
				{}, stub_profile(), stub_bid_ctx(), [],
			),
			stub_bid_ctx(),
		)
		self.assertEqual(plain, explicit_none)
		self.assertNotIn("GENERATE VIA STUDIO", plain)
		self.assertNotIn("SATISFIED BY GENERATED ARTIFACT", plain)
		self.assertIn("No field template exists", plain)

		scoped = render_pack_html(
			build_pack(
				profile_regime({"studio_scope": "Business Profile"}),
				{}, stub_profile(), stub_bid_ctx(), [],
			),
			stub_bid_ctx(),
		)
		self.assertIn("GENERATE VIA STUDIO", scoped)
		self.assertIn("Business Profile", scoped)
		self.assertIn("No field template exists", scoped)

		satisfied_pack = build_pack(
			profile_regime({
				"studio_scope": "Business Profile",
				"generated_artifact": "/files/umzansi-company-profile-a4.pdf",
			}),
			{}, stub_profile(), stub_bid_ctx(), [],
		)
		satisfied = render_pack_html(satisfied_pack, stub_bid_ctx())
		self.assertIn("SATISFIED BY GENERATED ARTIFACT", satisfied)
		self.assertIn("umzansi-company-profile-a4.pdf", satisfied)
		self.assertIn("studio document: Business Profile", satisfied)
		self.assertNotIn("No field template exists", satisfied)
		self.assertNotIn("GENERATE VIA STUDIO", satisfied)
		manifest_row = satisfied_pack["manifest"]["forms"][0]
		self.assertTrue(manifest_row["generated"])
		self.assertFalse(
			build_pack(profile_regime({}), {}, stub_profile(), stub_bid_ctx(), [])
			["manifest"]["forms"][0]["generated"]
		)

	def test_capability_register_renders_as_table(self):
		# wave-2 (findings F-07): profile capability rows render as a table on
		# the ICT-CAPABILITY worksheet; an empty register is an amber gap
		templates = {t["template_code"]: t for t in load_fixture("tender_form_templates.json")}
		self.assertIn("ICT-CAPABILITY", templates)
		# deliberately in NO regime's fixture set - reached via template_code
		for regime in load_fixture("tender_form_regimes.json"):
			self.assertNotIn(
				"ICT-CAPABILITY", {f["form_code"] for f in regime["forms"]},
				regime["regime_code"],
			)
		regime = {
			"regime_code": "MBD", "regime_name": "Municipal (MBD forms)",
			"forms": [{"form_code": "5.1(i)", "form_name": "Capability schedule",
			           "mandatory": 1, "kill_note": "", "template_code": "ICT-CAPABILITY"}],
		}
		profile = stub_profile()
		profile["capabilities"] = [
			{"capability_type": "Portfolio / Reference Site", "label": "www.client-municipality.gov.za",
			 "value": "Live since 2022", "detail": "Design, hosting and maintenance",
			 "reference_url": "https://www.client-municipality.gov.za", "valid_until": None},
			{"capability_type": "Uptime SLA", "label": "Managed hosting SLA",
			 "value": "99.9% monthly", "detail": None, "reference_url": None, "valid_until": None},
		]
		pack = build_pack(regime, templates, profile, stub_bid_ctx(), [])
		html = render_pack_html(pack, stub_bid_ctx())
		self.assertIn("www.client-municipality.gov.za", html)
		self.assertIn("99.9% monthly", html)
		self.assertIn("Uptime SLA", html)

		empty_profile = stub_profile()
		empty_profile["capabilities"] = []
		pack = build_pack(regime, templates, empty_profile, stub_bid_ctx(), [])
		html = render_pack_html(pack, stub_bid_ctx())
		self.assertIn("Not in your Business Profile", html)

	def test_directors_render_as_table(self):
		template = stub_template("F1", extra_fields=[
			{"section": "Directors", "field_label": "All directors", "source_type": "Profile Field",
			 "source_field": "directors", "signature_role": "", "multiline": 0, "guidance": ""},
		])
		pack = build_pack(stub_regime(codes=("F1",)), {"F1": template}, stub_profile(), stub_bid_ctx(), [])
		html = render_pack_html(pack, stub_bid_ctx())
		self.assertIn("8001015009087", html)
		self.assertIn("Tax Reference No", html)


class TestSigning(FrappeTestCase):
	WITNESSED_TEMPLATE_FIELDS = [
		{"section": "Witnesses", "field_label": "Witness 1 - signature", "source_type": "Signature",
		 "source_field": "", "signature_role": "Witness 1", "multiline": 0, "guidance": ""},
		{"section": "Witnesses", "field_label": "Witness 2 - signature", "source_type": "Signature",
		 "source_field": "", "signature_role": "Witness 2", "multiline": 0, "guidance": ""},
		{"section": "Commissioner", "field_label": "Commissioner of Oaths", "source_type": "Signature",
		 "source_field": "", "signature_role": "Commissioner of Oaths", "multiline": 0, "guidance": ""},
	]

	def _signing(self, sign=True, **overrides):
		payload = {
			"sign": sign,
			"signatory_name": "R. Sinyage",
			"signatory_capacity": "Director",
			"signatory_id": "8001015009087",
			"signature_url": "/private/files/signature_stamp.png",
			"initials_url": "/private/files/initials_stamp.png",
			"witnesses": [
				{"full_name": "W. One", "id_number": "9001015009087", "capacity": "Employee",
				 "signature_url": "/private/files/witness_1_stamp.png"},
				{"full_name": "W. Two", "id_number": "9101015009087", "capacity": "Employee",
				 "signature_url": None},
			],
			"ink_warning": None,
		}
		payload.update(overrides)
		return payload

	def _html(self, signing):
		templates = {"F1": stub_template("F1", extra_fields=self.WITNESSED_TEMPLATE_FIELDS)}
		pack = build_pack(stub_regime(codes=("F1",)), templates, stub_profile(), stub_bid_ctx(), [], signing)
		return pack, render_pack_html(pack, stub_bid_ctx(), signing)

	def test_unsigned_pack_renders_markers_not_images(self):
		pack, html = self._html({"sign": False})
		self.assertFalse(pack["manifest"]["signed"])
		self.assertIn("Sign here", html)
		self.assertIn("Witness 1 sign here", html)
		self.assertIn("Initial here", html)
		self.assertNotIn("<img", html)

	def test_signed_pack_stamps_images_and_notes_provenance(self):
		signing = self._signing()
		pack, html = self._html(signing)
		manifest = pack["manifest"]
		self.assertTrue(manifest["signed"])
		self.assertEqual(manifest["signature_provenance"], "stamped from uploaded scan")
		self.assertIn('src="/private/files/signature_stamp.png"', html)
		self.assertIn('src="/private/files/initials_stamp.png"', html)
		# witness 1 has an image -> stamped; witness 2 has none -> marked blank
		self.assertIn('src="/private/files/witness_1_stamp.png"', html)
		self.assertIn("Witness 2 sign here", html)
		# witness details caption always renders
		self.assertIn("W. Two", html)
		# no ink warning for an unknown/online buyer
		self.assertFalse(any("ORIGINAL INK" in w for w in manifest["warnings"]))

	def test_commissioner_slot_is_never_stamped(self):
		_pack, html = self._html(self._signing())
		self.assertIn("signed and stamped by the commissioner", html)
		self.assertNotIn('alt="Commissioner', html)

	def test_wet_ink_warning_is_data_driven(self):
		signing = self._signing(ink_warning=(
			"This buyer requires the physical pack signed in ORIGINAL INK "
			"(hard-copy submission governs) - print this pack and sign/initial "
			"by hand before delivering; the stamped scan is not acceptable on "
			"the physical pack."
		))
		pack, html = self._html(signing)
		self.assertTrue(any("ORIGINAL INK" in w for w in pack["manifest"]["warnings"]))
		self.assertIn("ORIGINAL INK", html)

	def test_wet_ink_patterns_ship_as_fixture_data(self):
		rules = {r["rule_code"]: r for r in load_fixture("tender_compliance_rules.json")}
		params = json.loads(rules["KILL-25"]["params"])
		patterns = params["wet_ink_hard_copy_patterns"]
		self.assertIn("ethekwini", patterns)
		# every wet-ink buyer must be one where hard copy also governs/applies -
		# the AND of the two facts is curated into this single list
		self.assertTrue(patterns)


class TestSignatureBackgroundStrip(FrappeTestCase):
	def _synthetic_signature(self, background, size=(120, 60)):
		from PIL import Image, ImageDraw

		image = Image.new("RGB", size, background)
		draw = ImageDraw.Draw(image)
		draw.line([(10, 45), (40, 12), (70, 48), (110, 15)], fill=(10, 10, 40), width=3)
		output = io.BytesIO()
		image.save(output, format="PNG")
		return output.getvalue()

	def _assert_stripped(self, background):
		from PIL import Image

		processed = strip_background(self._synthetic_signature(background))
		image = Image.open(io.BytesIO(processed))
		self.assertEqual(image.mode, "RGBA")
		# corners (background) transparent
		width, height = image.size
		for corner in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
			self.assertEqual(image.getpixel(corner)[3], 0, corner)
		# a point on the stroke stays opaque
		self.assertEqual(image.getpixel((40, 12))[3], 255)

	def test_signature_on_white(self):
		self._assert_stripped((255, 255, 255))

	def test_signature_on_solid_color(self):
		self._assert_stripped((180, 210, 240))

	def test_deterministic_output(self):
		data = self._synthetic_signature((255, 255, 255))
		self.assertEqual(strip_background(data), strip_background(data))


class TestArtifactExpiryCapture(FrappeTestCase):
	def test_non_expiring_types_are_a_subset_of_the_doctype_options(self):
		from {app_name}.tender.doctype.compliance_artifact.compliance_artifact import (
			NON_EXPIRING_ARTIFACT_TYPES,
		)

		doctype_json = os.path.join(
			os.path.dirname(__file__), "..", "doctype", "compliance_artifact", "compliance_artifact.json"
		)
		with open(doctype_json, encoding="utf-8") as f:
			meta = json.load(f)
		fields = {field["fieldname"]: field for field in meta["fields"]}
		options = set(fields["artifact_type"]["options"].split("\n"))
		for artifact_type in NON_EXPIRING_ARTIFACT_TYPES:
			self.assertIn(artifact_type, options, artifact_type)
		# every other type expires, so the expiry date is desk-mandatory too -
		# the JSON expression and the controller constant must agree
		expression = fields["valid_until"]["mandatory_depends_on"]
		for artifact_type in NON_EXPIRING_ARTIFACT_TYPES:
			self.assertIn(artifact_type, expression, artifact_type)


class TestManifestWiring(FrappeTestCase):
	def test_pack_and_quotation_endpoints_registered(self):
		manifest_path = os.path.join(os.path.dirname(__file__), "..", "manifest.json")
		with open(manifest_path, encoding="utf-8") as f:
			manifest = json.load(f)
		cmds = manifest["app_type"]["control"]["hooks"]["whitelisted_methods"]
		for key, target_tail in (
			("{app_name}.api.tenders.generate_bid_pack", "generate_bid_pack.generate_bid_pack"),
			("{app_name}.api.tenders.get_pack_status", "get_pack_status.get_pack_status"),
			("{app_name}.api.tenders.create_bid_quotation", "create_bid_quotation.create_bid_quotation"),
		):
			self.assertIn(key, cmds)
			self.assertTrue(cmds[key].endswith(target_tail), key)
		# soft erp integration wiring: guarded custom-field creation runs from
		# after_install + the weekly sweep; the Quotation doc_event is
		# registered unconditionally (frappe consults doc_events by doctype
		# name at runtime, so it never fires without the erp module)
		hooks = manifest["hooks"]
		self.assertIn(
			"{app_name}.tender.control.quotation_link.ensure_quotation_tender_field",
			hooks["after_install"],
		)
		self.assertIn(
			"{app_name}.tender.control.quotation_link.ensure_quotation_tender_field",
			hooks["scheduler_events"]["weekly"],
		)
		self.assertEqual(
			hooks["doc_events"]["Quotation"]["validate"],
			"{app_name}.tender.control.quotation_link.sync_quotation_link",
		)
		# fixture list ships the form templates
		self.assertIn({"dt": "Tender Form Template"}, hooks["fixtures"])


class TestFormTemplateFixtureIntegrity(FrappeTestCase):
	"""The templates ARE the form knowledge - malformed data must fail here."""

	def test_templates_fixture_shape(self):
		templates = load_fixture("tender_form_templates.json")
		codes = [t["template_code"] for t in templates]
		self.assertEqual(len(codes), len(set(codes)), "duplicate template_code")
		for template in templates:
			self.assertEqual(template["doctype"], "Tender Form Template")
			self.assertTrue(template["form_title"], template["template_code"])
			self.assertTrue(template["fields_table"], template["template_code"])
			for row in template["fields_table"]:
				self.assertIn(
					row["source_type"],
					("Profile Field", "Bid Field", "User Input", "Signature"),
					template["template_code"],
				)
				self.assertTrue(row["field_label"], template["template_code"])
				self.assertIn(row.get("signature_role", ""), SIGNATURE_ROLES)
				if row["source_type"] == "Profile Field":
					self.assertIn(
						row["source_field"], FILL_FIELDS,
						f"{template['template_code']}: unknown profile field {row['source_field']}",
					)
				elif row["source_type"] == "Bid Field":
					self.assertIn(
						row["source_field"], BID_CONTEXT_KEYS,
						f"{template['template_code']}: unknown bid field {row['source_field']}",
					)
				elif row["source_type"] == "Signature":
					self.assertTrue(
						row.get("signature_role"),
						f"{template['template_code']}: signature row without a role",
					)

	def test_every_regime_form_has_a_template(self):
		templates = {t["template_code"] for t in load_fixture("tender_form_templates.json")}
		regimes = load_fixture("tender_form_regimes.json")
		for regime in regimes:
			for form in regime["forms"]:
				self.assertIn(
					form["form_code"], templates,
					f"regime {regime['regime_code']} form {form['form_code']} has no template",
				)

	def test_headline_forms_carry_the_core_traps(self):
		templates = {t["template_code"]: t for t in load_fixture("tender_form_templates.json")}
		# cover forms demand the total price on the face of the form
		for code in ("SBD1", "MBD1"):
			labels = [f["field_label"] for f in templates[code]["fields_table"]]
			self.assertTrue(any("TOTAL BID PRICE" in label for label in labels), code)
		# declarations of interest carry the directors table and CSD-linked-companies trap
		for code in ("SBD4", "MBD4", "SBD4-W"):
			rows = templates[code]["fields_table"]
			self.assertTrue(
				any(r["source_field"] == "directors" for r in rows), code
			)
			self.assertTrue(
				any("CSD-registered companies" in (r["guidance"] or "") + r["field_label"] for r in rows),
				code,
			)
		# preference claims are explicit-number claims
		for code in ("SBD6.1", "MBD6.1", "SBD6.1-W"):
			rows = templates[code]["fields_table"]
			self.assertTrue(any("points" in r["field_label"].lower() for r in rows), code)
		# MBD9 signature is the kill - template must end in a Signatory slot
		mbd9_roles = [
			r["signature_role"] for r in templates["MBD9"]["fields_table"] if r["source_type"] == "Signature"
		]
		self.assertIn("Signatory", mbd9_roles)
		# commissioner slots exist on the commissioned municipal declarations and are role-marked
		for code in ("MBD4", "MBD8", "MBD9"):
			roles = [
				r["signature_role"] for r in templates[code]["fields_table"] if r["source_type"] == "Signature"
			]
			self.assertIn("Commissioner of Oaths", roles, code)
		# witness slots on the witnessed contract forms
		for code in ("SBD7", "C1.1", "NDA"):
			roles = [
				r["signature_role"] for r in templates[code]["fields_table"] if r["source_type"] == "Signature"
			]
			self.assertIn("Witness 1", roles, code)
			self.assertIn("Witness 2", roles, code)
