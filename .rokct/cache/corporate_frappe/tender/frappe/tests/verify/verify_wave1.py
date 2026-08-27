"""Standalone wave-1 verification: imports rules.py / preference_frameworks.py /
pack_builder.py directly (frappe stubbed), replays the documented sample-bid
contexts against the updated fixtures, and generates an MBD-regime pack to
confirm the pricing schedule renders. Exit code 0 = all checks pass."""

import importlib.util
import json
import os
import tempfile
import sys
import types

# O-05: in-tree suite runs must leave no __pycache__ litter under src/
sys.dont_write_bytecode = True

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SRC = os.path.join(REPO, "tender/frappe/src/control")
FIXTURES = os.path.join(REPO, "tender/frappe/fixtures")
# rendered pack samples are run OUTPUT, not fixtures - keep them out of the
# tree (a temp dir), so re-running the suite never dirties the repo
OUT = tempfile.mkdtemp(prefix="verify_wave1_")

# ---- frappe stub (rules.py imports frappe + frappe.utils.cint/flt) ----
frappe_stub = types.ModuleType("frappe")
utils_stub = types.ModuleType("frappe.utils")
utils_stub.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
utils_stub.flt = lambda v, precision=None: float(v) if v not in (None, "") else 0.0
frappe_stub.utils = utils_stub
sys.modules.setdefault("frappe", frappe_stub)
sys.modules.setdefault("frappe.utils", utils_stub)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rules = load_module("t_rules", os.path.join(SRC, "compliance/rules.py"))
prefs = load_module("t_prefs", os.path.join(SRC, "compliance/preference_frameworks.py"))
pack_builder = load_module("t_pack_builder", os.path.join(SRC, "pack_builder.py"))

with open(os.path.join(FIXTURES, "tender_compliance_rules.json"), encoding="utf-8") as f:
    RULES = {r["rule_code"]: r for r in json.load(f)}
with open(os.path.join(FIXTURES, "tender_form_regimes.json"), encoding="utf-8") as f:
    REGIMES = {r["regime_code"]: r for r in json.load(f)}
with open(os.path.join(FIXTURES, "tender_form_templates.json"), encoding="utf-8") as f:
    TEMPLATES = {t["template_code"]: t for t in json.load(f)}

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


applies = rules.rule_applies

# ---- the five documented sample-bid contexts ----
rnm = {"regime": "MBD", "estimated_value": 42500000,
       "institution": "Ray Nkonyeni Local Municipality",
       "subject": "Construction of Mgodlwa Bridge in Ward 8"}
dffe = {"regime": "SBD",
        "institution": "Department of Forestry, Fisheries and the Environment",
        "subject": "Determination of the state of forests in South Africa"}
vcw = {"regime": "SBD", "estimated_value": 168000000,
       "institution": "Vaal Central Water",
       "subject": "Total Security Solution: physical guarding services; supply, "
                  "installation and maintenance incl. perimeter security fencing and related works"}
twk = {"regime": "MBD", "estimated_value": 2179056,
       "institution": "Theewaterskloof Municipality",
       "subject": "Support, Maintenance, Development and Hosting of a Website "
                  "for the Theewaterskloof Municipality"}
musina = {"regime": "MBD", "estimated_value": 2573750,
          "institution": "Musina Local Municipality",
          "subject": "Interactive Cloud-Based Customer Service Ticketing and "
                     "Helpdesk Management System"}

print("== (a) widened rules: documented buyers/subjects fire, original targets keep firing ==")
check("GATE-SECTOR fires on VCW security subject", applies(RULES["GATE-SECTOR"], vcw))
check("GATE-SECTOR keeps Dept of Tourism", applies(RULES["GATE-SECTOR"], {"institution": "Department of Tourism"}))
check("GATE-SECTOR silent on TWK website", not applies(RULES["GATE-SECTOR"], twk))
check("GATE-SECTOR silent on Mogale (v3 negative)", not applies(RULES["GATE-SECTOR"], {"institution": "Mogale City Local Municipality"}))
check("GATE-INSURANCE fires on VCW", applies(RULES["GATE-INSURANCE"], vcw))
check("GATE-INSURANCE keeps SANRAL", applies(RULES["GATE-INSURANCE"], {"institution": "SA National Roads Agency SOC Ltd (SANRAL)"}))
check("GATE-INSURANCE keeps Cape Town", applies(RULES["GATE-INSURANCE"], {"institution": "City of Cape Town Metropolitan Municipality"}))
check("GATE-INSURANCE silent on Musina", not applies(RULES["GATE-INSURANCE"], musina))
check("GATE-POPIA fires on Musina helpdesk/ticketing subject", applies(RULES["GATE-POPIA"], musina))
check("GATE-POPIA fires on TWK website-hosting subject", applies(RULES["GATE-POPIA"], twk))
check("GATE-POPIA keeps Transnet", applies(RULES["GATE-POPIA"], {"institution": "TRANSNET SOC LTD"}))
check("GATE-POPIA keeps SANRAL", applies(RULES["GATE-POPIA"], {"institution": "SANRAL"}))
check("GATE-POPIA silent on RNM bridge", not applies(RULES["GATE-POPIA"], rnm))
check("GATE-POPIA silent on Eskom (v3 negative)", not applies(RULES["GATE-POPIA"], {"institution": "Eskom Holdings SOC Ltd"}))

print("== (b) regime rescoping: GATE-RATES / GATE-CIDB / GATE-COIDA ==")
check("GATE-RATES still fires on MBD (RNM)", applies(RULES["GATE-RATES"], rnm))
check("GATE-RATES still fires on MBD (TWK)", applies(RULES["GATE-RATES"], twk))
check("GATE-RATES still fires on MBD (Musina)", applies(RULES["GATE-RATES"], musina))
check("GATE-RATES now fires on VCW (SBD water board)", applies(RULES["GATE-RATES"], vcw))
check("GATE-RATES silent on DFFE (SBD national dept)", not applies(RULES["GATE-RATES"], dffe))
check("GATE-RATES silent on regime-less bid", not applies(RULES["GATE-RATES"], {"regime": None}))
for code in ("GATE-CIDB", "GATE-COIDA"):
    check(f"{code} still fires on CIDB regime", applies(RULES[code], {"regime": "CIDB"}))
    check(f"{code} now fires on RNM bridge under MBD", applies(RULES[code], rnm))
    check(f"{code} now fires on VCW works/site services", applies(RULES[code], vcw))
    check(f"{code} silent on TWK website", not applies(RULES[code], twk))
    check(f"{code} silent on DFFE", not applies(RULES[code], dffe))
check("GATE-MBD5 unchanged: ON at R42.5m", applies(RULES["GATE-MBD5"], rnm))
check("GATE-MBD5 unchanged: OFF at R2.57m", not applies(RULES["GATE-MBD5"], musina))
check("KILL-19 unchanged: MBD only", applies(RULES["KILL-19"], musina) and not applies(RULES["KILL-19"], dffe))

print("== any_of operator semantics ==")
cm = rules.condition_matches
check("any_of OR works", cm({"any_of": [{"regime_matches": ["mbd"]}, {"institution_matches": ["vaal central water"]}]}, {"regime": "SBD", "institution": "Vaal Central Water"}))
check("any_of empty never matches", not cm({"any_of": []}, {"regime": "MBD"}))
check("any_of non-list never matches", not cm({"any_of": "mbd"}, {"regime": "MBD"}))
check("any_of [{}] never matches", not cm({"any_of": [{}]}, {"regime": "MBD"}))
check("any_of AND-composes with siblings", cm({"any_of": [{"regime_matches": ["mbd"]}], "estimated_value_over": 1}, {"regime": "MBD", "estimated_value": 2}) and not cm({"any_of": [{"regime_matches": ["mbd"]}], "estimated_value_over": 5}, {"regime": "MBD", "estimated_value": 2}))
ctx = rules.bid_context({"regime": "MBD", "tender_title": "Hosting of a Website"})
check("bid_context exposes subject from tender_title", ctx["subject"] == "Hosting of a Website")
check("bid_context subject None when no title", rules.bid_context({"regime": "MBD"})["subject"] is None)

print("== (c) preference-framework conflict lint (F-12) ==")
musina_texts = [
    "MBD 6.1 - Preference Points Claim Form (PPR 2022, specific goals)",
    "Form C - Declaration of Interest: HDI Equity Ownership ...% = ... Points out of 20 (<R1 000 000)",
    "Form D - Certificate of Preference for Local Content and SABS mark (Section 35, Local Government Ordinance, 1939)",
]
detected = prefs.detect_preference_frameworks(musina_texts)
check("Musina-shaped pack detects 3 frameworks", len(detected) == 3)
warning = prefs.preference_framework_conflict(musina_texts, operative_system="80/20")
check("conflict warning fires", warning is not None and "conflicting preference frameworks" in warning and "80/20" in warning)
normal_texts = [
    "MBD 6.1 - Preference Points Claim Form (specific goals)",
    "MBD 6.2 - Declaration of Local Production and Content (per SATS 1286)",
]
check("normal single-framework pack stays silent", prefs.preference_framework_conflict(normal_texts) is None)
check("empty input stays silent", prefs.preference_framework_conflict([]) is None and prefs.preference_framework_conflict(None) is None)
params = json.loads(RULES["WARN-PREF-CONFLICT"]["params"])
check("fixture rule ships the same patterns as data",
      prefs.preference_framework_conflict(musina_texts, framework_patterns=params["framework_patterns"]) is not None)
check("WARN-PREF-CONFLICT never auto-applies", not applies(RULES["WARN-PREF-CONFLICT"], {"regime": "MBD", "subject": "anything"}))

print("== F-10: MBD/CIDB packs render the pricing schedule ==")
profile = {"trading_name": "Sinyage Trading", "registered_name": "Sinyage Trading (Pty) Ltd",
           "authorized_signatory_capacity": "Director"}
bid_ctx = {
    "bid_name": "BID-00042", "tender_slug": "cor-01-2026-27",
    "tender_title": "Support, Maintenance, Development and Hosting of a Website",
    "institution": "Theewaterskloof Municipality", "closing_date": "2026-09-18",
    "tender_number": "COR 01/2026/27", "ocid": "ocds-9t57fa-165555",
    "estimated_value": "2179056", "preference_system": "80/20", "regime": "MBD",
    "generated_on": "2026-08-20", "quotation": "SAL-QTN-0007",
    "pricing_lines": [
        {"item": "WEB-01", "description": "Website maintenance - Year 1", "qty": 12,
         "uom": "Month", "rate": 36317.60, "amount": 435811.20},
        {"item": "WEB-02", "description": "Hosting - Year 1", "qty": 12,
         "uom": "Month", "rate": 5000.00, "amount": 60000.00},
    ],
    "pricing_total": "495811.20",
}
for regime_code, out_name in (("MBD", "pack-mbd.html"), ("CIDB", "pack-cidb.html")):
    pack = pack_builder.build_pack(REGIMES[regime_code], TEMPLATES, profile, bid_ctx, [])
    html = pack_builder.render_pack_html(pack, bid_ctx)
    with open(os.path.join(OUT, out_name), "w", encoding="utf-8") as f:
        f.write(html)
    form_code = "MBD3.x" if regime_code == "MBD" else "T2.x-PRICE"
    form = next(fm for fm in pack["forms"] if fm["form_code"] == form_code)
    check(f"{regime_code} pack contains {form_code} with a template", form["has_template"])
    check(f"{regime_code} pack renders the pricing line items", "WEB-01" in html and "Website maintenance - Year 1" in html)
    check(f"{regime_code} pack renders the pricing table columns", "Rate (R)" in html and "Amount (R)" in html)
    check(f"{regime_code} pack renders the quotation total", "495811.2" in html)
    check(f"{regime_code} pack has no conflict warning (single framework)",
          not any("conflicting preference frameworks" in w for w in pack["manifest"]["warnings"]))
# regression: SBD pack still renders pricing_lines on SBD3.x
sbd_pack = pack_builder.build_pack(REGIMES["SBD"], TEMPLATES, profile, dict(bid_ctx, regime="SBD"), [])
sbd_html = pack_builder.render_pack_html(sbd_pack, bid_ctx)
check("SBD pack still renders pricing lines (SBD3.x)", "WEB-01" in sbd_html)
# F-12 wiring: a conflicted form set produces the manifest warning
conflicted_regime = {
    "regime_code": "MBD", "regime_name": "Municipal (MBD forms)",
    "forms": [
        {"form_code": "MBD6.1", "form_name": "Preference Points Claim Form (PPR 2022 specific goals)", "mandatory": 1, "kill_note": ""},
        {"form_code": "FORM-C", "form_name": "Form C - HDI Equity Ownership claim (Points out of 20)", "mandatory": 1, "kill_note": "Non-completion forfeits the preference."},
        {"form_code": "FORM-D", "form_name": "Form D - Local Content / SABS mark (Local Government Ordinance, 1939)", "mandatory": 1, "kill_note": "Non-completion forfeits the preference."},
    ],
}
conflicted_pack = pack_builder.build_pack(conflicted_regime, {}, profile, bid_ctx, [])
check("conflicted pack manifest carries the F-12 warning",
      any("conflicting preference frameworks" in w for w in conflicted_pack["manifest"]["warnings"]))

print("== every regime form still has a template; fixture shapes hold ==")
missing = [(r["regime_code"], f["form_code"]) for r in REGIMES.values() for f in r["forms"] if f["form_code"] not in TEMPLATES]
check("every regime form has a template", not missing)
counts = {}
with open(os.path.join(FIXTURES, "tender_compliance_rules.json"), encoding="utf-8") as f:
    all_rules = json.load(f)
for r in all_rules:
    counts[r["rule_class"]] = counts.get(r["rule_class"], 0) + 1
# wave-2 PR-B adds PRICE-MULTIYEAR-ESC (F-06): Pricing Rule 2 -> 3, total 55 -> 56
# wave-3 adds GATE-PACK-COLLECT (F-08): Registration Gate 19 -> 20, total 56 -> 57
# wave-2 PR-C adds 12 QUIRK-* Buyer Quirk rules (F-11): new class, total 57 -> 69
check("rule counts: 20/25/7/3/2/12, total 69",
      counts == {"Registration Gate": 20, "Disqualification Cause": 25, "Scoring Rule": 7,
                 "Pricing Rule": 3, "Form Rule": 2, "Buyer Quirk": 12} and len(all_rules) == 69)
for r in all_rules:
    if r.get("trigger_condition"):
        assert isinstance(json.loads(r["trigger_condition"]), dict), r["rule_code"]
    if r.get("params"):
        json.loads(r["params"])
check("all trigger_condition / params JSON parse", True)

print("== plan #1 regression lint: no doubled braces in f-string log lines ==")
# A doubled brace inside an f-string prints the literal text (e.g. the
# 13 endpoints that logged "trace_id={trace_id}" verbatim). The composer
# only ever substitutes the literal {app_name}, so no source line needs
# brace-escaping - any surviving "{{" in an f-string print is a bug.
offenders = []
for root, _dirs, files in os.walk(SRC):
    for fname in files:
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if "print(f" in line and "{{" in line:
                    offenders.append(f"{os.path.relpath(fpath, SRC)}:{lineno}")
check("no f-string log line doubles its braces", not offenders)
if offenders:
    print("OFFENDERS:", offenders)

failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL WAVE-1 CHECKS PASSED")
