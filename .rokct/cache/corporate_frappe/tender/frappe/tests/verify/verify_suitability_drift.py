#!/usr/bin/env python3
"""Standalone verification for the scheduled suitability drift report
(assessment plan #9): the calibration corpus run (gates fired, band
distribution, confidence mix, enrichment coverage) recomputed weekly
over the live cached catalog against FIXED synthetic reference
personas, stored as one Tender Suitability Drift Snapshot per run.
Proves the pure module (compliance/suitability_drift.py): reference
personas frozen and synthetic (P1/P2 gate-complete, P3 the empty-profile
canary), snapshot shape reusing enrichment_stats verbatim, counting
correctness over a known corpus, byte-level determinism, snapshot
comparison deltas; the frappe glue (drift_report.py) end-to-end against
a stubbed frappe (control-only, idempotent per run date, empty-cache
no-op, snapshot stored with sorted-keys payload); and the wiring
(doctype schema, weekly scheduler registration in the manifest). Exit
code 0 = all checks pass."""

import copy
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
FIXTURES = os.path.join(REPO, "tender/frappe/fixtures")

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


# --------------------------------------------------------------------------
# frappe stub (the suitability engine imports frappe.utils.cint)
# --------------------------------------------------------------------------
frappe_stub = types.ModuleType("frappe")
utils_stub = types.ModuleType("frappe.utils")
utils_stub.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
utils_stub.flt = lambda v, precision=None: float(v) if v not in (None, "") else 0.0
utils_stub.nowdate = lambda: "2026-08-24"
frappe_stub.utils = utils_stub
frappe_stub.whitelist = lambda *a, **k: (lambda f: f)
frappe_stub.conf = {"app_role": "control"}
frappe_stub.db = types.SimpleNamespace(
    get_value=lambda *a, **k: None, exists=lambda *a, **k: False
)
sys.modules["frappe"] = frappe_stub
sys.modules["frappe.utils"] = utils_stub


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


drift = load_module(
    "v_suitability_drift", os.path.join(SRC, "compliance/suitability_drift.py")
)
suitability = load_module(
    "v_drift_suitability", os.path.join(SRC, "compliance/suitability.py")
)
enrichment_gate = load_module(
    "v_drift_enrichment_gate", os.path.join(SRC, "compliance/enrichment_gate.py")
)

with open(os.path.join(FIXTURES, "tender_compliance_rules.json"), encoding="utf-8") as f:
    ALL_RULES = json.load(f)
FUNCTIONALITY_PARAMS = json.loads(
    {r["rule_code"]: r for r in ALL_RULES}["SCORE-FUNCTIONALITY"]["params"]
)
TODAY = "2026-08-24"

CARDS = [
    {  # enriched ICT card - pack_verified for every persona
        "slug": "ocds-drift-1",
        "title": "Cloud helpdesk management system",
        "institution": "Musina Local Municipality",
        "category": "Services: ICT and related",
        "province": "Limpopo", "status": "ACTIVE",
        "closing_date": "2026-09-15",
        "is_there_a_briefing_session": "No",
    },
    {  # advert-only construction card with a statutory CIDB demand
        "slug": "ocds-drift-2",
        "title": "Construction of a community hall",
        "institution": "Capricorn District Municipality",
        "category": "Civil engineering",
        "province": "Limpopo", "status": "ACTIVE",
        "closing_date": "2026-09-20",
        "is_there_a_briefing_session": "No",
    },
    {  # already-closed card - gates for every persona
        "slug": "ocds-drift-3",
        "title": "Supply of stationery",
        "institution": "SARS",
        "category": "Supplies: Stationery",
        "province": "Gauteng", "status": "ACTIVE",
        "closing_date": "2026-01-01",
        "is_there_a_briefing_session": "No",
    },
]
ENRICHMENT = {
    "ocds-drift-1": {"tasks": ["Provide company registration documents | 1"]},
}


def snapshot(**kw):
    args = dict(records=CARDS, enrichment_map=ENRICHMENT, rules_list=ALL_RULES,
                functionality_params=FUNCTIONALITY_PARAMS, gate_params=None,
                today=TODAY)
    args.update(kw)
    return drift.drift_snapshot(**args)


SNAP = snapshot()

# --------------------------------------------------------------------------
# (a) the reference personas - a frozen, synthetic yardstick
# --------------------------------------------------------------------------
print("== (a) fixed synthetic reference personas ==")
check("three committed personas, the calibration run's own P1/P2/P3",
      sorted(drift.REFERENCE_PROFILES)
      == ["p1_services_smme", "p2_construction_smme", "p3_empty_profile"])
p1 = drift.REFERENCE_PROFILES["p1_services_smme"]
p2 = drift.REFERENCE_PROFILES["p2_construction_smme"]
check("P1/P2 clear the profile-side gates (CSD, TCS PIN, CIPC) so they "
      "measure card-side gates, not their own gaps",
      suitability.check_profile_completeness(p1)["complete"]
      and suitability.check_profile_completeness(p2)["complete"])
check("P1 matches the model doc: services sectors, Gauteng, NO CIDB; "
      "P2: CIDB 2GB, Limpopo + Gauteng",
      p1["cidb_grade"] == "" and p1["operating_provinces"] == "Gauteng"
      and len([s for s in p1["operating_sectors"].split(",") if s.strip()]) == 7
      and p2["cidb_grade"] == "2GB"
      and "Limpopo" in p2["operating_provinces"])
check("P3 is the EMPTY profile - the PROFILE-INCOMPLETE canary",
      drift.REFERENCE_PROFILES["p3_empty_profile"] == {})
check("persona values are marked SYNTHETIC in the capability text and "
      "the module says they must never be swapped for user data",
      all("SYNTHETIC" in t for t in p1["capability_texts"] + p2["capability_texts"])
      and "never against any user's data" in (drift.__doc__ or ""))

# --------------------------------------------------------------------------
# (b) snapshot shape - existing machinery reused, not reinvented
# --------------------------------------------------------------------------
print("== (b) snapshot shape ==")
check("snapshot carries run_on, catalog, profiles, semantics, caveats",
      set(SNAP) == {"run_on", "catalog", "profiles", "semantics", "caveats"}
      and SNAP["run_on"] == TODAY)
check("the catalog block IS enrichment_stats' output verbatim (F-08 "
      "machinery reused: 1 full / 2 advert-only here)",
      SNAP["catalog"] == enrichment_gate.enrichment_stats(CARDS, ENRICHMENT, None)
      and SNAP["catalog"]["full"] == 1 and SNAP["catalog"]["advert_only"] == 2)
check("one corpus-run block per persona, sorted by key",
      list(SNAP["profiles"])
      == ["p1_services_smme", "p2_construction_smme", "p3_empty_profile"])
p1_run = SNAP["profiles"]["p1_services_smme"]
check("each block counts cards_scored, all six bands, both confidences, "
      "gates fired and the score spread",
      set(p1_run) == {"cards_scored", "bands", "confidence", "gates_fired",
                      "scores"}
      and set(p1_run["bands"]) == {"strong", "review", "marginal", "poor",
                                   "no_bid", "unscored"}
      and set(p1_run["confidence"]) == {"pack_verified", "advert_only"}
      and set(p1_run["scores"]) == {"scored", "distinct", "min", "median",
                                    "max"})

# --------------------------------------------------------------------------
# (c) counting correctness over the known corpus
# --------------------------------------------------------------------------
print("== (c) counting correctness ==")
check("every persona scored every card; band counts always sum to the "
      "cards scored",
      all(run["cards_scored"] == 3
          and sum(run["bands"].values()) == 3
          for run in SNAP["profiles"].values()))
check("confidence mix mirrors enrichment coverage for every persona "
      "(the one enriched card is pack_verified, the rest advert_only)",
      all(run["confidence"] == {"pack_verified": 1, "advert_only": 2}
          for run in SNAP["profiles"].values()))
p3_run = SNAP["profiles"]["p3_empty_profile"]
check("the empty-profile canary: every card no_bid, PROFILE-INCOMPLETE "
      "fires on all 3, no numeric scores at all",
      p3_run["bands"]["no_bid"] == 3
      and p3_run["gates_fired"].get("PROFILE-INCOMPLETE") == 3
      and p3_run["scores"] == {"scored": 0, "distinct": 0, "min": None,
                               "median": None, "max": None})
check("real personas differ from the canary (P1 scores at least one "
      "card numerically; the closed card gates for everyone)",
      p1_run["scores"]["scored"] >= 1
      and p1_run["scores"]["min"] is not None
      and p1_run["bands"]["no_bid"] >= 1
      and any("CLOS" in code or "closed" in code.lower()
              for code in p1_run["gates_fired"]))
check("gates_fired keys are sorted (stable diffs between snapshots)",
      all(list(run["gates_fired"]) == sorted(run["gates_fired"])
          for run in SNAP["profiles"].values()))
check("an empty catalog yields an all-zero snapshot, never an error",
      snapshot(records=[], enrichment_map={})["profiles"]
      ["p1_services_smme"]["cards_scored"] == 0)

# --------------------------------------------------------------------------
# (d) determinism - same inputs, byte-identical snapshot
# --------------------------------------------------------------------------
print("== (d) determinism ==")
inputs_copy = copy.deepcopy((CARDS, ENRICHMENT))
again = snapshot()
check("two runs over identical inputs are identical, byte-for-byte "
      "under sorted-keys serialization",
      again == SNAP
      and json.dumps(again, sort_keys=True) == json.dumps(SNAP, sort_keys=True))
check("the corpus run never mutates its inputs",
      (CARDS, ENRICHMENT) == inputs_copy)

# --------------------------------------------------------------------------
# (e) honesty layer
# --------------------------------------------------------------------------
print("== (e) semantics + caveats ==")
check("semantics: deterministic, no AI, catalog drift only - never a "
      "win probability, never a user's fit",
      "no AI" in SNAP["semantics"]
      and "never a win probability" in SNAP["semantics"]
      and "never a user's fit" in SNAP["semantics"])
check("caveats carry the yardstick rule (synthetic personas, not user "
      "data) and argued-not-fitted weights",
      any("SYNTHETIC" in c for c in SNAP["caveats"])
      and any("argued-not-fitted" in c for c in SNAP["caveats"]))

# --------------------------------------------------------------------------
# (f) snapshot comparison - drift as plain deltas
# --------------------------------------------------------------------------
print("== (f) compare_snapshots ==")
check("no previous snapshot -> honestly unavailable, never a fake zero "
      "baseline",
      drift.compare_snapshots(None, SNAP)
      == {"available": False, "reason": "no previous snapshot"})
zero = drift.compare_snapshots(SNAP, SNAP)
check("identical snapshots -> zero drift everywhere (shares in pct "
      "points, gates in counts)",
      zero["available"] is True and zero["catalog_total_delta"] == 0
      and all(v == 0.0 for run in zero["profiles"].values()
              for v in run["band_share_delta_pct"].values())
      and all(v == 0 for run in zero["profiles"].values()
              for v in run["gates_fired_delta"].values()))
moved = copy.deepcopy(SNAP)
moved["profiles"]["p3_empty_profile"]["bands"] = {
    "strong": 0, "review": 0, "marginal": 0, "poor": 0, "no_bid": 2,
    "unscored": 1}
moved["profiles"]["p3_empty_profile"]["gates_fired"] = {
    "PROFILE-INCOMPLETE": 2}
delta = drift.compare_snapshots(SNAP, moved)["profiles"]["p3_empty_profile"]
check("a real shift reads as share drift: no_bid 100 -> 66.7 pct is "
      "-33.3 points, unscored +33.3, PROFILE-INCOMPLETE -1 count",
      delta["band_share_delta_pct"]["no_bid"] == -33.3
      and delta["band_share_delta_pct"]["unscored"] == 33.3
      and delta["gates_fired_delta"]["PROFILE-INCOMPLETE"] == -1)
check("a persona missing from the previous snapshot is reported, not "
      "zero-filled",
      drift.compare_snapshots(
          {"run_on": "x", "catalog": {"total": 0}, "profiles": {}}, SNAP
      )["profiles"]["p1_services_smme"]
      == {"available": False, "reason": "new profile"})

# --------------------------------------------------------------------------
# (g) purity
# --------------------------------------------------------------------------
print("== (g) purity ==")
drift_src = open(os.path.join(SRC, "compliance/suitability_drift.py")).read()
check("suitability_drift.py is frappe-free and reuses the existing "
      "machinery (enrichment_stats, score_suitability, median_value) - "
      "no new statistics frameworks",
      "import frappe" not in drift_src and "requests" not in drift_src
      and "enrichment_stats" in drift_src and "score_suitability" in drift_src
      and "median_value" in drift_src)

# --------------------------------------------------------------------------
# (h) the scheduled glue against a stubbed frappe
# --------------------------------------------------------------------------
print("== (h) drift_report glue (frappe stubbed) ==")


def build_frappe(app_role="control", existing_run=False, previous_rows=None):
    frappe = types.ModuleType("frappe")
    frappe.conf = {"app_role": app_role}
    frappe.utils = utils_stub
    frappe.inserted = []

    def exists(doctype, filters=None):
        assert doctype == "Tender Suitability Drift Snapshot"
        return existing_run

    def get_all(doctype, fields=None, order_by=None, limit=None):
        assert doctype == "Tender Suitability Drift Snapshot"
        return list(previous_rows or [])

    def get_doc(payload):
        doc = types.SimpleNamespace(**payload)
        doc.name = "TSDS-00001"
        doc.insert = lambda ignore_permissions=False: frappe.inserted.append(payload)
        return doc

    frappe.db = types.SimpleNamespace(exists=exists)
    frappe.get_all = get_all
    frappe.get_doc = get_doc
    return frappe


def load_glue(frappe_mod, records):
    src = open(os.path.join(SRC, "drift_report.py")).read()
    src = src.replace("{app_name}", "_app_stub")

    opp_utils = types.ModuleType("_app_stub.tender.control.api.opportunity_utils")
    opp_utils.get_cached_opportunities = lambda kind: (
        records if kind == "tenders"
        else {"advanced_enrichment": ENRICHMENT} if kind == "meta" else None
    )
    rules_mod = types.ModuleType("_app_stub.tender.control.compliance.rules")
    rules_mod.load_rules = lambda rule_class=None: list(ALL_RULES)
    rules_mod.get_scoring_rule = lambda code: FUNCTIONALITY_PARAMS
    gate_mod = types.ModuleType(
        "_app_stub.tender.control.compliance.enrichment_gate")
    gate_mod.load_gate_params = lambda: None

    pkg_names = [
        "_app_stub", "_app_stub.tender", "_app_stub.tender.control",
        "_app_stub.tender.control.api", "_app_stub.tender.control.compliance",
    ]
    saved = {}
    mods = {}
    for name in pkg_names:
        mods[name] = types.ModuleType(name)
        mods[name].__path__ = []
    mods["_app_stub.tender.control.api"].opportunity_utils = opp_utils
    mods["_app_stub.tender.control.api.opportunity_utils"] = opp_utils
    mods["_app_stub.tender.control.compliance"].rules = rules_mod
    mods["_app_stub.tender.control.compliance.rules"] = rules_mod
    mods["_app_stub.tender.control.compliance"].enrichment_gate = gate_mod
    mods["_app_stub.tender.control.compliance.enrichment_gate"] = gate_mod
    mods["_app_stub.tender.control.compliance"].suitability_drift = drift
    mods["_app_stub.tender.control.compliance.suitability_drift"] = drift
    for name, mod in list(mods.items()) + [
            ("frappe", frappe_mod), ("frappe.utils", frappe_mod.utils)]:
        saved[name] = sys.modules.get(name)
        sys.modules[name] = mod
    try:
        module = types.ModuleType("v_drift_glue")
        exec(compile(src, "drift_report.py", "exec"), module.__dict__)
        return module
    finally:
        for name, orig in saved.items():
            if name.startswith("_app_stub"):
                # the glue imports the stub package chain lazily at CALL
                # time - it must stay importable after loading
                continue
            if orig is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = orig


frappe_run = build_frappe()
glue = load_glue(frappe_run, CARDS)
name = glue.run_suitability_drift_report()
stored = frappe_run.inserted[0] if frappe_run.inserted else {}
stored_payload = json.loads(stored.get("payload") or "{}")
check("a run stores exactly one snapshot doc with the summary columns "
      "off the catalog block",
      name == "TSDS-00001" and len(frappe_run.inserted) == 1
      and stored.get("doctype") == "Tender Suitability Drift Snapshot"
      and stored.get("run_on") == "2026-08-24"
      and stored.get("catalog_total") == 3 and stored.get("full_records") == 1
      and stored.get("advert_only_records") == 2
      and stored.get("profiles_scored") == 3)
check("the stored payload IS the pure snapshot (plus the drift block) "
      "serialized with sorted keys",
      {k: stored_payload.get(k) for k in SNAP} == json.loads(
          json.dumps(dict(SNAP, run_on="2026-08-24"), sort_keys=True))
      and stored.get("payload") == json.dumps(stored_payload, sort_keys=True))
check("first run's drift block honestly says no previous snapshot",
      stored_payload["drift_vs_previous"]
      == {"available": False, "reason": "no previous snapshot"})
prev_row = [{"name": "TSDS-00000", "payload": stored.get("payload")}]
frappe_second = build_frappe(previous_rows=prev_row)
second = load_glue(frappe_second, CARDS).run_suitability_drift_report()
second_payload = json.loads(frappe_second.inserted[0]["payload"])
check("a later run diffs against the latest stored snapshot (zero drift "
      "here: same catalog)",
      second == "TSDS-00001"
      and second_payload["drift_vs_previous"]["available"] is True
      and second_payload["drift_vs_previous"]["catalog_total_delta"] == 0)
frappe_tenant = build_frappe(app_role="tenant")
check("control hub only: a tenant/other bench run is a no-op",
      load_glue(frappe_tenant, CARDS).run_suitability_drift_report() is None
      and frappe_tenant.inserted == [])
frappe_same_day = build_frappe(existing_run=True)
check("idempotent per run date: a same-day re-run stores nothing",
      load_glue(frappe_same_day, CARDS).run_suitability_drift_report() is None
      and frappe_same_day.inserted == [])
frappe_cold = build_frappe()
check("a cold/empty catalog cache stores nothing (an all-zero snapshot "
      "would read as drift)",
      load_glue(frappe_cold, []).run_suitability_drift_report() is None
      and frappe_cold.inserted == [])

# --------------------------------------------------------------------------
# (i) wiring: doctype schema + weekly schedule
# --------------------------------------------------------------------------
print("== (i) wiring ==")
with open(os.path.join(
        SRC, "doctype/tender_suitability_drift_snapshot/"
        "tender_suitability_drift_snapshot.json"), encoding="utf-8") as f:
    snapshot_dt = json.load(f)
fields = {fld["fieldname"]: fld for fld in snapshot_dt["fields"]}
check("Tender Suitability Drift Snapshot doctype carries the snapshot "
      "schema (run_on + summary ints + JSON payload + semantics), "
      "module tender",
      snapshot_dt["module"] == "tender"
      and {"run_on", "catalog_total", "full_records", "advert_only_records",
           "profiles_scored", "payload", "semantics"} <= set(fields)
      and fields["payload"]["fieldtype"] == "Code"
      and fields["payload"].get("options") == "JSON"
      and fields["run_on"]["fieldtype"] == "Date")
check("snapshot fields are read-only state (all computation lives in "
      "the pure module)",
      all(fields[f].get("read_only") == 1 for f in
          ("run_on", "catalog_total", "payload", "semantics")))
with open(MANIFEST, encoding="utf-8") as f:
    manifest = json.load(f)
scheduler = manifest["app_type"]["control"]["hooks"]["scheduler_events"]
check("run_suitability_drift_report is scheduled WEEKLY in the module "
      "manifest, beside the artifact-expiry sweep",
      "{app_name}.tender.control.drift_report.run_suitability_drift_report"
      in scheduler.get("weekly", []))
glue_src = open(os.path.join(SRC, "drift_report.py")).read()
check("the glue is persistence-only per the renewal_sync pattern "
      "(control guard, cached catalog in, snapshot doc out - no scoring "
      "logic of its own)",
      'frappe.conf.get("app_role") != "control"' in glue_src
      and "drift_snapshot(" in glue_src and "compare_snapshots(" in glue_src
      and "def score" not in glue_src)

# --------------------------------------------------------------------------
print()
passed = sum(1 for _, ok in checks if ok)
print(f"{passed}/{len(checks)} checks passed")
sys.exit(0 if passed == len(checks) else 1)
