#!/usr/bin/env python3
"""Standalone O-04 end-to-end smoke - the F-15(b) studio hook driven with
REAL engine-generated artifacts (findings doc, "Open items for the
builder", O-04; committed to tests/verify/ per O-06's rule).

The hook shipped in PRs #45/#46 (tender_bid_returnable artifact fields,
attach_returnable_artifact attach->attest, the
[RETURNABLE-ARTIFACT-UNATTESTED] readiness gate, the pack worksheet's
GENERATE VIA STUDIO / SATISFIED BY GENERATED ARTIFACT states) had only
ever been exercised with synthetic files. This smoke runs the whole loop
through the REAL modules, end to end on ONE bid:

1. capture two "Company Profile"-class returnables with a studio_scope and
   no artifact -> the worksheet renders the GENERATE VIA STUDIO pointer and
   readiness opens NO gate (the attestation gate is additive: it fires only
   once a generated_artifact is attached - that is what the code does, and
   what this suite asserts);
2. attach the engine-generated business_profile.md + compliance_log.md via
   the attach_returnable_artifact endpoint logic (unattested first) ->
   validate_submission_readiness fails with
   [RETURNABLE-ARTIFACT-UNATTESTED] per row, and the worksheet renders
   SATISFIED BY GENERATED ARTIFACT with the NOT YET ATTESTED caveat;
3. attest -> the gate clears, the caveat drops, the hand-fill placeholder
   stays suppressed, the manifest carries generated+attested;
4. regression guard: rows without the hook fields still render
   byte-identically to the no-hook baseline, and detach returns the
   worksheet byte-identically to the pre-attach pointer state.

REAL-FILES MODE: set O4_BUSINESS_PROFILE and O4_COMPLIANCE_LOG to the two
files a `startupos compile --only business_profile` run produced (engine:
RokctAI/The-Rokct-Protocol core/utils/startup_os, the studio manifest's
pinned SHA af85e32). With no evidence uploaded they carry the engine's
honest "Pending — ..." markers - expected and fine: the smoke tests the
attach/attest mechanics, not document completeness. The real files are
deliberately NOT committed; without the env vars the suite falls back to
the small committed stand-ins in data/ (clearly marked SYNTHETIC) and the
engine-provenance checks print SKIP lines instead - mirroring
verify_pr_e.py's real-PDF honesty. Both modes must be all green.
"""

import importlib.util
import os
import sys
import types

# O-05: in-tree suite runs must leave no __pycache__ litter under src/
sys.dont_write_bytecode = True

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SRC = os.path.join(REPO, "tender/frappe/src/control")
HERE = os.path.dirname(os.path.abspath(__file__))

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


# --------------------------------------------------------------------------
# frappe stub (same shape as verify_pr_e.py - endpoints only)
# --------------------------------------------------------------------------
class Thrown(Exception):
    pass


frappe_stub = types.ModuleType("frappe")
utils_stub = types.ModuleType("frappe.utils")
utils_stub.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
utils_stub.flt = lambda v, precision=None: float(v) if v not in (None, "") else 0.0
utils_stub.nowdate = lambda: "2026-08-21"
utils_stub.getdate = lambda v=None: v
utils_stub.now = lambda: "2026-08-21 12:00:00"
frappe_stub.utils = utils_stub


def _throw(msg, exc=None, title=None):
    raise Thrown(f"{title or ''}: {msg}")


frappe_stub.throw = _throw
frappe_stub.whitelist = lambda *a, **k: (lambda f: f)
frappe_stub.PermissionError = Thrown
frappe_stub.conf = {"app_role": "control"}
frappe_stub.session = types.SimpleNamespace(user="desk@example.com")
frappe_stub.local = types.SimpleNamespace(request=None)
frappe_stub.get_request_header = lambda *a, **k: None
frappe_stub.msgprint = lambda *a, **k: None
frappe_stub.get_all = lambda *a, **k: []
frappe_stub.get_doc = lambda *a, **k: None
frappe_stub.log_error = lambda *a, **k: None
frappe_stub.get_traceback = lambda: "traceback"
frappe_stub.sendmail = lambda **k: None
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
    path = os.path.join(SRC, relpath)
    with open(path, encoding="utf-8") as f:
        source = f.read().replace("{app_name}", stub_root)
    module = types.ModuleType(name)
    module.__file__ = path
    exec(compile(source, path, "exec"), module.__dict__)
    return module


def throws(fn, needle):
    try:
        fn()
        return False
    except Thrown as e:
        return needle in str(e)


pack_lints = load_module("o4_pack_lints", os.path.join(SRC, "compliance/pack_lints.py"))
gate = load_module("o4_submission_gate", os.path.join(SRC, "compliance/submission_gate.py"))
pack_builder = load_module("o4_pack_builder", os.path.join(SRC, "pack_builder.py"))

for mod_name in ("_app_stub", "_app_stub.tender", "_app_stub.tender.control",
                 "_app_stub.tender.control.api", "_app_stub.tender.control.api.tenders"):
    sys.modules.setdefault(mod_name, types.ModuleType(mod_name))
ent_stub = types.ModuleType("_app_stub.tender.control.api.tenders.tender_entitlement")
sys.modules["_app_stub.tender.control.api.tenders.tender_entitlement"] = ent_stub

attach = load_endpoint("o4_attach", "api/tenders/attach_returnable_artifact.py")
gbp = load_endpoint("o4_generate", "api/tenders/generate_bid_pack.py")

# --------------------------------------------------------------------------
# input artifacts - REAL engine files via env, or the committed stand-ins
# --------------------------------------------------------------------------
print("== O-04 input artifacts ==")
ENV_BP = os.environ.get("O4_BUSINESS_PROFILE") or ""
ENV_CL = os.environ.get("O4_COMPLIANCE_LOG") or ""
if bool(ENV_BP) != bool(ENV_CL):
    print("ERROR: set BOTH O4_BUSINESS_PROFILE and O4_COMPLIANCE_LOG (or "
          "neither, for the synthetic fallback) - refusing a half-real run.")
    sys.exit(2)
REAL_MODE = bool(ENV_BP)
BP_PATH = ENV_BP or os.path.join(HERE, "data", "o4_business_profile.md")
CL_PATH = ENV_CL or os.path.join(HERE, "data", "o4_compliance_log.md")
print("MODE: REAL engine files (env)" if REAL_MODE else
      "MODE: SYNTHETIC fallback fixtures (set O4_BUSINESS_PROFILE / "
      "O4_COMPLIANCE_LOG to engine output for the real-files run)")

with open(BP_PATH, encoding="utf-8") as f:
    BP_TEXT = f.read()
with open(CL_PATH, encoding="utf-8") as f:
    CL_TEXT = f.read()

check("both input files exist, non-empty, UTF-8 markdown with a top-level "
      "heading",
      BP_TEXT.strip() and CL_TEXT.strip()
      and BP_TEXT.lstrip().startswith("# ") and CL_TEXT.lstrip().startswith("# "))
check("the files are the two O-04 artifacts: a Business Profile and a "
      "Compliance Log",
      "Business Profile" in BP_TEXT.splitlines()[0]
      and CL_TEXT.splitlines()[0].startswith("# Compliance Log"))
check("the engine's honest not-verified markers are present (no evidence "
      "uploaded -> 'Pending' / 'not verified' text; expected - the smoke "
      "tests attach/attest mechanics, not document completeness)",
      "Pending" in BP_TEXT and "not verified" in CL_TEXT)
if REAL_MODE:
    check("REAL FILES: business_profile.md carries the engine's own "
          "document-control provenance (Engine: StartupOS + content-hash "
          "revision) - this is engine output, not a hand-made stand-in",
          "**Engine**: StartupOS" in BP_TEXT and "content hash" in BP_TEXT)
    check("REAL FILES: compliance_log.md carries the engine's generated "
          "header (Generated + Jurisdiction lines)",
          "Generated:" in CL_TEXT and "Jurisdiction:" in CL_TEXT)
else:
    print("SKIP engine-provenance checks: synthetic fallback fixtures in use")
    print("SKIP   (generate the real files with `startupos compile --only "
          "business_profile`")
    print("SKIP   and set O4_BUSINESS_PROFILE / O4_COMPLIANCE_LOG)")
    check("fallback stand-ins are honestly labelled: both committed "
          "fixtures name themselves SYNTHETIC STAND-IN, never engine output",
          "SYNTHETIC STAND-IN" in BP_TEXT and "SYNTHETIC STAND-IN" in CL_TEXT)


# --------------------------------------------------------------------------
# the bid under smoke - two captured returnables, driven through the REAL
# endpoint -> regime fold -> builder -> renderer chain
# --------------------------------------------------------------------------
class FakeRow(dict):
    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        self[key] = value


class FakeBidDoc(dict):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.saved = 0

    def __getattr__(self, key):
        return self.get(key)

    def append(self, table, row):
        self.setdefault(table, []).append(dict(row))

    def save(self, ignore_permissions=False):
        self.saved += 1

    def db_set(self, field, value):
        self[field] = value


ROW_BP = FakeRow(ref_code="16", title="Company Profile", mandatory=1,
                 category="Technical Returnable", studio_scope="Business Profile")
ROW_CL = FakeRow(ref_code="17", title="Compliance status of the bidder", mandatory=1,
                 category="Technical Returnable", studio_scope="Compliance Log")
BID = FakeBidDoc(name="BID-O4", user="desk@example.com",
                 custom_returnables=[ROW_BP, ROW_CL], returnables_override=1,
                 functionality_mode="No scored functionality")
ent_stub.get_owned_bid = lambda name: BID

CTX = {"bid_name": "BID-O4", "generated_on": "2026-08-21"}


def render_pack(gate_failures=()):
    """The generate_bid_pack chain on the CURRENT bid rows: the REAL
    apply_custom_returnables fold (ref_code -> form_code, the studio hook
    travelling with the row), the REAL builder, the REAL renderer - only
    the regime fixture/db read is inlined (no templates, no profile)."""
    regime = gbp.apply_custom_returnables(
        {"regime_code": "MBD", "regime_name": "Municipal (MBD forms)", "forms": []},
        BID)
    pack = pack_builder.build_pack(regime, {}, {}, CTX, list(gate_failures))
    return pack, pack_builder.render_pack_html(pack, CTX)


# --------------------------------------------------------------------------
# 1. captured, scope-only: pointer renders, NO gate open yet
# --------------------------------------------------------------------------
print("== 1. scope-only capture: GENERATE VIA STUDIO, no gate ==")
check("pre-attach readiness: scope-only rows open NO gate - the "
      "[RETURNABLE-ARTIFACT-UNATTESTED] gate is additive and fires only "
      "once a generated_artifact is attached (what the code actually does)",
      gate.validate_submission_readiness(BID) == []
      and pack_lints.unattested_artifact_failures(BID["custom_returnables"]) == [])
pack0, html0 = render_pack()
check("worksheet renders the GENERATE VIA STUDIO pointer for BOTH rows, "
      "naming their studio documents; hand-fill placeholder still present; "
      "no SATISFIED provenance yet",
      html0.count("GENERATE VIA STUDIO") == 2
      and "Business Profile" in html0 and "Compliance Log" in html0
      and html0.count("No field template exists") == 2
      and "SATISFIED BY GENERATED ARTIFACT" not in html0)

# --------------------------------------------------------------------------
# 2. attach the engine files (unattested) - gate fires, provenance renders
# --------------------------------------------------------------------------
print("== 2. attach engine files unattested: gate fires, caveat renders ==")
BP_URL = "/files/" + os.path.basename(BP_PATH)
CL_URL = "/files/" + os.path.basename(CL_PATH)
FILES = {
    BP_URL: {"name": "F-O4-BP", "attached_to_doctype": "Tender Bid",
             "attached_to_name": "BID-O4", "content": BP_TEXT},
    CL_URL: {"name": "F-O4-CL", "attached_to_doctype": "Tender Bid",
             "attached_to_name": "BID-O4", "content": CL_TEXT},
    "/files/other-bids-profile.md": {
        "name": "F-O4-X", "attached_to_doctype": "Tender Bid",
        "attached_to_name": "BID-OTHER", "content": BP_TEXT},
}
frappe_stub.db.get_value = lambda doctype, filters, field=None: (
    FILES.get(filters.get("file_url"), {}).get("name") if doctype == "File" else None)
frappe_stub.get_doc = lambda doctype, name: (
    [f for f in FILES.values() if f["name"] == name][0] if doctype == "File" else None)

res_bp = attach.attach_returnable_artifact("BID-O4", "16", file_url=BP_URL)
res_cl = attach.attach_returnable_artifact("BID-O4", "17", file_url=CL_URL)
check("attach records both real artifacts with an audit timestamp but NOT "
      "satisfied (unattested), saving the bid each time; the endpoint's own "
      "note names the gate tag",
      res_bp["generated_artifact"] == BP_URL and res_cl["generated_artifact"] == CL_URL
      and res_bp["satisfied"] is False and res_cl["satisfied"] is False
      and res_bp["artifact_attested"] is False and res_bp["artifact_attached_on"]
      and BID.saved == 2
      and "[RETURNABLE-ARTIFACT-UNATTESTED]" in res_bp["note"]
      and "[RETURNABLE-ARTIFACT-UNATTESTED]" in res_cl["note"])
fails = gate.validate_submission_readiness(BID)
check("validate_submission_readiness now fails once PER unattested "
      "artifact, each failure tagged [RETURNABLE-ARTIFACT-UNATTESTED] and "
      "naming its row + file",
      len(fails) == 2
      and all(pack_lints.UNATTESTED_ARTIFACT_TAG in f for f in fails)
      and "'16'" in fails[0] and BP_URL in fails[0]
      and "'17'" in fails[1] and CL_URL in fails[1])
pack1, html1 = render_pack(gate_failures=fails)
check("worksheet renders SATISFIED BY GENERATED ARTIFACT for both files, "
      "suppresses the hand-fill placeholder and the studio pointer, and "
      "carries the NOT YET ATTESTED caveat on each",
      html1.count("SATISFIED BY GENERATED ARTIFACT") == 2
      and BP_URL in html1 and CL_URL in html1
      and "No field template exists" not in html1
      and "GENERATE VIA STUDIO" not in html1
      and html1.count("NOT YET ATTESTED") == 2
      and "studio document: Business Profile" in html1)
check("the same failures flow to the pack cover + warning page exactly as "
      "generate_bid_pack wires them (2 FATAL gates named, tag printed)",
      "2 FATAL compliance gate(s) still open" in html1
      and html1.count(pack_lints.UNATTESTED_ARTIFACT_TAG) == 2
      and pack1["manifest"]["open_fatal_gates"] == fails)
check("entitlement discipline holds mid-smoke: the same real file "
      "registered against ANOTHER bid is refused",
      throws(lambda: attach.attach_returnable_artifact(
          "BID-O4", "16", file_url="/files/other-bids-profile.md"),
          "not attached to this bid"))

# --------------------------------------------------------------------------
# 3. attest - gate clears, caveat drops, manifest carries the flags
# --------------------------------------------------------------------------
print("== 3. attest: gate clears, SATISFIED renders clean ==")
res_bp2 = attach.attach_returnable_artifact("BID-O4", "16", attest=1)
res_cl2 = attach.attach_returnable_artifact("BID-O4", "17", attest=1)
check("attest=1 flips both rows to satisfied (generated-and-attested), "
      "endpoint note confirms",
      res_bp2["satisfied"] is True and res_cl2["satisfied"] is True
      and res_bp2["note"] == "Satisfied: generated-and-attested."
      and res_bp2["generated_artifact"] == BP_URL)
check("the readiness gate CLEARS: validate_submission_readiness returns "
      "no failures after attestation",
      gate.validate_submission_readiness(BID) == [])
pack2, html2 = render_pack(gate_failures=gate.validate_submission_readiness(BID))
check("attested worksheet: SATISFIED BY GENERATED ARTIFACT stays for both, "
      "the NOT YET ATTESTED caveat and the hand-fill placeholder are gone, "
      "no FATAL-gate cover warning",
      html2.count("SATISFIED BY GENERATED ARTIFACT") == 2
      and "NOT YET ATTESTED" not in html2
      and "No field template exists" not in html2
      and "FATAL compliance gate" not in html2)
check("manifest provenance flags: both forms generated+attested now, and "
      "the phase-2 manifest had generated=True but attested=False",
      all(f["generated"] is True and f["attested"] is True
          for f in pack2["manifest"]["forms"])
      and all(f["generated"] is True and f["attested"] is False
              for f in pack1["manifest"]["forms"]))

# --------------------------------------------------------------------------
# 4. regression guards - no-hook baseline and detach round-trip
# --------------------------------------------------------------------------
print("== 4. regression: no-hook baseline byte-identical; detach round-trip ==")


def render_plain(rows):
    regime = gbp.apply_custom_returnables(
        {"regime_code": "MBD", "regime_name": "Municipal (MBD forms)", "forms": []},
        FakeBidDoc(name="BID-O4", custom_returnables=rows, returnables_override=1))
    return pack_builder.render_pack_html(
        pack_builder.build_pack(regime, {}, {}, CTX, []), CTX)


baseline = render_plain([FakeRow(ref_code="MBD 4", title="Declaration of Interest",
                                 mandatory=1)])
with_empty_hook = render_plain([FakeRow(ref_code="MBD 4", title="Declaration of Interest",
                                        mandatory=1, studio_scope=None,
                                        generated_artifact=None, artifact_attested=0)])
check("a bid with NO artifact fields renders byte-identically to the "
      "no-hook baseline - zero studio/artifact notices leak in",
      baseline == with_empty_hook
      and "GENERATE VIA STUDIO" not in baseline
      and "SATISFIED BY GENERATED ARTIFACT" not in baseline
      and "NOT YET ATTESTED" not in baseline)
attach.attach_returnable_artifact("BID-O4", "16", detach=1)
attach.attach_returnable_artifact("BID-O4", "17", detach=1)
check("detach round-trip: clearing both artifacts returns readiness to "
      "clean and the worksheet BYTE-IDENTICALLY to the pre-attach "
      "GENERATE VIA STUDIO state",
      gate.validate_submission_readiness(BID) == []
      and render_pack()[1] == html0)

# --------------------------------------------------------------------------
# hygiene
# --------------------------------------------------------------------------
print("== hygiene ==")
FIXTURES = (os.path.join(HERE, "data", "o4_business_profile.md"),
            os.path.join(HERE, "data", "o4_compliance_log.md"))
check("the committed fallback fixtures exist, are small, LF-only, and name "
      "themselves SYNTHETIC STAND-IN (the real engine files are never "
      "committed - env-var only)",
      all(os.path.exists(p) and os.path.getsize(p) < 4096
          and b"\r" not in open(p, "rb").read()
          and "SYNTHETIC STAND-IN" in open(p, encoding="utf-8").read()
          for p in FIXTURES))
check("O-05: the suite runs with sys.dont_write_bytecode set, so in-tree "
      "runs leave no __pycache__ litter under src/",
      sys.dont_write_bytecode is True)

# --------------------------------------------------------------------------
failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed"
      + (" [REAL engine files]" if REAL_MODE else " [synthetic fallback]"))
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL O-04 SMOKE CHECKS PASSED")
