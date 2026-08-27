#!/usr/bin/env python3
"""Standalone verification for PR-E - the F-02 CALIBRATION round (post-PR #43
review, findings doc "F-02 follow-up") plus the F-15(b) studio hook and the
two review follow-ups (signed-pack dispatch, cover-price lint basis).

Every calibration check runs BEFORE-BROKEN / AFTER-FIXED: the "before"
evidence re-runs the pre-calibration pattern (quoted inline from PR #43's
pack_parse.py) against text shaped EXACTLY like the real Musina buyer PDF
(65pp, fetched from musina.gov.za - the fixtures below quote its verbatim
lines), proving the miss; the "after" check proves the shipped parser now
reads it. The four verified failure modes:

1. section-5.1 items written dot-style ("a.") where the old paren-letter
   regex demanded "a)";
2. "Form A" on its own line with the ALL-CAPS title lines below (old Form
   regex demanded same-line titles);
3. "TENDER" / "NUMBER 18-2025/26" wrapped across two lines (both old
   tender-number regexes were single-line);
4. template_code linking matched only the ref_code while the MBD/SBD token
   lives in the item TITLE - it could never fire on the documented styles.

Plus the follow-up's two smaller notes (the >=2-per-letter tradeoff is now
documented in the parser; this verify suite is COMMITTED to the tree so the
claimed counts are re-runnable), the F-15(b) generated-artifact hook gated
generated-AND-attested like the F-13 dispatch outputs, the signed-pack
dispatch fix and the explicit/tolerant cover-price comparison basis.

O-01 round (F-02 residual): the bare regime-code headings the calibration
round still missed - "MBD 6.1" / "MBD8" / "MBD 9" standing alone with no
title text ON the line - are now a fourth accepted item family
(heading-only, never an inline mention; lookahead-title join reused where
a title follows). Verified BEFORE-BROKEN/AFTER-FIXED below and, with the
real PDF present, 21/21 returnables.

Optionally verifies against the REAL buyer PDF: set MUSINA_PACK_PDF to the
downloaded pack (or drop it at data/musina-18-2025-26-pack.pdf - it is NOT
committed; fetch it from the musina.gov.za download page quoted in
tender/mock-samples/18-2025-26-musina-helpdesk/README.md). Without it the
real-PDF section reports SKIP lines, not failures.
"""

import importlib.util
import json
import os
import re
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
# frappe stub (endpoints only - the parsing/lint modules import none)
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


text_extract = load_module("e_text_extract", os.path.join(SRC, "parsing/text_extract.py"))
pack_parse = load_module("e_pack_parse", os.path.join(SRC, "parsing/pack_parse.py"))
pack_ingest = load_module("e_pack_ingest", os.path.join(SRC, "parsing/pack_ingest.py"))
pack_lints = load_module("e_pack_lints", os.path.join(SRC, "compliance/pack_lints.py"))
gate = load_module("e_submission_gate", os.path.join(SRC, "compliance/submission_gate.py"))
pack_builder = load_module("e_pack_builder", os.path.join(SRC, "pack_builder.py"))

QUOTED = pack_parse.QUOTED
NOT_FOUND = pack_parse.NOT_FOUND

# --------------------------------------------------------------------------
# fixtures - VERBATIM lines from the real Musina buyer PDF's text layer
# (pypdf extraction of the 65-page official pack for TENDER 18-2025/26)
# --------------------------------------------------------------------------
REAL_51_TEXT = """5. Mandatory bid requirements to assess bidder's ability to execute the bid
5.1 To ensure your proposal is considered for evaluation, the bidder must ensure that their
proposal includes the following:
a. The proposal must include and detail the proposed system solution functionality that meets the
minimum specifications requirement of the tender.
b. The proposal must include and detail the tariff costs for the Call center Management system
solution.
c. The bidder must attach a detailed project plan for the system, with clear timelines/timeframes,
outlining milestones from project inception to completion.
d. Hand-completed and signed tender document.
e. The bidder must specify the system software proposed for use on the project and attach a
system description as proof.
f. The bidder must provide proof of execution of similar work and solutions, of at least three (3
contactable references, and appointment letters of a similar service rendered with a contract
term /duration of at least 12 months as proof.
g. Risk management plan associated with the project
h. User Operational Training Plan (for all system users, system administrators, and mobile app
users)
i. Attach the Recent Audited financial statements (previous 3 financial years)
j. Attach Service Provider Banking Rating [A to C] not older than 3 months.
k. Detailed pricing per price schedule.
l. The solution/proposal must provide documented information that outlines the following:
"""

REAL_FORMS_TEXT = """MUSINA LOCAL MUNICIPALITY
Form A

(To be completed by Bidder)

FORM OF BID

TO: Municipal Manager
MUSINA LOCAL MUNICIPALITY
Form B

(To be completed by Bidder)

SIGNATORY AUTHORISATION

I/We the undersigned, am/are authorised to enter into this contract on behalf
MUSINA LOCAL MUNICIPALITY

Form D

(To be completed by Bidder)

CERTIFICATE OF PREFERENCE CLAIMED BY BIDDER FOR LOCAL CONTENT AND
SABS MARK

1. The attention of Bidders is directed to the preferences summarized in Section
MUSINA LOCAL MUNICIPALITY
Form E

(To be completed by Bidder)

CONTRACT BETWEEN THE EMPLOYER AND BIDDER IN TERMS OF SECTION 37(2) OF
THE OCCUPATIONAL HEALTH AND SAFETY ACT

The Employer and the Bidder hereby agree, in terms of the provisions of Section
"""

REAL_ANNEXURE_TEXT = """ANNEXURE C

MBD 4

DECLARATION OF INTEREST

1. No bid will be accepted from persons in the service of the state.
"""

REAL_TENDER_NO_TEXT = """YOU ARE HEREBY INVITED TO BID FOR THE FOLLOWING TENDER:
SERVICE PROVIDER FOR THE PROVISION OF AN INTERACTIVE CLOUD-BASED
CUSTOMER SERVICE TICKETING AND HELPDESK MANAGEMENT SYSTEM FOR
A PERIOD OF THREE YEARS

TENDER
NUMBER 18-2025/26
"""

# the pre-calibration patterns, quoted from PR #43's pack_parse.py - the
# BEFORE-BROKEN evidence recomputes each miss with these
OLD_RE_ITEM_PAREN_LETTER = re.compile(r"^\(?([a-z])\)\s+(\S.{2,140})$")
OLD_RE_ITEM_FORM = re.compile(r"^form\s+([A-Z])\b\s*[:–—\-]?\s*(\S.{2,140})$", re.I)
OLD_RE_TENDER_NO_LABELLED = pack_parse.RE_TENDER_NO_LABELLED  # unchanged, single-line use was the bug
OLD_RE_TENDER_NO_HEADING = pack_parse.RE_TENDER_NO_HEADING

# --------------------------------------------------------------------------
# fix 1 - dot-style list letters ("a." as well as "a)" / "(a)")
# --------------------------------------------------------------------------
print("== calibration fix 1: dot-style 5.1 list ('a.' style) ==")
real_51_lines = [ln.strip() for ln in REAL_51_TEXT.splitlines() if ln.strip()]
check("BEFORE-BROKEN: the old '(a)'-only regex matches ZERO of the real "
      "pack's dot-style 5.1 lines",
      not any(OLD_RE_ITEM_PAREN_LETTER.match(ln) for ln in real_51_lines))
p51 = pack_parse.parse_pack_text(REAL_51_TEXT)
codes_51 = {i["ref_code"] for i in p51["returnables"]["items"]}
check("AFTER-FIXED: all twelve 5.1(a)..5.1(l) items extract from the real "
      "dot-style list, section-coded",
      {f"5.1({letter})" for letter in "abcdefghijkl"} <= codes_51)
item_a = [i for i in p51["returnables"]["items"] if i["ref_code"] == "5.1(a)"][0]
check("dot-style item quotes its verbatim source line",
      item_a["source_line"].startswith("a. The proposal must include"))
check("paren and bracket spellings still parse (no regression): '(a) x' "
      "and 'a) x' both extract in list mode",
      {i["ref_code"] for i in pack_parse.parse_pack_text(
          "returnable documents\n(a) first thing here\nb) second thing here\n"
      )["returnables"]["items"]} == {"(a)", "(b)"})

# --------------------------------------------------------------------------
# fix 2 - bare "Form X" marker, ALL-CAPS title on following lines
# --------------------------------------------------------------------------
print("== calibration fix 2: Form marker and title on separate lines ==")
real_form_lines = [ln.strip() for ln in REAL_FORMS_TEXT.splitlines() if ln.strip()]
check("BEFORE-BROKEN: the old same-line Form regex matches ZERO real "
      "pack Form lines (titles live lines below)",
      not any(OLD_RE_ITEM_FORM.match(ln) for ln in real_form_lines))
pf = pack_parse.parse_pack_text(REAL_FORMS_TEXT)
forms = {i["ref_code"]: i for i in pf["returnables"]["items"]}
check("AFTER-FIXED: Forms A/B/D/E extract with their ALL-CAPS titles "
      "joined across the wrap",
      forms["Form A"]["title"] == "FORM OF BID"
      and forms["Form B"]["title"] == "SIGNATORY AUTHORISATION"
      and forms["Form D"]["title"]
      == "CERTIFICATE OF PREFERENCE CLAIMED BY BIDDER FOR LOCAL CONTENT AND SABS MARK"
      and forms["Form E"]["title"]
      == "CONTRACT BETWEEN THE EMPLOYER AND BIDDER IN TERMS OF SECTION 37(2) OF THE OCCUPATIONAL HEALTH AND SAFETY ACT")
check("the parenthetical '(To be completed by Bidder)' instruction line is "
      "skipped, never harvested as a title",
      all("To be completed" not in i["title"] for i in pf["returnables"]["items"]))
check("joined quote discipline: source_line spans the marker and title "
      "lines verbatim, newline-separated",
      forms["Form A"]["source_line"] == "Form A\nFORM OF BID"
      and forms["Form D"]["source_line"]
      == "Form D\nCERTIFICATE OF PREFERENCE CLAIMED BY BIDDER FOR LOCAL CONTENT AND\nSABS MARK")
check("same-line 'Form A - Form of Bid' style still parses identically "
      "(no regression on the documented style)",
      pack_parse.parse_pack_text("Form A - Form of Bid\nForm B - Signatory Authorisation\n")
      ["returnables"]["items"][0]["title"] == "Form of Bid")
check("a bare 'Form A' followed by prose (no ALL-CAPS title) is NOT "
      "harvested - no guessing",
      pack_parse.parse_pack_text(
          "Form A\nplease complete all sections in full before returning\n"
      )["returnables"]["count"] == 0)
pann = pack_parse.parse_pack_text(REAL_ANNEXURE_TEXT)
ann_items = {i["ref_code"]: i for i in pann["returnables"]["items"]}
check("bare 'ANNEXURE C' joins to its 'MBD 4' + 'DECLARATION OF INTEREST' "
      "title lines (the real pack labels MBD 4 as Annexure C)",
      ann_items.get("Annexure C", {}).get("title") == "MBD 4 DECLARATION OF INTEREST")

# --------------------------------------------------------------------------
# fix 3 - tender number wrapped across two lines
# --------------------------------------------------------------------------
print("== calibration fix 3: TENDER / NUMBER 18-2025/26 wrap ==")
real_no_lines = [ln.strip() for ln in REAL_TENDER_NO_TEXT.splitlines() if ln.strip()]
check("BEFORE-BROKEN: neither old single-line tender-number regex hits any "
      "single real line (the label wraps)",
      not any(OLD_RE_TENDER_NO_LABELLED.search(ln) and
              any(ch.isdigit() for ch in OLD_RE_TENDER_NO_LABELLED.search(ln).group(1))
              for ln in real_no_lines)
      and not any(OLD_RE_TENDER_NO_HEADING.search(ln) for ln in real_no_lines))
pno = pack_parse.parse_pack_text(REAL_TENDER_NO_TEXT)
check("AFTER-FIXED: tender number QUOTED '18-2025/26' across the wrap",
      pno["tender_number"]["status"] == QUOTED
      and pno["tender_number"]["value"] == "18-2025/26")
check("wrapped quote discipline: source_line is the two verbatim lines "
      "newline-joined ('TENDER' + 'NUMBER 18-2025/26')",
      pno["tender_number"]["source_line"] == "TENDER\nNUMBER 18-2025/26")
single_and_wrap = pack_parse.parse_pack_text(
    "Tender No: 8/2/RNM0614\nTENDER\nNUMBER 99-9999/99\n")
check("single-line hits always win over pair joins - wrap tolerance can "
      "never change a previously-QUOTED result",
      single_and_wrap["tender_number"]["value"] == "8/2/RNM0614")
check("wrap tolerance applies to the other scalar labels too: a closing "
      "date wrapped after its label still parses",
      pack_parse.parse_pack_text("Closing date for submissions\n11 May 2026 at 11h00\n")
      ["closing_date"]["value"] == "2026-05-11")
garbage = pack_parse.parse_pack_text(
    "Dear Sir or Madam\nPlease find attached our covering letter.\n"
    "We look forward to hearing from you.\n")
check("wrap tolerance never invents values: garbage text still all NOT-FOUND",
      all(garbage[k]["status"] == NOT_FOUND for k in
          ("tender_number", "closing_date", "functionality",
           "preference_system", "submission_channel", "wet_ink")))

# --------------------------------------------------------------------------
# fix 4 - template linking from a leading MBD/SBD token in the TITLE
# --------------------------------------------------------------------------
print("== calibration fix 4: template_code linking from the item title ==")
KNOWN = ["MBD1", "MBD4", "MBD6.1", "MBD8", "MBD9", "SBD3.x", "ICT-CAPABILITY"]
check("BEFORE-BROKEN: ref-code-only linking finds nothing for 'Annexure C' "
      "/ 'Form B' style refs (the token lives in the title)",
      pack_ingest._template_code_for("Annexure C", KNOWN) is None
      and pack_ingest._template_code_for("Form B", KNOWN) is None)
check("AFTER-FIXED: a LEADING 'MBD 4' title token exact-links to MBD4",
      pack_ingest._template_code_from_title("MBD 4 DECLARATION OF INTEREST", KNOWN) == "MBD4")
check("dotted codes link too ('MBD 6.1 - Preference Points Claim Form')",
      pack_ingest._template_code_from_title(
          "MBD 6.1 - Preference Points Claim Form", KNOWN) == "MBD6.1")
check("exact-only discipline holds: a MID-title token does not link, an "
      "unknown code does not link",
      pack_ingest._template_code_from_title(
          "Preference Points Claim Form, PPR 2022 (RNM/MBD 6.1)", KNOWN) is None
      and pack_ingest._template_code_from_title("MBD 77 Unknown Form", KNOWN) is None)
preview = pack_ingest.build_ingest_preview(pann, bid=None, known_template_codes=KNOWN)
ann_row = [r for r in preview["proposed_returnables"] if r["ref_code"] == "Annexure C"][0]
check("end to end: the real pack's 'Annexure C' row now proposes "
      "template_code MBD4 from its title",
      ann_row["template_code"] == "MBD4")
check("ref-code linking still wins where it applies (a captured 'MBD 8' "
      "ref still links by ref)",
      pack_ingest._template_code_for("MBD 8", KNOWN) == "MBD8")

# --------------------------------------------------------------------------
# O-01 - bare regime-code headings ("MBD 6.1" / "MBD8" / "MBD 9" alone)
# --------------------------------------------------------------------------
print("== O-01: bare regime-code headings (the last 3 of the real pack's 21) ==")

# VERBATIM stripped lines from the real Musina buyer PDF's text layer: the
# MBD 6.1 / MBD8 / MBD 9 pages open with the bare code alone on its line
# (the pack itself spells MBD8 unspaced). The first MBD8 occurrence is a
# running header above a signature block - dot leaders, NO title; the
# second carries the true title page. MBD 9 appears twice, titled both
# times.
REAL_REGIME_TEXT = """50
MBD 6.1

PREFERENCE POINTS CLAIM FORM IN TERMS OF THE PREFERENTIAL PROCUREMENT
REGULATIONS 2022

This preference form must form part of all tenders invited.  It contains general
information and serves as a claim form for preference points for specific goals.

MBD8

……………………………………….
SIGNATURE(S) OF TENDERER(S)

55

MBD8

DECLARATION OF BIDDER’S PAST SUPPLY CHAIN MANAGEMENT
PRACTICES

1 This Municipal Bidding Document must form part of all bids invited.

58

MBD 9

CERTIFICATE OF INDEPENDENT BID DETERMINATION

1 This Municipal Bidding Document (MBD) must form part of all bids¹ invited.

59

MBD 9

CERTIFICATE OF INDEPENDENT BID DETERMINATION

I, the undersigned, in submitting the accompanying bid:
"""

real_regime_lines = [ln.strip() for ln in REAL_REGIME_TEXT.splitlines() if ln.strip()]
bare_code_lines = [ln for ln in real_regime_lines if ln in ("MBD 6.1", "MBD8", "MBD 9")]
check("BEFORE-BROKEN: no pre-O-01 item family matches any of the real "
      "pack's bare MBD 6.1/MBD8/MBD 9 heading lines",
      len(bare_code_lines) == 5
      and not any(fam.match(ln) for ln in bare_code_lines for fam in (
          pack_parse.RE_ITEM_ANNEXURE, pack_parse.RE_ITEM_FORM,
          pack_parse.RE_ITEM_FORM_BARE, pack_parse.RE_ITEM_ANNEXURE_BARE,
          pack_parse.RE_ITEM_LETTERED, pack_parse.RE_ITEM_NUMBERED,
          pack_parse.RE_ITEM_PAREN_LETTER)))
pr = pack_parse.parse_pack_text(REAL_REGIME_TEXT)
regime_items = {i["ref_code"]: i for i in pr["returnables"]["items"]}
check("AFTER-FIXED: the three regime headings extract, space-normalised "
      "(MBD8 -> 'MBD 8'), repeated headings deduped to one item each",
      set(regime_items) == {"MBD 6.1", "MBD 8", "MBD 9"}
      and pr["returnables"]["count"] == 3)
check("titles join across the wrap exactly as the Form family does",
      regime_items["MBD 6.1"]["title"]
      == "PREFERENCE POINTS CLAIM FORM IN TERMS OF THE PREFERENTIAL PROCUREMENT REGULATIONS 2022"
      and regime_items["MBD 8"]["title"]
      == "DECLARATION OF BIDDER’S PAST SUPPLY CHAIN MANAGEMENT PRACTICES"
      and regime_items["MBD 9"]["title"] == "CERTIFICATE OF INDEPENDENT BID DETERMINATION")
check("quote discipline: source_line spans the verbatim heading + title "
      "lines, newline-joined; the pack's own MBD8 spelling is preserved in "
      "the quote",
      regime_items["MBD 6.1"]["source_line"]
      == "MBD 6.1\nPREFERENCE POINTS CLAIM FORM IN TERMS OF THE PREFERENTIAL PROCUREMENT\nREGULATIONS 2022"
      and regime_items["MBD 8"]["source_line"]
      == "MBD8\nDECLARATION OF BIDDER’S PAST SUPPLY CHAIN MANAGEMENT\nPRACTICES"
      and regime_items["MBD 9"]["source_line"]
      == "MBD 9\nCERTIFICATE OF INDEPENDENT BID DETERMINATION")
check("title completion, never value change: the titleless running-header "
      "MBD8 (dot leaders below it) is captured alone with an EMPTY title, "
      "then the titled occurrence fills it in",
      pack_parse.parse_pack_text(
          "MBD8\n……………………………………….\nSIGNATURE(S) OF TENDERER(S)\n"
      )["returnables"]["items"][0]["title"] == ""
      and pack_parse.parse_pack_text(
          "MBD8\n……………………………………….\nSIGNATURE(S) OF TENDERER(S)\n"
      )["returnables"]["items"][0]["source_line"] == "MBD8")
check("HEADING-ONLY discipline: inline mentions of the same codes in body "
      "text NEVER match ('...complete MBD 6.1 and return it...')",
      pack_parse.parse_pack_text(
          "The bidder must complete MBD 6.1 and return it with the bid.\n"
          "Refer to MBD8 for the required declaration.\n"
          "the attached Certificate of Bid Determination (MBD 9) is binding.\n"
      )["returnables"]["count"] == 0)
check("a trailing colon on the bare heading is tolerated ('MBD 9:'), same "
      "as the other bare markers",
      pack_parse.parse_pack_text(
          "MBD 9:\nCERTIFICATE OF INDEPENDENT BID DETERMINATION\n"
      )["returnables"]["items"][0]["ref_code"] == "MBD 9")
check("consumed-title suppression: the 'MBD 4' line joined into "
      "'Annexure C's title is NOT re-harvested as its own regime item "
      "(the real pack's ANNEXURE C page parses to exactly one item)",
      {i["ref_code"] for i in pack_parse.parse_pack_text(REAL_ANNEXURE_TEXT)
       ["returnables"]["items"]} == {"Annexure C"})
regime_preview = pack_ingest.build_ingest_preview(pr, bid=None, known_template_codes=KNOWN)
regime_rows = {r["ref_code"]: r for r in regime_preview["proposed_returnables"]}
check("template linking via the existing exact-token mechanism: "
      "'MBD 6.1'/'MBD 8'/'MBD 9' link MBD6.1/MBD8/MBD9 as Buyer Form rows",
      regime_rows["MBD 6.1"]["template_code"] == "MBD6.1"
      and regime_rows["MBD 8"]["template_code"] == "MBD8"
      and regime_rows["MBD 9"]["template_code"] == "MBD9"
      and all(regime_rows[c]["category"] == "Buyer Form" for c in regime_rows))
fixture_codes = {t["template_code"] for t in json.load(open(os.path.join(
    REPO, "tender/frappe/fixtures/tender_form_templates.json")))}
check("the shipped template fixture set really carries MBD6.1/MBD8/MBD9 "
      "(the linking above is not hypothetical)",
      {"MBD6.1", "MBD8", "MBD9"} <= fixture_codes)

# --------------------------------------------------------------------------
# the follow-up's two smaller notes
# --------------------------------------------------------------------------
print("== follow-up notes: >=2-per-letter documented; suite committed ==")
parser_src = open(os.path.join(SRC, "parsing/pack_parse.py"), encoding="utf-8").read()
check("note 1: the >=2-per-letter tradeoff is documented IN the parser "
      "(calibration note naming the deliberate single-item drop)",
      "CALIBRATION NOTE" in parser_src and ">= 2" in parser_src
      and "single-item lettered schedule" in parser_src.replace("\n\t# ", " ").replace("\n# ", " ").replace("  ", " ")
      or ("CALIBRATION NOTE" in parser_src and "single-item" in parser_src))
check("note 1 behaviour unchanged: a lone lettered line is still not a "
      "schedule (deliberate tradeoff kept)",
      pack_parse.parse_pack_text("A4 paper must be used for all correspondence.\n")
      ["returnables"]["count"] == 0)
check("note 2: the verification suites are COMMITTED to the tree "
      "(wave1/2a/2b/3/pr_c/pr_d/pr_e all present beside this file)",
      all(os.path.exists(os.path.join(HERE, f"verify_{name}.py")) for name in
          ("wave1", "wave2_pr_a", "wave2_pr_b", "wave3", "pr_c", "pr_d", "pr_e")))

# --------------------------------------------------------------------------
# review follow-up (ii) - cover-price lint comparison basis
# --------------------------------------------------------------------------
print("== review follow-up: cover-price lint explicit/tolerant basis ==")
grid_3yr = [
    {"period_label": "Year 1", "once_off": 50000, "annual_total": 120000},
    {"period_label": "Year 2", "annual_total": 126000},
    {"period_label": "Year 3", "annual_total": 132300},
    {"period_label": "Call tariff", "unit_tariff": 350},
]
check("BEFORE-BROKEN premise fixed: a quotation priced YEAR-1-ONLY "
      "(R170,000 vs 3-year grid) no longer false-positives",
      pack_lints.pricing_reconciliation_warnings(grid_3yr, cover_price=170000) == [])
check("full-term cover still reconciles silently (R428,300)",
      pack_lints.pricing_reconciliation_warnings(grid_3yr, cover_price=428300) == [])
w = pack_lints.pricing_reconciliation_warnings(grid_3yr, cover_price=999999)
check("a cover matching NEITHER basis still warns, naming both grid totals "
      "explicitly (full-term and first-period)",
      len(w) == 1 and pack_lints.COVER_MISMATCH_TAG in w[0]
      and "428,300.00" in w[0] and "170,000.00" in w[0] and "999,999.00" in w[0]
      and "neither" in w[0])

# --------------------------------------------------------------------------
# review follow-up (i) - dispatch sends the SIGNED pack when generable
# --------------------------------------------------------------------------
print("== review follow-up: dispatch_bid_pack sends the signed pack ==")


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


for mod_name in ("_app_stub", "_app_stub.tender", "_app_stub.tender.control",
                 "_app_stub.tender.control.api", "_app_stub.tender.control.api.tenders",
                 "_app_stub.tender.control.compliance", "_app_stub.tender.control.parsing"):
    sys.modules.setdefault(mod_name, types.ModuleType(mod_name))

ent_stub = types.ModuleType("_app_stub.tender.control.api.tenders.tender_entitlement")
sys.modules["_app_stub.tender.control.api.tenders.tender_entitlement"] = ent_stub
sg_stub = types.ModuleType("_app_stub.tender.control.compliance.submission_gate")
sg_stub.validate_submission_readiness = lambda bid: []
sys.modules["_app_stub.tender.control.compliance.submission_gate"] = sg_stub

SIGN_CALLS = []
gbp_stub = types.ModuleType("_app_stub.tender.control.api.tenders.generate_bid_pack")
gbp_stub.generate_bid_pack = lambda bid, sign=0: (
    SIGN_CALLS.append(sign) or {
        "manifest": {"bid": bid, "form_count": 12},
        "html": "<!DOCTYPE html><html>SIGNED PACK</html>" if sign else
                "<!DOCTYPE html><html>REVIEW PACK</html>",
    })
PROFILE = {}
gbp_stub.load_profile = lambda user: (PROFILE or None, {})
sys.modules["_app_stub.tender.control.api.tenders.generate_bid_pack"] = gbp_stub

sent = []
frappe_stub.sendmail = lambda **kw: sent.append(kw)

# dispatch now sends through the REAL notification seam (plan #14): register
# the real notify.py under the stub root so the endpoint exercises the seam
# end-to-end; frappe.sendmail stays the mocked transport underneath.
sys.modules["_app_stub.tender.control.notify"] = load_module(
    "e_notify", os.path.join(SRC, "notify.py"))

dispatch = load_endpoint("e_dispatch", "api/tenders/dispatch_bid_pack.py")

BID = FakeBidDoc(name="BID-7", user="desk@example.com",
                 submission_channel="Email allowed",
                 buyer_contact_email="scm@example.gov.za")
ent_stub.get_owned_bid = lambda name: BID

PROFILE.clear()
result_unsigned = dispatch.dispatch_bid_pack(
    "BID-7", mode="pack", confirm_email="scm@example.gov.za")
check("no signature image on the profile -> the unsigned pack goes out "
      "exactly as before (sign=0, original filename, pack_signed False)",
      SIGN_CALLS == [0] and result_unsigned["pack_signed"] is False
      and sent[-1]["attachments"][0]["fname"] == "BID-7-bid-pack.html"
      and "REVIEW PACK" in sent[-1]["attachments"][0]["fcontent"])

PROFILE.update({"signature_image_processed": "/files/sig-clean.png"})
result_signed = dispatch.dispatch_bid_pack(
    "BID-7", mode="pack", confirm_email="scm@example.gov.za")
check("BEFORE-BROKEN premise fixed: with a signature image the dispatched "
      "pack is the SIGNED regeneration (sign=1), not the unsigned review pack",
      SIGN_CALLS == [0, 1] and result_signed["pack_signed"] is True
      and "SIGNED PACK" in sent[-1]["attachments"][0]["fcontent"])
check("the signed dispatch names itself: attachment filename carries "
      "-signed and the result reports pack_signed",
      sent[-1]["attachments"][0]["fname"] == "BID-7-bid-pack-signed.html")
check("correspondence mode never regenerates or attaches any pack (signed "
      "or not)",
      dispatch.dispatch_bid_pack(
          "BID-7", mode="correspondence", confirm_email="scm@example.gov.za",
          message="Written query")["pack_attached"] is False
      and SIGN_CALLS == [0, 1] and sent[-1]["attachments"] is None)

# --------------------------------------------------------------------------
# F-15(b) - generated-artifact hook, gated generated-AND-attested
# --------------------------------------------------------------------------
print("== F-15(b): studio hook - attach, attest, gate, render ==")


class FakeRow(dict):
    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        self[key] = value


check("pure gate: no artifact -> no failure; artifact unattested -> "
      "failure with the tag; attested -> clean",
      pack_lints.unattested_artifact_failures([{"ref_code": "16"}]) == []
      and len(pack_lints.unattested_artifact_failures(
          [{"ref_code": "16", "generated_artifact": "/files/profile.pdf"}])) == 1
      and pack_lints.UNATTESTED_ARTIFACT_TAG in pack_lints.unattested_artifact_failures(
          [{"ref_code": "16", "generated_artifact": "/files/profile.pdf"}])[0]
      and pack_lints.unattested_artifact_failures(
          [{"ref_code": "16", "generated_artifact": "/files/profile.pdf",
            "artifact_attested": 1}]) == [])
check("validate_submission_readiness includes the attestation gate "
      "(unattested artifact fails readiness; attested bid is clean)",
      any("RETURNABLE-ARTIFACT-UNATTESTED" in f for f in gate.validate_submission_readiness(
          FakeBidDoc(custom_returnables=[
              {"ref_code": "16", "generated_artifact": "/files/profile.pdf"}],
              functionality_mode="No scored functionality")))
      and gate.validate_submission_readiness(
          FakeBidDoc(custom_returnables=[
              {"ref_code": "16", "generated_artifact": "/files/profile.pdf",
               "artifact_attested": 1}],
              functionality_mode="No scored functionality")) == [])

FILES = {}
frappe_stub.db.get_value = lambda doctype, filters, field=None: (
    FILES.get(filters.get("file_url"), {}).get("name") if doctype == "File" else None)
frappe_stub.get_doc = lambda doctype, name: (
    [f for f in FILES.values() if f["name"] == name][0] if doctype == "File" else None)

attach = load_endpoint("e_attach", "api/tenders/attach_returnable_artifact.py")

ROW = FakeRow(ref_code="16", title="Company Profile", mandatory=1)
ABID = FakeBidDoc(name="BID-16", user="desk@example.com", custom_returnables=[ROW])
ent_stub.get_owned_bid = lambda name: ABID
FILES["/files/profile.pdf"] = {
    "name": "F1", "attached_to_doctype": "Tender Bid", "attached_to_name": "BID-16"}
FILES["/files/foreign.pdf"] = {
    "name": "F2", "attached_to_doctype": "Tender Bid", "attached_to_name": "BID-99"}

res_attach = attach.attach_returnable_artifact("BID-16", "16", file_url="/files/profile.pdf")
check("attach records the artifact + audit timestamp but NOT satisfied "
      "(unattested), and saves the bid",
      res_attach["generated_artifact"] == "/files/profile.pdf"
      and res_attach["satisfied"] is False and res_attach["artifact_attested"] is False
      and res_attach["artifact_attached_on"] and ABID.saved == 1
      and "UNATTESTED" in res_attach["note"])
res_attest = attach.attach_returnable_artifact("BID-16", "16", attest=1)
check("attest=1 on the attached artifact flips it to satisfied "
      "(generated-and-attested)",
      res_attest["satisfied"] is True and res_attest["artifact_attested"] is True)
check("a file attached to ANOTHER bid is refused (entitlement discipline)",
      throws(lambda: attach.attach_returnable_artifact(
          "BID-16", "16", file_url="/files/foreign.pdf"), "not attached to this bid"))
check("an unknown file_url is refused",
      throws(lambda: attach.attach_returnable_artifact(
          "BID-16", "16", file_url="/files/nope.pdf"), "File Not Found"))
check("an unknown ref_code is refused",
      throws(lambda: attach.attach_returnable_artifact(
          "BID-16", "Form Z", file_url="/files/profile.pdf"), "Returnable Not Found"))
check("attest with nothing attached is refused; a bare call is refused",
      throws(lambda: attach.attach_returnable_artifact(
          "BID-16", "16", detach=1) and attach.attach_returnable_artifact(
          "BID-16", "16", attest=1), "No Artifact Attached")
      and throws(lambda: attach.attach_returnable_artifact("BID-16", "16"),
                 "Nothing To Do"))
check("re-attaching a NEW artifact resets the attestation (attest never "
      "carries over to a different document)",
      (attach.attach_returnable_artifact(
          "BID-16", "16", file_url="/files/profile.pdf", attest=1)["satisfied"] is True)
      and (attach.attach_returnable_artifact(
          "BID-16", "16", file_url="/files/profile.pdf")["artifact_attested"] is False))
res_detach = attach.attach_returnable_artifact("BID-16", "16", detach=1)
check("detach clears artifact, attestation and timestamp",
      res_detach["generated_artifact"] is None and res_detach["satisfied"] is False
      and res_detach["artifact_attached_on"] is None)

# render states (fold of the studio-hook first pass + attestation caveat)
CTX = {"bid_name": "BID-16", "generated_on": "2026-08-21"}


def profile_regime(extra):
    row = {"form_code": "16", "form_name": "Company Profile", "mandatory": 1,
           "kill_note": "", "template_code": None, "guidance": "",
           "category": "Technical Returnable"}
    row.update(extra)
    return {"regime_code": "MBD", "regime_name": "Municipal (MBD forms)",
            "forms": [row]}


plain_html = pack_builder.render_pack_html(
    pack_builder.build_pack(profile_regime({}), {}, {}, CTX, []), CTX)
check("no-hook rows render byte-identically (no studio/artifact notices)",
      plain_html == pack_builder.render_pack_html(
          pack_builder.build_pack(profile_regime(
              {"studio_scope": None, "generated_artifact": None}), {}, {}, CTX, []), CTX)
      and "GENERATE VIA STUDIO" not in plain_html
      and "SATISFIED BY GENERATED ARTIFACT" not in plain_html)
scoped_html = pack_builder.render_pack_html(
    pack_builder.build_pack(profile_regime(
        {"studio_scope": "Business Profile"}), {}, {}, CTX, []), CTX)
check("scope-only row renders the GENERATE VIA STUDIO pointer, placeholder "
      "stays",
      "GENERATE VIA STUDIO" in scoped_html and "Business Profile" in scoped_html
      and "No field template exists" in scoped_html)
unattested_pack = pack_builder.build_pack(profile_regime(
    {"studio_scope": "Business Profile",
     "generated_artifact": "/files/umzansi-company-profile-a4.pdf"}), {}, {}, CTX, [])
unattested_html = pack_builder.render_pack_html(unattested_pack, CTX)
check("artifact row renders SATISFIED provenance, suppresses the "
      "placeholder, and (unattested) carries the NOT YET ATTESTED caveat",
      "SATISFIED BY GENERATED ARTIFACT" in unattested_html
      and "umzansi-company-profile-a4.pdf" in unattested_html
      and "No field template exists" not in unattested_html
      and "NOT YET ATTESTED" in unattested_html)
attested_pack = pack_builder.build_pack(profile_regime(
    {"studio_scope": "Business Profile",
     "generated_artifact": "/files/umzansi-company-profile-a4.pdf",
     "artifact_attested": 1}), {}, {}, CTX, [])
attested_html = pack_builder.render_pack_html(attested_pack, CTX)
check("attested artifact drops the caveat; manifest rows carry "
      "generated + attested flags",
      "NOT YET ATTESTED" not in attested_html
      and attested_pack["manifest"]["forms"][0]["generated"] is True
      and attested_pack["manifest"]["forms"][0]["attested"] is True
      and unattested_pack["manifest"]["forms"][0]["attested"] is False)

seed_src = open(os.path.join(SRC, "api/tenders/seed_bid_returnables.py"), encoding="utf-8").read()
seed_mod = load_endpoint("e_seed", "api/tenders/seed_bid_returnables.py")
check("seeding whitelist EXCLUDES the studio/artifact fields - one bid's "
      "artifact never seeds another as satisfied",
      not ({"studio_scope", "generated_artifact", "artifact_attested",
            "artifact_attached_on"} & set(seed_mod.RETURNABLE_FIELDS)))

returnable_json = json.load(open(os.path.join(
    SRC, "doctype/tender_bid_returnable/tender_bid_returnable.json")))
fieldnames = [f["fieldname"] for f in returnable_json["fields"]]
check("doctype carries the full hook field set (studio_scope, "
      "generated_artifact, artifact_attested, artifact_attached_on)",
      all(f in fieldnames for f in (
          "studio_scope", "generated_artifact", "artifact_attested",
          "artifact_attached_on")))

manifest = json.load(open(os.path.join(REPO, "tender/frappe/manifest.json")))
methods = manifest["app_type"]["control"]["hooks"]["whitelisted_methods"]
check("attach_returnable_artifact registered in all three manifest cmd "
      "families",
      all(key in methods for key in (
          "{app_name}.api.tenders.attach_returnable_artifact",
          "control:attach_returnable_artifact",
          "control.control.api.tenders.attach_returnable_artifact")))

# --------------------------------------------------------------------------
# the REAL 65-page Musina buyer PDF (optional - set MUSINA_PACK_PDF)
# --------------------------------------------------------------------------
print("== REAL Musina buyer PDF (65pp, TENDER 18-2025/26) ==")
REAL_PDF = os.environ.get("MUSINA_PACK_PDF") or os.path.join(
    HERE, "data", "musina-18-2025-26-pack.pdf")
if os.path.exists(REAL_PDF):
    extraction = text_extract.extract_pack_text(open(REAL_PDF, "rb").read())
    check("real PDF text layer extracts (65 pages)",
          extraction["status"] == "ok" and extraction["pages"] == 65)
    real = pack_parse.parse_pack_text(extraction["text"])
    real_items = {i["ref_code"] for i in real["returnables"]["items"]}
    expected = {f"5.1({letter})" for letter in "abcdefghijkl"} | {
        "Form A", "Form B", "Form C", "Form D", "Form E", "Annexure C",
        "MBD 6.1", "MBD 8", "MBD 9"}
    check("REAL PACK: ALL 21 of the pack's known returnables extract "
          "(twelve 5.1 items + Forms A-E + Annexure C/MBD 4 + the O-01 "
          "bare MBD 6.1/MBD8/MBD 9 headings; was 18 before O-01)",
          real["returnables"]["count"] == 21 and expected == real_items)
    real_regime = {i["ref_code"]: i for i in real["returnables"]["items"]
                   if i["style"] == "regime"}
    check("REAL PACK: the three regime headings quote their verbatim "
          "heading+title lines (MBD8 spelled unspaced by the pack itself)",
          real_regime["MBD 6.1"]["source_line"].startswith(
              "MBD 6.1\nPREFERENCE POINTS CLAIM FORM")
          and real_regime["MBD 8"]["source_line"]
          == "MBD8\nDECLARATION OF BIDDER’S PAST SUPPLY CHAIN MANAGEMENT\nPRACTICES"
          and real_regime["MBD 9"]["source_line"]
          == "MBD 9\nCERTIFICATE OF INDEPENDENT BID DETERMINATION")
    check("REAL PACK: tender number QUOTED '18-2025/26' across the "
          "TENDER/NUMBER wrap (was NOT-FOUND)",
          real["tender_number"]["status"] == QUOTED
          and real["tender_number"]["value"] == "18-2025/26"
          and real["tender_number"]["source_line"] == "TENDER\nNUMBER 18-2025/26")
    check("REAL PACK: no scalar regressed - closing 2026-05-11 11:00, "
          "80/20, Physical tender box, wet-ink all still QUOTED from the "
          "same lines",
          real["closing_date"]["value"] == "2026-05-11"
          and real["closing_date"]["time"] == "11:00"
          and real["closing_date"]["source_line"] == "CLOSING DATE:  11 MAY 2026 @ 11:00"
          and real["preference_system"]["value"] == "80/20"
          and real["submission_channel"]["value"] == "Physical tender box"
          and real["wet_ink"]["status"] == QUOTED
          and "COMPLETED IN INK" in real["wet_ink"]["source_line"])
    check("REAL PACK: functionality still correctly NOT-FOUND (this pack "
          "has no scored stage) - wrap tolerance invented nothing",
          real["functionality"]["status"] == NOT_FOUND
          and real["functionality"]["value"] is None)
    real_preview = pack_ingest.build_ingest_preview(
        real, bid=None, known_template_codes=KNOWN)
    real_ann = [r for r in real_preview["proposed_returnables"]
                if r["ref_code"] == "Annexure C"]
    real_prev_rows = {r["ref_code"]: r for r in real_preview["proposed_returnables"]}
    check("REAL PACK: ingest preview proposes 21 rows; Annexure C links "
          "MBD4 from its title and the three regime rows link "
          "MBD6.1/MBD8/MBD9 by ref code",
          len(real_preview["proposed_returnables"]) == 21
          and real_ann and real_ann[0]["template_code"] == "MBD4"
          and real_prev_rows["MBD 6.1"]["template_code"] == "MBD6.1"
          and real_prev_rows["MBD 8"]["template_code"] == "MBD8"
          and real_prev_rows["MBD 9"]["template_code"] == "MBD9")
else:
    print("SKIP real-PDF checks: pack not found at " + REAL_PDF)
    print("SKIP   fetch it from the musina.gov.za download page quoted in")
    print("SKIP   tender/mock-samples/18-2025-26-musina-helpdesk/README.md")
    print("SKIP   and set MUSINA_PACK_PDF (real-PDF verification still owed)")

# --------------------------------------------------------------------------
# hygiene
# --------------------------------------------------------------------------
print("== hygiene ==")
TOUCHED = (
    "parsing/pack_parse.py", "parsing/pack_ingest.py",
    "compliance/pack_lints.py", "compliance/submission_gate.py",
    "api/tenders/attach_returnable_artifact.py",
    "api/tenders/dispatch_bid_pack.py", "api/tenders/generate_bid_pack.py",
    "api/tenders/seed_bid_returnables.py", "pack_builder.py",
)
check("LF line endings, no CRLF in any touched module",
      all(b"\r" not in open(os.path.join(SRC, p), "rb").read() for p in TOUCHED))
check("parser modules stay frappe-free / network-free / OCR-free",
      all(token not in open(os.path.join(SRC, "parsing/pack_parse.py")).read()
          + open(os.path.join(SRC, "parsing/pack_ingest.py")).read()
          for token in ("import frappe", "requests.", "urllib", "tesseract")))
check("O-05: the suite runs with sys.dont_write_bytecode set, so in-tree "
      "runs leave no __pycache__ litter under src/",
      sys.dont_write_bytecode is True)

# --------------------------------------------------------------------------
failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL PR-E CHECKS PASSED")
