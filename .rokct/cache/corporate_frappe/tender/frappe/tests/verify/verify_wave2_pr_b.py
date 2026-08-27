"""Standalone wave-2 PR-B verification (F-06 multi-year term/pricing grid,
F-02 buyer-authored returnables, F-07 capability register + ICT-CAPABILITY).

Loads the real modules directly (frappe stubbed), execs generate_bid_pack.py
with the composer placeholder substituted, and proves:

(a) a Musina-shaped 36-month bid renders the official Year 1/2/3 grid
    (Once-Off / Monthly / Annual / unit-tariff columns) on SBD3.x, MBD3.x
    and T2.x-PRICE, the captured grid totals to the sample's R2,573,750.00,
    and the TWK 5-year shape renders 5 rows + the escalation column;
(b) a single-year bid's pack output is BYTE-IDENTICAL to the pre-change
    code + fixtures (baseline pulled from git), and the applicable rule set
    is unchanged for all sample contexts;
(c) custom returnables render as template-less worksheet pages in issued
    order, template_code rows resolve to real templates (incl.
    ICT-CAPABILITY), override/append/dedupe semantics hold, and the Musina
    legacy Forms C/D trip WARN-PREF-CONFLICT;
(d) profile capability items render as a table in the ICT-CAPABILITY page,
    and an empty register renders the amber profile gap;
(e) PRICE-MULTIYEAR-ESC fires only on multi-year contexts;
(f) Sectioned functionality with an EMPTY sections table produces the
    SECTIONED-NO-SECTIONS warning (visible on the pack cover) while still
    passing the gate; populated sections behave exactly as shipped in #37.

Baseline for (b): the committed verbatim snapshot of the pre-PR-B tree
(PR #37's merge commit 686850c) under data/pr_b_baseline_686850c/ - no
git history needed, so the suite runs on shallow clones (plan #2 of
tender/SDK-Assessment-2026-08-24.md). $PR_B_BASE_REF still overrides to
a git ref for ad-hoc comparisons; when git can serve 686850c the
snapshot is additionally drift-checked against it (SKIP when history is
shallow/absent). Exit code 0 = all checks pass."""

import importlib.util
import json
import os
import subprocess
import sys
import types

# O-05: in-tree suite runs must leave no __pycache__ litter under src/
sys.dont_write_bytecode = True
from datetime import date

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SRC = os.path.join(REPO, "tender/frappe/src/control")
FIXTURES = os.path.join(REPO, "tender/frappe/fixtures")
SCRATCH = os.path.dirname(os.path.abspath(__file__))

# ---- frappe stub (same shape as verify_wave2_pr_a.py) ----
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


def load_module_from_source(name, source, filename):
    module = types.ModuleType(name)
    module.__file__ = filename
    exec(compile(source, filename, "exec"), module.__dict__)
    return module


rules = load_module("t_rules", os.path.join(SRC, "compliance/rules.py"))
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
    gbp = load_module_from_source(
        "t_generate_bid_pack", f.read().replace("{app_name}", "_app_stub"),
        os.path.join(SRC, "api/tenders/generate_bid_pack.py"),
    )


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


PROFILE = {
    "trading_name": "Sinyage Trading",
    "registered_name": "Sinyage Trading (Pty) Ltd",
    "authorized_signatory_capacity": "Director",
}

print("== (a) F-06: Musina-shaped 36-month bid renders the Year 1/2/3 grid and totals ==")
# The Musina 18-2025/26 official-grid shape: Once-Off / Monthly / Annual per
# Year 1-3 plus a per-unit call tariff ("actual variable value dependent on
# call activity"); fixed-portion 3-year total R2,573,750.00.
MUSINA_PERIODS = [
    {"period_label": "Year 1", "once_off": 393750.0, "monthly": 41666.67,
     "annual_total": 893750.04, "unit_tariff": None, "unit_label": None,
     "escalation_applied_pct": None, "notes": "Implementation + licence + support"},
    {"period_label": "Year 2", "once_off": 0.0, "monthly": 69999.99,
     "annual_total": 839999.88, "unit_tariff": None, "unit_label": None,
     "escalation_applied_pct": None, "notes": None},
    {"period_label": "Year 3", "once_off": 0.0, "monthly": 70000.01,
     "annual_total": 840000.08, "unit_tariff": None, "unit_label": None,
     "escalation_applied_pct": None, "notes": None},
    {"period_label": "Per-unit call tariff", "once_off": None, "monthly": None,
     "annual_total": None, "unit_tariff": 85.0, "unit_label": "per logged call",
     "escalation_applied_pct": None,
     "notes": "Actual variable value dependent on call activity over the term"},
]
musina_bid = FakeBid(
    regime="MBD", tender_slug="musina-18-2025-26",
    tender_title="Interactive Cloud-Based Customer Service Ticketing and Helpdesk Management System",
    institution="Musina Local Municipality", estimated_value=2573750,
    contract_term_months=36, escalation_provision="None / firm prices",
    pricing_periods=[FakeBid(p) for p in MUSINA_PERIODS],
)
musina_ctx = gbp.build_bid_context(musina_bid)
check("build_bid_context carries the term/escalation fields",
      musina_ctx["contract_term_months"] == "36"
      and musina_ctx["escalation_provision"] == "None / firm prices")
check("build_bid_context serialises 4 pricing-period rows",
      isinstance(musina_ctx["pricing_periods"], list) and len(musina_ctx["pricing_periods"]) == 4)
year_rows = [p for p in musina_ctx["pricing_periods"] if p["annual_total"] is not None]
fixed_total = round(sum(p["annual_total"] for p in year_rows), 2)
check("captured grid totals to the Musina fixed-portion R2,573,750.00", fixed_total == 2573750.00)
check("grid template row present on SBD3.x, MBD3.x AND T2.x-PRICE",
      all(any(f["source_field"] == "pricing_periods" for f in TEMPLATES[c]["fields_table"])
          for c in ("SBD3.x", "MBD3.x", "T2.x-PRICE")))

musina_pack = pack_builder.build_pack(
    gbp.load_regime(musina_bid), TEMPLATES, PROFILE, musina_ctx, [])
musina_html = pack_builder.render_pack_html(musina_pack, musina_ctx)
check("MBD3.x page renders the Year 1/2/3 grid rows",
      all(s in musina_html for s in ("Year 1", "Year 2", "Year 3")))
check("grid renders the official columns (Once-Off/Monthly/Annual/Unit Tariff)",
      all(s in musina_html for s in ("Once-Off (R)", "Monthly (R)", "Annual Total (R)", "Unit Tariff (R)")))
check("per-unit call-tariff line renders with its unit label",
      "Per-unit call tariff" in musina_html and "per logged call" in musina_html)
check("grid cell values land in the page",
      "393750.0" in musina_html and "839999.88" in musina_html and "85.0" in musina_html)
mbd3x_form = next(f for f in musina_pack["forms"] if f["form_code"] == "MBD3.x")
check("grid row counts as a filled auto field on the pricing worksheet",
      "Multi-year pricing grid (per-period Once-Off / Monthly / Annual / unit-tariff columns)"
      not in mbd3x_form["missing_auto"] and mbd3x_form["auto_filled"] >= 4)

# same grid on an SBD-regime pack (SBD3.x)
sbd_bid = FakeBid(regime="SBD", tender_slug="sbd-multiyear", tender_title="Multi-year service",
                  institution="Department X", contract_term_months=36,
                  pricing_periods=[FakeBid(p) for p in MUSINA_PERIODS])
sbd_ctx = gbp.build_bid_context(sbd_bid)
sbd_html = pack_builder.render_pack_html(
    pack_builder.build_pack(gbp.load_regime(sbd_bid), TEMPLATES, PROFILE, sbd_ctx, []), sbd_ctx)
check("SBD3.x page renders the same grid on an SBD pack",
      "Year 3" in sbd_html and "Once-Off (R)" in sbd_html)

# TWK 5-year escalated shape: 5 rows + escalation column (mock 5.0% p.a.)
twk_periods = [
    FakeBid({"period_label": f"Year {i}", "once_off": None,
             "monthly": round(36317.60 * (1.05 ** (i - 1)), 2),
             "annual_total": round(435811.20 * (1.05 ** (i - 1)), 2),
             "unit_tariff": None, "unit_label": None,
             "escalation_applied_pct": None if i == 1 else 5.0, "notes": None})
    for i in range(1, 6)
]
twk_bid = FakeBid(regime="MBD", tender_slug="cor-01-2026-27",
                  tender_title="Support, Maintenance, Development and Hosting of a Website",
                  institution="Theewaterskloof Municipality", estimated_value=2179056,
                  contract_term_months=60, escalation_provision="Fixed % per annum",
                  escalation_rate_pct=5.0, pricing_periods=twk_periods)
twk_ctx = gbp.build_bid_context(twk_bid)
twk_html = pack_builder.render_pack_html(
    pack_builder.build_pack(gbp.load_regime(twk_bid), TEMPLATES, PROFILE, twk_ctx, []), twk_ctx)
check("TWK 5-year shape renders 5 period rows",
      all(f"Year {i}" in twk_html for i in range(1, 6)))
check("TWK escalation column renders the applied 5.0% p.a.",
      "Escalation %" in twk_html and "5.0" in twk_html)

print("== (b) single-year bid: pack output byte-identical to pre-change code + fixtures ==")
# Baseline = the pre-PR-B tree (PR #37's merge commit 686850c, main just
# before PR-B landed), snapshotted VERBATIM under data/pr_b_baseline_686850c/
# so the byte-identity check needs no git history (plan #2: `git show` on a
# shallow clone fails with a subprocess error that looks like a real
# failure). PR_B_BASE_REF still overrides to a git ref for ad-hoc
# comparisons; without the override the committed snapshot is additionally
# drift-checked against git 686850c whenever history can serve it.
BASELINE_COMMIT = "686850c"
BASELINE_DIR = os.path.join(SCRATCH, "data", "pr_b_baseline_686850c")
BASELINE_FILES = {
    "tender/frappe/src/control/pack_builder.py": "pack_builder.py",
    "tender/frappe/src/control/api/tenders/generate_bid_pack.py": "generate_bid_pack.py",
    "tender/frappe/src/control/compliance/rules.py": "rules.py",
    "tender/frappe/fixtures/tender_form_templates.json": "tender_form_templates.json",
    "tender/frappe/fixtures/tender_compliance_rules.json": "tender_compliance_rules.json",
}
base_ref = os.environ.get("PR_B_BASE_REF")


def git_show(ref, path):
    return subprocess.run(
        ["git", "-C", REPO, "show", f"{ref}:{path}"],
        check=True, capture_output=True, text=True,
    ).stdout


def snapshot_read(path):
    with open(os.path.join(BASELINE_DIR, BASELINE_FILES[path]), encoding="utf-8") as fh:
        return fh.read()


def baseline_read(path):
    return git_show(base_ref, path) if base_ref else snapshot_read(path)


snapshot_complete = all(
    os.path.exists(os.path.join(BASELINE_DIR, name)) for name in BASELINE_FILES.values()
)
baseline_available = bool(base_ref) or snapshot_complete
print(f"   baseline: {base_ref or 'committed snapshot data/pr_b_baseline_686850c/'}")

if base_ref:
    print("SKIP snapshot-vs-git drift check (PR_B_BASE_REF override in use)")
elif not snapshot_complete:
    print("SKIP snapshot-vs-git drift check (committed snapshot incomplete)")
else:
    try:
        drift = [path for path in BASELINE_FILES
                 if git_show(BASELINE_COMMIT, path) != snapshot_read(path)]
    except Exception:
        drift = None
    if drift is None:
        print(f"SKIP committed baseline snapshot byte-identical to git {BASELINE_COMMIT} "
              "(history unavailable - e.g. shallow clone)")
    else:
        check(f"committed baseline snapshot byte-identical to git {BASELINE_COMMIT}",
              drift == [])

if baseline_available:
    old_pack_builder = load_module_from_source(
        "t_pack_builder_old", baseline_read("tender/frappe/src/control/pack_builder.py"),
        os.path.join(SRC, "pack_builder.py"))
    old_gbp = load_module_from_source(
        "t_generate_bid_pack_old",
        baseline_read("tender/frappe/src/control/api/tenders/generate_bid_pack.py").replace("{app_name}", "_app_stub"),
        os.path.join(SRC, "api/tenders/generate_bid_pack.py"))
    old_rules_mod = load_module_from_source(
        "t_rules_old", baseline_read("tender/frappe/src/control/compliance/rules.py"),
        os.path.join(SRC, "compliance/rules.py"))
    OLD_TEMPLATES = {t["template_code"]: t
                     for t in json.loads(baseline_read("tender/frappe/fixtures/tender_form_templates.json"))}
    OLD_RULES_ALL = json.loads(baseline_read("tender/frappe/fixtures/tender_compliance_rules.json"))
else:
    # Degrade to SKIP, matching the suite family's discipline (README): a
    # missing baseline must read as "not checked here", never as a failure.
    old_pack_builder = old_gbp = old_rules_mod = None
    OLD_TEMPLATES = OLD_RULES_ALL = None
    print("SKIP baseline comparisons (no committed snapshot and no PR_B_BASE_REF)")

plain_bids = [
    FakeBid(regime="MBD", tender_slug="cor-01-2026-27",
            tender_title="Hosting of a Website", institution="Theewaterskloof Municipality"),
    FakeBid(regime="SBD", tender_slug="dffe-forests",
            tender_title="Determination of the state of forests in South Africa",
            institution="Department of Forestry, Fisheries and the Environment"),
    FakeBid(regime="CIDB", tender_slug="rrm", tender_title="Routine road maintenance",
            institution="SANRAL", estimated_value=9000000),
    FakeBid(regime="MBD", overlay_regime="CIDB", tender_slug="8-2-rnm0614",
            tender_title="Construction of Mgodlwa Bridge in Ward 8",
            institution="Ray Nkonyeni Local Municipality", estimated_value=42500000),
]
if baseline_available:
    all_identical = True
    for bid in plain_bids:
        new_ctx = gbp.build_bid_context(bid)
        old_ctx = old_gbp.build_bid_context(bid)
        new_html = pack_builder.render_pack_html(
            pack_builder.build_pack(gbp.load_regime(bid), TEMPLATES, PROFILE, new_ctx, []), new_ctx)
        old_html = old_pack_builder.render_pack_html(
            old_pack_builder.build_pack(old_gbp.load_regime(bid), OLD_TEMPLATES, PROFILE, old_ctx, []),
            old_ctx)
        if new_html != old_html:
            all_identical = False
            print("   HTML MISMATCH for", bid.get("institution"))
    check("4 single-year packs (MBD/SBD/CIDB/MBD+CIDB) byte-identical to pre-change "
          "old-code+old-fixtures output", all_identical)
    check("apply_custom_returnables without rows returns the regime untouched",
          gbp.apply_custom_returnables(gbp.load_regime(plain_bids[0]), plain_bids[0])
          == old_gbp.load_regime(plain_bids[0]))
else:
    print("SKIP 4 single-year packs byte-identical to pre-change output (no baseline)")
    print("SKIP apply_custom_returnables without rows returns the regime untouched (no baseline)")

sample_contexts = [
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
if baseline_available:
    rule_sets_identical = True
    for bid in sample_contexts:
        # wave-2 PR-C ships QUIRK-* Buyer Quirk rules (F-11) that INTENTIONALLY
        # attach to the sample buyers via institution_matches - exclude that new
        # class here so this check keeps its original meaning: no OTHER rule's
        # applicability changed, and PRICE-MULTIYEAR-ESC still attaches to none
        # of the no-term contexts.
        new_set = {r["rule_code"] for r in ALL_RULES
                   if r["rule_class"] != "Buyer Quirk"
                   and rules.rule_applies(r, rules.bid_context(bid))}
        old_set = {r["rule_code"] for r in OLD_RULES_ALL
                   if old_rules_mod.rule_applies(r, old_rules_mod.bid_context(bid))}
        if new_set != old_set:
            rule_sets_identical = False
            print("   RULE-SET MISMATCH", bid.get("institution"), new_set ^ old_set)
    check("applicable rule set identical to pre-change for all 7 no-term contexts "
          "(PRICE-MULTIYEAR-ESC attaches to none of them; PR-C Buyer Quirks excluded "
          "as intentional additions)", rule_sets_identical)
else:
    print("SKIP applicable rule set identical to pre-change for all 7 no-term contexts (no baseline)")

print("== (c) F-02: buyer-authored returnables ==")
MUSINA_RETURNABLES = [
    FakeBid(ref_code="Form A", title="Form A - Certificate of Acquaintance with Tender Documents",
            mandatory=1, category="Buyer Form",
            kill_note="Failure to complete and sign will invalidate the tender.",
            template_code=None, guidance="Initial every page of the terms of reference."),
    FakeBid(ref_code="Form B", title="Form B - Declaration of Interest", mandatory=1,
            category="Buyer Form", kill_note="", template_code="MBD4", guidance=""),
    FakeBid(ref_code="Form C",
            title="Form C - HDI Equity Ownership claim: ...% = ... Points out of 20",
            mandatory=1, category="Legacy Preference Form",
            kill_note="Non-completion forfeits the preference.", template_code=None, guidance=""),
    FakeBid(ref_code="Form D",
            title="Form D - Certificate of Preference for Local Content and SABS mark "
                  "(Local Government Ordinance, 1939)",
            mandatory=1, category="Legacy Preference Form",
            kill_note="Non-completion forfeits the preference.", template_code=None, guidance=""),
    FakeBid(ref_code="Form E", title="Form E - Municipal Rates and Taxes declaration",
            mandatory=1, category="Buyer Form", kill_note="", template_code=None, guidance=""),
    FakeBid(ref_code="MBD 6.1", title="Preference Points Claim Form", mandatory=1,
            category="Buyer Form", kill_note="", template_code="MBD6.1", guidance=""),
    FakeBid(ref_code="MBD 8", title="Declaration of Bidder's Past SCM Practices", mandatory=1,
            category="Buyer Form", kill_note="", template_code="MBD8", guidance=""),
    FakeBid(ref_code="MBD 9", title="Certificate of Independent Bid Determination", mandatory=1,
            category="Buyer Form", kill_note="", template_code="MBD9", guidance=""),
    FakeBid(ref_code="5.1(i)", title="Company profile, organogram and capability schedule",
            mandatory=1, category="Technical Returnable", kill_note="",
            template_code="ICT-CAPABILITY", guidance="Attach the signed capability schedule."),
]
override_bid = FakeBid(
    regime="MBD", tender_slug="musina-18-2025-26",
    tender_title="Cloud-Based Helpdesk Management System",
    institution="Musina Local Municipality", preference_system="80/20",
    returnables_override=1, custom_returnables=MUSINA_RETURNABLES,
)
override_regime = gbp.apply_custom_returnables(gbp.load_regime(override_bid), override_bid)
check("override: pack form set is EXACTLY the nine captured returnables, issued order",
      [f["form_code"] for f in override_regime["forms"]]
      == ["Form A", "Form B", "Form C", "Form D", "Form E", "MBD 6.1", "MBD 8", "MBD 9", "5.1(i)"])
override_ctx = gbp.build_bid_context(override_bid)
override_pack = pack_builder.build_pack(override_regime, TEMPLATES, PROFILE, override_ctx, [])
override_html = pack_builder.render_pack_html(override_pack, override_ctx)
by_code = {f["form_code"]: f for f in override_pack["forms"]}
check("template-less rows render the guided worksheet page",
      not by_code["Form A"]["has_template"] and "No field template exists" in override_html)
check("captured kill note renders on the worksheet page",
      "Failure to complete and sign will invalidate the tender." in override_html)
check("captured guidance renders as the worksheet's instruction notice",
      by_code["Form A"]["instructions"] == "Initial every page of the terms of reference.")
check("template_code rows resolve to real templates (MBD4/6.1/8/9)",
      all(by_code[c]["has_template"] for c in ("Form B", "MBD 6.1", "MBD 8", "MBD 9")))
check("ICT-CAPABILITY reachable via a custom returnable's template_code",
      by_code["5.1(i)"]["has_template"]
      and by_code["5.1(i)"]["form_name"] == "Website / Hosting Capability Schedule")
check("legacy Forms C/D trip the WARN-PREF-CONFLICT lint on the generated pack",
      any("conflicting preference frameworks" in w for w in override_pack["manifest"]["warnings"]))

append_bid = FakeBid(
    regime="MBD", tender_slug="musina-18-2025-26",
    tender_title="Cloud-Based Helpdesk Management System",
    institution="Musina Local Municipality",
    returnables_override=0,
    custom_returnables=[MUSINA_RETURNABLES[0],
                        FakeBid(ref_code="MBD4", title="Captured duplicate - must lose",
                                mandatory=1, category="Buyer Form", kill_note="",
                                template_code=None, guidance="")],
)
append_regime = gbp.apply_custom_returnables(gbp.load_regime(append_bid), append_bid)
fixture_codes = [f["form_code"] for f in REGIME_FIXTURES["MBD"]["forms"]]
append_codes = [f["form_code"] for f in append_regime["forms"]]
check("override unticked: full fixture regime set kept (never-delete), custom rows appended",
      append_codes[: len(fixture_codes)] == fixture_codes and "Form A" in append_codes)
mbd4_rows = [f for f in append_regime["forms"] if f["form_code"] == "MBD4"]
check("dedupe by form_code: the regime's fixture row wins over a captured duplicate",
      len(mbd4_rows) == 1 and mbd4_rows[0]["form_name"] != "Captured duplicate - must lose")

print("== (d) F-07: capability register renders in the ICT-CAPABILITY template ==")
CAPABILITIES = [
    {"capability_type": "Portfolio / Reference Site", "label": "www.client-municipality.gov.za",
     "value": "Live since 2022", "detail": "Design, hosting and maintenance",
     "reference_url": "https://www.client-municipality.gov.za", "valid_until": None},
    {"capability_type": "Hosting Infrastructure", "label": "Teraco JB1",
     "value": "ZA-only", "detail": "Tier III colocation", "reference_url": None,
     "valid_until": None},
    {"capability_type": "Uptime SLA", "label": "Managed hosting SLA",
     "value": "99.9% monthly", "detail": None, "reference_url": None, "valid_until": None},
    {"capability_type": "Security Certification", "label": "ISO/IEC 27001",
     "value": "Certified", "detail": None, "reference_url": None, "valid_until": "2027-03-31"},
]
twk_returnable_bid = FakeBid(
    regime="MBD", tender_slug="cor-01-2026-27",
    tender_title="Support, Maintenance, Development and Hosting of a Website",
    institution="Theewaterskloof Municipality", returnables_override=0,
    custom_returnables=[FakeBid(ref_code="RS-7", title="Website / hosting capability schedule",
                                mandatory=1, category="Technical Returnable", kill_note="",
                                template_code="ICT-CAPABILITY", guidance="")],
)
cap_profile = dict(PROFILE, capabilities=CAPABILITIES)
twk_regime = gbp.apply_custom_returnables(gbp.load_regime(twk_returnable_bid), twk_returnable_bid)
twk_ctx2 = gbp.build_bid_context(twk_returnable_bid)
cap_pack = pack_builder.build_pack(twk_regime, TEMPLATES, cap_profile, twk_ctx2, [])
cap_html = pack_builder.render_pack_html(cap_pack, twk_ctx2)
check("capability rows render as a table (type/item/value columns)",
      all(s in cap_html for s in ("www.client-municipality.gov.za", "Teraco JB1",
                                  "99.9% monthly", "Valid Until", "2027-03-31")))
check("pack-specific SLA/DR demands render as USER INPUT blanks",
      "Uptime SLA offered (as THIS pack defines and measures it)" in cap_html
      and "Disaster recovery / backup regime for this contract" in cap_html)
empty_pack = pack_builder.build_pack(
    twk_regime, TEMPLATES, dict(PROFILE, capabilities=[]), twk_ctx2, [])
empty_html = pack_builder.render_pack_html(empty_pack, twk_ctx2)
check("empty capability register renders the amber profile gap, never silently blank",
      "Not in your Business Profile" in empty_html)
check("capabilities registered in the profile FILL_FIELDS surface",
      "\"capabilities\"" in open(
          os.path.join(SRC, "doctype/tender_business_profile/tender_business_profile.py"),
          encoding="utf-8").read()
      or '"capabilities",' in open(
          os.path.join(SRC, "doctype/tender_business_profile/tender_business_profile.py"),
          encoding="utf-8").read())

print("== (e) PRICE-MULTIYEAR-ESC fires only on multi-year contexts ==")
rule = RULES["PRICE-MULTIYEAR-ESC"]
check("rule shape: Pricing Rule / Curable / Conditional / term-over-12 trigger",
      rule["rule_class"] == "Pricing Rule" and rule["severity"] == "Curable"
      and rule["scope"] == "Conditional"
      and json.loads(rule["trigger_condition"]) == {"contract_term_months_over": 12})
check("params carry the firm-price review note",
      "firm_price_review_note" in json.loads(rule["params"]))
check("fires on the Musina 36-month context",
      rules.rule_applies(rule, rules.bid_context(musina_bid)))
check("fires on the TWK 5-year (60-month) context",
      rules.rule_applies(rule, rules.bid_context(twk_bid)))
check("stays off a 12-month DFFE-shaped bid",
      not rules.rule_applies(rule, rules.bid_context(
          FakeBid(regime="SBD", institution="DFFE", contract_term_months=12))))
check("stays off unset and zero terms",
      not rules.rule_applies(rule, rules.bid_context(FakeBid(regime="MBD")))
      and not rules.rule_applies(rule, rules.bid_context(
          FakeBid(regime="MBD", contract_term_months=0))))
check("bid_context normalises a zero term to None",
      rules.bid_context(FakeBid(regime="MBD", contract_term_months=0))["contract_term_months"] is None)

print("== (f) Sectioned mode with empty sections: warning, never a block ==")
gate = load_module("t_submission_gate", os.path.join(SRC, "compliance/submission_gate.py"))
empty_sectioned = FakeBid(functionality_mode="Sectioned", functionality_sections=[],
                          user="u@example.com", closing_date="2026-09-30")
check("Sectioned + empty sections still PASSES the gate",
      gate.validate_submission_readiness(empty_sectioned) == [])
check("...but produces the SECTIONED-NO-SECTIONS warning",
      gate.submission_readiness_warnings(empty_sectioned)
      == [gate.SECTIONED_NO_SECTIONS_WARNING]
      and "Sectioned functionality selected but no sections captured"
      in gate.SECTIONED_NO_SECTIONS_WARNING)
check("missing sections table (None) warns the same",
      gate.submission_readiness_warnings(FakeBid(functionality_mode="Sectioned"))
      == [gate.SECTIONED_NO_SECTIONS_WARNING])
vcw_sections = [
    {"section_label": "Section 1 - Guarding services", "max_points": 335,
     "threshold_pct": 75, "self_score_points": 290},
    {"section_label": "Section 2 - Fencing and related works", "max_points": 165,
     "threshold_pct": 75, "self_score_points": 110},
]
populated = FakeBid(functionality_mode="Sectioned", functionality_sections=vcw_sections,
                    user="u@example.com", closing_date="2026-09-30")
pop_failures = gate.validate_submission_readiness(populated)
check("populated sections behave as shipped in #37: failing section still kills, no warning",
      len(pop_failures) == 1 and "Section 2 - Fencing and related works" in pop_failures[0]
      and gate.submission_readiness_warnings(populated) == [])
vcw_sections[1]["self_score_points"] = 130
check("populated sections that clear still pass with no warning",
      gate.validate_submission_readiness(populated) == []
      and gate.submission_readiness_warnings(populated) == [])
check("other modes never warn",
      gate.submission_readiness_warnings(FakeBid(functionality_mode="Single threshold")) == []
      and gate.submission_readiness_warnings(FakeBid(functionality_mode="No scored functionality")) == []
      and gate.submission_readiness_warnings(FakeBid()) == [])
warn_pack = pack_builder.build_pack(
    gbp.load_regime(FakeBid(regime="MBD")), TEMPLATES, PROFILE,
    gbp.build_bid_context(FakeBid(regime="MBD", tender_slug="s", tender_title="t")),
    [], None, gate.submission_readiness_warnings(empty_sectioned))
check("the warning lands in the pack manifest and prints on the cover",
      any("SECTIONED-NO-SECTIONS" in w for w in warn_pack["manifest"]["warnings"])
      and "SECTIONED-NO-SECTIONS" in pack_builder.render_pack_html(
          warn_pack, gbp.build_bid_context(FakeBid(regime="MBD", tender_slug="s", tender_title="t"))))

print("== regression: fixtures shaped as expected ==")
counts = {}
for r in ALL_RULES:
    counts[r["rule_class"]] = counts.get(r["rule_class"], 0) + 1
# wave-3 adds GATE-PACK-COLLECT (F-08): Registration Gate 19 -> 20, total 56 -> 57
# wave-2 PR-C adds 12 QUIRK-* Buyer Quirk rules (F-11): new class, total 57 -> 69
check("rule counts: 20/25/7/3/2/12, total 69 (PRICE-MULTIYEAR-ESC + GATE-PACK-COLLECT + QUIRK-*)",
      counts == {"Registration Gate": 20, "Disqualification Cause": 25, "Scoring Rule": 7,
                 "Pricing Rule": 3, "Form Rule": 2, "Buyer Quirk": 12} and len(ALL_RULES) == 69)
check("every regime form still has a template",
      not [(r["regime_code"], f["form_code"]) for r in REGIME_FIXTURES.values()
           for f in r["forms"] if f["form_code"] not in TEMPLATES])
check("ICT-CAPABILITY exists but is in NO regime's fixture set (packs never inflate)",
      "ICT-CAPABILITY" in TEMPLATES
      and all("ICT-CAPABILITY" not in {f["form_code"] for f in r["forms"]}
              for r in REGIME_FIXTURES.values()))
if baseline_available:
    check("templates fixture grew by exactly one (34 -> 35)",
          len(TEMPLATES) == 35 and len(OLD_TEMPLATES) == 34)
else:
    print("SKIP templates fixture grew by exactly one (34 -> 35) (no baseline)")

failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL WAVE-2 PR-B CHECKS PASSED")
