# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Standalone verification for the 2026-08-24 assessment's fix/hygiene items
(tender/SDK-Assessment-2026-08-24.md section 5a).

Same harness family as the sibling verify_* suites: frappe stubbed
in-memory, the REAL modules loaded from this repo (composer `{app_name}`
placeholder substituted), one PASS/FAIL line per check.

Sections:
  (3)  catalog BASE_URL is a setting - Tender Control Settings.
       catalog_base_url with the shipped URL as default/fallback, consumed
       by fetch_remote_json via get_catalog_base_url().
  (5)  structured telemetry - api/telemetry.py's log_api_call routes every
       endpoint's per-call line through frappe.logger("tender.api") as one
       JSON event, degrading to the legacy stderr line (and never raising)
       when no logger is available; every endpoint shim uses it, with a
       format-identical inline fallback for standalone loads.
  (15) tender_country wired as the country fixture-pack scope - the
       shipped fixtures are the SOUTH AFRICA (ZA) pack; the South Africa
       default keeps every behavior EXACTLY as before, while any other
       country loads no rules (honest empty) and never runs the SA
       eTenders direct fetcher.
"""

import importlib.util
import json
import os
import re
import sys
import types

# O-05: in-tree suite runs must leave no __pycache__ litter under src/
sys.dont_write_bytecode = True

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SRC = os.path.join(REPO, "tender/frappe/src/control")

# ---- frappe stub ----
frappe_stub = types.ModuleType("frappe")
utils_stub = types.ModuleType("frappe.utils")
utils_stub.cint = lambda v, default=0: int(float(v)) if v not in (None, "") else default
utils_stub.flt = lambda v, precision=None: float(v) if v not in (None, "") else 0.0
frappe_stub.utils = utils_stub
frappe_stub.whitelist = lambda *a, **k: (lambda f: f)
frappe_stub.conf = {}
frappe_stub.db = types.SimpleNamespace()
sys.modules["frappe"] = frappe_stub
sys.modules["frappe.utils"] = utils_stub

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


def load_module_from_source(name, source, filename):
    module = types.ModuleType(name)
    module.__file__ = filename
    exec(compile(source, filename, "exec"), module.__dict__)
    return module


def read(relpath):
    with open(os.path.join(REPO, relpath), encoding="utf-8") as f:
        return f.read()


print("== (3) catalog BASE_URL is a setting (catalog_base_url seam) ==")

# exec the real opportunity_utils/__init__.py with the composer placeholder
# substituted; its five submodule imports get inert stubs.
for mod_name in (
    "_app_stub", "_app_stub.tender", "_app_stub.tender.control",
    "_app_stub.tender.control.api",
):
    sys.modules.setdefault(mod_name, types.ModuleType(mod_name))
OU_ROOT = "_app_stub.tender.control.api.opportunity_utils"
for sub in (
    "get_opportunities_from_json", "get_cached_opportunities",
    "refresh_all_data", "fetch_remote_json", "validate_tenant_secret",
):
    sub_mod = types.ModuleType(f"{OU_ROOT}.{sub}")
    setattr(sub_mod, sub, lambda *a, **k: None)
    sys.modules[f"{OU_ROOT}.{sub}"] = sub_mod

ou_init_path = os.path.join(SRC, "api/opportunity_utils/__init__.py")
ou = load_module_from_source(
    "t_opportunity_utils",
    read("tender/frappe/src/control/api/opportunity_utils/__init__.py")
    .replace("{app_name}", "_app_stub"),
    ou_init_path,
)

SHIPPED_URL = "https://raw.githubusercontent.com/RokctAI/opportunities/main/published/api/"
check("shipped BASE_URL default unchanged", ou.BASE_URL == SHIPPED_URL)

# no site context at all (db has no get_single_value): shipped default
frappe_stub.db = types.SimpleNamespace()
check("get_catalog_base_url: no site context -> shipped default",
      ou.get_catalog_base_url() == ou.BASE_URL)

# setting unset (None) and blank: shipped default
frappe_stub.db = types.SimpleNamespace(get_single_value=lambda *a, **k: None)
unset_ok = ou.get_catalog_base_url() == ou.BASE_URL
frappe_stub.db = types.SimpleNamespace(get_single_value=lambda *a, **k: "   ")
check("get_catalog_base_url: unset/blank setting -> shipped default",
      unset_ok and ou.get_catalog_base_url() == ou.BASE_URL)

# configured value wins; trailing slash normalised, never doubled
frappe_stub.db = types.SimpleNamespace(
    get_single_value=lambda *a, **k: "https://staging.example/catalog/api")
no_slash = ou.get_catalog_base_url()
frappe_stub.db = types.SimpleNamespace(
    get_single_value=lambda *a, **k: "https://staging.example/catalog/api/")
with_slash = ou.get_catalog_base_url()
check("get_catalog_base_url: configured URL wins, trailing slash normalised",
      no_slash == "https://staging.example/catalog/api/" and with_slash == no_slash)

# the reader looks the setting up on Tender Control Settings.catalog_base_url
seen = []
frappe_stub.db = types.SimpleNamespace(
    get_single_value=lambda doctype, field: seen.append((doctype, field)) or None)
ou.get_catalog_base_url()
check("get_catalog_base_url reads Tender Control Settings.catalog_base_url",
      seen == [("Tender Control Settings", "catalog_base_url")])
frappe_stub.db = types.SimpleNamespace()

# doctype JSON: the field ships with the current URL as its default
settings_fields = {
    f["fieldname"]: f
    for f in json.loads(read(
        "tender/frappe/src/control/doctype/tender_control_settings/"
        "tender_control_settings.json"))["fields"]
}
cbu = settings_fields.get("catalog_base_url")
check("Tender Control Settings ships catalog_base_url (Data) defaulting to the shipped URL",
      cbu is not None and cbu.get("fieldtype") == "Data"
      and cbu.get("default") == SHIPPED_URL)

# the consumer really goes through the seam
frj_src = read("tender/frappe/src/control/api/opportunity_utils/fetch_remote_json.py")
check("fetch_remote_json builds its URL from get_catalog_base_url(), not a hardcoded BASE_URL",
      "get_catalog_base_url()" in frj_src and '{BASE_URL}' not in frj_src)

print("== (5) structured telemetry: log_api_call routes through frappe.logger ==")

import contextlib
import io

telemetry = load_module_from_source(
    "t_telemetry", read("tender/frappe/src/control/api/telemetry.py"),
    os.path.join(SRC, "api/telemetry.py"))

# happy path: one JSON info line through frappe.logger("tender.api"), no stderr
logged = []


class _Recorder:
    def info(self, message):
        logged.append(message)


logger_calls = []


def fake_logger(name, allow_site=False):
    logger_calls.append((name, allow_site))
    return _Recorder()


frappe_stub.logger = fake_logger
err = io.StringIO()
with contextlib.redirect_stderr(err):
    telemetry.log_api_call("get_my_bids", "trace-123", bid="BID-0001")
payload = json.loads(logged[0]) if logged else {}
check("log_api_call emits ONE structured JSON event through frappe.logger",
      len(logged) == 1
      and payload == {"event": "api_call", "endpoint": "get_my_bids",
                      "trace_id": "trace-123", "bid": "BID-0001"}
      and err.getvalue() == "")
check("logger is named tender.api with allow_site=True",
      logger_calls == [("tender.api", True)])

# no logger at all (stubbed frappe): exact legacy stderr line, never a raise
del frappe_stub.logger
err = io.StringIO()
with contextlib.redirect_stderr(err):
    telemetry.log_api_call("claim_tender", "trace-456", slug="my-slug")
check("without frappe.logger the helper degrades to the exact legacy stderr line",
      err.getvalue() == "[tender.api] claim_tender slug=my-slug trace_id=trace-456\n")

# a logger that BLOWS UP mid-write: still the stderr fallback, never a raise
def exploding_logger(name, allow_site=False):
    raise RuntimeError("no site context")


frappe_stub.logger = exploding_logger
err = io.StringIO()
with contextlib.redirect_stderr(err):
    try:
        telemetry.log_api_call("get_tender_detail", None)
        raised = False
    except Exception:
        raised = True
check("a raising logger degrades to stderr and NEVER breaks the request",
      not raised and err.getvalue() == "[tender.api] get_tender_detail trace_id=None\n")
del frappe_stub.logger

# every endpoint shim uses the helper: no bare [tender.api] print survives
# outside the guarded fallback def, and each carries the guarded import.
ENDPOINT_FILES = sorted(
    os.path.join("tender/frappe/src/control/api/tenders", f)
    for f in os.listdir(os.path.join(SRC, "api/tenders"))
    if f.endswith(".py") and f not in ("__init__.py", "tender_entitlement.py")
) + ["tender/frappe/src/control/api/external/get_public_opportunities.py"]
# 22 at the 2026-08-24 assessment; the plan-#58 wave adds get_award_ledger
# (plan #12) and get_compliance_calendar (plan #13), both on the helper.
check("24 endpoint shims on disk (23 tenders + external)", len(ENDPOINT_FILES) == 24)

missing_call, missing_guard, bare_prints = [], [], []
for rel in ENDPOINT_FILES:
    src_text = read(rel)
    # one hit is the fallback def itself; a real call site makes it >= 2
    if src_text.count("log_api_call(") < 2:
        missing_call.append(rel)
    if "from {app_name}.tender.control.api.telemetry import log_api_call" not in src_text:
        missing_guard.append(rel)
    for line in src_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("print(") and "[tender.api]" in stripped \
                and "{endpoint}{extras}" not in stripped:
            bare_prints.append((rel, stripped))
check("every endpoint shim calls log_api_call", missing_call == [])
check("every endpoint shim carries the guarded telemetry import (stub-safe fallback)",
      missing_guard == [])
check("no bare [tender.api] print survives outside the fallback def", bare_prints == [])

# end-to-end through a REAL shim, fallback mode: exec get_my_bids with the
# composer placeholder substituted and NO telemetry module importable - the
# inline fallback must reproduce the legacy line byte-for-byte.
frappe_stub.local = types.SimpleNamespace()  # no request attr -> trace None
frappe_stub.conf = {"app_role": "control"}
frappe_stub.session = types.SimpleNamespace(user="desk@example.com")
frappe_stub.get_all = lambda *a, **k: []
frappe_stub.get_request_header = lambda *a, **k: None
frappe_stub.throw = lambda *a, **k: (_ for _ in ()).throw(Exception(a[0] if a else ""))
frappe_stub.PermissionError = Exception
gmb = load_module_from_source(
    "t_get_my_bids_fallback",
    read("tender/frappe/src/control/api/tenders/get_my_bids.py").replace("{app_name}", "_no_such_pkg"),
    os.path.join(SRC, "api/tenders/get_my_bids.py"))
err = io.StringIO()
with contextlib.redirect_stderr(err):
    gmb.get_my_bids()
check("standalone shim load: inline fallback prints the legacy line byte-for-byte",
      err.getvalue() == "[tender.api] get_my_bids trace_id=None\n")

# end-to-end, composed mode: register the REAL telemetry module under the
# stub package path - the shim must route through frappe.logger, stderr silent.
sys.modules["_app_stub.tender.control.api.telemetry"] = telemetry
logged.clear()
logger_calls.clear()
frappe_stub.logger = fake_logger
gmb2 = load_module_from_source(
    "t_get_my_bids_composed",
    read("tender/frappe/src/control/api/tenders/get_my_bids.py").replace("{app_name}", "_app_stub"),
    os.path.join(SRC, "api/tenders/get_my_bids.py"))
err = io.StringIO()
with contextlib.redirect_stderr(err):
    gmb2.get_my_bids()
composed_payload = json.loads(logged[0]) if logged else {}
check("composed shim load: the call routes through frappe.logger as a JSON event, stderr silent",
      len(logged) == 1 and err.getvalue() == ""
      and composed_payload.get("endpoint") == "get_my_bids"
      and composed_payload.get("event") == "api_call")
del frappe_stub.logger

print("== (15) tender_country wired: country-as-fixture-pack scoping ==")

utils_stub.getdate = lambda v=None: v
utils_stub.now = lambda: "2026-08-24 00:00:00"

rules_spec = importlib.util.spec_from_file_location(
    "t_rules_hygiene", os.path.join(SRC, "compliance/rules.py"))
rules_mod = importlib.util.module_from_spec(rules_spec)
rules_spec.loader.exec_module(rules_mod)

SAMPLE_RULES = [
    {"rule_code": "GATE-TAX", "severity": "Fatal", "enabled": 1},
    {"rule_code": "WARN-X", "severity": "Curable", "enabled": 1},
]

# default install (no site value at all, and the shipped default): ZA pack
# active, load_rules passes the fixture rows through EXACTLY as before.
frappe_stub.db = types.SimpleNamespace()  # no get_single_value -> default
frappe_stub.get_all = lambda *a, **k: [dict(r) for r in SAMPLE_RULES]
check("default install resolves to the South Africa pack, active",
      rules_mod.fixture_pack_country() == "South Africa"
      and rules_mod.fixture_pack_active())
loaded = rules_mod.load_rules()
check("ZA default: load_rules serves the full rule set exactly as before "
      "(Fatal-first, nothing filtered)",
      [r["rule_code"] for r in loaded] == ["GATE-TAX", "WARN-X"])
frappe_stub.db = types.SimpleNamespace(get_single_value=lambda *a, **k: "South Africa")
explicit_sa = rules_mod.load_rules()
frappe_stub.db = types.SimpleNamespace(get_single_value=lambda *a, **k: "ZA")
za_alias = rules_mod.load_rules()
check("explicit South Africa and the ZA alias behave identically to the default",
      [r["rule_code"] for r in explicit_sa] == ["GATE-TAX", "WARN-X"]
      and [r["rule_code"] for r in za_alias] == ["GATE-TAX", "WARN-X"])

# a country with NO shipped fixture pack: honest empty, never SA rules abroad
frappe_stub.db = types.SimpleNamespace(
    get_single_value=lambda *a, **k: "Kenya",
    exists=lambda *a, **k: True,
)
check("unpacked country (Kenya): fixture_pack_active is False",
      not rules_mod.fixture_pack_active())
check("unpacked country: load_rules returns an HONEST EMPTY set even though "
      "rule rows exist", rules_mod.load_rules() == [])
check("unpacked country: get_scoring_rule returns None (PPPFA machinery is "
      "the SA pack)", rules_mod.get_scoring_rule("SCORE-PPPFA-80-20") is None)

# the SA eTenders direct fetcher never runs outside the pack
requests_stub = types.ModuleType("requests")


class _RequestException(Exception):
    pass


def _no_network(*a, **k):
    raise RuntimeError("network attempted")


requests_stub.RequestException = _RequestException
requests_stub.get = _no_network
sys.modules["requests"] = requests_stub

frappe_stub.conf = {"app_role": "control"}
tasks_settings = {}
frappe_stub.get_single = lambda doctype: types.SimpleNamespace(
    get=lambda field, default=None: tasks_settings.get(field, default))
frappe_stub.db = types.SimpleNamespace()
tasks_mod = load_module_from_source(
    "t_tasks_hygiene",
    read("tender/frappe/src/control/tasks.py").replace("{app_name}", "_app_stub"),
    os.path.join(SRC, "tasks.py"))

tasks_settings.clear()
tasks_settings["tender_country"] = "Kenya"
kenya_result = tasks_mod._fetch_and_cache_tenders_on_control()
check("unpacked country: the eTenders direct fetcher returns None without a "
      "single network call", kenya_result is None)

tasks_settings.clear()  # unset -> default South Africa -> gate passes
try:
    tasks_mod._fetch_and_cache_tenders_on_control()
    reached_network = False
except RuntimeError:
    reached_network = True
check("default country: the fetcher passes the gate and proceeds to fetch "
      "(unchanged behavior)", reached_network)

check("tasks.py mirror of FIXTURE_PACK_COUNTRIES matches compliance/rules.py "
      "(canonical) exactly",
      tasks_mod.FIXTURE_PACK_COUNTRIES == rules_mod.FIXTURE_PACK_COUNTRIES
      and tasks_mod.DEFAULT_TENDER_COUNTRY == rules_mod.DEFAULT_TENDER_COUNTRY)

tcs_fields = {
    f["fieldname"]: f
    for f in json.loads(read(
        "tender/frappe/src/control/doctype/tender_control_settings/"
        "tender_control_settings.json"))["fields"]
}
tc = tcs_fields.get("tender_country")
check("tender_country still defaults to South Africa and now DOCUMENTS the "
      "fixture-pack scope it controls",
      tc is not None and tc.get("default") == "South Africa"
      and "fixture pack" in str(tc.get("description", "")).lower())

failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL HYGIENE CHECKS PASSED")
