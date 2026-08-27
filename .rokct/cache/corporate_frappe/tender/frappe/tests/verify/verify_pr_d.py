#!/usr/bin/env python3
"""Standalone verification for PR-D (F-02 full, first pass: deterministic
pack parsing - text_extract / pack_parse / pack_ingest + parse_tender_pack).

frappe fully stubbed in-memory; real modules loaded from the repo (the
endpoint exec'd with the composer {app_name} placeholder substituted).
Synthetic pack-text fixtures are shaped like the three documented sample
styles and quote real pack lines from the mock-samples checklists (Musina
18-2025/26, RNM 8/2/RNM0614, DFFE B005). Proves:

parse:  returnables extracted with correct codes/titles per style (RNM
        lettered A1/B1/C1.1, DFFE Annexure A-C + numbered admin rows,
        Musina Form A-E + checklist numbers + 5.1(x) mandatory items);
        closing date/time, tender number, functionality threshold (+points
        pair / max points), preference system, channel signals and wet-ink
        extracted where present; NOT-FOUND (never a guess) when absent;
        every QUOTED value carries its verbatim source line.
ingest: preview rows are Tender Bid Returnable-shaped with the quoted line
        as guidance; already-captured ref codes skipped; conflicts with
        bid-held values produce [PARSE-CONFLICT] warnings; matching values
        report already-set-match; template-code linking is exact-only.
apply:  endpoint preview NEVER modifies the bid; apply=1 appends; the
        selected_refs selection is honored; field values never applied.
extract: real repo PDF smoke test (pypdf), plain-text passthrough,
        no-text-layer and extractor-missing degradation.
wiring: submission_readiness_warnings suggests the parser ONLY when
        GATE-PACK-COLLECT is open AND a pack file is attached; manifest
        registers the endpoint in all three families + pypdf dependency;
        parser modules stay frappe-free / network-free / OCR-free.
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

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


# --------------------------------------------------------------------------
# frappe stub (endpoint + submission_gate only - parsing modules import none)
# --------------------------------------------------------------------------
class Thrown(Exception):
    pass


frappe_stub = types.ModuleType("frappe")
utils_stub = types.ModuleType("frappe.utils")
utils_stub.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
utils_stub.flt = lambda v, precision=None: float(v) if v not in (None, "") else 0.0
utils_stub.nowdate = lambda: "2026-08-21"
utils_stub.getdate = lambda v=None: v
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


text_extract = load_module("d_text_extract", os.path.join(SRC, "parsing/text_extract.py"))
pack_parse = load_module("d_pack_parse", os.path.join(SRC, "parsing/pack_parse.py"))
pack_ingest = load_module("d_pack_ingest", os.path.join(SRC, "parsing/pack_ingest.py"))
gate = load_module("d_submission_gate", os.path.join(SRC, "compliance/submission_gate.py"))

# --------------------------------------------------------------------------
# fixtures - three styles; quoted lines come from the mock-samples checklists
# --------------------------------------------------------------------------
RNM_TEXT = """T1.1 TENDER NOTICE AND INVITATION TO TENDER
Tender No: 8/2/RNM0614
CONSTRUCTION OF MGODLWA PEDESTRIAN BRIDGE IN WARD 8
Closing: 8 September 2026 at 12:00 in the bid box
The tenderer must complete and return documents A1 to A21; B1 to B2; C1.1 and C3 as listed below as part of his/her tender submission:
A1 Authority To Sign Documents
A2 Letter Of Good Standing, Workmen's Compensation Commissioner
A3 Certificate Of Authority for Joint Ventures
A4 Schedule Of Work Carried Out by The Tenderer
A10 Pricing Schedule - Firm Prices (RNM/MBD3.1)
A12 Record Of Addenda to Tender Documents
A15 Joint Venture Disclosure Form
A21 Preference Points Claim Form, PPR 2022 (RNM/MBD 6.1)
B1 CIDB Contractor Registration Certificate
B2 Tax Pin (RNM/MBD2)
C1.1 Form of Offer and Acceptance
C3 Scope of Work
rejecting all tender offers that fail to score the minimum number of 60% (42 out of 70) of the points for quality
The 90/10 preference point system is applicable to this tender.
The tender must be submitted in a sealed envelope and deposited in the tender box.
"""

DFFE_TEXT = """BID NO: DFFE-B005 26/27
APPOINTMENT OF A SERVICE PROVIDER FOR THE TRIENNIAL STATE OF THE FORESTS REPORT
CLOSING DATE: 2026-09-02 11:00
The bid proposal will be screened for compliance with administrative requirements as indicated below:
1. Master Bid Document - Provided and bound
2. Electronic Copy (USB) - Same as the master bid document
3. SCM - SBD 1 - Invitation to Bid - Completed and signed
Annexure A - Pricing Schedule
Annexure B - Curriculum Vitae Template
Annexure C - Consent and Indemnity Form
The bidder must score a minimum of 75% during Phase 2 (functionality) of the evaluation to qualify for Phase 3 of the evaluation
TOTAL POINTS ON FUNCTIONALITY 100
The preference point system applicable for this bid is 80/20.
"""

MUSINA_TEXT = """TENDER 18-2025/26
INTERACTIVE CLOUD BASED CUSTOMER SERVICE TICKETING AND HELPDESK MANAGEMENT SYSTEM
CLOSING DATE: 11 May 2026 @ 11:00
CHECKLIST OF DOCUMENTATION TO BE ATTACHED
1. Tax Compliance Status Pin Issued
2. Certified ID copies of all members / owners / directors / shareholders / Trustees
3. Copy of municipal rates and taxes statement of account not older than three months for all directors and for the company
4. Central supplier database registration report
Forms to be completed by the Bidder
Form A - Form of Bid
Form B - Signatory Authorisation
Form C - Declaration of Interest
Form D - Certificate of Preference for Local Content and SABS mark
Form E - OHS Act s37(2) contract
5.1 Mandatory bid requirements - To ensure your proposal is considered for evaluation
(c) detailed project plan with clear timelines/timeframes, outlining milestones from project inception to completion
(g) Risk management plan associated with the project
(j) Service Provider Banking Rating [A to C] not older than 3 months
2nd Stage: Price and specific goals on the 80/20 preference point system, where 80 points is for Price and 20 points is for specific goals
BID DOCUMENT MUST BE COMPLETED IN INK
Tenders submitted by facsimile, telex, telegram or e-mail WILL NOT BE CONSIDERED
The bid must be sealed envelope marked with the bid number and deposited in the tender box at Reception Office Room 53
"""

GARBAGE_TEXT = """Dear Sir or Madam
Please find attached our covering letter.
We look forward to hearing from you.
A4 paper must be used for all correspondence.
Yours faithfully
"""

QUOTED = pack_parse.QUOTED
NOT_FOUND = pack_parse.NOT_FOUND

# --------------------------------------------------------------------------
# pack_parse - RNM lettered schedule style
# --------------------------------------------------------------------------
print("== pack_parse: RNM lettered schedule (A1..A21; B1-B2; C1.1, C3) ==")
rnm = pack_parse.parse_pack_text(RNM_TEXT)
rnm_items = {i["ref_code"]: i for i in rnm["returnables"]["items"]}
check("12 lettered returnables extracted, status QUOTED",
      rnm["returnables"]["status"] == QUOTED and rnm["returnables"]["count"] == 12)
check("codes A1/A10/A21/B1/B2/C1.1/C3 all present with pack titles verbatim",
      rnm_items["A1"]["title"] == "Authority To Sign Documents"
      and rnm_items["A10"]["title"] == "Pricing Schedule - Firm Prices (RNM/MBD3.1)"
      and rnm_items["A21"]["title"] == "Preference Points Claim Form, PPR 2022 (RNM/MBD 6.1)"
      and rnm_items["B1"]["title"] == "CIDB Contractor Registration Certificate"
      and rnm_items["B2"]["title"] == "Tax Pin (RNM/MBD2)"
      and rnm_items["C1.1"]["title"] == "Form of Offer and Acceptance"
      and rnm_items["C3"]["title"] == "Scope of Work")
check("every item carries its verbatim source line",
      all(i["source_line"].startswith(i["ref_code"] + " ")
          for i in rnm["returnables"]["items"]))
check("tender number quoted from 'Tender No:' label",
      rnm["tender_number"]["status"] == QUOTED
      and rnm["tender_number"]["value"] == "8/2/RNM0614")
check("closing '8 September 2026 at 12:00' -> 2026-09-08 12:00 (QUOTED)",
      rnm["closing_date"]["status"] == QUOTED
      and rnm["closing_date"]["value"] == "2026-09-08"
      and rnm["closing_date"]["time"] == "12:00")
check("functionality threshold 60% with points pair 42/70 from the quoted "
      "'minimum number of 60% (42 out of 70)' line",
      rnm["functionality"]["status"] == QUOTED
      and rnm["functionality"]["value"] == 60.0
      and rnm["functionality"]["threshold_points"] == 42
      and rnm["functionality"]["max_points"] == 70
      and "minimum number of 60%" in rnm["functionality"]["source_line"])
check("preference system 90/10 quoted", rnm["preference_system"]["value"] == "90/10")
check("channel -> Physical tender box from sealed-envelope signal",
      rnm["submission_channel"]["status"] == QUOTED
      and rnm["submission_channel"]["value"] == "Physical tender box"
      and {s["signal"] for s in rnm["submission_channel"]["signals"]}
          >= {"sealed_envelope", "tender_box"})
check("wet ink NOT-FOUND on RNM fixture (no ink language present)",
      rnm["wet_ink"]["status"] == NOT_FOUND)

# --------------------------------------------------------------------------
# pack_parse - DFFE annexures + numbered admin list
# --------------------------------------------------------------------------
print("== pack_parse: DFFE annexures + numbered admin screening list ==")
dffe = pack_parse.parse_pack_text(DFFE_TEXT)
dffe_items = {i["ref_code"]: i for i in dffe["returnables"]["items"]}
check("Annexure A/B/C extracted with titles",
      dffe_items["Annexure A"]["title"] == "Pricing Schedule"
      and dffe_items["Annexure B"]["title"] == "Curriculum Vitae Template"
      and dffe_items["Annexure C"]["title"] == "Consent and Indemnity Form")
check("numbered admin rows 1-3 captured (list-mode gated by the quoted "
      "'screened for compliance with administrative requirements' header)",
      dffe_items["1"]["title"].startswith("Master Bid Document")
      and dffe_items["2"]["title"].startswith("Electronic Copy (USB)")
      and dffe_items["3"]["title"].startswith("SCM - SBD 1"))
check("closing ISO date + 11:00 quoted",
      dffe["closing_date"]["value"] == "2026-09-02"
      and dffe["closing_date"]["time"] == "11:00")
check("bid number 'DFFE-B005 26/27' quoted from BID NO label",
      dffe["tender_number"]["value"] == "DFFE-B005 26/27")
check("functionality threshold 75% + max points 100 from the separate "
      "'TOTAL POINTS ON FUNCTIONALITY 100' line",
      dffe["functionality"]["value"] == 75.0
      and dffe["functionality"]["max_points"] == 100
      and "minimum of 75%" in dffe["functionality"]["source_line"])
check("preference 80/20 quoted; channel and wet-ink NOT-FOUND (absent from pack)",
      dffe["preference_system"]["value"] == "80/20"
      and dffe["submission_channel"]["status"] == NOT_FOUND
      and dffe["wet_ink"]["status"] == NOT_FOUND)

# --------------------------------------------------------------------------
# pack_parse - Musina form letters + checklist + 5.1 mandatory items
# --------------------------------------------------------------------------
print("== pack_parse: Musina Form A-E + checklist numbers + 5.1(x) items ==")
mus = pack_parse.parse_pack_text(MUSINA_TEXT)
mus_items = {i["ref_code"]: i for i in mus["returnables"]["items"]}
check("Forms A-E extracted with buyer titles",
      mus_items["Form A"]["title"] == "Form of Bid"
      and mus_items["Form B"]["title"] == "Signatory Authorisation"
      and mus_items["Form C"]["title"] == "Declaration of Interest"
      and mus_items["Form D"]["title"] == "Certificate of Preference for Local Content and SABS mark"
      and mus_items["Form E"]["title"] == "OHS Act s37(2) contract")
check("page-2 checklist rows 1-4 captured (gated by the quoted 'CHECKLIST "
      "OF DOCUMENTATION TO BE ATTACHED' header)",
      mus_items["1"]["title"] == "Tax Compliance Status Pin Issued"
      and mus_items["4"]["title"] == "Central supplier database registration report")
check("5.1 mandatory items ref-coded with the section number: 5.1(c)/(g)/(j)",
      mus_items["5.1(c)"]["title"].startswith("detailed project plan")
      and mus_items["5.1(g)"]["title"] == "Risk management plan associated with the project"
      and mus_items["5.1(j)"]["title"] == "Service Provider Banking Rating [A to C] not older than 3 months")
check("closing '11 May 2026 @ 11:00' -> 2026-05-11 11:00",
      mus["closing_date"]["value"] == "2026-05-11"
      and mus["closing_date"]["time"] == "11:00")
check("tender number '18-2025/26' from the TENDER heading",
      mus["tender_number"]["value"] == "18-2025/26")
check("functionality NOT-FOUND (Musina eliminates on mandatory requirements, "
      "no scored threshold) - not guessed",
      mus["functionality"]["status"] == NOT_FOUND
      and mus["functionality"]["value"] is None)
check("preference 80/20 from the quoted 2nd Stage line",
      mus["preference_system"]["value"] == "80/20"
      and "80/20 preference point system" in mus["preference_system"]["source_line"])
check("wet ink QUOTED from 'BID DOCUMENT MUST BE COMPLETED IN INK'",
      mus["wet_ink"]["status"] == QUOTED
      and "COMPLETED IN INK" in mus["wet_ink"]["source_line"])
check("channel Physical tender box; email-prohibition signal captured from "
      "the quoted facsimile/e-mail line",
      mus["submission_channel"]["value"] == "Physical tender box"
      and "email_prohibited" in {s["signal"] for s in mus["submission_channel"]["signals"]})

# --------------------------------------------------------------------------
# pack_parse - NOT-FOUND discipline on non-pack text
# --------------------------------------------------------------------------
print("== pack_parse: NOT-FOUND, never guessed ==")
garbage = pack_parse.parse_pack_text(GARBAGE_TEXT)
check("garbage text: every scalar NOT-FOUND, zero returnables (the lone "
      "'A4 paper' line is NOT harvested as a schedule item)",
      all(garbage[k]["status"] == NOT_FOUND for k in
          ("tender_number", "closing_date", "functionality",
           "preference_system", "submission_channel", "wet_ink"))
      and garbage["returnables"]["status"] == NOT_FOUND
      and garbage["returnables"]["items"] == [])
check("empty text parses to all NOT-FOUND without error",
      pack_parse.parse_pack_text("")["returnables"]["count"] == 0)
email_txt = "Bids may be submitted by e-mail to scm@example.gov.za\n"
check("email-allowed signal proposes 'Email allowed' when no prohibition/"
      "physical signal exists",
      pack_parse.parse_pack_text(email_txt)["submission_channel"]["value"] == "Email allowed")
portal_txt = "Submissions only via the eTender portal before closing.\n"
check("portal signal proposes 'Portal upload'",
      pack_parse.parse_pack_text(portal_txt)["submission_channel"]["value"] == "Portal upload")

print("== pack_parse: adversarial cases ==")
collapsed = pack_parse.parse_pack_text(
    "Tender No: 8/2/RNM0614 Closing Date To Be Announced\n")
check("collapsed PDF line: tender number stops at the reference, trailing "
      "words not swallowed ('8/2/RNM0614', not '... Closing Date')",
      collapsed["tender_number"]["value"] == "8/2/RNM0614")
cidb_sections = pack_parse.parse_pack_text(
    "T1.1 Tender Notice and Invitation to Tender\n"
    "T1.2 Tender Data\n"
    "T2.1 List of Returnable Documents\n"
    "T2.2 Returnable Schedules\n")
check("CIDB pack-structure section codes (T1.1/T2.1...) are NOT harvested "
      "as returnables",
      cidb_sections["returnables"]["count"] == 0)
subcontract = pack_parse.parse_pack_text(
    "A minimum of 30% of the contract value must be subcontracted to "
    "designated groups to earn preference points\n")
check("a subcontracting 'minimum of 30%' near preference-points language "
      "stays NOT-FOUND, never a fake functionality threshold",
      subcontract["functionality"]["status"] == NOT_FOUND)
check("RNM/DFFE thresholds still extract after the context tightening "
      "('quality' / 'functionality' context words)",
      rnm["functionality"]["value"] == 60.0 and dffe["functionality"]["value"] == 75.0)

# --------------------------------------------------------------------------
# pack_ingest - preview mapping onto the existing surface
# --------------------------------------------------------------------------
print("== pack_ingest: Tender Bid Returnable-shaped preview, quoted guidance ==")
returnable_json = json.load(open(os.path.join(
    SRC, "doctype/tender_bid_returnable/tender_bid_returnable.json")))
# capture fields only: the F-15 studio-hook / artifact-state fields are
# desk- or endpoint-managed, never proposed by the parser preview
ARTIFACT_STATE_FIELDS = {
    "studio_scope", "generated_artifact", "artifact_attested",
    "artifact_attached_on", "artifact_sha256"}
doctype_fields = {
    f["fieldname"] for f in returnable_json["fields"]
} - ARTIFACT_STATE_FIELDS

preview = pack_ingest.build_ingest_preview(mus, bid={
    "closing_date": "2026-05-11",
    "functionality_threshold": None,
    "preference_system": None,
    "submission_channel": None,
    "custom_returnables": [{"ref_code": "Form A"}],
}, known_template_codes=["MBD4", "MBD6.1", "MBD8", "MBD9"])

check("every proposed row's keys are exactly the Tender Bid Returnable "
      "capture fields", preview["proposed_returnables"]
      and all(set(r) == doctype_fields for r in preview["proposed_returnables"]))
check("guidance on each row quotes the source line and says verify",
      all(r["guidance"].startswith('Parsed from the pack (QUOTED): "')
          and "verify" in r["guidance"]
          for r in preview["proposed_returnables"]))
row_b = [r for r in preview["proposed_returnables"] if r["ref_code"] == "Form B"][0]
check("Form B row: mandatory=1, category Buyer Form, no invented template/"
      "kill note, source line inside guidance",
      row_b["mandatory"] == 1 and row_b["category"] == "Buyer Form"
      and row_b["template_code"] is None and row_b["kill_note"] == ""
      and "Form B - Signatory Authorisation" in row_b["guidance"])
check("already-captured Form A skipped from proposals and reported",
      preview["already_captured"] == ["Form A"]
      and not [r for r in preview["proposed_returnables"] if r["ref_code"] == "Form A"])
check("5.1 items proposed as Technical Returnable",
      [r for r in preview["proposed_returnables"] if r["ref_code"] == "5.1(j)"][0]
      ["category"] == "Technical Returnable")
fields = preview["proposed_fields"]
check("closing date matches the bid -> already-set-match, no conflict warning",
      fields["closing_date"]["action"] == "already-set-match")
check("preference/channel propose (bid blank); functionality not-found",
      fields["preference_system"]["action"] == "propose"
      and fields["submission_channel"]["action"] == "propose"
      and fields["functionality_threshold"]["action"] == "not-found")
check("no [PARSE-CONFLICT] warnings when nothing disagrees",
      not [w for w in preview["warnings"] if "[PARSE-CONFLICT]" in w])
check("not_found names the parse keys that missed",
      "functionality" in preview["not_found"])

print("== pack_ingest: disagreement warnings ==")
conflicted = pack_ingest.build_ingest_preview(mus, bid={
    "closing_date": "2026-06-01",
    "functionality_threshold": None,
    "preference_system": "90/10",
    "submission_channel": "Portal upload",
    "custom_returnables": [],
})
conflict_warnings = [w for w in conflicted["warnings"] if "[PARSE-CONFLICT]" in w]
check("closing/preference/channel disagreements each raise [PARSE-CONFLICT] "
      "and neither value is changed",
      len(conflict_warnings) == 3
      and all(f["action"] == "conflict" for f in (
          conflicted["proposed_fields"]["closing_date"],
          conflicted["proposed_fields"]["preference_system"],
          conflicted["proposed_fields"]["submission_channel"]))
      and "2026-05-11" in conflict_warnings[0] and "2026-06-01" in conflict_warnings[0])
match_dffe = pack_ingest.build_ingest_preview(dffe, bid={
    "closing_date": None, "functionality_threshold": 75,
    "preference_system": "80/20", "submission_channel": None,
    "custom_returnables": [],
})
check("numeric threshold 75.0 vs bid 75 and preference 80/20 vs 80/20 both "
      "report already-set-match (no false conflicts)",
      match_dffe["proposed_fields"]["functionality_threshold"]["action"] == "already-set-match"
      and match_dffe["proposed_fields"]["preference_system"]["action"] == "already-set-match")
straddle = pack_parse.parse_pack_text(
    "the 80/20 preference point system applies\n"
    "points will be awarded on the 90/10 preference point system\n")
straddle_prev = pack_ingest.build_ingest_preview(straddle, bid={})
check("a pack quoting BOTH 80/20 and 90/10 raises the straddling "
      "[PARSE-CONFLICT] warning (F-12)",
      len(straddle["preference_system"]["all_hits"]) == 2
      and any("MORE THAN ONE preference point system" in w
              for w in straddle_prev["warnings"]))
check("template-code linking is exact-only: 'MBD 4' -> MBD4, 'Annexure A' "
      "-> None",
      pack_ingest._template_code_for("MBD 4", ["MBD4", "MBD6.1"]) == "MBD4"
      and pack_ingest._template_code_for("MBD 6.1", ["MBD4", "MBD6.1"]) == "MBD6.1"
      and pack_ingest._template_code_for("Annexure A", ["MBD4"]) is None
      and pack_ingest._template_code_for("A4", ["MBD4"]) is None)

# --------------------------------------------------------------------------
# text_extract - real PDF smoke + degradation paths
# --------------------------------------------------------------------------
print("== text_extract: real repo PDF smoke test + degradation ==")
pdf_path = os.path.join(
    REPO, "tender/mock-samples/18-2025-26-musina-helpdesk/03-bid-pack.pdf")
try:
    import pypdf  # noqa: F401
    HAVE_PYPDF = True
except ImportError:
    HAVE_PYPDF = False
if HAVE_PYPDF and os.path.exists(pdf_path):
    with open(pdf_path, "rb") as f:
        pdf_result = text_extract.extract_pack_text(f.read())
    check("repo PDF (Musina generated pack) extracts: status ok, pypdf, "
          f"pages={pdf_result['pages']}, {len(pdf_result['text'])} chars of text",
          pdf_result["status"] == "ok" and pdf_result["extractor"] == "pypdf"
          and pdf_result["pages"] > 0 and len(pdf_result["text"]) > 1000)
    parsed_pdf = pack_parse.parse_pack_text(pdf_result["text"])
    check("parse over the real PDF text runs clean and stays two-level "
          "(QUOTED/NOT-FOUND only)",
          all((parsed_pdf[k]["status"] in (QUOTED, NOT_FOUND)) for k in
              ("tender_number", "closing_date", "functionality",
               "preference_system", "submission_channel", "wet_ink")))
else:
    check("PDF smoke SKIPPED (pypdf or sample PDF unavailable) - parse/"
          "ingest proven on text fixtures only", True)
check("plain-text bytes pass through (utf-8 decode, extractor plain-text)",
      text_extract.extract_pack_text("CLOSING DATE: 2026-09-02".encode())["status"] == "ok"
      and text_extract.extract_pack_text(b"abc")["extractor"] == "plain-text")
check("str input used as-is; empty input errors",
      text_extract.extract_pack_text("some pack text")["status"] == "ok"
      and text_extract.extract_pack_text("")["status"] == "error"
      and text_extract.extract_pack_text(None)["status"] == "error")

_orig_pypdf, _orig_pdfminer = text_extract._try_pypdf, text_extract._try_pdfminer
text_extract._try_pypdf = lambda content: None
text_extract._try_pdfminer = lambda content: None
missing = text_extract.extract_pack_text(b"%PDF-1.4 fake")
check("no PDF library -> explicit extractor-missing status naming pypdf, "
      "text empty, never a crash or a guess",
      missing["status"] == "extractor-missing" and missing["text"] == ""
      and "pypdf" in missing["note"])
text_extract._try_pypdf = lambda content: ("pypdf", "   \n  ", 3)
scan = text_extract.extract_pack_text(b"%PDF-1.4 fake-scan")
check("empty text layer (scan) -> explicit no-text-layer status, note says "
      "no OCR / capture by hand",
      scan["status"] == "no-text-layer" and scan["pages"] == 3
      and "OCR" in scan["note"])
text_extract._try_pypdf, text_extract._try_pdfminer = _orig_pypdf, _orig_pdfminer

# --------------------------------------------------------------------------
# endpoint - preview never writes; apply honors selection
# --------------------------------------------------------------------------
print("== parse_tender_pack endpoint: preview-only default, gated apply ==")


class FakeBid(dict):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.saved = 0

    def __getattr__(self, key):
        return self.get(key)

    def append(self, table, row):
        self.setdefault(table, []).append(dict(row))

    def save(self, **k):
        self.saved += 1


def make_bid(**over):
    bid = FakeBid({
        "name": "BID-0001", "user": "desk@example.com",
        "closing_date": None, "functionality_threshold": None,
        "preference_system": None, "submission_channel": None,
        "custom_returnables": [], "checklist": [],
    })
    bid.update(over)
    return bid


CURRENT_BID = make_bid()

stub_root = types.ModuleType("_app_stub")
for mod_name in ("_app_stub", "_app_stub.tender", "_app_stub.tender.control",
                 "_app_stub.tender.control.api", "_app_stub.tender.control.api.tenders",
                 "_app_stub.tender.control.parsing"):
    sys.modules.setdefault(mod_name, types.ModuleType(mod_name))
ent = types.ModuleType("_app_stub.tender.control.api.tenders.tender_entitlement")
ent.get_owned_bid = lambda name: CURRENT_BID
sys.modules["_app_stub.tender.control.api.tenders.tender_entitlement"] = ent
sys.modules["_app_stub.tender.control.parsing.text_extract"] = text_extract
sys.modules["_app_stub.tender.control.parsing.pack_parse"] = pack_parse
sys.modules["_app_stub.tender.control.parsing.pack_ingest"] = pack_ingest

endpoint = load_endpoint("d_parse_tender_pack", "api/tenders/parse_tender_pack.py")

result = endpoint.parse_tender_pack("BID-0001", pack_text=MUSINA_TEXT)
check("default call returns preview + parse + extraction and NEVER modifies "
      "the bid (no rows appended, no save, applied=0)",
      result["applied"] == 0 and CURRENT_BID["custom_returnables"] == []
      and CURRENT_BID.saved == 0
      and result["preview"]["proposed_returnables"]
      and result["extraction"]["extractor"] == "plain-text"
      and "text" not in result["extraction"]
      and "apply=1" in result["note"])
n_proposed = len(result["preview"]["proposed_returnables"])

CURRENT_BID = make_bid()
sel = endpoint.parse_tender_pack(
    "BID-0001", pack_text=MUSINA_TEXT, apply=1, selected_refs='["Form B", "5.1(j)"]')
check("apply=1 + selected_refs applies EXACTLY the selected rows (2 of "
      f"{n_proposed}), bid saved once, quoted guidance travels onto the row",
      sel["applied"] == 2 and CURRENT_BID.saved == 1
      and [r["ref_code"] for r in CURRENT_BID["custom_returnables"]] == ["Form B", "5.1(j)"]
      and "Signatory Authorisation" in CURRENT_BID["custom_returnables"][0]["guidance"])
check("field values NOT applied even on apply=1 (closing/preference/channel "
      "stay untouched on the bid)",
      CURRENT_BID["closing_date"] is None
      and CURRENT_BID["preference_system"] is None
      and CURRENT_BID["submission_channel"] is None)

CURRENT_BID = make_bid(custom_returnables=[{"ref_code": "Form A"}])
all_applied = endpoint.parse_tender_pack("BID-0001", pack_text=MUSINA_TEXT, apply=1)
check("apply=1 without selection applies all proposed rows, still skipping "
      "the already-captured Form A",
      all_applied["applied"] == n_proposed - 1
      and "Form A" not in [r["ref_code"] for r in CURRENT_BID["custom_returnables"][1:]])

check("selection matching is case/whitespace-insensitive and unknown refs "
      "select nothing",
      [r["ref_code"] for r in endpoint.select_rows(
          [{"ref_code": "Form B"}, {"ref_code": "5.1(j)"}], "form b")] == ["Form B"]
      and endpoint.select_rows([{"ref_code": "Form B"}], '["NOPE"]') == [])

CURRENT_BID = make_bid()
try:
    endpoint.parse_tender_pack("BID-0001")
    check("no file_url and no pack_text -> throws", False)
except Thrown as e:
    check("no file_url and no pack_text -> throws No Pack Provided",
          "No Pack Provided" in str(e))

# file_url path: File attached to another user's doc is refused
file_doc = types.SimpleNamespace(
    get=lambda key, _d={"attached_to_doctype": "Tender Bid",
                        "attached_to_name": "SOMEONE-ELSES-BID",
                        "file_name": "pack.pdf"}: _d.get(key),
    get_content=lambda: b"content")
frappe_stub.db.get_value = lambda doctype, filters=None, field=None: (
    "FILE-1" if doctype == "File" else None)
frappe_stub.get_doc = lambda doctype, name=None: file_doc
try:
    endpoint.parse_tender_pack("BID-0001", file_url="/private/files/pack.pdf")
    check("file attached to someone else's doc -> refused", False)
except Thrown as e:
    check("file attached to someone else's doc -> refused (never read)",
          "not attached to this bid" in str(e))
file_doc.get = lambda key, _d={"attached_to_doctype": "Tender Bid",
                               "attached_to_name": "BID-0001",
                               "file_name": "pack.txt"}: _d.get(key)
file_doc.get_content = lambda: DFFE_TEXT.encode()
owned = endpoint.parse_tender_pack("BID-0001", file_url="/private/files/pack.txt")
check("file attached to THIS bid reads + parses (DFFE annexures found via "
      "file_url path)",
      any(r["ref_code"] == "Annexure C"
          for r in owned["preview"]["proposed_returnables"]))
frappe_stub.db.get_value = lambda *a, **k: None
frappe_stub.get_doc = lambda *a, **k: None

extractor_out = None
try:
    _orig = text_extract._try_pypdf
    text_extract._try_pypdf = lambda content: ("pypdf", "", 2)
    CURRENT_BID = make_bid()
    file_doc2 = types.SimpleNamespace(
        get=lambda key, _d={"attached_to_doctype": "Tender Bid",
                            "attached_to_name": "BID-0001",
                            "file_name": "scan.pdf"}: _d.get(key),
        get_content=lambda: b"%PDF-1.4 scanned")
    frappe_stub.db.get_value = lambda doctype, filters=None, field=None: "FILE-2"
    frappe_stub.get_doc = lambda doctype, name=None: file_doc2
    extractor_out = endpoint.parse_tender_pack("BID-0001", file_url="/f/scan.pdf")
finally:
    text_extract._try_pypdf = _orig
    frappe_stub.db.get_value = lambda *a, **k: None
    frappe_stub.get_doc = lambda *a, **k: None
check("scanned PDF via endpoint -> explicit no-text-layer result, no parse, "
      "no preview, nothing applied",
      extractor_out["extraction"]["status"] == "no-text-layer"
      and extractor_out["parse"] is None and extractor_out["preview"] is None
      and extractor_out["applied"] == 0 and CURRENT_BID.saved == 0)

# --------------------------------------------------------------------------
# submission_gate wiring - the [PARSE-PACK-AVAILABLE] suggestion
# --------------------------------------------------------------------------
print("== submission_gate: parse-the-pack suggestion ==")
open_gate_row = {"rule_code": "GATE-PACK-COLLECT", "status": "Open",
                 "task_text": "Collect the pack", "severity": "Fatal"}
check("pure function: fires only on open GATE-PACK-COLLECT + pack file",
      pack_ingest.parse_pack_suggestion_warning([open_gate_row], True)
      and "[PARSE-PACK-AVAILABLE]" in
          pack_ingest.parse_pack_suggestion_warning([open_gate_row], True)
      and pack_ingest.parse_pack_suggestion_warning([open_gate_row], False) is None
      and pack_ingest.parse_pack_suggestion_warning(
          [dict(open_gate_row, status="Done")], True) is None
      and pack_ingest.parse_pack_suggestion_warning(
          [{"rule_code": "GATE-CSD", "status": "Open"}], True) is None
      and pack_ingest.parse_pack_suggestion_warning([], True) is None)

_orig_get_all = frappe_stub.get_all
frappe_stub.get_all = lambda doctype, filters=None, pluck=None, **k: (
    ["musina-pack.pdf"] if doctype == "File" else [])
warns = gate.submission_readiness_warnings(
    {"name": "BID-0001", "checklist": [open_gate_row]}, template_codes=[])
check("submission_readiness_warnings surfaces the suggestion when the gate "
      "is open and a .pdf is attached",
      any("[PARSE-PACK-AVAILABLE]" in w for w in warns))
warns_done = gate.submission_readiness_warnings(
    {"name": "BID-0001",
     "checklist": [dict(open_gate_row, status="Done")]}, template_codes=[])
frappe_stub.get_all = lambda doctype, filters=None, pluck=None, **k: []
warns_nofile = gate.submission_readiness_warnings(
    {"name": "BID-0001", "checklist": [open_gate_row]}, template_codes=[])
warns_noname = gate.submission_readiness_warnings(
    {"checklist": [open_gate_row]}, template_codes=[])
frappe_stub.get_all = _orig_get_all
check("silent when the gate is Done, no file is attached, or the bid has no "
      "name (guarded, advisory-only)",
      not any("[PARSE-PACK-AVAILABLE]" in w
              for w in warns_done + warns_nofile + warns_noname))

# --------------------------------------------------------------------------
# manifest + hard-rule hygiene
# --------------------------------------------------------------------------
print("== manifest + hygiene ==")
manifest = json.load(open(os.path.join(REPO, "tender/frappe/manifest.json")))
methods = manifest["app_type"]["control"]["hooks"]["whitelisted_methods"]
target = "{app_name}.tender.control.api.tenders.parse_tender_pack.parse_tender_pack"
check("parse_tender_pack registered in all three manifest families under "
      "app_type.control; tenant untouched; pypdf declared as a dependency",
      methods.get("{app_name}.api.tenders.parse_tender_pack") == target
      and methods.get("control:parse_tender_pack") == target
      and methods.get("control.control.api.tenders.parse_tender_pack") == target
      and manifest["app_type"]["tenant"] == {}
      and "pypdf" in manifest["app_type"]["control"]["dependencies"])
check("prior endpoints still registered (additive only)",
      all(key in methods for key in (
          "control:seed_bid_returnables", "control:dispatch_bid_pack",
          "control:generate_bid_pack", "control:get_pack_status")))

parser_sources = "".join(
    open(os.path.join(SRC, "parsing", fn)).read()
    for fn in ("__init__.py", "text_extract.py", "pack_parse.py", "pack_ingest.py"))
check("parsing modules are frappe-free, network-free and OCR-free (no "
      "frappe/requests/urllib/socket/http/tesseract import anywhere)",
      "import frappe" not in parser_sources
      and "import requests" not in parser_sources
      and "import urllib" not in parser_sources
      and "import socket" not in parser_sources
      and "import http" not in parser_sources
      and "tesseract" not in parser_sources.lower())
check("PDF library imports are lazy and guarded (module imported fine with "
      "or without pypdf; a BROKEN install also degrades; extractor-missing "
      "path proven above)",
      "from pypdf import" in parser_sources
      and open(os.path.join(SRC, "parsing/text_extract.py")).read()
          .count("except Exception") >= 2)
check("LF line endings, no CRLF in any new file",
      all(b"\r" not in open(os.path.join(SRC, p), "rb").read() for p in (
          "parsing/__init__.py", "parsing/text_extract.py",
          "parsing/pack_parse.py", "parsing/pack_ingest.py",
          "api/tenders/parse_tender_pack.py", "compliance/submission_gate.py")))

# --------------------------------------------------------------------------
failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL PR-D CHECKS PASSED")
