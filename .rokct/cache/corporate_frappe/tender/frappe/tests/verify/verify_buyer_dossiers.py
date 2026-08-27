"""Standalone verification for the buyer-dossier feature: the derived
per-buyer behavioural tables (built from the committed
tender/awards-dataset/awards_only.csv by tools/build_buyer_dossiers.py),
generator determinism (rebuild-diff against the committed fixture), the
supplier-name normalisation quirk fixes and the placeholder-identity
exclusion, the min-N publication gates (N >= 30 clean amounts per price
cell, N >= 30 identified awards per concentration stat), the
exact -> alias -> none lookup chain shared with market_context.py, the
honesty caveats on every payload, and the gateway endpoint + manifest +
nextjs wiring. Exit code 0 = all checks pass."""

import importlib.util
import json
import os
import re
import sys
import tempfile
import types

# O-05: in-tree suite runs must leave no __pycache__ litter under src/
sys.dont_write_bytecode = True

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SRC = os.path.join(REPO, "tender/frappe/src/control")
NEXTJS = os.path.join(REPO, "tender/nextjs/templates/control")
DATA_JSON = os.path.join(SRC, "compliance/data/buyer_dossiers.json")
AWARDS_CSV = os.path.join(REPO, "tender/awards-dataset/awards_only.csv")
GENERATOR = os.path.join(REPO, "tender/frappe/tools/build_buyer_dossiers.py")
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


bd = load_module("v_buyer_dossiers", os.path.join(SRC, "compliance/buyer_dossiers.py"))
generator = load_module("v_build_buyer_dossiers", GENERATOR)

with open(DATA_JSON, encoding="utf-8") as f:
    COMMITTED_TEXT = f.read()
TABLES = json.loads(COMMITTED_TEXT)

# --------------------------------------------------------------------------
# (a) generator determinism: rebuild from the committed CSV and diff
# --------------------------------------------------------------------------
print("== (a) generator determinism (tables == deterministic rebuild) ==")
rebuilt = generator.render(generator.build_tables(AWARDS_CSV))
check("committed tables byte-match a fresh deterministic rebuild from the CSV",
      rebuilt == COMMITTED_TEXT)
check("a second rebuild is byte-identical (no ordering/hashing drift)",
      generator.render(generator.build_tables(AWARDS_CSV)) == rebuilt)

# --------------------------------------------------------------------------
# (b) table integrity: schema, totals, the min-N discipline
# --------------------------------------------------------------------------
print("== (b) table integrity ==")
check("top-level schema: meta + buyers", set(TABLES) == {"meta", "buyers"})
meta = TABLES["meta"]
buyers = TABLES["buyers"]
check("meta pins the source dataset, its sha256 and the snapshot date",
      meta["source"] == "tender/awards-dataset/awards_only.csv"
      and len(meta["source_sha256"]) == 64
      and meta["snapshot_date"] == "2026-08-20")
check("every buyer in the feed gets a dossier (581 buyers, 32,589 awards)",
      meta["buyers"] == len(buyers) == 581 and meta["awards"] == 32589
      and sum(v["award_count"] for v in buyers.values()) == 32589)
check("placeholder exclusion is corpus-visible: 12,250 id-'0' rows (37.6%, "
      "research report section 4) plus the placeholder-name artifacts",
      meta["identified_awards"] + meta["placeholder_awards"] == meta["awards"]
      and 12250 <= meta["placeholder_awards"] <= 12262
      and meta["identified_awards"]
      == sum(v["identified_award_count"] for v in buyers.values()))
check("buyer keys are their own normalized names (lookup by construction)",
      all(bd.normalize_buyer(v["buyer"]) == k for k, v in buyers.items()))
check("per-buyer identified + placeholder always equals award_count",
      all(v["identified_award_count"] + v["placeholder_award_count"]
          == v["award_count"] for v in buyers.values()))
check("MEDIANS ONLY: no field anywhere in the fixture carries a mean",
      not re.search(r'"[^"]*mean[^"]*":', COMMITTED_TEXT))
check("min-N floors pinned in meta (both 30, the #53 style judgment)",
      meta["min_amount_n"] == 30 and meta["min_concentration_n"] == 30)
check("price cells published ONLY at N >= 30 clean amounts; below that the "
      "median is null, never a guess",
      all((v["median_rand"] is not None) == (v["benchmark_count"] >= 30)
          for v in buyers.values()))
check("every published IQR brackets its median (q1 <= median <= q3)",
      all(v["iqr_rand"][0] <= v["median_rand"] <= v["iqr_rand"][1]
          for v in buyers.values() if v["median_rand"] is not None))
concentration_keys = ("distinct_supplier_count", "top_supplier",
                      "top_supplier_share_pct",
                      "single_win_supplier_share_pct")
check("concentration stats published ONLY at N >= 30 IDENTIFIED awards - "
      "all four fields null together below the floor (concentration on 5 "
      "awards is noise)",
      all(all((v[key] is not None)
              == (v["identified_award_count"] >= 30)
              for key in concentration_keys)
          for v in buyers.values()))
check("published shares stay sane percentages (0 < share <= 100; "
      "single-win share consistent with distinct <= identified)",
      all(0 < v["top_supplier_share_pct"] <= 100
          and 0 <= v["single_win_supplier_share_pct"] <= 100
          and v["distinct_supplier_count"] <= v["identified_award_count"]
          for v in buyers.values()
          if v["top_supplier_share_pct"] is not None))
eskom = buyers["eskom"]
check("known buyer reproduces the report: ESKOM median R121.05m over 772 "
      "clean amounts; long-tail concentration (601 suppliers over 843 "
      "identified awards, top share ~2%)",
      eskom["median_rand"] == 121047075 and eskom["benchmark_count"] == 772
      and eskom["identified_award_count"] == 843
      and eskom["distinct_supplier_count"] == 601
      and eskom["top_supplier_share_pct"] == 2.25
      and eskom["single_win_supplier_share_pct"] == 56.23)
thin = [v for v in buyers.values() if v["award_count"] < 30]
check("thin buyers exist and publish counts but no gated stats",
      thin and all(v["median_rand"] is None
                   and v["top_supplier_share_pct"] is None for v in thin))

# --------------------------------------------------------------------------
# (c) supplier normalisation + placeholder identity
# --------------------------------------------------------------------------
print("== (c) supplier normalisation + placeholder exclusion ==")
norm = generator.normalize_supplier_name
check("fully parenthesised blank-name quirk unwraps: ' (AGRI EXPERTS JV)' "
      "-> 'agri experts jv'",
      norm(" (AGRI EXPERTS JV)") == "agri experts jv"
      and norm("(EZINGENI SECURITY AND CLEANING)")
      == "ezingeni security and cleaning")
check("unwrapped form merges with the bare form of the same supplier",
      norm(" (Agri Experts JV)") == norm("AGRI EXPERTS JV"))
check("partial parentheticals are NEVER unwrapped (no fuzzy merging): "
      "'SULZER PUMPS (SOUTH AFRICA)' keeps its parenthetical",
      norm("SULZER PUMPS (SOUTH AFRICA)") == "sulzer pumps (south africa)")
check("conservative recipe otherwise: trim, casefold, whitespace collapse, "
      "trailing punctuation",
      norm("  Foo   BAR. ") == "foo bar" and norm(None) == "")
check("placeholder supplier id '0' yields NO identity (excluded from "
      "concentration, still counted in award_count)",
      generator.supplier_identity(
          {"supplier_ids": "0", "supplier_names": "REAL LOOKING NAME"})
      is None)
check("placeholder supplier names ('None', single characters) yield NO "
      "identity even with a real id",
      generator.supplier_identity(
          {"supplier_ids": "12345", "supplier_names": "None"}) is None
      and generator.supplier_identity(
          {"supplier_ids": "12345", "supplier_names": " N "}) is None)
check("a real identity survives: real id + real name -> normalised key",
      generator.supplier_identity(
          {"supplier_ids": "89846",
           "supplier_names": "SULZER PUMPS (SOUTH AFRICA)"})
      == "sulzer pumps (south africa)")

# --------------------------------------------------------------------------
# (d) lookup chain: exact -> alias -> none (market_context machinery)
# --------------------------------------------------------------------------
print("== (d) lookup chain ==")
entry, match = bd.resolve_dossier("ESKOM", TABLES)
check("exact hit: 'ESKOM' resolves its dossier by normalized name",
      match == "exact" and entry["buyer"] == "ESKOM")
entry, match = bd.resolve_dossier("ESKOM SOC Ltd", TABLES)
check("alias hit: 'ESKOM SOC Ltd' resolves via the suffix-stripped alias",
      match == "alias" and entry["buyer"] == "ESKOM")
entry, match = bd.resolve_dossier("SANRAL", TABLES)
check("parenthetical acronym alias: 'SANRAL' resolves the full SANRAL row",
      match == "alias" and "SANRAL" in entry["buyer"])
entry, match = bd.resolve_dossier("Some Unknown Buyer (Pty) Ltd", TABLES)
check("unknown buyer -> (None, 'none'): deliberately NO averaged default "
      "dossier", entry is None and match == "none")
payload = bd.resolve_buyer_dossier("ESKOM SOC Ltd", tables=TABLES)
check("matched payload carries the dossier verbatim + match provenance",
      payload["available"] and payload["matched"]
      and payload["match_type"] == "alias"
      and payload["dossier"] == TABLES["buyers"]["eskom"]
      and payload["dataset"]["snapshot_date"] == "2026-08-20")
miss = bd.resolve_buyer_dossier("City of Tshwane Metro", tables=TABLES)
check("unmatched payload: matched False, dossier None, channel-gap caveat "
      "FIRST (absence is not evidence of no awards)",
      miss["available"] and not miss["matched"] and miss["dossier"] is None
      and "channel gap" in miss["caveats"][0])
check("missing tables -> honest unavailable block, never a crash",
      bd.resolve_buyer_dossier("ESKOM", tables={})["available"] is False)

# --------------------------------------------------------------------------
# (e) honesty caveats on every payload
# --------------------------------------------------------------------------
print("== (e) payload caveats ==")
for name, p in (("matched", payload), ("unmatched", miss)):
    caveats = " | ".join(p["caveats"])
    check("{0} payload carries the full honesty layer: winner-side only, "
          "publication bias, PROXY semantics, placeholder exclusion, "
          "upper-bound counts".format(name),
          "winner-side" in caveats and "NEVER predicts winning" in caveats
          and "publication-discipline bias" in caveats
          and "PROXY" in caveats
          and "placeholder" in caveats and "UPPER bound" in caveats)
check("semantics line states aggregate public data + medians-only + N-gated",
      "aggregate public data" in payload["semantics"]
      and "medians/IQR never means" in payload["semantics"]
      and "N-gated" in payload["semantics"])
check("newcomer proxy definition in the fixture states the "
      "within-published-dataset limit",
      "proxy within the published-awards dataset only"
      in meta["definitions"]["single_win_supplier_share_pct"])

# --------------------------------------------------------------------------
# (f) wiring: manifest (all three cmd families) + nextjs surface
# --------------------------------------------------------------------------
print("== (f) wiring ==")
with open(MANIFEST, encoding="utf-8") as f:
    manifest = json.load(f)
methods = manifest["app_type"]["control"]["hooks"]["whitelisted_methods"]
target = "{app_name}.tender.control.api.tenders.get_buyer_dossier.get_buyer_dossier"
check("get_buyer_dossier rides the single gateway in ALL THREE cmd "
      "families ({app_name}.api.tenders.*, control:*, "
      "control.control.api.tenders.*)",
      methods.get("{app_name}.api.tenders.get_buyer_dossier") == target
      and methods.get("control:get_buyer_dossier") == target
      and methods.get("control.control.api.tenders.get_buyer_dossier")
      == target)
bids_src = open(os.path.join(NEXTJS, "app/services/control/bids.ts"),
                encoding="utf-8").read()
check("nextjs service calls the canonical control: cmd",
      '"control:get_buyer_dossier"' in bids_src
      and "getBuyerDossier" in bids_src)
panel_src = open(os.path.join(NEXTJS, "components/custom/buyer-dossier.tsx"),
                 encoding="utf-8").read()
check("buyer panel is self-contained and renders nothing on empty/error "
      "(a control plane hiccup never breaks the detail page)",
      "BuyerDossierPanel" in panel_src
      and panel_src.count("return null") >= 3
      and "never predicts" in panel_src)
page_src = open(os.path.join(
    NEXTJS, "app/opportunities/[type]/[slug]/page.tsx"),
    encoding="utf-8").read()
check("detail page wires the panel once, near the suitability check",
      page_src.count("<BuyerDossierPanel") == 1
      and page_src.index("TenderSuitabilityCheck")
      < page_src.index("<BuyerDossierPanel"))

# --------------------------------------------------------------------------
# (g) the gateway endpoint against a stubbed frappe
# --------------------------------------------------------------------------
print("== (g) get_buyer_dossier endpoint (frappe stubbed) ==")


def build_frappe(user="ray@example.com", app_role="control"):
    frappe = types.ModuleType("frappe")
    frappe.conf = {"app_role": app_role}
    frappe.session = types.SimpleNamespace(user=user)
    frappe.local = types.SimpleNamespace(request=None)
    frappe.whitelist = lambda **kw: (lambda fn: fn)
    frappe.PermissionError = PermissionError

    def throw(msg, exc=Exception, title=None):
        raise (exc if isinstance(exc, type) else Exception)(msg)

    frappe.throw = throw
    frappe.get_request_header = lambda name: None
    utils = types.ModuleType("frappe.utils")
    utils.nowdate = lambda: "2026-08-23"
    frappe.utils = utils
    return frappe


def load_endpoint(frappe_mod):
    src = open(os.path.join(SRC, "api/tenders/get_buyer_dossier.py")).read()
    src = src.replace("{app_name}", "_app_stub")
    path = os.path.join(tempfile.mkdtemp(prefix="buyer_dossier_"), "ep.py")
    open(path, "w").write(src)

    # fake package chain _app_stub.tender.control.compliance.buyer_dossiers
    pkg_names = ["_app_stub", "_app_stub.tender", "_app_stub.tender.control",
                 "_app_stub.tender.control.compliance"]
    saved = {}
    mods = {}
    for name in pkg_names:
        mods[name] = types.ModuleType(name)
        mods[name].__path__ = []
    mods["_app_stub.tender.control.compliance"].buyer_dossiers = bd
    mods["_app_stub.tender.control.compliance.buyer_dossiers"] = bd
    for name, mod in list(mods.items()) + [
            ("frappe", frappe_mod), ("frappe.utils", frappe_mod.utils)]:
        if isinstance(name, tuple):
            name, mod = name
        saved[name] = sys.modules.get(name)
        sys.modules[name] = mod
    try:
        spec = importlib.util.spec_from_file_location("v_dossier_ep", path)
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


endpoint = load_endpoint(build_frappe())
res = endpoint.get_buyer_dossier("ESKOM SOC Ltd")
check("logged-in call serves the resolved dossier with caveats + timestamp",
      res["matched"] and res["dossier"]["buyer"] == "ESKOM"
      and res["dossier"]["median_rand"] == 121047075
      and len(res["caveats"]) == len(bd.DOSSIER_CAVEATS)
      and res["generated_on"] == "2026-08-23")
res_miss = endpoint.get_buyer_dossier("Totally Unknown Municipality")
check("unknown buyer serves an honest miss (matched False), never an error",
      res_miss["available"] and not res_miss["matched"]
      and res_miss["dossier"] is None)
guest_ep = load_endpoint(build_frappe(user="Guest"))
try:
    guest_ep.get_buyer_dossier("ESKOM")
    guest_blocked = False
except PermissionError:
    guest_blocked = True
check("guests are refused (login required, same doctrine as the radar "
      "endpoint)", guest_blocked)
tenant_ep = load_endpoint(build_frappe(app_role="tenant"))
try:
    tenant_ep.get_buyer_dossier("ESKOM")
    tenant_blocked = False
except Exception:
    tenant_blocked = True
check("non-control sites are refused (control-only guard)", tenant_blocked)

# --------------------------------------------------------------------------
# (h) the Renewal Watch lateness/trust hook (additive, guarded)
# --------------------------------------------------------------------------
print("== (h) renewal-ledger hook on the dossier payload ==")

check("without a renewal ledger the payload carries renewal=None and is "
      "otherwise unchanged (guarded degradation)",
      res["renewal"] is None and res_miss["renewal"] is None)

# real sibling modules behind the stub chain for the hook's call-time imports
renewal_mod = load_module("v_dossier_renewal", os.path.join(SRC, "compliance/renewal.py"))
mc_mod = load_module("v_dossier_mc", os.path.join(SRC, "compliance/market_context.py"))
sys.modules["_app_stub.tender.control.compliance.renewal"] = renewal_mod
sys.modules["_app_stub.tender.control.compliance.market_context"] = mc_mod

RESOLVED_WATCHES = [
    {"buyer_normalized": "eskom", "status": "confirmed", "error_days": 120},
    {"buyer_normalized": "eskom", "status": "confirmed", "error_days": 60},
    {"buyer_normalized": "eskom", "status": "missed", "error_days": None},
]


def get_all_watches(doctype, filters=None, fields=None, **kw):
    assert doctype == "Tender Renewal Watch"
    wanted_status = filters["status"][1]
    wanted_buyers = filters["buyer_normalized"][1]
    return [dict(w) for w in RESOLVED_WATCHES
            if w["status"] in wanted_status
            and w["buyer_normalized"] in wanted_buyers]


ledger_frappe = build_frappe()
ledger_frappe.get_all = get_all_watches
ledger_ep = load_endpoint(ledger_frappe)
lres = ledger_ep.get_buyer_dossier("ESKOM SOC Ltd")
check("with resolved watches the dossier carries the counter-based trust "
      "(2 confirmed / 1 missed -> 66.67%) - counts, never probabilities",
      lres["renewal"]["trust"] == {"confirmed": 2, "missed": 1,
                                   "resolved": 3, "hit_rate_pct": 66.67}
      and "never probabilities" in lres["renewal"]["semantics"])
check("lateness correction is the ledger's median confirmed error "
      "(median of 120/60 = 90 days)",
      lres["renewal"]["lateness_days"] == 90)
check("the hook joins on the SHARED normalize_buyer key (alias input "
      "'ESKOM SOC Ltd' still finds the 'eskom' ledger rows)",
      mc_mod.normalize_buyer("ESKOM") == "eskom"
      and lres["dossier"]["buyer"] == "ESKOM")
check("a buyer with no resolved watches still gets renewal=None on a "
      "ledger-capable site",
      ledger_ep.get_buyer_dossier("Totally Unknown Municipality")["renewal"]
      is None)
check("the renewal hook never disturbs the dossier itself (same dossier "
      "block with and without the ledger)",
      lres["dossier"] == res["dossier"] and lres["caveats"] == res["caveats"])

# --------------------------------------------------------------------------
print()
passed = sum(1 for _, ok in checks if ok)
print(f"{passed}/{len(checks)} checks passed")
sys.exit(0 if passed == len(checks) else 1)
