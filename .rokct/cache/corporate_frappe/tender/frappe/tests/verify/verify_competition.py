#!/usr/bin/env python3
"""Standalone verification for the low-competition tender finder -
deterministic FIELD-NARROWNESS scoring per catalog card from public
requirements only, NEVER a win probability. Proves the pure module
(compliance/competition.py): the two new whitelisted extractors
(EME/QSE set-asides with the affidavit noise guard, local-content
statements), narrowness scoring across signal combinations with the
documented weights, tier boundaries, the no-signal -> wide rule, the
score cap, the meets-requirements crossing that REUSES suitability.py's
gate functions (check_cidb_gate, check_bbbee) instead of forking them,
and the per-card opportunity verdict. Also proves the wiring:
get_low_competition_tenders registered in ALL THREE manifest cmd
families, and the endpoint's payload against a stubbed frappe (login
required, control-only, enrichment only for entitled callers, ranked
deterministic output, honesty caveats). Exit code 0 = all checks
pass."""

import importlib.util
import json
import os
import sys
import types

# O-05: in-tree suite runs must leave no __pycache__ litter under src/
sys.dont_write_bytecode = True

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SRC = os.path.join(REPO, "tender/frappe/src/control")
MANIFEST = os.path.join(REPO, "tender/frappe/manifest.json")

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


# --------------------------------------------------------------------------
# frappe stub (suitability.py imports frappe.utils.cint at module load)
# --------------------------------------------------------------------------
class Thrown(Exception):
    pass


frappe_stub = types.ModuleType("frappe")
utils_stub = types.ModuleType("frappe.utils")
utils_stub.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
utils_stub.flt = lambda v, precision=None: float(v) if v not in (None, "") else 0.0
utils_stub.nowdate = lambda: "2026-08-23"
frappe_stub.utils = utils_stub
sys.modules["frappe"] = frappe_stub
sys.modules["frappe.utils"] = utils_stub


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


competition = load_module("v_competition", os.path.join(SRC, "compliance/competition.py"))
TODAY = "2026-08-23"

# --------------------------------------------------------------------------
# (a) set-aside extraction: quoted-or-nothing, affidavit noise guard
# --------------------------------------------------------------------------
print("== (a) EME/QSE set-aside extraction ==")
sa = competition.parse_set_aside(["This tender is set aside for EMEs only | 1"])
check("'set aside for EMEs' -> classes [EME], quotes its line",
      sa and sa["classes"] == ["EME"] and "set aside for EMEs" in sa["quoted"])
check("'reserved for QSEs' -> classes [QSE]",
      competition.parse_set_aside(["Cleaning services reserved for QSEs"])
      == {"classes": ["QSE"], "quoted": "Cleaning services reserved for QSEs"})
check("prequalification wording counts: 'Pre-qualification: only an EME or QSE may respond'",
      competition.parse_set_aside(
          ["Pre-qualification: only an EME or QSE may respond"])["classes"]
      == ["EME", "QSE"])
check("bare EME mention without a set-aside token NEVER counts",
      competition.parse_set_aside(["EME bidders are encouraged to apply"]) is None)
check("affidavit-explainer lines are noise, never set-asides",
      competition.parse_set_aside(
          ["Provide the sworn EME/QSE affidavit for pre-qualification"]) is None)
check("a set-aside token without a class token never counts",
      competition.parse_set_aside(["Set aside for military veterans"]) is None)
check("empty / None input -> None",
      competition.parse_set_aside([]) is None
      and competition.parse_set_aside(None) is None)

print("== (a2) local-content extraction ==")
lc = competition.parse_local_content(
    ["Local content: SATS 1286 minimum threshold applies | 2"])
check("'local content ... SATS 1286' line -> quoted",
      lc and "SATS 1286" in lc["quoted"])
check("'designated sector' token counts",
      competition.parse_local_content(
          ["This is a designated sector procurement"]) is not None)
check("unrelated lines never count",
      competition.parse_local_content(["Submit the tax PIN"]) is None)

print("== (a3) profile enterprise class ==")
check("descriptive select options parse to the leading class token",
      competition.profile_enterprise_class(
          {"enterprise_type": "EME (turnover under R10m - sworn affidavit)"}) == "EME"
      and competition.profile_enterprise_class(
          {"enterprise_type": "QSE (R10m-R50m - sworn affidavit)"}) == "QSE"
      and competition.profile_enterprise_class(
          {"enterprise_type": "Generic (over R50m - SANAS certificate)"}) == "GENERIC")
check("undeclared enterprise type -> None (unknown, never a fail)",
      competition.profile_enterprise_class({}) is None
      and competition.profile_enterprise_class({"enterprise_type": ""}) is None)

# --------------------------------------------------------------------------
# (b) reuse proof: suitability's extractors are imported, never forked
# --------------------------------------------------------------------------
print("== (b) suitability logic is REUSED, not re-implemented ==")
with open(os.path.join(SRC, "compliance/competition.py"), encoding="utf-8") as f:
    competition_src = f.read()
check("competition.py imports the CIDB/prequal/date/gate functions from "
      "suitability.py",
      "from .suitability import" in competition_src
      and "parse_cidb_requirement" in competition_src
      and "check_cidb_gate" in competition_src
      and "check_bbbee" in competition_src)
check("no forked re-implementation: competition.py defines none of the "
      "suitability extractors or their regexes",
      "def parse_cidb_requirement" not in competition_src
      and "def parse_bbbee_prequal_evidence" not in competition_src
      and "def check_cidb_gate" not in competition_src
      and "def check_bbbee" not in competition_src
      and "RE_CIDB" not in competition_src
      and "RE_BBBEE_TOKEN" not in competition_src)
check("the reused extractor works through competition's namespace "
      "(CIDB '7CE' quoted-or-nothing)",
      competition.parse_cidb_requirement(["CIDB grading 7CE required"])
      == {"grade": 7, "class_code": "CE", "quoted": "CIDB grading 7CE required"})

# --------------------------------------------------------------------------
# (c) narrowness scoring across signal combinations
# --------------------------------------------------------------------------
print("== (c) narrowness scoring: documented weighted sum ==")


def narrow(card, tasks=None):
    return competition.score_field_narrowness(card, task_texts=tasks, today=TODAY)


plain = narrow({"title": "Supply of stationery", "closing_date": "2026-10-30"})
check("no-signal card -> score 0, tier wide, no signals",
      plain["score"] == 0 and plain["tier"] == "wide" and plain["signals"] == [])

cidb1 = narrow({"title": "Minor works"}, ["CIDB grading 1CE or higher required"])
check("CIDB grade 1 -> base 10 points (wide)",
      cidb1["score"] == 10 and cidb1["tier"] == "wide"
      and cidb1["signals"][0]["code"] == "NARROW-CIDB")
cidb7 = narrow({"title": "Roadworks"}, ["CIDB Grade 7 CE required, active at close"])
check("CIDB grade 7 -> 10 + 4x6 = 34 points (moderate), reason names the "
      "grade-7 exclusion",
      cidb7["score"] == 34 and cidb7["tier"] == "moderate"
      and "grade 7+" in cidb7["signals"][0]["detail"])
cidb9 = narrow({"title": "Dam"}, ["CIDB 9CE contractor grading required"])
check("CIDB grade 9 -> 42 points", cidb9["score"] == 42)

sa_only = narrow({"title": "Supply set aside for EMEs"})
check("EME set-aside alone -> 25 (moderate)",
      sa_only["score"] == 25 and sa_only["tier"] == "moderate")
sa_pq = narrow({"title": "Supply set aside for EMEs"},
               ["B-BBEE pre-qualification: minimum status level 2 applies"])
check("set-aside + B-BBEE prequal -> 25 + 15 = 40 (narrow)",
      sa_pq["score"] == 40 and sa_pq["tier"] == "narrow")
check("a B-BBEE level mention WITHOUT prequal wording never narrows "
      "(suitability's over-enumeration guard, reused)",
      narrow({"title": "Supply"},
             ["B-BBEE points table: level 1 = 20 points"])["score"] == 0)

metro_brief = narrow({"title": "T", "is_it_compulsory": "Yes",
                      "province": "Gauteng",
                      "briefing_date_and_time": "2026-09-01 10:00"})
check("compulsory briefing (metro province) -> 10",
      metro_brief["score"] == 10 and not metro_brief["signals"][0]["non_metro"])
rural_brief = narrow({"title": "T", "is_it_compulsory": "Yes",
                      "province": "Limpopo",
                      "briefing_date_and_time": "2026-09-01 10:00"})
check("compulsory briefing in a non-metro province -> 10 + 8 = 18, reason "
      "names the travel filter",
      rural_brief["score"] == 18 and rural_brief["signals"][0]["non_metro"]
      and "no metro" in rural_brief["signals"][0]["detail"])

check("<= 7 days to close -> 15; 8-14 days -> 8; > 14 days -> nothing; "
      "already-closed -> no window signal",
      narrow({"title": "T", "closing_date": "2026-08-28"})["score"] == 15
      and narrow({"title": "T", "closing_date": "2026-09-02"})["score"] == 8
      and narrow({"title": "T", "closing_date": "2026-09-15"})["score"] == 0
      and narrow({"title": "T", "closing_date": "2026-08-01"})["score"] == 0)

check("local content -> 10",
      narrow({"title": "T"}, ["Local content: SATS 1286 threshold"])["score"] == 10)

everything = narrow(
    {"title": "Works set aside for EMEs", "is_it_compulsory": "Yes",
     "province": "Northern Cape", "briefing_date_and_time": "2026-08-25 10:00",
     "closing_date": "2026-08-28"},
    ["CIDB 9CE grading required",
     "B-BBEE pre-qualification: level 1 required",
     "Local content: SATS 1286 threshold applies"])
check("all signals together cap at 100 (42+25+15+18+15+10 = 125 -> 100), "
      "tier very_narrow, six signals each with a human-readable reason",
      everything["score"] == 100 and everything["tier"] == "very_narrow"
      and len(everything["signals"]) == 6
      and all(s["detail"] for s in everything["signals"]))
check("every payload carries the field-not-win semantics",
      "NEVER a win probability" in everything["semantics"]
      and "NEVER a win probability" in plain["semantics"])

print("== (c2) tier boundaries ==")
check("tier boundaries: 19 wide / 20 moderate / 39 moderate / 40 narrow / "
      "59 narrow / 60 very_narrow / 100 very_narrow",
      competition.tier_for(19) == "wide"
      and competition.tier_for(20) == "moderate"
      and competition.tier_for(39) == "moderate"
      and competition.tier_for(40) == "narrow"
      and competition.tier_for(59) == "narrow"
      and competition.tier_for(60) == "very_narrow"
      and competition.tier_for(100) == "very_narrow")
check("determinism: identical inputs give identical output",
      narrow({"title": "Works set aside for EMEs"},
             ["CIDB 7CE required"])
      == narrow({"title": "Works set aside for EMEs"}, ["CIDB 7CE required"]))

# --------------------------------------------------------------------------
# (d) meets-requirements crossing (suitability's gate logic reused)
# --------------------------------------------------------------------------
print("== (d) crossing the narrow field with the caller's profile ==")
EME_PROFILE = {
    "enterprise_type": "EME (turnover under R10m - sworn affidavit)",
    "bbbee_level": "1",
    "bbbee_certificate_expiry": "2027-01-01",
    "cidb_grade": "7CE",
    "operating_provinces": "Limpopo, Gauteng",
    "briefing_travel_radius": "National",
}


def cross(card, tasks=None, profile=EME_PROFILE):
    n = competition.score_field_narrowness(card, task_texts=tasks, today=TODAY)
    return competition.cross_with_profile(profile, n, today=TODAY)


r = cross({"title": "Roadworks"}, ["CIDB Grade 7 CE required"])
check("CIDB: profile 7CE meets required 7CE (check_cidb_gate reused)",
      r["checks"][0]["code"] == "NARROW-CIDB" and r["checks"][0]["met"] is True
      and r["meets_narrowing_requirements"])
r = cross({"title": "Roadworks"}, ["CIDB Grade 7 CE required"],
          dict(EME_PROFILE, cidb_grade="6CE"))
check("CIDB one grade below -> JV-conditional = unknown (caveat), never a "
      "clean pass and never a hard fail",
      r["checks"][0]["met"] is None and r["meets_narrowing_requirements"]
      and any("joint venture" in c for c in r["caveats"]))
r = cross({"title": "Roadworks"}, ["CIDB Grade 7 CE required"],
          dict(EME_PROFILE, cidb_grade="4CE"))
check("CIDB grade 4 vs required 7 -> affirmatively unmet, not an opportunity",
      r["checks"][0]["met"] is False and not r["meets_narrowing_requirements"])
r = cross({"title": "Roadworks"}, ["CIDB Grade 7 CE required"],
          dict(EME_PROFILE, cidb_grade="7GB"))
check("CIDB wrong works class -> unmet",
      r["checks"][0]["met"] is False)

r = cross({"title": "Supply set aside for EMEs"})
check("set-aside: EME profile inside an EME set-aside -> met",
      r["checks"][0]["met"] is True)
r = cross({"title": "Supply set aside for EMEs"},
          profile=dict(EME_PROFILE,
                       enterprise_type="Generic (over R50m - SANAS certificate)"))
check("set-aside: Generic profile against an EME set-aside -> unmet",
      r["checks"][0]["met"] is False and not r["meets_narrowing_requirements"])
r = cross({"title": "Supply set aside for EMEs"},
          profile=dict(EME_PROFILE, enterprise_type=""))
check("set-aside: undeclared enterprise type -> unknown, becomes a caveat, "
      "never silently blocks",
      r["checks"][0]["met"] is None and r["meets_narrowing_requirements"]
      and any("enterprise type" in c.lower() for c in r["caveats"]))

r = cross({"title": "T"}, ["B-BBEE pre-qualification: level 2 required"])
check("B-BBEE prequal: valid level 1 certificate -> met (check_bbbee reused)",
      r["checks"][0]["code"] == "NARROW-BBBEE-PREQUAL"
      and r["checks"][0]["met"] is True)
r = cross({"title": "T"}, ["B-BBEE pre-qualification: level 2 required"],
          dict(EME_PROFILE, bbbee_level="Non-compliant"))
check("B-BBEE prequal: non-compliant profile -> unmet",
      r["checks"][0]["met"] is False)
r = cross({"title": "T"}, ["B-BBEE pre-qualification: level 2 required"],
          dict(EME_PROFILE, bbbee_certificate_expiry="2026-01-01"))
check("B-BBEE prequal: expired certificate -> unmet",
      r["checks"][0]["met"] is False)

BRIEF_CARD = {"title": "T", "is_it_compulsory": "Yes", "province": "Limpopo",
              "briefing_date_and_time": "2026-09-01 10:00"}
r = cross(BRIEF_CARD)
check("briefing inside the declared footprint -> met",
      r["checks"][0]["code"] == "NARROW-BRIEFING" and r["checks"][0]["met"] is True)
r = cross(dict(BRIEF_CARD, province="Northern Cape"),
          profile=dict(EME_PROFILE,
                       briefing_travel_radius="Local (own provinces only)"))
check("briefing outside the footprint with a local-only travel radius -> unmet",
      r["checks"][0]["met"] is False and not r["meets_narrowing_requirements"])
r = cross(dict(BRIEF_CARD, province="Northern Cape"))
check("briefing outside the footprint with a national radius -> met",
      r["checks"][0]["met"] is True)
r = cross(dict(BRIEF_CARD, briefing_date_and_time="0001-01-01 00:00"))
check("placeholder briefing date -> unknown + caveat (positive evidence "
      "only, suitability's placeholder rule reused)",
      r["checks"][0]["met"] is None
      and any("placeholder" in c for c in r["caveats"]))
r = cross(dict(BRIEF_CARD, briefing_date_and_time="2026-08-10 10:00"))
check("briefing already held -> affirmatively unmet (field closed to "
      "newcomers)",
      r["checks"][0]["met"] is False)

r = cross({"title": "T", "closing_date": "2026-08-28"})
check("short window -> met with a standing-documents caveat (capacity, not "
      "registration)",
      r["checks"][0]["code"] == "NARROW-WINDOW" and r["checks"][0]["met"] is True
      and any("standing documents" in c for c in r["caveats"]))
r = cross({"title": "T"}, ["Local content: SATS 1286 threshold"])
check("local content -> unknown + verify-ability caveat, never blocks",
      r["checks"][0]["met"] is None and r["meets_narrowing_requirements"]
      and any("SATS 1286" in c for c in r["caveats"]))

# --------------------------------------------------------------------------
# (e) the per-card opportunity verdict
# --------------------------------------------------------------------------
print("== (e) opportunity verdict: narrow field AND requirements cleared ==")
NARROW_CARD = {"slug": "t-1", "title": "Works set aside for EMEs",
               "institution": "Musina Local Municipality",
               "is_it_compulsory": "Yes", "province": "Limpopo",
               "briefing_date_and_time": "2026-09-01 10:00",
               "closing_date": "2026-09-15"}
a = competition.assess_low_competition(NARROW_CARD, EME_PROFILE, today=TODAY)
check("narrow field + requirements cleared + open -> opportunity",
      a["opportunity"] and a["narrowness"]["tier"] == "narrow"
      and a["slug"] == "t-1" and not a["closed"])
a = competition.assess_low_competition(
    NARROW_CARD,
    dict(EME_PROFILE, enterprise_type="Generic (over R50m - SANAS certificate)"),
    today=TODAY)
check("narrow field but the caller misses the set-aside -> NOT an opportunity",
      not a["opportunity"]
      and not a["requirements"]["meets_narrowing_requirements"])
a = competition.assess_low_competition(
    {"slug": "t-2", "title": "Supply of stationery",
     "closing_date": "2026-10-30"}, EME_PROFILE, today=TODAY)
check("wide field -> never an opportunity even when everything is met",
      not a["opportunity"] and a["narrowness"]["tier"] == "wide")
a = competition.assess_low_competition(
    dict(NARROW_CARD, closing_date="2026-08-01"), EME_PROFILE, today=TODAY)
check("closing date passed -> closed, never an opportunity",
      a["closed"] and not a["opportunity"])

# --------------------------------------------------------------------------
# (f) manifest wiring: all three cmd families
# --------------------------------------------------------------------------
print("== (f) manifest wiring ==")
with open(MANIFEST, encoding="utf-8") as f:
    methods = json.load(f)["app_type"]["control"]["hooks"]["whitelisted_methods"]
target = ("{app_name}.tender.control.api.tenders.get_low_competition_tenders"
          ".get_low_competition_tenders")
check("get_low_competition_tenders rides the single gateway in ALL THREE "
      "cmd families ({app_name}.api.tenders.*, control:*, "
      "control.control.api.tenders.*)",
      methods.get("{app_name}.api.tenders.get_low_competition_tenders") == target
      and methods.get("control:get_low_competition_tenders") == target
      and methods.get("control.control.api.tenders.get_low_competition_tenders")
      == target)

# --------------------------------------------------------------------------
# (g) the endpoint against a stubbed frappe
# --------------------------------------------------------------------------
print("== (g) get_low_competition_tenders endpoint (frappe stubbed) ==")

CATALOG = [
    # very narrow ONLY once enrichment lines are visible (entitled callers)
    {"slug": "vn-1", "title": "Bulk water pipeline construction",
     "institution": "Vhembe District Municipality", "province": "Limpopo",
     "is_it_compulsory": "Yes", "briefing_date_and_time": "2026-09-01 10:00",
     "closing_date": "2026-09-15", "status": "ACTIVE"},
    # narrow from the advert surface alone
    {"slug": "n-1", "title": "Supply of stationery set aside for EMEs",
     "institution": "Capricorn District Municipality", "province": "Limpopo",
     "is_it_compulsory": "Yes", "briefing_date_and_time": "2026-08-30 10:00",
     "closing_date": "2026-09-02", "status": "ACTIVE"},
    # narrow but reserved for QSEs - an EME caller does not clear it
    {"slug": "unmet-1", "title": "Cleaning services reserved for QSEs",
     "institution": "Polokwane Local Municipality", "province": "Limpopo",
     "is_it_compulsory": "Yes", "briefing_date_and_time": "2026-08-30 10:00",
     "closing_date": "2026-09-20", "status": "ACTIVE"},
    # narrow on paper but already closed
    {"slug": "closed-1", "title": "Security set aside for EMEs",
     "institution": "Musina Local Municipality", "province": "Limpopo",
     "is_it_compulsory": "Yes", "briefing_date_and_time": "2026-07-01 10:00",
     "closing_date": "2026-08-01", "status": "CLOSED"},
    # wide - no narrowing signal at all
    {"slug": "wide-1", "title": "Supply of office furniture",
     "institution": "National Treasury", "province": "National",
     "closing_date": "2026-10-30", "status": "ACTIVE"},
]
ENRICHMENT = {
    "vn-1": {"enrichment": "ADVANCED", "tasks": [
        "Confirm CIDB contractor grading 7CE is active and in good standing | 1",
        "This tender is set aside for EMEs only | 1",
        "Local content: SATS 1286 minimum threshold applies | 2",
    ]},
}
PROFILE_DOC = dict(EME_PROFILE, csd_maaa_number="MAAA0123456",
                   tcs_pin="PIN123456789",
                   company_registration_no="2019/123456/07")


def build_frappe(user="desk@example.com", profile_exists=True):
    frappe = types.ModuleType("frappe")
    frappe.conf = {"app_role": "control"}
    frappe.session = types.SimpleNamespace(user=user)
    frappe.local = types.SimpleNamespace(request=None)
    frappe.whitelist = lambda *a, **k: (lambda fn: fn)
    frappe.PermissionError = PermissionError

    def throw(msg, exc=None, title=None):
        raise (exc if isinstance(exc, type) else Thrown)(msg)

    frappe.throw = throw
    frappe.get_request_header = lambda name: None
    frappe.db = types.SimpleNamespace(
        get_value=lambda *a, **k: "TBP-00001" if profile_exists else None)
    frappe.get_doc = lambda doctype, name: dict(PROFILE_DOC)
    utils = types.ModuleType("frappe.utils")
    utils.cint = utils_stub.cint
    utils.nowdate = lambda: TODAY
    frappe.utils = utils
    return frappe


def load_endpoint(frappe_mod, entitled=True):
    def read_with_stub(relpath, name):
        with open(os.path.join(SRC, relpath), encoding="utf-8") as f:
            source = f.read().replace("{app_name}", "_app_stub")
        module = types.ModuleType(name)
        module.__file__ = os.path.join(SRC, relpath)
        return source, module

    # fake package chain the endpoint imports lazily at call time
    pkg_names = ["_app_stub", "_app_stub.tender", "_app_stub.tender.control",
                 "_app_stub.tender.control.api",
                 "_app_stub.tender.control.api.tenders",
                 "_app_stub.tender.control.compliance"]
    mods = {}
    for name in pkg_names:
        mods[name] = types.ModuleType(name)
        mods[name].__path__ = []

    opp_utils = types.ModuleType("_app_stub.tender.control.api.opportunity_utils")
    opp_utils.get_cached_opportunities = lambda opt_type: (
        [dict(c) for c in CATALOG] if opt_type == "tenders" else {})
    entitle = types.ModuleType(
        "_app_stub.tender.control.api.tenders.tender_entitlement")
    entitle.get_tender_entitlement = lambda user=None: (
        {"entitled": True, "reason": "plan", "plan": "Pro"} if entitled
        else {"entitled": False, "reason": "plan_excludes_tenders", "plan": None})
    entitle.get_enrichment_for_slug = lambda slug: ENRICHMENT.get(slug)

    mods["_app_stub.tender.control.api.opportunity_utils"] = opp_utils
    mods["_app_stub.tender.control.api.tenders.tender_entitlement"] = entitle
    mods["_app_stub.tender.control.compliance.competition"] = competition
    mods["_app_stub.tender.control.compliance"].competition = competition
    mods["_app_stub.tender.control.api"].opportunity_utils = opp_utils
    mods["_app_stub.tender.control.api.tenders"].tender_entitlement = entitle

    saved = {}
    for name, mod in list(mods.items()) + [
            ("frappe", frappe_mod), ("frappe.utils", frappe_mod.utils)]:
        saved[name] = sys.modules.get(name)
        sys.modules[name] = mod
    try:
        # the REAL profile_snapshot (never a fork) from get_tender_suitability
        suit_src, suit_mod = read_with_stub(
            "api/tenders/get_tender_suitability.py",
            "_app_stub.tender.control.api.tenders.get_tender_suitability")
        exec(compile(suit_src, suit_mod.__file__, "exec"), suit_mod.__dict__)
        sys.modules[suit_mod.__name__] = suit_mod
        mods["_app_stub.tender.control.api.tenders"].get_tender_suitability = suit_mod

        ep_src, ep_mod = read_with_stub(
            "api/tenders/get_low_competition_tenders.py", "v_lowcomp_ep")
        exec(compile(ep_src, ep_mod.__file__, "exec"), ep_mod.__dict__)
        return ep_mod
    finally:
        for name, orig in saved.items():
            if name.startswith("_app_stub"):
                # imported lazily at CALL time - must stay importable
                continue
            if orig is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = orig


endpoint = load_endpoint(build_frappe(), entitled=True)
radar = endpoint.get_low_competition_tenders()
check("entitled caller: enrichment-narrowed vn-1 ranks first (very_narrow "
      "87), advert-narrowed n-1 second (narrow 51); unmet/closed/wide "
      "cards never appear",
      [o["slug"] for o in radar["opportunities"]] == ["vn-1", "n-1"]
      and radar["opportunities"][0]["narrowness"]["tier"] == "very_narrow"
      and radar["opportunities"][0]["narrowness"]["score"] == 87
      and radar["opportunities"][1]["narrowness"]["score"] == 51)
check("summary counts the scan honestly and the payload carries the "
      "entitlement",
      radar["summary"] == {"scanned": 5, "matching": 2, "returned": 2,
                           "min_tier": "narrow"}
      and radar["entitled"] is True)
check("per-row enrichment_used flags which cards used enrichment lines",
      radar["opportunities"][0]["enrichment_used"] is True
      and radar["opportunities"][1]["enrichment_used"] is False)
check("every served row cleared its narrowing requirements and carries "
      "human-readable reasons",
      all(o["requirements"]["meets_narrowing_requirements"]
          and o["opportunity"]
          and all(s["detail"] for s in o["narrowness"]["signals"])
          for o in radar["opportunities"]))
check("the honesty layer rides every response: field narrowness, NEVER a "
      "win probability, no model",
      any("NEVER a win probability" in c for c in radar["caveats"])
      and "never who wins" in radar["semantics"]
      and len(radar["caveats"]) == 4)

# NOTE: load_endpoint installs fresh _app_stub modules into sys.modules,
# and endpoints import them lazily at CALL time - so every call on an
# endpoint happens before the next load_endpoint.
wide_radar = endpoint.get_low_competition_tenders(min_tier="wide", limit=2)
check("min_tier widens the filter and limit caps deterministically "
      "(narrowest first)",
      [o["slug"] for o in wide_radar["opportunities"]] == ["vn-1", "n-1"]
      and wide_radar["summary"]["matching"] == 3
      and wide_radar["summary"]["returned"] == 2)
try:
    endpoint.get_low_competition_tenders(min_tier="tiny")
    bad_tier_refused = False
except Exception as exc:
    bad_tier_refused = "narrowness tier" in str(exc)
check("an unknown min_tier is refused with a friendly message", bad_tier_refused)

non_entitled = load_endpoint(build_frappe(), entitled=False)
radar_ne = non_entitled.get_low_competition_tenders()
check("non-entitled caller: enrichment lines never leak into the scoring - "
      "vn-1 stays wide on its advert surface and only n-1 is served",
      [o["slug"] for o in radar_ne["opportunities"]] == ["n-1"]
      and radar_ne["entitled"] is False)

guest_ep = load_endpoint(build_frappe(user="Guest"))
try:
    guest_ep.get_low_competition_tenders()
    guest_blocked = False
except PermissionError:
    guest_blocked = True
check("guests are refused (login required, same doctrine as the "
      "suitability and radar endpoints)", guest_blocked)

no_profile_ep = load_endpoint(build_frappe(profile_exists=False))
try:
    no_profile_ep.get_low_competition_tenders()
    profile_prompted = False
except Exception as exc:
    profile_prompted = "business profile" in str(exc).lower()
check("a caller without a Tender Business Profile gets the friendly "
      "set-up-your-profile error", profile_prompted)

# --------------------------------------------------------------------------
print()
passed = sum(1 for _, ok in checks if ok)
print(f"{passed}/{len(checks)} checks passed")
sys.exit(0 if passed == len(checks) else 1)
