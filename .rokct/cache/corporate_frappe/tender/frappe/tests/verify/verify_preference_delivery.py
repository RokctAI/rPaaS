#!/usr/bin/env python3
"""Standalone verification for preference-aware delivery (the opt-in
personalization layer on get_relevant_tenders). Proves the pure module
(compliance/preference_delivery.py): explicit-mismatch-only province
dropping (national / unspecified / unknown always kept), deterministic
sector ranking with stable tie order, the additive preference_fit
annotation, input immutability and determinism - all on top of the
suitability engine's OWN imported factors (no re-implementation). Then
proves the endpoint (api/tenders/get_relevant_tenders.py, exec'd with the
composer {app_name} placeholder substituted against a stubbed frappe):
the legacy path is BYTE-IDENTICAL with zero profile involvement, the
authenticated opt-in path personalizes against the caller's own profile,
the tenant-secret guest path resolves tenant site -> Company Subscription
-> company -> Tender Business Profile, profile_user is admin-only and
refused outright for tenants, a missing profile degrades to the legacy
passthrough, and the endpoint stays registered in ALL THREE manifest cmd
families. Exit code 0 = all checks pass."""

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

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


# --------------------------------------------------------------------------
# frappe stub (suitability.py imports frappe.utils.cint at module level)
# --------------------------------------------------------------------------
class Thrown(Exception):
    pass


utils_stub = types.ModuleType("frappe.utils")
utils_stub.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
utils_stub.flt = lambda v, precision=None: float(v) if v not in (None, "") else 0.0
utils_stub.nowdate = lambda: "2026-08-23"
frappe_stub = types.ModuleType("frappe")
frappe_stub.utils = utils_stub
frappe_stub.log_error = lambda *a, **k: None
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


pd = load_module("v_pref_delivery", os.path.join(SRC, "compliance/preference_delivery.py"))
suitability = load_module("v_pref_suitability", os.path.join(SRC, "compliance/suitability.py"))

PROFILE = {
    "operating_sectors": "ICT, security services",
    "operating_provinces": "Gauteng, Limpopo",
    "capability_texts": [],
}

CARDS = [
    {"slug": "t-1", "title": "Supply of stationery", "category": "Supplies: General",
     "province": "Western Cape"},
    {"slug": "t-2", "title": "ICT infrastructure maintenance",
     "category": "Services: ICT and related", "province": "Gauteng"},
    {"slug": "t-3", "title": "Provision of security services",
     "category": "Services: Security", "province": "National"},
    {"slug": "t-4", "title": "Grass cutting", "category": "Services: General",
     "province": ""},
    {"slug": "t-5", "title": "ICT support services",
     "category": "Services: ICT and related", "province": "Limpopo"},
]

# --------------------------------------------------------------------------
# (a) pure module: dropping is explicit-mismatch only
# --------------------------------------------------------------------------
print("== (a) province filter: positive evidence only ==")
out = pd.personalize_tenders(CARDS, PROFILE)
slugs = [c["slug"] for c in out]
check("explicit province mismatch (Western Cape vs Gauteng/Limpopo) is dropped",
      "t-1" not in slugs)
check("national and unspecified-province cards are always kept",
      "t-3" in slugs and "t-4" in slugs)
check("declared-province matches are kept", "t-2" in slugs and "t-5" in slugs)
no_prov = pd.personalize_tenders(CARDS, {"operating_sectors": "ICT"})
check("profile with NO declared provinces drops nothing (unknown never filters)",
      len(no_prov) == len(CARDS))
check("empty items / empty profile degrade to empty list, never a crash",
      pd.personalize_tenders([], PROFILE) == []
      and pd.personalize_tenders(None, None) == [])

# --------------------------------------------------------------------------
# (b) pure module: deterministic sector ranking + stable ties
# --------------------------------------------------------------------------
print("== (b) sector ranking ==")
check("sector matches rank ahead of non-matches (ICT/security first)",
      slugs.index("t-2") < slugs.index("t-4")
      and slugs.index("t-3") < slugs.index("t-4"))
check("tied sector values keep catalog order (stable sort: t-2 before t-5)",
      slugs.index("t-2") < slugs.index("t-5"))
unknown_rank = pd.personalize_tenders(
    [{"slug": "u-1", "title": "Anything", "category": "Services: General"}],
    {"operating_sectors": ""})
check("undeclared sectors -> band 'unknown' ranked via the documented "
      "stand-in (0.35), never punished below a known mismatch",
      unknown_rank[0]["preference_fit"]["band"] == "unknown"
      and pd.UNKNOWN_RANK_VALUE == 0.35
      and pd.UNKNOWN_RANK_VALUE > 0.1)
check("band mapping covers the factor's whole range",
      pd.sector_band(1.0) == "sector_match"
      and pd.sector_band(0.85) == "sector_match"
      and pd.sector_band(0.6) == "capability_overlap"
      and pd.sector_band(None) == "unknown"
      and pd.sector_band(0.1) == "outside_declared_sectors")

# --------------------------------------------------------------------------
# (c) pure module: annotation, immutability, determinism, reuse
# --------------------------------------------------------------------------
print("== (c) annotation + discipline ==")
fit = out[0]["preference_fit"]
check("every returned card carries the additive preference_fit block "
      "(band + machine-readable codes + honesty semantics)",
      all("preference_fit" in c for c in out)
      and {"band", "sector_code", "sector_detail", "geo_code", "semantics"}
      <= set(fit)
      and "never a win prediction" in fit["semantics"])
originals = copy.deepcopy(CARDS)
pd.personalize_tenders(CARDS, PROFILE)
check("input cards are never mutated (copies annotated, originals untouched)",
      CARDS == originals and "preference_fit" not in CARDS[0])
check("deterministic: identical inputs give identical output",
      pd.personalize_tenders(CARDS, PROFILE) == out)
src_text = open(os.path.join(SRC, "compliance/preference_delivery.py")).read()
check("factors are IMPORTED from the suitability engine, not re-implemented "
      "(no local factor definitions; same behaviour on a shared card)",
      "from .suitability import _factor_geography, _factor_sector" in src_text
      and "def _factor_sector" not in src_text
      and "def _factor_geography" not in src_text
      and pd._factor_sector(CARDS[1], PROFILE)
      == suitability._factor_sector(CARDS[1], PROFILE))
check("module carries no probability language (deterministic doctrine)",
      "probabilit" not in src_text.lower().replace("no probabilities", ""))

# --------------------------------------------------------------------------
# (d) endpoint: stub chain + frappe wiring
# --------------------------------------------------------------------------
print("== (d) endpoint: legacy path byte-identical, zero profile involvement ==")

PASSTHROUGH = [dict(c) for c in CARDS]
calls = {"db_get_value": [], "get_all": [], "get_doc": [], "opps": []}


def reset_frappe(user="Guest", headers=None, roles=()):
    frappe_stub.conf = {"app_role": "control"}
    frappe_stub.session = types.SimpleNamespace(user=user)
    request = types.SimpleNamespace(
        headers=dict(headers or {}), host="fallback.example.com")
    request.headers = types.SimpleNamespace(
        get=lambda key, default=None: dict(headers or {}).get(key, default))
    frappe_stub.local = types.SimpleNamespace(request=request)
    frappe_stub.get_request_header = lambda *a, **k: None
    frappe_stub.whitelist = lambda **kw: (lambda fn: fn)
    frappe_stub.PermissionError = Thrown

    def throw(msg, exc=Exception, title=None):
        raise (exc if isinstance(exc, type) else Thrown)(msg)

    frappe_stub.throw = throw
    frappe_stub.get_roles = lambda user=None: list(roles)
    for key in calls:
        calls[key] = []


DB_VALUES = {}


def db_get_value(doctype, filters, fieldname):
    calls["db_get_value"].append((doctype, dict(filters), fieldname))
    return DB_VALUES.get((doctype, json.dumps(filters, sort_keys=True), fieldname))


GET_ALL_ROWS = {}


def get_all(doctype, filters=None, fields=None, order_by=None, limit=None):
    calls["get_all"].append((doctype, dict(filters or {})))
    return [dict(r) for r in GET_ALL_ROWS.get(
        (doctype, json.dumps(filters or {}, sort_keys=True)), [])]


class ProfileDoc:
    """Minimal Tender Business Profile doc stand-in for profile_snapshot."""

    def __init__(self, data):
        self._data = dict(data)

    def get(self, key):
        return self._data.get(key)


PROFILE_DOCS = {}


def get_doc(doctype, name):
    calls["get_doc"].append((doctype, name))
    return ProfileDoc(PROFILE_DOCS[name])


frappe_stub.db = types.SimpleNamespace(get_value=db_get_value)
frappe_stub.get_all = get_all
frappe_stub.get_doc = get_doc

# stub package chain the endpoint imports lazily at call time
for mod_name in ("_app_stub", "_app_stub.tender", "_app_stub.tender.control",
                 "_app_stub.tender.control.api",
                 "_app_stub.tender.control.api.tenders",
                 "_app_stub.tender.control.compliance"):
    mod = types.ModuleType(mod_name)
    mod.__path__ = []
    sys.modules[mod_name] = mod

ou_stub = types.ModuleType("_app_stub.tender.control.api.opportunity_utils")


def get_opportunities_from_json(opportunity_type, filters=None, public=False):
    calls["opps"].append((opportunity_type, filters))
    return [dict(c) for c in PASSTHROUGH]


ou_stub.get_opportunities_from_json = get_opportunities_from_json
ou_stub.validate_tenant_secret = lambda: True
sys.modules["_app_stub.tender.control.api.opportunity_utils"] = ou_stub

# the REAL sibling modules behind the stub chain (reset first so the
# module-level @frappe.whitelist() decorator exists on the stub)
reset_frappe()
gts = load_endpoint("v_pref_gts", "api/tenders/get_tender_suitability.py")
sys.modules["_app_stub.tender.control.api.tenders.get_tender_suitability"] = gts
sys.modules["_app_stub.tender.control.compliance.preference_delivery"] = pd

reset_frappe()
ep = load_endpoint("v_pref_endpoint", "api/tenders/get_relevant_tenders.py")

reset_frappe(user="Guest")
legacy = ep.get_relevant_tenders(filters=None)
check("legacy call returns the EXACT passthrough (byte-identical JSON)",
      json.dumps(legacy, sort_keys=True)
      == json.dumps(PASSTHROUGH, sort_keys=True))
check("legacy call involves NO profile machinery at all (no db reads, no "
      "doc loads)", calls["db_get_value"] == [] and calls["get_all"] == []
      and calls["get_doc"] == [])
reset_frappe(user="Guest")
legacy_filtered = ep.get_relevant_tenders(filters='{"category": "IT"}')
check("legacy filters still pass straight through to the passthrough layer",
      calls["opps"] == [("tenders", '{"category": "IT"}')]
      and json.dumps(legacy_filtered, sort_keys=True)
      == json.dumps(PASSTHROUGH, sort_keys=True))
reset_frappe(user="Guest")
check("personalized=0 (explicit) is the legacy path too",
      json.dumps(ep.get_relevant_tenders(personalized=0), sort_keys=True)
      == json.dumps(PASSTHROUGH, sort_keys=True)
      and calls["db_get_value"] == [])

# --------------------------------------------------------------------------
# (e) endpoint: authenticated opt-in path
# --------------------------------------------------------------------------
print("== (e) endpoint: authenticated opt-in ==")
PROFILE_DOCS["TBP-0001"] = {
    "operating_sectors": "ICT, security services",
    "operating_provinces": "Gauteng, Limpopo",
    "capabilities": [],
}
DB_VALUES[("Tender Business Profile",
           json.dumps({"user": "bidder@example.com"}, sort_keys=True),
           "name")] = "TBP-0001"

reset_frappe(user="bidder@example.com")
personal = ep.get_relevant_tenders(personalized=1)
pslugs = [c["slug"] for c in personal]
check("authenticated opt-in resolves the CALLER'S OWN profile and "
      "personalizes (mismatch dropped, annotations attached)",
      "t-1" not in pslugs and len(personal) == 4
      and all("preference_fit" in c for c in personal)
      and calls["get_doc"] == [("Tender Business Profile", "TBP-0001")])
check("opt-in ranking matches the pure module exactly",
      pslugs == [c["slug"] for c in pd.personalize_tenders(PASSTHROUGH, {
          "operating_sectors": "ICT, security services",
          "operating_provinces": "Gauteng, Limpopo",
          "capability_texts": [],
          "csd_maaa_number": "", "tcs_pin": "", "company_registration_no": "",
      })])
check("'1' as a string opts in too (query-string transport)",
      [c["slug"] for c in (reset_frappe(user="bidder@example.com"),
                           ep.get_relevant_tenders(personalized="1"))[1]]
      == pslugs)

reset_frappe(user="bidder@example.com")
try:
    ep.get_relevant_tenders(personalized=1, profile_user="other@example.com")
    non_admin_refused = False
except Thrown:
    non_admin_refused = True
check("non-admin naming another profile_user is refused (PermissionError)",
      non_admin_refused)

DB_VALUES[("Tender Business Profile",
           json.dumps({"user": "other@example.com"}, sort_keys=True),
           "name")] = "TBP-0001"
reset_frappe(user="admin@example.com", roles=("System Manager",))
admin_result = ep.get_relevant_tenders(personalized=1,
                                       profile_user="other@example.com")
check("System Manager may personalize for a named profile user",
      [c["slug"] for c in admin_result] == pslugs)

reset_frappe(user="nobody@example.com")
bare = ep.get_relevant_tenders(personalized=1)
check("opt-in WITHOUT a profile degrades to the legacy passthrough "
      "(personalization is a layer, never a gate on delivery)",
      json.dumps(bare, sort_keys=True)
      == json.dumps(PASSTHROUGH, sort_keys=True))

# --------------------------------------------------------------------------
# (f) endpoint: tenant-secret guest path (the daily-sync caller)
# --------------------------------------------------------------------------
print("== (f) endpoint: tenant-secret guest opt-in ==")
DB_VALUES[("Company Subscription",
           json.dumps({"site_name": "acme.rokct.app"}, sort_keys=True),
           "company")] = "ACME Trading (Pty) Ltd"
GET_ALL_ROWS[("Tender Business Profile",
              json.dumps({"company": "ACME Trading (Pty) Ltd"},
                         sort_keys=True))] = [{"name": "TBP-0001"}]

reset_frappe(user="Guest", headers={"X-Rokct-Tenant": "acme.rokct.app"})
tenant_result = ep.get_relevant_tenders(personalized=1)
check("tenant guest opt-in resolves tenant site -> Company Subscription -> "
      "company -> Tender Business Profile and personalizes",
      [c["slug"] for c in tenant_result] == pslugs
      and ("Company Subscription",
           {"site_name": "acme.rokct.app"}, "company") in calls["db_get_value"])
check("tenant profile lookup is deterministic (ordered, limit 1)",
      calls["get_all"] == [("Tender Business Profile",
                            {"company": "ACME Trading (Pty) Ltd"})])

reset_frappe(user="Guest", headers={"X-Rokct-Tenant": "acme.rokct.app"})
try:
    ep.get_relevant_tenders(personalized=1, profile_user="other@example.com")
    tenant_named_refused = False
except Thrown:
    tenant_named_refused = True
check("tenant guest naming a profile_user is refused outright "
      "(never another subscriber's preferences)", tenant_named_refused)

reset_frappe(user="Guest", headers={"X-Rokct-Tenant": "unknown.rokct.app"})
unknown_tenant = ep.get_relevant_tenders(personalized=1)
check("unknown tenant site degrades to the legacy passthrough",
      json.dumps(unknown_tenant, sort_keys=True)
      == json.dumps(PASSTHROUGH, sort_keys=True))

# --------------------------------------------------------------------------
# (g) manifest: the endpoint stays registered in ALL THREE cmd families
# --------------------------------------------------------------------------
print("== (g) manifest wiring ==")
manifest = json.load(open(MANIFEST, encoding="utf-8"))
methods = manifest["app_type"]["control"]["hooks"]["whitelisted_methods"]
target = ("{app_name}.tender.control.api.tenders.get_relevant_tenders."
          "get_relevant_tenders")
check("get_relevant_tenders registered in all three cmd families "
      "({app_name}.api.tenders.*, control:*, control.control.api.tenders.*)",
      methods.get("{app_name}.api.tenders.get_relevant_tenders") == target
      and methods.get("control:get_relevant_tenders") == target
      and methods.get("control.control.api.tenders.get_relevant_tenders")
      == target)

# --------------------------------------------------------------------------
print()
passed = sum(1 for _, ok in checks if ok)
print(f"{passed}/{len(checks)} checks passed")
sys.exit(0 if passed == len(checks) else 1)
