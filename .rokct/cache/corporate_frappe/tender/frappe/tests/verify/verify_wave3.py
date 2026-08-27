#!/usr/bin/env python3
"""Standalone verification for wave-3 (F-14 direct fetcher + F-08 enrichment gating).

Runs the rewritten test_tender_fetching.py contract logic outside a bench:
frappe fully stubbed in-memory, requests mocked. Proves:

F-14 fetcher (_fetch_and_cache_tenders_on_control):
  - gap fetch above the persisted max
  - trailing re-fetch window (amendments upserted in place)
  - "{}" (never-published) skip and empty-run termination
  - persistent-500 skip after bounded retries, scan continues
  - ocid dedup / upsert into Raw Tender Cache
  - max-id persistence on Tender Control Settings
  - bootstrap binary search when no max is persisted
  - the lossy LIST endpoint is never touched
  - non-control role is a no-op

F-08 gate (compliance/enrichment_gate.py + GATE-PACK-COLLECT fixture):
  - classification of two REAL records pulled read-only from the published
    catalog (one full-by-enrichment, one advert-only)
  - the fixture rule fires on Advert-Only bid context only
  - enrichment_stats shape over the real catalog
"""

import json
import os
import sys
import types

# O-05: in-tree suite runs must leave no __pycache__ litter under src/
sys.dont_write_bytecode = True
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SRC = os.path.join(REPO, "tender/frappe/src/control")
FIXTURES = os.path.join(REPO, "tender/frappe/fixtures")
HERE = os.path.dirname(os.path.abspath(__file__))

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


# --------------------------------------------------------------------------
# frappe / requests stubs
# --------------------------------------------------------------------------
class SingleStore(dict):
    def get(self, key, default=None):
        return dict.get(self, key, default)


class FakeDB:
    def __init__(self):
        self.raw_cache = {}  # ocid -> row dict
        self.singles = {"Tender Control Settings": SingleStore()}
        self.commits = 0

    def get_value(self, doctype, filters, fieldname):
        assert doctype == "Raw Tender Cache"
        ocid = filters["ocid"]
        row = self.raw_cache.get(ocid)
        return row and row["name"]

    def set_value(self, doctype, name, values):
        assert doctype == "Raw Tender Cache"
        for row in self.raw_cache.values():
            if row["name"] == name:
                row.update(values)
                row["updates"] = row.get("updates", 0) + 1
                return
        raise AssertionError("set_value on missing row " + name)

    def set_single_value(self, doctype, field, value):
        self.singles.setdefault(doctype, SingleStore())[field] = value

    def commit(self):
        self.commits += 1


class FakeDoc(dict):
    def __init__(self, db, payload):
        super().__init__(payload)
        self._db = db

    def insert(self, ignore_permissions=False):
        ocid = self["ocid"]
        assert ocid not in self._db.raw_cache, "duplicate insert for " + ocid
        self._db.raw_cache[ocid] = {
            "name": "RTC-" + ocid,
            "ocid": ocid,
            "data": self["data"],
            "retrieved_on": self["retrieved_on"],
            "updates": 0,
        }
        return self


def build_frappe(conf):
    frappe = types.ModuleType("frappe")
    frappe.conf = dict(conf)
    frappe.db = FakeDB()
    frappe.get_single = lambda doctype: frappe.db.singles.setdefault(doctype, SingleStore())
    frappe.get_doc = lambda payload: FakeDoc(frappe.db, payload)
    utils = types.ModuleType("frappe.utils")
    utils.cint = lambda v: int(v or 0)
    utils.flt = lambda v: float(v or 0)
    utils.now = lambda: "2026-08-20 12:00:00"
    frappe.utils = utils
    return frappe, utils


def release(n, title, amended=False):
    payload = {
        "ocid": f"ocds-9t57fa-{n}",
        "id": f"ocds-9t57fa-{n}-2026-08-20",
        "tag": ["compiled", "tenderAmendment"] if amended else ["compiled"],
        "tender": {"id": str(n), "title": title},
    }
    return payload


def build_requests(responses):
    """requests stub serving ONLY the single-release endpoint.

    responses: id -> release dict | {} | "500". Unknown ids answer "{}"
    (the API's real beyond-the-max behaviour).
    """
    requests_mod = types.ModuleType("requests")

    class RequestException(Exception):
        pass

    requests_mod.RequestException = RequestException
    calls = []

    class Resp:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            if self._payload is None:
                raise ValueError("no json")
            return self._payload

    def get(url, timeout=None, **kwargs):
        assert "?" not in url and "PageNumber" not in url, (
            "list pagination forbidden (F-14): " + url
        )
        assert "/release/ocds-9t57fa-" in url, url
        release_id = int(url.rsplit("-", 1)[1])
        calls.append(release_id)
        spec = responses.get(release_id, {})
        if spec == "500":
            return Resp(500, None)
        return Resp(200, spec)

    requests_mod.get = get
    requests_mod.calls = calls
    return requests_mod


def load_tasks(frappe_mod, requests_mod):
    import importlib.util

    src = open(os.path.join(SRC, "tasks.py")).read().replace("{app_name}", "_app_stub")
    path = os.path.join(tempfile.mkdtemp(prefix="wave3_pycheck_"), "wave3_tasks.py")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(src)

    time_stub = types.ModuleType("time")
    time_stub.sleeps = []
    time_stub.sleep = lambda s: time_stub.sleeps.append(s)

    saved = {}
    for name, mod in (
        ("frappe", frappe_mod),
        ("frappe.utils", frappe_mod.utils),
        ("requests", requests_mod),
        ("time", time_stub),
    ):
        saved[name] = sys.modules.get(name)
        sys.modules[name] = mod
    try:
        spec = importlib.util.spec_from_file_location("wave3_tasks_" + str(len(checks)), path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        for name, orig in saved.items():
            if orig is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = orig
    mod._time_stub = time_stub
    return mod


def run_fetch(responses, last_max, refetch_window=2, conf=None, settings_extra=None):
    frappe_mod, _ = build_frappe(conf or {"app_role": "control", "etenders_api_url": "http://mock-api.com"})
    settings = frappe_mod.db.singles["Tender Control Settings"]
    settings["last_fetched_release_id"] = last_max
    settings["refetch_window_ids"] = refetch_window
    for k, v in (settings_extra or {}).items():
        settings[k] = v
    requests_mod = build_requests(responses)
    tasks = load_tasks(frappe_mod, requests_mod)
    stats = tasks._fetch_and_cache_tenders_on_control()
    return stats, frappe_mod, requests_mod, tasks


print("== F-14: gap fetch, trailing re-fetch, max persistence ==")
stats, fr, rq, tasks = run_fetch(
    {
        99: release(99, "Recent 99"),
        100: release(100, "Recent 100"),
        101: release(101, "New 101"),
        102: release(102, "New 102"),
    },
    last_max=100,
)
check("gap fetch: ids 101-102 cached, 4 rows total",
      len(fr.db.raw_cache) == 4 and "ocds-9t57fa-101" in fr.db.raw_cache
      and "ocds-9t57fa-102" in fr.db.raw_cache)
check("trailing re-fetch: window ids 99,100 fetched first",
      rq.calls[:2] == [99, 100])
check("new max persisted on Tender Control Settings (100 -> 102)",
      fr.db.singles["Tender Control Settings"]["last_fetched_release_id"] == 102
      and stats["last_max_after"] == 102 and stats["last_max_before"] == 100)
check("scan terminated after EMPTY_RUN_LIMIT consecutive '{}' ids",
      stats["unpublished"] == tasks.EMPTY_RUN_LIMIT
      and max(rq.calls) == 102 + tasks.EMPTY_RUN_LIMIT)
check("stats: 4 inserted, 0 updated, 0 errors",
      stats["inserted"] == 4 and stats["updated"] == 0 and stats["errors"] == 0)
check("throttle: one polite sleep per request",
      len([s for s in tasks._time_stub.sleeps if s == 0.2]) == len(rq.calls))
check("db committed", fr.db.commits >= 1)

print("== F-14: ocid dedup / amendment upsert ==")
stats, fr, rq, tasks = run_fetch(
    {
        100: release(100, "T100"),
        101: release(101, "T101"),
        102: release(102, "T102"),
    },
    last_max=100,
)
row101_before = dict(fr.db.raw_cache["ocds-9t57fa-101"])
# second run against the SAME db: 101 amended, 103 newly published
requests2 = build_requests(
    {
        101: release(101, "T101 AMENDED", amended=True),
        102: release(102, "T102"),
        103: release(103, "T103"),
    }
)
fr.db.singles["Tender Control Settings"]["refetch_window_ids"] = 2
tasks2 = load_tasks(fr, requests2)
stats2 = tasks2._fetch_and_cache_tenders_on_control()
row101 = fr.db.raw_cache["ocds-9t57fa-101"]
check("re-fetched amendment UPDATED in place (no duplicate row)",
      len(fr.db.raw_cache) == 4 and row101["updates"] == 1
      and "AMENDED" in row101["data"] and "AMENDED" not in row101_before["data"])
check("second run stats: 1 inserted (103), 2 updated (101,102)",
      stats2["inserted"] == 1 and stats2["updated"] == 2)
check("max advanced 102 -> 103",
      fr.db.singles["Tender Control Settings"]["last_fetched_release_id"] == 103)

print("== F-14: '{}' holes and persistent 500s are skipped ==")
stats, fr, rq, tasks = run_fetch(
    {
        100: release(100, "T100"),
        101: {},        # never-published hole inside the id space
        102: "500",     # persistent server error
        103: release(103, "T103"),
    },
    last_max=100,
    refetch_window=1,
)
check("scan continued past the hole and the 500: id 103 cached",
      "ocds-9t57fa-103" in fr.db.raw_cache
      and fr.db.singles["Tender Control Settings"]["last_fetched_release_id"] == 103)
check("persistent 500 retried exactly RETRY_ATTEMPTS times then skipped",
      len([c for c in rq.calls if c == 102]) == tasks.RETRY_ATTEMPTS
      and stats["errors"] == 1)
check("hole counted as unpublished, not an error",
      stats["unpublished"] == 1 + tasks.EMPTY_RUN_LIMIT)

print("== F-14: bootstrap (no persisted max) binary-searches the current max ==")
corpus = {n: release(n, f"T{n}") for n in range(1, 1001) if n % 37 != 0}  # ~2.7% holes
stats, fr, rq, tasks = run_fetch(corpus, last_max=0, refetch_window=10)
check("bootstrap: approx max found within PROBE_SPAN of true max (1000)",
      1000 - tasks.PROBE_SPAN <= stats["last_max_after"] <= 1000
      and fr.db.singles["Tender Control Settings"]["last_fetched_release_id"] == stats["last_max_after"])
check("bootstrap ingests only a trailing window, not the whole corpus",
      0 < len(fr.db.raw_cache) <= 10 + tasks.PROBE_SPAN
      and len(rq.calls) < 200)

print("== F-14: guards ==")
stats, fr, rq, tasks = run_fetch({1: release(1, "T1")}, last_max=1,
                                 conf={"app_role": "tenant"})
check("non-control role: no-op, zero requests, nothing cached",
      stats is None and rq.calls == [] and len(fr.db.raw_cache) == 0)

print("== F-14: budget cap ==")
stats, fr, rq, tasks = run_fetch(
    {n: release(n, f"T{n}") for n in range(101, 5000)},
    last_max=100, refetch_window=1, settings_extra={"max_ids_per_run": 50},
)
check("max_ids_per_run bounds the run; resume pointer still advances",
      stats["fetched"] == 50
      and fr.db.singles["Tender Control Settings"]["last_fetched_release_id"] == 100 + 49)

# --------------------------------------------------------------------------
# F-08: enrichment gate against two REAL catalog records
# --------------------------------------------------------------------------
print("== F-08: advert-only classification on real published-catalog records ==")
import importlib.util


def load_by_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


eg = load_by_path("w3_enrichment_gate", os.path.join(SRC, "compliance/enrichment_gate.py"))
# rules.py imports frappe at module level - park a stub for the by-path load
_frappe_stub, _ = build_frappe({})
sys.modules.setdefault("frappe", _frappe_stub)
sys.modules.setdefault("frappe.utils", _frappe_stub.utils)
rules_mod = load_by_path("w3_rules", os.path.join(SRC, "compliance/rules.py"))

catalog = json.load(open(os.path.join(HERE, "data", "tenders_catalog.json")))
meta = json.load(open(os.path.join(HERE, "data", "meta_catalog.json")))
ae = meta["advanced_enrichment"]

full_recs = [r for r in catalog if r.get("slug") in ae]
advert_recs = [r for r in catalog if r.get("slug") not in ae]
check("real catalog pulled read-only: 517 records, exactly 1 with pack-derived enrichment",
      len(catalog) == 517 and len(full_recs) == 1 and len(advert_recs) == 516)

full_rec, advert_rec = full_recs[0], advert_recs[0]
full_class = eg.classify_source_record(full_rec, ae[full_rec["slug"]])
advert_class = eg.classify_source_record(advert_rec, None)
check(f"real full record ({full_rec['slug']}) classified Full",
      full_class == eg.FULL)
check(f"real advert-only record ({advert_rec['slug']}, "
      f"{len(json.dumps(advert_rec))}B) classified Advert-Only",
      advert_class == eg.ADVERT_ONLY)
check("calibration holds: every live record is advert-sized (<= 2048B threshold)",
      max(len(json.dumps(r)) for r in catalog) < 2048)
check("inline pack-content field flips the verdict to Full (future-proofing)",
      eg.classify_source_record(dict(advert_rec, pack_content="FULL PACK TEXT"), None)
      == eg.FULL)
check("oversized record flips the verdict to Full (byte threshold is a rule param)",
      eg.classify_source_record(dict(advert_rec, tender_documents="x" * 4000), None)
      == eg.FULL
      and eg.classify_source_record(dict(advert_rec, tender_documents="x" * 4000),
                                    None, {"advert_only_max_bytes": 99999})
      == eg.ADVERT_ONLY)

print("== F-08: GATE-PACK-COLLECT fires on the advert-only bid only ==")
all_rules = json.load(open(os.path.join(FIXTURES, "tender_compliance_rules.json")))
gate = [r for r in all_rules if r["name"] == "GATE-PACK-COLLECT"][0]
check("fixture: Conditional Fatal Registration Gate with parsable trigger + params",
      gate["scope"] == "Conditional" and gate["severity"] == "Fatal"
      and gate["rule_class"] == "Registration Gate"
      and isinstance(json.loads(gate["trigger_condition"]), dict)
      and json.loads(gate["params"])["advert_only_max_bytes"] == 2048)

bid_advert = {"tender_slug": advert_rec["slug"], "tender_title": advert_rec["title"],
              "institution": advert_rec["institution"], "regime": "MBD",
              "source_record_class": advert_class}
bid_full = {"tender_slug": full_rec["slug"], "tender_title": full_rec["title"],
            "institution": full_rec["institution"], "regime": "MBD",
            "source_record_class": full_class}
ctx_advert = rules_mod.bid_context(bid_advert)
ctx_full = rules_mod.bid_context(bid_full)
check("bid_context carries source_record_class",
      ctx_advert["source_record_class"] == "Advert-Only"
      and ctx_full["source_record_class"] == "Full")
check("gate applies to the advert-only bid ONLY",
      rules_mod.rule_applies(gate, ctx_advert)
      and not rules_mod.rule_applies(gate, ctx_full)
      and not rules_mod.rule_applies(gate, rules_mod.bid_context({})))
check("gate has desk-renderable checklist text in the mock-sample style",
      "Collect the FULL official tender pack" in gate["checklist_text"]
      and "nothing can be finalised from the advert alone" in gate["checklist_text"])

print("== F-08: per-category enrichment stats over the real catalog ==")
stats = eg.enrichment_stats(catalog, ae)
check("totals: 517 records, 1 full, 516 advert-only",
      stats["total"] == 517 and stats["full"] == 1 and stats["advert_only"] == 516)
cat_totals = sum(b["total"] for b in stats["categories"].values())
check("category buckets partition the catalog and carry advert_only_pct",
      cat_totals == 517
      and all(0.0 <= b["advert_only_pct"] <= 100.0 for b in stats["categories"].values())
      and all(b["full"] + b["advert_only"] == b["total"] for b in stats["categories"].values()))
check("stats are pure/deterministic (same input -> same output)",
      eg.enrichment_stats(catalog, ae) == stats)

# --------------------------------------------------------------------------
failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL WAVE-3 CHECKS PASSED")
