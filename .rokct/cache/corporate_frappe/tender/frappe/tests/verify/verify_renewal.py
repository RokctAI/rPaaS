#!/usr/bin/env python3
"""Standalone verification for Renewal Watch (Ray's approved design:
"keep a ledger, not a model" - deterministic, NO AI). Proves the pure
renewal module (compliance/renewal.py): stated-duration parsing over
advert AND pack text (positives, negatives, noise guards, modal
selection), calendar/median math, observed-gap -> median-cycle learning,
stated-duration prediction with the per-buyer lateness correction,
window confirm/miss logic, counter-based trust, and the whole
plan_sync value the frappe glue applies verbatim. Also proves the
wiring: get_renewal_radar registered in ALL THREE manifest cmd
families, the doctype schemas matching the design, the additive sync
and pack-parse hooks present, and the radar endpoint's payload against
a stubbed frappe. Exit code 0 = all checks pass."""

import datetime
import importlib.util
import json
import os
import sys
import tempfile
import types

# O-05: in-tree suite runs must leave no __pycache__ litter under src/
sys.dont_write_bytecode = True

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SRC = os.path.join(REPO, "tender/frappe/src/control")
MANIFEST = os.path.join(REPO, "tender/frappe/manifest.json")

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renewal = load_module("v_renewal", os.path.join(SRC, "compliance/renewal.py"))
TODAY = datetime.date(2026, 8, 23)

# --------------------------------------------------------------------------
# (a) duration parsing - positives (advert phrasings AND pack phrasings)
# --------------------------------------------------------------------------
print("== (a) duration parsing: stated terms are read, in months ==")
parse = renewal.parse_contract_duration_months
check("'36 months' -> 36", parse("supply for 36 months") == 36)
check("'contract period of 36 months' -> 36",
      parse("contract period of 36 months") == 36)
check("'three (3) years' -> 36 (digit in parentheses wins)",
      parse("appointment for three (3) years") == 36)
check("'24 month period' -> 24", parse("a 24 month period") == 24)
check("'period of 5 years' -> 60", parse("for a period of 5 years") == 60)
check("'12-month contract' -> 12", parse("a 12-month contract") == 12)
check("'for a period of thirty-six (36) months' -> 36",
      parse("cleaning services for a period of thirty-six (36) months") == 36)
check("'five (5) year term' -> 60", parse("a five (5) year term") == 60)
check("'twenty four (24) months' -> 24",
      parse("security services for twenty four (24) months") == 24)
check("SLA wording: 'service level agreement for 36 months' -> 36",
      parse("service level agreement for 36 months") == 36)
check("'over a 36-month period' -> 36 ('over' is not a noise guard)",
      parse("maintenance over a 36-month period") == 36)
check("bare word form: 'three year contract' -> 36",
      parse("a three year contract for support") == 36)
check("bare word form: 'thirty six months' -> 36",
      parse("for thirty six months from commencement") == 36)
check("upper bound accepted: '10 years' -> 120", parse("a 10 years lease") == 120)
check("modal selection: the pack's repeated term beats a one-off value",
      parse("Contract period: 36 months. ... The term of 36 months "
            "commences on award. Transition plan: 12 months.") == 36)
check("tie on count -> earliest mention wins (deterministic)",
      parse("either 24 months or, alternatively, 36 months") == 24)

# --------------------------------------------------------------------------
# (b) duration parsing - negatives and the section-8 noise guards
# --------------------------------------------------------------------------
print("== (b) duration parsing: noise never becomes a term ==")
check("experience is not a term: \"minimum of 5 years' experience\"",
      parse("bidders must have a minimum of 5 years' experience") is None)
check("experience (word form + parenthetical): 'five (5) years relevant "
      "experience'", parse("five (5) years relevant experience required") is None)
check("warranty is not a term: '12 months warranty'",
      parse("equipment carries a 12 months warranty") is None)
check("warranty period: 'warranty period of 24 months'",
      parse("with a warranty period of 24 months") is None)
check("defects liability: 'defects liability period of 12 months'",
      parse("a defects liability period of 12 months applies") is None)
check("delivery phrase: 'delivery within 12 months'",
      parse("delivery within 12 months of the order") is None)
check("track-record phrase: 'in the past five years'",
      parse("projects completed in the past five years") is None)
check("horizon phrase: 'within the next 12 months'",
      parse("expected demand within the next 12 months") is None)
check("bid validity: 'validity period of 12 months'",
      parse("offers with a validity period of 12 months") is None)
check("below the 6-month floor: '3 months' -> None",
      parse("a 3 months engagement") is None)
check("above the 120-month cap: '180 months' -> None",
      parse("a 180 months concession") is None)
check("days never parse: '90 days' -> None",
      parse("valid for 90 days") is None)
check("no unit, no match: '36 clients' -> None",
      parse("supporting 36 clients monthly") is None)
check("empty and None input -> None", parse("") is None and parse(None) is None)
check("opaque SA reference codes never parse ('MWP1569CX', '5/2/1/2020-21')",
      parse("Tender MWP1569CX ref 5/2/1/2020-21") is None)

# --------------------------------------------------------------------------
# (c) calendar + median primitives
# --------------------------------------------------------------------------
print("== (c) calendar and median primitives ==")
D = datetime.date
check("add_months clamps month-end (2026-01-31 +1 -> 2026-02-28; leap "
      "2024-01-31 +1 -> 2024-02-29)",
      renewal.add_months(D(2026, 1, 31), 1) == D(2026, 2, 28)
      and renewal.add_months(D(2024, 1, 31), 1) == D(2024, 2, 29))
check("add_months walks whole years (+36 months = +3 years)",
      renewal.add_months(D(2026, 5, 22), 36) == D(2029, 5, 22))
check("median: odd picks middle, even averages the pair, empty is None",
      renewal.median_value([3, 1, 2]) == 2
      and renewal.median_value([1, 2, 3, 10]) == 2.5
      and renewal.median_value([]) is None)
check("parse_iso_date: date, datetime-string, and the catalog's "
      "'0001-01-01' placeholder -> None",
      renewal.parse_iso_date("2026-05-22 14:00") == D(2026, 5, 22)
      and renewal.parse_iso_date(D(2026, 5, 22)) == D(2026, 5, 22)
      and renewal.parse_iso_date("0001-01-01 00:00") is None
      and renewal.parse_iso_date("not a date") is None)

# --------------------------------------------------------------------------
# (d) observed gaps -> the learned cycle
# --------------------------------------------------------------------------
print("== (d) observed gaps -> median cycle ==")
dates = [D(2020, 1, 1), D(2021, 1, 1), D(2021, 1, 15), D(2022, 1, 10)]
gaps = renewal.observed_gap_days(dates)
check("amendment noise dropped: the 14-day re-post is not a cycle "
      "(gaps below 180 days excluded)", gaps == [366, 360])
check("median cycle = median observed gap ((366+360)/2 -> 363)",
      renewal.median_cycle_days(gaps) == 363)
check("one gap is an anecdote, not a rhythm: cycle needs >= 2 gaps",
      renewal.median_cycle_days([366]) is None
      and renewal.median_cycle_days([]) is None)
check("gaps beyond the 3700-day band are unrelated demand, dropped",
      renewal.observed_gap_days([D(2010, 1, 1), D(2025, 1, 1)]) == [])
check("duplicate advert dates collapse (parallel lots are one demand "
      "event, never a zero-day gap)",
      renewal.observed_gap_days([D(2020, 1, 1), D(2020, 1, 1), D(2021, 1, 1)])
      == [366])

# --------------------------------------------------------------------------
# (e) prediction: stated duration -> window, lateness correction applied
# --------------------------------------------------------------------------
print("== (e) stated-duration prediction + lateness correction ==")
watch = renewal.build_stated_watch(
    "ESKOM SOC Ltd", "Services: Electrical", "ocds-9t57fa-1", "2026-05-22",
    36, TODAY)
check("prediction = closing date + stated duration (2026-05-22 + 36mo "
      "-> 2029-05-22)", watch["predicted_date"] == "2029-05-22")
check("window is -90/+180 days around the prediction (asymmetric: "
      "extensions make buyers late, not early)",
      watch["predicted_window_start"] == "2029-02-21"
      and watch["predicted_window_end"] == "2029-11-18")
check("watch carries the full doctype shape (buyer_normalized via the "
      "market-context normalizer, anchor, source, status open)",
      watch["buyer_normalized"] == "eskom soc ltd"
      and watch["anchor_ocid"] == "ocds-9t57fa-1"
      and watch["anchor_date"] == "2026-05-22"
      and watch["source"] == "stated_duration"
      and watch["stated_duration_months"] == 36
      and watch["status"] == "open")
late = renewal.build_stated_watch(
    "ESKOM SOC Ltd", "Services: Electrical", "ocds-9t57fa-1", "2026-05-22",
    36, TODAY, lateness_days=120)
check("lateness correction shifts the whole window ('this buyer runs "
      "about 4 months late': +120 days)",
      late["predicted_date"] == "2029-09-19"
      and late["predicted_window_start"] == "2029-06-21"
      and late["predicted_window_end"] == "2030-03-18")
check("a historical anchor whose window already closed opens NO watch "
      "(the ledger keeps the event; a dead watch is never born)",
      renewal.build_stated_watch("X", "Y", "o-1", "2020-01-01", 12, TODAY)
      is None)
cycle_watch = renewal.build_cycle_watch(
    "Musina Local Municipality", "Services: ICT and related", "o-9",
    "2026-01-10", 363, TODAY)
check("observed-cycle prediction = latest advert + median gap (no "
      "lateness correction - observed gaps already embody real timing)",
      cycle_watch["predicted_date"] == "2027-01-08"
      and cycle_watch["source"] == "observed_cycle"
      and cycle_watch["stated_duration_months"] is None)

# --------------------------------------------------------------------------
# (f) confirm / miss window logic
# --------------------------------------------------------------------------
print("== (f) window confirm / miss logic ==")


def adverts(*pairs):
    return [{"ocid": ocid, "event_date": day} for ocid, day in pairs]


W = watch  # window 2029-02-21 .. 2029-11-18, predicted 2029-05-22
check("in-window advert confirms, with signed error_days (late by 40)",
      renewal.evaluate_watch(
          W, adverts(("o-2", "2029-07-01")), D(2029, 7, 2))
      == {"action": "confirm", "confirmed_ocid": "o-2",
          "confirmed_date": "2029-07-01", "error_days": 40})
check("early-but-in-window confirms with NEGATIVE error_days",
      renewal.evaluate_watch(
          W, adverts(("o-3", "2029-03-01")), D(2029, 3, 2))["error_days"]
      == -82)
check("earliest in-window candidate wins (deterministic tie policy)",
      renewal.evaluate_watch(
          W, adverts(("o-5", "2029-08-01"), ("o-4", "2029-06-01")),
          D(2029, 9, 1))["confirmed_ocid"] == "o-4")
check("a candidate BEFORE the window neither confirms nor resolves "
      "(early re-advert = new demand, watch stays open)",
      renewal.evaluate_watch(
          W, adverts(("o-6", "2029-01-01")), D(2029, 3, 1))
      == {"action": "hold"})
check("the anchor advert never confirms its own watch",
      renewal.evaluate_watch(
          W, adverts(("ocds-9t57fa-1", "2029-05-22")), D(2029, 6, 1))
      == {"action": "hold"})
check("no match inside window_end + grace -> still hold (no flapping)",
      renewal.evaluate_watch(W, [], D(2029, 12, 1)) == {"action": "hold"})
check("no match past window_end + 60-day grace -> missed",
      renewal.evaluate_watch(W, [], D(2030, 1, 18)) == {"action": "miss"})

# --------------------------------------------------------------------------
# (g) lateness + trust are recomputed counters, never fitted state
# --------------------------------------------------------------------------
print("== (g) lateness correction + counter-based trust ==")
resolved = [
    {"buyer_normalized": "eskom", "status": "confirmed", "error_days": 130},
    {"buyer_normalized": "eskom", "status": "confirmed", "error_days": 110},
    {"buyer_normalized": "eskom", "status": "confirmed", "error_days": 150},
    {"buyer_normalized": "eskom", "status": "missed", "error_days": None},
    {"buyer_normalized": "transnet soc ltd", "status": "confirmed",
     "error_days": -20},
]
check("lateness = running MEDIAN error per buyer (ESKOM ~4 months late "
      "-> +130; the missed watch contributes no error)",
      renewal.buyer_lateness_days(resolved)
      == {"eskom": 130, "transnet soc ltd": -20})
trust = renewal.buyer_trust(resolved)
check("trust is a counter: ESKOM 3 confirmed / 4 resolved = 75.0%",
      trust["eskom"] == {"confirmed": 3, "missed": 1, "resolved": 4,
                         "hit_rate_pct": 75.0})
check("unresolved buyer -> counts zero, hit rate None (never a guess)",
      renewal.hit_rate(0, 0)
      == {"confirmed": 0, "missed": 0, "resolved": 0, "hit_rate_pct": None})

# --------------------------------------------------------------------------
# (h) plan_sync - the whole sync decision as one pure value
# --------------------------------------------------------------------------
print("== (h) plan_sync end-to-end ==")
CARDS = [
    {  # states a term -> advert event + stated-duration watch
        "title": "Provision of security services for a period of "
                 "thirty-six (36) months",
        "tender_number": "ocds-9t57fa-100", "slug": "ocds-9t57fa-100",
        "institution": "ESKOM SOC Ltd", "category": "Services: Functional",
        "province": "Gauteng", "date_published": "2026-08-01",
        "closing_date": "2026-09-01 12:00", "status": "ACTIVE",
    },
    {  # no stated term -> event only
        "title": "Tender Opportunity: TPT/2026/03/0221",
        "tender_number": "ocds-9t57fa-101", "slug": "ocds-9t57fa-101",
        "institution": "Transnet SOC Ltd", "category": "Services: General",
        "date_published": "2026-08-05", "closing_date": "2026-09-10 10:00",
    },
    {  # confirms the open Musina watch (in its window)
        "title": "Interactive Cloud-Based Helpdesk Management System",
        "tender_number": "ocds-9t57fa-102", "slug": "ocds-9t57fa-102",
        "institution": "Musina Local Municipality",
        "category": "Services: ICT and related",
        "date_published": "2026-08-10", "closing_date": "2026-09-15 12:00",
    },
]
LEDGER = [  # an established eThekwini yearly rhythm, currently unwatched
    {"buyer": "eThekwini Metropolitan Municipality",
     "buyer_normalized": "ethekwini metropolitan municipality",
     "category": "Services: General", "event_type": "advert",
     "ocid": "e-1", "event_date": "2024-06-01",
     "stated_duration_months": None, "source_field": ""},
    {"buyer": "eThekwini Metropolitan Municipality",
     "buyer_normalized": "ethekwini metropolitan municipality",
     "category": "Services: General", "event_type": "advert",
     "ocid": "e-2", "event_date": "2025-06-01",
     "stated_duration_months": None, "source_field": ""},
    {"buyer": "eThekwini Metropolitan Municipality",
     "buyer_normalized": "ethekwini metropolitan municipality",
     "category": "Services: General", "event_type": "advert",
     "ocid": "e-3", "event_date": "2026-06-01",
     "stated_duration_months": None, "source_field": ""},
]
OPEN_WATCHES = [
    {  # Musina: window straddles today; card 102 lands inside it
        "name": "TRW-00001", "buyer": "Musina Local Municipality",
        "buyer_normalized": "musina local municipality",
        "category": "Services: ICT and related", "anchor_ocid": "m-0",
        "anchor_date": "2024-08-20", "source": "stated_duration",
        "stated_duration_months": 24, "predicted_date": "2026-08-20",
        "predicted_window_start": "2026-05-22",
        "predicted_window_end": "2027-02-16", "status": "open"},
    {  # long-dead window, no successor -> missed
        "name": "TRW-00002", "buyer": "Stats SA",
        "buyer_normalized": "stats sa", "category": "Services: Professional",
        "anchor_ocid": "s-0", "anchor_date": "2023-01-15",
        "source": "stated_duration", "stated_duration_months": 24,
        "predicted_date": "2025-01-15",
        "predicted_window_start": "2024-10-17",
        "predicted_window_end": "2025-07-14", "status": "open"},
]
RESOLVED = [
    {"name": "TRW-00000", "buyer": "ESKOM SOC Ltd",
     "buyer_normalized": "eskom soc ltd",
     "category": "Services: Functional", "anchor_ocid": "k-0",
     "anchor_date": "2022-01-01", "source": "stated_duration",
     "stated_duration_months": 36, "predicted_date": "2025-01-01",
     "predicted_window_start": "2024-10-03",
     "predicted_window_end": "2025-06-30", "status": "confirmed",
     "confirmed_ocid": "k-1", "confirmed_date": "2025-05-01",
     "error_days": 120},
]
plan = renewal.plan_sync(CARDS, LEDGER, OPEN_WATCHES, RESOLVED, today=TODAY)
check("every new card becomes one advert ledger event (dedup by ocid)",
      [e["ocid"] for e in plan["new_events"]]
      == ["ocds-9t57fa-100", "ocds-9t57fa-101", "ocds-9t57fa-102"])
ev = plan["new_events"][0]
check("the stated term is parsed off the card text and recorded on its "
      "event (36, source advert_text)",
      ev["stated_duration_months"] == 36 and ev["source_field"] == "advert_text"
      and plan["new_events"][1]["stated_duration_months"] is None)
updates = {u["name"]: u for u in plan["watch_updates"]}
check("open Musina watch CONFIRMED by the in-window successor, "
      "error_days = confirmed - predicted (-10)",
      updates["TRW-00001"]["status"] == "confirmed"
      and updates["TRW-00001"]["confirmed_ocid"] == "ocds-9t57fa-102"
      and updates["TRW-00001"]["confirmed_date"] == "2026-08-10"
      and updates["TRW-00001"]["error_days"] == -10)
check("open watch past window_end + grace with no successor -> MISSED",
      updates["TRW-00002"]["status"] == "missed"
      and "confirmed_ocid" not in updates["TRW-00002"])
by_source = {}
for w in plan["new_watches"]:
    by_source.setdefault(w["source"], []).append(w)
stated = by_source.get("stated_duration", [])
check("new stated-duration watch: anchor = the card's CLOSING date, "
      "prediction = close + 36mo + the buyer's lateness correction "
      "(ESKOM median error +120d: 2029-09-01 -> 2029-12-30)",
      len(stated) == 1 and stated[0]["anchor_ocid"] == "ocds-9t57fa-100"
      and stated[0]["anchor_date"] == "2026-09-01"
      and stated[0]["predicted_date"] == "2029-12-30")
cycles = by_source.get("observed_cycle", [])
check("established unwatched cell earns an observed-cycle watch "
      "(eThekwini yearly rhythm: latest advert + median gap 365d)",
      len(cycles) == 1 and cycles[0]["anchor_ocid"] == "e-3"
      and cycles[0]["predicted_date"] == "2027-06-01")
check("stats mirror the plan (3 events, 1 stated, 1 confirm, 1 miss, "
      "2 watches)",
      plan["stats"] == {"cards_seen": 3, "cards_skipped": 0,
                        "events_appended": 3, "durations_stated": 1,
                        "watches_confirmed": 1, "watches_missed": 1,
                        "watches_created": 2})
check("plan_sync is deterministic: same inputs, identical plan",
      renewal.plan_sync(CARDS, LEDGER, OPEN_WATCHES, RESOLVED, today=TODAY)
      == plan)
replay_events = LEDGER + plan["new_events"]
replay_watches = OPEN_WATCHES + plan["new_watches"]
replay = renewal.plan_sync(CARDS, replay_events, [
    w for w in replay_watches if w["name" if "name" in w else "anchor_ocid"]
    not in ("TRW-00001", "TRW-00002")
], RESOLVED, today=TODAY)
check("re-running over the applied plan appends nothing new "
      "(ledger idempotence)",
      replay["new_events"] == [] and replay["new_watches"] == []
      and replay["watch_updates"] == [])

# --------------------------------------------------------------------------
# (i) wiring: manifest, doctypes, hooks, purity
# --------------------------------------------------------------------------
print("== (i) wiring ==")
with open(MANIFEST, encoding="utf-8") as f:
    manifest = json.load(f)
methods = manifest["app_type"]["control"]["hooks"]["whitelisted_methods"]
target = "{app_name}.tender.control.api.tenders.get_renewal_radar.get_renewal_radar"
check("get_renewal_radar rides the single gateway in ALL THREE cmd "
      "families ({app_name}.api.tenders.*, control:*, "
      "control.control.api.tenders.*)",
      methods.get("{app_name}.api.tenders.get_renewal_radar") == target
      and methods.get("control:get_renewal_radar") == target
      and methods.get("control.control.api.tenders.get_renewal_radar")
      == target)

with open(os.path.join(
        SRC, "doctype/tender_renewal_watch/tender_renewal_watch.json"),
        encoding="utf-8") as f:
    watch_dt = json.load(f)
watch_fields = {fld["fieldname"]: fld for fld in watch_dt["fields"]}
check("Tender Renewal Watch carries every design field",
      {"buyer", "buyer_normalized", "category", "anchor_ocid", "source",
       "predicted_window_start", "predicted_window_end", "predicted_date",
       "status", "confirmed_ocid", "confirmed_date", "error_days"}
      <= set(watch_fields))
check("watch selects match the design (source stated_duration/"
      "observed_cycle; status open/confirmed/missed, default open)",
      watch_fields["source"]["options"] == "stated_duration\nobserved_cycle"
      and watch_fields["status"]["options"] == "open\nconfirmed\nmissed"
      and watch_fields["status"]["default"] == "open")
with open(os.path.join(
        SRC, "doctype/tender_renewal_event/tender_renewal_event.json"),
        encoding="utf-8") as f:
    event_dt = json.load(f)
event_fields = {fld["fieldname"]: fld for fld in event_dt["fields"]}
check("Tender Renewal Event ledger schema: buyer/category/event_type "
      "(advert|award|close)/ocid/event_date/stated_duration_months/"
      "source_field",
      {"buyer", "buyer_normalized", "category", "event_type", "ocid",
       "event_date", "stated_duration_months", "source_field"}
      <= set(event_fields)
      and event_fields["event_type"]["options"] == "advert\naward\nclose")

renewal_src = open(os.path.join(SRC, "compliance/renewal.py")).read()
check("renewal.py stays frappe-free and stdlib-only (ledger math is "
      "standalone-testable, like suitability.py)",
      "import frappe" not in renewal_src
      and "requests" not in renewal_src)
tasks_src = open(os.path.join(SRC, "tasks.py")).read()
check("opportunities sync hook present and ADDITIVE (guarded so a "
      "renewal failure never breaks the cache refresh)",
      "update_renewal_watches" in tasks_src
      and tasks_src.index("refresh_all_data()")
      < tasks_src.index("update_renewal_watches"))
pack_src = open(
    os.path.join(SRC, "api/tenders/parse_tender_pack.py")).read()
check("pack-parse hook present (pack PDFs feed stated durations into "
      "the ledger from day one), guarded additively",
      "record_pack_duration" in pack_src
      and "except Exception" in pack_src.split("record_pack_duration")[2])

# --------------------------------------------------------------------------
# (j) the radar endpoint against a stubbed frappe
# --------------------------------------------------------------------------
print("== (j) get_renewal_radar endpoint (frappe stubbed) ==")


def build_frappe(watch_rows):
    frappe = types.ModuleType("frappe")
    frappe.conf = {"app_role": "control"}
    frappe.session = types.SimpleNamespace(user="ray@example.com")
    frappe.local = types.SimpleNamespace(request=None)
    frappe.whitelist = lambda **kw: (lambda fn: fn)
    frappe.PermissionError = PermissionError

    def throw(msg, exc=Exception, title=None):
        raise (exc if isinstance(exc, type) else Exception)(msg)

    frappe.throw = throw
    frappe.get_request_header = lambda name: None

    def get_all(doctype, filters=None, fields=None, order_by=None, limit=None):
        assert doctype == "Tender Renewal Watch"
        status = (filters or {}).get("status")
        wanted = status[1] if isinstance(status, tuple) else (status,)
        rows = [dict(r) for r in watch_rows if r["status"] in wanted]
        if order_by:
            rows.sort(key=lambda r: (str(r.get("predicted_date")),
                                     str(r.get("name"))))
        return rows

    frappe.get_all = get_all
    utils = types.ModuleType("frappe.utils")
    utils.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
    utils.nowdate = lambda: "2026-08-23"
    frappe.utils = utils
    return frappe


def load_endpoint(frappe_mod):
    src = open(os.path.join(SRC, "api/tenders/get_renewal_radar.py")).read()
    src = src.replace("{app_name}", "_app_stub")
    path = os.path.join(tempfile.mkdtemp(prefix="renewal_radar_"), "ep.py")
    open(path, "w").write(src)

    # fake package chain _app_stub.tender.control.compliance.renewal
    pkg_names = ["_app_stub", "_app_stub.tender", "_app_stub.tender.control",
                 "_app_stub.tender.control.compliance"]
    saved = {}
    mods = {}
    for name in pkg_names:
        mods[name] = types.ModuleType(name)
        mods[name].__path__ = []
    mods["_app_stub.tender.control.compliance"].renewal = renewal
    mods["_app_stub.tender.control.compliance.renewal"] = renewal
    for name, mod in list(mods.items()) + [
            ("frappe", frappe_mod), ("frappe.utils", frappe_mod.utils)]:
        if isinstance(name, tuple):
            name, mod = name
        saved[name] = sys.modules.get(name)
        sys.modules[name] = mod
    try:
        spec = importlib.util.spec_from_file_location("v_radar_ep", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
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


ROWS = [
    {"name": "TRW-1", "buyer": "ESKOM", "buyer_normalized": "eskom",
     "category": "Services: Electrical", "anchor_ocid": "o-1",
     "anchor_date": datetime.date(2026, 5, 22), "source": "stated_duration",
     "stated_duration_months": 36,
     "predicted_date": datetime.date(2026, 11, 1),
     "predicted_window_start": datetime.date(2026, 8, 3),
     "predicted_window_end": datetime.date(2027, 4, 30), "status": "open"},
    {"name": "TRW-2", "buyer": "PRASA", "buyer_normalized": "prasa",
     "category": "Services: General", "anchor_ocid": "o-2",
     "anchor_date": datetime.date(2026, 6, 1), "source": "observed_cycle",
     "stated_duration_months": 0,
     "predicted_date": datetime.date(2028, 6, 1),
     "predicted_window_start": datetime.date(2028, 3, 3),
     "predicted_window_end": datetime.date(2028, 11, 28), "status": "open"},
    {"name": "TRW-3", "buyer": "ESKOM", "buyer_normalized": "eskom",
     "category": "Services: General", "anchor_ocid": "o-3",
     "anchor_date": None, "source": "stated_duration",
     "stated_duration_months": 24,
     "predicted_date": datetime.date(2025, 12, 1),
     "predicted_window_start": datetime.date(2025, 9, 2),
     "predicted_window_end": datetime.date(2026, 5, 30),
     "status": "confirmed", "error_days": 30},
    {"name": "TRW-4", "buyer": "ESKOM", "buyer_normalized": "eskom",
     "category": "Supplies: General", "anchor_ocid": "o-4",
     "anchor_date": None, "source": "stated_duration",
     "stated_duration_months": 12,
     "predicted_date": datetime.date(2025, 6, 1),
     "predicted_window_start": datetime.date(2025, 3, 3),
     "predicted_window_end": datetime.date(2025, 11, 28),
     "status": "missed", "error_days": None},
]
endpoint = load_endpoint(build_frappe(ROWS))
radar = endpoint.get_renewal_radar()
check("12-month horizon: only the watch predicted within it is served "
      "(TRW-2 at 2028 stays off the default radar)",
      [w["name"] for w in radar["watches"]] == ["TRW-1"]
      and radar["summary"] == {"open_total": 2, "upcoming": 1,
                               "months_ahead": 12, "confirmed_total": 1,
                               "missed_total": 1})
row = radar["watches"][0]
check("watch rows serialize the full window as dates + the buyer's "
      "trust counters attached (ESKOM 1/2 = 50%)",
      row["predicted_window_start"] == "2026-08-03"
      and row["predicted_window_end"] == "2027-04-30"
      and row["trust"] == {"confirmed": 1, "missed": 1, "resolved": 2,
                           "hit_rate_pct": 50.0})
check("a wider horizon serves the cycle watch too, soonest first",
      [w["name"] for w in endpoint.get_renewal_radar(months_ahead=36)["watches"]]
      == ["TRW-1", "TRW-2"])
check("the honesty layer rides every response (lead calendar, never a "
      "certainty; no probabilities anywhere)",
      any("LEAD CALENDAR" in c for c in radar["caveats"])
      and "no model, no probabilities" in radar["semantics"]
      and len(radar["caveats"]) == 5)
guest_frappe = build_frappe(ROWS)
guest_frappe.session = types.SimpleNamespace(user="Guest")
guest_ep = load_endpoint(guest_frappe)
try:
    guest_ep.get_renewal_radar()
    guest_blocked = False
except PermissionError:
    guest_blocked = True
check("guests are refused (login required, same doctrine as the "
      "suitability endpoint)", guest_blocked)

# --------------------------------------------------------------------------
print()
passed = sum(1 for _, ok in checks if ok)
print(f"{passed}/{len(checks)} checks passed")
sys.exit(0 if passed == len(checks) else 1)
