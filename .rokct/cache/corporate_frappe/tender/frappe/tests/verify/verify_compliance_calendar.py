#!/usr/bin/env python3
"""Standalone verification for the unified compliance calendar
(assessment plan #13) - ASSEMBLY of the four existing date streams (bid
closings, briefing dates, compliance-artifact expiries, renewal
expected-advertisement windows) into one dated feed, with the plan's
honesty constraint enforced as an invariant: renewal entries are WATCH
items, never commitments, and the 2-of-12-validated caveat rides every
payload. Proves the pure assembler (compliance/compliance_calendar.py):
per-stream extraction with the existing placeholder-date discipline,
merge + total deterministic ordering, horizon and limit behaviour,
summary counts, determinism; the endpoint against a stubbed frappe
(per-user scoping of bids/artifacts to the caller, guest refusal); and
the wiring (registered in ALL THREE manifest cmd families, bids.ts
service method, the render-nothing-on-empty panel, the My Bids page
wiring line). Exit code 0 = all checks pass."""

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
NEXTJS = os.path.join(REPO, "tender/nextjs/templates/control")

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cal = load_module(
    "v_compliance_calendar", os.path.join(SRC, "compliance/compliance_calendar.py")
)
TODAY = "2026-08-24"

BIDS = [
    {"name": "TB-1", "tender_slug": "s-close", "tender_title": "Helpdesk system",
     "institution": "Musina Local Municipality",
     "closing_date": "2026-09-15 12:00", "status": "Preparing"},
    {"name": "TB-2", "tender_slug": "s-brief", "tender_title": "Security services",
     "institution": "ESKOM SOC Ltd",
     "closing_date": "2026-09-01", "status": "Watching"},
    {"name": "TB-3", "tender_slug": "s-done", "tender_title": "Old bid",
     "institution": "SARS", "closing_date": "2026-09-02", "status": "Submitted"},
    {"name": "TB-4", "tender_slug": "s-past", "tender_title": "Closed already",
     "institution": "SARS", "closing_date": "2026-08-01", "status": "Preparing"},
    {"name": "TB-5", "tender_slug": "s-far", "tender_title": "Beyond horizon",
     "institution": "SARS", "closing_date": "2027-06-01", "status": "Preparing"},
    {"name": "TB-6", "tender_slug": "s-placeholder", "tender_title": "No real date",
     "institution": "SARS", "closing_date": "0001-01-01 00:00",
     "status": "Preparing"},
]
CARDS = {
    "s-close": {"briefing_date_and_time": "2026-09-01 10:00",
                "is_it_compulsory": "Yes"},
    "s-brief": {"briefing_date_and_time": "2026-08-28",
                "is_it_compulsory": "No"},
    "s-done": {"briefing_date_and_time": "2026-08-30",
               "is_it_compulsory": "Yes"},
    "s-past": {"briefing_date_and_time": "0001-01-01 00:00",
               "is_it_compulsory": "Yes"},
}
ARTIFACTS = [
    {"name": "CART-1", "artifact_type": "Tax Compliance Status PIN",
     "reference": "PIN123", "valid_until": "2026-09-01", "status": "Amber"},
    {"name": "CART-2", "artifact_type": "B-BBEE Affidavit", "reference": "",
     "valid_until": "2026-08-01", "status": "Expired"},
    {"name": "CART-3", "artifact_type": "CIDB Grading", "reference": "2GB",
     "valid_until": "2027-08-01", "status": "Green"},
]
OPEN_WATCHES = [
    {"name": "TRW-1", "buyer": "ESKOM SOC Ltd", "buyer_normalized": "eskom soc ltd",
     "category": "Services: Electrical", "source": "stated_duration",
     "predicted_date": "2026-09-01", "predicted_window_start": "2026-06-03",
     "predicted_window_end": "2027-02-28", "status": "open"},
    {"name": "TRW-2", "buyer": "PRASA", "buyer_normalized": "prasa",
     "category": "Services: General", "source": "observed_cycle",
     "predicted_date": "2028-06-01", "predicted_window_start": "2028-03-03",
     "predicted_window_end": "2028-11-28", "status": "open"},
]
RESOLVED = [
    {"buyer_normalized": "eskom soc ltd", "status": "confirmed", "error_days": 40},
    {"buyer_normalized": "eskom soc ltd", "status": "missed", "error_days": None},
]


def build(**kw):
    args = dict(bids=BIDS, artifacts=ARTIFACTS, cards_by_slug=CARDS,
                open_watches=OPEN_WATCHES, resolved_watches=RESOLVED,
                today=TODAY)
    args.update(kw)
    return cal.build_compliance_calendar(**args)


FEED = build()
BY_STREAM = {}
for e in FEED["entries"]:
    BY_STREAM.setdefault(e["stream"], []).append(e)

# --------------------------------------------------------------------------
# (a) per-stream assembly - existing logic reused, nothing reinvented
# --------------------------------------------------------------------------
print("== (a) stream assembly ==")
closings = BY_STREAM.get("bid_closing", [])
check("bid closings: only OPEN bids (Watching/Preparing) inside the "
      "horizon appear - Submitted, already-closed, beyond-horizon and "
      "placeholder-dated bids are absent",
      [c["ref"]["name"] for c in closings] == ["TB-2", "TB-1"])
check("closing entry carries the bid's real fields (date from the "
      "datetime form, KILL-01 wording, slug + institution in ref)",
      closings[1]["date"] == "2026-09-15"
      and closings[1]["days_away"] == 22
      and "KILL-01" in closings[1]["detail"]
      and closings[1]["ref"]["tender_slug"] == "s-close"
      and closings[1]["ref"]["institution"] == "Musina Local Municipality")
briefings = BY_STREAM.get("briefing", [])
check("briefings: read off each OPEN bid's catalog card - the Submitted "
      "bid's briefing and the placeholder 0001-01-01 briefing never "
      "become entries",
      [b["ref"]["name"] for b in briefings] == ["TB-2", "TB-1"])
check("compulsory briefing is flagged as the fatal-gate save; "
      "non-compulsory says so",
      briefings[1]["ref"]["compulsory"] is True
      and "COMPULSORY" in briefings[1]["detail"]
      and briefings[0]["ref"]["compulsory"] is False
      and "not marked compulsory" in briefings[0]["detail"])
expiries = BY_STREAM.get("artifact_expiry", [])
check("artifact expiries: the sweep's valid_until field as a dated feed "
      "- upcoming only (already-Expired and beyond-horizon absent)",
      [a["ref"]["name"] for a in expiries] == ["CART-1"])
check("expiry entry carries type (reference) label and the artifact's "
      "current traffic-light status",
      expiries[0]["title"] == "Tax Compliance Status PIN (PIN123)"
      and expiries[0]["ref"]["status"] == "Amber")
renewals = BY_STREAM.get("renewal_window", [])
check("renewal stream: the radar's open watches inside the horizon "
      "(TRW-2 at 2028 stays off a 90-day calendar)",
      [r["ref"]["name"] for r in renewals] == ["TRW-1"])
check("renewal entry carries the full expected window + the buyer's "
      "counter-based trust (1 of 2 confirmed)",
      renewals[0]["ref"]["predicted_window_start"] == "2026-06-03"
      and renewals[0]["ref"]["predicted_window_end"] == "2027-02-28"
      and renewals[0]["ref"]["trust"] == {"confirmed": 1, "missed": 1,
                                          "resolved": 2, "hit_rate_pct": 50.0})

# --------------------------------------------------------------------------
# (b) merging + ordering
# --------------------------------------------------------------------------
print("== (b) stream merging and deterministic ordering ==")
check("one merged feed, soonest first",
      [e["date"] for e in FEED["entries"]]
      == sorted(e["date"] for e in FEED["entries"]))
same_day = [e for e in FEED["entries"] if e["date"] == "2026-09-01"]
check("same-day precedence is the fixed stream order: closing before "
      "briefing before expiry before renewal window",
      [e["stream"] for e in same_day]
      == ["bid_closing", "briefing", "artifact_expiry", "renewal_window"])
check("summary counts every in-horizon entry per stream",
      FEED["summary"]["streams"] == {"bid_closing": 2, "briefing": 2,
                                     "artifact_expiry": 1,
                                     "renewal_window": 1}
      and FEED["summary"]["total"] == 6
      and FEED["summary"]["horizon"] == "2026-11-22")
check("assembly is deterministic: same inputs, identical feed",
      build() == FEED)
inputs_copy = copy.deepcopy((BIDS, ARTIFACTS, CARDS, OPEN_WATCHES, RESOLVED))
check("assembly never mutates its inputs",
      (BIDS, ARTIFACTS, CARDS, OPEN_WATCHES, RESOLVED) == inputs_copy)

# --------------------------------------------------------------------------
# (c) watch-item semantics - the plan's CRITICAL constraint
# --------------------------------------------------------------------------
print("== (c) watch-item semantics (renewal is NEVER a commitment) ==")
check("every renewal_window entry is item_class 'watch', without "
      "exception",
      all(e["item_class"] == "watch"
          for e in FEED["entries"] if e["stream"] == "renewal_window")
      and len(renewals) > 0)
check("every non-renewal entry is a commitment (real date, real "
      "obligation)",
      all(e["item_class"] == "commitment"
          for e in FEED["entries"] if e["stream"] != "renewal_window"))
check("summary splits the feed on the honesty axis (5 commitments, "
      "1 watch)",
      FEED["summary"]["commitments"] == 5 and FEED["summary"]["watches"] == 1)
check("the watch row's own detail restates the semantics (prepare now, "
      "never a certainty)",
      "WATCH item" in renewals[0]["detail"]
      and "never a certainty" in renewals[0]["detail"])
wide = build(days_ahead=800)
check("days_ahead is capped at 366 - even a wide calendar never turns "
      "the 2028 watch into an entry silently",
      wide["summary"]["days_ahead"] == 366
      and "TRW-2" not in [e["ref"]["name"] for e in wide["entries"]])

# --------------------------------------------------------------------------
# (d) caveats - the 2-of-12 honesty note rides every payload
# --------------------------------------------------------------------------
print("== (d) caveats ==")
check("the renewal-validation caveat (only 2 of 12 sampled due "
      "predictions validated) rides the payload verbatim",
      any("2 of 12" in c and "WATCH" in c for c in FEED["caveats"]))
check("placeholder-date and user-entered-expiry caveats ride along; "
      "semantics says assembly / deterministic / no AI",
      any("0001-01-01" in c for c in FEED["caveats"])
      and any("user-entered" in c for c in FEED["caveats"])
      and "assembly" in FEED["semantics"] and "no AI" in FEED["semantics"])
check("caveats also ride an EMPTY calendar (honesty is unconditional)",
      build(bids=[], artifacts=[], cards_by_slug={}, open_watches=[],
            resolved_watches=[])["caveats"] == FEED["caveats"])

# --------------------------------------------------------------------------
# (e) horizon + limit behaviour
# --------------------------------------------------------------------------
print("== (e) horizon and limit ==")
short = build(days_ahead=5)
check("a 5-day horizon keeps only the 2026-08-28 briefing",
      [e["date"] for e in short["entries"]] == ["2026-08-28"]
      and short["summary"]["total"] == 1)
capped = build(limit=2)
check("limit truncates the feed but the summary still reports the true "
      "stream totals (total 6, shown 2)",
      len(capped["entries"]) == 2 and capped["summary"]["total"] == 6
      and capped["summary"]["shown"] == 2
      and capped["summary"]["streams"] == FEED["summary"]["streams"])
check("an empty world builds an empty feed (never an error)",
      build(bids=None, artifacts=None, cards_by_slug=None, open_watches=None,
            resolved_watches=None)["entries"] == [])
try:
    cal.build_compliance_calendar([], [], {}, [], [], "not a date")
    bad_today = False
except ValueError:
    bad_today = True
check("an unparseable 'today' raises instead of guessing", bad_today)

# --------------------------------------------------------------------------
# (f) module purity
# --------------------------------------------------------------------------
print("== (f) purity ==")
cal_src = open(os.path.join(SRC, "compliance/compliance_calendar.py")).read()
check("compliance_calendar.py is frappe-free and reuses the renewal "
      "ledger's date parsing (assembly, not new logic)",
      "import frappe" not in cal_src and "requests" not in cal_src
      and "parse_iso_date" in cal_src and "buyer_trust" in cal_src)

# --------------------------------------------------------------------------
# (g) the endpoint against a stubbed frappe
# --------------------------------------------------------------------------
print("== (g) get_compliance_calendar endpoint (frappe stubbed) ==")

QUERIED_FILTERS = {}


def build_frappe(user="ray@example.com"):
    frappe = types.ModuleType("frappe")
    frappe.conf = {"app_role": "control"}
    frappe.session = types.SimpleNamespace(user=user)
    frappe.local = types.SimpleNamespace(request=None)
    frappe.whitelist = lambda **kw: (lambda fn: fn)
    frappe.PermissionError = PermissionError

    def throw(msg, exc=Exception, title=None):
        raise (exc if isinstance(exc, type) else Exception)(msg)

    frappe.throw = throw
    frappe.get_request_header = lambda name: None

    def get_all(doctype, filters=None, fields=None, order_by=None):
        QUERIED_FILTERS.setdefault(doctype, []).append(dict(filters or {}))
        if doctype == "Tender Bid":
            assert (filters or {}).get("user") == frappe.session.user
            return [dict(b) for b in BIDS]
        if doctype == "Compliance Artifact":
            assert (filters or {}).get("user") == frappe.session.user
            return [dict(a) for a in ARTIFACTS]
        if doctype == "Tender Renewal Watch":
            status = (filters or {}).get("status")
            wanted = status[1] if isinstance(status, tuple) else (status,)
            rows = OPEN_WATCHES + [
                dict(r, name="TRW-R%d" % i, buyer="X", category="Y",
                     source="stated_duration", predicted_date="2026-01-01",
                     predicted_window_start="2025-10-03",
                     predicted_window_end="2026-06-30")
                for i, r in enumerate(RESOLVED)]
            return [dict(r) for r in rows if r["status"] in wanted]
        raise AssertionError("unexpected doctype " + doctype)

    frappe.get_all = get_all
    utils = types.ModuleType("frappe.utils")
    utils.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
    utils.nowdate = lambda: TODAY
    frappe.utils = utils
    return frappe


def load_endpoint(frappe_mod):
    src = open(os.path.join(SRC, "api/tenders/get_compliance_calendar.py")).read()
    src = src.replace("{app_name}", "_app_stub")

    entitlement = types.ModuleType(
        "_app_stub.tender.control.api.tenders.tender_entitlement")
    entitlement.find_tender_by_slug = lambda slug: CARDS.get(slug)

    pkg_names = [
        "_app_stub", "_app_stub.tender", "_app_stub.tender.control",
        "_app_stub.tender.control.api", "_app_stub.tender.control.api.tenders",
        "_app_stub.tender.control.compliance",
    ]
    saved = {}
    mods = {}
    for name in pkg_names:
        mods[name] = types.ModuleType(name)
        mods[name].__path__ = []
    mods["_app_stub.tender.control.api.tenders"].tender_entitlement = entitlement
    mods["_app_stub.tender.control.api.tenders.tender_entitlement"] = entitlement
    mods["_app_stub.tender.control.compliance"].compliance_calendar = cal
    mods["_app_stub.tender.control.compliance.compliance_calendar"] = cal
    for name, mod in list(mods.items()) + [
            ("frappe", frappe_mod), ("frappe.utils", frappe_mod.utils)]:
        saved[name] = sys.modules.get(name)
        sys.modules[name] = mod
    try:
        module = types.ModuleType("v_calendar_ep")
        exec(compile(src, "get_compliance_calendar.py", "exec"), module.__dict__)
        return module
    finally:
        for name, orig in saved.items():
            if name.startswith("_app_stub"):
                # the endpoint imports the stub package chain lazily at
                # CALL time - it must stay importable after loading
                continue
            if orig is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = orig


endpoint = load_endpoint(build_frappe())
payload = endpoint.get_compliance_calendar()
check("endpoint serves the pure assembler's feed verbatim (same six "
      "entries, same summary as the direct build)",
      payload["summary"] == FEED["summary"]
      and [(e["stream"], e["ref"]["name"]) for e in payload["entries"]]
      == [(e["stream"], e["ref"]["name"]) for e in FEED["entries"]])
check("per-user scoping: bids AND artifacts are queried filtered to the "
      "session user (never unscoped)",
      all(f.get("user") == "ray@example.com"
          for f in QUERIED_FILTERS.get("Tender Bid", []))
      and all(f.get("user") == "ray@example.com"
              for f in QUERIED_FILTERS.get("Compliance Artifact", [])))
check("the endpoint's trace log uses the fixed single-brace form "
      "(no {{trace_id}} regression)",
      "trace_id={trace_id}" in open(
          os.path.join(SRC, "api/tenders/get_compliance_calendar.py")).read()
      and "{{trace_id}}" not in open(
          os.path.join(SRC, "api/tenders/get_compliance_calendar.py")).read())
guest_ep = load_endpoint(build_frappe(user="Guest"))
try:
    guest_ep.get_compliance_calendar()
    guest_blocked = False
except PermissionError:
    guest_blocked = True
check("guests are refused (login required, same doctrine as the radar)",
      guest_blocked)

# --------------------------------------------------------------------------
# (h) wiring: manifest, service, panel, page
# --------------------------------------------------------------------------
print("== (h) wiring ==")
with open(MANIFEST, encoding="utf-8") as f:
    manifest = json.load(f)
methods = manifest["app_type"]["control"]["hooks"]["whitelisted_methods"]
target = ("{app_name}.tender.control.api.tenders.get_compliance_calendar"
          ".get_compliance_calendar")
check("get_compliance_calendar rides the single gateway in ALL THREE "
      "cmd families ({app_name}.api.tenders.*, control:*, "
      "control.control.api.tenders.*)",
      methods.get("{app_name}.api.tenders.get_compliance_calendar") == target
      and methods.get("control:get_compliance_calendar") == target
      and methods.get("control.control.api.tenders.get_compliance_calendar")
      == target)
bids_ts = open(os.path.join(NEXTJS, "app/services/control/bids.ts")).read()
check("bids.ts service calls the canonical control: cmd and types the "
      "watch/commitment axis",
      'ControlBaseService.call("control:get_compliance_calendar"' in bids_ts
      and "getComplianceCalendar(" in bids_ts
      and '"commitment" | "watch"' in bids_ts)
panel = open(os.path.join(NEXTJS,
                          "components/custom/compliance-calendar.tsx")).read()
check("calendar panel renders NOTHING on empty or error (a control-plane "
      "hiccup never breaks the bids page)",
      panel.count("return null") >= 2
      and "if (entries.length === 0) return null" in panel)
check("panel renders renewal rows as watch items with the 2-of-12 note, "
      "never deadline styling",
      "watch — not a commitment" in panel and "2 of 12" in panel
      and 'entry.item_class === "watch"' in panel)
page = open(os.path.join(NEXTJS, "app/opportunities/bids/page.tsx")).read()
check("My Bids page wires the panel with one line",
      "<ComplianceCalendarSection />" in page
      and "components/custom/compliance-calendar" in page)

# --------------------------------------------------------------------------
print()
passed = sum(1 for _, ok in checks if ok)
print(f"{passed}/{len(checks)} checks passed")
sys.exit(0 if passed == len(checks) else 1)
