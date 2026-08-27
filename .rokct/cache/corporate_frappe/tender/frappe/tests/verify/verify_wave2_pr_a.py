"""Standalone wave-2 PR-A verification (F-01 overlay regime, F-05 sectioned
functionality, F-09 checklist/submission_gate standalone imports).

Loads the real modules directly (frappe stubbed), execs generate_bid_pack.py
with the composer placeholder substituted so load_regime/build_bid_context run
against fake regime docs, and proves:

(a) an RNM-shaped MBD+CIDB bid yields the union form set (base-wins dedupe)
    in ONE combined RNM-shaped pack, with both regimes' rules firing;
(b) a bid WITHOUT an overlay is byte-identical to the pre-change behaviour
    for its form list, its applicable rule set, and its rendered pack HTML;
(c) Sectioned mode: a two-section bid fails naming the failing section and
    passes when both clear; Single mode reproduces wave-1 byte-identically;
    "No scored functionality" silences the gate;
(d) checklist.py and submission_gate.py import and run standalone by path.

Exit code 0 = all checks pass."""

import importlib.util
import json
import os
import sys
import types

# O-05: in-tree suite runs must leave no __pycache__ litter under src/
sys.dont_write_bytecode = True
from datetime import date

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SRC = os.path.join(REPO, "tender/frappe/src/control")
FIXTURES = os.path.join(REPO, "tender/frappe/fixtures")

# ---- frappe stub ----
frappe_stub = types.ModuleType("frappe")
utils_stub = types.ModuleType("frappe.utils")
utils_stub.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
utils_stub.flt = lambda v, precision=None: float(v) if v not in (None, "") else 0.0
utils_stub.nowdate = lambda: "2026-08-20"


def _getdate(value=None):
    if value in (None, ""):
        return date(2026, 8, 20)
    if isinstance(value, date):
        return value
    parts = str(value).split(" ")[0].split("-")
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


utils_stub.getdate = _getdate
frappe_stub.utils = utils_stub


def _throw(msg, *a, **k):
    raise Exception(msg)


frappe_stub.throw = _throw
frappe_stub.whitelist = lambda *a, **k: (lambda f: f)
frappe_stub.get_all = lambda *a, **k: []
frappe_stub.db = types.SimpleNamespace(
    get_value=lambda *a, **k: None, exists=lambda *a, **k: False,
    get_single_value=lambda *a, **k: 0,
)
sys.modules["frappe"] = frappe_stub
sys.modules["frappe.utils"] = utils_stub


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rules = load_module("t_rules", os.path.join(SRC, "compliance/rules.py"))
scoring = load_module("t_scoring", os.path.join(SRC, "compliance/scoring.py"))
pack_builder = load_module("t_pack_builder", os.path.join(SRC, "pack_builder.py"))

with open(os.path.join(FIXTURES, "tender_compliance_rules.json"), encoding="utf-8") as f:
    ALL_RULES = json.load(f)
RULES = {r["rule_code"]: r for r in ALL_RULES}
with open(os.path.join(FIXTURES, "tender_form_regimes.json"), encoding="utf-8") as f:
    REGIME_FIXTURES = {r["regime_code"]: r for r in json.load(f)}
with open(os.path.join(FIXTURES, "tender_form_templates.json"), encoding="utf-8") as f:
    TEMPLATES = {t["template_code"]: t for t in json.load(f)}

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


# ---- exec generate_bid_pack.py with the composer placeholder substituted ----
# The literal {app_name} placeholder is a parse error; substituting a stub
# package name lets the REAL merge/context code run under the frappe stub.
entitlement_stub = types.ModuleType("_app_stub.tender.control.api.tenders.tender_entitlement")
entitlement_stub.find_tender_by_slug = lambda slug: None
entitlement_stub.get_owned_bid = lambda bid: None
for mod_name in (
    "_app_stub", "_app_stub.tender", "_app_stub.tender.control",
    "_app_stub.tender.control.api", "_app_stub.tender.control.api.tenders",
):
    sys.modules.setdefault(mod_name, types.ModuleType(mod_name))
sys.modules["_app_stub.tender.control.api.tenders.tender_entitlement"] = entitlement_stub

with open(os.path.join(SRC, "api/tenders/generate_bid_pack.py"), encoding="utf-8") as f:
    gbp_source = f.read().replace("{app_name}", "_app_stub")
gbp = types.ModuleType("t_generate_bid_pack")
gbp.__file__ = os.path.join(SRC, "api/tenders/generate_bid_pack.py")
exec(compile(gbp_source, gbp.__file__, "exec"), gbp.__dict__)


class FakeRow:
    def __init__(self, data):
        self.__dict__.update(data)


class FakeRegimeDoc:
    def __init__(self, fixture):
        self.regime_code = fixture["regime_code"]
        self.regime_name = fixture["regime_name"]
        self.forms = [FakeRow(row) for row in fixture["forms"]]


def fake_get_doc(doctype, name):
    assert doctype == "Tender Form Regime", doctype
    return FakeRegimeDoc(name if isinstance(name, dict) else REGIME_FIXTURES[name])


frappe_stub.get_doc = fake_get_doc


class FakeBid(dict):
    def __getattr__(self, key):
        return self.get(key)


print("== (a) F-01: RNM-shaped MBD+CIDB bid -> ONE combined pack, union form set ==")
rnm_bid = FakeBid(
    regime="MBD", overlay_regime="CIDB", tender_slug="8-2-rnm0614",
    tender_title="Construction of Mgodlwa Bridge in Ward 8",
    institution="Ray Nkonyeni Local Municipality", estimated_value=42500000,
)
merged = gbp.load_regime(rnm_bid)
check("merged regime_code is MBD+CIDB", merged["regime_code"] == "MBD+CIDB")
check("merged carries base/overlay codes for the manifest",
      merged.get("base_regime_code") == "MBD" and merged.get("overlay_regime_code") == "CIDB")
check("merged regime_name joins both names",
      merged["regime_name"] == REGIME_FIXTURES["MBD"]["regime_name"] + " + " + REGIME_FIXTURES["CIDB"]["regime_name"])
merged_codes = [f["form_code"] for f in merged["forms"]]
check("form index has the MBD spread (MBD4/5/8/9/6.1)",
      all(c in merged_codes for c in ("MBD4", "MBD5", "MBD8", "MBD9", "MBD6.1")))
check("form index has the CIDB overlay (C1.1/T2.x/HS-PLAN)",
      all(c in merged_codes for c in ("C1.1", "T2.x", "HS-PLAN")))
check("exactly one row per form_code (dedupe)", len(merged_codes) == len(set(merged_codes)))
check("stable order: base rows first, overlay appended",
      merged_codes[: len(REGIME_FIXTURES["MBD"]["forms"])]
      == [f["form_code"] for f in REGIME_FIXTURES["MBD"]["forms"]])
# base-wins dedupe on a synthetic overlap (fixture MBD/CIDB share no code)
overlap_overlay = {
    "regime_code": "XOVL", "regime_name": "Overlap Overlay",
    "forms": [{"form_code": "POPIA", "form_name": "OVERLAY VERSION - must lose",
               "mandatory": 1, "kill_note": "overlay note"},
              {"form_code": "XTRA-1", "form_name": "Extra overlay form", "mandatory": 1, "kill_note": ""}],
}
merged2 = gbp.load_regime(FakeBid(regime="MBD", overlay_regime=overlap_overlay))
popia_rows = [f for f in merged2["forms"] if f["form_code"] == "POPIA"]
check("base wins the dedupe on a shared form_code",
      len(popia_rows) == 1 and popia_rows[0]["form_name"] != "OVERLAY VERSION - must lose")
check("non-overlapping overlay row still appended", "XTRA-1" in [f["form_code"] for f in merged2["forms"]])

# rules: both regimes' rules fire on the merged bid context
rnm_ctx = rules.bid_context(rnm_bid)
check("bid_context carries overlay_regime", rnm_ctx["overlay_regime"] == "CIDB")
check("bid_context regime_codes joins both codes", rnm_ctx["regime_codes"] == "MBD CIDB")
check("bid_context regime stays the single base code", rnm_ctx["regime"] == "MBD")
check("KILL-21 (regimes fence 'CIDB') attaches via the regime set",
      rules.rule_applies(RULES["KILL-21"], rnm_ctx))
check("GATE-CIDB attaches on the RNM bridge bid", rules.rule_applies(RULES["GATE-CIDB"], rnm_ctx))
check("GATE-COIDA attaches on the RNM bridge bid", rules.rule_applies(RULES["GATE-COIDA"], rnm_ctx))
check("MBD-fenced KILL-19 still attaches (base regime in the set)",
      rules.rule_applies(RULES["KILL-19"], rnm_ctx))
check("regime_codes_matches condition fires on EITHER code",
      rules.condition_matches({"regime_codes_matches": ["cidb"]}, rnm_ctx)
      and rules.condition_matches({"regime_codes_matches": ["mbd"]}, rnm_ctx))

# one combined RNM-shaped pack out of pack_builder
bid_ctx = gbp.build_bid_context(rnm_bid)
check("build_bid_context exposes overlay_regime", bid_ctx["overlay_regime"] == "CIDB")
profile = {"trading_name": "Sinyage Trading", "registered_name": "Sinyage Trading (Pty) Ltd",
           "authorized_signatory_capacity": "Director"}
pack = pack_builder.build_pack(merged, TEMPLATES, profile, bid_ctx, [])
html = pack_builder.render_pack_html(pack, bid_ctx)
pack_codes = [f["form_code"] for f in pack["forms"]]
check("combined pack renders every union form",
      pack_codes == merged_codes and pack["manifest"]["form_count"] == len(merged_codes))
check("combined pack shows the joined regime on the cover", "MBD+CIDB" in html)
check("both pricing worksheets render (MBD3.x AND T2.x-PRICE)",
      "MBD3.x" in pack_codes and "T2.x-PRICE" in pack_codes)
check("one self-contained HTML document", html.lower().count("<!doctype") == 1)

print("== (b) no-overlay bid: byte-identical form list, rule set and pack HTML ==")
plain_bid = FakeBid(regime="MBD", tender_slug="cor-01-2026-27",
                    tender_title="Hosting of a Website", institution="Theewaterskloof Municipality")
plain_regime = gbp.load_regime(plain_bid)


def old_load_regime(fixture):  # the pre-change output, reconstructed verbatim
    return {
        "regime_code": fixture["regime_code"],
        "regime_name": fixture["regime_name"],
        "forms": [
            {"form_code": r["form_code"], "form_name": r["form_name"],
             "mandatory": r["mandatory"], "kill_note": r["kill_note"]}
            for r in fixture["forms"]
        ],
    }


check("load_regime without overlay == pre-change dict (no extra keys)",
      plain_regime == old_load_regime(REGIME_FIXTURES["MBD"]))


def old_rule_applies(rule, context):  # pre-change fence, reconstructed verbatim
    if not utils_stub.cint(rule.get("enabled")):
        return False
    regimes = rules.parse_regimes(rule.get("regimes"))
    if regimes:
        if (context.get("regime") or "").upper() not in regimes:
            return False
    if rule.get("scope") == "Universal":
        return True
    condition = rules.parse_json_field(rule.get("trigger_condition"))
    if condition:
        return rules.condition_matches(condition, context)
    return bool(regimes)


sample_bids = [
    {"regime": "MBD", "estimated_value": 42500000, "institution": "Ray Nkonyeni Local Municipality",
     "tender_title": "Construction of Mgodlwa Bridge in Ward 8"},
    {"regime": "SBD", "institution": "Department of Forestry, Fisheries and the Environment",
     "tender_title": "Determination of the state of forests in South Africa"},
    {"regime": "SBD", "estimated_value": 168000000, "institution": "Vaal Central Water",
     "tender_title": "Total Security Solution: physical guarding services and perimeter security fencing"},
    {"regime": "MBD", "estimated_value": 2179056, "institution": "Theewaterskloof Municipality",
     "tender_title": "Support, Maintenance, Development and Hosting of a Website"},
    {"regime": "MBD", "estimated_value": 2573750, "institution": "Musina Local Municipality",
     "tender_title": "Interactive Cloud-Based Customer Service Ticketing and Helpdesk Management System"},
    {"regime": "CIDB", "estimated_value": 9000000, "institution": "SANRAL",
     "tender_title": "Routine road maintenance"},
    {"regime": None},
]
identical = True
for bid in sample_bids:
    new_ctx = rules.bid_context(bid)
    old_ctx = {k: v for k, v in new_ctx.items() if k not in ("overlay_regime", "regime_codes")}
    new_set = {r["rule_code"] for r in ALL_RULES if rules.rule_applies(r, new_ctx)}
    old_set = {r["rule_code"] for r in ALL_RULES if old_rule_applies(r, old_ctx)}
    if new_set != old_set:
        identical = False
        print("   MISMATCH", bid.get("institution"), new_set ^ old_set)
check("applicable rule set identical to pre-change for all 7 no-overlay contexts (56 rules)", identical)
plain_ctx = gbp.build_bid_context(plain_bid)
old_style_ctx = {k: v for k, v in plain_ctx.items() if k != "overlay_regime"}
pack_new = pack_builder.build_pack(plain_regime, TEMPLATES, profile, plain_ctx, [])
pack_old = pack_builder.build_pack(old_load_regime(REGIME_FIXTURES["MBD"]), TEMPLATES, profile, old_style_ctx, [])
check("no-overlay pack HTML byte-identical to pre-change",
      pack_builder.render_pack_html(pack_new, plain_ctx) == pack_builder.render_pack_html(pack_old, old_style_ctx))

print("== (c) F-05: sectioned / single / no-scored functionality ==")
gate = load_module("t_submission_gate", os.path.join(SRC, "compliance/submission_gate.py"))
vcw_sections = [
    {"section_label": "Section 1 - Guarding services", "max_points": 335,
     "threshold_pct": 75, "self_score_points": 290},
    {"section_label": "Section 2 - Fencing and related works", "max_points": 165,
     "threshold_pct": 75, "self_score_points": 110},
]
vcw_bid = FakeBid(functionality_mode="Sectioned", functionality_sections=vcw_sections,
                  user="u@example.com", closing_date="2026-09-30")
failures = gate.validate_submission_readiness(vcw_bid)
check("DFFE/VCW-shaped two-section bid FAILS when one section is under threshold", len(failures) == 1)
check("gate names the failing section by label",
      failures and "Section 2 - Fencing and related works" in failures[0])
check("gate does not name the passing section",
      not any("Section 1" in f for f in failures))
vcw_sections[1]["self_score_points"] = 130  # 78.8% >= 75%
check("two-section bid PASSES when both sections clear",
      gate.validate_submission_readiness(vcw_bid) == [])
check("Sectioned mode ignores the single-pair fields entirely",
      gate.validate_submission_readiness(FakeBid(
          functionality_mode="Sectioned", functionality_sections=vcw_sections,
          functionality_threshold=99, functionality_self_score=1)) == [])
# scoring helpers directly (DFFE single 75% rubric + RNM 42/70 via sections)
check("DFFE 100-pt rubric row at 80/100 vs 75% passes",
      scoring.passes_functionality_sections([{"section_label": "DFFE rubric", "max_points": 100,
                                              "threshold_pct": 75, "self_score_points": 80}]))
check("RNM METHOD 4 41/70 vs 60% fails, 42/70 passes",
      scoring.failing_functionality_sections([{"section_label": "M4", "max_points": 70,
                                               "threshold_pct": 60, "self_score_points": 41}]) == ["M4"]
      and scoring.passes_functionality_sections([{"section_label": "M4", "max_points": 70,
                                                  "threshold_pct": 60, "self_score_points": 42}]))
check("informational row (no threshold) and malformed row (no max) never fail",
      scoring.passes_functionality_sections([
          {"section_label": "Info", "max_points": 100, "self_score_points": 0},
          {"section_label": "Broken", "max_points": 0, "threshold_pct": 75}]))
# Single mode reproduces wave-1 behaviour byte-identically
LEGACY_MSG = ("Functionality self-score is below the pack's threshold - "
              "functionality is an elimination gate before price and preference.")
for mode in (None, "", "Single threshold"):
    f_fail = gate.validate_submission_readiness(FakeBid(
        functionality_mode=mode, functionality_threshold=70, functionality_self_score=65))
    f_pass = gate.validate_submission_readiness(FakeBid(
        functionality_mode=mode, functionality_threshold=70, functionality_self_score=75))
    check(f"mode={mode!r}: single-pair gate fires the exact legacy message",
          f_fail == [LEGACY_MSG])
    check(f"mode={mode!r}: single-pair gate silent when the score clears", f_pass == [])
check("legacy no-threshold bid still passes (blank mode)",
      gate.validate_submission_readiness(FakeBid()) == [])
# Musina negative case: gate skipped entirely, even with stale pair values
check("'No scored functionality' silences the gate (Musina case)",
      gate.validate_submission_readiness(FakeBid(
          functionality_mode="No scored functionality",
          functionality_threshold=70, functionality_self_score=None)) == [])

print("== (d) F-09: checklist.py and submission_gate.py run standalone by path ==")
checklist = load_module("t_checklist", os.path.join(SRC, "compliance/checklist.py"))
check("submission_gate imports standalone by file path", hasattr(gate, "validate_submission_readiness"))
check("checklist imports standalone by file path", hasattr(checklist, "compliance_checklist_rows"))
# run checklist assembly against the REAL fixture rules through the stub
frappe_stub.get_all = lambda doctype, filters=None, fields=None, **k: [
    dict(r, name=r["rule_code"]) for r in ALL_RULES
    if doctype == "Tender Compliance Rule" and r.get("enabled")
]
musina_bid = FakeBid(regime="MBD", estimated_value=2573750,
                     institution="Musina Local Municipality",
                     tender_title="Cloud-Based Helpdesk Management System", checklist=[])
rows = checklist.compliance_checklist_rows(musina_bid)
row_codes = {r["rule_code"] for r in rows}
check("checklist assembles rows from fixture rules standalone",
      len(rows) > 10 and {"GATE-CSD", "GATE-TCS", "KILL-19"} <= row_codes)
check("checklist rows carry text/severity/status shape",
      all(r["task_text"] and r["severity"] and r["status"] == "Open" for r in rows))


class AppendableBid(FakeBid):
    def append(self, table, row):
        self.setdefault(table, []).append(row)


bid2 = AppendableBid(musina_bid)
bid2["checklist"] = []
appended_first = checklist.sync_compliance_checklist(bid2)
bid2["checklist"] = [FakeBid(rule_code=r["rule_code"]) for r in rows]
check("sync_compliance_checklist appends then is idempotent standalone",
      appended_first == len(rows) and checklist.sync_compliance_checklist(bid2) == 0)
gate_failures2 = gate.validate_submission_readiness(FakeBid(
    regime="MBD", user="u@example.com",
    checklist=[FakeBid(severity="Fatal", status="Open", task_text="CSD registration", rule_code="GATE-CSD")]))
check("gate consumes fixture rules standalone (fatal checklist row reported)",
      any("GATE-CSD" in f for f in gate_failures2))
for path in ("compliance/checklist.py", "compliance/submission_gate.py"):
    with open(os.path.join(SRC, path), encoding="utf-8") as f:
        src_text = f.read()
    check(f"{path} carries no {{app_name}} placeholder or ignore marker",
          "{app_name}" not in src_text and "compliance-ignore-file" not in src_text)

print("== regression: fixtures untouched, rule counts hold ==")
counts = {}
for r in ALL_RULES:
    counts[r["rule_class"]] = counts.get(r["rule_class"], 0) + 1
# wave-2 PR-B adds PRICE-MULTIYEAR-ESC (F-06): Pricing Rule 2 -> 3, total 55 -> 56
# wave-3 adds GATE-PACK-COLLECT (F-08): Registration Gate 19 -> 20, total 56 -> 57
# wave-2 PR-C adds 12 QUIRK-* Buyer Quirk rules (F-11): new class, total 57 -> 69
check("rule counts: 20/25/7/3/2/12, total 69",
      counts == {"Registration Gate": 20, "Disqualification Cause": 25, "Scoring Rule": 7,
                 "Pricing Rule": 3, "Form Rule": 2, "Buyer Quirk": 12} and len(ALL_RULES) == 69)
check("every regime form still has a template",
      not [(r["regime_code"], f["form_code"]) for r in REGIME_FIXTURES.values()
           for f in r["forms"] if f["form_code"] not in TEMPLATES])

failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL WAVE-2 PR-A CHECKS PASSED")
