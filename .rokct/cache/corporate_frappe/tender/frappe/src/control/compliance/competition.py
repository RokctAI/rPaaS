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

"""Low-competition tender finder: deterministic FIELD-NARROWNESS scoring.

Rates how narrow the set of firms is that can even qualify to bid on one
published catalog card, from PUBLIC requirements only (the card itself
plus, where the caller is entitled, its published enrichment demand
lines). The score describes the FIELD - never the caller, and never a
win probability: a narrow field says "few firms can clear the bar", it
says nothing about who wins among those that do.

Everything here is the same doctrine as ``suitability.py``: pure data
comparison, whitelisted regex extraction, quoted-or-nothing evidence,
no AI, no network. The CIDB-grading, B-BBEE-prequalification and
briefing/date extraction is IMPORTED from ``suitability.py`` (never
re-implemented); only the two extractors that module does not have -
EME/QSE set-asides and local-content/designated-sector statements - are
defined here, under the same hard-whitelist rules.

**Narrowing signals and weights** (deterministic weighted sum, capped at
100 - each signal shrinks the set of firms that can lawfully bid):

- ``NARROW-CIDB`` - a quoted CIDB grading requirement.
  ``W_CIDB_BASE`` (10) + ``W_CIDB_PER_GRADE`` (4) x (grade - 1), so
  grade 1 = 10 ... grade 7 = 34 ... grade 9 = 42. CIDB registration is
  statutory for public construction works and the register is a
  pyramid: each grade step excludes most of the firms below it - grade
  7+ excludes the overwhelming majority of registered contractors.
- ``NARROW-SET-ASIDE`` - an EME/QSE set-aside or EME/QSE
  pre-qualification (25). Excludes every Generic (>R50m) firm outright,
  the strongest single field-shrinker under PPR 2022 prequalification.
- ``NARROW-BBBEE-PREQUAL`` - a quoted B-BBEE pre-qualification (15).
  Pass/fail on B-BBEE status, so non-compliant and expired-certificate
  firms are out before evaluation (level mentions in points tables
  never count - suitability's over-enumeration guard, reused verbatim).
- ``NARROW-BRIEFING`` - compulsory briefing (10), plus
  ``W_BRIEFING_NON_METRO`` (8) more when the card sits in a province
  with no metropolitan municipality (Limpopo, Mpumalanga, North West,
  Northern Cape): physical attendance far from the metros filters out
  every firm unwilling to travel.
- ``NARROW-WINDOW`` - short submission window: <= 7 days to close (15)
  or 8-14 days (8). Firms without standing documents simply cannot
  assemble a compliant bid in time.
- ``NARROW-LOCAL-CONTENT`` - a quoted local-content / designated-sector
  requirement (10): only firms able to certify SATS 1286 local
  production thresholds can comply.

**Tiers** (documented boundaries, deterministic):
``wide`` < 20 <= ``moderate`` < 40 <= ``narrow`` < 60 <=
``very_narrow``. A card with no narrowing signal scores 0 = ``wide``.

**Crossing with the caller's profile**: a card is an OPPORTUNITY for
this caller when the field is narrow (tier ``narrow``/``very_narrow``,
or the caller's chosen floor) AND the caller clears every narrowing
requirement that is checkable against the profile - the CIDB check and
the B-BBEE status check are ``suitability.py``'s own gate functions
(``check_cidb_gate``, ``check_bbbee``) reused verbatim; the set-aside
check compares the profile's declared enterprise type; the briefing
check applies the profile's travel radius and operating provinces. A
requirement that cannot be checked from the profile never blocks - it
becomes a caveat (positive-evidence doctrine: unknowns lower certainty,
they never silently pass or fail).

Aggregate public data only: the inputs are the published catalog card,
the published enrichment lines, and the caller's OWN profile - never
any other subscriber's data.
"""

import re

# Same-package imports (F-09 pattern, identical to suitability.py):
# relative on a composed bench, importlib fallback keeps this module
# importable standalone by file path.
try:
	from .suitability import (
		check_bbbee,
		check_cidb_gate,
		compute_days_to_close,
		enrichment_task_texts,
		is_placeholder_date,
		parse_bbbee_prequal_evidence,
		parse_card_datetime,
		parse_cidb_requirement,
		parse_profile_cidb_grade,
		parse_real_past_date,
		_split_tokens,
	)
	from .rules import normalize_text
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

	_suitability = _load_sibling("tender_competition_suitability", "suitability.py")
	_rules = _load_sibling("tender_competition_rules", "rules.py")
	check_bbbee = _suitability.check_bbbee
	check_cidb_gate = _suitability.check_cidb_gate
	compute_days_to_close = _suitability.compute_days_to_close
	enrichment_task_texts = _suitability.enrichment_task_texts
	is_placeholder_date = _suitability.is_placeholder_date
	parse_bbbee_prequal_evidence = _suitability.parse_bbbee_prequal_evidence
	parse_card_datetime = _suitability.parse_card_datetime
	parse_cidb_requirement = _suitability.parse_cidb_requirement
	parse_profile_cidb_grade = _suitability.parse_profile_cidb_grade
	parse_real_past_date = _suitability.parse_real_past_date
	_split_tokens = _suitability._split_tokens
	normalize_text = _rules.normalize_text


# --------------------------------------------------------------------------
# Weights, tiers, whitelists
# --------------------------------------------------------------------------

# Narrowing-signal weights - the full rationale lives in the module
# docstring above; change them there and here together.
W_CIDB_BASE = 10
W_CIDB_PER_GRADE = 4
W_SET_ASIDE = 25
W_BBBEE_PREQUAL = 15
W_BRIEFING = 10
W_BRIEFING_NON_METRO = 8
W_WINDOW_VERY_SHORT = 15  # <= 7 days to close
W_WINDOW_SHORT = 8        # 8-14 days to close
W_LOCAL_CONTENT = 10

SHORT_WINDOW_VERY_DAYS = 7
SHORT_WINDOW_DAYS = 14

SCORE_CAP = 100

TIER_WIDE = "wide"
TIER_MODERATE = "moderate"
TIER_NARROW = "narrow"
TIER_VERY_NARROW = "very_narrow"
# Ordered widest -> narrowest; index = rank for min-tier filtering.
TIER_ORDER = (TIER_WIDE, TIER_MODERATE, TIER_NARROW, TIER_VERY_NARROW)
TIER_MODERATE_FLOOR = 20
TIER_NARROW_FLOOR = 40
TIER_VERY_NARROW_FLOOR = 60

# Provinces with NO metropolitan municipality (SA has eight metros:
# three in Gauteng, and one each in the Western Cape, KwaZulu-Natal and
# the Free State, plus two in the Eastern Cape). A compulsory briefing
# in one of these provinces means travel far from where most firms sit.
NON_METRO_PROVINCES = ("limpopo", "mpumalanga", "north west", "northern cape")

# EME/QSE set-aside evidence: a quoted line must carry BOTH an
# enterprise-class token AND a set-aside/pre-qualification token.
# A bare EME/QSE mention (the sworn-affidavit option every pack
# explains) never counts - the same over-enumeration guard doctrine as
# suitability's B-BBEE prequalification extractor.
RE_EME_TOKEN = re.compile(r"\bemes?\b", re.IGNORECASE)
RE_QSE_TOKEN = re.compile(r"\bqses?\b", re.IGNORECASE)
RE_SET_ASIDE_TOKEN = re.compile(
	r"set[- ]?aside|reserved for|only open to|open only to|exclusively for|"
	r"limited to|restricted to|targeted at|pre[- ]?qualif",
	re.IGNORECASE,
)

# Local-content / designated-sector evidence (quoted-or-nothing).
LOCAL_CONTENT_LINE_TOKENS = (
	"local content", "local production", "sats 1286", "designated sector",
)

FIELD_SEMANTICS = (
	"field narrowness describes how many firms can QUALIFY to bid, computed "
	"deterministically from public requirements only - it describes the "
	"field, never the caller, and it is NEVER a win probability"
)


# --------------------------------------------------------------------------
# Extraction (only what suitability.py does not already provide)
# --------------------------------------------------------------------------

def card_texts(card):
	"""The public free-text surfaces of a catalog card worth scanning."""
	return [
		str(part)
		for part in (
			(card or {}).get("title"),
			(card or {}).get("category"),
			(card or {}).get("tender_type"),
		)
		if part not in (None, "")
	]


def parse_set_aside(texts):
	"""Extracts an EME/QSE set-aside statement from public text lines.

	Returns ``{"classes": [..], "quoted": line}`` for the first line
	carrying BOTH an enterprise-class token (EME / QSE) AND a
	set-aside or pre-qualification token, else None. ``classes`` lists
	the enterprise classes the field is reserved to, in EME, QSE order.
	Affidavit-explainer lines ("sworn EME/QSE affidavit ...") are noise,
	not set-asides - they name the class only to describe an evidence
	format, so they never count.
	"""
	for raw in texts or []:
		line = str(raw or "")
		if "affidavit" in line.lower():
			continue
		if not RE_SET_ASIDE_TOKEN.search(line):
			continue
		classes = []
		if RE_EME_TOKEN.search(line):
			classes.append("EME")
		if RE_QSE_TOKEN.search(line):
			classes.append("QSE")
		if classes:
			return {"classes": classes, "quoted": line.strip()}
	return None


def parse_local_content(texts):
	"""Extracts a local-content / designated-sector statement, else None.

	Returns ``{"quoted": line}`` for the first line carrying one of the
	whitelisted local-content tokens (quoted-or-nothing).
	"""
	for raw in texts or []:
		line = str(raw or "")
		lowered = line.lower()
		if any(token in lowered for token in LOCAL_CONTENT_LINE_TOKENS):
			return {"quoted": line.strip()}
	return None


def profile_enterprise_class(profile):
	"""The profile's declared enterprise class: "EME" | "QSE" | "GENERIC"
	| None (undeclared).

	The Tender Business Profile's ``enterprise_type`` select stores
	descriptive options ("EME (turnover under R10m - sworn affidavit)");
	only the leading class token is trusted.
	"""
	raw = str((profile or {}).get("enterprise_type") or "").strip().upper()
	if raw.startswith("EME"):
		return "EME"
	if raw.startswith("QSE"):
		return "QSE"
	if raw.startswith("GENERIC"):
		return "GENERIC"
	return None


# --------------------------------------------------------------------------
# Field-narrowness scoring
# --------------------------------------------------------------------------

def tier_for(score):
	"""Maps a 0-100 narrowness score to its tier (documented boundaries)."""
	if score >= TIER_VERY_NARROW_FLOOR:
		return TIER_VERY_NARROW
	if score >= TIER_NARROW_FLOOR:
		return TIER_NARROW
	if score >= TIER_MODERATE_FLOOR:
		return TIER_MODERATE
	return TIER_WIDE


def score_field_narrowness(card, task_texts=None, today=None):
	"""Scores how narrow the field of qualifying firms is for one card.

	Pure function over the published card and (optionally) its published
	enrichment demand lines. Returns ``{"score", "tier", "signals",
	"days_to_close", "semantics"}``; each signal carries its ``code``,
	``points``, a human-readable ``detail`` and the machine fields the
	profile-crossing needs. Deterministic: identical inputs give
	identical output. Never a win probability.
	"""
	card = card or {}
	texts = card_texts(card) + [str(t) for t in (task_texts or []) if t]
	signals = []
	score = 0

	# --- required CIDB grading (suitability's extractor, reused) ---
	cidb = parse_cidb_requirement(texts)
	if cidb:
		points = W_CIDB_BASE + W_CIDB_PER_GRADE * (cidb["grade"] - 1)
		score += points
		signals.append({
			"code": "NARROW-CIDB",
			"points": points,
			"grade": cidb["grade"],
			"class_code": cidb["class_code"],
			"quoted": cidb["quoted"],
			"detail": (
				"Requires CIDB grading {0}{1}: only contractors registered at "
				"grade {0} or above in class {1} can bid{2}".format(
					cidb["grade"],
					cidb["class_code"],
					" - grade 7+ excludes the overwhelming majority of "
					"registered firms" if cidb["grade"] >= 7 else "",
				)
			),
		})

	# --- EME/QSE set-aside / prequalification ---
	set_aside = parse_set_aside(texts)
	if set_aside:
		score += W_SET_ASIDE
		signals.append({
			"code": "NARROW-SET-ASIDE",
			"points": W_SET_ASIDE,
			"classes": set_aside["classes"],
			"quoted": set_aside["quoted"],
			"detail": (
				"Set aside for {0} bidders: every larger firm is excluded "
				"outright".format(" / ".join(set_aside["classes"]))
			),
		})

	# --- B-BBEE pre-qualification (suitability's extractor, reused;
	#     level mentions in points tables never count) ---
	prequal = parse_bbbee_prequal_evidence(texts)
	if prequal:
		score += W_BBBEE_PREQUAL
		signals.append({
			"code": "NARROW-BBBEE-PREQUAL",
			"points": W_BBBEE_PREQUAL,
			"quoted": prequal["quoted"],
			"detail": (
				"B-BBEE pre-qualification applies: pass/fail on B-BBEE status "
				"before evaluation - non-compliant and expired-certificate "
				"firms are out of the field"
			),
		})

	# --- compulsory briefing (+ non-metro travel narrowing) ---
	if str(card.get("is_it_compulsory") or "").strip().lower() == "yes":
		points = W_BRIEFING
		province = normalize_text(card.get("province"))
		non_metro = any(token == province for token in NON_METRO_PROVINCES)
		detail = (
			"Compulsory briefing: only firms that physically attend stay in "
			"the field"
		)
		if non_metro:
			points += W_BRIEFING_NON_METRO
			detail += (
				" - and it sits in {0}, a province with no metro, so travel "
				"filters out most out-of-province firms".format(
					card.get("province")
				)
			)
		score += points
		signals.append({
			"code": "NARROW-BRIEFING",
			"points": points,
			"province": card.get("province"),
			"non_metro": non_metro,
			"briefing_date_and_time": card.get("briefing_date_and_time"),
			"detail": detail,
		})

	# --- short submission window ---
	days_to_close = compute_days_to_close(card, today)
	if days_to_close is not None and 0 <= days_to_close <= SHORT_WINDOW_DAYS:
		very_short = days_to_close <= SHORT_WINDOW_VERY_DAYS
		points = W_WINDOW_VERY_SHORT if very_short else W_WINDOW_SHORT
		score += points
		signals.append({
			"code": "NARROW-WINDOW",
			"points": points,
			"days_to_close": days_to_close,
			"detail": (
				"Only {0} day(s) to close: firms without standing documents "
				"cannot assemble a compliant bid in time".format(days_to_close)
			),
		})

	# --- local content / designated sector ---
	local_content = parse_local_content(texts)
	if local_content:
		score += W_LOCAL_CONTENT
		signals.append({
			"code": "NARROW-LOCAL-CONTENT",
			"points": W_LOCAL_CONTENT,
			"quoted": local_content["quoted"],
			"detail": (
				"Local-content / designated-sector requirement: only firms "
				"able to certify the SATS 1286 local-production thresholds "
				"can comply"
			),
		})

	score = min(score, SCORE_CAP)
	return {
		"score": score,
		"tier": tier_for(score),
		"signals": signals,
		"days_to_close": days_to_close,
		"semantics": FIELD_SEMANTICS,
	}


# --------------------------------------------------------------------------
# Crossing the narrow field with the caller's profile
# --------------------------------------------------------------------------

def _check_set_aside(profile, signal):
	held = profile_enterprise_class(profile)
	classes = signal.get("classes") or []
	if held is None:
		return (None,
			"No enterprise type declared on the profile - declare EME/QSE "
			"status to confirm this set-aside is open to you")
	if held in classes:
		return (True,
			"Profile is {0} - inside the {1} set-aside".format(
				held, " / ".join(classes)))
	return (False,
		"Set aside for {0}; profile is {1}".format(" / ".join(classes), held))


def _check_briefing(profile, signal, today):
	raw = signal.get("briefing_date_and_time")
	if is_placeholder_date(raw):
		return (None,
			"Briefing date on the card is a registry placeholder - confirm "
			"the real date before committing")
	if parse_real_past_date(raw, today):
		return (False,
			"Compulsory briefing was already held on {0} - the field is "
			"closed to newcomers".format(str(raw)[:16]))
	province = normalize_text(signal.get("province"))
	radius = normalize_text(profile.get("briefing_travel_radius"))
	declared = [
		normalize_text(token)
		for token in _split_tokens(profile.get("operating_provinces"))
	]
	in_footprint = bool(province) and any(
		token and (token in province or province in token) for token in declared
	)
	if not province or province in ("national", "all", "south africa", "n/a"):
		return (True, "Briefing province unspecified/national - attendable")
	if in_footprint:
		return (True,
			"Briefing is inside the declared operating footprint ({0})".format(
				signal.get("province")))
	if radius.startswith("national"):
		return (True,
			"Profile travel radius is national - the {0} briefing is "
			"reachable".format(signal.get("province")))
	if radius.startswith("local"):
		return (False,
			"Briefing is in {0}, outside the declared footprint, and the "
			"profile's travel radius is local-only".format(signal.get("province")))
	if not declared and not radius:
		return (None,
			"No operating provinces or travel radius declared - confirm the "
			"{0} briefing is reachable".format(signal.get("province")))
	return (None,
		"Briefing is in {0}, outside the declared footprint - confirm it is "
		"within your travel radius".format(signal.get("province")))


def cross_with_profile(profile, narrowness, today=None):
	"""Checks the caller's profile against each narrowing signal.

	Reuses ``suitability.py``'s gate/profile logic for the checkable
	requirements (``check_cidb_gate`` for CIDB, ``check_bbbee`` for the
	B-BBEE prequalification). Returns ``{"checks", "caveats",
	"meets_narrowing_requirements"}``: each check carries ``code``,
	``met`` (True / False / None-unknown) and a human-readable
	``detail``. ``meets_narrowing_requirements`` is True when NO check
	affirmatively fails - unknowns become caveats, they never block
	(and never silently pass: they stay visible).
	"""
	profile = profile or {}
	checks = []
	caveats = []
	for signal in (narrowness or {}).get("signals") or []:
		code = signal.get("code")
		if code == "NARROW-CIDB":
			status, detail = check_cidb_gate(profile, {
				"grade": signal["grade"],
				"class_code": signal["class_code"],
				"quoted": signal.get("quoted") or "",
			})
			met = {"satisfied": True, "unsatisfied": False}.get(status)
			checks.append({"code": code, "met": met, "detail": detail})
			if met is None:
				caveats.append(detail)
		elif code == "NARROW-SET-ASIDE":
			met, detail = _check_set_aside(profile, signal)
			checks.append({"code": code, "met": met, "detail": detail})
			if met is None:
				caveats.append(detail)
		elif code == "NARROW-BBBEE-PREQUAL":
			status, detail = check_bbbee(profile, today)
			met = status == "satisfied"
			checks.append({"code": code, "met": met, "detail": detail})
		elif code == "NARROW-BRIEFING":
			met, detail = _check_briefing(profile, signal, today)
			checks.append({"code": code, "met": met, "detail": detail})
			if met is None:
				caveats.append(detail)
		elif code == "NARROW-WINDOW":
			detail = (
				"Short window is a capacity question, not a registration - "
				"{0} day(s) demand standing documents ready to go".format(
					signal.get("days_to_close")
				)
			)
			checks.append({"code": code, "met": True, "detail": detail})
			caveats.append(detail)
		elif code == "NARROW-LOCAL-CONTENT":
			detail = (
				"Local-content ability has no profile counterpart - verify "
				"you can certify the SATS 1286 thresholds before bidding"
			)
			checks.append({"code": code, "met": None, "detail": detail})
			caveats.append(detail)
	meets = all(check["met"] is not False for check in checks)
	return {
		"checks": checks,
		"caveats": caveats,
		"meets_narrowing_requirements": meets,
	}


def assess_low_competition(card, profile, task_texts=None, today=None):
	"""Full per-card assessment: narrowness + profile crossing + verdict.

	A card is an ``opportunity`` for this caller when the field is
	narrow (tier ``narrow`` or ``very_narrow``), the closing date has
	not passed, and the caller clears every checkable narrowing
	requirement. Pure and deterministic; never a win probability.
	"""
	card = card or {}
	narrowness = score_field_narrowness(card, task_texts=task_texts, today=today)
	requirements = cross_with_profile(profile, narrowness, today=today)
	closed = bool(parse_real_past_date(
		card.get("closing_date") or card.get("deadline"), today
	))
	narrow_enough = TIER_ORDER.index(narrowness["tier"]) >= TIER_ORDER.index(TIER_NARROW)
	return {
		"slug": card.get("slug") or card.get("tender_number"),
		"title": card.get("title"),
		"institution": card.get("institution") or card.get("organization"),
		"province": card.get("province"),
		"closing_date": card.get("closing_date") or card.get("deadline"),
		"days_to_close": narrowness["days_to_close"],
		"closed": closed,
		"narrowness": narrowness,
		"requirements": requirements,
		"opportunity": (
			narrow_enough
			and not closed
			and requirements["meets_narrowing_requirements"]
		),
		"semantics": FIELD_SEMANTICS,
	}
