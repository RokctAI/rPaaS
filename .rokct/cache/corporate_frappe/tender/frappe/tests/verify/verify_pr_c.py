#!/usr/bin/env python3
"""Standalone verification for PR-C (F-11 buyer quirks, per-buyer returnable
seeding, template-code + pricing-reconciliation lints, F-13 email dispatch).

frappe fully stubbed in-memory; the real modules/fixtures are loaded from
the repo (endpoints exec'd with the composer {app_name} placeholder
substituted). Proves:

F-11: every QUIRK-* fixture rule fires on its documented buyer's context
      ONLY (RNM / DFFE / VCW / Musina; none for advert-only TWK), flows
      into checklist rows, and ships its machine constants in params.
Seeding: seed_bid_returnables returns the most recent prior same-buyer
      bid's captured list; preview NEVER modifies the bid; apply=1 appends
      with ref_code dedupe; no-prior and no-institution paths.
Lints: unmatched template_code warning fires (worksheet still renders);
      pricing reconciliation catches monthly x 12 != annual, a fixed-total
      vs cover-price mismatch, and escalation-set-but-flat; silent on a
      clean escalated grid; SECTIONED-NO-SECTIONS behaviour unchanged.
F-13: dispatch_bid_pack refuses without retyped confirmation / email-
      allowed channel / clean gates; full-pack mode sends via mocked
      sendmail with the pack attached and writes the audit fields;
      correspondence mode needs no channel/gates and never attaches;
      sendmail failure degrades gracefully with no audit write.
Regression: manifest cmd families registered, doctype options additive,
      cover Delivery line only when a channel is captured.
"""

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
utils_stub.nowdate = lambda: "2026-08-20"
utils_stub.now = lambda: "2026-08-20 12:00:00"
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
frappe_stub.get_traceback = lambda: "traceback"
frappe_stub.msgprint = lambda *a, **k: None
frappe_stub.get_all = lambda *a, **k: []
frappe_stub.get_doc = lambda *a, **k: None
frappe_stub.db = types.SimpleNamespace(
    get_value=lambda *a, **k: None,
    exists=lambda *a, **k: False,
    get_single_value=lambda *a, **k: 0,
    commit=lambda: None,
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


rules = load_module("c_rules", os.path.join(SRC, "compliance/rules.py"))
pack_lints = load_module("c_pack_lints", os.path.join(SRC, "compliance/pack_lints.py"))
gate = load_module("c_submission_gate", os.path.join(SRC, "compliance/submission_gate.py"))
checklist_mod = load_module("c_checklist", os.path.join(SRC, "compliance/checklist.py"))
pack_builder = load_module("c_pack_builder", os.path.join(SRC, "pack_builder.py"))

with open(os.path.join(FIXTURES, "tender_compliance_rules.json"), encoding="utf-8") as f:
    ALL_RULES = json.load(f)
RULES = {r["rule_code"]: r for r in ALL_RULES}
QUIRKS = [r for r in ALL_RULES if r["rule_code"].startswith("QUIRK-")]


class FakeBid(dict):
    def __getattr__(self, key):
        return self.get(key)


# --------------------------------------------------------------------------
# F-11: quirk rules fire on their documented buyers and stay off others
# --------------------------------------------------------------------------
print("== F-11: QUIRK-* rules fire per buyer, off everywhere else ==")
CONTEXTS = {
    "RNM": rules.bid_context({"regime": "MBD", "estimated_value": 42500000,
        "institution": "Ray Nkonyeni Local Municipality",
        "tender_title": "Construction of Mgodlwa Bridge in Ward 8"}),
    "DFFE": rules.bid_context({"regime": "SBD", "estimated_value": 2737000,
        "institution": "Department of Forestry, Fisheries and the Environment",
        "tender_title": "Determination of the state of forests in South Africa"}),
    "VCW": rules.bid_context({"regime": "SBD", "estimated_value": 168000000,
        "institution": "Vaal Central Water",
        "tender_title": "Total Security Solution"}),
    "MUSINA": rules.bid_context({"regime": "MBD", "estimated_value": 2573750,
        "institution": "Musina Local Municipality",
        "tender_title": "Helpdesk Management System"}),
    "TWK": rules.bid_context({"regime": "MBD", "estimated_value": 2179056,
        "institution": "Theewaterskloof Municipality",
        "tender_title": "Hosting of a Website"}),
    "NONE": rules.bid_context({"regime": "MBD"}),
}

check("12 QUIRK-* rules shipped, all rule_class 'Buyer Quirk', Conditional, "
      "with checklist text and an institution_matches trigger",
      len(QUIRKS) == 12
      and all(q["rule_class"] == "Buyer Quirk" and q["scope"] == "Conditional"
              and q["checklist_text"]
              and "institution_matches" in json.loads(q["trigger_condition"])
              for q in QUIRKS))

expected_fire = {
    "QUIRK-RNM-INK": "RNM", "QUIRK-RNM-LOCALITY": "RNM",
    "QUIRK-DFFE-MASTERDOC": "DFFE",
    "QUIRK-VCW-PRICEBAND": "VCW", "QUIRK-VCW-ROTATION": "VCW",
    "QUIRK-VCW-INSPECTION": "VCW",
    "QUIRK-MUSINA-PAGEINIT": "MUSINA", "QUIRK-MUSINA-ATTACH-ORDER": "MUSINA",
    "QUIRK-MUSINA-WHOLE-DOC": "MUSINA", "QUIRK-MUSINA-BOX-HOURS": "MUSINA",
    "QUIRK-MUSINA-WRITTEN-QUERIES": "MUSINA", "QUIRK-MUSINA-TOLLFREE": "MUSINA",
}
matrix_ok = sorted(expected_fire) == sorted(q["rule_code"] for q in QUIRKS)
for code, owner in expected_fire.items():
    for key, ctx in CONTEXTS.items():
        applies = rules.rule_applies(RULES[code], ctx)
        if applies != (key == owner):
            matrix_ok = False
            print(f"   MISMATCH {code} on {key}: applies={applies}")
check("fire matrix exact: each quirk fires on its own buyer's context ONLY "
      "(incl. off TWK and off a no-institution bid)", matrix_ok)
check("no quirk encoded for advert-only-grounded TWK",
      not [q for q in QUIRKS if "TWK" in q["rule_code"] or "THEEWATER" in q["rule_code"]])

sev = {q["rule_code"]: q["severity"] for q in QUIRKS}
check("severities per pack language: INK/MASTERDOC/PRICEBAND/INSPECTION/"
      "PAGEINIT/WHOLE-DOC Fatal; LOCALITY/ROTATION Points-only; rest Curable",
      all(sev[c] == "Fatal" for c in ("QUIRK-RNM-INK", "QUIRK-DFFE-MASTERDOC",
          "QUIRK-VCW-PRICEBAND", "QUIRK-VCW-INSPECTION",
          "QUIRK-MUSINA-PAGEINIT", "QUIRK-MUSINA-WHOLE-DOC"))
      and all(sev[c] == "Points-only" for c in ("QUIRK-RNM-LOCALITY", "QUIRK-VCW-ROTATION"))
      and all(sev[c] == "Curable" for c in ("QUIRK-MUSINA-ATTACH-ORDER",
          "QUIRK-MUSINA-BOX-HOURS", "QUIRK-MUSINA-WRITTEN-QUERIES",
          "QUIRK-MUSINA-TOLLFREE")))

check("machine constants in params: VCW band 20% / rotation R250m / "
      "inspection 75%, RNM goal table 10/5/1, RNM 2 copies, Musina box hours",
      json.loads(RULES["QUIRK-VCW-PRICEBAND"]["params"])["tolerance_pct"] == 20
      and json.loads(RULES["QUIRK-VCW-ROTATION"]["params"])["rotation_threshold_rand"] == 250000000
      and json.loads(RULES["QUIRK-VCW-INSPECTION"]["params"])["inspection_threshold_pct"] == 75
      and [g[1] for g in json.loads(RULES["QUIRK-RNM-LOCALITY"]["params"])["goal_table"]] == [10, 5, 1]
      and json.loads(RULES["QUIRK-RNM-INK"]["params"])["copies_required"] == 2
      and json.loads(RULES["QUIRK-MUSINA-BOX-HOURS"]["params"])["box_hours"] == "07:30-16:00")

# quirks flow into checklist rows through the untouched engine
frappe_stub.get_all = lambda doctype, filters=None, fields=None, **k: [
    dict(r) for r in ALL_RULES if doctype == "Tender Compliance Rule"
]
musina_bid = FakeBid(regime="MBD", estimated_value=2573750,
                     institution="Musina Local Municipality")
rows = checklist_mod.compliance_checklist_rows(musina_bid)
row_codes = {r["rule_code"] for r in rows}
check("Musina bid checklist gains all 6 Musina quirk rows via the existing "
      "sync (zero engine change) and no other buyer's quirks",
      {c for c in row_codes if c.startswith("QUIRK-")}
      == {c for c, o in expected_fire.items() if o == "MUSINA"})
frappe_stub.get_all = lambda *a, **k: []

check("rule counts: 20/25/7/3/2/12, total 69; doctype rule_class options "
      "additive (all six prior options kept + Buyer Quirk)",
      len(ALL_RULES) == 69
      and (lambda opts: all(o in opts for o in (
          "Registration Gate", "Disqualification Cause", "Form Rule",
          "Pricing Rule", "Submission Rule", "Scoring Rule", "Buyer Quirk")))(
          json.load(open(os.path.join(
              SRC, "doctype/tender_compliance_rule/tender_compliance_rule.json")))
          ["fields"][2]["options"].split("\n")))

# --------------------------------------------------------------------------
# Lints: unmatched template_code
# --------------------------------------------------------------------------
print("== lint: unmatched template_code named, worksheet still renders ==")
with open(os.path.join(FIXTURES, "tender_form_templates.json"), encoding="utf-8") as f:
    TEMPLATES = {t["template_code"]: t for t in json.load(f)}

typo_rows = [
    {"ref_code": "Form A", "title": "Form of Bid", "template_code": "MBD44"},
    {"ref_code": "Form B", "title": "Signatory Authorisation", "template_code": "MBD4"},
    {"ref_code": "5.1(c)", "title": "Project plan"},
]
warns = pack_lints.unmatched_template_code_warnings(typo_rows, TEMPLATES.keys())
check("typo'd code warned once, naming ref + code; valid and blank codes silent",
      len(warns) == 1 and "Form A" in warns[0] and "MBD44" in warns[0]
      and pack_lints.UNMATCHED_TEMPLATE_TAG in warns[0])
check("unknown template list (None) stays silent instead of mass-flagging",
      pack_lints.unmatched_template_code_warnings(typo_rows, None) == [])
check("matching is case-insensitive on the stripped code",
      pack_lints.unmatched_template_code_warnings(
          [{"ref_code": "X", "template_code": " mbd4 "}], TEMPLATES.keys()) == [])

# the worksheet still renders template-less (behaviour unchanged)
gbp = load_endpoint("c_gbp", "api/tenders/generate_bid_pack.py")
form = pack_builder.build_form(
    gbp._custom_returnable_row(FakeBid(ref_code="Form A", title="Form of Bid",
                                       mandatory=1, template_code="MBD44")),
    TEMPLATES.get("MBD44"), {}, {})
check("unmatched-code returnable still renders the guided template-less page",
      form["has_template"] is False and form["form_name"] == "Form of Bid")

# surfaced via submission_readiness_warnings and the pack cover
lint_bid = FakeBid(custom_returnables=typo_rows)
gate_warns = gate.submission_readiness_warnings(lint_bid, template_codes=TEMPLATES.keys())
check("surfaced via submission_readiness_warnings",
      len(gate_warns) == 1 and "MBD44" in gate_warns[0])
ctx = {"bid_name": "BID-1", "generated_on": "2026-08-20"}
pack = pack_builder.build_pack({"regime_code": "MBD", "regime_name": "x", "forms": []},
                               TEMPLATES, {}, ctx, [], None, gate_warns)
html = pack_builder.render_pack_html(pack, ctx)
check("unmatched code named on the pack cover via extra_warnings",
      "MBD44" in pack["manifest"]["warnings"][-1] and "MBD44" in html)

# --------------------------------------------------------------------------
# Lints: pricing reconciliation
# --------------------------------------------------------------------------
print("== lint: pricing grid reconciliation ==")
mismatch = [{"period_label": "Year 1", "monthly": 10000, "annual_total": 125000}]
w = pack_lints.pricing_reconciliation_warnings(mismatch)
check("monthly x 12 != annual caught (R125,000.00 vs R120,000.00)",
      len(w) == 1 and pack_lints.ANNUAL_MISMATCH_TAG in w[0] and "Year 1" in w[0])

w = pack_lints.pricing_reconciliation_warnings(
    [{"period_label": "Year 1", "annual_total": 1000000},
     {"period_label": "Year 2", "annual_total": 1000000},
     {"period_label": "Call tariff", "unit_tariff": 350}],
    cover_price=2573750)
check("fixed-portion total vs cover price mismatch caught (unit tariffs excluded)",
      len(w) == 1 and pack_lints.COVER_MISMATCH_TAG in w[0]
      and "2,000,000.00" in w[0] and "2,573,750.00" in w[0])

w = pack_lints.pricing_reconciliation_warnings(
    [{"period_label": "Year 1", "monthly": 10000, "annual_total": 120000},
     {"period_label": "Year 2", "monthly": 10000, "annual_total": 120000},
     {"period_label": "Year 3", "monthly": 10000, "annual_total": 120000}],
    cover_price=360000, escalation_rate_pct=5)
check("escalation recorded but not applied caught (flat grid + 5% rate)",
      len(w) == 1 and pack_lints.ESCALATION_FLAT_TAG in w[0])

clean = [
    {"period_label": "Year 1", "once_off": 50000, "monthly": 10000, "annual_total": 120000},
    {"period_label": "Year 2", "monthly": 10500, "annual_total": 126000},
    {"period_label": "Year 3", "monthly": 11025, "annual_total": 132300},
    {"period_label": "Per-unit call tariff", "unit_tariff": 350, "unit_label": "per logged call"},
]
check("silent on a clean escalated grid that reconciles to its cover price",
      pack_lints.pricing_reconciliation_warnings(
          clean, cover_price=428300, escalation_rate_pct=5) == [])
check("rounding tolerance: a 50c difference does not warn",
      pack_lints.pricing_reconciliation_warnings(
          [{"period_label": "Y1", "monthly": 1000.04, "annual_total": 12000}]) == [])
check("no data, no warnings (empty grid, no cover, no rate)",
      pack_lints.pricing_reconciliation_warnings([]) == []
      and pack_lints.pricing_reconciliation_warnings(None) == [])

# through the gate, with the cover price read from the soft-linked Quotation
frappe_stub.db.exists = lambda doctype, name=None: True
frappe_stub.db.get_value = lambda doctype, name, field: 2600000
recon_bid = FakeBid(quotation="SAL-QTN-0001",
                    pricing_periods=[{"period_label": "Year 1", "annual_total": 1000000},
                                     {"period_label": "Year 2", "annual_total": 1000000}],
                    escalation_rate_pct=5)
gw = gate.submission_readiness_warnings(recon_bid, template_codes=[])
check("gate surfaces cover-price mismatch (quotation total R2.6m vs grid R2m) "
      "AND the flat-escalation warning",
      any(pack_lints.COVER_MISMATCH_TAG in x for x in gw)
      and any(pack_lints.ESCALATION_FLAT_TAG in x for x in gw) and len(gw) == 2)
frappe_stub.db.exists = lambda *a, **k: False
frappe_stub.db.get_value = lambda *a, **k: None

check("SECTIONED-NO-SECTIONS behaviour unchanged (exact single warning)",
      gate.submission_readiness_warnings(FakeBid(functionality_mode="Sectioned"))
      == [gate.SECTIONED_NO_SECTIONS_WARNING]
      and gate.submission_readiness_warnings(FakeBid()) == [])

# --------------------------------------------------------------------------
# Per-buyer returnable seeding
# --------------------------------------------------------------------------
print("== seeding: prior same-buyer returnables, preview-only by default ==")


class FakeBidDoc(dict):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.saved = 0
        self.appended = []

    def __getattr__(self, key):
        return self.get(key)

    def append(self, table, row):
        self.setdefault(table, []).append(dict(row))
        self.appended.append((table, dict(row)))

    def save(self, ignore_permissions=False):
        self.saved += 1

    def db_set(self, field, value):
        self[field] = value
        self.setdefault("_db_set", []).append((field, value))


MUSINA_ROWS = [
    {"ref_code": "Form A", "title": "Form of Bid", "mandatory": 1,
     "category": "Buyer Form", "kill_note": "Failure to complete this document "
     "will result in the whole bid document being rejected",
     "template_code": None, "guidance": None},
    {"ref_code": "Form B", "title": "Signatory Authorisation", "mandatory": 1,
     "category": "Buyer Form", "kill_note": None, "template_code": None,
     "guidance": None},
    {"ref_code": "Form C", "title": "Declaration of Interest (legacy HDI)",
     "mandatory": 1, "category": "Legacy Preference Form", "kill_note": None,
     "template_code": None, "guidance": None},
]

new_bid = FakeBidDoc(name="BID-2", user="desk@example.com",
                     institution="Musina Local Municipality")
old_bid_empty = FakeBidDoc(name="BID-9", user="desk@example.com",
                           institution="Musina Local Municipality")
old_bid = FakeBidDoc(name="BID-1", user="desk@example.com",
                     institution="Musina Local Municipality",
                     tender_title="Helpdesk Management System",
                     custom_returnables=[dict(r) for r in MUSINA_ROWS])

DOCS = {"BID-1": old_bid, "BID-2": new_bid, "BID-9": old_bid_empty}
get_all_calls = []


def seed_get_all(doctype, filters=None, fields=None, order_by=None, **k):
    get_all_calls.append((doctype, filters, order_by))
    assert doctype == "Tender Bid"
    assert filters["user"] == "desk@example.com"
    assert filters["name"] == ["!=", "BID-2"]
    assert order_by == "modified desc"
    if filters["institution"] != "Musina Local Municipality":
        return []
    return [{"name": "BID-9"}, {"name": "BID-1"}]  # most recent first: empty one


frappe_stub.get_all = seed_get_all
frappe_stub.get_doc = lambda doctype, name: DOCS[name]

ent_stub = types.ModuleType("_app_stub.tender.control.api.tenders.tender_entitlement")
ent_stub.get_owned_bid = lambda name: DOCS[name]
for mod_name in ("_app_stub", "_app_stub.tender", "_app_stub.tender.control",
                 "_app_stub.tender.control.api", "_app_stub.tender.control.api.tenders",
                 "_app_stub.tender.control.compliance"):
    sys.modules.setdefault(mod_name, types.ModuleType(mod_name))
sys.modules["_app_stub.tender.control.api.tenders.tender_entitlement"] = ent_stub

seed = load_endpoint("c_seed", "api/tenders/seed_bid_returnables.py")

preview = seed.seed_bid_returnables("BID-2")
check("preview returns the most recent prior bid WITH rows (skipping the more "
      "recent row-less bid) and all 3 captured rows in order",
      preview["source_bid"] == "BID-1"
      and [r["ref_code"] for r in preview["rows"]] == ["Form A", "Form B", "Form C"]
      and preview["rows"][0]["kill_note"].startswith("Failure to complete")
      and preview["applied"] == 0)
check("preview NEVER modifies the bid (no rows appended, no save)",
      new_bid.appended == [] and new_bid.saved == 0
      and not new_bid.get("custom_returnables"))
check("preview carries the verify-against-this-pack note",
      "STARTING POINT" in preview["note"])

# opt-in apply, with a pre-existing row deduped by ref_code
new_bid["custom_returnables"] = [{"ref_code": "form a", "title": "Already captured"}]
applied = seed.seed_bid_returnables("BID-2", apply=1)
check("apply=1 appends only the missing rows (ref_code dedupe, normalized) "
      "and saves once",
      applied["applied"] == 2 and new_bid.saved == 1
      and [r["ref_code"] for r in new_bid["custom_returnables"]]
      == ["form a", "Form B", "Form C"])
check("serialized rows carry only capture fields, never child-row identity",
      all(set(r.keys()) == set(seed.RETURNABLE_FIELDS) for r in preview["rows"]))

no_prior = FakeBidDoc(name="BID-2", user="desk@example.com",
                      institution="Vaal Central Water")
DOCS_SAVE = DOCS.copy()
ent_stub.get_owned_bid = lambda name: no_prior
res = seed.seed_bid_returnables("BID-2")
check("no prior same-buyer bid with rows -> source_bid None, empty rows, note",
      res["source_bid"] is None and res["rows"] == [] and res["applied"] == 0)

no_inst = FakeBidDoc(name="BID-3", user="desk@example.com")
ent_stub.get_owned_bid = lambda name: no_inst
try:
    seed.seed_bid_returnables("BID-3")
    check("bid without institution refused", False)
except Thrown as e:
    check("bid without institution refused", "No Buyer On Bid" in str(e))
ent_stub.get_owned_bid = lambda name: DOCS_SAVE[name]

# --------------------------------------------------------------------------
# F-13: dispatch endpoint
# --------------------------------------------------------------------------
print("== F-13: dispatch_bid_pack gating, send, audit ==")
sg_stub = types.ModuleType("_app_stub.tender.control.compliance.submission_gate")
GATE_FAILURES = []
sg_stub.validate_submission_readiness = lambda bid: list(GATE_FAILURES)
sys.modules["_app_stub.tender.control.compliance.submission_gate"] = sg_stub

gbp_stub = types.ModuleType("_app_stub.tender.control.api.tenders.generate_bid_pack")
gbp_stub.generate_bid_pack = lambda bid, sign=0: {
    "manifest": {"bid": bid, "form_count": 12},
    "html": "<!DOCTYPE html><html>PACK</html>",
}
# the real module also exports load_profile (dispatch reads it to decide
# signed vs unsigned); no profile here -> the original unsigned path, so
# every PR-C expectation below is unchanged
gbp_stub.load_profile = lambda user: (None, {})
sys.modules["_app_stub.tender.control.api.tenders.generate_bid_pack"] = gbp_stub

sent = []


def fake_sendmail(recipients=None, subject=None, message=None, attachments=None):
    sent.append({"recipients": recipients, "subject": subject,
                 "message": message, "attachments": attachments})


frappe_stub.sendmail = fake_sendmail

# dispatch now sends through the REAL notification seam (plan #14): register
# the real notify.py under the stub root so the endpoint exercises the seam
# end-to-end; frappe.sendmail stays the mocked transport underneath, so
# every dispatch expectation below doubles as call-site equivalence proof.
sys.modules["_app_stub.tender.control.notify"] = load_module(
    "c_notify", os.path.join(SRC, "notify.py"))

dispatch = load_endpoint("c_dispatch", "api/tenders/dispatch_bid_pack.py")

BID = FakeBidDoc(name="BID-7", user="desk@example.com",
                 tender_slug="18-2025-26", tender_title="Helpdesk Management System",
                 institution="Musina Local Municipality",
                 buyer_contact_person="Mrs. R.M. Siziba",
                 buyer_contact_email="scm@example.gov.za")
ent_stub.get_owned_bid = lambda name: BID


def throws(fn, needle):
    try:
        fn()
        return False
    except Thrown as e:
        return needle in str(e)


check("refused without the retyped confirmation (correspondence mode)",
      throws(lambda: dispatch.dispatch_bid_pack("BID-7", mode="correspondence",
                                                message="Written query"),
             "Destination Not Confirmed") and sent == [])
check("refused on a MISMATCHED confirmation",
      throws(lambda: dispatch.dispatch_bid_pack("BID-7", mode="pack",
                                                confirm_email="wrong@example.gov.za"),
             "Destination Not Confirmed") and sent == [])
check("pack mode refused while submission_channel is blank/physical",
      throws(lambda: dispatch.dispatch_bid_pack("BID-7", mode="pack",
                                                confirm_email="scm@example.gov.za"),
             "Channel Does Not Allow Email Submission"))
BID["submission_channel"] = "Physical tender box"
check("pack mode refused on 'Physical tender box' too",
      throws(lambda: dispatch.dispatch_bid_pack("BID-7", mode="pack",
                                                confirm_email="scm@example.gov.za"),
             "Channel Does Not Allow Email Submission"))

BID["submission_channel"] = "Email allowed"
GATE_FAILURES[:] = ["Fatal checklist item still open: CSD report [GATE-CSD]"]
check("pack mode refused while fatal gates are open (hard gate, not a setting)",
      throws(lambda: dispatch.dispatch_bid_pack("BID-7", mode="pack",
                                                confirm_email="scm@example.gov.za"),
             "Submission Gates Open") and sent == [])

GATE_FAILURES[:] = []
result = dispatch.dispatch_bid_pack("BID-7", mode="pack",
                                    confirm_email="scm@example.gov.za")
check("full-pack mode sends via sendmail with pack HTML + manifest attached",
      len(sent) == 1 and sent[0]["recipients"] == ["scm@example.gov.za"]
      and len(sent[0]["attachments"]) == 2
      and sent[0]["attachments"][0]["fname"] == "BID-7-bid-pack.html"
      and "PACK" in sent[0]["attachments"][0]["fcontent"]
      and json.loads(sent[0]["attachments"][1]["fcontent"])["form_count"] == 12)
check("audit fields written and returned (dispatched_on/dispatched_to)",
      result["sent"] is True and result["pack_attached"] is True
      and BID["dispatched_to"] == "scm@example.gov.za"
      and BID["dispatched_on"] == "2026-08-20 12:00:00"
      and ("dispatched_on", "2026-08-20 12:00:00") in BID["_db_set"])
check("confirmation is whitespace/case tolerant but nothing else",
      dispatch.normalize_email("  SCM@Example.GOV.za ") == "scm@example.gov.za"
      and dispatch.normalize_email("scm@example.gov") != "scm@example.gov.za")

# correspondence: no channel/gate requirement, never attaches
BID2 = FakeBidDoc(name="BID-8", user="desk@example.com",
                  tender_slug="vcw403", tender_title="Total Security Solution",
                  buyer_contact_email="bids@vcwater.example")
ent_stub.get_owned_bid = lambda name: BID2
GATE_FAILURES[:] = ["open gate"]  # gates open, channel blank - still fine
result2 = dispatch.dispatch_bid_pack(
    "BID-8", mode="correspondence", confirm_email="bids@vcwater.example",
    subject="Clarification question", message="Please confirm the briefing venue.")
check("correspondence mode works with gates open and no channel, and NEVER "
      "attaches the pack",
      result2["sent"] is True and result2["pack_attached"] is False
      and len(sent) == 2 and sent[1]["attachments"] is None
      and sent[1]["message"] == "Please confirm the briefing venue.")
check("correspondence refused without a message body",
      throws(lambda: dispatch.dispatch_bid_pack("BID-8", mode="correspondence",
                                                confirm_email="bids@vcwater.example"),
             "No Message"))
check("unknown mode refused",
      throws(lambda: dispatch.dispatch_bid_pack("BID-8", mode="both",
                                                confirm_email="bids@vcwater.example"),
             "Invalid Mode"))

# graceful degradation: sendmail raising (no Email Account) -> no audit write
BID3 = FakeBidDoc(name="BID-9", user="desk@example.com",
                  buyer_contact_email="x@example.gov.za")
ent_stub.get_owned_bid = lambda name: BID3


def broken_sendmail(**kwargs):
    raise RuntimeError("no outgoing email account")


frappe_stub.sendmail = broken_sendmail
logged = []
frappe_stub.log_error = lambda tb, title: logged.append(title)
result3 = dispatch.dispatch_bid_pack(
    "BID-9", mode="correspondence", confirm_email="x@example.gov.za",
    message="test")
check("sendmail failure degrades gracefully: sent=False, reason returned, "
      "failure logged, NO audit fields written",
      result3["sent"] is False and "Email Account" in result3["reason"]
      and logged == ["Bid Pack Dispatch Failed"]
      and "dispatched_on" not in BID3 and "dispatched_to" not in BID3)
frappe_stub.sendmail = fake_sendmail

BID4 = FakeBidDoc(name="BID-10", user="desk@example.com")  # no contact email
ent_stub.get_owned_bid = lambda name: BID4
check("refused without a captured buyer contact email",
      throws(lambda: dispatch.dispatch_bid_pack("BID-10", mode="correspondence",
                                                confirm_email="", message="x"),
             "No Buyer Contact Email"))
ent_stub.get_owned_bid = lambda name: BID

frappe_stub.conf = {"app_role": "tenant"}
check("non-control role refused",
      throws(lambda: dispatch.dispatch_bid_pack("BID-7"), "Action Not Allowed"))
frappe_stub.conf = {"app_role": "control"}

# --------------------------------------------------------------------------
# F-13: cover delivery line + regression
# --------------------------------------------------------------------------
print("== F-13: cover delivery line; manifest registrations ==")
ctx_channel = {"bid_name": "BID-7", "generated_on": "2026-08-20",
               "submission_channel": "Physical tender box"}
pack7 = pack_builder.build_pack({"regime_code": "MBD", "regime_name": "x", "forms": []},
                                TEMPLATES, {}, ctx_channel, [])
html7 = pack_builder.render_pack_html(pack7, ctx_channel)
check("cover renders 'Delivery: Physical tender box' when the channel is captured",
      "<b>Delivery:</b> Physical tender box" in html7)
ctx_none = {"bid_name": "BID-7", "generated_on": "2026-08-20"}
ctx_blank = dict(ctx_none, submission_channel=None)
check("no channel -> no delivery line, byte-identical output for absent vs None",
      "Delivery:" not in pack_builder.render_pack_html(
          pack_builder.build_pack({"regime_code": "MBD", "regime_name": "x",
                                   "forms": []}, TEMPLATES, {}, ctx_none, []), ctx_none)
      and pack_builder.render_pack_html(
          pack_builder.build_pack({"regime_code": "MBD", "regime_name": "x",
                                   "forms": []}, TEMPLATES, {}, ctx_none, []), ctx_none)
      == pack_builder.render_pack_html(
          pack_builder.build_pack({"regime_code": "MBD", "regime_name": "x",
                                   "forms": []}, TEMPLATES, {}, ctx_blank, []), ctx_blank))

with open(os.path.join(REPO, "tender/frappe/manifest.json"), encoding="utf-8") as f:
    manifest = json.load(f)
methods = manifest["app_type"]["control"]["hooks"]["whitelisted_methods"]
check("manifest registers seed_bid_returnables + dispatch_bid_pack in all "
      "three cmd families, app_type.control only",
      all(key in methods for key in (
          "{app_name}.api.tenders.seed_bid_returnables",
          "control:seed_bid_returnables",
          "control.control.api.tenders.seed_bid_returnables",
          "{app_name}.api.tenders.dispatch_bid_pack",
          "control:dispatch_bid_pack",
          "control.control.api.tenders.dispatch_bid_pack"))
      and manifest["app_type"]["tenant"] == {})

bid_json = json.load(open(os.path.join(SRC, "doctype/tender_bid/tender_bid.json")))
fieldnames = [f["fieldname"] for f in bid_json["fields"]]
check("Tender Bid carries the 5 new F-13 fields (channel select gated on "
      "'Email allowed'; audit fields read-only), all prior fields intact",
      all(f in fieldnames for f in ("submission_channel", "buyer_contact_person",
          "buyer_contact_email", "dispatched_on", "dispatched_to"))
      and all(f in fieldnames for f in ("regime", "overlay_regime",
          "custom_returnables", "pricing_periods", "functionality_sections",
          "checklist"))
      and [f for f in bid_json["fields"] if f["fieldname"] == "submission_channel"][0]
          ["options"] == "\nPhysical tender box\nPortal upload\nEmail allowed"
      and all([f for f in bid_json["fields"] if f["fieldname"] == name][0]
              .get("read_only") == 1 for name in ("dispatched_on", "dispatched_to")))

# --------------------------------------------------------------------------
failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL PR-C CHECKS PASSED")
