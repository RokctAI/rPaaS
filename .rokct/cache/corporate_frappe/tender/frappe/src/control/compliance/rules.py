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

"""Rule loading and deterministic applicability matching.

Rules are Tender Compliance Rule records (fixture-shipped, desk-editable).
A rule applies to a bid when:

- it is enabled, AND
- its ``regimes`` list (comma-separated regime codes) is empty or intersects
  the bid's regime SET - the base ``regime`` plus the optional
  ``overlay_regime`` (F-01: e.g. an MBD bid carrying a CIDB overlay matches
  rules fenced to either code; single-regime bids behave exactly as before,
  the widening is pure), AND
- its scope is Universal, or its scope is Conditional and its JSON
  ``trigger_condition`` matches the bid context (see ``condition_matches``).

``condition_matches`` semantics (pure data comparison, no AI):

- ``"<field>_over": N``  -> context[field] is set and > N
- ``"<field>_under": N`` -> context[field] is set and <= N
- ``"<field>_matches": [p, q]`` -> normalized (lowercased, whitespace-collapsed)
  context[field] CONTAINS any normalized pattern - used for buyer matching on
  the bid's ``institution`` (the OCDS buyer name cached from the tender feed)
  and for subject-matter matching on the bid's ``subject`` (the cached tender
  title/description text). Patterns are fixture data; no buyer name or
  subject keyword is ever hard-coded here.
- ``"<field>": [a, b]``  -> context[field] in [a, b]
- ``"<field>": value``   -> context[field] == value
- ``"any_of": [c1, c2]`` -> at least one sub-condition dict matches (each
  evaluated with these same semantics). This is the OR combinator the
  wave-1 fixture deltas use: e.g. GATE-RATES fires on the MBD regime OR a
  water-board buyer, GATE-POPIA on its buyer list OR a personal-information
  subject. An empty/non-list ``any_of`` never matches.

A Conditional rule with neither a parsable trigger nor a regime restriction
never auto-applies - it stays desk-visible guidance a human can act on.
"""

import json

import frappe
from frappe.utils import cint, flt

SEVERITY_ORDER = {"Fatal": 0, "Curable": 1, "Points-only": 2}

# --- Country fixture packs (assessment plan #15) ----------------------------
#
# A country is a FIXTURE PACK: the shipped Tender Compliance Rule / Tender
# Form Regime / Tender Form Template / Tender Workflow Template fixtures are
# the SOUTH AFRICA (ZA) pack - MBD/SBD/CIDB regimes, PPPFA preference
# points, CIDB grading, the lot. Tender Control Settings.tender_country
# scopes them: with the default South Africa everything behaves exactly as
# before; any other configured country has NO shipped pack yet, so the SA
# rules must never fire there - rule loading returns an honest empty set
# instead of implying configurability that does not exist. Shipping another
# country = shipping its fixture pack + listing it here; no code changes to
# the rule engine itself.
#
# tasks.py mirrors this tuple (its module is exec'd standalone by
# verify_wave3, so it cannot import this one); verify_hygiene cross-checks
# the two copies stay identical.
FIXTURE_PACK_COUNTRIES = ("South Africa", "ZA")
DEFAULT_TENDER_COUNTRY = "South Africa"


def fixture_pack_country():
	"""The configured Tender Control Settings.tender_country, defaulting to
	South Africa. Stub-safe: any lookup failure (no site context, standalone
	verify runs against an in-memory frappe stub) means the default."""
	try:
		configured = frappe.db.get_single_value("Tender Control Settings", "tender_country")
	except Exception:
		configured = None
	return str(configured or "").strip() or DEFAULT_TENDER_COUNTRY


def fixture_pack_active(country=None):
	"""True when a shipped fixture pack covers the (or the active) country."""
	return (country or fixture_pack_country()) in FIXTURE_PACK_COUNTRIES


def parse_json_field(raw):
	"""Parses a JSON Code field defensively; returns {} / None on bad data."""
	if not raw:
		return {}
	if isinstance(raw, dict):
		return raw
	try:
		parsed = json.loads(raw)
	except (TypeError, ValueError):
		return {}
	return parsed if isinstance(parsed, dict) else {}


def parse_regimes(raw):
	"""Splits the comma-separated regimes field into a set of codes."""
	if not raw:
		return set()
	return {part.strip().upper() for part in str(raw).split(",") if part.strip()}


def normalize_text(value):
	"""Lowercases and collapses whitespace for deterministic text comparison."""
	return " ".join(str(value or "").lower().split())


def text_matches_any(actual, patterns):
	"""True when the normalized actual text contains any normalized pattern.

	A plain substring test over normalized text - deterministic and desk-
	auditable. Patterns come from fixture data (e.g. a rule's trigger
	condition listing buyer-name fragments); an empty/missing actual value
	or pattern list never matches.
	"""
	if actual is None or not patterns:
		return False
	haystack = normalize_text(actual)
	if not haystack:
		return False
	if isinstance(patterns, str):
		patterns = [patterns]
	for pattern in patterns:
		needle = normalize_text(pattern)
		if needle and needle in haystack:
			return True
	return False


def condition_matches(condition, context):
	"""Deterministically matches a trigger-condition dict against a context dict."""
	if not condition:
		return False
	for key, expected in condition.items():
		if key == "any_of":
			if not isinstance(expected, list):
				return False
			if not any(
				isinstance(sub, dict) and sub and condition_matches(sub, context)
				for sub in expected
			):
				return False
		elif key.endswith("_matches"):
			field = key[: -len("_matches")]
			if not text_matches_any(context.get(field), expected):
				return False
		elif key.endswith("_over"):
			field = key[: -len("_over")]
			actual = context.get(field)
			if actual is None or flt(actual) <= flt(expected):
				return False
		elif key.endswith("_under"):
			field = key[: -len("_under")]
			actual = context.get(field)
			if actual is None or flt(actual) > flt(expected):
				return False
		elif isinstance(expected, list):
			if context.get(key) not in expected:
				return False
		else:
			if context.get(key) != expected:
				return False
	return True


def rule_applies(rule, context):
	"""True when a Tender Compliance Rule record applies to the bid context."""
	if not cint(rule.get("enabled")):
		return False

	regimes = parse_regimes(rule.get("regimes"))
	if regimes:
		bid_regimes = {
			(context.get("regime") or "").upper(),
			(context.get("overlay_regime") or "").upper(),
		} - {""}
		if not regimes & bid_regimes:
			return False

	if rule.get("scope") == "Universal":
		return True

	condition = parse_json_field(rule.get("trigger_condition"))
	if condition:
		return condition_matches(condition, context)

	# Conditional with a regime restriction only: the regime match above
	# already succeeded, so the rule applies.
	return bool(regimes)


def bid_context(bid):
	"""Builds the deterministic matching context from a Tender Bid document.

	``subject`` is the bid's cached tender text (title today; description too
	once a bid carries one) so subject-matter rules can fire on WHAT is being
	procured, not only on WHO is buying - e.g. a POPIA rule on a helpdesk/
	website-hosting tender. Still a plain field comparison, no AI.

	``regime_codes`` is the joined base+overlay code text (F-01, e.g.
	"MBD CIDB") so ``regime_codes_matches`` trigger conditions can fire on
	EITHER code of a dual-regime bid; the existing ``regime`` value keeps its
	exact single-code semantics, untouched.
	"""
	subject_parts = [
		str(part)
		for part in (bid.get("tender_title"), bid.get("tender_description"))
		if part not in (None, "")
	]
	regime_parts = [
		str(part)
		for part in (bid.get("regime"), bid.get("overlay_regime"))
		if part not in (None, "")
	]
	return {
		"regime": bid.get("regime"),
		"overlay_regime": bid.get("overlay_regime"),
		"regime_codes": " ".join(regime_parts) or None,
		"estimated_value": bid.get("estimated_value"),
		# F-06: multi-year term matching - PRICE-MULTIYEAR-ESC triggers on
		# {"contract_term_months_over": 12} through the existing _over
		# operator; unset/0 terms never fire it.
		"contract_term_months": bid.get("contract_term_months") or None,
		"institution": bid.get("institution"),
		# F-08: "Full" / "Advert-Only" classification of the catalog record
		# the bid was created from (set by claim_tender via
		# compliance/enrichment_gate.py) - GATE-PACK-COLLECT triggers on
		# {"source_record_class": "Advert-Only"}. Plain equality, no AI.
		"source_record_class": bid.get("source_record_class"),
		"status": bid.get("status"),
		"tender_title": bid.get("tender_title"),
		"subject": " ".join(subject_parts) or None,
	}


def load_rules(rule_class=None):
	"""Loads enabled Tender Compliance Rule records, Fatal-first.

	Country-scoped (plan #15): when the configured tender_country has no
	shipped fixture pack, NO rules load - an honest empty set, never SA
	rules applied abroad. The South Africa default keeps the full set.
	"""
	if not fixture_pack_active():
		return []
	filters = {"enabled": 1}
	if rule_class:
		filters["rule_class"] = rule_class
	rules = frappe.get_all(
		"Tender Compliance Rule",
		filters=filters,
		fields=[
			"name",
			"rule_code",
			"title",
			"rule_class",
			"scope",
			"severity",
			"enabled",
			"regimes",
			"trigger_condition",
			"artifact_type",
			"freshness_days",
			"checklist_text",
			"params",
			"guide_ref",
		],
	)
	rules.sort(key=lambda r: (SEVERITY_ORDER.get(r.get("severity"), 9), r.get("rule_code") or ""))
	return rules


def get_applicable_rules(bid, rule_class=None):
	"""Enabled rules that apply to this bid, Fatal-first then by rule_code."""
	context = bid_context(bid)
	return [rule for rule in load_rules(rule_class) if rule_applies(rule, context)]


def get_scoring_rule(rule_code):
	"""Loads one Scoring Rule's params dict by rule_code, or None.

	Country-scoped like load_rules (plan #15): the shipped scoring rules
	(PPPFA 80/20 / 90/10 machinery) are the SA pack - None outside it.
	"""
	if not fixture_pack_active():
		return None
	if not frappe.db.exists("Tender Compliance Rule", rule_code):
		return None
	rule = frappe.get_doc("Tender Compliance Rule", rule_code)
	if not cint(rule.enabled):
		return None
	return parse_json_field(rule.params)
