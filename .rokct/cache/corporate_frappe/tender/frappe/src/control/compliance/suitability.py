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

"""Automated suitability scoring (opportunities FEEDBACK.md section 1.2).

Two-stage worth-bidding triage of one opportunity card (tender / grant /
equity, as published in the opportunities catalog) against the bidder's
Tender Business Profile. The model is the MERGED design from the two
2026-08-23 research passes (see ``tender/Suitability-Scoring-Model.md``):
the corpus research pass over 1,990 live cards plus the independent
PR-blind research report (``tender/Suitability-Scoring-Research.md``).

Everything here is pure data comparison: fixture-shipped compliance rules,
regex extraction with hard whitelists, plain substring matching over
normalized text. No AI, no network, no fuzzy middle - the same doctrine as
``rules.py`` and the F-02 pack parser.

**Stage 1 - hard gates (unweighted).** Any firing gate means the card is
not winnable at any fit score: band ``no_bid``, NO numeric score (a number
would imply comparability that does not exist), all firing reasons
returned. Gates fire only on positive evidence - an unknown never fails a
gate, it lowers confidence or surfaces as a manual check instead:

- closing date already passed;
- compulsory briefing already held (``is_it_compulsory`` = Yes and a REAL
  past ``briefing_date_and_time``; placeholder dates like 0001-01-01 are
  unknowns - they flag data hygiene, never gate);
- CIDB (statutory): category-triggered via GATE-CIDB for ungraded
  profiles; exact class-and-grade comparison where a required grading is
  quoted; one-grade-below is a JV-conditional pass (manual check), a
  graded profile against an unquoted grade passes provisionally (manual
  check);
- B-BBEE pre-qualification: buyer-fixture trigger UNION quoted
  pre-qualification evidence from pack/enrichment lines; level *mentions*
  (points tables) never gate;
- profile completeness (CSD / TCS PIN / CIPC): profile-side, reported ONCE
  as ``profile_completeness`` - the remedy is fixing the profile, not
  skipping the tender.

**Stage 2 - fit score 0-100** over seven factors (``FIT_WEIGHTS``),
renormalised over the factors actually KNOWN - an unknown factor
redistributes its weight instead of silently scoring:

- ``sector_fit`` (30): continuous token-overlap of declared operating
  sectors vs the card's category/title/focus text;
- ``readiness`` (20): the demanded returnables parsed from enrichment
  demand lines (8 parseable demand types) vs profile evidence - the
  officer's gap list; neutral (unknown) when unenriched;
- ``process_feasibility`` (15): days-to-close, attendable compulsory
  briefing, submission effort gates (vetting / integrity pact /
  insurance);
- ``geography_fit`` (15): declared provinces vs the card province,
  national matches all;
- ``buyer_burden`` (10): buyer type plus applicable QUIRK fixture rules,
  refined (additively - the fixture base rules always stand) by the real
  per-buyer award-outcome stats where the buyer resolves in the derived
  awards tables (``market_context.py``);
- ``engagement_economics`` (10): tender type (RFQ vs open tender) and
  stated contract duration where present;
- ``pack_informed`` (10): functionality threshold (fixed extractor
  covering the quoted no-percent forms), preference system and document
  fees - defined only when pack/enrichment text exists.

Every tender payload additionally carries a ``market_context`` block
(resolved by ``market_context.py`` from the derived awards reference
tables - typical winning-price band with its table level, buyer
publication behaviour, entrant share): market colour beside the score,
never a gate and never a win predictor.

Bands: ``strong`` (>= 80), ``review`` (60-79), ``marginal`` (40-59),
``poor`` (< 40), ``no_bid`` (gated). Every payload carries ``confidence``
(``pack_verified`` | ``advert_only``) and ``days_to_close``; on
advert-only cards the score's first job is triage - ranking which packs
to fetch, then re-scoring at full confidence after pack collection.

Grants gate on jurisdiction first, then score on fit; equity funders have
no deadlines so they get standing-fit shortlist semantics (no urgency
factors). The score NEVER predicts winning - under PPR 2022 price takes
80/90 of 100 points and neither the bidder's price nor competitors' is
knowable from an advert.
"""

import datetime
import re

from frappe.utils import cint

# Same-package imports (F-09 pattern): relative on a composed bench, importlib
# fallback keeps this module importable standalone by file path.
try:
	from .rules import normalize_text, rule_applies
	from .enrichment_gate import classify_source_record, ADVERT_ONLY
	from . import market_context as market_context_module
except ImportError:  # standalone by-path import - load the siblings directly
	import importlib.util as _importlib_util
	import os as _os

	def _load_sibling(_module_name, _filename):
		_spec = _importlib_util.spec_from_file_location(
			_module_name,
			_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), _filename),
		)
		_module = _importlib_util.module_from_spec(_spec)
		_spec.loader.exec_module(_module)
		return _module

	_rules = _load_sibling("tender_suitability_rules", "rules.py")
	_enrichment_gate = _load_sibling("tender_suitability_enrichment_gate", "enrichment_gate.py")
	market_context_module = _load_sibling(
		"tender_suitability_market_context", "market_context.py"
	)
	normalize_text = _rules.normalize_text
	rule_applies = _rules.rule_applies
	classify_source_record = _enrichment_gate.classify_source_record
	ADVERT_ONLY = _enrichment_gate.ADVERT_ONLY


# --------------------------------------------------------------------------
# Score model constants
# --------------------------------------------------------------------------

# Stage-2 fit factors. Weights are argued from prevalence x discrimination
# over the 2026-08-23 corpus (no award-outcome data exists to fit against);
# the merged-model decision record carries the evidence per factor.
FIT_WEIGHTS = {
	"sector_fit": 30,
	"readiness": 20,
	"process_feasibility": 15,
	"geography_fit": 15,
	"buyer_burden": 10,
	"engagement_economics": 10,
	"pack_informed": 10,
}

BAND_STRONG = 80
BAND_REVIEW = 60
BAND_MARGINAL = 40
BAND_NO_BID = "no_bid"

CONFIDENCE_PACK_VERIFIED = "pack_verified"
CONFIDENCE_ADVERT_ONLY = "advert_only"

# A briefing/closing date whose year predates this is a registry
# placeholder (0001-01-01 pattern: 37 compulsory-briefing cards live), not
# evidence that anything happened - positive-evidence handling treats it
# as unknown and flags it for source re-verification.
PLACEHOLDER_YEAR_FLOOR = 1900

# Corpus defaults mirrored from the SCORE-FUNCTIONALITY fixture params
# (functionality-thresholds.csv, 238 observations); the fixture wins when the
# caller passes the live params.
DEFAULT_FUNCTIONALITY_PARAMS = {
	"threshold_default_pct": 70,
	"threshold_mode_pct": 70,
	"threshold_median_pct": 70,
	"threshold_min_observed": 36,
	"threshold_max_observed": 100,
	"observations": 238,
}

# CIDB contractor grading: designation whitelist so free text like
# "Grade 12" (a school certificate) can never read as a grading. Same
# hard-whitelist doctrine as the protocol-side enrichment extractor.
CIDB_CLASS_CODES = (
	"GB", "CE", "ME", "EP", "EB",
	"SB", "SC", "SD", "SE", "SF", "SG", "SH", "SI", "SJ",
	"SK", "SL", "SM", "SN", "SO", "SQ",
)

RE_CIDB = re.compile(
	r"\b(?:grade\s*)?([1-9])\s*(" + "|".join(CIDB_CLASS_CODES) + r")\b",
	re.IGNORECASE,
)

# Functionality threshold extraction - quoted-or-nothing whitelist.
# The percent form is kept; the no-percent forms cover how the live
# enrichment corpus actually quotes thresholds ("minimum functionality
# threshold of 80", "ACCEPTABLE MINIMUM SCORE 60", "Minimum Required
# Score for functionality is: 60") - the original percent-only pattern
# fired on 0 of 372 live enrichment entries.
RE_FUNCTIONALITY_PCT = re.compile(
	r"functionality[^.\n]{0,120}?\b(\d{1,3})\s*%", re.IGNORECASE
)
RE_FUNCTIONALITY_NO_PCT_FORMS = (
	# "minimum functionality threshold of 80"
	re.compile(r"functionality\s+threshold\s+of\s+(\d{1,3})\b", re.IGNORECASE),
	# "Minimum Required Score for functionality is: 60"
	re.compile(r"minimum\s+required\s+score[^0-9\n]{0,40}?(\d{1,3})\b", re.IGNORECASE),
	# "ACCEPTABLE MINIMUM SCORE 60" / "minimum acceptable score of 60"
	re.compile(
		r"(?:acceptable|minimum)\s+(?:minimum\s+|acceptable\s+)?"
		r"(?:qualifying\s+)?score[^0-9\n]{0,15}(\d{1,3})\b",
		re.IGNORECASE,
	),
)
# Guard: a no-percent number is only trusted on a line that is actually
# talking about a functionality/qualifying bar.
FUNCTIONALITY_LINE_TOKENS = (
	"functionality", "minimum score", "qualifying score",
	"minimum required score", "acceptable minimum",
)
# Observed corpus band is 36-100; a bare no-percent number below 30 is
# more likely raw points on a non-100 scale, so it is never trusted.
FUNCTIONALITY_NO_PCT_FLOOR = 30

# B-BBEE pre-qualification evidence: a quoted line must carry BOTH a
# B-BBEE token and a pre-qualification token. Plain level mentions
# (points tables enumerate every level) never count - gating on them
# would disqualify bidders from tenders that merely publish a points
# table (the over-enumeration trap).
RE_BBBEE_TOKEN = re.compile(r"\bb[- ]?bbee\b", re.IGNORECASE)
RE_PREQUAL_TOKEN = re.compile(r"pre[- ]?qualif", re.IGNORECASE)

# Contract duration: "36 months" style statements on the card title or
# enrichment lines. Multi-year terms signal recurring-revenue fit.
RE_DURATION_MONTHS = re.compile(r"\b(\d{1,3})\s*months?\b", re.IGNORECASE)

# Document fee: an explicit rand amount on a line mentioning a fee.
RE_FEE_RAND = re.compile(r"\bR\s?(\d{2,6})(?:\.\d{2})?\b")
FEE_LINE_TOKENS = ("non-refundable", "non refundable", "document fee", "tender fee", "deposit fee")

# Preference system statements (quoted-or-nothing).
RE_PREF_8020 = re.compile(r"\b80\s*/\s*20\b")
RE_PREF_9010 = re.compile(r"\b90\s*/\s*10\b")

# Fatal, profile-checkable universal gates: rule_code -> (field, label).
# These form the present-once profile_completeness block.
PROFILE_GATE_FIELDS = {
	"GATE-CSD": ("csd_maaa_number", "CSD registration (MAAA number)"),
	"GATE-TCS": ("tcs_pin", "SARS Tax Compliance Status PIN"),
	"GATE-CIPC": ("company_registration_no", "CIPC company registration"),
}

# Submission-effort gates: applicable rules that are satisfiable with
# effort (so effort signals, never exclusions) - each deducts from
# process_feasibility and stays visible as its own manual check.
EFFORT_GATE_PENALTIES = {
	"GATE-SECURITY-VETTING": 0.10,
	"GATE-INTEGRITY-PACT": 0.10,
	"GATE-INSURANCE": 0.10,
}

# Readiness: the 8 demand types parseable from enrichment demand lines,
# each mapped to the profile evidence field that answers it.
READINESS_DEMANDS = (
	("tax", re.compile(r"tax compliance|sars.{0,20}pin|tcs pin", re.IGNORECASE),
		"tcs_pin", "SARS tax compliance (TCS PIN)"),
	("csd", re.compile(r"\bcsd\b|central supplier|\bmaaa\b", re.IGNORECASE),
		"csd_maaa_number", "CSD registration report"),
	("bbbee", re.compile(r"\bb[- ]?bbee\b", re.IGNORECASE),
		"bbbee_level", "B-BBEE certificate / sworn affidavit"),
	("rates", re.compile(r"municipal (?:rates|accounts)|rates.{0,20}clearance", re.IGNORECASE),
		"municipal_rates_current", "Municipal rates account (< 90 days)"),
	("coida", re.compile(r"\bcoida\b|compensation fund", re.IGNORECASE),
		"coida_good_standing", "COIDA letter of good standing"),
	("psira", re.compile(r"\bpsira\b", re.IGNORECASE),
		"psira_registered", "PSIRA registration"),
	("nhbrc", re.compile(r"\bnhbrc\b", re.IGNORECASE),
		"nhbrc_registered", "NHBRC registration"),
	("experience", re.compile(
		r"trinity of evidence|previous projects|track record|reference site", re.IGNORECASE),
		"track_record_evidence", "Track-record / experience evidence"),
)

# Grant jurisdiction gate: explicit, whitelisted non-SA jurisdiction
# statements on the card text ("... in New Zealand", "US-based ... only").
# Positive evidence only - an unstated jurisdiction never gates, it
# surfaces as a manual check.
GRANT_FOREIGN_JURISDICTIONS = (
	"new zealand", "canada", "australia", "united states", "usa",
	"united kingdom", "uk companies", "ireland", "malta", "cyprus",
	"singapore", "india", "nigeria", "kenya", "ghana", "european union",
	"eu member", "eu-based", "europe-based",
)
GRANT_SA_TOKENS = ("south africa", "african", "africa", "global", "worldwide", "international")

# Equity territory tokens an SA-based bidder can reach.
EQUITY_TERRITORY_FULL = ("south africa", "global", "worldwide")
EQUITY_TERRITORY_PARTIAL = ("africa", "sub-saharan", "emerging markets")

# Buyer-type whitelist (structured institution names, not free keywords):
# municipal buyers add rates-clearance windows and single-shot cure
# culture on top of the universal spine.
MUNICIPAL_TOKENS = ("municipality", "municipal", "metropolitan", "district")


# --------------------------------------------------------------------------
# Deterministic extraction helpers
# --------------------------------------------------------------------------

def parse_card_datetime(value):
	"""Parses a catalog date/datetime string to a ``datetime``, else None.

	Accepts "YYYY-MM-DD" and "YYYY-MM-DD HH:MM" (the two live catalog
	formats). Unparseable text ("See Documents", "N/A") returns None.
	Placeholder dates parse - callers must check ``is_placeholder_date``
	before treating a parsed date as evidence.
	"""
	text = str(value or "").strip()
	for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
		try:
			return datetime.datetime.strptime(text[: len(fmt.replace("%Y", "0000"))], fmt)
		except ValueError:
			continue
	return None


def is_placeholder_date(value):
	"""True when the date parses but is a registry placeholder (year < 1900).

	0001-01-01 briefing dates are UNKNOWN, not evidence a briefing was
	held - the positive-evidence rule (37 live compulsory-briefing cards).
	"""
	parsed = parse_card_datetime(value)
	return bool(parsed) and parsed.year < PLACEHOLDER_YEAR_FLOOR


def parse_real_past_date(value, today):
	"""Returns the parsed datetime when it is REAL (non-placeholder) and
	strictly before today, else None."""
	parsed = parse_card_datetime(value)
	if not parsed or parsed.year < PLACEHOLDER_YEAR_FLOOR:
		return None
	today_parsed = parse_card_datetime(today)
	if not today_parsed:
		return None
	return parsed if parsed.date() < today_parsed.date() else None


def compute_days_to_close(card, today):
	"""Days from today to the card's closing date; None when unparseable."""
	closing = parse_card_datetime((card or {}).get("closing_date") or (card or {}).get("deadline"))
	today_parsed = parse_card_datetime(today)
	if not closing or closing.year < PLACEHOLDER_YEAR_FLOOR or not today_parsed:
		return None
	return (closing.date() - today_parsed.date()).days


def parse_cidb_requirement(texts):
	"""Extracts a CIDB grading requirement from requirement/task lines.

	Returns ``{"grade": int, "class_code": str, "quoted": line}`` for the
	first line that both mentions CIDB and carries a whitelisted grading
	token (e.g. "1CE", "Grade 7 GB"), else None. Quoted-or-nothing - the
	F-02 doctrine.
	"""
	for raw in texts or []:
		line = str(raw or "")
		if "cidb" not in line.lower():
			continue
		match = RE_CIDB.search(line)
		if match:
			return {
				"grade": int(match.group(1)),
				"class_code": match.group(2).upper(),
				"quoted": line.strip(),
			}
	return None


def parse_profile_cidb_grade(raw):
	"""Parses the profile's free-text ``cidb_grade`` field (e.g. "4CE").

	Returns ``{"grade": int, "class_code": str}`` or None when the field is
	empty or not a recognisable grading.
	"""
	if not raw:
		return None
	match = RE_CIDB.search(str(raw))
	if not match:
		return None
	return {"grade": int(match.group(1)), "class_code": match.group(2).upper()}


def parse_functionality_threshold(texts):
	"""Extracts a functionality threshold from requirement lines.

	Returns ``{"threshold_pct": int, "quoted": line, "form": str}`` for the
	first line carrying an affirmative threshold statement, else None.
	Two whitelisted families: the percent form ("functionality ... NN%",
	NN in 1..100) and the quoted no-percent forms the live enrichment
	corpus uses ("minimum functionality threshold of 80", "ACCEPTABLE
	MINIMUM SCORE 60", "Minimum Required Score for functionality is: 60";
	NN in 30..100 - lower bare numbers are likely raw points on a
	non-100 scale and are never trusted). A bare number on a line that
	never talks about a functionality/qualifying bar is never trusted.
	"""
	for raw in texts or []:
		line = str(raw or "")
		lowered = line.lower()
		if not any(token in lowered for token in FUNCTIONALITY_LINE_TOKENS):
			continue
		match = RE_FUNCTIONALITY_PCT.search(line)
		if match:
			value = int(match.group(1))
			if 1 <= value <= 100:
				return {"threshold_pct": value, "quoted": line.strip(), "form": "percent"}
		for pattern in RE_FUNCTIONALITY_NO_PCT_FORMS:
			match = pattern.search(line)
			if match:
				value = int(match.group(1))
				if FUNCTIONALITY_NO_PCT_FLOOR <= value <= 100:
					return {
						"threshold_pct": value,
						"quoted": line.strip(),
						"form": "no_percent",
					}
	return None


def parse_bbbee_prequal_evidence(texts):
	"""Returns ``{"quoted": line}`` for the first line quoting a B-BBEE
	PRE-QUALIFICATION statement, else None.

	The line must carry both a B-BBEE token and a pre-qualification token.
	Level mentions alone (preference-points tables enumerate every level)
	NEVER count as gate evidence - the over-enumeration trap.
	"""
	for raw in texts or []:
		line = str(raw or "")
		if RE_BBBEE_TOKEN.search(line) and RE_PREQUAL_TOKEN.search(line):
			return {"quoted": line.strip()}
	return None


def parse_contract_duration_months(card, texts):
	"""Largest "NN months" statement on the card title or task lines, else None."""
	best = None
	sources = [str((card or {}).get("title") or "")] + [str(t or "") for t in (texts or [])]
	for line in sources:
		for match in RE_DURATION_MONTHS.finditer(line):
			months = int(match.group(1))
			if 1 <= months <= 240 and (best is None or months > best):
				best = months
	return best


def parse_document_fee(texts):
	"""Explicit rand-amount document fee on a fee-mentioning line, else None."""
	for raw in texts or []:
		line = str(raw or "")
		lowered = line.lower()
		if not any(token in lowered for token in FEE_LINE_TOKENS):
			continue
		match = RE_FEE_RAND.search(line)
		if match:
			return {"amount_rand": int(match.group(1)), "quoted": line.strip()}
	return None


def enrichment_task_texts(enrichment_entry):
	"""Flattens an advanced_enrichment entry's task lines to plain strings.

	Task lines are published as "text | N" (weight suffix); the suffix is
	harmless to the extractors so lines are passed through as-is.
	"""
	if not isinstance(enrichment_entry, dict):
		return []
	return [str(task) for task in (enrichment_entry.get("tasks") or []) if task]


def card_context(card, enrichment_entry=None):
	"""Builds the rules-matching context for a published catalog card.

	The card has no bid yet, so the context mirrors ``rules.bid_context``
	minus bid-only fields: buyer-triggered and subject-triggered rules fire,
	regime- and value-fenced rules stay silent (unknowable from an advert).
	"""
	card = card or {}
	subject_parts = [
		str(part)
		for part in (card.get("title"), card.get("category"), card.get("tender_type"))
		if part not in (None, "")
	]
	return {
		"regime": None,
		"overlay_regime": None,
		"regime_codes": None,
		"estimated_value": None,
		"contract_term_months": None,
		"institution": card.get("institution") or card.get("organization"),
		"source_record_class": classify_source_record(card, enrichment_entry),
		"status": card.get("status"),
		"tender_title": card.get("title"),
		"subject": " ".join(subject_parts) or None,
	}


def _split_tokens(raw):
	"""Splits a comma/newline-separated Small Text field into clean tokens."""
	if not raw:
		return []
	parts = re.split(r"[,\n;]", str(raw))
	return [part.strip() for part in parts if part.strip()]


def _is_expired(date_text, today):
	"""True when both dates are set and date_text < today (ISO strings)."""
	if not date_text or not today:
		return False
	return str(date_text)[:10] < str(today)[:10]


def _has_evidence(profile, fieldname):
	"""True when a profile evidence field is affirmatively set.

	Check fields snapshot as "1"/"" (or arrive as 1/0); Data fields as
	text. "0"/"no"/"false" never count as evidence.
	"""
	value = str((profile or {}).get(fieldname) or "").strip().lower()
	return value not in ("", "0", "no", "false", "none")


# --------------------------------------------------------------------------
# Per-gate profile checks
# --------------------------------------------------------------------------

def check_cidb_gate(profile, cidb_requirement):
	"""Checks the profile's CIDB grading against a parsed requirement.

	Returns (status, detail); status is one of:

	- ``satisfied``: exact class, grade >= required;
	- ``conditional``: same class, exactly ONE grade below - biddable only
	  via a JV with a suitably graded lead partner (the JV rule); never a
	  clean pass, always a manual check;
	- ``provisional``: gate fired on subject/category only (no quoted
	  grade) and the profile holds SOME grading - passes provisionally,
	  the exact class/grade must be verified from the pack;
	- ``unsatisfied``: everything else. CIDB registration is statutory for
	  public construction works, so a category-triggered gate with an
	  ungraded profile fails even when the advert never states the grade.
	"""
	held = parse_profile_cidb_grade(profile.get("cidb_grade"))
	if cidb_requirement:
		required = "{0}{1}".format(cidb_requirement["grade"], cidb_requirement["class_code"])
		if not held:
			return (
				"unsatisfied",
				"Tender requires CIDB {0} but the profile holds no readable CIDB grading "
				"(expected e.g. 4CE)".format(required),
			)
		if held["class_code"] != cidb_requirement["class_code"]:
			return (
				"unsatisfied",
				"Tender requires CIDB class {0} (grade {1}); profile grading {2}{3} is a "
				"different works class".format(
					cidb_requirement["class_code"],
					cidb_requirement["grade"],
					held["grade"],
					held["class_code"],
				),
			)
		if held["grade"] >= cidb_requirement["grade"]:
			return (
				"satisfied",
				"Profile CIDB grading {0}{1} meets the required {2}".format(
					held["grade"], held["class_code"], required
				),
			)
		if held["grade"] == cidb_requirement["grade"] - 1:
			return (
				"conditional",
				"Profile grading {0}{1} is ONE grade below the required {2}: biddable only "
				"as a joint venture with a suitably graded lead partner (JV rule) - "
				"conditional, not a clean pass".format(
					held["grade"], held["class_code"], required
				),
			)
		return (
			"unsatisfied",
			"Tender requires CIDB {0} or higher; profile grading {1}{2} is below "
			"it".format(required, held["grade"], held["class_code"]),
		)
	if held:
		return (
			"provisional",
			"CIDB registration required (grade unstated in the advert) - profile holds "
			"{0}{1}; verify the exact class and grade in the tender pack".format(
				held["grade"], held["class_code"]
			),
		)
	return (
		"unsatisfied",
		"This is construction-category work: CIDB registration is statutory for public "
		"construction tenders and the profile holds no readable CIDB grading",
	)


def check_bbbee(profile, today=None):
	"""Checks the profile's B-BBEE status: level set, not expired.

	Returns (status, detail). The prequalification LEVEL demanded by a
	specific tender lives in its pack, so a valid certificate passes
	provisionally.
	"""
	level = str(profile.get("bbbee_level") or "").strip()
	if not level:
		return ("unsatisfied", "No B-BBEE level on the profile")
	if level.lower() == "non-compliant":
		return ("unsatisfied", "Profile B-BBEE status is Non-compliant")
	if _is_expired(profile.get("bbbee_certificate_expiry"), today):
		return (
			"unsatisfied",
			"Profile B-BBEE certificate expired on {0}".format(
				str(profile.get("bbbee_certificate_expiry"))[:10]
			),
		)
	return (
		"satisfied",
		"Profile holds B-BBEE level {0} - verify this tender's prequalification level "
		"in the pack".format(level),
	)


def check_profile_completeness(profile):
	"""The present-once profile-side gate: CSD / TCS PIN / CIPC.

	Returns ``{"complete": bool, "missing": [labels], "note": str}``. These
	universal Fatal gates apply identically to every public tender, so the
	payload reports them ONCE here instead of repeating them per card
	dimension. The Defaulters/Restricted-suppliers check is a register
	lookup with no profile counterpart - it stays in the grouped universal
	manual checks.
	"""
	missing = []
	for fieldname, label in PROFILE_GATE_FIELDS.values():
		if not str(profile.get(fieldname) or "").strip():
			missing.append(label)
	return {
		"complete": not missing,
		"missing": missing,
		"note": (
			"Profile-side gate: these registrations apply to EVERY public tender - "
			"the remedy is completing the business profile once, not skipping this card"
		),
	}


# --------------------------------------------------------------------------
# Stage 1 - hard gates (unweighted; fire only on positive evidence)
# --------------------------------------------------------------------------

def evaluate_hard_gates(
	card, profile, applicable_rules, task_texts, today, opportunity_type="tenders"
):
	"""Evaluates every hard gate and returns ALL firing reasons.

	Returns (hard_failures, gate_notes, manual_checks, data_flags):
	``hard_failures`` is the complete list of firing gate reasons (band
	``no_bid`` when non-empty); ``gate_notes`` are satisfied/conditional
	gate reasons worth surfacing; ``manual_checks`` are gate-derived
	manual checks (JV-conditional, provisional CIDB, placeholder
	briefing); ``data_flags`` are registry data-hygiene flags.
	"""
	card = card or {}
	profile = profile or {}
	hard_failures = []
	gate_notes = []
	manual_checks = []
	data_flags = []

	# --- closing date passed (all opportunity types with a date) ---
	closing_passed = parse_real_past_date(
		card.get("closing_date") or card.get("deadline"), today
	)
	if closing_passed:
		hard_failures.append({
			"code": "GATE-CLOSED",
			"status": "unsatisfied",
			"detail": "Closing date {0} has already passed".format(
				closing_passed.date().isoformat()
			),
		})

	if opportunity_type == "grants":
		jurisdiction = parse_grant_jurisdiction(card)
		if jurisdiction:
			hard_failures.append({
				"code": "GATE-JURISDICTION",
				"status": "unsatisfied",
				"detail": (
					"Grant is explicitly fenced to another jurisdiction ({0}): "
					"{1}".format(jurisdiction["jurisdiction"], jurisdiction["quoted"])
				),
			})
		else:
			manual_checks.append({
				"code": "GRANT-JURISDICTION",
				"severity": "Fatal",
				"title": "Grant jurisdiction unverified",
				"checklist_text": (
					"The card does not state an explicit jurisdiction fence - verify "
					"eligibility for South African applicants in the grant call itself"
				),
			})
		return hard_failures, gate_notes, manual_checks, data_flags

	if opportunity_type != "tenders":
		# Equity funders are standing counterparties: no deadlines, no gates.
		return hard_failures, gate_notes, manual_checks, data_flags

	# --- compulsory briefing already held (positive evidence only) ---
	if str(card.get("is_it_compulsory") or "").strip().lower() == "yes":
		briefing_raw = card.get("briefing_date_and_time")
		if is_placeholder_date(briefing_raw):
			data_flags.append({
				"code": "FLAG-BRIEFING-PLACEHOLDER",
				"detail": (
					"Compulsory briefing carries a placeholder date ({0}): whether it "
					"was already held is UNKNOWN - re-verify against the source advert "
					"(registry data hygiene)".format(str(briefing_raw)[:16])
				),
			})
			manual_checks.append({
				"code": "GATE-BRIEFING-HELD",
				"severity": "Fatal",
				"title": "Compulsory briefing date unknown (placeholder)",
				"checklist_text": (
					"The briefing date on this card is a registry placeholder - confirm "
					"the real compulsory-briefing date before committing effort"
				),
			})
		else:
			held = parse_real_past_date(briefing_raw, today)
			if held:
				hard_failures.append({
					"code": "GATE-BRIEFING-HELD",
					"status": "unsatisfied",
					"detail": (
						"Compulsory briefing was already held on {0} - attendance is "
						"pass/fail, so the bid cannot qualify".format(
							str(briefing_raw)[:16]
						)
					),
				})

	# --- CIDB (statutory; category-triggered via the fixture rule) ---
	cidb_applies = any(
		rule.get("rule_code") == "GATE-CIDB" for rule in applicable_rules or []
	)
	cidb_requirement = parse_cidb_requirement(task_texts)
	if cidb_applies or cidb_requirement:
		status, detail = check_cidb_gate(profile, cidb_requirement)
		reason = {"code": "GATE-CIDB", "status": status, "detail": detail}
		if status == "unsatisfied":
			hard_failures.append(reason)
		else:
			gate_notes.append(reason)
			if status in ("conditional", "provisional"):
				manual_checks.append({
					"code": "GATE-CIDB",
					"severity": "Fatal",
					"title": "CIDB grading needs manual confirmation",
					"checklist_text": detail,
				})

	# --- B-BBEE pre-qualification (buyer fixture UNION quoted pack evidence) ---
	prequal_rule_applies = any(
		rule.get("rule_code") == "GATE-BBBEE-PREQUAL" for rule in applicable_rules or []
	)
	prequal_evidence = parse_bbbee_prequal_evidence(task_texts)
	if prequal_rule_applies or prequal_evidence:
		status, detail = check_bbbee(profile, today)
		if prequal_evidence:
			detail += " [quoted: {0}]".format(prequal_evidence["quoted"])
		reason = {"code": "GATE-BBBEE-PREQUAL", "status": status, "detail": detail}
		if status == "unsatisfied":
			hard_failures.append(reason)
		else:
			gate_notes.append(reason)

	# --- profile completeness handled by the caller (present once) ---
	return hard_failures, gate_notes, manual_checks, data_flags


def parse_grant_jurisdiction(card):
	"""Explicit foreign-jurisdiction fence on a grant card, else None.

	Whitelisted jurisdiction names matched over title + focus_area; a
	South-Africa/Africa/global mention on the same text neutralises the
	match (the programme reaches SA applicants). Positive evidence only.
	"""
	haystack = normalize_text(" ".join(
		str(part)
		for part in ((card or {}).get("title"), (card or {}).get("focus_area"))
		if part
	))
	if not haystack:
		return None
	if any(token in haystack for token in GRANT_SA_TOKENS):
		return None
	for jurisdiction in GRANT_FOREIGN_JURISDICTIONS:
		for pattern in (
			"in " + jurisdiction,
			jurisdiction + " only",
			jurisdiction + "-based",
			jurisdiction + " based",
		):
			if pattern in haystack:
				return {"jurisdiction": jurisdiction, "quoted": pattern}
	return None


# --------------------------------------------------------------------------
# Stage 2 - fit factors (each returns (value 0..1 or None-unknown, reasons))
# --------------------------------------------------------------------------

def _factor_sector(card, profile):
	haystack = normalize_text(" ".join(
		str(part)
		for part in (
			card.get("category"),
			card.get("title"),
			card.get("focus_area"),
			card.get("industry"),
			card.get("tender_type"),
		)
		if part
	))
	sectors = _split_tokens(profile.get("operating_sectors"))
	matched = [
		token for token in sectors
		if normalize_text(token) and normalize_text(token) in haystack
	]
	if matched:
		# Continuous overlap: every extra matching declared sector deepens
		# the fit signal (0.85 for one token, 1.0 from two up).
		value = min(1.0, 0.7 + 0.15 * len(matched))
		return value, [{
			"code": "SECTOR-MATCH",
			"status": "satisfied",
			"detail": "Declared sector(s) match this opportunity: {0}".format(
				", ".join(matched)
			),
		}]
	capability_texts = [
		normalize_text(text) for text in (profile.get("capability_texts") or []) if text
	]
	capability_hits = [
		text for text in capability_texts
		if text and any(word in haystack for word in text.split() if len(word) >= 5)
	]
	if capability_hits:
		return 0.6, [{
			"code": "SECTOR-CAPABILITY",
			"status": "partial",
			"detail": "No declared sector matches, but capability-register entries "
			"overlap this opportunity's subject",
		}]
	if not sectors:
		return None, [{
			"code": "SECTOR-UNDECLARED",
			"status": "unknown",
			"detail": "No operating sectors declared on the profile - factor treated as "
			"unknown (weight redistributed); declare sectors for a sharper fit signal",
		}]
	return 0.1, [{
		"code": "SECTOR-MISMATCH",
		"status": "unsatisfied",
		"detail": "None of the declared sectors ({0}) match this opportunity's "
		"category/title".format(", ".join(sectors)),
	}]


def _factor_readiness(task_texts, profile, enriched):
	if not enriched or not task_texts:
		return None, [{
			"code": "READINESS-UNKNOWN",
			"status": "unknown",
			"detail": "No pack/enrichment demand lines for this card - demanded "
			"returnables are unknown, factor weight redistributed (never silently "
			"awarded)",
		}]
	joined = "\n".join(task_texts)
	demanded = []
	evidenced = []
	gaps = []
	for _key, pattern, fieldname, label in READINESS_DEMANDS:
		if pattern.search(joined):
			demanded.append(label)
			if _has_evidence(profile, fieldname):
				evidenced.append(label)
			else:
				gaps.append(label)
	if not demanded:
		return None, [{
			"code": "READINESS-UNKNOWN",
			"status": "unknown",
			"detail": "No parseable document demands on this card's enrichment lines - "
			"factor weight redistributed",
		}]
	value = len(evidenced) / len(demanded)
	detail = "{0}/{1} demanded returnables evidenced on the profile".format(
		len(evidenced), len(demanded)
	)
	if gaps:
		detail += "; gaps: " + ", ".join(gaps)
	return value, [{
		"code": "READINESS-GAPLIST",
		"status": "satisfied" if not gaps else "partial",
		"detail": detail,
		"demanded": demanded,
		"evidenced": evidenced,
		"gaps": gaps,
	}]


def _factor_process(card, profile, applicable_rules, task_texts, today, days_to_close):
	value = 1.0
	notes = []
	if days_to_close is not None:
		if days_to_close <= 3:
			value -= 0.4
			notes.append("only {0} day(s) to close".format(days_to_close))
		elif days_to_close <= 7:
			value -= 0.25
			notes.append("{0} days to close (tight)".format(days_to_close))
		elif days_to_close <= 14:
			value -= 0.1
			notes.append("{0} days to close".format(days_to_close))
	else:
		notes.append("closing date unparseable on the card - verify from the documents")
	if str(card.get("is_it_compulsory") or "").strip().lower() == "yes":
		briefing = parse_card_datetime(card.get("briefing_date_and_time"))
		today_parsed = parse_card_datetime(today)
		if (
			briefing
			and briefing.year >= PLACEHOLDER_YEAR_FLOOR
			and today_parsed
			and briefing.date() >= today_parsed.date()
		):
			value -= 0.15
			notes.append(
				"compulsory briefing to attend on {0}".format(
					str(card.get("briefing_date_and_time"))[:16]
				)
			)
			province = normalize_text(card.get("province"))
			declared = [
				normalize_text(token)
				for token in _split_tokens(profile.get("operating_provinces"))
			]
			radius = normalize_text(profile.get("briefing_travel_radius"))
			if (
				radius.startswith("local")
				and province
				and province not in ("national", "all", "south africa", "n/a")
				and declared
				and not any(
					token and (token in province or province in token) for token in declared
				)
			):
				value -= 0.1
				notes.append(
					"briefing is outside the declared footprint and the profile's "
					"briefing travel radius is local-only"
				)
	for rule in applicable_rules or []:
		penalty = EFFORT_GATE_PENALTIES.get(rule.get("rule_code"))
		if penalty:
			value -= penalty
			notes.append(
				"{0} applies (satisfiable with effort - see manual checks)".format(
					rule.get("rule_code")
				)
			)
	for raw in task_texts or []:
		lowered = str(raw or "").lower()
		if "hand deliver" in lowered or "hand-deliver" in lowered:
			notes.append("hand delivery quoted in the demand lines")
			break
	return max(value, 0.0), [{
		"code": "PROCESS-FEASIBILITY",
		"status": "info",
		"detail": "; ".join(notes) or "standard process burden",
	}]


def _factor_geography(card, profile):
	province = normalize_text(
		card.get("province") or card.get("territory") or card.get("country")
	)
	provinces = _split_tokens(profile.get("operating_provinces"))
	if not province or province in ("national", "all", "south africa", "n/a"):
		return 1.0, [{
			"code": "GEO-NATIONAL",
			"status": "satisfied",
			"detail": "Opportunity is national / unspecified - open to all provinces",
		}]
	for token in provinces:
		normalized = normalize_text(token)
		if normalized and (normalized in province or province in normalized):
			return 1.0, [{
				"code": "GEO-MATCH",
				"status": "satisfied",
				"detail": "Profile operates in {0}".format(card.get("province")),
			}]
	if not provinces:
		return None, [{
			"code": "GEO-UNDECLARED",
			"status": "unknown",
			"detail": "No operating provinces declared on the profile - factor treated "
			"as unknown (weight redistributed); opportunity is in {0}".format(
				card.get("province")
			),
		}]
	return 0.1, [{
		"code": "GEO-MISMATCH",
		"status": "unsatisfied",
		"detail": "Opportunity is in {0}; profile declares {1}".format(
			card.get("province"), ", ".join(provinces)
		),
	}]


def _factor_equity_territory(card):
	"""Equity standing-fit geography: card territory/country vs an SA bidder."""
	haystack = normalize_text(" ".join(
		str(part)
		for part in (card.get("territory"), card.get("country"))
		if part
	))
	if not haystack:
		return None, [{
			"code": "GEO-UNDECLARED",
			"status": "unknown",
			"detail": "Funder territory unstated - factor weight redistributed",
		}]
	if any(token in haystack for token in EQUITY_TERRITORY_FULL):
		return 1.0, [{
			"code": "GEO-MATCH",
			"status": "satisfied",
			"detail": "Funder invests in {0}".format(
				card.get("territory") or card.get("country")
			),
		}]
	if any(token in haystack for token in EQUITY_TERRITORY_PARTIAL):
		return 0.8, [{
			"code": "GEO-PARTIAL",
			"status": "partial",
			"detail": "Funder territory ({0}) covers the region - confirm South Africa "
			"is in mandate".format(card.get("territory") or card.get("country")),
		}]
	return 0.1, [{
		"code": "GEO-MISMATCH",
		"status": "unsatisfied",
		"detail": "Funder territory is {0} - outside a South African bidder's "
		"reach".format(card.get("territory") or card.get("country")),
	}]


# Market-context buyer-burden refinement thresholds (derived awards
# tables, tender/Award-Outcomes-Research.md): additive on top of the
# QUIRK/municipal base rules, which always stand.
BUYER_INCUMBENCY_LOCKED_PCT = 50.0   # SANRAL-style at-buyer incumbency
BUYER_ENTRANT_FRIENDLY_PCT = 60.0    # entrant share where entry is normal


def _factor_buyer_burden(card, applicable_rules, buyer_stats=None):
	value = 1.0
	notes = []
	institution = normalize_text(card.get("institution") or card.get("organization"))
	if any(token in institution for token in MUNICIPAL_TOKENS):
		value -= 0.2
		notes.append(
			"municipal buyer: rates-clearance windows and single-shot cure culture "
			"add process burden"
		)
	quirks = [
		rule.get("rule_code")
		for rule in applicable_rules or []
		if str(rule.get("rule_code") or "").startswith("QUIRK-")
	]
	if quirks:
		value -= min(0.1 * len(quirks), 0.4)
		notes.append(
			"{0} buyer-quirk rule(s) apply: {1}".format(len(quirks), ", ".join(quirks))
		)
	# Additive refinement from the REAL per-buyer award-outcome stats,
	# only where the buyer resolved in the derived awards tables (an
	# unmatched buyer changes nothing - the fixture logic above is the
	# base and is never removed).
	if buyer_stats and buyer_stats.get("matched"):
		behavior = buyer_stats.get("publication_behavior")
		if behavior in ("zero", "low"):
			value -= 0.1
			notes.append(
				"buyer publishes few or no award outcomes to the OCDS feed "
				"({0}) - outcome visibility is poor, price benchmarks and "
				"post-bid feedback will be scarce".format(
					"0%" if behavior == "zero"
					else "{0}%".format(buyer_stats.get("publication_rate_pct"))
				)
			)
		incumbency = buyer_stats.get("incumbency_share_pct")
		if incumbency is not None and incumbency >= BUYER_INCUMBENCY_LOCKED_PCT:
			value -= 0.1
			notes.append(
				"incumbent-heavy buyer: {0}% of its published awards go to "
				"suppliers with 3+ wins at this buyer".format(incumbency)
			)
		entrant = buyer_stats.get("entrant_share_pct")
		if entrant is not None and entrant >= BUYER_ENTRANT_FRIENDLY_PCT:
			value = min(value + 0.1, 1.0)
			notes.append(
				"entrant-friendly buyer: small entrants (<= 2 lifetime wins) "
				"take {0}% of its published awards".format(entrant)
			)
	return max(value, 0.0), [{
		"code": "BUYER-BURDEN",
		"status": "info",
		"detail": "; ".join(notes) or "no known buyer-specific burden",
	}]


def _factor_economics(card, task_texts):
	tender_type = normalize_text(card.get("tender_type"))
	if "quotation" in tender_type or tender_type == "rfq":
		value = 1.0
		notes = ["RFQ - light process"]
	elif "proposal" in tender_type:
		value = 0.8
		notes = ["RFP process"]
	elif "expression of interest" in tender_type or "information" in tender_type or tender_type in ("rfi", "eoi"):
		value = 0.5
		notes = ["market-sounding process (EOI/RFI) - no immediate award"]
	elif tender_type:
		value = 0.7
		notes = ["open-tender process weight"]
	else:
		value = 0.7
		notes = ["tender type unstated"]
	duration = parse_contract_duration_months(card, task_texts)
	if duration is not None:
		if duration >= 24:
			value = min(value + 0.2, 1.0)
			notes.append("{0}-month term - recurring-revenue fit".format(duration))
		elif duration >= 12:
			value = min(value + 0.1, 1.0)
			notes.append("{0}-month term".format(duration))
		else:
			notes.append("{0}-month term (short engagement)".format(duration))
	return value, [{
		"code": "ENGAGEMENT-ECONOMICS",
		"status": "info",
		"detail": "; ".join(notes),
	}]


def _factor_pack_informed(task_texts, functionality_params, enriched):
	if not enriched or not task_texts:
		return None, [{
			"code": "PACK-UNKNOWN",
			"status": "unknown",
			"detail": "No pack/enrichment text - pack-informed factor weight "
			"redistributed until the official pack is collected",
		}]
	params = dict(DEFAULT_FUNCTIONALITY_PARAMS)
	if isinstance(functionality_params, dict):
		params.update({k: v for k, v in functionality_params.items() if v not in (None, "")})
	value = 1.0
	notes = []
	reasons = []
	parsed = parse_functionality_threshold(task_texts)
	if parsed:
		threshold = parsed["threshold_pct"]
		if threshold >= 80:
			value -= 0.35
			demand = "high"
		elif threshold > (cint(params.get("threshold_median_pct")) or 70):
			value -= 0.2
			demand = "elevated"
		else:
			demand = "standard"
		notes.append(
			"functionality threshold {0} ({1} demand vs corpus median {2}, observed "
			"{3}-{4} over {5} tenders)".format(
				threshold,
				demand,
				params.get("threshold_median_pct"),
				params.get("threshold_min_observed"),
				params.get("threshold_max_observed"),
				params.get("observations"),
			)
		)
		reasons.append({
			"code": "FUNCTIONALITY-THRESHOLD",
			"status": "info",
			"threshold_pct": parsed["threshold_pct"],
			"threshold_source": "enrichment",
			"demand": demand,
			"quoted": parsed["quoted"],
			"detail": notes[-1],
		})
	elif any("functionality" in str(line).lower() for line in task_texts):
		value -= 0.1
		notes.append("functionality evaluation applies (threshold unstated)")
	joined = "\n".join(task_texts)
	if RE_PREF_9010.search(joined) and not RE_PREF_8020.search(joined):
		notes.append("90/10 preference system quoted (above-R50m regime)")
	elif RE_PREF_8020.search(joined):
		notes.append("80/20 preference system quoted")
	fee = parse_document_fee(task_texts)
	if fee:
		value -= 0.1
		notes.append("document fee R{0} quoted".format(fee["amount_rand"]))
	reasons.insert(0, {
		"code": "PACK-INFORMED",
		"status": "info",
		"detail": "; ".join(notes) or "pack text present; no additional demands parsed",
	})
	return max(value, 0.0), reasons


# --------------------------------------------------------------------------
# Bands + the scorer
# --------------------------------------------------------------------------

def band_for(score, hard_failures):
	"""Maps a 0-100 fit score (+ hard failures) to its suitability band."""
	if hard_failures:
		return BAND_NO_BID
	if score >= BAND_STRONG:
		return "strong"
	if score >= BAND_REVIEW:
		return "review"
	if score >= BAND_MARGINAL:
		return "marginal"
	return "poor"


def _collapse_manual_checks(applicable_rules, profile, today):
	"""Splits unverifiable applicable rules into ONE grouped universal
	entry plus individual card-specific entries.

	The ~25 universal process-discipline KILLs apply to every tender and
	are never profile-checkable; listing them per card is noise. Rules
	with a Conditional scope (buyer quirks, subject/buyer gates) stay
	individual - they are card-specific and actionable.
	"""
	handled = set(PROFILE_GATE_FIELDS) | {"GATE-CIDB", "GATE-BBBEE-PREQUAL"}
	universal_codes = []
	individual = []
	warnings = []
	for rule in applicable_rules or []:
		code = rule.get("rule_code") or ""
		if code in handled:
			continue
		if code == "GATE-BBBEE":
			status, detail = check_bbbee(profile, today)
			if status == "unsatisfied":
				warnings.append(
					"B-BBEE evidence problem ({0}) - zeroes preference points but the "
					"bid survives (points-only)".format(detail)
				)
			continue
		if code == "PRICE-VAT":
			if not str(profile.get("vat_number") or "").strip():
				warnings.append(
					"No VAT number on the profile - the pack marks the VAT line for "
					"manual completion"
				)
			continue
		if rule.get("scope") == "Universal":
			universal_codes.append(code)
		else:
			individual.append({
				"code": code,
				"severity": rule.get("severity"),
				"title": rule.get("title"),
				"checklist_text": rule.get("checklist_text") or "",
			})
	grouped = []
	if universal_codes:
		grouped.append({
			"code": "PROCESS-DISCIPLINE",
			"severity": "Fatal",
			"title": "Universal process discipline ({0} rules)".format(
				len(universal_codes)
			),
			"checklist_text": (
				"The universal submission-discipline rules (completeness, signatures, "
				"sealing, deadlines, declarations) apply to this tender as to every "
				"public tender - they are enforced at pack build, not scoreable here"
			),
			"count": len(universal_codes),
			"codes": sorted(universal_codes),
		})
	return grouped + individual, warnings


def score_suitability(
	card,
	profile,
	rules_list=None,
	enrichment_entry=None,
	functionality_params=None,
	opportunity_type="tenders",
	today=None,
	market_tables=None,
):
	"""Scores one opportunity card against a business-profile snapshot.

	Pure function: ``card`` is a published catalog row, ``profile`` a plain
	dict of Tender Business Profile fields (plus ``capability_texts``),
	``rules_list`` the enabled Tender Compliance Rule records (fixture rows
	or DB rows - same shape). ``market_tables`` optionally injects the
	derived awards reference tables (tests); by default the committed
	fixture ships with the module - still deterministic data.  Returns the
	full result dict described in the module docstring. Deterministic:
	identical inputs give identical output.
	"""
	card = card or {}
	profile = profile or {}
	task_texts = enrichment_task_texts(enrichment_entry)
	context = card_context(card, enrichment_entry)
	advert_only = context.get("source_record_class") == ADVERT_ONLY
	enriched = bool(task_texts)
	confidence = CONFIDENCE_PACK_VERIFIED if enriched else CONFIDENCE_ADVERT_ONLY
	days_to_close = compute_days_to_close(card, today)
	is_tender = opportunity_type == "tenders"
	is_equity = opportunity_type == "equity"

	# Market context (derived awards reference tables): tender cards only -
	# grant/equity cards live outside the public-procurement award record.
	if is_tender:
		market_ctx = market_context_module.resolve_market_context(
			card, tables=market_tables
		)
	else:
		market_ctx = {
			"available": False,
			"reason": "market context applies to tender cards only "
			"(derived from the public eTenders award record)",
		}
	market_buyer_stats = (
		market_ctx.get("buyer_stats") if market_ctx.get("available") else None
	)

	# The compliance-rule corpus encodes SA public-sector TENDER law; grant
	# and equity cards are scored on fit dimensions only.
	applicable = []
	if is_tender:
		for rule in rules_list or []:
			if rule_applies(rule, context):
				applicable.append(rule)

	# ---- stage 1: hard gates ----
	hard_failures, gate_notes, gate_manual_checks, data_flags = evaluate_hard_gates(
		card, profile, applicable, task_texts, today, opportunity_type
	)

	profile_completeness = check_profile_completeness(profile)
	if is_tender and not profile_completeness["complete"]:
		hard_failures.append({
			"code": "PROFILE-INCOMPLETE",
			"status": "unsatisfied",
			"detail": (
				"Profile incomplete for public bidding - missing: {0}. {1}".format(
					", ".join(profile_completeness["missing"]),
					profile_completeness["note"],
				)
			),
		})

	manual_checks, coverage_warnings = ([], [])
	if is_tender:
		manual_checks, coverage_warnings = _collapse_manual_checks(
			applicable, profile, today
		)
	manual_checks = gate_manual_checks + manual_checks

	# ---- stage 2: fit factors (renormalised over KNOWN factors only) ----
	factors = {}
	if is_equity:
		factors["sector_fit"] = _factor_sector(card, profile)
		factors["geography_fit"] = _factor_equity_territory(card)
		# Standing counterparties: no urgency, readiness, buyer-burden,
		# economics or pack factors - a shortlist, not a pipeline score.
		for name in ("readiness", "process_feasibility", "buyer_burden",
				"engagement_economics", "pack_informed"):
			factors[name] = (None, [{
				"code": "NOT-APPLICABLE",
				"status": "unknown",
				"detail": "Not applicable to standing equity counterparties",
			}])
	elif not is_tender:  # grants
		factors["sector_fit"] = _factor_sector(card, profile)
		factors["geography_fit"] = (None, [{
			"code": "GEO-UNDECLARED",
			"status": "unknown",
			"detail": "Grant cards carry no province - factor weight redistributed",
		}])
		factors["readiness"] = (None, [{
			"code": "READINESS-UNKNOWN",
			"status": "unknown",
			"detail": "No demand lines exist for grant cards - weight redistributed",
		}])
		factors["process_feasibility"] = _factor_process(
			card, profile, [], task_texts, today, days_to_close
		)
		for name in ("buyer_burden", "engagement_economics", "pack_informed"):
			factors[name] = (None, [{
				"code": "NOT-APPLICABLE",
				"status": "unknown",
				"detail": "Not applicable to grant cards",
			}])
	else:
		factors["sector_fit"] = _factor_sector(card, profile)
		factors["readiness"] = _factor_readiness(task_texts, profile, enriched)
		factors["process_feasibility"] = _factor_process(
			card, profile, applicable, task_texts, today, days_to_close
		)
		factors["geography_fit"] = _factor_geography(card, profile)
		factors["buyer_burden"] = _factor_buyer_burden(
			card, applicable, market_buyer_stats
		)
		factors["engagement_economics"] = _factor_economics(card, task_texts)
		factors["pack_informed"] = _factor_pack_informed(
			task_texts, functionality_params, enriched
		)

	known_weight = sum(
		FIT_WEIGHTS[name] for name, (value, _r) in factors.items() if value is not None
	)
	if known_weight and not hard_failures:
		weighted = sum(
			FIT_WEIGHTS[name] * value
			for name, (value, _r) in factors.items()
			if value is not None
		)
		score = int(round(100.0 * weighted / known_weight))
	else:
		score = None

	dimensions = {}
	for name, (value, reasons) in factors.items():
		dimensions[name] = {
			"points": round(value * FIT_WEIGHTS[name], 1) if value is not None else None,
			"max": FIT_WEIGHTS[name],
			"known": value is not None,
			"reasons": reasons,
		}

	# ---- payload ----
	warnings = list(coverage_warnings)
	triage = None
	if advert_only and is_tender:
		warnings.append(
			"Advert-only source record: requirements beyond the universal spine are "
			"unknown until the official tender pack is collected (GATE-PACK-COLLECT)"
		)
		triage = (
			"advert_only score: its purpose is pack-fetch prioritisation - fetch the "
			"pack for promising cards, then re-score at pack_verified confidence"
		)
	cidb_requirement = parse_cidb_requirement(task_texts)
	if cidb_requirement:
		warnings.append(
			"CIDB requirement quoted from enrichment: " + cidb_requirement["quoted"]
		)

	if hard_failures or score is not None:
		band = band_for(score, hard_failures)
	else:
		# No gate fired but nothing is known (e.g. an equity card scored
		# against a profile with no declared sectors): honest "unscored",
		# never a fake number.
		band = "unscored"

	return {
		"score": score,
		"band": band,
		"eligible": not hard_failures,
		"opportunity_type": opportunity_type,
		"semantics": "standing_fit_shortlist" if is_equity else "worth_bidding_triage",
		"source_record_class": context.get("source_record_class"),
		"confidence": confidence,
		"days_to_close": days_to_close,
		"known_weight": known_weight,
		"dimensions": dimensions,
		"hard_failures": hard_failures,
		"gate_notes": gate_notes,
		"profile_completeness": profile_completeness,
		"manual_checks": manual_checks,
		"data_flags": data_flags,
		"triage": triage,
		"warnings": warnings,
		"market_context": market_ctx,
	}
