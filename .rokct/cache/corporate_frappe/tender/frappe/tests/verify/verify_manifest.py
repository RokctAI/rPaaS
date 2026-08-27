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

"""Standalone manifest<->code agreement verification (assessment plan #6).

manifest.json maps the whitelist aliases (public, `control:`, and legacy
dotted names) to endpoint dotted paths BY HAND - the exact class of
silent-failure bug the bids.ts comment records already happened once
(unprefixed cmds "never existed on the gateway and failed silently").
Mirroring the forex SDK's manifest test, this suite asserts agreement in
BOTH directions, statically (ast - no imports, no frappe needed beyond the
suite family's conventions):

  forward:  every alias target resolves to a real module file, a real
            top-level function in it, decorated @frappe.whitelist;
  reverse:  every @frappe.whitelist function under src/control/api/ is the
            target of at least one alias - nothing whitelisted is
            unreachable through the gateway map.

Plus hook agreement: scheduler_events / doc_events / after_install targets
resolve to real functions too, and the hand-written JSON carries no
silently-swallowed duplicate alias keys.
"""

import ast
import json
import os
import sys

# O-05: in-tree suite runs must leave no __pycache__ litter under src/
sys.dont_write_bytecode = True

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
FRAPPE_PKG = os.path.join(REPO, "tender/frappe")
SRC = os.path.join(FRAPPE_PKG, "src")

checks = []


def check(label, ok):
    checks.append((label, bool(ok)))
    print(("PASS " if ok else "FAIL ") + label)


# ---- load the manifest, refusing duplicate keys anywhere ------------------
DUPES = []


def dupe_guard(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            DUPES.append(key)
        seen[key] = value
    return seen


with open(os.path.join(FRAPPE_PKG, "manifest.json"), encoding="utf-8") as f:
    manifest = json.load(f, object_pairs_hook=dupe_guard)

hooks = manifest["app_type"]["control"]["hooks"]
ALIASES = hooks["whitelisted_methods"]

check("manifest JSON carries no duplicate keys (a duplicate alias would be "
      "silently swallowed)", DUPES == [])
# 66 at the 2026-08-24 assessment; the plan-#58 wave adds get_award_ledger
# (plan #12) and get_compliance_calendar (plan #13) to all three cmd
# families: 66 + 6 = 72 aliases over 22 + 2 = 24 endpoints.
check("72 whitelist aliases mapped", len(ALIASES) == 72)


# ---- static module index: top-level functions + whitelist decoration ------
def module_functions(relpath):
    """{function_name: is_frappe_whitelisted} for a module's top level."""
    with open(os.path.join(SRC, relpath), encoding="utf-8") as fh:
        # endpoint shims carry the composer's literal {app_name} placeholder
        # in imports; substitute so ast can parse the REAL file content.
        tree = ast.parse(fh.read().replace("{app_name}", "composed_app"))
    out = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            whitelisted = False
            for deco in node.decorator_list:
                target = deco.func if isinstance(deco, ast.Call) else deco
                if (isinstance(target, ast.Attribute) and target.attr == "whitelist"
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "frappe"):
                    whitelisted = True
            out[node.name] = whitelisted
    return out


def resolve_target(dotted):
    """(module_relpath, function_name) for a '{app_name}.tender....' target,
    or (None, None) when the module file does not exist."""
    parts = dotted.split(".")
    if parts[0] != "{app_name}" or parts[1] != "tender":
        return (None, None)
    relpath = os.path.join(*parts[2:-1]) + ".py"
    if not os.path.exists(os.path.join(SRC, relpath)):
        return (None, None)
    return (relpath, parts[-1])


print("== forward: every alias target exists in code and is whitelisted ==")
module_cache = {}
bad_module, bad_function, bad_whitelist = [], [], []
target_files, target_functions = set(), set()
for alias, dotted in ALIASES.items():
    relpath, func = resolve_target(dotted)
    if relpath is None:
        bad_module.append((alias, dotted))
        continue
    if relpath not in module_cache:
        module_cache[relpath] = module_functions(relpath)
    if func not in module_cache[relpath]:
        bad_function.append((alias, dotted))
        continue
    if not module_cache[relpath][func]:
        bad_whitelist.append((alias, dotted))
    target_files.add(relpath)
    target_functions.add((relpath, func))

check("every alias target resolves to an existing module under src/", bad_module == [])
check("every alias target names a real top-level function in its module",
      bad_function == [])
check("every alias target function is @frappe.whitelist decorated",
      bad_whitelist == [])
check("aliases fan in to exactly 24 endpoint functions in 24 module files",
      len(target_functions) == 24 and len(target_files) == 24)
check("all three alias families point INTO the map (public {app_name}.api.tenders.*, "
      "control:*, legacy control.control.api.*)",
      any(a.startswith("{app_name}.api.tenders.") for a in ALIASES)
      and any(a.startswith("control:") for a in ALIASES)
      and any(a.startswith("control.control.api.") for a in ALIASES))

print("== reverse: every whitelisted api function is reachable through an alias ==")
whitelisted_in_code = set()
api_root = os.path.join(SRC, "control", "api")
for root, _dirs, files in os.walk(api_root):
    for name in sorted(files):
        if not name.endswith(".py"):
            continue
        relpath = os.path.relpath(os.path.join(root, name), SRC)
        if relpath not in module_cache:
            module_cache[relpath] = module_functions(relpath)
        for func, is_whitelisted in module_cache[relpath].items():
            if is_whitelisted:
                whitelisted_in_code.add((relpath, func))

unmapped = sorted(whitelisted_in_code - target_functions)
phantom = sorted(target_functions - whitelisted_in_code)
if unmapped:
    print("   UNMAPPED (whitelisted but no alias):", unmapped)
if phantom:
    print("   PHANTOM (aliased but not found whitelisted):", phantom)
check("every @frappe.whitelist function under src/control/api/ is the target "
      "of at least one alias", unmapped == [])
check("no alias points at a function that is not @frappe.whitelist in code "
      "(sets agree in BOTH directions)", phantom == [] and
      whitelisted_in_code == target_functions)

print("== hooks: scheduler / doc_events / after_install targets exist ==")
hook_targets = list(hooks.get("after_install", []))
for jobs in hooks.get("scheduler_events", {}).values():
    hook_targets.extend(jobs)
for doc_hooks in hooks.get("doc_events", {}).values():
    hook_targets.extend(doc_hooks.values())
bad_hooks = []
for dotted in hook_targets:
    relpath, func = resolve_target(dotted)
    if relpath is None:
        bad_hooks.append(dotted)
        continue
    if relpath not in module_cache:
        module_cache[relpath] = module_functions(relpath)
    if func not in module_cache[relpath]:
        bad_hooks.append(dotted)
if bad_hooks:
    print("   BAD HOOK TARGETS:", bad_hooks)
check("all scheduler_events / doc_events / after_install targets resolve to "
      "real functions", bad_hooks == [] and len(hook_targets) >= 6)

failed = [label for label, ok in checks if not ok]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL MANIFEST CHECKS PASSED")
