"""Standalone verification for the market-context integration: the
derived awards reference tables (built from the committed
tender/awards-dataset/awards_only.csv by tools/build_market_context.py),
their integrity discipline (medians/IQR only, flag-cleaned amounts,
N >= 30 per published price cell), the deterministic buyer lookup with
its fallback chain (buyer -> category x province -> category -> province
-> absent), the additive market_context payload block on the suitability
scorer (every pre-existing payload key untouched), the additive
buyer_burden refinement from real per-buyer stats, and a known-buyer
(ESKOM) plus unknown-buyer case. Exit code 0 = all checks pass."""

import importlib.util
import json
import os
import sys
import types

# O-05: in-tree suite runs must leave no __pycache__ litter under src/
sys.dont_write_bytecode = True

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SRC = os.path.join(REPO, "tender/frappe/src/control")
FIXTURES = os.path.join(REPO, "tender/frappe/fixtures")
DATA_JSON = os.path.join(SRC, "compliance/data/market_context.json")
AWARDS_CSV = os.path.join(REPO, "tender/awards-dataset/awards_only.csv")
GENERATOR = os.path.join(REPO, "tender/frappe/tools/build_market_context.py")

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


# --------------------------------------------------------------------------
# frappe stub (suitability.py imports frappe.utils.cint)
# --------------------------------------------------------------------------
frappe_stub = types.ModuleType("frappe")
utils_stub = types.ModuleType("frappe.utils")
utils_stub.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
utils_stub.flt = lambda v, precision=None: float(v) if v not in (None, "") else 0.0
utils_stub.nowdate = lambda: TODAY_STR
utils_stub.now = lambda: TODAY_STR + " 12:00:00"
utils_stub.getdate = lambda v=None: v
frappe_stub.utils = utils_stub
frappe_stub.log_error = lambda *a, **k: None
sys.modules["frappe"] = frappe_stub
sys.modules["frappe.utils"] = utils_stub
TODAY_STR = "2026-08-23"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mc = load_module("v_market_context", os.path.join(SRC, "compliance/market_context.py"))
suitability = load_module("v_suitability", os.path.join(SRC, "compliance/suitability.py"))
generator = load_module("v_build_market_context", GENERATOR)

with open(DATA_JSON, encoding="utf-8") as f:
    COMMITTED_TEXT = f.read()
TABLES = json.loads(COMMITTED_TEXT)

with open(os.path.join(FIXTURES, "tender_compliance_rules.json"), encoding="utf-8") as f:
    ALL_RULES = json.load(f)
TODAY = "2026-08-23"

# --------------------------------------------------------------------------
# (a) generator reproducibility: rebuild from the committed CSV and diff
# --------------------------------------------------------------------------
print("== (a) generator reproducibility (tables == deterministic rebuild) ==")
rebuilt = generator.render(generator.build_tables(AWARDS_CSV))
check("committed tables byte-match a fresh deterministic rebuild from the CSV",
      rebuilt == COMMITTED_TEXT)

# --------------------------------------------------------------------------
# (b) table integrity: schema, medians-only, the N >= 30 discipline
# --------------------------------------------------------------------------
print("== (b) table integrity ==")
check("top-level schema: meta/buyers/default_buyer + the three price tables",
      set(TABLES) == {"meta", "buyers", "default_buyer",
                      "category_province", "category", "province"})
meta = TABLES["meta"]
check("meta pins the source dataset, its sha256 and the snapshot date",
      meta["source"] == "tender/awards-dataset/awards_only.csv"
      and len(meta["source_sha256"]) == 64 and meta["snapshot_date"] == "2026-08-20")
check("meta counts match the research report (32,589 awards; 22,311 "
      "flag-clean benchmark rows)",
      meta["awards"] == 32589 and meta["benchmark_rows"] == 22311)
check("overall benchmark median matches the report (R13,885,686)",
      meta["overall"]["median_rand"] == 13885686
      and meta["overall"]["n"] == 22311)
check("MEDIANS ONLY: no table field anywhere carries a mean",
      "mean" not in COMMITTED_TEXT.lower())

price_cells = (
    list(TABLES["category_province"].values())
    + list(TABLES["category"].values())
    + list(TABLES["province"].values())
)
check("every published price cell respects N >= 30 (the #53 discipline)",
      price_cells
      and all(c["n"] >= meta["min_cell_n"] == 30 for c in price_cells))
check("every price cell's IQR brackets its median (q1 <= median <= q3)",
      all(c["iqr_rand"][0] <= c["median_rand"] <= c["iqr_rand"][1]
          for c in price_cells))
check("category x province cells exist and only use the coarse categories",
      len(TABLES["category_province"]) >= 25
      and all(k.split("|")[0] in ("services", "goods", "works")
              for k in TABLES["category_province"]))
check("category + province fallback tables cover the coarse categories and "
      "provinces", set(TABLES["category"]) == {"services", "goods", "works"}
      and len(TABLES["province"]) == 10)

buyers = TABLES["buyers"]
check("~200 top buyers committed (200 computed + 3 documented zero "
      "publishers)", len(buyers) == 203)
check("buyer keys are their own normalized names (lookup by construction)",
      all(mc.normalize_buyer(v["buyer"]) == k for k, v in buyers.items()))
check("buyer medians published ONLY where the buyer holds >= 30 clean "
      "amounts; below that the median is null, never a guess",
      all((v["median_rand"] is not None) == (v["benchmark_count"] >= 30)
          for v in buyers.values()))
check("zero publishers committed with award_count 0 + behavior 'zero' "
      "(channel gap, not zero awards)",
      all(buyers[mc.normalize_buyer(n)]["award_count"] == 0
          and buyers[mc.normalize_buyer(n)]["publication_behavior"] == "zero"
          for n in ("City of Tshwane", "Mnquma Local Municipality",
                    "City Council of Johannesburg")))
check("default buyer entry never prices (median null) but carries the "
      "corpus entrant share (55.54% - report section 4)",
      TABLES["default_buyer"]["median_rand"] is None
      and TABLES["default_buyer"]["entrant_share_pct"] == 55.54)
check("known per-buyer stats reproduce the report: SANRAL incumbency "
      "61.56%, Justice median R1.40m band, ESKOM median R121.05m",
      buyers[mc.normalize_buyer(
          "South African National Roads Agency Soc Limited (SANRAL)"
      )]["incumbency_share_pct"] == 61.56
      and buyers["justice & constitutional development"]["median_rand"] == 1395640
      and buyers["eskom"]["median_rand"] == 121047075)

# --------------------------------------------------------------------------
# (c) lookup fallback chain: buyer -> cat x prov -> category -> province -> absent
# --------------------------------------------------------------------------
print("== (c) lookup fallback chain ==")


def ctx(institution, category, province):
    return mc.resolve_market_context(
        {"institution": institution, "category": category, "province": province},
        tables=TABLES)


eskom = ctx("ESKOM SOC Ltd", "Services: Electrical", "Gauteng")
check("buyer hit: 'ESKOM SOC Ltd' resolves to buyer ESKOM via the "
      "suffix-stripped alias", eskom["buyer_stats"]["matched"]
      and eskom["buyer_stats"]["match_type"] == "alias"
      and eskom["buyer_stats"]["buyer"] == "ESKOM")
check("buyer-level price band wins the chain where the buyer holds N >= 30",
      eskom["price_band"]["level"] == "buyer"
      and eskom["price_band"]["n"] == buyers["eskom"]["benchmark_count"]
      and eskom["price_band"]["median_rand"] == 121047075)
sanral = ctx("SANRAL", "Civil engineering", "National")
check("parenthetical acronym alias: 'SANRAL' resolves the full SANRAL row",
      sanral["buyer_stats"]["matched"]
      and "SANRAL" in sanral["buyer_stats"]["buyer"])
unknown = ctx("Some Unknown Buyer (Pty) Ltd", "Services: Professional", "Gauteng")
check("unknown buyer falls to category x province (level named in the band)",
      not unknown["buyer_stats"]["matched"]
      and unknown["buyer_stats"]["match_type"] == "default"
      and unknown["price_band"]["level"] == "category_province"
      and unknown["price_band"]["n"]
      == TABLES["category_province"]["services|gauteng"]["n"])
cat_only = ctx("Some Unknown Buyer", "Construction", "")
check("no province -> category-level fallback (works)",
      cat_only["price_band"]["level"] == "category"
      and cat_only["coarse_category"] == "works"
      and cat_only["price_band"]["median_rand"]
      == TABLES["category"]["works"]["median_rand"])
prov_only = ctx("Some Unknown Buyer", "General Procurement", "Free State")
check("unmappable category -> province-level fallback",
      prov_only["coarse_category"] is None
      and prov_only["price_band"]["level"] == "province"
      and prov_only["price_band"]["n"] == TABLES["province"]["free state"]["n"])
absent = ctx("Some Unknown Buyer", "General Procurement", "")
check("nothing comparable -> price band ABSENT with the caveat named "
      "(never a guess)", absent["price_band"] is None
      and any("N>=30" in c for c in absent["caveats"]))
zero_pub = ctx("City of Tshwane", "Supplies: General", "Gauteng")
check("zero publisher resolves (behavior 'zero') and prices from the "
      "category x province cell, never from its empty buyer row",
      zero_pub["buyer_stats"]["matched"]
      and zero_pub["buyer_stats"]["publication_behavior"] == "zero"
      and zero_pub["price_band"]["level"] == "category_province")
check("coarse category mapping is the deterministic whitelist",
      mc.coarse_category("Civil engineering") == "works"
      and mc.coarse_category("Supplies: Medical") == "goods"
      and mc.coarse_category("Manufacture of furniture") == "goods"
      and mc.coarse_category("Services: Professional") == "services"
      and mc.coarse_category("Human health activities") == "services"
      and mc.coarse_category("General Procurement") is None
      and mc.coarse_category("") is None)
check("missing tables -> honest unavailable block, never a crash",
      mc.resolve_market_context({"institution": "X"}, tables={})["available"]
      is False)

# --------------------------------------------------------------------------
# (d) payload additivity on the scorer + the ESKOM / unknown-buyer cases
# --------------------------------------------------------------------------
print("== (d) scorer payload: additive market_context block ==")
FULL_PROFILE = {
    "csd_maaa_number": "MAAA0123456",
    "tcs_pin": "PIN123456789",
    "company_registration_no": "2019/123456/07",
    "vat_number": "4123456789",
    "enterprise_type": "EME (turnover under R10m - sworn affidavit)",
    "bbbee_level": "1",
    "bbbee_certificate_expiry": "2027-01-01",
    "cidb_grade": "",
    "operating_sectors": "ICT, electrical, maintenance",
    "operating_provinces": "Gauteng",
    "capability_texts": [],
    "coida_good_standing": "1",
    "municipal_rates_current": "1",
    "track_record_evidence": "1",
}
ESKOM_CARD = {
    "slug": "mc-eskom-1",
    "title": "Maintenance of electrical infrastructure",
    "institution": "ESKOM SOC Ltd",
    "category": "Services: Electrical",
    "tender_type": "Request for Bid(Open-Tender)",
    "province": "Gauteng",
    "status": "ACTIVE",
    "closing_date": "2026-09-20",
    "is_it_compulsory": "No",
}

# The pre-existing payload contract (verify_suitability.py's model) - every
# key must still be present after the market-context extension.
PRE_EXISTING_KEYS = {
    "score", "band", "eligible", "opportunity_type", "semantics",
    "source_record_class", "confidence", "days_to_close", "known_weight",
    "dimensions", "hard_failures", "gate_notes", "profile_completeness",
    "manual_checks", "data_flags", "triage", "warnings",
}


def score(card, profile, enrichment=None, opportunity_type="tenders"):
    return suitability.score_suitability(
        card, profile, rules_list=ALL_RULES, enrichment_entry=enrichment,
        opportunity_type=opportunity_type, today=TODAY, market_tables=TABLES)


res = score(ESKOM_CARD, FULL_PROFILE)
check("ALL pre-existing payload keys still present (additive extension)",
      PRE_EXISTING_KEYS <= set(res))
check("payload gains exactly one new key: market_context",
      set(res) - PRE_EXISTING_KEYS == {"market_context"})
mctx = res["market_context"]
check("known-buyer case (ESKOM): matched buyer stats with publication "
      "behaviour + entrant note in machine-readable fields",
      mctx["available"] and mctx["buyer_stats"]["buyer"] == "ESKOM"
      and mctx["buyer_stats"]["publication_rate_pct"] == 9.87
      and mctx["buyer_stats"]["publication_behavior"] == "low"
      and "win 57.83%" in mctx["buyer_stats"]["entrant_note"])
check("known-buyer price band: buyer level, median + IQR + N + semantics",
      mctx["price_band"]["level"] == "buyer"
      and mctx["price_band"]["median_rand"] == 121047075
      and len(mctx["price_band"]["iqr_rand"]) == 2
      and "contract-total" in mctx["price_band"]["semantics"])
check("market context never gates: honesty caveats say so and the card "
      "stays eligible", res["eligible"]
      and any("NEVER predicts winning" in c for c in mctx["caveats"]))

UNKNOWN_CARD = dict(ESKOM_CARD, slug="mc-unknown-1",
                    institution="Really Obscure Trading 123 CC",
                    category="Services: Professional")
ures = score(UNKNOWN_CARD, FULL_PROFILE)
umctx = ures["market_context"]
check("unknown-buyer case: default stats (corpus entrant share), band from "
      "the category x province table",
      not umctx["buyer_stats"]["matched"]
      and umctx["buyer_stats"]["entrant_share_pct"] == 55.54
      and umctx["price_band"]["level"] == "category_province")

check("scoring stays deterministic with market context attached",
      score(ESKOM_CARD, FULL_PROFILE) == res)

no_tables = suitability.score_suitability(
    ESKOM_CARD, FULL_PROFILE, rules_list=ALL_RULES, today=TODAY,
    market_tables={})
check("empty/missing tables degrade to an honest unavailable block; the "
      "card still scores",
      no_tables["market_context"]["available"] is False
      and no_tables["score"] is not None
      and no_tables["band"] in ("strong", "review", "marginal", "poor"))

grant = score({"slug": "g", "title": "Grant Opportunity: SME support",
               "organization": "SEDA", "deadline": "2026-12-01"},
              FULL_PROFILE, opportunity_type="grants")
equity = score({"slug": "e", "title": "Equity Opportunity: Fund",
                "organization": "Fund", "territory": "South Africa"},
               FULL_PROFILE, opportunity_type="equity")
check("grants/equity carry an explicit not-applicable market_context "
      "(tender-only data), never a fabricated band",
      grant["market_context"]["available"] is False
      and equity["market_context"]["available"] is False)

# --------------------------------------------------------------------------
# (e) buyer_burden consumes the real per-buyer stats - ADDITIVELY
# --------------------------------------------------------------------------
print("== (e) buyer_burden refinement (additive, base rules never removed) ==")
bb_detail = res["dimensions"]["buyer_burden"]["reasons"][0]["detail"]
check("ESKOM burden notes the low publication rate (outcome visibility)",
      "publishes few or no award outcomes" in bb_detail and "9.87%" in bb_detail)
sanral_card = dict(ESKOM_CARD, slug="mc-sanral-1",
                   institution="South African National Roads Agency Soc "
                               "Limited (SANRAL)",
                   category="Civil engineering")
sres = score(sanral_card, dict(FULL_PROFILE, cidb_grade="9CE",
                               operating_sectors="civil engineering, roads"))
sdetail = sres["dimensions"]["buyer_burden"]["reasons"][0]["detail"]
check("SANRAL burden notes the 61.56% at-buyer incumbency concentration",
      "incumbent-heavy" in sdetail and "61.56%" in sdetail)
justice_card = dict(ESKOM_CARD, slug="mc-justice-1",
                    institution="Justice & Constitutional Development",
                    category="Services: Professional")
jres = score(justice_card, FULL_PROFILE)
jdetail = jres["dimensions"]["buyer_burden"]["reasons"][0]["detail"]
check("entrant-friendly buyer (Justice, 62.87%) earns the entrant credit "
      "note", "entrant-friendly" in jdetail and "62.87%" in jdetail)
check("refined factors still respect the 0..1 band",
      0 <= res["dimensions"]["buyer_burden"]["points"]
      <= suitability.FIT_WEIGHTS["buyer_burden"]
      and 0 <= jres["dimensions"]["buyer_burden"]["points"]
      <= suitability.FIT_WEIGHTS["buyer_burden"])

# The base fixture logic must be untouched for unmatched buyers: a
# municipal buyer outside the awards tables keeps exactly the pre-existing
# municipal deduction and QUIRK handling.
MUSINA_CARD = {
    "slug": "mc-musina-1",
    "title": "Interactive Cloud-Based Helpdesk Management System",
    "institution": "Musina Local Municipality",
    "category": "Services: ICT and related",
    "tender_type": "Request for Quotation",
    "province": "Limpopo",
    "status": "ACTIVE",
    "closing_date": "2026-09-15",
    "is_it_compulsory": "No",
}
mres = score(MUSINA_CARD, dict(FULL_PROFILE, operating_provinces="Limpopo"))
mdetail = mres["dimensions"]["buyer_burden"]["reasons"][0]["detail"]
check("unmatched buyer (Musina): municipal + QUIRK base logic only - no "
      "market refinement applied",
      not mres["market_context"]["buyer_stats"]["matched"]
      and "municipal buyer" in mdetail
      and "QUIRK-MUSINA" in mdetail
      and "award outcomes" not in mdetail
      and "incumbent-heavy" not in mdetail
      and "entrant-friendly" not in mdetail)
base_bb, _ = suitability._factor_buyer_burden(MUSINA_CARD, [], None)
stats_bb, _ = suitability._factor_buyer_burden(
    MUSINA_CARD, [], mres["market_context"]["buyer_stats"])
check("unmatched buyer stats change nothing in the factor value",
      base_bb == stats_bb)

# --------------------------------------------------------------------------
print()
passed = sum(1 for _, ok in checks if ok)
print(f"{passed}/{len(checks)} checks passed")
sys.exit(0 if passed == len(checks) else 1)
