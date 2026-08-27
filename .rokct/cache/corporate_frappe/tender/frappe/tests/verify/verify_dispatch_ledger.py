#!/usr/bin/env python3
"""Standalone verification for plan #11 (SDK-Assessment-2026-08-24): the
dispatch checksum / immutability ledger.

frappe fully stubbed in-memory; the real modules are loaded from the repo
(endpoints exec'd with the composer {app_name} placeholder substituted,
and the REAL compliance/dispatch_ledger.py wired under the placeholder
import path so the glue runs the genuine hashing). Proves:

Hashing:  sha256_hex is deterministic (known NIST vector), one encoding
          rule (str -> UTF-8 == bytes), and refuses non-payload types -
          no fingerprint of nothing, ever.
Records:  build_dispatch_record freezes the EXACT bytes handed to
          sendmail - per-attachment fname/sha256/size entries in send
          order, pack/manifest digests classified by the dispatch fname
          rule, correspondence recorded with the message digest and no
          fabricated attachment hashes.
Append-only: the Tender Dispatch Record controller refuses updates and
          deletes for everyone (ledger, not state); the doctype JSON
          grants no write/delete permission and every field is read-only.
Glue:     a successful dispatch appends one ledger record whose digests
          match the sent attachment bytes, stores those bytes as private
          Files on the bid, and returns the ledger summary; a failed
          sendmail appends NOTHING.
Failure isolation: a ledger write blowing up NEVER fails the dispatch -
          sent stays True, audit fields stand, the failure is logged; a
          File store failure drops only the file_url, never the digest.
Attest:   attach_returnable_artifact fingerprints the artifact bytes on
          attach and RE-hashes at attest time (later file edits are
          detectable via artifact_unaltered); detach clears the digest;
          a hashing failure never blocks the attach/attest.
"""

import hashlib
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


def throws(fn, needle):
    try:
        fn()
        return False
    except Thrown as e:
        return needle in str(e)


# --------------------------------------------------------------------------
# frappe stub
# --------------------------------------------------------------------------
class Thrown(Exception):
    pass


frappe_stub = types.ModuleType("frappe")
utils_stub = types.ModuleType("frappe.utils")
utils_stub.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
utils_stub.flt = lambda v, precision=None: float(v) if v not in (None, "") else 0.0
utils_stub.nowdate = lambda: "2026-08-24"
utils_stub.now = lambda: "2026-08-24 12:00:00"
utils_stub.getdate = lambda v=None: v
frappe_stub.utils = utils_stub

model_stub = types.ModuleType("frappe.model")
document_stub = types.ModuleType("frappe.model.document")


class StubDocument:
    """Just enough of frappe Document for the controller under test."""

    def __init__(self, **kwargs):
        self.__dict__["_values"] = dict(kwargs)
        self.__dict__["_is_new"] = kwargs.pop("_is_new", True)

    def __getattr__(self, key):
        return self.__dict__["_values"].get(key)

    def __setattr__(self, key, value):
        self.__dict__["_values"][key] = value

    def get(self, key, default=None):
        return self.__dict__["_values"].get(key, default)

    def is_new(self):
        return self.__dict__["_is_new"]


document_stub.Document = StubDocument
model_stub.document = document_stub


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
sys.modules["frappe.model"] = model_stub
sys.modules["frappe.model.document"] = document_stub


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


LEDGER_PATH = os.path.join(SRC, "compliance/dispatch_ledger.py")
ledger = load_module("dl_ledger", LEDGER_PATH)
# wire the REAL pure module under the composer import path, so the endpoint
# glue below exercises the genuine hashing, not a stub
sys.modules["_app_stub.tender.control.compliance.dispatch_ledger"] = ledger

# --------------------------------------------------------------------------
# hashing primitive
# --------------------------------------------------------------------------
print("== sha256_hex: determinism, one encoding rule, refusals ==")

NIST_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
check("known vector: sha256_hex('abc') matches the NIST test digest",
      ledger.sha256_hex("abc") == NIST_ABC
      and ledger.sha256_hex(b"abc") == NIST_ABC)
check("deterministic: repeated calls agree; bytearray hashes like bytes",
      ledger.sha256_hex("pack") == ledger.sha256_hex("pack")
      and ledger.sha256_hex(bytearray(b"pack")) == ledger.sha256_hex(b"pack"))
check("one encoding rule: str is hashed as its UTF-8 bytes (non-ASCII too)",
      ledger.sha256_hex("Musina R100 – café")
      == ledger.sha256_hex("Musina R100 – café".encode("utf-8")))
check("a single flipped byte changes the digest",
      ledger.sha256_hex("PACK v1") != ledger.sha256_hex("PACK v2"))


def raises_value_error(fn):
    try:
        fn()
        return False
    except ValueError:
        return True


check("refuses to fingerprint non-payloads: None and int raise ValueError",
      raises_value_error(lambda: ledger.sha256_hex(None))
      and raises_value_error(lambda: ledger.sha256_hex(42)))
check("payload_size counts the hashed bytes (UTF-8), refuses None",
      ledger.payload_size("abc") == 3
      and ledger.payload_size("café") == 5
      and raises_value_error(lambda: ledger.payload_size(None)))

# --------------------------------------------------------------------------
# attachment entries + digest classification
# --------------------------------------------------------------------------
print("== attachment entries and pack/manifest classification ==")

PACK_HTML = "<!DOCTYPE html><html>THE PACK AS SENT</html>"
MANIFEST_STR = json.dumps({"bid": "BID-7", "form_count": 12}, indent=2)
ATTACHMENTS = [
    {"fname": "BID-7-bid-pack.html", "fcontent": PACK_HTML},
    {"fname": "BID-7-manifest.json", "fcontent": MANIFEST_STR},
]

entries = ledger.build_attachment_entries(ATTACHMENTS)
check("entries preserve send order with fname/sha256/size per attachment",
      [e["fname"] for e in entries] == ["BID-7-bid-pack.html", "BID-7-manifest.json"]
      and entries[0]["sha256"] == hashlib.sha256(PACK_HTML.encode("utf-8")).hexdigest()
      and entries[1]["sha256"] == hashlib.sha256(MANIFEST_STR.encode("utf-8")).hexdigest()
      and entries[0]["size_bytes"] == len(PACK_HTML.encode("utf-8"))
      and entries[1]["size_bytes"] == len(MANIFEST_STR.encode("utf-8")))
check("None/empty attachments (correspondence tier) -> no entries",
      ledger.build_attachment_entries(None) == []
      and ledger.build_attachment_entries([]) == [])
p_sha, m_sha = ledger.classify_digests(entries)
check("classification: .html -> pack digest, -manifest.json -> manifest digest",
      p_sha == entries[0]["sha256"] and m_sha == entries[1]["sha256"])
check("no attachments -> empty digests, never a fabricated hash-of-nothing",
      ledger.classify_digests([]) == ("", ""))
check("first match wins; a stray .json is NOT mistaken for the manifest",
      ledger.classify_digests(ledger.build_attachment_entries([
          {"fname": "a-bid-pack-signed.html", "fcontent": "signed"},
          {"fname": "b-bid-pack.html", "fcontent": "second"},
          {"fname": "extra.json", "fcontent": "{}"},
      ])) == (ledger.sha256_hex("signed"), ""))

# --------------------------------------------------------------------------
# record building
# --------------------------------------------------------------------------
print("== build_dispatch_record: shape, digests, both tiers ==")

record = ledger.build_dispatch_record(
    bid="BID-7", mode="pack", recipient="scm@example.gov.za",
    subject="Bid submission: Helpdesk", message="Please find attached.",
    dispatched_on="2026-08-24 12:00:00", attachments=ATTACHMENTS,
    pack_signed=True)
check("pack record carries the full field set",
      set(record) == {"bid", "mode", "recipient", "subject", "dispatched_on",
                      "pack_signed", "pack_sha256", "manifest_sha256",
                      "message_sha256", "attachment_count", "attachments"})
check("pack record digests fingerprint the EXACT sent bytes",
      record["pack_sha256"] == hashlib.sha256(PACK_HTML.encode("utf-8")).hexdigest()
      and record["manifest_sha256"] == hashlib.sha256(MANIFEST_STR.encode("utf-8")).hexdigest()
      and record["message_sha256"] == ledger.sha256_hex("Please find attached.")
      and record["attachment_count"] == 2 and record["pack_signed"] == 1
      and record["bid"] == "BID-7" and record["recipient"] == "scm@example.gov.za"
      and record["dispatched_on"] == "2026-08-24 12:00:00")
check("record building is deterministic (same inputs -> identical record)",
      record == ledger.build_dispatch_record(
          bid="BID-7", mode="pack", recipient="scm@example.gov.za",
          subject="Bid submission: Helpdesk", message="Please find attached.",
          dispatched_on="2026-08-24 12:00:00", attachments=ATTACHMENTS,
          pack_signed=True))
corr = ledger.build_dispatch_record(
    bid="BID-8", mode="correspondence", recipient="bids@vcwater.example",
    subject="Clarification", message="Please confirm the briefing venue.",
    dispatched_on="2026-08-24 12:00:00", attachments=None, pack_signed=False)
check("correspondence record: message digest only - no attachment or pack "
      "digests, pack_signed 0",
      corr["mode"] == "correspondence" and corr["attachments"] == []
      and corr["attachment_count"] == 0 and corr["pack_sha256"] == ""
      and corr["manifest_sha256"] == "" and corr["pack_signed"] == 0
      and corr["message_sha256"] == ledger.sha256_hex(
          "Please confirm the briefing venue."))
check("no message body -> empty message digest (unknown stays unknown)",
      ledger.build_dispatch_record(
          bid="B", mode="correspondence", recipient="x@y", subject="s",
          message=None, dispatched_on="2026-08-24 12:00:00")["message_sha256"] == "")

# --------------------------------------------------------------------------
# artifact_unaltered
# --------------------------------------------------------------------------
print("== artifact_unaltered: edit detection, honest unknowns ==")

ARTIFACT_BYTES = b"%PDF-1.4 generated business profile"
stored = ledger.sha256_hex(ARTIFACT_BYTES)
check("no stored digest -> None (unknown), never a fabricated pass",
      ledger.artifact_unaltered(None, ARTIFACT_BYTES) is None
      and ledger.artifact_unaltered("  ", ARTIFACT_BYTES) is None)
check("matching bytes -> True (case/whitespace-tolerant stored digest)",
      ledger.artifact_unaltered(stored, ARTIFACT_BYTES) is True
      and ledger.artifact_unaltered(" " + stored.upper() + " ", ARTIFACT_BYTES) is True)
check("edited bytes -> False (the detectability the ledger exists for)",
      ledger.artifact_unaltered(stored, ARTIFACT_BYTES + b" EDITED") is False)

# --------------------------------------------------------------------------
# frappe-free discipline + doctype JSON shape
# --------------------------------------------------------------------------
print("== module discipline and doctype shape ==")

with open(LEDGER_PATH, encoding="utf-8") as f:
    ledger_source = f.read()
check("dispatch_ledger.py is frappe-free and placeholder-free (pure, "
      "standalone-testable - the renewal.py discipline)",
      "import frappe" not in ledger_source and "{app_name}" not in ledger_source)

with open(os.path.join(
        SRC, "doctype/tender_dispatch_record/tender_dispatch_record.json"),
        encoding="utf-8") as f:
    tdr_json = json.load(f)
check("Tender Dispatch Record doctype: every field read-only, and no role "
      "is granted write or delete",
      all(fld.get("read_only") == 1 or fld["fieldtype"] == "Check"
          for fld in tdr_json["fields"])
      and all(not p.get("write") and not p.get("delete")
              for p in tdr_json["permissions"])
      and any(p.get("create") for p in tdr_json["permissions"]))
check("ledger digests fit their fields (Data length 64 == hex sha256)",
      all(fld.get("length") == 64 for fld in tdr_json["fields"]
          if fld["fieldname"].endswith("_sha256")))

with open(os.path.join(
        SRC, "doctype/tender_bid_returnable/tender_bid_returnable.json"),
        encoding="utf-8") as f:
    tbr_json = json.load(f)
check("Tender Bid Returnable gained artifact_sha256 (read-only, length 64) "
      "and kept every pre-ledger field (additive only)",
      any(fld["fieldname"] == "artifact_sha256" and fld.get("read_only") == 1
          and fld.get("length") == 64 for fld in tbr_json["fields"])
      and {"ref_code", "title", "mandatory", "generated_artifact",
           "artifact_attested", "artifact_attached_on"} <= set(tbr_json["field_order"]))

# --------------------------------------------------------------------------
# append-only controller
# --------------------------------------------------------------------------
print("== Tender Dispatch Record controller: append-only, enforced in code ==")

tdr = load_module(
    "dl_tdr", os.path.join(
        SRC, "doctype/tender_dispatch_record/tender_dispatch_record.py"))

fresh = tdr.TenderDispatchRecord(bid="BID-7", _is_new=True)
try:
    fresh.validate()
    fresh_ok = True
except Thrown:
    fresh_ok = False
check("appending a new record validates cleanly", fresh_ok)
existing = tdr.TenderDispatchRecord(bid="BID-7", _is_new=False)
check("updating an existing record is refused for every role",
      throws(existing.validate, "Append-Only"))
check("deleting a record is refused for every role",
      throws(existing.on_trash, "Append-Only")
      and throws(fresh.on_trash, "Append-Only"))

# --------------------------------------------------------------------------
# dispatch glue: ledger appended on success, guarded on failure
# --------------------------------------------------------------------------
print("== dispatch glue: append on send, never fail the dispatch ==")


class FakeBidDoc(dict):
    def __getattr__(self, key):
        return self.get(key)

    def db_set(self, field, value):
        self[field] = value
        self.setdefault("_db_set", []).append((field, value))


ent_stub = types.ModuleType("_app_stub.tender.control.api.tenders.tender_entitlement")
sys.modules["_app_stub.tender.control.api.tenders.tender_entitlement"] = ent_stub

sg_stub = types.ModuleType("_app_stub.tender.control.compliance.submission_gate")
sg_stub.validate_submission_readiness = lambda bid: []
sys.modules["_app_stub.tender.control.compliance.submission_gate"] = sg_stub

gbp_stub = types.ModuleType("_app_stub.tender.control.api.tenders.generate_bid_pack")
gbp_stub.generate_bid_pack = lambda bid, sign=0: {
    "manifest": {"bid": bid, "form_count": 12},
    "html": PACK_HTML,
}
gbp_stub.load_profile = lambda user: (None, {})
sys.modules["_app_stub.tender.control.api.tenders.generate_bid_pack"] = gbp_stub

sent = []
frappe_stub.sendmail = lambda recipients=None, subject=None, message=None, \
    attachments=None: sent.append({
        "recipients": recipients, "subject": subject,
        "message": message, "attachments": attachments})

LEDGER_ROWS = []
FILE_STORE = []
FAIL_LEDGER_INSERT = []
FAIL_FILE_STORE = []


class FakeInsertDoc(dict):
    def __getattr__(self, key):
        return self.get(key)

    def insert(self, ignore_permissions=False):
        if self["doctype"] == "Tender Dispatch Record":
            if FAIL_LEDGER_INSERT:
                raise RuntimeError("db down")
            self["name"] = f"TDR-{len(LEDGER_ROWS) + 1:05d}"
            LEDGER_ROWS.append(self)
        elif self["doctype"] == "File":
            if FAIL_FILE_STORE:
                raise RuntimeError("file store down")
            self["file_url"] = f"/private/files/{self['file_name']}"
            FILE_STORE.append(self)
        return self


def fake_get_doc(*args, **kwargs):
    if args and isinstance(args[0], dict):
        return FakeInsertDoc(args[0])
    return None


frappe_stub.get_doc = fake_get_doc

logged = []
frappe_stub.log_error = lambda tb, title: logged.append(title)

# plan #14 landed the notify() seam in this endpoint: register the REAL
# notify.py under the stub root so the send path runs through the genuine
# seam (which makes the exact frappe.sendmail call this suite stubs).
sys.modules["_app_stub.tender.control.notify"] = load_module(
    "dl_notify", os.path.join(SRC, "notify.py"))

dispatch = load_endpoint("dl_dispatch", "api/tenders/dispatch_bid_pack.py")

BID = FakeBidDoc(name="BID-7", user="desk@example.com",
                 tender_slug="18-2025-26", tender_title="Helpdesk Management System",
                 submission_channel="Email allowed",
                 buyer_contact_email="scm@example.gov.za")
ent_stub.get_owned_bid = lambda name: BID

result = dispatch.dispatch_bid_pack("BID-7", mode="pack",
                                    confirm_email="scm@example.gov.za")
check("successful pack dispatch appends exactly one ledger record and "
      "reports it (recorded, record name, digests)",
      result["sent"] is True and result["ledger"]["recorded"] is True
      and len(LEDGER_ROWS) == 1 and result["ledger"]["record"] == "TDR-00001"
      and result["ledger"]["pack_sha256"] == ledger.sha256_hex(PACK_HTML))
row = LEDGER_ROWS[0]
sent_manifest = sent[0]["attachments"][1]["fcontent"]
check("the record fingerprints the EXACT bytes handed to sendmail (pack "
      "HTML + manifest JSON string + message body)",
      row["pack_sha256"] == hashlib.sha256(
          sent[0]["attachments"][0]["fcontent"].encode("utf-8")).hexdigest()
      and row["manifest_sha256"] == hashlib.sha256(
          sent_manifest.encode("utf-8")).hexdigest()
      and row["message_sha256"] == ledger.sha256_hex(sent[0]["message"]))
check("the record ties the send together: bid, mode, recipient, audit "
      "timestamp, session user, attachment count",
      row["bid"] == "BID-7" and row["mode"] == "pack"
      and row["recipient"] == "scm@example.gov.za"
      and row["dispatched_on"] == BID["dispatched_on"]
      and row["dispatched_by"] == "desk@example.com"
      and row["attachment_count"] == 2 and row["pack_signed"] == 0)
row_entries = json.loads(row["attachments_json"])
check("the ACTUALLY-SENT bytes are stored as private Files on the bid, and "
      "attachments_json links each entry to its stored copy in send order",
      len(FILE_STORE) == 2
      and all(f["attached_to_doctype"] == "Tender Bid"
              and f["attached_to_name"] == "BID-7" and f["is_private"] == 1
              for f in FILE_STORE)
      and FILE_STORE[0]["content"] == sent[0]["attachments"][0]["fcontent"]
      and FILE_STORE[1]["content"] == sent_manifest
      and [e["fname"] for e in row_entries]
      == ["BID-7-bid-pack.html", "BID-7-manifest.json"]
      and row_entries[0]["file_url"] == "/private/files/dispatched-BID-7-bid-pack.html"
      and result["ledger"]["sent_files"] == [e["file_url"] for e in row_entries])

corr_result = dispatch.dispatch_bid_pack(
    "BID-7", mode="correspondence", confirm_email="scm@example.gov.za",
    subject="Clarification", message="Please confirm the briefing venue.")
check("correspondence sends are ledgered too: message digest, no pack/"
      "manifest digests, no stored files",
      corr_result["ledger"]["recorded"] is True and len(LEDGER_ROWS) == 2
      and LEDGER_ROWS[1]["mode"] == "correspondence"
      and LEDGER_ROWS[1]["message_sha256"]
      == ledger.sha256_hex("Please confirm the briefing venue.")
      and LEDGER_ROWS[1]["pack_sha256"] == ""
      and LEDGER_ROWS[1]["attachment_count"] == 0 and len(FILE_STORE) == 2)

# signed pack: digest must be of the signed regeneration actually attached
gbp_stub.load_profile = lambda user: (
    {"signature_image_processed": "/files/sig.png"}, {})
gbp_stub.generate_bid_pack = lambda bid, sign=0: {
    "manifest": {"bid": bid, "form_count": 12},
    "html": PACK_HTML + ("<!--SIGNED-->" if sign else ""),
}
signed_result = dispatch.dispatch_bid_pack("BID-7", mode="pack",
                                           confirm_email="scm@example.gov.za")
check("a signed-pack send records pack_signed=1 and the digest of the "
      "SIGNED bytes that went out",
      signed_result["pack_signed"] is True
      and LEDGER_ROWS[2]["pack_signed"] == 1
      and LEDGER_ROWS[2]["pack_sha256"]
      == ledger.sha256_hex(PACK_HTML + "<!--SIGNED-->")
      and LEDGER_ROWS[2]["pack_sha256"] != LEDGER_ROWS[0]["pack_sha256"])
gbp_stub.load_profile = lambda user: (None, {})
gbp_stub.generate_bid_pack = lambda bid, sign=0: {
    "manifest": {"bid": bid, "form_count": 12}, "html": PACK_HTML}

# failed sendmail: nothing sent -> nothing ledgered
frappe_stub.sendmail = lambda **kwargs: (_ for _ in ()).throw(
    RuntimeError("no outgoing email account"))
fail_result = dispatch.dispatch_bid_pack(
    "BID-7", mode="correspondence", confirm_email="scm@example.gov.za",
    message="test")
check("a FAILED send appends NOTHING to the ledger (records mean 'this "
      "left the system', never 'this was attempted')",
      fail_result["sent"] is False and len(LEDGER_ROWS) == 3
      and "ledger" not in fail_result)
frappe_stub.sendmail = lambda recipients=None, subject=None, message=None, \
    attachments=None: sent.append({
        "recipients": recipients, "subject": subject,
        "message": message, "attachments": attachments})

# failure isolation: ledger write blowing up never fails the dispatch
FAIL_LEDGER_INSERT.append(True)
BID.pop("_db_set", None)
logged[:] = []
guard_result = dispatch.dispatch_bid_pack("BID-7", mode="pack",
                                          confirm_email="scm@example.gov.za")
check("FAILURE ISOLATION: a ledger insert exception never fails the "
      "dispatch - sent=True, audit fields written, recorded=False with a "
      "note, failure logged",
      guard_result["sent"] is True
      and guard_result["ledger"]["recorded"] is False
      and "note" in guard_result["ledger"]
      and ("dispatched_on", "2026-08-24 12:00:00") in BID["_db_set"]
      and ("dispatched_to", "scm@example.gov.za") in BID["_db_set"]
      and logged == ["Dispatch Ledger Write Failed"]
      and len(LEDGER_ROWS) == 3)
FAIL_LEDGER_INSERT[:] = []

# file-store failure: the digest is the evidence, the stored copy is sugar
FAIL_FILE_STORE.append(True)
logged[:] = []
fs_result = dispatch.dispatch_bid_pack("BID-7", mode="pack",
                                       confirm_email="scm@example.gov.za")
fs_entries = json.loads(LEDGER_ROWS[3]["attachments_json"])
check("a File store failure drops only the file_url - the record still "
      "appends with its digests, and the failure is logged per file",
      fs_result["sent"] is True and fs_result["ledger"]["recorded"] is True
      and len(LEDGER_ROWS) == 4
      and LEDGER_ROWS[3]["pack_sha256"] == ledger.sha256_hex(PACK_HTML)
      and all(e["file_url"] is None for e in fs_entries)
      and fs_result["ledger"]["sent_files"] == []
      and logged == ["Dispatch Ledger File Store Failed"] * 2)
FAIL_FILE_STORE[:] = []

# --------------------------------------------------------------------------
# attest-time artifact hashing
# --------------------------------------------------------------------------
print("== attest-time hashing: fingerprint as reviewed, guarded ==")


class FakeRow(dict):
    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        self[key] = value


class FakeBidDocSaving(FakeBidDoc):
    def save(self, ignore_permissions=False):
        pass


class FakeFile:
    def __init__(self, name, attached_to, content):
        self.name = name
        self.attached_to = attached_to
        self.content = content
        self.raise_on_read = False

    def get(self, key, default=None):
        if key == "attached_to_doctype":
            return "Tender Bid"
        if key == "attached_to_name":
            return self.attached_to
        return getattr(self, key, default)

    def get_content(self):
        if self.raise_on_read:
            raise RuntimeError("backing file unreadable")
        return self.content


FILES = {"/files/profile.pdf": FakeFile("F1", "BID-16", b"PROFILE v1")}
frappe_stub.db.get_value = lambda doctype, filters, field=None: (
    FILES[filters["file_url"]].name
    if doctype == "File" and filters.get("file_url") in FILES else None)
frappe_stub.get_doc = lambda *args, **kwargs: (
    next(f for f in FILES.values() if f.name == args[1])
    if args and args[0] == "File" else None)
frappe_stub.db.commit = lambda: None

attach = load_endpoint("dl_attach", "api/tenders/attach_returnable_artifact.py")

ROW = FakeRow(ref_code="16", title="Company Profile", mandatory=1)
ABID = FakeBidDocSaving(name="BID-16", user="desk@example.com",
                        custom_returnables=[ROW])
ent_stub.get_owned_bid = lambda name: ABID

res_attach = attach.attach_returnable_artifact(
    "BID-16", "16", file_url="/files/profile.pdf")
check("attach fingerprints the attached bytes into artifact_sha256 and "
      "returns the digest",
      res_attach["artifact_sha256"] == ledger.sha256_hex(b"PROFILE v1")
      and ROW["artifact_sha256"] == ledger.sha256_hex(b"PROFILE v1")
      and res_attach["satisfied"] is False)

# the file is edited AFTER attach but BEFORE attest: the attest-time hash
# must fingerprint the bytes the desk actually reviewed
FILES["/files/profile.pdf"].content = b"PROFILE v2 (edited before review)"
res_attest = attach.attach_returnable_artifact("BID-16", "16", attest=1)
check("attest RE-hashes at attest time: the stored digest moves to the "
      "reviewed bytes, not the first-attached bytes",
      res_attest["artifact_attested"] is True and res_attest["satisfied"] is True
      and res_attest["artifact_sha256"]
      == ledger.sha256_hex(b"PROFILE v2 (edited before review)")
      and res_attest["artifact_sha256"] != ledger.sha256_hex(b"PROFILE v1"))
check("artifact_unaltered closes the loop: True against the current bytes, "
      "False once the file is edited after attestation",
      ledger.artifact_unaltered(
          ROW["artifact_sha256"], b"PROFILE v2 (edited before review)") is True
      and ledger.artifact_unaltered(
          ROW["artifact_sha256"], b"PROFILE v3 (edited after attest)") is False)

res_detach = attach.attach_returnable_artifact("BID-16", "16", detach=1)
check("detach clears the digest with the artifact and attestation",
      res_detach["artifact_sha256"] is None and ROW["artifact_sha256"] is None
      and res_detach["satisfied"] is False)

# guarded hashing: an unreadable backing file never blocks the flow
FILES["/files/profile.pdf"].raise_on_read = True
logged[:] = []
res_guard = attach.attach_returnable_artifact(
    "BID-16", "16", file_url="/files/profile.pdf", attest=1)
check("FAILURE ISOLATION: a hashing failure never blocks attach/attest - "
      "attested with an EMPTY digest (never fabricated), failure logged",
      res_guard["artifact_attested"] is True and res_guard["satisfied"] is True
      and res_guard["artifact_sha256"] is None
      and logged == ["Returnable Artifact Hash Failed"])
FILES["/files/profile.pdf"].raise_on_read = False

res_both = attach.attach_returnable_artifact(
    "BID-16", "16", file_url="/files/profile.pdf", attest=1)
check("attach+attest in one call hashes the bytes being attested",
      res_both["satisfied"] is True and res_both["artifact_sha256"]
      == ledger.sha256_hex(b"PROFILE v2 (edited before review)"))

# --------------------------------------------------------------------------
failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL DISPATCH-LEDGER CHECKS PASSED")
