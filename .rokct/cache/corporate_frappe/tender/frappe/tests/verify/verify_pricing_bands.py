#!/usr/bin/env python3
"""Standalone verification for bid-time pricing bands: the frappe-free
compliance/pricing_bands.py module (band SELECTION delegated verbatim to
market_context.resolve_market_context - fallback chain buyer ->
category x province -> category -> province, N >= 30 discipline -
plus deterministic rand FORMATTING mirroring the frontend's formatRand),
the additive get_my_bids payload enrichment (each tracked bid carries
its tender's typical winning-price band, or None - guarded so a failure
serves the payload exactly as before), and the nextjs wiring (typed
payload, render-nothing-on-empty panel, single-gateway cmd unchanged).
Runs against synthetic tables AND the real committed market-context
fixture + catalog snapshot. Exit code 0 = all checks pass."""

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


pricing_bands = load_module(
    "v_pricing_bands", os.path.join(SRC, "compliance/pricing_bands.py"))
market_context = load_module(
    "v_pb_market_context", os.path.join(SRC, "compliance/market_context.py"))

# --------------------------------------------------------------------------
# (a) format_rand mirrors the frontend formatRand convention exactly
# --------------------------------------------------------------------------
print("== (a) format_rand: one deterministic figure on every surface ==")
fr = pricing_bands.format_rand
check("R950 below the thousand mark", fr(950) == "R950")
check("thousands: R25k (rounded like JS Math.round)", fr(25_400) == "R25k")
check("half rounds away from zero: 1500 -> R2k (JS Math.round parity)",
      fr(1_500) == "R2k")
check("millions keep one decimal: R14.4m", fr(14_400_000) == "R14.4m")
check("R63.3m (the real ARC median's label)", fr(63_333_400) == "R63.3m")
check("billions keep two decimals: R1.20bn", fr(1_200_000_000) == "R1.20bn")
check("R209.7m stays in millions below 1e9", fr(209_719_560) == "R209.7m")
check("missing amount -> None, never a guess",
      fr(None) is None and fr("not-a-number") is None)

# --------------------------------------------------------------------------
# (b) band selection: the fallback chain is market_context's, verbatim
# --------------------------------------------------------------------------
print("== (b) fallback chain buyer -> category x province -> category -> "
      "province -> absent ==")

TABLES = {
    "meta": {"source": "synthetic", "snapshot_date": "2026-08-20",
             "awards": 1000, "benchmark_rows": 600, "min_cell_n": 30},
    "default_buyer": {"buyer": None, "award_count": 1000,
                      "benchmark_count": 600, "median_rand": 9_000_000,
                      "iqr_rand": [1_000_000, 90_000_000],
                      "entrant_share_pct": 30.0,
                      "publication_behavior": "unknown"},
    "buyers": {
        "eskom": {"buyer": "ESKOM", "award_count": 120,
                  "benchmark_count": 45, "median_rand": 20_000_000,
                  "iqr_rand": [5_000_000, 60_000_000],
                  "publication_behavior": "high"},
        "small buyer": {"buyer": "Small Buyer", "award_count": 40,
                        "benchmark_count": 10, "median_rand": 1_000_000,
                        "iqr_rand": [500_000, 2_000_000]},
    },
    "category_province": {
        "services|gauteng": {"median_rand": 14_400_000,
                             "iqr_rand": [1_656_002, 165_305_197], "n": 900},
    },
    "category": {
        "services": {"median_rand": 12_000_000,
                     "iqr_rand": [1_500_000, 100_000_000], "n": 5000},
    },
    "province": {
        "limpopo": {"median_rand": 8_000_000,
                    "iqr_rand": [900_000, 70_000_000], "n": 700},
    },
}

bpb = pricing_bands.bid_pricing_band
band = bpb({"institution": "ESKOM SOC Ltd",
            "category": "Services: General", "province": "Gauteng"},
           tables=TABLES)
check("matched buyer with N >= 30 wins the chain (alias via suffix strip)",
      band is not None and band["level"] == "buyer"
      and band["median_rand"] == 20_000_000 and band["n"] == 45)
band = bpb({"institution": "Small Buyer",
            "category": "Services: General", "province": "Gauteng"},
           tables=TABLES)
check("buyer below the N >= 30 discipline falls to category x province",
      band is not None and band["level"] == "category_province"
      and band["median_rand"] == 14_400_000)
band = bpb({"institution": "Unknown Municipality",
            "category": "Services: General", "province": "Northern Cape"},
           tables=TABLES)
check("no buyer, no province cell -> category level",
      band is not None and band["level"] == "category"
      and band["median_rand"] == 12_000_000)
band = bpb({"institution": "Unknown Municipality",
            "category": "General Procurement", "province": "Limpopo"},
           tables=TABLES)
check("unmapped category skips category levels -> province",
      band is not None and band["level"] == "province"
      and band["median_rand"] == 8_000_000)
check("nothing comparable -> None (client renders NOTHING, never a guess)",
      bpb({"institution": "Unknown Municipality",
           "category": "General Procurement", "province": "Mars"},
          tables=TABLES) is None)
check("missing tables -> None (available False, no fake band)",
      bpb({"institution": "ESKOM"}, tables={}) is None)
check("selection agrees with market_context.resolve_market_context "
      "verbatim (no duplicated chain)",
      market_context.resolve_market_context(
          {"institution": "ESKOM SOC Ltd", "category": "Services: General",
           "province": "Gauteng"}, tables=TABLES,
      )["price_band"]["median_rand"] == 20_000_000)

# --------------------------------------------------------------------------
# (c) the block is display-ready and carries PR #55's honesty caveats
# --------------------------------------------------------------------------
print("== (c) block shape, labels, caveats ==")
band = bpb({"institution": "ESKOM", "category": "Services: General",
            "province": "Gauteng"}, tables=TABLES)
check("headline: scope + median + IQR, pre-formatted",
      band["headline"] == "Published awards for this buyer: "
      "median R20.0m, IQR R5.0m - R60.0m")
check("labels formatted server-side (median_label / iqr_label)",
      band["median_label"] == "R20.0m"
      and band["iqr_label"] == "R5.0m - R60.0m")
check("the one-line caveat mirrors PR #55: winner-side successes only, "
      "publication bias, prices the market, never predicts winning",
      "published successes" in band["caveat"]
      and "publication bias" in band["caveat"]
      and "never predicts" in band["caveat"])
check("the machine-readable caveats ride along (winner-side feed, "
      "no win/loss base rates, contract-total semantics)",
      len(band["caveats"]) == 3
      and any("publication bias" in c for c in band["caveats"])
      and any("NEVER predicts winning" in c for c in band["caveats"])
      and any("contract-total" in c for c in band["caveats"]))
check("dataset provenance carried (source + snapshot date)",
      band["dataset"]["source"] == "synthetic"
      and band["dataset"]["snapshot_date"] == "2026-08-20")
check("band semantics string rides from market_context (median/IQR only, "
      "means unusable)", "median/IQR" in (band["semantics"] or ""))

# --------------------------------------------------------------------------
# (d) attach_pricing_bands: additive per-bid attachment
# --------------------------------------------------------------------------
print("== (d) attach_pricing_bands over the cached catalog ==")
CARDS = [
    {"slug": "esk-001", "tender_number": "ESK/2026/001",
     "institution": "ESKOM", "category": "Services: General",
     "province": "Gauteng"},
    {"slug": "lim-002", "tender_number": "LIM/2026/002",
     "institution": "Unknown Municipality",
     "category": "General Procurement", "province": "Limpopo"},
    {"slug": "mars-003", "tender_number": "MARS/2026/003",
     "institution": "Unknown Municipality",
     "category": "General Procurement", "province": "Mars"},
]
bids = [
    {"name": "BID-1", "tender_slug": "esk-001", "status": "Interested"},
    {"name": "BID-2", "tender_slug": "LIM/2026/002", "status": "Preparing"},
    {"name": "BID-3", "tender_slug": "mars-003", "status": "Interested"},
    {"name": "BID-4", "tender_slug": "gone-from-catalog", "status": "Won"},
]
out = pricing_bands.attach_pricing_bands(bids, CARDS, tables=TABLES)
check("attaches in place and returns the same list, order preserved",
      out is bids and [b["name"] for b in out]
      == ["BID-1", "BID-2", "BID-3", "BID-4"])
check("slug match resolves the band", bids[0]["pricing_band"]["level"] == "buyer")
check("tender_number match resolves too (find_tender_by_slug contract)",
      bids[1]["pricing_band"]["level"] == "province")
check("card with no honest band -> pricing_band None",
      bids[2]["pricing_band"] is None)
check("bid whose tender left the catalog -> pricing_band None",
      bids[3]["pricing_band"] is None)
check("existing bid fields untouched (ADDITIVE enrichment)",
      bids[0]["status"] == "Interested" and bids[3]["status"] == "Won"
      and all(set(b) - {"pricing_band"} == {"name", "tender_slug", "status"}
              for b in bids))

# --------------------------------------------------------------------------
# (e) the real committed fixture + real catalog snapshot
# --------------------------------------------------------------------------
print("== (e) real market-context fixture and catalog ==")
real_tables = market_context.load_market_tables(
    os.path.join(SRC, "compliance/data/market_context.json"))
check("committed fixture loads", bool(real_tables))
band = bpb({"institution": "Agricultural Research Council",
            "category": "Services: General", "province": "Gauteng"},
           tables=real_tables)
check("real buyer band (ARC): buyer level, median R63.3m from 114 awards",
      band is not None and band["level"] == "buyer"
      and band["median_rand"] == 63_333_400
      and band["median_label"] == "R63.3m" and band["n"] == 114)
check("real dataset provenance: 32,589 published awards, 2026-08-20 snapshot",
      band["dataset"]["awards"] == 32589
      and band["dataset"]["snapshot_date"] == "2026-08-20")
with open(os.path.join(REPO, "tender/frappe/tests/verify/data/"
                       "tenders_catalog.json"), encoding="utf-8") as f:
    catalog = json.load(f)
pseudo_bids = [{"name": f"B{i}", "tender_slug": c["slug"]}
               for i, c in enumerate(catalog)]
pricing_bands.attach_pricing_bands(pseudo_bids, catalog, tables=real_tables)
banded = [b["pricing_band"] for b in pseudo_bids if b["pricing_band"]]
check("catalog snapshot: every bid resolved (band or honest None), "
      "and most cards find a comparable cell",
      len(pseudo_bids) == len(catalog) and len(banded) > len(catalog) // 2)
check("every attached band is well-formed (level in chain, R-label, "
      "positive N, caveat present)",
      all(b["level"] in ("buyer", "category_province", "category", "province")
          and str(b["median_label"]).startswith("R")
          and (b["n"] or 0) > 0 and "never predicts" in b["caveat"]
          for b in banded))

# --------------------------------------------------------------------------
# (f) purity: frappe-free, selection logic never duplicated
# --------------------------------------------------------------------------
print("== (f) module purity ==")
pb_src = open(os.path.join(SRC, "compliance/pricing_bands.py")).read()
check("pricing_bands.py stays frappe-free and stdlib-only",
      "import frappe" not in pb_src and "requests" not in pb_src)
check("band selection is imported from market_context, never re-implemented",
      "resolve_market_context" in pb_src
      and "def resolve_price_band" not in pb_src
      and "def resolve_buyer" not in pb_src
      and "def coarse_category" not in pb_src)

# --------------------------------------------------------------------------
# (g) wiring: get_my_bids enrichment guarded, gateway unchanged, nextjs typed
# --------------------------------------------------------------------------
print("== (g) wiring ==")
ep_src = open(os.path.join(SRC, "api/tenders/get_my_bids.py")).read()
check("get_my_bids enrichment present and guarded (any failure serves the "
      "payload exactly as before)",
      "attach_pricing_bands" in ep_src
      and "except Exception" in ep_src.split("attach_pricing_bands")[-1]
      and "get_cached_opportunities" in ep_src)
check("enrichment is additive: the base field list and checklist counts "
      "are untouched",
      '"outcome_value",' in ep_src and 'bid["tasks_done"] = done' in ep_src)
with open(MANIFEST, encoding="utf-8") as f:
    manifest = json.load(f)
methods = manifest["app_type"]["control"]["hooks"]["whitelisted_methods"]
target = "{app_name}.tender.control.api.tenders.get_my_bids.get_my_bids"
check("no new endpoint: get_my_bids still rides the single gateway in ALL "
      "THREE cmd families, unchanged",
      methods.get("{app_name}.api.tenders.get_my_bids") == target
      and methods.get("control:get_my_bids") == target
      and methods.get("control.control.api.tenders.get_my_bids") == target)
bids_ts = open(os.path.join(NEXT, "app/services/control/bids.ts")).read()
check("bids.ts types the band payload (BidPricingBand, optional/null on "
      "TenderBid)",
      "interface BidPricingBand" in bids_ts
      and "pricing_band?: BidPricingBand | null" in bids_ts)
panel_src = open(os.path.join(NEXT, "components/custom/pricing-band.tsx")).read()
check("panel renders NOTHING on a missing band (renewal-radar doctrine)",
      "return null" in panel_src
      and "band.median_rand == null" in panel_src)
check("panel is presentational only: no fetch of its own, no per-method "
      "URL - the band arrives on the get_my_bids payload",
      "fetch(" not in panel_src and "http" not in panel_src.lower()
      and "ControlBaseService" not in panel_src)
page_src = open(os.path.join(NEXT, "app/opportunities/bids/page.tsx")).read()
check("bids page renders the panel per tracked bid",
      "PricingBandPanel" in page_src
      and "band={bid.pricing_band}" in page_src)

# --------------------------------------------------------------------------
# (h) the enriched endpoint against a stubbed frappe
# --------------------------------------------------------------------------
print("== (h) get_my_bids endpoint (frappe stubbed) ==")


class AttrDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


BID_ROWS = [
    AttrDict(name="BID-A", tender_slug="arc-001", tender_title="ARC panel",
             institution="Agricultural Research Council",
             closing_date="2026-09-30", status="Preparing",
             enrichment_level=None, submitted_on=None, outcome_value=None),
    AttrDict(name="BID-B", tender_slug="gone-002", tender_title="Old one",
             institution="Somewhere", closing_date="2026-10-15",
             status="Interested", enrichment_level=None, submitted_on=None,
             outcome_value=None),
]
ENDPOINT_CARDS = [
    {"slug": "arc-001", "tender_number": "ARC/2026/001",
     "institution": "Agricultural Research Council",
     "category": "Services: General", "province": "Gauteng"},
]


def build_frappe():
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
    frappe.get_all = lambda doctype, filters=None, fields=None, order_by=None: [
        AttrDict(r) for r in BID_ROWS]
    frappe.db = types.SimpleNamespace(
        count=lambda doctype, filters=None:
            3 if (filters or {}).get("status") != "Done" else 1)
    return frappe


def load_endpoint(frappe_mod, cards_fn):
    src = open(os.path.join(SRC, "api/tenders/get_my_bids.py")).read()
    src = src.replace("{app_name}", "_app_stub")
    path = os.path.join(tempfile.mkdtemp(prefix="pricing_bands_"), "ep.py")
    open(path, "w").write(src)

    pkg_names = [
        "_app_stub", "_app_stub.tender", "_app_stub.tender.control",
        "_app_stub.tender.control.api",
        "_app_stub.tender.control.compliance",
    ]
    mods = {}
    for name in pkg_names:
        mods[name] = types.ModuleType(name)
        mods[name].__path__ = []
    opp_utils = types.ModuleType("_app_stub.tender.control.api.opportunity_utils")
    opp_utils.get_cached_opportunities = cards_fn
    mods["_app_stub.tender.control.api"].opportunity_utils = opp_utils
    mods["_app_stub.tender.control.api.opportunity_utils"] = opp_utils
    mods["_app_stub.tender.control.compliance"].pricing_bands = pricing_bands
    mods["_app_stub.tender.control.compliance.pricing_bands"] = pricing_bands
    saved = {}
    for name, mod in list(mods.items()) + [("frappe", frappe_mod)]:
        saved[name] = sys.modules.get(name)
        sys.modules[name] = mod
    try:
        spec = importlib.util.spec_from_file_location("v_bids_ep", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for name, orig in saved.items():
            if name.startswith("_app_stub"):
                # the endpoint imports the stub chain lazily at CALL time
                continue
            if orig is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = orig


endpoint = load_endpoint(build_frappe(), lambda opt_type: list(ENDPOINT_CARDS))
payload = endpoint.get_my_bids()
check("payload still lists the bids with checklist counts (base behaviour "
      "untouched)",
      [b["name"] for b in payload] == ["BID-A", "BID-B"]
      and payload[0]["tasks_total"] == 3 and payload[0]["tasks_done"] == 1)
check("catalog-matched bid carries the REAL committed band (ARC buyer "
      "level, R63.3m)",
      payload[0]["pricing_band"] is not None
      and payload[0]["pricing_band"]["level"] == "buyer"
      and payload[0]["pricing_band"]["median_label"] == "R63.3m")
check("bid without a catalog card carries pricing_band None (panel "
      "renders nothing)", payload[1]["pricing_band"] is None)


def broken_cards(opt_type):
    raise RuntimeError("catalog cache down")


broken_ep = load_endpoint(build_frappe(), broken_cards)
broken_payload = broken_ep.get_my_bids()
check("enrichment failure serves the payload exactly as it always was "
      "(guard proven: no pricing_band key, base fields intact)",
      [b["name"] for b in broken_payload] == ["BID-A", "BID-B"]
      and all("pricing_band" not in b for b in broken_payload)
      and broken_payload[0]["tasks_total"] == 3)

guest_frappe = build_frappe()
guest_frappe.session = types.SimpleNamespace(user="Guest")
guest_ep = load_endpoint(guest_frappe, lambda opt_type: list(ENDPOINT_CARDS))
try:
    guest_ep.get_my_bids()
    guest_blocked = False
except PermissionError:
    guest_blocked = True
check("guests are still refused (login-required doctrine unchanged)",
      guest_blocked)

# --------------------------------------------------------------------------
print()
passed = sum(1 for _, ok in checks if ok)
print(f"{passed}/{len(checks)} checks passed")
sys.exit(0 if passed == len(checks) else 1)
