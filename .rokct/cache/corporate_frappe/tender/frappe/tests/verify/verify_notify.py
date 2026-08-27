#!/usr/bin/env python3
"""Standalone verification for the notification seam (plan #14).

frappe fully stubbed in-memory; the REAL modules are loaded from the repo
(the endpoint exec'd with the composer {app_name} placeholder substituted).
Proves:

Seam:  notify() passes the exact sendmail kwargs through, degrades
       gracefully on channel failure under the caller's error-log title,
       gates on User.receive_tender_notifications when (and only when)
       require_opt_in is set, filters blank recipients, refuses unknown
       channels without raising, and lets future channels plug in via
       register_channel without any new sendmail call site.
Equivalence: both prior direct frappe.sendmail call sites now send through
       the seam with byte-identical email content and unchanged behaviour -
       artifact_expiry keeps its opt-in skip, its subject/message bytes,
       its status writes and its error-log title; dispatch_bid_pack keeps
       its audit-only-on-accepted-send discipline, its degradation reason
       and its error-log title, and buyer mail stays confirm-gated, never
       opt-in-gated.
Single seam: frappe.sendmail( appears in exactly ONE module under src/ -
       notify.py.
"""

import importlib.util
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
frappe_stub.get_traceback = lambda: "traceback"

OPTED_IN = set()


def _user_opt_in(doctype, name, field):
    assert doctype == "User" and field == "receive_tender_notifications"
    return 1 if name in OPTED_IN else 0


frappe_stub.db = types.SimpleNamespace(
    get_value=_user_opt_in,
    exists=lambda *a, **k: False,
    get_single_value=lambda *a, **k: 0,
    commit=lambda: None,
)

sent = []


def fake_sendmail(recipients=None, subject=None, message=None, attachments=None):
    sent.append({"recipients": recipients, "subject": subject,
                 "message": message, "attachments": attachments})


frappe_stub.sendmail = fake_sendmail
logged = []
frappe_stub.log_error = lambda text, title: logged.append((title, text))

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


notify_mod = load_module("n_notify", os.path.join(SRC, "notify.py"))
notify = notify_mod.notify

# --------------------------------------------------------------------------
# seam: send path
# --------------------------------------------------------------------------
print("== seam: email send path ==")
check("email is the only built-in channel",
      notify_mod.registered_channels() == ["email"]
      and notify_mod.CHANNEL_EMAIL == "email")

result = notify(recipients=["a@example.co.za"], subject="Sub", message="Body")
check("accepted send passes the exact sendmail kwargs through "
      "(recipients/subject/message, attachments defaulting to None)",
      result["sent"] is True and result["channel"] == "email"
      and result["recipients"] == ["a@example.co.za"] and result["reason"] is None
      and sent == [{"recipients": ["a@example.co.za"], "subject": "Sub",
                    "message": "Body", "attachments": None}])

atts = [{"fname": "pack.html", "fcontent": "<html>PACK</html>"}]
notify(recipients=["b@example.co.za"], subject="S", message="M", attachments=atts)
check("attachments pass through untouched",
      sent[-1]["attachments"] is atts)

sent.clear()
result = notify(recipients=[None, "", "c@example.co.za"], subject="S", message="M")
check("blank/None recipients filtered out before the send",
      result["sent"] is True and result["recipients"] == ["c@example.co.za"]
      and sent[-1]["recipients"] == ["c@example.co.za"])

sent.clear()
logged.clear()
result = notify(recipients=[], subject="S", message="M")
result_none = notify(recipients=None, subject="S", message="M")
check("no addressable recipient -> nothing sent, nothing logged, "
      "reason no-recipients",
      result["sent"] is False and result["reason"] == "no-recipients"
      and result_none["sent"] is False and result_none["recipients"] == []
      and sent == [] and logged == [])

# --------------------------------------------------------------------------
# seam: opt-in gate
# --------------------------------------------------------------------------
print("== seam: require_opt_in gates on User.receive_tender_notifications ==")
OPTED_IN.clear()
OPTED_IN.add("in@example.co.za")

sent.clear()
result = notify(recipients=["in@example.co.za", "out@example.co.za"],
                subject="S", message="M", require_opt_in=True)
check("mixed list: only the opted-in recipient is kept and sent to",
      result["sent"] is True and result["recipients"] == ["in@example.co.za"]
      and sent[-1]["recipients"] == ["in@example.co.za"])

sent.clear()
logged.clear()
result = notify(recipients=["out@example.co.za"], subject="S", message="M",
                require_opt_in=True)
check("every recipient opted out -> the old per-call-site skip: no send, "
      "no log, reason no-recipients",
      result["sent"] is False and result["reason"] == "no-recipients"
      and sent == [] and logged == [])

sent.clear()
result = notify(recipients=["out@example.co.za"], subject="S", message="M")
check("without require_opt_in the flag is never consulted (buyer-facing "
      "mail must not be opt-in-gated)",
      result["sent"] is True and sent[-1]["recipients"] == ["out@example.co.za"])


def _raising_get_value(*a, **k):
    raise RuntimeError("custom field not installed")


frappe_stub.db.get_value = _raising_get_value
sent.clear()
result = notify(recipients=["in@example.co.za"], subject="S", message="M",
                require_opt_in=True)
check("opt-in read is missing-safe: a raising db read counts as NOT opted "
      "in, never a traceback",
      result["sent"] is False and result["reason"] == "no-recipients"
      and sent == [])
frappe_stub.db.get_value = _user_opt_in

# --------------------------------------------------------------------------
# seam: graceful degradation
# --------------------------------------------------------------------------
print("== seam: degradation - failures logged, never raised ==")


def broken_sendmail(**kwargs):
    raise RuntimeError("no outgoing email account")


frappe_stub.sendmail = broken_sendmail
logged.clear()
result = notify(recipients=["a@example.co.za"], subject="S", message="M",
                failure_log_title="Bid Pack Dispatch Failed")
check("channel failure -> sent False, reason send-failed, logged under the "
      "CALLER'S error-log title",
      result["sent"] is False and result["reason"] == "send-failed"
      and logged == [("Bid Pack Dispatch Failed", "traceback")])

logged.clear()
result = notify(recipients=["a@example.co.za"], subject="S", message="M")
check("default failure title used when the caller names none",
      result["sent"] is False
      and logged == [("Tender Notification Failed", "traceback")])


def broken_log_error(*a, **k):
    raise RuntimeError("error log unwritable")


frappe_stub.log_error = broken_log_error
result = notify(recipients=["a@example.co.za"], subject="S", message="M")
check("log_error itself raising is swallowed - the seam never raises",
      result["sent"] is False and result["reason"] == "send-failed")
frappe_stub.log_error = lambda text, title: logged.append((title, text))
frappe_stub.sendmail = fake_sendmail

sent.clear()
logged.clear()
result = notify(recipients=["a@example.co.za"], subject="S", message="M",
                channel="sms")
check("unknown channel -> refused gracefully: no send, reason "
      "unknown-channel, logged (not raised)",
      result["sent"] is False and result["reason"] == "unknown-channel"
      and sent == [] and len(logged) == 1 and "sms" in logged[0][1])

# --------------------------------------------------------------------------
# seam: channel pluggability
# --------------------------------------------------------------------------
print("== seam: future channels plug in via register_channel ==")
comms_sent = []
notify_mod.register_channel(
    "comms", lambda recipients=None, subject=None, message=None,
    attachments=None: comms_sent.append({"recipients": recipients,
                                         "subject": subject}))
sent.clear()
result = notify(recipients=["a@example.co.za"], subject="Via comms",
                message="M", channel="comms")
check("a registered channel receives the send and email is untouched",
      result["sent"] is True and result["channel"] == "comms"
      and comms_sent == [{"recipients": ["a@example.co.za"],
                          "subject": "Via comms"}]
      and sent == [] and "comms" in notify_mod.registered_channels())


def broken_channel(**kwargs):
    raise RuntimeError("comms module down")


notify_mod.register_channel("comms", broken_channel)
logged.clear()
result = notify(recipients=["a@example.co.za"], subject="S", message="M",
                channel="comms", failure_log_title="Comms Failed")
check("a pluggable channel failing degrades exactly like email (logged, "
      "sent False, never raised)",
      result["sent"] is False and result["reason"] == "send-failed"
      and logged == [("Comms Failed", "traceback")])

# --------------------------------------------------------------------------
# call-site equivalence: artifact_expiry
# --------------------------------------------------------------------------
print("== equivalence: artifact_expiry sends through the seam unchanged ==")


class FakeArtifact(dict):
    def __getattr__(self, key):
        return self.get(key)

    def compute_status(self):
        return self["_next_status"]

    def db_set(self, field, value, update_modified=True):
        self[field] = value
        self.setdefault("_db_set", []).append((field, value, update_modified))


expiry = load_module("n_artifact_expiry",
                     os.path.join(SRC, "compliance/artifact_expiry.py"))

ARTIFACTS = {
    "ART-1": FakeArtifact(name="ART-1", user="ayanda@example.co.za",
                          artifact_type="Tax Clearance / TCS PIN",
                          reference="TCS-123", status="Amber",
                          _next_status="Expired"),
    "ART-2": FakeArtifact(name="ART-2", user="busi@example.co.za",
                          artifact_type="BBBEE Certificate",
                          reference=None, status="Green",
                          _next_status="Amber"),
    "ART-3": FakeArtifact(name="ART-3", user="ayanda@example.co.za",
                          artifact_type="Letter of Good Standing",
                          reference="LGS-9", status="Green",
                          _next_status="Green"),
}
frappe_stub.get_all = lambda doctype, **k: (
    list(ARTIFACTS) if doctype == "Compliance Artifact" else [])
frappe_stub.get_doc = lambda doctype, name: ARTIFACTS[name]

OPTED_IN.clear()
OPTED_IN.add("ayanda@example.co.za")  # busi@ has NOT opted in
sent.clear()
logged.clear()
expiry.sweep_compliance_artifacts()

check("one email, to the opted-in owner only - the non-opted-in user's "
      "change stays silent exactly as before",
      len(sent) == 1 and sent[0]["recipients"] == ["ayanda@example.co.za"])
check("subject and message bytes unchanged from the pre-seam email",
      sent[0]["subject"] == "Tender compliance documents need attention"
      and sent[0]["message"] == (
          "The following standing compliance documents are expiring or "
          "expired:\n\n- Tax Clearance / TCS PIN (TCS-123): Expired")
      and sent[0]["attachments"] is None)
check("status writes unchanged: both changed artifacts written with "
      "update_modified=False (opted-in or not), unchanged artifact untouched",
      ARTIFACTS["ART-1"]["_db_set"] == [("status", "Expired", False)]
      and ARTIFACTS["ART-2"]["_db_set"] == [("status", "Amber", False)]
      and "_db_set" not in ARTIFACTS["ART-3"])

sent.clear()
frappe_stub.sendmail = broken_sendmail
OPTED_IN.add("busi@example.co.za")
ARTIFACTS["ART-2"]["status"] = "Green"  # make it change again
logged.clear()
expiry.sweep_compliance_artifacts()
check("sendmail failure degrades gracefully under the unchanged error-log "
      "title and the status write still lands",
      logged == [("Compliance Artifact Notification Failed", "traceback")]
      and ARTIFACTS["ART-2"]["status"] == "Amber")
frappe_stub.sendmail = fake_sendmail

calls = []
frappe_stub.get_all = lambda *a, **k: calls.append(a) or []
frappe_stub.conf = {"app_role": "tenant"}
expiry.sweep_compliance_artifacts()
check("non-control role: the sweep is a no-op (no reads, no sends)",
      calls == [])
frappe_stub.conf = {"app_role": "control"}
frappe_stub.get_all = lambda *a, **k: []

# --------------------------------------------------------------------------
# call-site equivalence: dispatch_bid_pack
# --------------------------------------------------------------------------
print("== equivalence: dispatch_bid_pack sends through the seam unchanged ==")


class FakeBidDoc(dict):
    def __getattr__(self, key):
        return self.get(key)

    def db_set(self, field, value):
        self[field] = value
        self.setdefault("_db_set", []).append((field, value))


for mod_name in ("_app_stub", "_app_stub.tender", "_app_stub.tender.control",
                 "_app_stub.tender.control.api",
                 "_app_stub.tender.control.api.tenders",
                 "_app_stub.tender.control.compliance"):
    sys.modules.setdefault(mod_name, types.ModuleType(mod_name))

BID = FakeBidDoc(name="BID-7", user="desk@example.com",
                 tender_title="Helpdesk Management System",
                 buyer_contact_email="scm@example.gov.za")
ent_stub = types.ModuleType("_app_stub.tender.control.api.tenders.tender_entitlement")
ent_stub.get_owned_bid = lambda name: BID
sys.modules["_app_stub.tender.control.api.tenders.tender_entitlement"] = ent_stub
sg_stub = types.ModuleType("_app_stub.tender.control.compliance.submission_gate")
sg_stub.validate_submission_readiness = lambda bid: []
sys.modules["_app_stub.tender.control.compliance.submission_gate"] = sg_stub
# the REAL seam, as the composed bench would import it
sys.modules["_app_stub.tender.control.notify"] = notify_mod

dispatch = load_endpoint("n_dispatch", "api/tenders/dispatch_bid_pack.py")

OPTED_IN.clear()  # nobody opted in - buyer mail must still go out
sent.clear()
result = dispatch.dispatch_bid_pack(
    "BID-7", mode="correspondence", confirm_email="scm@example.gov.za",
    subject="Clarification question", message="Please confirm the venue.")
check("correspondence dispatch sends through the seam with the exact "
      "pre-seam kwargs and writes the audit fields on the accepted send",
      result["sent"] is True and len(sent) == 1
      and sent[0] == {"recipients": ["scm@example.gov.za"],
                      "subject": "Clarification question",
                      "message": "Please confirm the venue.",
                      "attachments": None}
      and BID["dispatched_to"] == "scm@example.gov.za"
      and BID["dispatched_on"] == "2026-08-24 12:00:00")
check("buyer-contact mail is confirm-gated, never opt-in-gated: it went "
      "out with NOBODY opted in to tender notifications",
      len(OPTED_IN) == 0 and result["dispatched_to"] == "scm@example.gov.za")

BID2 = FakeBidDoc(name="BID-8", user="desk@example.com",
                  buyer_contact_email="x@example.gov.za")
ent_stub.get_owned_bid = lambda name: BID2
frappe_stub.sendmail = broken_sendmail
logged.clear()
result = dispatch.dispatch_bid_pack(
    "BID-8", mode="correspondence", confirm_email="x@example.gov.za",
    message="test")
check("send failure keeps the pre-seam degradation: sent False, the 'Email "
      "Account' reason, the unchanged error-log title, NO audit write",
      result["sent"] is False and "Email Account" in result["reason"]
      and logged == [("Bid Pack Dispatch Failed", "traceback")]
      and "dispatched_on" not in BID2 and "dispatched_to" not in BID2)
frappe_stub.sendmail = fake_sendmail

# --------------------------------------------------------------------------
# single seam
# --------------------------------------------------------------------------
print("== single seam: one sendmail call site under src/ ==")
sendmail_sites = []
for root, dirs, files in os.walk(SRC):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for filename in files:
        if not filename.endswith(".py"):
            continue
        path = os.path.join(root, filename)
        with open(path, encoding="utf-8") as f:
            if "frappe.sendmail(" in f.read():
                sendmail_sites.append(os.path.relpath(path, SRC))
check("frappe.sendmail( appears in exactly one module: notify.py",
      sendmail_sites == ["notify.py"])
check("both prior call sites now name the seam",
      "notify(" in open(os.path.join(SRC, "compliance/artifact_expiry.py"),
                        encoding="utf-8").read()
      and "notify(" in open(os.path.join(SRC, "api/tenders/dispatch_bid_pack.py"),
                            encoding="utf-8").read())
check("LF line endings, no CRLF, in the seam and both rewired call sites",
      all(b"\r" not in open(os.path.join(SRC, p), "rb").read()
          for p in ("notify.py", "compliance/artifact_expiry.py",
                    "api/tenders/dispatch_bid_pack.py")))
check("O-05: the suite runs with sys.dont_write_bytecode set",
      sys.dont_write_bytecode is True)

# --------------------------------------------------------------------------
failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL NOTIFY-SEAM CHECKS PASSED")
