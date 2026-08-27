"""Standalone verification for the automated suitability scorer
(opportunities FEEDBACK.md section 1.2) - the MERGED two-stage model
(see tender/Suitability-Scoring-Model.md): stage-1 hard gates (closing
passed, compulsory-briefing-already-held with the placeholder-date rule,
category-triggered statutory CIDB with JV-conditional / provisional
outcomes, B-BBEE prequalification union trigger with the over-enumeration
guard, present-once profile completeness) with NO numeric score on
no_bid; stage-2 fit 0-100 renormalised over KNOWN factors with the
confidence flag, days_to_close and triage note; the fixed functionality
extractor (quoted no-percent forms); collapsed universal manual checks;
grants jurisdiction gate; equity standing-fit semantics; the
get_tender_suitability endpoint (friendly errors, enrichment never used
for non-entitled callers) and the additive manifest + doctype
registrations. Exit code 0 = all checks pass."""

import importlib.util
import json
import os
import sys
import types

# O-05: in-tree suite runs must leave no __pycache__ litter under src/
sys.dont_write_bytecode = True

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SRC = os.path.join(REPO, "tender/frappe/src/control")
FIXTURES = os.path.join(REPO, "tender/frappe/fixtures")

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


# --------------------------------------------------------------------------
# frappe stub
# --------------------------------------------------------------------------
class Thrown(Exception):
    pass


frappe_stub = types.ModuleType("frappe")
utils_stub = types.ModuleType("frappe.utils")
utils_stub.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
utils_stub.flt = lambda v, precision=None: float(v) if v not in (None, "") else 0.0
utils_stub.nowdate = lambda: "2026-08-23"
utils_stub.now = lambda: "2026-08-23 12:00:00"
utils_stub.getdate = lambda v=None: v
frappe_stub.utils = utils_stub


def _throw(msg, exc=None, title=None):
    raise Thrown(f"{title or ''}: {msg}")


frappe_stub.throw = _throw
frappe_stub.whitelist = lambda *a, **k: (lambda f: f)
frappe_stub.PermissionError = Thrown
frappe_stub.DoesNotExistError = Thrown
frappe_stub.conf = {"app_role": "control"}
frappe_stub.session = types.SimpleNamespace(user="desk@example.com")
frappe_stub.local = types.SimpleNamespace(request=None)
frappe_stub.get_request_header = lambda *a, **k: None
frappe_stub.log_error = lambda *a, **k: None
frappe_stub.get_all = lambda *a, **k: []
frappe_stub.get_doc = lambda *a, **k: None
frappe_stub.db = types.SimpleNamespace(
    get_value=lambda *a, **k: None,
    exists=lambda *a, **k: False,
    get_single_value=lambda *a, **k: 0,
)
sys.modules["frappe"] = frappe_stub
sys.modules["frappe.utils"] = utils_stub


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_endpoint(name, relpath, stub_root="_app_stub"):
    """Execs an {app_name}-placeholder endpoint with the placeholder filled."""
    path = os.path.join(SRC, relpath)
    with open(path, encoding="utf-8") as f:
        source = f.read().replace("{app_name}", stub_root)
    module = types.ModuleType(name)
    module.__file__ = path
    exec(compile(source, path, "exec"), module.__dict__)
    return module


suitability = load_module("s_suitability", os.path.join(SRC, "compliance/suitability.py"))

with open(os.path.join(FIXTURES, "tender_compliance_rules.json"), encoding="utf-8") as f:
    ALL_RULES = json.load(f)
RULES = {r["rule_code"]: r for r in ALL_RULES}
FUNCTIONALITY_PARAMS = json.loads(RULES["SCORE-FUNCTIONALITY"]["params"])
TODAY = "2026-08-23"


def score(card, profile, enrichment=None, opportunity_type="tenders"):
    return suitability.score_suitability(
        card, profile, rules_list=ALL_RULES, enrichment_entry=enrichment,
        functionality_params=FUNCTIONALITY_PARAMS,
        opportunity_type=opportunity_type, today=TODAY)


# --------------------------------------------------------------------------
# (a) deterministic extraction: CIDB, functionality (incl. no-% forms)
# --------------------------------------------------------------------------
print("== (a) CIDB extraction: whitelisted grading tokens, quoted-or-nothing ==")
req = suitability.parse_cidb_requirement(
    ["Confirm CIDB contractor grading '1CE OR HIGHER' is active and in good standing | 1"]
)
check("real enrichment line -> grade 1, class CE",
      req and req["grade"] == 1 and req["class_code"] == "CE")
check("extraction quotes its source line",
      req and "1CE OR HIGHER" in req["quoted"])
req7 = suitability.parse_cidb_requirement(["CIDB Grade 7 GB required, active at close"])
check("'Grade 7 GB' spaced form -> grade 7, class GB",
      req7 and req7["grade"] == 7 and req7["class_code"] == "GB")
check("'Grade 12' (school certificate) NEVER reads as a grading",
      suitability.parse_cidb_requirement(["CIDB office wants a Grade 12 certificate"]) is None)
check("'12CE' never matches (grade is a single digit 1-9)",
      suitability.parse_cidb_requirement(["CIDB grading 12CE mentioned"]) is None)
check("grading token on a line that never mentions CIDB is ignored",
      suitability.parse_cidb_requirement(["Provide 3CE reference sites"]) is None)
check("empty / None input -> None",
      suitability.parse_cidb_requirement([]) is None
      and suitability.parse_cidb_requirement(None) is None)
check("profile grade '2CE' parses", suitability.parse_profile_cidb_grade("2CE")
      == {"grade": 2, "class_code": "CE"})
check("empty / junk profile grade -> None",
      suitability.parse_profile_cidb_grade("") is None
      and suitability.parse_profile_cidb_grade("N/A") is None)

print("== (a2) functionality threshold extraction: % form + live no-% forms ==")
fn = suitability.parse_functionality_threshold(
    ["Achieve the minimum functionality threshold of 70% to proceed to price | 2"]
)
check("'functionality threshold of 70%' -> 70 (percent form kept)",
      fn and fn["threshold_pct"] == 70 and fn["form"] == "percent"
      and "70%" in fn["quoted"])
fn80 = suitability.parse_functionality_threshold(
    ["Achieve the minimum functionality threshold of 80 to proceed | 2"])
check("'minimum functionality threshold of 80' (no %) -> 80",
      fn80 and fn80["threshold_pct"] == 80 and fn80["form"] == "no_percent")
fn60 = suitability.parse_functionality_threshold(["ACCEPTABLE MINIMUM SCORE 60"])
check("'ACCEPTABLE MINIMUM SCORE 60' -> 60", fn60 and fn60["threshold_pct"] == 60)
fnr = suitability.parse_functionality_threshold(
    ["Minimum Required Score for functionality is: 60"])
check("'Minimum Required Score for functionality is: 60' -> 60",
      fnr and fnr["threshold_pct"] == 60)
check("extraction quotes its source line (no-% form)",
      fn80 and "threshold of 80" in fn80["quoted"])
check("a bare number on a non-threshold line is never trusted",
      suitability.parse_functionality_threshold(["functionality evaluated out of 200"]) is None
      and suitability.parse_functionality_threshold(["Submit 3 copies within 90 days"]) is None)
check("no-% numbers below the observed floor (30) are never trusted",
      suitability.parse_functionality_threshold(["acceptable minimum score 20"]) is None)
check("no functionality mention -> None",
      suitability.parse_functionality_threshold(["Submit the tax PIN"]) is None)

print("== (a3) date parsing: placeholders are UNKNOWN, not evidence ==")
check("placeholder 0001-01-01 detected",
      suitability.is_placeholder_date("0001-01-01 00:00")
      and not suitability.is_placeholder_date("2026-08-10 10:00"))
check("real past date parses; placeholder/future/junk do not count as past",
      suitability.parse_real_past_date("2026-08-10 10:00", TODAY)
      and suitability.parse_real_past_date("0001-01-01 00:00", TODAY) is None
      and suitability.parse_real_past_date("2026-09-10", TODAY) is None
      and suitability.parse_real_past_date("N/A", TODAY) is None)

# --------------------------------------------------------------------------
# (b) strong-fit case + payload contract
# --------------------------------------------------------------------------
print("== (b) strong-fit: full profile vs a matching ICT tender ==")
FULL_PROFILE = {
    "csd_maaa_number": "MAAA0123456",
    "tcs_pin": "PIN123456789",
    "company_registration_no": "2019/123456/07",
    "vat_number": "4123456789",
    "enterprise_type": "EME (turnover under R10m - sworn affidavit)",
    "bbbee_level": "1",
    "bbbee_certificate_expiry": "2027-01-01",
    "cidb_grade": "",
    "operating_sectors": "ICT, helpdesk, software",
    "operating_provinces": "Limpopo, Gauteng",
    "capability_texts": ["Reference site: municipal helpdesk rollout"],
    "coida_good_standing": "1",
    "municipal_rates_current": "1",
    "track_record_evidence": "1",
}
MUSINA_CARD = {
    "slug": "ocds-test-1",
    "title": "Interactive Cloud-Based Customer Service Ticketing and Helpdesk Management System",
    "institution": "Musina Local Municipality",
    "category": "Services: ICT and related",
    "tender_type": "Request for Quotation",
    "province": "Limpopo",
    "status": "ACTIVE",
    "closing_date": "2026-09-15",
    "is_there_a_briefing_session": "No",
    "is_it_compulsory": "No",
    "briefing_date_and_time": "N/A",
}
ENRICHED = {"enrichment": "ADVANCED", "tasks": [
    "Verify Tax Compliance status on SARS and provide valid PIN | 1",
    "Verify the company and every director are NOT listed on the Restricted Suppliers register | 1",
]}
strong = score(MUSINA_CARD, FULL_PROFILE, ENRICHED)
check("strong case is eligible with no hard failures",
      strong["eligible"] and strong["hard_failures"] == [])
check("strong case band is 'strong' with score >= 80",
      strong["band"] == "strong" and strong["score"] >= suitability.BAND_STRONG)
check("payload carries confidence pack_verified on an enriched card",
      strong["confidence"] == "pack_verified")
check("payload carries days_to_close computed from the card",
      strong["days_to_close"] == 23)
check("semantics is worth_bidding_triage for tenders",
      strong["semantics"] == "worth_bidding_triage")
check("all seven fit factors present (weights renormalise, so the raw sum "
      "of 110 never reaches the payload)",
      set(strong["dimensions"]) == set(suitability.FIT_WEIGHTS)
      and sum(suitability.FIT_WEIGHTS.values()) == 110)
check("sector factor matched declared sectors at full value (2+ tokens)",
      strong["dimensions"]["sector_fit"]["points"]
      == suitability.FIT_WEIGHTS["sector_fit"]
      and strong["dimensions"]["sector_fit"]["reasons"][0]["code"] == "SECTOR-MATCH")
check("geography matched Limpopo at full weight",
      strong["dimensions"]["geography_fit"]["points"]
      == suitability.FIT_WEIGHTS["geography_fit"])
check("readiness factor KNOWN: demanded tax returnable evidenced by the profile",
      strong["dimensions"]["readiness"]["known"]
      and strong["dimensions"]["readiness"]["points"]
      == suitability.FIT_WEIGHTS["readiness"])
check("profile_completeness reported once and complete",
      strong["profile_completeness"]["complete"]
      and strong["profile_completeness"]["missing"] == [])
check("municipal buyer burden deducted with a named reason",
      strong["dimensions"]["buyer_burden"]["points"]
      < suitability.FIT_WEIGHTS["buyer_burden"]
      and "municipal" in strong["dimensions"]["buyer_burden"]["reasons"][0]["detail"])
check("RFQ scores light process in engagement economics",
      "RFQ" in strong["dimensions"]["engagement_economics"]["reasons"][0]["detail"])
check("buyer quirks the profile cannot answer surface as individual manual checks",
      any(m["code"] == "QUIRK-MUSINA-PAGEINIT" for m in strong["manual_checks"]))
strong_again = score(MUSINA_CARD, FULL_PROFILE, ENRICHED)
check("scoring is deterministic (identical inputs -> identical result)",
      strong == strong_again)

print("== (b2) collapsed universal manual checks ==")
groups = [m for m in strong["manual_checks"] if m["code"] == "PROCESS-DISCIPLINE"]
check("the ~25 universal process-KILL rules collapse into ONE grouped entry",
      len(groups) == 1 and groups[0]["count"] >= 20
      and "KILL-01" in groups[0]["codes"])
check("no universal KILL rule appears as its own manual-check entry",
      not any(str(m["code"]).startswith("KILL-") for m in strong["manual_checks"]))
check("card-specific conditional rules stay individual (Musina quirks)",
      sum(1 for m in strong["manual_checks"]
          if str(m["code"]).startswith("QUIRK-MUSINA")) >= 3)

print("== (b3) advert-only: renormalisation + confidence + triage ==")
advert = score(MUSINA_CARD, FULL_PROFILE, None)
check("advert-only card carries confidence advert_only + GATE-PACK-COLLECT warning",
      advert["confidence"] == "advert_only"
      and advert["source_record_class"] == "Advert-Only"
      and any("Advert-only" in w for w in advert["warnings"]))
check("advert-only triage note: score prioritises pack fetching, re-score later",
      advert["triage"] and "pack-fetch" in advert["triage"]
      and "re-score" in advert["triage"])
check("unknown factors (readiness, pack_informed) carry no points and are marked",
      advert["dimensions"]["readiness"]["points"] is None
      and not advert["dimensions"]["readiness"]["known"]
      and advert["dimensions"]["pack_informed"]["points"] is None)
check("known weight excludes exactly the unknown factors",
      advert["known_weight"] == sum(suitability.FIT_WEIGHTS.values())
      - suitability.FIT_WEIGHTS["readiness"] - suitability.FIT_WEIGHTS["pack_informed"])
weighted = sum(
    d["points"] for d in advert["dimensions"].values() if d["points"] is not None)
check("score is renormalised over KNOWN weight (not silently awarded)",
      advert["score"] == int(round(100.0 * weighted / advert["known_weight"])))
check("GATE-PACK-COLLECT lands in the manual checks on advert-only",
      any(m["code"] == "GATE-PACK-COLLECT" for m in advert["manual_checks"]))

undeclared = dict(FULL_PROFILE, operating_sectors="", capability_texts=[],
                  operating_provinces="")
ud = score(MUSINA_CARD, undeclared, None)
check("undeclared sector/geography go UNKNOWN and redistribute (never neutral-score)",
      not ud["dimensions"]["sector_fit"]["known"]
      and not ud["dimensions"]["geography_fit"]["known"]
      and ud["known_weight"] == suitability.FIT_WEIGHTS["process_feasibility"]
      + suitability.FIT_WEIGHTS["buyer_burden"]
      + suitability.FIT_WEIGHTS["engagement_economics"])

# --------------------------------------------------------------------------
# (c) stage-1 gates: briefing
# --------------------------------------------------------------------------
print("== (c) briefing gate: real past date gates, placeholder flags ==")
held = dict(MUSINA_CARD, is_there_a_briefing_session="Yes", is_it_compulsory="Yes",
            briefing_date_and_time="2026-08-10 10:00")
hr = score(held, FULL_PROFILE, ENRICHED)
check("compulsory briefing already held -> band no_bid, not eligible",
      hr["band"] == "no_bid" and not hr["eligible"])
check("no numeric score on no_bid (score is None, never a fake number)",
      hr["score"] is None)
check("GATE-BRIEFING-HELD is the firing reason with the date quoted",
      any(f["code"] == "GATE-BRIEFING-HELD" and "2026-08-10" in f["detail"]
          for f in hr["hard_failures"]))
placeholder = dict(held, briefing_date_and_time="0001-01-01 00:00")
pr = score(placeholder, FULL_PROFILE, ENRICHED)
check("placeholder briefing date NEVER gates (positive evidence only)",
      pr["eligible"] and pr["band"] != "no_bid" and pr["score"] is not None)
check("placeholder surfaces as a data-hygiene flag + manual check",
      any(f["code"] == "FLAG-BRIEFING-PLACEHOLDER" for f in pr["data_flags"])
      and any(m["code"] == "GATE-BRIEFING-HELD" for m in pr["manual_checks"]))
future = dict(held, briefing_date_and_time="2026-09-01 10:00")
fr = score(future, FULL_PROFILE, ENRICHED)
check("attendable future briefing never gates; it costs process feasibility",
      fr["eligible"]
      and fr["dimensions"]["process_feasibility"]["points"]
      < strong["dimensions"]["process_feasibility"]["points"])
closed = dict(MUSINA_CARD, closing_date="2026-08-01")
cr = score(closed, FULL_PROFILE, ENRICHED)
check("closing date passed -> no_bid via GATE-CLOSED, score None",
      cr["band"] == "no_bid" and cr["score"] is None
      and any(f["code"] == "GATE-CLOSED" for f in cr["hard_failures"]))
multi = dict(closed, is_it_compulsory="Yes", briefing_date_and_time="2026-08-10 10:00")
mr = score(multi, FULL_PROFILE, ENRICHED)
check("ALL firing gate reasons are returned together",
      {f["code"] for f in mr["hard_failures"]} >= {"GATE-CLOSED", "GATE-BRIEFING-HELD"})

# --------------------------------------------------------------------------
# (d) stage-1 gates: CIDB (category-triggered statutory + extracted grade)
# --------------------------------------------------------------------------
print("== (d) CIDB gate: statutory category trigger, grade compare, JV rule ==")
ROADS_CARD = {
    "slug": "ocds-test-2",
    "title": "Construction of a gravel access road and stormwater works",
    "institution": "Vhembe District Municipality",
    "category": "Civil engineering",
    "tender_type": "Request for Bid(Open-Tender)",
    "province": "Limpopo",
    "status": "ACTIVE",
    "closing_date": "2026-09-20",
    "is_it_compulsory": "No",
}
construction_profile = dict(FULL_PROFILE,
                            operating_sectors="construction, civil engineering")
ungraded = dict(construction_profile, cidb_grade="")
ug = score(ROADS_CARD, ungraded, None)
check("category-triggered CIDB (no quoted grade) gates an UNGRADED profile - "
      "statutory breadth",
      ug["band"] == "no_bid" and ug["score"] is None
      and any(f["code"] == "GATE-CIDB" and "statutory" in f["detail"]
              for f in ug["hard_failures"]))
graded_unquoted = dict(construction_profile, cidb_grade="2GB")
gu = score(ROADS_CARD, graded_unquoted, None)
check("graded profile vs unquoted grade -> provisional pass + manual check",
      gu["eligible"]
      and any(n["code"] == "GATE-CIDB" and n["status"] == "provisional"
              for n in gu["gate_notes"])
      and any(m["code"] == "GATE-CIDB" for m in gu["manual_checks"]))
CIDB_TASKS = {"enrichment": "ADVANCED", "tasks": [
    "Confirm CIDB contractor grading '6CE OR HIGHER' is active and in good standing | 1",
]}
low = score(ROADS_CARD, dict(construction_profile, cidb_grade="1CE"), CIDB_TASKS)
check("CIDB 1CE vs required 6CE -> no_bid with an actionable below-grade reason",
      low["band"] == "no_bid"
      and any(f["code"] == "GATE-CIDB" and "below" in f["detail"]
              for f in low["hard_failures"]))
check("the quoted CIDB requirement is surfaced in warnings",
      any("6CE OR HIGHER" in w for w in low["warnings"]))
wrong_class = score(ROADS_CARD, dict(construction_profile, cidb_grade="8GB"), CIDB_TASKS)
check("CIDB class mismatch (8GB vs 6CE) hard-fails with a class reason",
      any(f["code"] == "GATE-CIDB" and "class" in f["detail"].lower()
          for f in wrong_class["hard_failures"]))
good = score(ROADS_CARD, dict(construction_profile, cidb_grade="7CE"), CIDB_TASKS)
check("CIDB 7CE vs required 6CE passes the gate cleanly (eligible, scored)",
      good["eligible"] and good["score"] is not None)
jv = score(ROADS_CARD, dict(construction_profile, cidb_grade="5CE"), CIDB_TASKS)
check("one grade below (5CE vs 6CE) -> JV-CONDITIONAL pass, never clean",
      jv["eligible"]
      and any(n["code"] == "GATE-CIDB" and n["status"] == "conditional"
              and "joint venture" in n["detail"].lower() for n in jv["gate_notes"])
      and any(m["code"] == "GATE-CIDB" for m in jv["manual_checks"]))
two_below = score(ROADS_CARD, dict(construction_profile, cidb_grade="4CE"), CIDB_TASKS)
check("two grades below (4CE vs 6CE) still hard-fails",
      two_below["band"] == "no_bid")

# --------------------------------------------------------------------------
# (e) stage-1 gates: B-BBEE prequal union + profile completeness
# --------------------------------------------------------------------------
print("== (e) B-BBEE prequalification + profile completeness ==")
ESKOM_CARD = dict(MUSINA_CARD, slug="ocds-test-3", institution="ESKOM SOC Ltd",
                  province="National")
no_bee = dict(FULL_PROFILE, bbbee_level="")
nb = score(ESKOM_CARD, no_bee, ENRICHED)
check("buyer-fixture B-BBEE prequal trigger (Eskom) + no level -> no_bid",
      nb["band"] == "no_bid"
      and any(f["code"] == "GATE-BBBEE-PREQUAL" for f in nb["hard_failures"]))
ok_bee = score(ESKOM_CARD, FULL_PROFILE, ENRICHED)
check("valid certificate passes the prequal gate provisionally (note kept)",
      ok_bee["eligible"]
      and any(n["code"] == "GATE-BBBEE-PREQUAL" and n["status"] == "satisfied"
              for n in ok_bee["gate_notes"]))
PREQUAL_TASKS = {"enrichment": "ADVANCED", "tasks": [
    "Pre-qualification criteria: valid B-BBEE certificate level 1-2 required (pass/fail) | 1",
]}
pq = score(MUSINA_CARD, no_bee, PREQUAL_TASKS)
check("quoted pack pre-qualification evidence also triggers the gate (union)",
      pq["band"] == "no_bid"
      and any(f["code"] == "GATE-BBBEE-PREQUAL" and "quoted" in f["detail"]
              for f in pq["hard_failures"]))
POINTS_TABLE_TASKS = {"enrichment": "ADVANCED", "tasks": [
    "Preference points: B-BBEE Level 1 = 20 points, Level 2 = 18 points, Level 8 = 2 points | 1",
]}
pt = score(MUSINA_CARD, no_bee, POINTS_TABLE_TASKS)
check("B-BBEE level MENTIONS (points tables) never gate - over-enumeration guard",
      pt["eligible"]
      and not any(f["code"] == "GATE-BBBEE-PREQUAL" for f in pt["hard_failures"]))
check("parse_bbbee_prequal_evidence needs BOTH tokens",
      suitability.parse_bbbee_prequal_evidence(
          ["Pre-qualification: B-BBEE level 2 or better"]) is not None
      and suitability.parse_bbbee_prequal_evidence(
          ["B-BBEE Level 1 = 20 points"]) is None
      and suitability.parse_bbbee_prequal_evidence(
          ["Pre-qualification: local production"]) is None)

incomplete = dict(FULL_PROFILE, csd_maaa_number="", tcs_pin="")
inc = score(MUSINA_CARD, incomplete, ENRICHED)
check("missing CSD/TCS -> ONE grouped PROFILE-INCOMPLETE gate (present once)",
      inc["band"] == "no_bid" and inc["score"] is None
      and sum(1 for f in inc["hard_failures"] if f["code"] == "PROFILE-INCOMPLETE") == 1)
check("profile_completeness block lists exactly the missing registrations",
      inc["profile_completeness"]["complete"] is False
      and len(inc["profile_completeness"]["missing"]) == 2
      and any("CSD" in m for m in inc["profile_completeness"]["missing"]))
check("no per-card GATE-CSD/GATE-TCS entries (reported once, not per rule)",
      not any(f["code"] in ("GATE-CSD", "GATE-TCS", "GATE-CIPC")
              for f in inc["hard_failures"]))
expired_bee = dict(FULL_PROFILE, bbbee_certificate_expiry="2026-01-01")
eb = score(MUSINA_CARD, expired_bee, ENRICHED)
check("expired B-BBEE on a non-prequal card is a points-only warning, not a gate",
      eb["eligible"]
      and any("B-BBEE" in w and "points" in w for w in eb["warnings"]))

# --------------------------------------------------------------------------
# (f) stage-2 details: readiness gap list, pack-informed, mismatches
# --------------------------------------------------------------------------
print("== (f) readiness gap list + pack-informed factor ==")
DEMANDING = {"enrichment": "ADVANCED", "tasks": [
    "Verify Tax Compliance status on SARS and provide valid PIN | 1",
    "Provide municipal rates account not older than 90 days | 1",
    "Provide COIDA letter of good standing | 1",
    "Provide PSIRA registration certificate | 1",
    "Provide track record: previous projects with reference letters | 1",
]}
rd = score(MUSINA_CARD, FULL_PROFILE, DEMANDING)
readiness_reason = rd["dimensions"]["readiness"]["reasons"][0]
check("readiness counts demanded returnables vs profile evidence (4/5 here)",
      readiness_reason["code"] == "READINESS-GAPLIST"
      and len(readiness_reason["demanded"]) == 5
      and len(readiness_reason["evidenced"]) == 4)
check("the gap list names the missing returnable (PSIRA)",
      any("PSIRA" in gap for gap in readiness_reason["gaps"]))
HIGH_FN = {"enrichment": "ADVANCED", "tasks": [
    "Achieve the minimum functionality threshold of 80 to proceed | 2"]}
hf = score(MUSINA_CARD, FULL_PROFILE, HIGH_FN)
fn_reasons = hf["dimensions"]["pack_informed"]["reasons"]
check("quoted 80 threshold (no-% form) -> high demand, reduced pack points, quoted",
      any(r.get("threshold_pct") == 80 and r.get("demand") == "high"
          and "threshold of 80" in r.get("quoted", "") for r in fn_reasons)
      and hf["dimensions"]["pack_informed"]["points"]
      < suitability.FIT_WEIGHTS["pack_informed"])
mismatch = dict(FULL_PROFILE, operating_sectors="catering, farming",
                capability_texts=[], operating_provinces="Western Cape")
mm = score(MUSINA_CARD, mismatch, ENRICHED)
check("declared-but-unmatched sectors score low with the sectors named",
      mm["dimensions"]["sector_fit"]["reasons"][0]["code"] == "SECTOR-MISMATCH"
      and "catering" in mm["dimensions"]["sector_fit"]["reasons"][0]["detail"])
check("province mismatch scores low with both provinces named",
      mm["dimensions"]["geography_fit"]["reasons"][0]["code"] == "GEO-MISMATCH"
      and "Limpopo" in mm["dimensions"]["geography_fit"]["reasons"][0]["detail"])
national = dict(MUSINA_CARD, province="National")
nat = score(national, mismatch, ENRICHED)
check("national / unspecified opportunities match every declared footprint",
      nat["dimensions"]["geography_fit"]["points"]
      == suitability.FIT_WEIGHTS["geography_fit"])

# --------------------------------------------------------------------------
# (g) grants: jurisdiction gate first, then fit
# --------------------------------------------------------------------------
print("== (g) grants: jurisdiction-gate-first, fit second ==")
GRANT_CARD = {
    "slug": "2026-12-01_SME_Digitalisation",
    "title": "Grant Opportunity: SME Digitalisation Support",
    "organization": "Small Enterprise Development Agency",
    "focus_area": "ICT adoption, software, digital transformation for SMEs",
    "category": "General",
    "deadline": "2026-12-01",
}
grant = score(GRANT_CARD, FULL_PROFILE, None, opportunity_type="grants")
check("grant with no explicit jurisdiction fence is scored, not gated",
      grant["eligible"] and grant["score"] is not None)
check("unstated grant jurisdiction surfaces as a manual check",
      any(m["code"] == "GRANT-JURISDICTION" for m in grant["manual_checks"]))
check("grant sector fit matches on focus_area",
      grant["dimensions"]["sector_fit"]["reasons"][0]["code"] == "SECTOR-MATCH")
check("tender rule corpus never applies to grants (no quirk/kill manual checks)",
      not any(str(m["code"]).startswith(("QUIRK-", "KILL-", "PROCESS-"))
              for m in grant["manual_checks"]))
FOREIGN_GRANT = dict(GRANT_CARD, slug="nz-waste",
                     title="Grant Opportunity: Waste Minimisation Fund in New Zealand",
                     focus_area="Waste minimisation, resource efficiency")
fg = score(FOREIGN_GRANT, FULL_PROFILE, None, opportunity_type="grants")
check("explicit foreign jurisdiction (in New Zealand) gates the grant",
      fg["band"] == "no_bid" and fg["score"] is None
      and any(f["code"] == "GATE-JURISDICTION" for f in fg["hard_failures"]))
SA_GRANT = dict(GRANT_CARD, slug="sa-grant",
                title="Grant Opportunity: Township Digitalisation in South Africa")
sg = score(SA_GRANT, FULL_PROFILE, None, opportunity_type="grants")
check("a South Africa mention never trips the jurisdiction gate",
      sg["eligible"])
past_grant = dict(GRANT_CARD, deadline="2026-04-17")
pg = score(past_grant, FULL_PROFILE, None, opportunity_type="grants")
check("expired grant deadline gates (GATE-CLOSED)",
      pg["band"] == "no_bid"
      and any(f["code"] == "GATE-CLOSED" for f in pg["hard_failures"]))

# --------------------------------------------------------------------------
# (h) equity: standing-fit shortlist semantics
# --------------------------------------------------------------------------
print("== (h) equity: standing-fit shortlist (no urgency dims) ==")
EQUITY_CARD = {
    "slug": "sa-vc-fund",
    "title": "Equity Opportunity: Ubuntu Ventures",
    "organization": "Ubuntu Ventures",
    "funder_type": "VC",
    "funding_type": "Seed",
    "industry": "Tech / ICT / software",
    "territory": "Africa",
    "country": "South Africa",
    "category": "General",
}
eq = score(EQUITY_CARD, FULL_PROFILE, None, opportunity_type="equity")
check("equity semantics is standing_fit_shortlist (no gates, no deadline dims)",
      eq["semantics"] == "standing_fit_shortlist" and eq["hard_failures"] == []
      and eq["days_to_close"] is None)
check("equity scores over sector + territory only (other factors not applicable)",
      eq["dimensions"]["sector_fit"]["known"]
      and eq["dimensions"]["geography_fit"]["known"]
      and not eq["dimensions"]["process_feasibility"]["known"]
      and not eq["dimensions"]["engagement_economics"]["known"]
      and eq["known_weight"] == suitability.FIT_WEIGHTS["sector_fit"]
      + suitability.FIT_WEIGHTS["geography_fit"])
FOREIGN_EQUITY = dict(EQUITY_CARD, slug="us-vc", territory="North America", country="USA")
feq = score(FOREIGN_EQUITY, FULL_PROFILE, None, opportunity_type="equity")
check("out-of-territory funder ranks low, never 'ineligible'",
      feq["hard_failures"] == [] and feq["score"] < eq["score"])
nothing_known = score(dict(EQUITY_CARD, territory="", country=""),
                      {"operating_sectors": ""}, None, opportunity_type="equity")
check("nothing known -> band 'unscored', never a fake number",
      nothing_known["score"] is None and nothing_known["band"] == "unscored")

# --------------------------------------------------------------------------
# (i) endpoint: friendly errors, entitlement fence, result shape
# --------------------------------------------------------------------------
print("== (i) get_tender_suitability endpoint ==")

for mod_name in ("_app_stub", "_app_stub.tender", "_app_stub.tender.control",
                 "_app_stub.tender.control.api", "_app_stub.tender.control.api.tenders",
                 "_app_stub.tender.control.compliance"):
    sys.modules.setdefault(mod_name, types.ModuleType(mod_name))

CATALOGS = {"tenders": [MUSINA_CARD], "grants": [GRANT_CARD], "equity": [EQUITY_CARD]}
ou_stub = types.ModuleType("_app_stub.tender.control.api.opportunity_utils")
ou_stub.get_cached_opportunities = lambda kind: CATALOGS.get(kind, [])
sys.modules["_app_stub.tender.control.api.opportunity_utils"] = ou_stub

ENTITLED = {"entitled": False, "reason": "plan_excludes_tenders", "plan": None}
ent_stub = types.ModuleType("_app_stub.tender.control.api.tenders.tender_entitlement")
ent_stub.find_tender_by_slug = lambda slug: next(
    (c for c in CATALOGS["tenders"] if c["slug"] == slug), None)
ent_stub.get_enrichment_for_slug = lambda slug: ENRICHED
ent_stub.get_tender_entitlement = lambda user=None: dict(ENTITLED)
sys.modules["_app_stub.tender.control.api.tenders.tender_entitlement"] = ent_stub

rules_stub = types.ModuleType("_app_stub.tender.control.compliance.rules")
rules_stub.load_rules = lambda rule_class=None: list(ALL_RULES)
rules_stub.get_scoring_rule = lambda code: dict(FUNCTIONALITY_PARAMS)
sys.modules["_app_stub.tender.control.compliance.rules"] = rules_stub
sys.modules["_app_stub.tender.control.compliance.suitability"] = suitability

endpoint = load_endpoint("s_endpoint", "api/tenders/get_tender_suitability.py")


def throws(fn, needle):
    try:
        fn()
        return False
    except Thrown as e:
        return needle in str(e)


class FakeProfileDoc(dict):
    def get(self, key, default=None):
        return dict.get(self, key, default)


PROFILE_DOC = FakeProfileDoc(FULL_PROFILE)
PROFILE_DOC["capabilities"] = [
    {"label": "Reference site", "detail": "municipal helpdesk rollout"}]
PROFILE_DOC.pop("capability_texts", None)
PROFILE_DOC["coida_good_standing"] = 1
PROFILE_DOC["municipal_rates_current"] = 1
PROFILE_DOC["track_record_evidence"] = 1

frappe_stub.conf = {"app_role": "tenant"}
check("wrong app role -> Action Not Allowed",
      throws(lambda: endpoint.get_tender_suitability("ocds-test-1"), "Action Not Allowed"))
frappe_stub.conf = {"app_role": "control"}

frappe_stub.session = types.SimpleNamespace(user="Guest")
check("guest -> friendly log-in error",
      throws(lambda: endpoint.get_tender_suitability("ocds-test-1"), "log in"))
frappe_stub.session = types.SimpleNamespace(user="desk@example.com")

frappe_stub.db.get_value = lambda *a, **k: None
check("no business profile -> friendly Business Profile Needed error",
      throws(lambda: endpoint.get_tender_suitability("ocds-test-1"),
             "Business Profile Needed"))

frappe_stub.db.get_value = lambda doctype, filters=None, fieldname=None, **k: "TBP-00001"
frappe_stub.get_doc = lambda doctype, name: PROFILE_DOC

check("unknown opportunity_type -> friendly error naming the options",
      throws(lambda: endpoint.get_tender_suitability("x", opportunity_type="bonds"),
             "tenders, grants or equity"))
check("unknown slug -> not-found error",
      throws(lambda: endpoint.get_tender_suitability("no-such-slug"), "not found"))

res = endpoint.get_tender_suitability("ocds-test-1")
check("non-entitled caller: scored WITHOUT enrichment (enrichment_used False)",
      res["enrichment_used"] is False and res["entitled"] is False
      and res["entitlement_reason"] == "plan_excludes_tenders")
check("non-entitled result never quotes enrichment lines and is advert_only",
      not any("quoted from enrichment" in json.dumps(w) for w in res["warnings"])
      and res["source_record_class"] == "Advert-Only"
      and res["confidence"] == "advert_only")
check("result carries card identity + score + band + confidence + dimensions",
      res["slug"] == "ocds-test-1" and res["title"] == MUSINA_CARD["title"]
      and isinstance(res["score"], int)
      and res["band"] in ("strong", "review", "marginal", "poor", "no_bid", "unscored")
      and set(res["dimensions"]) == set(suitability.FIT_WEIGHTS)
      and isinstance(res["days_to_close"], int))
check("check-field readiness evidence snapshots as '1' (never a truthy '0')",
      endpoint.profile_snapshot(PROFILE_DOC)["coida_good_standing"] == "1"
      and endpoint.profile_snapshot(
          FakeProfileDoc(dict(PROFILE_DOC, coida_good_standing=0))
      )["coida_good_standing"] == "")

ENTITLED.update({"entitled": True, "reason": "plan", "plan": "PLAN-1"})
res_ent = endpoint.get_tender_suitability("ocds-test-1")
check("entitled caller: enrichment feeds the score (pack_verified, Full record)",
      res_ent["enrichment_used"] is True
      and res_ent["source_record_class"] == "Full"
      and res_ent["confidence"] == "pack_verified"
      and res_ent["dimensions"]["readiness"]["known"])

grant_res = endpoint.get_tender_suitability(GRANT_CARD["slug"], opportunity_type="grants")
check("grants route resolves by slug from the grants catalog",
      grant_res["opportunity_type"] == "grants"
      and grant_res["institution"] == GRANT_CARD["organization"]
      and grant_res["closing_date"] == GRANT_CARD["deadline"])
equity_res = endpoint.get_tender_suitability(EQUITY_CARD["slug"], opportunity_type="equity")
check("equity route returns standing-fit semantics",
      equity_res["semantics"] == "standing_fit_shortlist")

# --------------------------------------------------------------------------
# (j) additive registrations: manifest families + doctype fields
# --------------------------------------------------------------------------
print("== (j) manifest + doctype registrations (additive) ==")
with open(os.path.join(REPO, "tender/frappe/manifest.json"), encoding="utf-8") as f:
    manifest = json.load(f)
methods = manifest["app_type"]["control"]["hooks"]["whitelisted_methods"]
TARGET = "{app_name}.tender.control.api.tenders.get_tender_suitability.get_tender_suitability"
for key in ("{app_name}.api.tenders.get_tender_suitability",
            "control:get_tender_suitability",
            "control.control.api.tenders.get_tender_suitability"):
    check("manifest registers %s" % key, methods.get(key) == TARGET)
check("sibling endpoint registrations untouched",
      methods.get("control:get_my_bids")
      == "{app_name}.tender.control.api.tenders.get_my_bids.get_my_bids"
      and methods.get("control:attach_returnable_artifact")
      == "{app_name}.tender.control.api.tenders.attach_returnable_artifact"
         ".attach_returnable_artifact")

with open(os.path.join(
        SRC, "doctype/tender_business_profile/tender_business_profile.json"),
        encoding="utf-8") as f:
    profile_doctype = json.load(f)
fieldnames = [fld["fieldname"] for fld in profile_doctype["fields"]]
check("profile doctype keeps operating_sectors + operating_provinces",
      "operating_sectors" in fieldnames and "operating_provinces" in fieldnames)
for new_field in ("briefing_travel_radius", "coida_good_standing",
                  "municipal_rates_current", "psira_registered",
                  "nhbrc_registered", "track_record_evidence"):
    check("profile doctype gains %s (additive)" % new_field,
          new_field in fieldnames and new_field in profile_doctype["field_order"])
for existing in ("csd_maaa_number", "tcs_pin", "cidb_grade", "bbbee_level",
                 "capabilities", "witnesses", "directors"):
    check("existing profile field %s untouched" % existing, existing in fieldnames)
profile_py = open(os.path.join(
    SRC, "doctype/tender_business_profile/tender_business_profile.py"),
    encoding="utf-8").read()
check("FILL_FIELDS untouched (no new field leaked into pack auto-fill)",
      "coida_good_standing" not in profile_py
      and "briefing_travel_radius" not in profile_py)

# --------------------------------------------------------------------------
print()
passed = sum(1 for _, ok in checks if ok)
print(f"{passed}/{len(checks)} checks passed")
sys.exit(0 if passed == len(checks) else 1)
