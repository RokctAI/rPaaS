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

"""Deterministic compliance-layer tests: rule matching, scoring arithmetic,
checklist generation, artifact status, and fixture integrity. Like the other
suites, imports use the `{app_name}` template placeholder, so these run on a
composed bench.
"""

import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from {app_name}.tender.control.compliance.preference_frameworks import (
	detect_preference_frameworks,
	preference_framework_conflict,
)
from {app_name}.tender.control.compliance.rules import (
	bid_context,
	condition_matches,
	parse_json_field,
	parse_regimes,
	rule_applies,
)
from {app_name}.tender.control.compliance.scoring import (
	failing_functionality_sections,
	passes_functionality,
	passes_functionality_sections,
	preference_system_for_value,
	price_points,
	price_points_inverted,
)
from {app_name}.tender.control.compliance.submission_gate import (
	SECTIONED_NO_SECTIONS_WARNING,
	submission_readiness_warnings,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def load_fixture(filename):
	with open(os.path.join(FIXTURES_DIR, filename), encoding="utf-8") as f:
		return json.load(f)


class TestRuleMatching(FrappeTestCase):
	def test_condition_matches_value_over(self):
		self.assertTrue(condition_matches({"estimated_value_over": 10000000}, {"estimated_value": 15000000}))
		self.assertFalse(condition_matches({"estimated_value_over": 10000000}, {"estimated_value": 10000000}))
		self.assertFalse(condition_matches({"estimated_value_over": 10000000}, {"estimated_value": None}))

	def test_condition_matches_equality_and_membership(self):
		self.assertTrue(condition_matches({"regime": "MBD"}, {"regime": "MBD"}))
		self.assertFalse(condition_matches({"regime": "MBD"}, {"regime": "SBD"}))
		self.assertTrue(condition_matches({"regime": ["MBD", "SBD"]}, {"regime": "SBD"}))
		self.assertFalse(condition_matches({}, {"regime": "SBD"}))

	def test_condition_matches_text_patterns(self):
		# v3 buyer matching: "<field>_matches" is a normalized substring test
		# against a pattern list - patterns live in fixture data, never code
		cond = {"institution_matches": ["eskom", "transnet"]}
		self.assertTrue(condition_matches(cond, {"institution": "Eskom Holdings SOC Ltd"}))
		self.assertTrue(condition_matches(cond, {"institution": "TRANSNET   SOC LTD"}))
		self.assertFalse(condition_matches(cond, {"institution": "Mogale City Local Municipality"}))
		self.assertFalse(condition_matches(cond, {"institution": None}))
		self.assertFalse(condition_matches(cond, {}))
		self.assertFalse(condition_matches({"institution_matches": []}, {"institution": "Eskom"}))
		# combines with other operators (all keys must match)
		both = {"institution_matches": ["eskom"], "estimated_value_over": 1000000}
		self.assertTrue(both and condition_matches(both, {"institution": "eskom", "estimated_value": 2000000}))
		self.assertFalse(condition_matches(both, {"institution": "eskom", "estimated_value": 500}))

	def test_condition_matches_any_of(self):
		# wave-1 OR combinator: at least one sub-condition dict must match
		cond = {
			"any_of": [
				{"regime_matches": ["mbd"]},
				{"institution_matches": ["water board", "vaal central water"]},
			]
		}
		self.assertTrue(condition_matches(cond, {"regime": "MBD"}))
		self.assertTrue(condition_matches(cond, {"regime": "SBD", "institution": "Vaal Central Water"}))
		self.assertFalse(condition_matches(cond, {"regime": "SBD", "institution": "DFFE"}))
		# degenerate shapes never match
		self.assertFalse(condition_matches({"any_of": []}, {"regime": "MBD"}))
		self.assertFalse(condition_matches({"any_of": "mbd"}, {"regime": "MBD"}))
		self.assertFalse(condition_matches({"any_of": [{}]}, {"regime": "MBD"}))
		# AND-composes with sibling keys like every other operator
		both = {"any_of": [{"regime_matches": ["mbd"]}], "estimated_value_over": 1000000}
		self.assertTrue(condition_matches(both, {"regime": "MBD", "estimated_value": 2000000}))
		self.assertFalse(condition_matches(both, {"regime": "MBD", "estimated_value": 500}))

	def test_bid_context_carries_subject(self):
		# subject = cached tender title (+ description when a bid ever carries
		# one) so subject-matter rules can fire on WHAT is procured
		ctx = bid_context({
			"regime": "MBD",
			"tender_title": "Hosting of a Website for the Municipality",
		})
		self.assertEqual(ctx["subject"], "Hosting of a Website for the Municipality")
		self.assertEqual(ctx["tender_title"], "Hosting of a Website for the Municipality")
		self.assertIsNone(bid_context({"regime": "MBD"})["subject"])

	def test_regime_fence_matches_overlay_set(self):
		# wave-2 (findings F-01): the regimes fence is a set test over
		# {regime, overlay_regime} - a CIDB-fenced rule fires on an MBD bid
		# carrying a CIDB overlay; single-regime bids behave exactly as before
		rule = {"enabled": 1, "scope": "Conditional", "regimes": "CIDB", "trigger_condition": ""}
		self.assertTrue(rule_applies(rule, {"regime": "MBD", "overlay_regime": "CIDB"}))
		self.assertTrue(rule_applies(rule, {"regime": "CIDB"}))
		self.assertFalse(rule_applies(rule, {"regime": "MBD"}))
		self.assertFalse(rule_applies(rule, {"regime": "MBD", "overlay_regime": None}))
		self.assertFalse(rule_applies(rule, {"regime": None}))

	def test_bid_context_carries_overlay_and_joined_codes(self):
		# wave-2 (findings F-01): regime_codes joins base+overlay so
		# regime_codes_matches conditions can fire on EITHER code; the
		# existing regime value keeps its exact single-code semantics
		ctx = bid_context({"regime": "MBD", "overlay_regime": "CIDB"})
		self.assertEqual(ctx["regime"], "MBD")
		self.assertEqual(ctx["overlay_regime"], "CIDB")
		self.assertEqual(ctx["regime_codes"], "MBD CIDB")
		self.assertTrue(condition_matches({"regime_codes_matches": ["cidb"]}, ctx))
		self.assertTrue(condition_matches({"regime_codes_matches": ["mbd"]}, ctx))
		single = bid_context({"regime": "MBD"})
		self.assertIsNone(single["overlay_regime"])
		self.assertEqual(single["regime_codes"], "MBD")
		self.assertIsNone(bid_context({})["regime_codes"])

	def test_universal_rule_applies_everywhere(self):
		rule = {"enabled": 1, "scope": "Universal", "regimes": "", "trigger_condition": ""}
		self.assertTrue(rule_applies(rule, {"regime": None}))
		self.assertTrue(rule_applies(rule, {"regime": "MBD"}))

	def test_regime_restriction(self):
		rule = {"enabled": 1, "scope": "Conditional", "regimes": "MBD", "trigger_condition": ""}
		self.assertTrue(rule_applies(rule, {"regime": "MBD"}))
		self.assertFalse(rule_applies(rule, {"regime": "SBD"}))
		self.assertFalse(rule_applies(rule, {"regime": None}))

	def test_conditional_with_trigger(self):
		rule = {
			"enabled": 1,
			"scope": "Conditional",
			"regimes": "MBD",
			"trigger_condition": '{"estimated_value_over": 10000000}',
		}
		self.assertTrue(rule_applies(rule, {"regime": "MBD", "estimated_value": 12000000}))
		self.assertFalse(rule_applies(rule, {"regime": "MBD", "estimated_value": 5000000}))
		self.assertFalse(rule_applies(rule, {"regime": "SBD", "estimated_value": 12000000}))

	def test_conditional_without_trigger_or_regime_never_auto_applies(self):
		rule = {"enabled": 1, "scope": "Conditional", "regimes": "", "trigger_condition": ""}
		self.assertFalse(rule_applies(rule, {"regime": "MBD", "estimated_value": 99999999999}))

	def test_disabled_rule_never_applies(self):
		rule = {"enabled": 0, "scope": "Universal", "regimes": "", "trigger_condition": ""}
		self.assertFalse(rule_applies(rule, {}))

	def test_parse_helpers_are_defensive(self):
		self.assertEqual(parse_json_field("not json"), {})
		self.assertEqual(parse_json_field(""), {})
		self.assertEqual(parse_json_field('{"a": 1}'), {"a": 1})
		self.assertEqual(parse_regimes(" mbd, SBD "), {"MBD", "SBD"})
		self.assertEqual(parse_regimes(None), set())


class TestScoring(FrappeTestCase):
	def test_preference_system_thresholds(self):
		params = {"threshold_rand": 50000000, "straddle_band_pct": 10}
		self.assertEqual(preference_system_for_value(1000000, params), "80/20")
		self.assertEqual(preference_system_for_value(80000000, params), "90/10")
		self.assertEqual(preference_system_for_value(50000000, params), "Straddling")
		self.assertEqual(preference_system_for_value(46000000, params), "Straddling")
		self.assertEqual(preference_system_for_value(None, params), "")

	def test_preference_system_without_band(self):
		params = {"threshold_rand": 50000000, "straddle_band_pct": 0}
		self.assertEqual(preference_system_for_value(50000000, params), "80/20")
		self.assertEqual(preference_system_for_value(50000001, params), "90/10")

	def test_price_points_formula(self):
		# Lowest price takes the full base
		self.assertEqual(price_points(100, 100, 80), 80.0)
		# Ps = 80 * (1 - (110-100)/100) = 72
		self.assertAlmostEqual(price_points(110, 100, 80), 72.0)
		# 90/10 system
		self.assertAlmostEqual(price_points(110, 100, 90), 81.0)
		# Never negative
		self.assertEqual(price_points(300, 100, 80), 0.0)
		# Degenerate lowest price
		self.assertEqual(price_points(100, 0, 80), 0.0)

	def test_price_points_inverted_formula(self):
		# Income-generating/disposal tenders: highest acceptable offer takes the full base
		self.assertEqual(price_points_inverted(100, 100, 80), 80.0)
		# Ps = 80 * (1 + (90-100)/100) = 72
		self.assertAlmostEqual(price_points_inverted(90, 100, 80), 72.0)
		# 90/10 system
		self.assertAlmostEqual(price_points_inverted(90, 100, 90), 81.0)
		# Never negative
		self.assertEqual(price_points_inverted(0, 100, 80), 0.0)
		# Degenerate highest price
		self.assertEqual(price_points_inverted(100, 0, 80), 0.0)

	def test_functionality_gate(self):
		self.assertTrue(passes_functionality(75, 70))
		self.assertFalse(passes_functionality(65, 70))
		# v2: thresholds are per-tender data down to 40% - the gate reads the
		# recorded value, there is no hard-coded floor
		self.assertTrue(passes_functionality(45, 40))
		self.assertFalse(passes_functionality(39, 40))
		self.assertTrue(passes_functionality(None, None))
		self.assertTrue(passes_functionality(None, 0))
		self.assertFalse(passes_functionality(None, 70))

	def test_sectioned_functionality_gate(self):
		# wave-2 (findings F-05): VCW-shaped dual sections, each with its own
		# 75% kill - one failing section eliminates the whole bid
		sections = [
			{"section_label": "Section 1 - Guarding", "max_points": 335,
			 "threshold_pct": 75, "self_score_points": 290},
			{"section_label": "Section 2 - Fencing & related works", "max_points": 165,
			 "threshold_pct": 75, "self_score_points": 110},
		]
		self.assertEqual(
			failing_functionality_sections(sections), ["Section 2 - Fencing & related works"]
		)
		self.assertFalse(passes_functionality_sections(sections))
		sections[1]["self_score_points"] = 130  # 78.8% - clears its 75% kill
		self.assertEqual(failing_functionality_sections(sections), [])
		self.assertTrue(passes_functionality_sections(sections))
		# rows without a threshold are informational; malformed rows (no max
		# points) never fail a bid on bad data; empty input passes
		self.assertTrue(passes_functionality_sections([
			{"section_label": "Info", "max_points": 100, "self_score_points": 0},
			{"section_label": "Broken", "max_points": 0, "threshold_pct": 75, "self_score_points": 0},
		]))
		self.assertTrue(passes_functionality_sections([]))
		self.assertTrue(passes_functionality_sections(None))
		# a recorded threshold with no self-score fails - consistent with the
		# single-pair gate (RNM METHOD 4: 42/70 = 60%)
		self.assertEqual(
			failing_functionality_sections(
				[{"section_label": "RNM METHOD 4 matrix", "max_points": 70, "threshold_pct": 60}]
			),
			["RNM METHOD 4 matrix"],
		)

	def test_sectioned_mode_with_no_captured_sections_warns_but_never_blocks(self):
		# wave-2 PR-B review feedback: Sectioned mode with an EMPTY sections
		# table passes the gate silently (nothing to check - defensible), but
		# it must be VISIBLE - the advisory lint flags it in the wave-1
		# preference-conflict style, never as a hard failure
		self.assertEqual(
			submission_readiness_warnings(
				{"functionality_mode": "Sectioned", "functionality_sections": []}
			),
			[SECTIONED_NO_SECTIONS_WARNING],
		)
		self.assertEqual(
			submission_readiness_warnings({"functionality_mode": "Sectioned"}),
			[SECTIONED_NO_SECTIONS_WARNING],
		)
		self.assertIn(
			"Sectioned functionality selected but no sections captured",
			SECTIONED_NO_SECTIONS_WARNING,
		)
		# the empty-table gate itself stays a pass (the warning is the surface)
		self.assertTrue(passes_functionality_sections([]))
		# populated sections: no warning - behaviour exactly as shipped
		self.assertEqual(
			submission_readiness_warnings({
				"functionality_mode": "Sectioned",
				"functionality_sections": [
					{"section_label": "S1", "max_points": 100,
					 "threshold_pct": 75, "self_score_points": 80},
				],
			}),
			[],
		)
		# other modes never warn
		self.assertEqual(submission_readiness_warnings({"functionality_mode": "Single threshold"}), [])
		self.assertEqual(submission_readiness_warnings({"functionality_mode": "No scored functionality"}), [])
		self.assertEqual(submission_readiness_warnings({}), [])


class TestFixtureIntegrity(FrappeTestCase):
	"""The fixtures ARE the rulebook - malformed data must fail loudly here."""

	def test_compliance_rules_fixture_shape(self):
		rules = load_fixture("tender_compliance_rules.json")
		codes = [r["rule_code"] for r in rules]
		self.assertEqual(len(codes), len(set(codes)), "duplicate rule_code in fixture")
		for rule in rules:
			self.assertEqual(rule["doctype"], "Tender Compliance Rule")
			self.assertIn(rule["scope"], ("Universal", "Conditional"))
			self.assertIn(rule["severity"], ("Fatal", "Curable", "Points-only"))
			# JSON fields must parse
			if rule.get("trigger_condition"):
				self.assertIsInstance(json.loads(rule["trigger_condition"]), dict)
			if rule.get("params"):
				json.loads(rule["params"])

	def test_scoring_constants_present(self):
		rules = {r["rule_code"]: r for r in load_fixture("tender_compliance_rules.json")}
		params = json.loads(rules["SCORE-SYSTEM"]["params"])
		self.assertEqual(params["threshold_rand"], 50000000)
		formula = json.loads(rules["SCORE-PRICE-FORMULA"]["params"])
		self.assertEqual(formula["points_base_8020"], 80)
		self.assertEqual(formula["points_base_9010"], 90)
		# v3: SCORE-FUNCTIONALITY defaults come from the 238-observation
		# corpus scan (mode/median 70, observed range 36-100) - the threshold
		# itself stays per-tender data on the bid record
		functionality = json.loads(rules["SCORE-FUNCTIONALITY"]["params"])
		self.assertEqual(functionality["threshold_mode_pct"], 70)
		self.assertEqual(functionality["threshold_median_pct"], 70)
		self.assertEqual(functionality["threshold_default_pct"], 70)
		self.assertEqual(functionality["threshold_min_observed"], 36)
		self.assertEqual(functionality["threshold_max_observed"], 100)
		self.assertEqual(functionality["observations"], 238)
		# v2 mechanisms ship as data: s2(1)(f) override and panel mechanics
		self.assertIn("SCORE-OBJECTIVE-CRITERIA", rules)
		self.assertIn("SCORE-PANEL", rules)
		self.assertEqual(rules["SCORE-OBJECTIVE-CRITERIA"]["rule_class"], "Scoring Rule")
		self.assertEqual(rules["SCORE-PANEL"]["rule_class"], "Scoring Rule")

	def test_universal_hard_gates_are_fatal(self):
		rules = {r["rule_code"]: r for r in load_fixture("tender_compliance_rules.json")}
		for code in ("GATE-CSD", "GATE-TCS", "GATE-DEFAULTERS", "GATE-STATE-EMP", "GATE-CIPC"):
			self.assertEqual(rules[code]["scope"], "Universal", code)
			self.assertEqual(rules[code]["severity"], "Fatal", code)
			self.assertTrue(rules[code]["checklist_text"], code)
		# B-BBEE stays the universal SOFT gate ("still submit") as a preference
		# claim - the v2 pre-qualification exception is its own Fatal rule
		self.assertEqual(rules["GATE-BBBEE"]["severity"], "Points-only")
		prequal = rules["GATE-BBBEE-PREQUAL"]
		self.assertEqual(prequal["severity"], "Fatal")
		self.assertEqual(prequal["scope"], "Conditional")
		# v3: buyer-triggered via institution_matches - auto-applies only when
		# the bid's cached OCDS buyer name matches the fixture patterns
		self.assertTrue(prequal["trigger_condition"])
		self.assertFalse(prequal["regimes"])
		self.assertFalse(rule_applies(prequal, {"regime": "SBD", "estimated_value": 1}))
		self.assertTrue(
			rule_applies(prequal, {"regime": "SBD", "institution": "ESKOM HOLDINGS SOC LTD"})
		)
		# Security vetting likewise auto-applies only for security-adjacent buyers
		vetting = rules["GATE-SECURITY-VETTING"]
		self.assertEqual(vetting["severity"], "Fatal")
		self.assertFalse(rule_applies(vetting, {"regime": "SOE", "estimated_value": 1}))
		self.assertTrue(rule_applies(vetting, {"regime": "SOE", "institution": "Transnet SOC Ltd"}))

	def test_v3_buyer_triggered_gates(self):
		"""The five formerly-triggerless Conditional gates now carry buyer
		triggers as fixture DATA (institution_matches patterns from the 14
		buyer-profile sheets) - no buyer name lives in code."""
		rules = {r["rule_code"]: r for r in load_fixture("tender_compliance_rules.json")}
		expectations = {
			"GATE-SECTOR": ("Department of Tourism", "Mogale City Local Municipality"),
			"GATE-INSURANCE": ("City of Cape Town Metropolitan Municipality", "Statistics South Africa"),
			"GATE-BANK-LETTER": ("Airports Company South Africa SOC Ltd", "Eskom Holdings SOC Ltd"),
			"GATE-BBBEE-PREQUAL": ("Eskom Holdings SOC Ltd", "City of Tshwane"),
			"GATE-SECURITY-VETTING": ("SA National Roads Agency SOC Ltd (SANRAL)", "Stats SA"),
			"GATE-POPIA": ("TRANSNET SOC LTD", "Eskom Holdings SOC Ltd"),
			"GATE-INTEGRITY-PACT": ("Eskom Holdings SOC Ltd", "PRASA"),
			"GATE-LOCALITY": ("Air Traffic and Navigation Services SOC Ltd", "Transnet SOC Ltd"),
		}
		for code, (matching, non_matching) in expectations.items():
			rule = rules[code]
			self.assertEqual(rule["scope"], "Conditional", code)
			self.assertTrue(rule["trigger_condition"], code)
			self.assertTrue(rule_applies(rule, {"institution": matching}), code)
			self.assertFalse(rule_applies(rule, {"institution": non_matching}), code)
			# a bid with no cached buyer name never auto-picks-up a buyer gate
			self.assertFalse(rule_applies(rule, {"institution": None}), code)

	def test_wave1_subject_and_rescoped_triggers(self):
		"""Wave-1 fixture deltas (findings F-03/F-04): the five mock-sample
		buyers/subjects now trigger the documented rules, the original
		targets still match, and regime scoping no longer fences out
		demand-driven cases. Contexts mirror the five sample bids."""
		rules = {r["rule_code"]: r for r in load_fixture("tender_compliance_rules.json")}
		rnm = {
			"regime": "MBD", "estimated_value": 42500000,
			"institution": "Ray Nkonyeni Local Municipality",
			"subject": "Construction of Mgodlwa Bridge in Ward 8",
		}
		dffe = {
			"regime": "SBD",
			"institution": "Department of Forestry, Fisheries and the Environment",
			"subject": "Determination of the state of forests in South Africa",
		}
		vcw = {
			"regime": "SBD", "estimated_value": 168000000,
			"institution": "Vaal Central Water",
			"subject": "Total Security Solution: physical guarding services; supply, "
			"installation and maintenance incl. perimeter security fencing and related works",
		}
		twk = {
			"regime": "MBD", "estimated_value": 2179056,
			"institution": "Theewaterskloof Municipality",
			"subject": "Support, Maintenance, Development and Hosting of a Website "
			"for the Theewaterskloof Municipality",
		}
		musina = {
			"regime": "MBD", "estimated_value": 2573750,
			"institution": "Musina Local Municipality",
			"subject": "Interactive Cloud-Based Customer Service Ticketing and "
			"Helpdesk Management System",
		}

		# F-03: GATE-SECTOR fires on the security-services subject (PSIRA
		# pre-qualifiers) and keeps its original buyer trigger
		self.assertTrue(rule_applies(rules["GATE-SECTOR"], vcw))
		self.assertTrue(rule_applies(rules["GATE-SECTOR"], {"institution": "Department of Tourism"}))
		self.assertFalse(rule_applies(rules["GATE-SECTOR"], twk))
		self.assertFalse(rule_applies(rules["GATE-SECTOR"], dffe))

		# F-03: GATE-INSURANCE fires for VCW (R15m public-liability
		# pre-qualifier) and keeps its original buyer list
		self.assertTrue(rule_applies(rules["GATE-INSURANCE"], vcw))
		self.assertTrue(rule_applies(rules["GATE-INSURANCE"], {"institution": "SANRAL SOC Ltd"}))
		self.assertFalse(rule_applies(rules["GATE-INSURANCE"], musina))

		# F-03: GATE-POPIA fires on personal-information subjects (Musina
		# helpdesk spec text; TWK website hosting) and keeps SANRAL/Transnet
		self.assertTrue(rule_applies(rules["GATE-POPIA"], musina))
		self.assertTrue(rule_applies(rules["GATE-POPIA"], twk))
		self.assertTrue(rule_applies(rules["GATE-POPIA"], {"institution": "TRANSNET SOC LTD"}))
		self.assertFalse(rule_applies(rules["GATE-POPIA"], rnm))

		# F-04: GATE-RATES still fires on every MBD bid, now ALSO on the
		# SBD-regime water board that demanded rates clearance - and stays
		# off ordinary national-department SBD bids
		for mbd_bid in (rnm, twk, musina):
			self.assertTrue(rule_applies(rules["GATE-RATES"], mbd_bid))
		self.assertTrue(rule_applies(rules["GATE-RATES"], vcw))
		self.assertFalse(rule_applies(rules["GATE-RATES"], dffe))
		self.assertFalse(rule_applies(rules["GATE-RATES"], {"regime": None}))

		# F-04: GATE-CIDB / GATE-COIDA still fire on the CIDB regime, now
		# ALSO on works / site-based-services subjects under other regimes
		cidb_bid = {"regime": "CIDB", "subject": None}
		for code in ("GATE-CIDB", "GATE-COIDA"):
			self.assertTrue(rule_applies(rules[code], cidb_bid), code)
			self.assertTrue(rule_applies(rules[code], rnm), code)
			self.assertTrue(rule_applies(rules[code], vcw), code)
			self.assertFalse(rule_applies(rules[code], twk), code)
			self.assertFalse(rule_applies(rules[code], dffe), code)

		# GATE-MBD5's value trigger is untouched: ON at R42.5m, OFF at R2.57m
		self.assertTrue(rule_applies(rules["GATE-MBD5"], rnm))
		self.assertFalse(rule_applies(rules["GATE-MBD5"], musina))

	def test_wave1_preference_framework_conflict(self):
		"""F-12: the deterministic lint fires on a Musina-shaped pack
		(three preference frameworks at once) and stays silent on an
		ordinary single-framework pack."""
		musina_texts = [
			"MBD 6.1 - Preference Points Claim Form (PPR 2022, specific goals)",
			"Form C - Declaration of Interest: HDI Equity Ownership ...% = ... Points out of 20 (<R1 000 000)",
			"Form D - Certificate of Preference for Local Content and SABS mark (Section 35, Local Government Ordinance, 1939)",
		]
		frameworks = detect_preference_frameworks(musina_texts)
		self.assertEqual(len(frameworks), 3, frameworks)
		warning = preference_framework_conflict(musina_texts, operative_system="80/20")
		self.assertIsNotNone(warning)
		self.assertIn("conflicting preference frameworks", warning)
		self.assertIn("80/20", warning)
		self.assertIn("WARN-PREF-CONFLICT", warning)

		# ordinary pack: PPR 2022 claim form only (incl. the lawful SATS 1286
		# local-content instrument, which is NOT a conflicting framework)
		normal_texts = [
			"MBD 6.1 - Preference Points Claim Form (specific goals)",
			"MBD 6.2 - Declaration of Local Production and Content (per SATS 1286)",
		]
		self.assertIsNone(preference_framework_conflict(normal_texts))
		self.assertIsNone(preference_framework_conflict([]))
		self.assertIsNone(preference_framework_conflict(None))

		# the fixture rule ships the same patterns as desk-editable data
		rules = {r["rule_code"]: r for r in load_fixture("tender_compliance_rules.json")}
		rule = rules["WARN-PREF-CONFLICT"]
		self.assertEqual(rule["rule_class"], "Form Rule")
		self.assertEqual(rule["severity"], "Curable")
		params = json.loads(rule["params"])
		self.assertIn("framework_patterns", params)
		self.assertEqual(len(params["framework_patterns"]), 3)
		self.assertIsNotNone(
			preference_framework_conflict(musina_texts, framework_patterns=params["framework_patterns"])
		)
		# no auto trigger: desk-attached until per-pack returnable capture (F-02)
		self.assertFalse(rule_applies(rule, {"regime": "MBD", "subject": "anything"}))

	def test_price_multiyear_esc_fires_only_on_multi_year_terms(self):
		"""F-06: the escalation-basis pricing check attaches to a Musina-shaped
		36-month bid and stays off single-year (or unstated-term) bids."""
		rules = {r["rule_code"]: r for r in load_fixture("tender_compliance_rules.json")}
		rule = rules["PRICE-MULTIYEAR-ESC"]
		self.assertEqual(rule["rule_class"], "Pricing Rule")
		self.assertEqual(rule["severity"], "Curable")
		self.assertEqual(rule["scope"], "Conditional")
		self.assertEqual(
			json.loads(rule["trigger_condition"]), {"contract_term_months_over": 12}
		)
		self.assertIn("firm_price_review_note", json.loads(rule["params"]))
		self.assertIn("KILL-ALT-OFFER", rule["checklist_text"])

		musina = bid_context({
			"regime": "MBD", "estimated_value": 2573750,
			"institution": "Musina Local Municipality",
			"tender_title": "Cloud-Based Helpdesk Management System",
			"contract_term_months": 36,
		})
		self.assertEqual(musina["contract_term_months"], 36)
		self.assertTrue(rule_applies(rule, musina))
		# TWK's typical 5-year shape fires too
		self.assertTrue(rule_applies(rule, bid_context({"regime": "MBD", "contract_term_months": 60})))
		# a 12-month DFFE-shaped bid, an unset term and a zero term stay off
		self.assertFalse(rule_applies(rule, bid_context({"regime": "SBD", "contract_term_months": 12})))
		self.assertFalse(rule_applies(rule, bid_context({"regime": "SBD"})))
		self.assertFalse(rule_applies(rule, bid_context({"regime": "MBD", "contract_term_months": 0})))

	def test_v3_rules_present_and_counted(self):
		rules = load_fixture("tender_compliance_rules.json")
		by_code = {r["rule_code"]: r for r in rules}
		# v3 additions from the 65-row corpus rules-table
		for code, rule_class in (
			("GATE-POPIA", "Registration Gate"),
			("GATE-INTEGRITY-PACT", "Registration Gate"),
			("GATE-LOCALITY", "Registration Gate"),
			("SCORE-PREF-CLAIM", "Scoring Rule"),
			("PRICE-VAT", "Pricing Rule"),
			("PRICE-SECURITY", "Pricing Rule"),
			("FORM-VALIDITY", "Form Rule"),
		):
			self.assertIn(code, by_code, code)
			self.assertEqual(by_code[code]["rule_class"], rule_class, code)
			self.assertTrue(by_code[code]["checklist_text"], code)
		# totals: 20 gates + 25 kill causes + 7 scoring + 3 pricing + 2 form
		# + 12 buyer quirks
		# (wave-1 adds WARN-PREF-CONFLICT as a Form Rule - findings F-12;
		# wave-2 adds PRICE-MULTIYEAR-ESC as a Pricing Rule - findings F-06;
		# wave-3 adds GATE-PACK-COLLECT as a Registration Gate - findings
		# F-08, 19 -> 20; PR-C adds the 12 QUIRK-* Buyer Quirk rows -
		# findings F-11, total 57 -> 69)
		counts = {}
		for rule in rules:
			counts[rule["rule_class"]] = counts.get(rule["rule_class"], 0) + 1
		self.assertEqual(counts["Registration Gate"], 20)
		self.assertEqual(counts["Disqualification Cause"], 25)
		self.assertEqual(counts["Scoring Rule"], 7)
		self.assertEqual(counts["Pricing Rule"], 3)
		self.assertEqual(counts["Form Rule"], 2)
		self.assertEqual(counts["Buyer Quirk"], 12)
		self.assertEqual(len(rules), 69)
		# buyer facts ship as data on the rules that carry them
		self.assertIn("arrears_windows", json.loads(by_code["GATE-RATES"]["params"]))
		self.assertIn("cure_regimes", json.loads(by_code["KILL-14"]["params"]))
		self.assertIn("hard_copy_governs_patterns", json.loads(by_code["KILL-25"]["params"]))
		self.assertIn("buyer_cover_facts", json.loads(by_code["GATE-INSURANCE"]["params"]))

	def test_v2_kill_causes_present(self):
		rules = {r["rule_code"]: r for r in load_fixture("tender_compliance_rules.json")}
		# v2 additions: one-bid-per-entity and dual-channel governing-copy rules
		for code in ("KILL-24", "KILL-25"):
			self.assertEqual(rules[code]["rule_class"], "Disqualification Cause", code)
			self.assertEqual(rules[code]["severity"], "Fatal", code)
			self.assertTrue(rules[code]["checklist_text"], code)

	def test_buyer_quirk_rules_fire_on_their_buyer_only(self):
		# PR-C (findings F-11): every QUIRK-* row is a Conditional Buyer Quirk
		# with an institution_matches trigger, and fires ONLY on its own
		# buyer's context - Musina quirks must never attach to a DFFE bid.
		rules = load_fixture("tender_compliance_rules.json")
		quirks = [r for r in rules if r["rule_code"].startswith("QUIRK-")]
		self.assertEqual(len(quirks), 12)
		contexts = {
			"RNM": bid_context({"regime": "MBD", "estimated_value": 42500000,
				"institution": "Ray Nkonyeni Local Municipality"}),
			"DFFE": bid_context({"regime": "SBD", "institution":
				"Department of Forestry, Fisheries and the Environment"}),
			"VCW": bid_context({"regime": "SBD", "estimated_value": 168000000,
				"institution": "Vaal Central Water"}),
			"MUSINA": bid_context({"regime": "MBD", "estimated_value": 2573750,
				"institution": "Musina Local Municipality"}),
			"TWK": bid_context({"regime": "MBD", "institution":
				"Theewaterskloof Municipality"}),
		}
		for quirk in quirks:
			self.assertEqual(quirk["rule_class"], "Buyer Quirk", quirk["rule_code"])
			self.assertEqual(quirk["scope"], "Conditional", quirk["rule_code"])
			self.assertTrue(quirk["checklist_text"], quirk["rule_code"])
			buyer = quirk["rule_code"].split("-")[1]
			for key, context in contexts.items():
				self.assertEqual(
					rule_applies(quirk, context), key == buyer,
					f"{quirk['rule_code']} vs {key}",
				)
		# no quirk was encoded for the advert-only-grounded TWK buyer
		self.assertFalse([q for q in quirks if "TWK" in q["rule_code"]])
		# machine constants ship in params (VCW band/rotation, RNM goal table)
		self.assertEqual(
			json.loads({q["rule_code"]: q for q in quirks}["QUIRK-VCW-PRICEBAND"]["params"])["tolerance_pct"], 20
		)
		self.assertEqual(
			json.loads({q["rule_code"]: q for q in quirks}["QUIRK-VCW-ROTATION"]["params"])["rotation_threshold_rand"],
			250000000,
		)
		self.assertEqual(
			len(json.loads({q["rule_code"]: q for q in quirks}["QUIRK-RNM-LOCALITY"]["params"])["goal_table"]), 3
		)

	def test_form_regimes_fixture_shape(self):
		regimes = load_fixture("tender_form_regimes.json")
		codes = {r["regime_code"] for r in regimes}
		self.assertEqual(codes, {"SBD", "MBD", "SOE", "CIDB", "RFQ"})
		by_code = {r["regime_code"]: {f["form_code"] for f in r["forms"]} for r in regimes}
		# MBD 8 and 9 are always separate returnables in the municipal regime
		self.assertIn("MBD8", by_code["MBD"])
		self.assertIn("MBD9", by_code["MBD"])
		# v2 mandatory-returnable additions
		self.assertIn("MBD2", by_code["MBD"])
		self.assertIn("POPIA", by_code["MBD"])
		self.assertIn("SBD3.2", by_code["SBD"])
		self.assertIn("CST", by_code["SBD"])
		self.assertIn("DPIP-FPPO", by_code["SOE"])
		self.assertIn("INTEGRITY-PACT", by_code["SOE"])
		self.assertIn("GCC-ACCEPT", by_code["CIDB"])
		# wave-1 (findings F-10): every pricing regime renders pricing_lines -
		# MBD gets its own Pricing Schedules worksheet, CIDB a priced C2.2 variant
		self.assertIn("MBD3.x", by_code["MBD"])
		self.assertIn("T2.x-PRICE", by_code["CIDB"])

	def test_workflow_templates_fixture_shape(self):
		templates = load_fixture("tender_workflow_templates.json")
		names = {t["template_name"] for t in templates}
		self.assertIn("Default", names)
		# v2: panel/framework two-stage mechanics get their own workflow
		self.assertIn("Panel / Framework Entry", names)
		for template in templates:
			for task in template["tasks"]:
				self.assertTrue(task["subject"])
				self.assertGreaterEqual(task["due_date_offset_days"], 0)


class TestChecklistGeneration(FrappeTestCase):
	def setUp(self):
		frappe.conf.app_role = "control"
		frappe.set_user("Administrator")
		frappe.db.delete("Bid Checklist Item")
		frappe.db.delete("Tender Bid")

	def tearDown(self):
		frappe.db.delete("Bid Checklist Item")
		frappe.db.delete("Tender Bid")

	def _make_bid(self, **kwargs):
		doc = frappe.get_doc(
			{
				"doctype": "Tender Bid",
				"user": "Administrator",
				"tender_slug": kwargs.pop("tender_slug", "ocds-compliance-test"),
				"status": "Watching",
				**kwargs,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def test_universal_rules_seed_checklist(self):
		from {app_name}.tender.control.compliance.checklist import sync_compliance_checklist

		bid = self._make_bid()
		sync_compliance_checklist(bid)
		codes = {row.rule_code for row in bid.checklist if row.rule_code}
		self.assertIn("GATE-CSD", codes)
		self.assertIn("KILL-01", codes)
		# Conditional municipal gate must NOT appear on a regime-less bid
		self.assertNotIn("GATE-RATES", codes)
		# Idempotent
		before = len(bid.checklist)
		self.assertEqual(sync_compliance_checklist(bid), 0)
		self.assertEqual(len(bid.checklist), before)

	def test_regime_and_value_triggers(self):
		from {app_name}.tender.control.compliance.checklist import sync_compliance_checklist

		bid = self._make_bid(tender_slug="ocds-mbd-test", regime="MBD", estimated_value=12000000)
		sync_compliance_checklist(bid)
		codes = {row.rule_code for row in bid.checklist if row.rule_code}
		self.assertIn("GATE-RATES", codes)
		self.assertIn("GATE-MBD5", codes)

	def test_buyer_triggers_seed_checklist(self):
		# v3: the cached OCDS buyer name (institution) drives buyer-conditional
		# gates - an Eskom bid picks up the B-BBEE pre-qual check and the
		# Integrity Pact returnable; a buyer-less bid picks up neither
		from {app_name}.tender.control.compliance.checklist import sync_compliance_checklist

		bid = self._make_bid(tender_slug="ocds-eskom-test", institution="ESKOM HOLDINGS SOC LTD")
		sync_compliance_checklist(bid)
		codes = {row.rule_code for row in bid.checklist if row.rule_code}
		self.assertIn("GATE-BBBEE-PREQUAL", codes)
		self.assertIn("GATE-INTEGRITY-PACT", codes)
		self.assertNotIn("GATE-SECURITY-VETTING", codes)

		plain = self._make_bid(tender_slug="ocds-plain-test")
		sync_compliance_checklist(plain)
		plain_codes = {row.rule_code for row in plain.checklist if row.rule_code}
		self.assertNotIn("GATE-BBBEE-PREQUAL", plain_codes)
		self.assertNotIn("GATE-INTEGRITY-PACT", plain_codes)
		# the v3 universal rules land everywhere
		self.assertIn("PRICE-VAT", plain_codes)
		self.assertIn("FORM-VALIDITY", plain_codes)
		self.assertIn("SCORE-PREF-CLAIM", plain_codes)
