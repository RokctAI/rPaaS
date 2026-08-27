#!/usr/bin/env python3
"""Standalone verification for the award-outcome ledger (plan #12): the
frappe-free compliance/award_ledger.py module (own-outcome aggregation -
win rate over DECIDED bids only, per-buyer counters, quoted-vs-awarded
deltas placed against the bid-time pricing bands - plus published-award
matching over re-fetched OCDS releases, where a NON-EMPTY awards[] is the
ONLY award signal, tags are always ["compiled"] and never consulted, and
"no award published" is NEVER "lost"), the get_award_ledger endpoint
(login-required, own-bids scoping like get_my_bids, Raw Tender Cache read
per claimed ocid only), the research-bound caveats riding every payload
(winner-side feed, buyer-skewed publication, 72.01% usable values, no
award dates - release date is the proxy, NEVER a win probability), the
single-gateway manifest registration in all three cmd families, and the
nextjs wiring. Exit code 0 = all checks pass."""

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
NEXT = os.path.join(REPO, "tender/nextjs/templates/control")
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


ledger_mod = load_module(
    "v_award_ledger", os.path.join(SRC, "compliance/award_ledger.py"))

# --------------------------------------------------------------------------
# (a) helpers: ocid shape, amount flags, placeholder suppliers
# --------------------------------------------------------------------------
print("== (a) helpers: ocid shape, amount_flag classes, placeholders ==")
check("real eTenders ocid recognised", ledger_mod.looks_like_ocid("ocds-9t57fa-155126"))
check("plain tender numbers / slugs are NOT ocids",
      not ledger_mod.looks_like_ocid("TPT/2026/03/0221")
      and not ledger_mod.looks_like_ocid("musina-18-2025-26")
      and not ledger_mod.looks_like_ocid("")
      and not ledger_mod.looks_like_ocid(None))
af = ledger_mod.amount_flag
check("amount_flag: clean amount -> None (usable)", af(5_000_000) is None)
check("amount_flag: the CSV's zero class", af(0) == "zero")
check("amount_flag: non-zero below R100 -> lt_R100",
      af(50) == "lt_R100" and af(99.99) == "lt_R100")
check("amount_flag: above R10bn -> gt_R10bn (the R1.80tn class)",
      af(1_800_000_000_000) == "gt_R10bn" and af(10_000_000_001) == "gt_R10bn")
check("amount_flag: boundary values R100 / R10bn are clean",
      af(100) is None and af(10_000_000_000) is None)
check("amount_flag: missing / junk amount -> 'missing' (the 27.99% class)",
      af(None) == "missing" and af("not-a-number") == "missing")
ips = ledger_mod.is_placeholder_supplier
check("placeholder suppliers: the Midvaal 'non-award' string",
      ips("non-award") and ips("Non-Award"))
check("placeholder suppliers: 'None', single characters, empty",
      ips("None") and ips("x") and ips("") and ips(None))
check("real supplier names are never placeholders",
      not ips("Thebe Networks (Pty) Ltd")
      and not ips("Government Printing Works"))

# --------------------------------------------------------------------------
# (b) own-outcome aggregation math
# --------------------------------------------------------------------------
print("== (b) own-outcome aggregation: win rate over DECIDED bids only ==")
OWN_BIDS = [
    {"name": "BID-1", "tender_slug": "a", "institution": "SARS",
     "status": "Awarded", "estimated_value": 10_000_000,
     "outcome_value": 11_000_000},
    {"name": "BID-2", "tender_slug": "b", "institution": "SARS",
     "status": "Lost", "estimated_value": 2_000_000, "outcome_value": None},
    {"name": "BID-3", "tender_slug": "c", "institution": "ESKOM",
     "status": "Awarded", "estimated_value": None, "outcome_value": 4_000_000},
    {"name": "BID-4", "tender_slug": "d", "institution": "ESKOM",
     "status": "Submitted", "estimated_value": 1_000_000,
     "outcome_value": None},
    {"name": "BID-5", "tender_slug": "e", "institution": "City of Tshwane",
     "status": "Watching", "estimated_value": None, "outcome_value": None},
    {"name": "BID-6", "tender_slug": "f", "institution": "SARS",
     "status": "Withdrawn", "estimated_value": None, "outcome_value": None},
]
own = ledger_mod.aggregate_own_outcomes(OWN_BIDS)
check("status counters complete and correct",
      own["tracked"] == 6 and own["by_status"]["Awarded"] == 2
      and own["by_status"]["Lost"] == 1 and own["by_status"]["Submitted"] == 1
      and own["by_status"]["Watching"] == 1
      and own["by_status"]["Withdrawn"] == 1)
check("decided = awarded + lost; submitted bids await outcome, "
      "never counted as decided",
      own["decided"] == 3 and own["awaiting_outcome"] == 1)
check("win rate = share of DECIDED bids (2/3 = 66.7%)",
      own["win_rate"] is not None and own["win_rate"]["awarded"] == 2
      and own["win_rate"]["decided"] == 3
      and own["win_rate"]["rate_pct"] == 66.7)
check("win-rate semantics: a record over small N, never a probability",
      "never a probability" in own["win_rate"]["semantics"])
check("no decided outcomes -> win_rate None (no rate over zero)",
      ledger_mod.aggregate_own_outcomes(
          [{"name": "B", "status": "Submitted"}])["win_rate"] is None)
check("empty bid list aggregates to zeros, not errors",
      ledger_mod.aggregate_own_outcomes([])["tracked"] == 0
      and ledger_mod.aggregate_own_outcomes(None)["decided"] == 0)
buyers = {row["buyer"]: row for row in own["per_buyer"]}
check("per-buyer counters (SARS: 3 tracked, 1 awarded / 1 lost = 50.0%)",
      buyers["SARS"]["tracked"] == 3 and buyers["SARS"]["decided"] == 2
      and buyers["SARS"]["awarded"] == 1 and buyers["SARS"]["lost"] == 1
      and buyers["SARS"]["rate_pct"] == 50.0)
check("per-buyer rate only where decided bids exist (Tshwane: counts, "
      "rate None)",
      buyers["City of Tshwane"]["tracked"] == 1
      and buyers["City of Tshwane"]["decided"] == 0
      and buyers["City of Tshwane"]["rate_pct"] is None)
check("per-buyer ordering: most tracked first, then name",
      [r["buyer"] for r in own["per_buyer"]]
      == ["SARS", "ESKOM", "City of Tshwane"])
check("own-outcome block carries the per-subscriber privacy line",
      "PRIVATE" in own["privacy"] and "own" in own["privacy"])

# --------------------------------------------------------------------------
# (c) quoted-vs-awarded deltas against the bid-time pricing bands
# --------------------------------------------------------------------------
print("== (c) quoted-vs-awarded deltas + band positions ==")
TABLES = {
    "meta": {"source": "synthetic", "snapshot_date": "2026-08-20",
             "awards": 1000, "benchmark_rows": 600, "min_cell_n": 30},
    "default_buyer": {"buyer": None, "award_count": 1000,
                      "benchmark_count": 600, "median_rand": 9_000_000,
                      "iqr_rand": [1_000_000, 90_000_000]},
    "buyers": {
        "eskom": {"buyer": "ESKOM", "award_count": 120,
                  "benchmark_count": 45, "median_rand": 20_000_000,
                  "iqr_rand": [5_000_000, 60_000_000]},
    },
    "category_province": {}, "category": {}, "province": {},
}
CARDS = [
    {"slug": "a", "tender_number": "ocds-9t57fa-100", "institution": "ESKOM",
     "category": "Services: General", "province": "Gauteng"},
    {"slug": "c", "tender_number": "ocds-9t57fa-300", "institution": "ESKOM",
     "category": "Services: General", "province": "Gauteng"},
]
cards_by_key = ledger_mod.card_index(CARDS)
rows = ledger_mod.quoted_vs_awarded_rows(
    OWN_BIDS, cards_by_key=cards_by_key, tables=TABLES)
check("one row per Awarded bid with any value (Lost/Submitted never appear)",
      [r["bid"] for r in rows] == ["BID-1", "BID-3"])
check("delta math: quoted R10m, awarded R11m -> +R1m, +10.0%",
      rows[0]["delta_rand"] == 1_000_000 and rows[0]["delta_pct"] == 10.0)
check("one-sided row: awarded value without a quote -> deltas None, "
      "never a guess",
      rows[1]["quoted_rand"] is None and rows[1]["delta_rand"] is None
      and rows[1]["delta_pct"] is None)
check("quoted placed against the SAME band the bid was shown "
      "(ESKOM median R20m: R10m -> 50.0%, within IQR)",
      rows[0]["quoted_band_position"] is not None
      and rows[0]["quoted_band_position"]["ratio_to_median_pct"] == 50.0
      and rows[0]["quoted_band_position"]["position"] == "within_iqr"
      and rows[0]["quoted_band_position"]["band_level"] == "buyer")
check("awarded R4m sits below the R5m-R60m IQR",
      rows[1]["awarded_band_position"]["position"] == "below_iqr"
      and rows[1]["awarded_band_position"]["ratio_to_median_pct"] == 20.0)
check("no card / no tables -> band positions None (absent, never guessed)",
      ledger_mod.quoted_vs_awarded_rows(OWN_BIDS)[0]["quoted_band_position"]
      is None)
bp = ledger_mod.band_position
check("band_position: above the IQR", bp(
    100_000_000, {"median_rand": 20_000_000,
                  "iqr_rand": [5_000_000, 60_000_000],
                  "level": "buyer"})["position"] == "above_iqr")
check("band_position: missing value / band / median -> None",
      bp(None, {"median_rand": 1}) is None and bp(5, None) is None
      and bp(5, {"median_rand": None}) is None
      and bp(5, {"median_rand": 0}) is None)

# --------------------------------------------------------------------------
# (d) ocid resolution for claimed bids
# --------------------------------------------------------------------------
print("== (d) slug -> ocid resolution ==")
rbo = ledger_mod.resolve_bid_ocid
check("slug that IS an ocid resolves to itself (claim-by-tender_number path)",
      rbo({"tender_slug": "ocds-9t57fa-155126"}, {}) == "ocds-9t57fa-155126")
check("slug resolves through the card's tender_number when THAT is the ocid",
      rbo({"tender_slug": "a"}, cards_by_key) == "ocds-9t57fa-100")
check("card whose tender_number is a plain reference resolves to None",
      rbo({"tender_slug": "x"},
          ledger_mod.card_index([{"slug": "x",
                                  "tender_number": "SARS/2026/001"}])) is None)
check("unknown slug / no cards -> None (no fallback guessing)",
      rbo({"tender_slug": "gone"}, cards_by_key) is None
      and rbo({"tender_slug": "a"}, None) is None and rbo({}, {}) is None)

# --------------------------------------------------------------------------
# (e) award extraction: non-empty awards[] ONLY, tags never consulted
# --------------------------------------------------------------------------
print("== (e) award extraction from compiled releases ==")
AWARDED_RELEASE = {
    "ocid": "ocds-9t57fa-100",
    "date": "2026-06-01T00:00:00Z",
    "tag": ["compiled"],
    "tender": {"title": "Networks"},
    "awards": [{"status": "active",
                "value": {"amount": 11_000_000, "currency": "ZAR"},
                "suppliers": [{"id": "za-1", "name": "Thebe Networks (Pty) Ltd"}]}],
}
awards = ledger_mod.extract_awards(AWARDED_RELEASE)
check("non-empty awards[] detected with tag just ['compiled'] "
      "(tags carry no award signal on this feed)",
      len(awards) == 1 and awards[0]["winner"] == "Thebe Networks (Pty) Ltd")
check("clean amount usable, flag None",
      awards[0]["value_rand"] == 11_000_000 and awards[0]["amount_flag"] is None
      and awards[0]["value_usable"] and awards[0]["currency"] == "ZAR")
check("award_date is None ALWAYS (structurally absent from this feed) and "
      "the release date rides as the proxy",
      awards[0]["award_date"] is None
      and awards[0]["date_proxy"] == "2026-06-01T00:00:00Z")
check("empty awards[] -> no award, even when tags SAY award "
      "(detection is non-empty awards[] ONLY)",
      ledger_mod.extract_awards(
          {"ocid": "ocds-9t57fa-200", "tag": ["compiled", "award"],
           "awards": []}) == [])
check("missing awards key / placeholder '{}' release / junk -> no award",
      ledger_mod.extract_awards({"ocid": "ocds-9t57fa-201"}) == []
      and ledger_mod.extract_awards({}) == []
      and ledger_mod.extract_awards(None) == []
      and ledger_mod.extract_awards({"awards": "bogus"}) == [])
placeholder_awards = ledger_mod.extract_awards(
    {"ocid": "ocds-9t57fa-202", "date": "2026-05-01",
     "awards": [{"status": "active", "value": {"amount": 0, "currency": "ZAR"},
                 "suppliers": [{"name": "non-award"}]}]})
check("placeholder winner flagged, zero amount flagged - flagged, "
      "NEVER dropped",
      len(placeholder_awards) == 1
      and placeholder_awards[0]["winner"] == "non-award"
      and placeholder_awards[0]["winner_placeholder"]
      and placeholder_awards[0]["amount_flag"] == "zero"
      and not placeholder_awards[0]["value_usable"])
flagged = ledger_mod.extract_awards(
    {"ocid": "ocds-9t57fa-203",
     "awards": [{"value": {"amount": 50}, "suppliers": [{"name": "Real Co"}]},
                {"value": {"amount": 20_000_000_000},
                 "suppliers": [{"name": "Big Co"}]},
                {"suppliers": [{"name": "No Value Co"}]}]})
check("lt_R100 / gt_R10bn / missing amount classes all carried",
      [a["amount_flag"] for a in flagged] == ["lt_R100", "gt_R10bn", "missing"])
check("award without suppliers -> winner None, placeholder True",
      ledger_mod.extract_awards(
          {"ocid": "o", "awards": [{"value": {"amount": 1_000_000}}]}
      )[0]["winner"] is None
      and ledger_mod.extract_awards(
          {"ocid": "o", "awards": [{"value": {"amount": 1_000_000}}]}
      )[0]["winner_placeholder"])

# --------------------------------------------------------------------------
# (f) matching claimed bids to re-fetched releases
# --------------------------------------------------------------------------
print("== (f) bid <-> release matching: report, never decide ==")
MATCH_BIDS = [
    {"name": "BID-1", "tender_slug": "a", "tender_title": "Networks",
     "institution": "ESKOM", "status": "Submitted"},
    {"name": "BID-2", "tender_slug": "ocds-9t57fa-400",
     "tender_title": "Advertised, never awarded here",
     "institution": "City of Tshwane", "status": "Submitted"},
    {"name": "BID-3", "tender_slug": "no-ocid-here",
     "tender_title": "Non-OCDS source", "institution": "Someone",
     "status": "Watching"},
    {"name": "BID-4", "tender_slug": "ocds-9t57fa-500",
     "tender_title": "Never re-fetched", "institution": "ESKOM",
     "status": "Preparing"},
    {"name": "BID-5", "tender_slug": "ocds-9t57fa-600",
     "tender_title": "Placeholder cache row", "institution": "ESKOM",
     "status": "Submitted"},
]
RELEASES = {
    "ocds-9t57fa-100": AWARDED_RELEASE,
    "ocds-9t57fa-400": {"ocid": "ocds-9t57fa-400", "date": "2026-04-01",
                        "tag": ["compiled"], "awards": []},
    "ocds-9t57fa-600": {},  # the API's "{}" never-published placeholder
}
matched = ledger_mod.match_bid_awards(MATCH_BIDS, RELEASES, cards_by_key)
by_bid = {row["bid"]: row for row in matched["matches"]}
check("one row per claimed bid, regardless of status",
      len(matched["matches"]) == 5)
check("card-resolved ocid matches its re-fetched release and records the "
      "actual winner",
      by_bid["BID-1"]["ocid"] == "ocds-9t57fa-100"
      and by_bid["BID-1"]["published_award"]
      and by_bid["BID-1"]["awards"][0]["winner"] == "Thebe Networks (Pty) Ltd"
      and by_bid["BID-1"]["release_date"] == "2026-06-01T00:00:00Z")
check("published-award note: recorded, bid status never auto-flipped",
      "never auto-flipped" in by_bid["BID-1"]["note"])
check("awardless release -> no award published, note says NEVER lost",
      by_bid["BID-2"]["release_cached"]
      and not by_bid["BID-2"]["published_award"]
      and by_bid["BID-2"]["awards"] == []
      and "NEVER" in by_bid["BID-2"]["note"]
      and "lost" in by_bid["BID-2"]["note"])
check("no row computes an outcome for the user: no 'outcome'/'lost' verdict "
      "field exists, and every awardless cached release carries the "
      "never-lost note",
      not any("outcome" in row for row in matched["matches"])
      and all("NEVER" in row["note"]
              for row in matched["matches"]
              if row["release_cached"] and not row["published_award"]))
check("non-OCDS slug -> ocid None with the nothing-to-match note",
      by_bid["BID-3"]["ocid"] is None
      and by_bid["BID-3"]["note"] == ledger_mod.NOTE_NO_OCID)
check("ocid never re-fetched -> re-fetch-window note "
      "(older ids need re-enumeration)",
      by_bid["BID-4"]["ocid"] == "ocds-9t57fa-500"
      and not by_bid["BID-4"]["release_cached"]
      and "re-enumeration" in by_bid["BID-4"]["note"])
check("'{}' placeholder cache row treated as no release, not as data",
      not by_bid["BID-5"]["release_cached"]
      and by_bid["BID-5"]["note"] == ledger_mod.NOTE_NO_RELEASE)
check("match summary counts agree",
      matched["summary"] == {"claimed": 5, "with_ocid": 4,
                             "release_cached": 2, "published_award": 1,
                             "no_award_published": 1})

# --------------------------------------------------------------------------
# (g) the assembled payload and its research-bound caveats
# --------------------------------------------------------------------------
print("== (g) build_award_ledger payload + caveats ==")
payload = ledger_mod.build_award_ledger(
    OWN_BIDS, {"ocds-9t57fa-100": AWARDED_RELEASE}, cards=CARDS,
    tables=TABLES)
check("payload composes both halves plus semantics and caveats",
      set(payload) >= {"own_outcomes", "published_matches", "semantics",
                       "caveats"}
      and payload["own_outcomes"]["win_rate"]["rate_pct"] == 66.7
      and payload["published_matches"]["summary"]["published_award"] == 1)
caveats = payload["caveats"]
check("caveat: winner-side feed, NEVER a win probability",
      any("winner-side" in c and "NEVER" in c and "probability" in c
          for c in caveats))
check("caveat: buyer-skewed publication with the research numbers "
      "(SARS 75.74 / ESKOM 9.87 / zero publishers), no-match is never lost",
      any("75.74" in c and "9.87" in c and "0.00%" in c
          and "NEVER" in c and "lost" in c for c in caveats))
check("caveat: 72.01% usable values, flags ride, contract-total semantics",
      any("72.01" in c and "never" in c.lower() and "dropped" in c
          and "contract-total" in c for c in caveats))
check("caveat: no award dates - release date is the proxy, trailing "
      "window bound, re-enumeration the only recovery",
      any("no award dates" in c and "release date" in c
          and "re-enumerating" in c for c in caveats))
check("semantics line: calibration + own record, never win probability",
      "NEVER a win probability" in payload["semantics"])
check("caveats list is a copy (mutating a payload never poisons the module)",
      payload["caveats"] is not ledger_mod.LEDGER_CAVEATS)

# --------------------------------------------------------------------------
# (h) purity
# --------------------------------------------------------------------------
print("== (h) module purity ==")
al_src = open(os.path.join(SRC, "compliance/award_ledger.py")).read()
check("award_ledger.py stays frappe-free and stdlib-only",
      "import frappe" not in al_src and "requests" not in al_src)
check("band machinery imported from pricing_bands, never re-implemented",
      "bid_pricing_band" in al_src
      and "def resolve_market_context" not in al_src
      and "def resolve_price_band" not in al_src)
check("release tags are never consulted for award detection",
      '"tag"' not in al_src and "'tag'" not in al_src
      and 'get("tags"' not in al_src)

# --------------------------------------------------------------------------
# (i) the endpoint against a stubbed frappe: scoping, guards, degradation
# --------------------------------------------------------------------------
print("== (i) get_award_ledger endpoint (frappe stubbed) ==")


class AttrDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


ENDPOINT_BIDS = [
    AttrDict(name="BID-1", tender_slug="a", tender_title="Networks",
             institution="ESKOM", closing_date="2026-05-01",
             status="Awarded", estimated_value=10_000_000,
             submitted_on="2026-04-01", outcome_value=11_000_000),
    AttrDict(name="BID-2", tender_slug="ocds-9t57fa-400",
             tender_title="Tshwane one", institution="City of Tshwane",
             closing_date="2026-06-01", status="Submitted",
             estimated_value=None, submitted_on="2026-05-20",
             outcome_value=None),
    AttrDict(name="BID-3", tender_slug="ocds-9t57fa-700",
             tender_title="Corrupt cache row", institution="ESKOM",
             closing_date="2026-07-01", status="Lost", estimated_value=None,
             submitted_on=None, outcome_value=None),
]
CACHE_ROWS = {
    "ocds-9t57fa-100": json.dumps(AWARDED_RELEASE),
    "ocds-9t57fa-400": json.dumps(
        {"ocid": "ocds-9t57fa-400", "date": "2026-04-01",
         "tag": ["compiled"], "awards": []}),
    "ocds-9t57fa-700": "{ not valid json",
}


def build_frappe(user="ray@example.com", app_role="control"):
    frappe = types.ModuleType("frappe")
    frappe.conf = {"app_role": app_role}
    frappe.session = types.SimpleNamespace(user=user)
    frappe.local = types.SimpleNamespace(request=None)
    frappe.whitelist = lambda **kw: (lambda fn: fn)
    frappe.PermissionError = PermissionError
    frappe.captured = {}

    def throw(msg, exc=Exception, title=None):
        raise (exc if isinstance(exc, type) else Exception)(msg)

    frappe.throw = throw
    frappe.get_request_header = lambda name: None

    def get_all(doctype, filters=None, fields=None, order_by=None):
        frappe.captured["doctype"] = doctype
        frappe.captured["filters"] = dict(filters or {})
        frappe.captured["fields"] = list(fields or [])
        return [AttrDict(r) for r in ENDPOINT_BIDS]

    frappe.get_all = get_all

    def get_value(doctype, filters=None, fieldname=None):
        assert doctype == "Raw Tender Cache"
        frappe.captured.setdefault("cache_lookups", []).append(
            (filters or {}).get("ocid"))
        return CACHE_ROWS.get((filters or {}).get("ocid"))

    frappe.db = types.SimpleNamespace(get_value=get_value)
    utils = types.ModuleType("frappe.utils")
    utils.nowdate = lambda: "2026-08-24"
    frappe.utils = utils
    return frappe


market_context = load_module(
    "v_al_market_context", os.path.join(SRC, "compliance/market_context.py"))


def load_endpoint(frappe_mod, cards_fn, tables_fn=None):
    src = open(os.path.join(SRC, "api/tenders/get_award_ledger.py")).read()
    src = src.replace("{app_name}", "_al_stub")
    path = os.path.join(tempfile.mkdtemp(prefix="award_ledger_"), "ep.py")
    open(path, "w").write(src)

    pkg_names = [
        "_al_stub", "_al_stub.tender", "_al_stub.tender.control",
        "_al_stub.tender.control.api", "_al_stub.tender.control.compliance",
    ]
    mods = {}
    for name in pkg_names:
        mods[name] = types.ModuleType(name)
        mods[name].__path__ = []
    opp_utils = types.ModuleType("_al_stub.tender.control.api.opportunity_utils")
    opp_utils.get_cached_opportunities = cards_fn
    mods["_al_stub.tender.control.api"].opportunity_utils = opp_utils
    mods["_al_stub.tender.control.api.opportunity_utils"] = opp_utils
    mc_stub = types.ModuleType("_al_stub.tender.control.compliance.market_context")
    mc_stub.load_market_tables = tables_fn or (lambda: TABLES)
    mods["_al_stub.tender.control.compliance"].market_context = mc_stub
    mods["_al_stub.tender.control.compliance.market_context"] = mc_stub
    mods["_al_stub.tender.control.compliance"].award_ledger = ledger_mod
    mods["_al_stub.tender.control.compliance.award_ledger"] = ledger_mod
    saved = {}
    for name, mod in list(mods.items()) + [
            ("frappe", frappe_mod), ("frappe.utils", frappe_mod.utils)]:
        saved[name] = sys.modules.get(name)
        sys.modules[name] = mod
    try:
        spec = importlib.util.spec_from_file_location("v_al_ep", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for name, orig in saved.items():
            if name.startswith("_al_stub"):
                # the endpoint imports the stub chain lazily at CALL time
                continue
            if orig is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = orig


frappe_stub = build_frappe()
endpoint = load_endpoint(frappe_stub, lambda opt_type: list(CARDS))
result = endpoint.get_award_ledger()
check("own-bids scoping: the ONLY query filter is the session user "
      "(get_my_bids doctrine)",
      frappe_stub.captured["doctype"] == "Tender Bid"
      and frappe_stub.captured["filters"] == {"user": "ray@example.com"})
check("payload carries both halves, semantics, caveats, generated_on",
      set(result) >= {"own_outcomes", "published_matches", "semantics",
                      "caveats", "generated_on"}
      and result["generated_on"] == "2026-08-24")
check("own half aggregates the user's records (2 decided, 50.0% of "
      "decided) and stays private-labelled",
      result["own_outcomes"]["decided"] == 2
      and result["own_outcomes"]["win_rate"]["rate_pct"] == 50.0
      and "PRIVATE" in result["own_outcomes"]["privacy"])
check("quoted-vs-awarded delta rides with the band position",
      result["own_outcomes"]["quoted_vs_awarded"][0]["delta_pct"] == 10.0
      and result["own_outcomes"]["quoted_vs_awarded"][0]
      ["quoted_band_position"]["position"] == "within_iqr")
check("cache read per claimed ocid only, deduped - never a table scan",
      sorted(frappe_stub.captured["cache_lookups"])
      == ["ocds-9t57fa-100", "ocds-9t57fa-400", "ocds-9t57fa-700"])
by_bid_ep = {r["bid"]: r for r in result["published_matches"]["matches"]}
check("card-resolved ocid records the published winner",
      by_bid_ep["BID-1"]["published_award"]
      and by_bid_ep["BID-1"]["awards"][0]["winner"]
      == "Thebe Networks (Pty) Ltd")
check("Tshwane bid: release cached, no award published, note says "
      "NEVER lost",
      by_bid_ep["BID-2"]["release_cached"]
      and not by_bid_ep["BID-2"]["published_award"]
      and "NEVER" in by_bid_ep["BID-2"]["note"])
check("corrupt cache JSON degrades to the no-release note, never a crash",
      not by_bid_ep["BID-3"]["release_cached"]
      and by_bid_ep["BID-3"]["note"] == ledger_mod.NOTE_NO_RELEASE)
check("caveats ride the endpoint payload verbatim",
      any("72.01" in c for c in result["caveats"])
      and any("no award dates" in c for c in result["caveats"]))


def broken_cards(opt_type):
    raise RuntimeError("catalog cache down")


broken_frappe = build_frappe()
broken_ep = load_endpoint(broken_frappe, broken_cards,
                          tables_fn=lambda: (_ for _ in ()).throw(
                              RuntimeError("fixture down")))
broken_result = broken_ep.get_award_ledger()
check("catalog / fixture failures degrade the enrichment, never the "
      "ledger (slug-shaped ocids still match)",
      broken_result["own_outcomes"]["decided"] == 2
      and {r["bid"]: r for r in broken_result["published_matches"]["matches"]}
      ["BID-2"]["release_cached"]
      and broken_result["own_outcomes"]["quoted_vs_awarded"][0]
      ["quoted_band_position"] is None)

guest_ep = load_endpoint(build_frappe(user="Guest"),
                         lambda opt_type: list(CARDS))
try:
    guest_ep.get_award_ledger()
    guest_blocked = False
except PermissionError:
    guest_blocked = True
check("guests are refused (login-required: per-subscriber data)",
      guest_blocked)

tenant_ep = load_endpoint(build_frappe(app_role="tenant"),
                          lambda opt_type: list(CARDS))
try:
    tenant_ep.get_award_ledger()
    tenant_blocked = False
except Exception:
    tenant_blocked = True
check("non-control sites are refused (control hub only)", tenant_blocked)

# --------------------------------------------------------------------------
# (j) single gateway: manifest registration in ALL THREE cmd families
# --------------------------------------------------------------------------
print("== (j) manifest: three cmd families, one target ==")
with open(MANIFEST, encoding="utf-8") as f:
    manifest = json.load(f)
methods = manifest["app_type"]["control"]["hooks"]["whitelisted_methods"]
target = "{app_name}.tender.control.api.tenders.get_award_ledger.get_award_ledger"
check("public alias registered",
      methods.get("{app_name}.api.tenders.get_award_ledger") == target)
check("canonical control: alias registered (the gateway's cmd)",
      methods.get("control:get_award_ledger") == target)
check("legacy dotted alias registered",
      methods.get("control.control.api.tenders.get_award_ledger") == target)
check("endpoint module exists at the manifest target and whitelists "
      "get_award_ledger",
      os.path.exists(os.path.join(SRC, "api/tenders/get_award_ledger.py"))
      and "@frappe.whitelist()" in open(
          os.path.join(SRC, "api/tenders/get_award_ledger.py")).read())

# --------------------------------------------------------------------------
# (k) nextjs wiring
# --------------------------------------------------------------------------
print("== (k) nextjs wiring ==")
bids_ts = open(os.path.join(NEXT, "app/services/control/bids.ts")).read()
check("bids.ts types the ledger payload (AwardLedger + match/award rows)",
      "interface AwardLedger " in bids_ts
      and "interface AwardLedgerMatch" in bids_ts
      and "interface AwardLedgerAward" in bids_ts)
check("service method rides the single gateway's canonical control: cmd",
      "getAwardLedger" in bids_ts
      and '"control:get_award_ledger"' in bids_ts)
panel_src = open(os.path.join(NEXT, "components/custom/award-ledger.tsx")).read()
check("section self-fetches via the typed service and renders NOTHING on "
      "failure or an empty ledger (bids page never breaks)",
      "TenderBidService.getAwardLedger()" in panel_src
      and panel_src.count("return null") >= 2
      and "fetch(" not in panel_src)
check("section surfaces the caveats and the record-not-probability framing",
      "ledger.caveats" in panel_src
      and "never a win" in panel_src.lower())
check("no-award rendering never says lost",
      "no award published" in panel_src
      and '"lost"' not in panel_src.lower())
page_src = open(os.path.join(NEXT, "app/opportunities/bids/page.tsx")).read()
check("My Bids page wires the section (one line)",
      "AwardLedgerSection" in page_src
      and page_src.count("<AwardLedgerSection />") == 1)
readme = open(os.path.join(REPO, "tender/frappe/tests/verify/README.md")).read()
check("verify README lists this suite", "verify_award_ledger.py" in readme)

# --------------------------------------------------------------------------
print()
passed = sum(1 for _, ok in checks if ok)
print(f"{passed}/{len(checks)} checks passed")
sys.exit(0 if passed == len(checks) else 1)
