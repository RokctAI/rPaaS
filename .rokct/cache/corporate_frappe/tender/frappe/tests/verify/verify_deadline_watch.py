#!/usr/bin/env python3
"""Standalone verification for the bid deadline watcher (plan #10).

frappe fully stubbed in-memory; the REAL modules are loaded from the repo
(deadline_watch's standalone fallback pulls in the real submission_gate,
suitability and notify seam modules). Proves:

Window:    only active bids (Watching/Preparing) closing inside
           [today, today + N] earn a closing reminder - past closings and
           closings beyond the window stay silent; TODAY/TOMORROW named.
Detection: the reminder lists the submission-gate failure list verbatim
           (open Fatal checklist items, unattested generated artifacts)
           plus mandatory returnables with no artifact attached yet -
           disjoint sets, no double-counting.
No-notify: a bid inside the window with NOTHING open sends nothing; a
           user with no dirty bids gets no email; non-opted-in users get
           no email even with dirty bids; non-control role is a no-op.
Briefings: real upcoming briefing_date_and_time on the bid's cached
           catalog card inside the window reminds IN ADVANCE (compulsory
           flagged as a fatal gate); placeholder dates (0001-01-01), past
           briefings, out-of-window briefings, unparseable text, missing
           cards and an unavailable cache all stay silent.
Config:    N reads Tender Control Settings.deadline_watch_days (default 7,
           0/blank/unreadable falls back); the doctype ships the field.
Wiring:    daily scheduler entry in the manifest beside the existing
           tasks; the watcher sends ONLY through the notify() seam with
           require_opt_in, its own error-log title, and no sendmail call
           site of its own.
"""

import datetime
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
frappe_stub.get_traceback = lambda: "traceback"

OPTED_IN = set()
SETTINGS = {"deadline_watch_days": 0}


def _db_get_value(doctype, name, field):
    if doctype == "User" and field == "receive_tender_notifications":
        return 1 if name in OPTED_IN else 0
    return None


frappe_stub.db = types.SimpleNamespace(
    get_value=_db_get_value,
    exists=lambda *a, **k: False,
    get_single_value=lambda doctype, field: SETTINGS.get(field, 0),
    commit=lambda: None,
)

BIDS = {}
GET_ALL_CALLS = []


def _get_all(doctype, filters=None, fields=None, pluck=None, **k):
    GET_ALL_CALLS.append((doctype, filters))
    if doctype == "Tender Bid":
        assert filters == {"status": ["in", ["Watching", "Preparing"]]}
        assert pluck == "name"
        return [name for name, bid in BIDS.items()
                if bid.get("status") in ("Watching", "Preparing")]
    return []  # Tender Compliance Rule etc.: no fixture rules in this harness


frappe_stub.get_all = _get_all
frappe_stub.get_doc = lambda doctype, name: BIDS[name]

CATALOG = []


class FakeCache:
    def get_value(self, key):
        assert key == "opp_data_tenders"
        return CATALOG


frappe_stub.cache = lambda: FakeCache()

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


dw = load_module("d_deadline_watch", os.path.join(SRC, "compliance/deadline_watch.py"))


class FakeBid(dict):
    def __getattr__(self, key):
        return self.get(key)


TODAY = datetime.date(2026, 8, 24)
OPEN_GATE = [{"severity": "Fatal", "status": "Open", "rule_code": "GATE-CSD",
              "task_text": "Produce a CSD registration report"}]

# --------------------------------------------------------------------------
# config: N from Tender Control Settings, default-safe
# --------------------------------------------------------------------------
print("== config: deadline_watch_days ==")
check("default window is 7 days and 0/blank falls back to it",
      dw.DEFAULT_DEADLINE_WATCH_DAYS == 7 and dw.deadline_watch_days() == 7)
SETTINGS["deadline_watch_days"] = 3
check("a configured window is read from Tender Control Settings",
      dw.deadline_watch_days() == 3)
SETTINGS["deadline_watch_days"] = 0


def _raising_single(*a, **k):
    raise RuntimeError("no settings doctype")


frappe_stub.db.get_single_value = _raising_single
check("an unreadable setting falls back to the default instead of raising",
      dw.deadline_watch_days() == 7)
frappe_stub.db.get_single_value = lambda doctype, field: SETTINGS.get(field, 0)

settings_json = json.load(open(os.path.join(
    SRC, "doctype/tender_control_settings/tender_control_settings.json")))
fieldnames = [f["fieldname"] for f in settings_json["fields"]]
field = [f for f in settings_json["fields"] if f["fieldname"] == "deadline_watch_days"]
check("Tender Control Settings ships deadline_watch_days (Int, default 7) "
      "and every prior field stays intact",
      field and field[0]["fieldtype"] == "Int" and field[0]["default"] == "7"
      and all(f in fieldnames for f in (
          "tender_country", "enforce_submission_gates", "last_fetched_release_id",
          "refetch_window_ids", "max_ids_per_run")))

# --------------------------------------------------------------------------
# window selection
# --------------------------------------------------------------------------
print("== window selection: [today, today + N] and nothing else ==")
dirty = {"checklist": list(OPEN_GATE)}


def lines_for(closing, window=7, extra=None, card=None):
    bid = FakeBid(name="BID-W", user="u@example.co.za",
                  tender_title="Helpdesk Management System",
                  closing_date=closing, **(extra if extra is not None else dirty))
    return dw.bid_deadline_lines(bid, TODAY, window, card)


check("closing at the window edge (today + N) is included",
      any("closes in 7 days (2026-08-31)" in line for line in lines_for("2026-08-31")))
check("closing one day beyond the window stays silent",
      lines_for("2026-09-01") == [])
check("a PAST closing stays silent - that bid is a post-mortem, not a "
      "reminder (KILL-01 already fired)",
      lines_for("2026-08-23") == [])
check("closing today is named 'closes TODAY'",
      any("closes TODAY (2026-08-24)" in line for line in lines_for("2026-08-24")))
check("closing tomorrow is named 'closes TOMORROW'",
      any("closes TOMORROW (2026-08-25)" in line for line in lines_for("2026-08-25")))
check("no closing date -> no closing block",
      lines_for(None) == [])
check("a date-object closing date works like the string form (frappe rows)",
      any("closes in 3 days (2026-08-27)" in line
          for line in lines_for(datetime.date(2026, 8, 27))))
check("the window honours the configured N (closing in 5 days, N=3 -> silent)",
      lines_for("2026-08-29", window=3) == []
      and lines_for("2026-08-27", window=3) != [])

# --------------------------------------------------------------------------
# gate / returnable detection
# --------------------------------------------------------------------------
print("== detection: gate failures + mandatory returnables without artifacts ==")
bid = FakeBid(name="BID-1", user="u@example.co.za", closing_date="2026-08-27",
              checklist=list(OPEN_GATE),
              custom_returnables=[
                  {"ref_code": "Form A", "title": "Form of Bid", "mandatory": 1},
                  {"ref_code": "Form B", "title": "Signatory Authorisation",
                   "mandatory": 0},
                  {"ref_code": "Form C", "title": "Company Profile", "mandatory": 1,
                   "generated_artifact": "/files/profile.md",
                   "artifact_attested": 0},
              ])
issues = dw.open_deadline_issues(bid)
check("the submission-gate failure list is reused verbatim (open Fatal "
      "checklist item named with its rule code)",
      any("Fatal checklist item still open: Produce a CSD registration "
          "report [GATE-CSD]" in i for i in issues))
check("a mandatory returnable with NO artifact attached yet is named",
      any(i == "Mandatory returnable with no artifact attached yet: "
          "Form A - Form of Bid" for i in issues))
check("an optional returnable without an artifact stays silent",
      not any("Form B" in i for i in issues))
check("a generated-but-unattested artifact surfaces the gate's own "
      "unattested failure - and is NOT double-counted as artifact-less",
      any("has not been attested" in i and "Form C" in i for i in issues)
      and not any("no artifact attached yet: Form C" in i for i in issues))
check("exactly the three issues above - nothing invented",
      len(issues) == 3)

block = dw.bid_deadline_lines(bid, TODAY, 7)
check("the closing block carries the header plus one indented line per issue",
      len(block) == 4 and "cannot be admitted" in block[0]
      and all(line.startswith("    - ") for line in block[1:]))

# --------------------------------------------------------------------------
# no-notify cases
# --------------------------------------------------------------------------
print("== no-notify: clean bids inside the window stay silent ==")
clean_bid = FakeBid(name="BID-2", user="u@example.co.za",
                    closing_date="2026-08-26", checklist=[],
                    functionality_mode="No scored functionality",
                    custom_returnables=[
                        {"ref_code": "Form C", "title": "Company Profile",
                         "mandatory": 1,
                         "generated_artifact": "/files/profile.md",
                         "artifact_attested": 1}])
check("a bid closing in 2 days with NOTHING open sends nothing - the "
      "reminder is for work left, not for having claimed a tender",
      dw.open_deadline_issues(clean_bid) == []
      and dw.bid_deadline_lines(clean_bid, TODAY, 7) == [])

# --------------------------------------------------------------------------
# briefing reminders
# --------------------------------------------------------------------------
print("== briefings: advance reminders, positive evidence only ==")
brief_bid = FakeBid(name="BID-3", user="u@example.co.za",
                    tender_title="Total Security Solution")


def briefing(card):
    return dw.briefing_reminder_line(brief_bid, TODAY, 7, card)


compulsory_card = {"briefing_date_and_time": "2026-08-26 10:00",
                   "is_it_compulsory": "Yes"}
line = briefing(compulsory_card)
check("a real compulsory briefing inside the window reminds IN ADVANCE and "
      "names the fatal gate",
      line is not None and "COMPULSORY briefing on 2026-08-26 10:00" in line
      and "fatal gate" in line and "Total Security Solution" in line)
line = briefing({"briefing_date_and_time": "2026-08-26 10:00",
                 "is_it_compulsory": "No"})
check("a non-compulsory briefing is reminded as optional, never as a gate",
      line is not None and "optional" in line and "COMPULSORY" not in line)
check("a briefing TODAY is still reminded (last call)",
      briefing({"briefing_date_and_time": "2026-08-24 09:00",
                "is_it_compulsory": "Yes"}) is not None)
check("registry placeholder dates (0001-01-01) are never treated as a real "
      "briefing - the positive-evidence rule",
      briefing({"briefing_date_and_time": "0001-01-01 00:00",
                "is_it_compulsory": "Yes"}) is None)
check("a PAST briefing stays silent - missed-briefing honesty belongs to "
      "the suitability gate, not a reminder",
      briefing({"briefing_date_and_time": "2026-08-20 10:00",
                "is_it_compulsory": "Yes"}) is None)
check("a briefing beyond the window stays silent until it enters it",
      briefing({"briefing_date_and_time": "2026-09-05 10:00",
                "is_it_compulsory": "Yes"}) is None)
check("unparseable briefing text ('See Documents'), a blank value and a "
      "missing card all stay silent",
      briefing({"briefing_date_and_time": "See Documents"}) is None
      and briefing({"briefing_date_and_time": ""}) is None
      and briefing(None) is None)
check("the briefing reminder fires independently of the closing block "
      "(clean bid, closing outside the window)",
      dw.bid_deadline_lines(
          FakeBid(name="BID-3b", user="u@example.co.za",
                  tender_title="Total Security Solution",
                  closing_date="2026-10-30", checklist=[],
                  functionality_mode="No scored functionality"),
          TODAY, 7, compulsory_card) != [])

# --------------------------------------------------------------------------
# sweep end-to-end through the seam
# --------------------------------------------------------------------------
print("== sweep: opt-in emails through the notify() seam ==")
BIDS.clear()
BIDS.update({
    # ayanda: opted in, one dirty closing bid + one bid with a briefing
    "BID-A1": FakeBid(name="BID-A1", user="ayanda@example.co.za",
                      status="Preparing", tender_slug="musina-18",
                      tender_title="Helpdesk Management System",
                      closing_date="2026-08-27", checklist=list(OPEN_GATE)),
    "BID-A2": FakeBid(name="BID-A2", user="ayanda@example.co.za",
                      status="Watching", tender_slug="vcw-403",
                      tender_title="Total Security Solution",
                      closing_date=None, checklist=[],
                      functionality_mode="No scored functionality"),
    # busi: NOT opted in, dirty closing bid
    "BID-B1": FakeBid(name="BID-B1", user="busi@example.co.za",
                      status="Preparing", tender_slug="rnm-77",
                      tender_title="Mgodlwa Bridge",
                      closing_date="2026-08-25", checklist=list(OPEN_GATE)),
    # cebo: opted in but CLEAN inside the window -> no email at all
    "BID-C1": FakeBid(name="BID-C1", user="cebo@example.co.za",
                      status="Preparing", tender_slug="twk-9",
                      tender_title="Hosting of a Website",
                      closing_date="2026-08-26", checklist=[],
                      functionality_mode="No scored functionality"),
    # submitted bid with open work: filtered out by status before any check
    "BID-S1": FakeBid(name="BID-S1", user="ayanda@example.co.za",
                      status="Submitted", tender_slug="musina-18",
                      closing_date="2026-08-25", checklist=list(OPEN_GATE)),
})
CATALOG[:] = [
    {"slug": "vcw-403", "tender_number": "VCW403-2026",
     "briefing_date_and_time": "2026-08-26 10:00", "is_it_compulsory": "Yes"},
    {"slug": "twk-9", "briefing_date_and_time": "0001-01-01 00:00",
     "is_it_compulsory": "Yes"},
    "not-a-card",
]
OPTED_IN.clear()
OPTED_IN.update({"ayanda@example.co.za", "cebo@example.co.za"})
sent.clear()
logged.clear()

dw.sweep_bid_deadlines()

check("exactly one email went out - to the opted-in user with open work",
      len(sent) == 1 and sent[0]["recipients"] == ["ayanda@example.co.za"])
check("subject and friendly framing line as designed",
      sent[0]["subject"] == "Tender deadlines are coming up"
      and sent[0]["message"].startswith(
          "The clock is running on these bids - closing dates and briefings "
          "inside your reminder window:\n\n"))
check("one email carries BOTH of the user's reminders: the dirty closing "
      "bid and the other bid's compulsory briefing",
      "Helpdesk Management System (BID-A1) closes in 3 days (2026-08-27)"
      in sent[0]["message"]
      and "Fatal checklist item still open" in sent[0]["message"]
      and "Total Security Solution (BID-A2) has a COMPULSORY briefing on "
          "2026-08-26 10:00" in sent[0]["message"])
check("the non-opted-in user's dirty bid sent nothing (opt-in via the seam)",
      not any("busi@" in str(m["recipients"]) for m in sent))
check("the clean-bid user got no email (no-notify), the placeholder "
      "briefing card stayed silent, and nothing was logged",
      not any("cebo@" in str(m["recipients"]) for m in sent) and logged == [])
check("Submitted bids never enter the sweep (status filter), so BID-S1's "
      "open work is not in the email",
      "BID-S1" not in sent[0]["message"])

sent.clear()


def broken_sendmail(**kwargs):
    raise RuntimeError("no outgoing email account")


frappe_stub.sendmail = broken_sendmail
logged.clear()
dw.sweep_bid_deadlines()
check("a send failure degrades gracefully under the watcher's own "
      "error-log title and the sweep completes",
      logged == [("Bid Deadline Notification Failed", "traceback")])
frappe_stub.sendmail = fake_sendmail


class BrokenCache:
    def get_value(self, key):
        raise RuntimeError("redis down")


frappe_stub.cache = lambda: BrokenCache()
sent.clear()
dw.sweep_bid_deadlines()
check("an unavailable catalog cache only silences briefing reminders - the "
      "closing-deadline email still goes out",
      len(sent) == 1 and "closes in 3 days" in sent[0]["message"]
      and "COMPULSORY briefing" not in sent[0]["message"])
frappe_stub.cache = lambda: FakeCache()

check("tender_number is an accepted card key alongside slug",
      "vcw-403" in dw._cards_by_slug() and "VCW403-2026" in dw._cards_by_slug())

GET_ALL_CALLS.clear()
sent.clear()
frappe_stub.conf = {"app_role": "tenant"}
dw.sweep_bid_deadlines()
check("non-control role: the sweep is a no-op (no reads, no sends)",
      GET_ALL_CALLS == [] and sent == [])
frappe_stub.conf = {"app_role": "control"}

# --------------------------------------------------------------------------
# wiring
# --------------------------------------------------------------------------
print("== wiring: scheduler entry, seam-only sending, hygiene ==")
manifest = json.load(open(os.path.join(REPO, "tender/frappe/manifest.json")))
scheduler = manifest["app_type"]["control"]["hooks"]["scheduler_events"]
check("daily scheduler runs the watcher beside the existing catalog "
      "refresh; the weekly entries are untouched",
      "{app_name}.tender.control.compliance.deadline_watch.sweep_bid_deadlines"
      in scheduler["daily"]
      and "{app_name}.tender.control.tasks.refresh_opportunities_cache"
      in scheduler["daily"]
      and "{app_name}.tender.control.compliance.artifact_expiry."
          "sweep_compliance_artifacts" in scheduler["weekly"])

watcher_source = open(os.path.join(SRC, "compliance/deadline_watch.py"),
                      encoding="utf-8").read()
check("the watcher sends ONLY through the notify() seam - no sendmail call "
      "site of its own, opt-in required, own error-log title",
      "frappe.sendmail" not in watcher_source
      and "require_opt_in=True" in watcher_source
      and '"Bid Deadline Notification Failed"' in watcher_source)
check("LF line endings, no CRLF, in the watcher and the settings doctype",
      all(b"\r" not in open(os.path.join(SRC, p), "rb").read()
          for p in ("compliance/deadline_watch.py",
                    "doctype/tender_control_settings/tender_control_settings.json")))
check("O-05: the suite runs with sys.dont_write_bytecode set",
      sys.dont_write_bytecode is True)

# --------------------------------------------------------------------------
failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL DEADLINE-WATCH CHECKS PASSED")
