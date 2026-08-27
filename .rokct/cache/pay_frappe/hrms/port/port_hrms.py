#!/usr/bin/env python3
# Copyright (c) 2026 RokctAI
# License: GPL-3.0. This script is part of the `hrms/` GPLv3 subtree (see
# hrms/LICENSE); it transforms GPLv3 Frappe HR sources and is licensed
# GPL-3.0 to keep the subtree license-uniform.
"""
port_hrms.py — deterministic, re-runnable port of Frappe HR (frappe/hrms)
into the `hrms` frappe SDK module (erp/port_erpnext.py precedent, composed
by the-rokct-protocol's core/utils/frappe/compose_backend.py).

SOURCE:  a checkout of Frappenize/hrms @ rokct-hotfix
         (= stock upstream frappe/hrms version-16-hotfix tip,
         commit 6985c687d — carries the employee_leave_balance report
         permission fix and other fixes not yet released on the
         tag-bearing version-16 branch; see SOURCE_COMMIT below).
ERP:     the generated erp SDK tree (erp/frappe/, produced by
         erp/port/port_erpnext.py) — the mapping TARGET for every
         cross-app `erpnext.*` reference. Defaults to the sibling
         ../../erp/frappe of this script; override with --erp-tree.
DEST:    <host repo>/hrms/frappe/  (this script lives at
         <host repo>/hrms/port/).

Run:     python3 hrms/port/port_hrms.py [--source /workspace/hrms]
                                        [--erp-tree <path>/erp/frappe]

The whole transformation is done here, never by hand-editing ported files:
to change the port, change this script and re-run it. The script wipes and
regenerates hrms/frappe/doctype/, hrms/frappe/src/ and
hrms/frappe/manifest.json on every run and emits a machine-readable summary
to hrms/port/port_report.json.

=========================== LAYOUT DECISION ===========================

The composer's model is: one SDK module == one Frappe module ("Module Def").
compose_module() copies <sdk>/doctype/* to <app>/<module>/doctype/*, rewrites
every primary DocType JSON "module" to the manifest name, and copies
<sdk>/src/* to <app>/<module>/* (with src/www and src/patches redirected
app-level). Frappe resolves a doctype's disk path as
    get_module_path(doc.module) / "doctype" / scrub(doctype_name)
so with module == "hrms" every doctype MUST live at
<app>/hrms/doctype/<dt>/.

Frappe HR has 2 upstream Frappe modules (HR: 117 doctypes, Payroll: 43
doctypes) and 160 doctypes. Exactly like the erp port, they flatten into
the single "hrms" module — ZERO composer changes needed:

  hrms/frappe/doctype/<dt_snake>/         all 160 doctypes, upstream doctype
                                          NAMES kept verbatim (callers
                                          resolve by doctype name). Verified
                                          collision-free against every other
                                          fleet module's doctype dirs
                                          (erp's 501 included — the Employee
                                          family lives in erp's setup
                                          module and hrms only REFERENCES
                                          it) at port time: vs the erp tree
                                          by this script (hard error), vs
                                          the wider fleet in the 2026-08-19
                                          port review.
  hrms/frappe/src/<artifact>/<name>/      module-owned record/code artifacts
                                          frappe locates via the SAME
                                          get_module_path(module)/<artifact>/
                                          rule (report, page, print_format,
                                          workspace, notification, web_form,
                                          dashboard_chart, number_card, ...):
                                          also flattened, collision-checked.
  hrms/frappe/src/hrms_dashboard/         frappe's dashboard sync reads
                                          <module>/<module>_dashboard/ — the
                                          upstream hr_dashboard and
                                          payroll_dashboard dirs merge here.
  hrms/frappe/src/<upstream_module>/      everything else in a module dir
                                          (hr/utils.py, payroll/utils.py,
                                          payroll/data/, ...) keeps its
                                          upstream package structure, so
                                          `hrms.hr.utils` maps 1:1 to
                                          `{app_name}.hrms.hr.utils`.
  hrms/frappe/src/<top-level>/            top-level packages (api/, config/,
                                          controllers/, mixins/, overrides/,
                                          regional/, templates/, tests/,
                                          utils/, public/, ...) keep their
                                          upstream package structure.
  hrms/frappe/src/patches_post_install/   hrms/patches/post_install/* — the
                                          ONLY patches subtree ported.
                                          Unlike erp (whose patches are pure
                                          migration history), hrms's
                                          after_install runs these on EVERY
                                          install via
                                          run_post_install_patches(), so a
                                          fresh composed site needs them.
                                          They cannot live at src/patches/
                                          (the composer redirects that
                                          app-level, flat), hence the
                                          renamed package; setup.py's
                                          f-string patch runner is re-pointed
                                          by SETUP_REMAPS. patches/v*/ and
                                          patches.txt (migration history for
                                          pre-existing hrms DBs) stay
                                          excluded, erp-precedent.
  hrms/frappe/src/hrms_init.py            hrms/__init__.py's content (the
                                          composer overwrites the composed
                                          module's __init__.py with a stub,
                                          so package-level API —
                                          allow_regional, get_region,
                                          refetch_resource — must live in a
                                          named submodule). `import hrms` is
                                          rewritten to `from {app_name}.hrms
                                          import hrms_init as hrms`.

Import/dotted-path rewrite (applied to .py code, and to string literals in
.py/.js/.json/.html — the composer substitutes {app_name} in all of these,
in both doctype/ and src/ trees):
  hrms.<mod>.doctype.<dt>...      -> {app_name}.hrms.doctype.<dt>...
  hrms.<mod>.<artifact>.<x>...    -> {app_name}.hrms.<artifact>.<x>...
                                     (only when <x> was actually flattened)
  hrms.<anything else known>      -> {app_name}.hrms.<same path>
  hrms.<pkg __init__ attr>        -> {app_name}.hrms.hrms_init.<attr>
                                     (string literals only; code references
                                     resolve through the import alias)
  erpnext.*                       -> resolved against the GENERATED erp SDK
                                     tree (erp module precedent — hrms
                                     depends on ERPNext the way erp's own
                                     doctype files depend on the excluded
                                     crm module, so the same structural
                                     token rewrite is used, in both trees):
    erpnext.crm.<x>...            -> {app_name}.crm.<x>... (the crm module
                                     is excluded from erp and owned by the
                                     merged crm SDK module, productivity
                                     repo — mirror of port_erpnext.py's
                                     EXCLUDE_MODULES remap)
    erpnext.<mod>.doctype.<dt>... -> {app_name}.erp.doctype.<dt>...
                                     (dt verified in erp/frappe/doctype/)
    erpnext.<mod>.<artifact>.<x>  -> {app_name}.erp.<artifact>.<x> (verified
                                     in erp/frappe/src/<artifact>/<x>/)
    erpnext.<known top>...        -> {app_name}.erp.<same path> (verified
                                     against erp/frappe/src/ entries)
    erpnext.<pkg __init__ attr>   -> {app_name}.erp.erp_init.<attr>
                                     (string literals only; code refs via
                                     the rewritten `import erpnext` alias
                                     `from {app_name}.erp import erp_init
                                     as erpnext`)
  frappe.* / third-party imports  -> untouched
In .js/.json/.html only string literals (server-side dotted paths, e.g.
frappe.call methods) are rewritten; unquoted `hrms.*`/`erpnext.*` in JS is
the CLIENT-side JS namespace and is left alone.

A shell composing hrms MUST also compose erp (hrms's erpnext dependency is
pervasive and unguarded upstream — `required_apps = ["frappe/erpnext"]` —
so unlike the gateways<->erp seam there is no graceful degradation to
port); the manifest carries no machinery to express that, so it is
enforced socially + by import errors at compose time. The "lending" app
integration keeps upstream's graceful `frappe.get_installed_apps()` checks
verbatim (no lending SDK module exists in the fleet yet).

NOT PORTED (nothing is dropped silently — every category below is also
emitted into port_report.json):
  - locale/           (translations; frappe loads them app-level only, the
                       composer has no app-level asset channel)
  - www/              (the hrms/roster PWA page hosts + jobs portal need
                       app-level www which the composer redirects flat; the
                       Vue PWA itself lives at repo-root frontend/ + roster/
                       in upstream and was never inside the python package)
  - patches/v*_0, patches/v1_0, patches.txt (upstream migration history for
                       pre-existing Frappe HR databases; a composed shell
                       starts fresh. patches/post_install/ IS ported — see
                       LAYOUT above.)
  - hooks.py (translated to manifest.json), modules.txt
  - hooks.py keys the composer cannot express — carried into
    port_report.json["hooks_unsupported"] verbatim, with dotted values
    pre-mapped.
  - install hooks (after_install, before_uninstall, after_migrate,
    after_app_install, before_app_uninstall, setup_wizard_complete) are
    deliberately NOT declared in the manifest: the composed shell scaffold
    defines `after_install` as a plain *string* and merge_hooks() appends
    manifest entries with list.append(), crashing the generated hooks.py at
    import (empirically confirmed in the erp port). Fresh sites run once:
      bench --site <site> execute <app>.hrms.install.after_install
    See port_report.json["install_hooks_not_declared"].

ROKCT FIXES carried into the port (ROKCT_FIXES below): Frappenize rokct's
postgres fix for patches/post_install/update_employee_advance_status.py
(original commit 74d81739875f3c6fec9368a77ff1ce50cf720067 by Rendani
Sinyage, preserved on Frappenize/hrms@rokct and archived at
rokct-archive-2026-03) — pypika integer-truthiness expressions are not
valid boolean SQL on postgres. Applied as exact-anchor remaps, erp
PAYMENTS_REMAPS-style, and ledgered in port_report.json["rokct_fixes"].
"""

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

# Pinned upstream provenance. The port is only reproducible against exactly
# this commit of Frappenize/hrms (branch `rokct-hotfix`); the script
# hard-errors if the --source checkout is at any other commit.
SOURCE_COMMIT = "6985c687d2633bac58f98fa430e0c2d314fcad07"
SOURCE_BRANCH = "rokct-hotfix"

HERE = Path(__file__).resolve().parent
DEST = HERE.parent / "frappe"

SUBSTITUTABLE = (".py", ".js", ".html", ".json")

# Module-dir artifact types frappe resolves via get_module_path(module)/<type>/
# and that are therefore flattened to src/<type>/ (composing to
# <app>/hrms/<type>/). Same lists as the erp port; only types that actually
# exist in a module dir matter. "report" and "page" flatten SUBDIRECTORIES
# only: loose helper modules under them keep their upstream package path
# under src/<mod>/<type>/.
ARTIFACT_SUBDIR_ONLY = ("report", "page")
ARTIFACT_FULL = (
    "print_format",
    "notification",
    "web_form",
    "web_template",
    "workspace",
    "onboarding_step",
    "module_onboarding",
    "form_tour",
    "dashboard_chart",
    "dashboard_chart_source",
    "number_card",
    "print_format_field_template",
    "financial_report_template",
)

# Top-level package entries excluded from the port (see module docstring).
# "patches" is handled specially: post_install/ is relocated to
# src/patches_post_install/, the rest is excluded.
EXCLUDE_TOP = {
    "locale",
    "www",
    "patches",
    "hooks.py",
    "modules.txt",
    "patches.txt",
}

MODULE_NAME = "hrms"  # the manifest "name" == composed Frappe Module Def
APP = "{app_name}"  # composer token, resolved at compose time

# erp artifact types recognized when mapping erpnext.<mod>.<artifact>.<x>
# dotted paths onto the generated erp tree (existence-checked there).
ERP_ARTIFACT_TYPES = frozenset(ARTIFACT_SUBDIR_ONLY + ARTIFACT_FULL)

# Frappe modules EXCLUDED from erp and owned by another composed SDK module;
# erpnext.<mod>.X maps 1:1 to {app_name}.<mod>.X (mirror of
# port_erpnext.py's EXCLUDE_MODULES — the merged crm SDK module and the
# excised projects/support modules, all productivity repo, compose at
# {app_name}/<mod>/ with the upstream layout).
ERP_EXCLUDED_MODULES = {"crm", "projects", "support"}

# ---------------------------------------------------------------------------
# Targeted exact-anchor remaps (erp PAYMENTS_REMAPS mechanics: keyed by path
# relative to the upstream package, applied AFTER the dotted rewrites, each
# `old` must occur exactly once and every listed file must be visited, or
# the port aborts — upstream drift surfaces loudly instead of silently
# shipping a stale remap).
#
# SETUP_REMAPS: setup.py's run_post_install_patches() resolves patches by
# f-string against `hrms.patches.post_install.` — the ported package is
# src/patches_post_install/ (the composer redirects src/patches app-level),
# so the runner is re-pointed. setup.py is a src-tree file, so it may carry
# the composer's {app_name} token (erp templates/pages/order.py precedent).
SETUP_REMAPS = {
    "setup.py": [
        (
            '\t\t\tfrappe.get_attr(f"hrms.patches.post_install.'
            '{patch_name}.execute")()\n',
            "\t\t\t# ROKCT: post-install patches are ported to the "
            "patches_post_install\n"
            "\t\t\t# package (the composer redirects src/patches "
            "app-level; see\n"
            "\t\t\t# port/port_hrms.py).\n"
            '\t\t\tfrappe.get_attr(f"{app_name}.hrms.'
            'patches_post_install.{patch_name}.execute")()\n',
        ),
    ],
}

# ROKCT_FIXES: Frappenize rokct fork fixes carried into the port (see module
# docstring). Same exact-anchor mechanics as SETUP_REMAPS.
ROKCT_FIXES = {
    "patches/post_install/update_employee_advance_status.py": [
        # fix(postgres): properly cast return_amount bounds to boolean —
        # bare pypika column truthiness compiles to non-boolean SQL on
        # postgres. Original: Frappenize/hrms commit 74d81739875f3c6fec93
        # 68a77ff1ce50cf720067 (Rendani Sinyage), archived on branch
        # rokct-archive-2026-03.
        (
            "\t\t\t& ((advance.return_amount) & (advance.paid_amount == "
            "advance.return_amount))\n",
            "\t\t\t# ROKCT fix(postgres): cast bounds to boolean "
            "(rokct commit 74d817398)\n"
            "\t\t\t& ((advance.return_amount > 0) & (advance.paid_amount "
            "== advance.return_amount))\n",
        ),
        (
            "\t\t\t\t(advance.claimed_amount & advance.return_amount)\n",
            "\t\t\t\t# ROKCT fix(postgres): cast bounds to boolean "
            "(rokct commit 74d817398)\n"
            "\t\t\t\t((advance.claimed_amount > 0) & "
            "(advance.return_amount > 0))\n",
        ),
    ],
}


def scrub(txt):
    return txt.replace(" ", "_").replace("-", "_").lower()


def read_text(p: Path) -> str:
    raw = p.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise SystemExit(f"[-] {p} is not valid UTF-8 ({e}); the composer "
                         f"would crash copying it. Fix the port script.")


def write_text(p: Path, content: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(content)


def init_attrs_of(init_py: Path):
    names = set()
    for m in re.finditer(r"^(?:def|class)\s+(\w+)|^(\w+)\s*=",
                         read_text(init_py), re.M):
        names.add(m.group(1) or m.group(2))
    return names


class ErpTree:
    """The generated erp SDK tree (erp/frappe/) as a mapping target for
    erpnext.* dotted paths — the same topology port_erpnext.py produced:
    flattened doctype/, flattened artifact dirs and module packages under
    src/, package API in src/erp_init.py."""

    def __init__(self, root: Path):
        self.root = root
        if not (root / "doctype").is_dir() or not (root / "src").is_dir():
            raise SystemExit(f"[-] {root} does not look like the generated "
                             f"erp SDK tree (need doctype/ and src/). Point "
                             f"--erp-tree at <pay repo>/erp/frappe.")
        self.doctypes = {p.name for p in (root / "doctype").iterdir()
                         if p.is_dir()}
        self.tops = set()
        for p in (root / "src").iterdir():
            if p.name == "erp_init.py":
                continue
            self.tops.add(p.name if p.is_dir() else p.stem)
        self.init_attrs = init_attrs_of(root / "src" / "erp_init.py")

    def map_dotted(self, t):
        """Map the tail of an 'erpnext.'-rooted dotted path (list of parts
        after 'erpnext') to its composed location.

        Returns (mapped, string_only) or (None, False) when unknown."""
        if not t:
            return None, False
        if t[0] in ERP_EXCLUDED_MODULES:
            return f"{APP}." + ".".join(t), False
        if len(t) >= 3 and t[1] == "doctype":
            if t[2] in self.doctypes:
                return f"{APP}.erp.doctype." + ".".join(t[2:]), False
            if (self.root / "src" / t[0] / "doctype" / f"{t[2]}.py").exists():
                return f"{APP}.erp." + ".".join(t), False
            return None, False
        if (len(t) >= 3 and t[1] in ERP_ARTIFACT_TYPES
                and (self.root / "src" / t[1] / t[2]).is_dir()):
            return f"{APP}.erp." + ".".join(t[1:]), False
        if t[0] in self.tops:
            return f"{APP}.erp." + ".".join(t), False
        if t[0] in self.init_attrs:
            return f"{APP}.erp.erp_init." + ".".join(t), True
        return None, False


class Porter:
    def __init__(self, source: Path, erp_tree: Path):
        self.source = source
        self.pkg = source / "hrms"
        if not (self.pkg / "hooks.py").exists():
            raise SystemExit(f"[-] {self.pkg} does not look like the "
                             f"frappe/hrms package (no hooks.py).")
        head = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            capture_output=True, text=True)
        head_sha = head.stdout.strip() if head.returncode == 0 else None
        if head_sha != SOURCE_COMMIT:
            raise SystemExit(
                f"[-] source checkout {source} is at {head_sha or 'unknown'},"
                f" but the port is pinned to Frappenize/hrms@{SOURCE_BRANCH} "
                f"commit {SOURCE_COMMIT}. Check out that commit and re-run.")
        self.erp = ErpTree(erp_tree)
        self.module_dirs = self._module_dirs()
        self.doctypes = self._doctype_dirs()
        self.moved_artifacts = {}  # artifact_type -> set(subdir names moved)
        erp_overlap = sorted(set(self.doctypes) & self.erp.doctypes)
        if erp_overlap:
            raise SystemExit(f"[-] hrms doctype dirs collide with erp's: "
                             f"{erp_overlap} — a composed app would "
                             f"double-define them. Resolve erp-crm-"
                             f"precedent-style before porting.")
        self.report = {
            "source": str(source),
            "source_commit": SOURCE_COMMIT,
            "source_branch": SOURCE_BRANCH,
            "erp_tree": str(erp_tree),
            "module_count": len(self.module_dirs),
            "doctype_count": len(self.doctypes),
            "excluded": sorted(EXCLUDE_TOP),
            "patches_post_install": [],
            "rokct_fixes": {},
            "hooks_supported": {},
            "hooks_unsupported": {},
            "install_hooks_not_declared": {},
            "unmapped_dotted_paths": [],
            "notes": [],
        }
        erp_head = subprocess.run(
            ["git", "-C", str(erp_tree), "rev-parse", "HEAD"],
            capture_output=True, text=True)
        if erp_head.returncode == 0:
            self.report["erp_tree_repo_commit"] = erp_head.stdout.strip()
        self.init_attrs = init_attrs_of(self.pkg / "__init__.py")
        self.unmapped = {}
        self.remaps = {}
        for table in (SETUP_REMAPS, ROKCT_FIXES):
            for rel, rules in table.items():
                self.remaps.setdefault(rel, []).extend(rules)
        self.remapped = set()  # remap keys actually applied

    # ------------------------------------------------------------------ scan
    def _module_dirs(self):
        mods = []
        for line in (self.pkg / "modules.txt").read_text().splitlines():
            line = line.strip()
            if line:
                d = scrub(line)
                if not (self.pkg / d).is_dir():
                    raise SystemExit(f"[-] modules.txt entry '{line}' has no "
                                     f"directory {d}/")
                mods.append(d)
        return mods

    def _doctype_dirs(self):
        seen = {}
        for mod in self._module_dirs():
            dt_root = self.pkg / mod / "doctype"
            if not dt_root.is_dir():
                continue
            for dt in sorted(p.name for p in dt_root.iterdir() if p.is_dir()):
                if dt in seen:
                    raise SystemExit(f"[-] doctype dir collision: {dt} in "
                                     f"both {seen[dt]} and {mod}")
                seen[dt] = mod
        return seen

    # ------------------------------------------------------- dotted rewriting
    def _known_top(self):
        # every python-importable top-level name that survives under src/
        # with its upstream name (module dirs + loose top-level packages
        # and modules). patches/ survives only as patches_post_install
        # (added explicitly — dotted refs to it are handled by
        # SETUP_REMAPS, but the name must be considered "known" so nothing
        # regressing to hrms.patches_post_install.* goes unmapped).
        tops = set(self.module_dirs)
        for p in self.pkg.iterdir():
            if p.name in EXCLUDE_TOP or p.name == "__init__.py":
                continue
            if p.is_dir():
                tops.add(p.name)
            elif p.suffix == ".py":
                tops.add(p.stem)
        tops.add("patches_post_install")
        return tops

    def map_hrms_dotted(self, t):
        """Map the tail of a 'hrms.'-rooted dotted path (list of parts after
        'hrms') to its composed location.

        Returns (mapped, string_only) or (None, False) when unknown."""
        if not t:
            return None, False
        if t[0] in self.module_dirs and len(t) >= 2:
            if t[1] == "doctype":
                if len(t) >= 3 and t[2] in self.doctypes:
                    return f"{APP}.hrms.doctype." + ".".join(t[2:]), False
                if len(t) >= 3 and (t[0], t[2]) in self.loose_doctype_files:
                    return f"{APP}.hrms." + ".".join(t), False
                return None, False
            if (t[1] in self.moved_artifacts and len(t) >= 3
                    and t[2] in self.moved_artifacts[t[1]]):
                return f"{APP}.hrms." + ".".join(t[1:]), False
        if t[0] in self.known_top:
            return f"{APP}.hrms." + ".".join(t), False
        if t[0] in self.init_attrs:
            return f"{APP}.hrms.hrms_init." + ".".join(t), True
        return None, False

    DOTTED_RE = re.compile(
        r"(?<![\w.])(hrms|erpnext)((?:\.[A-Za-z_][A-Za-z0-9_]*)+)")

    def map_dotted(self, full):
        root, tail = full.split(".", 1)
        t = tail.split(".")
        if root == "hrms":
            return self.map_hrms_dotted(t)
        return self.erp.map_dotted(t)

    def rewrite_text(self, content, rel, is_python):
        """Rewrite hrms/erpnext dotted paths. For python, import statements
        are handled structurally first; then all dotted occurrences are
        mapped (init-attr paths only inside string literals). For
        js/json/html only string literals (quote-preceded) are rewritten."""
        if is_python:
            content = self._rewrite_imports(content, rel)
            content = self._rewrite_special_calls(content)

        def sub(m):
            full = m.group(1) + m.group(2)
            start = m.start()
            prev = content[start - 1] if start else ""
            in_string_start = prev in "\"'"
            mapped, string_only = self.map_dotted(full)
            if mapped is None:
                # hrms.patches.post_install is re-pointed by SETUP_REMAPS
                # (applied after this pass); erpnext.com/org are URLs and
                # hrms.bundle.* are asset filenames.
                if not full.startswith(("erpnext.com", "erpnext.org",
                                        "hrms.bundle",
                                        "hrms.patches.post_install")):
                    self.unmapped.setdefault(full, set()).add(rel)
                return full
            if is_python:
                if string_only and not in_string_start:
                    return full  # code ref via the rewritten import alias
                return mapped
            # js / json / html: only rewrite whole-string server paths
            return mapped if in_string_start else full

        return self.DOTTED_RE.sub(sub, content)

    def _rewrite_imports(self, content, rel):
        out = []
        for line in content.split("\n"):
            m = re.match(r"^(\s*)import (hrms|erpnext)(\s*(#.*)?)?$", line)
            if m:
                pkg = m.group(2)
                mod = "hrms" if pkg == "hrms" else "erp"
                init = f"{mod}_init" if mod == "erp" else "hrms_init"
                out.append(f"{m.group(1)}from {APP}.{mod} import {init} as "
                           f"{pkg}{m.group(3) or ''}")
                continue
            m = re.match(r"^(\s*)from (hrms|erpnext) import (.+)$", line)
            if m:
                indent, pkg, names_s = m.group(1), m.group(2), m.group(3)
                if pkg == "hrms":
                    mod, tops, init = "hrms", self.known_top, "hrms_init"
                else:
                    mod, tops, init = "erp", self.erp.tops, "erp_init"
                names = [n.strip() for n in names_s.split(",")]
                top, initial = [], []
                for n in names:
                    base = n.split(" as ")[0].strip()
                    (top if base in tops else initial).append(n)
                lines = []
                if top:
                    lines.append(f"{indent}from {APP}.{mod} import "
                                 + ", ".join(top))
                if initial:
                    lines.append(f"{indent}from {APP}.{mod}.{init} import "
                                 + ", ".join(initial))
                out.extend(lines)
                continue
            out.append(line)
        return "\n".join(out)

    def _rewrite_special_calls(self, content):
        # frappe.get_app_path("hrms", ...) resolves against the composed
        # APP, whose hrms module content lives one level down; doctype trees
        # are additionally flattened out of their upstream module dir
        # (setup.py's setup_notifications reads doctype email templates).
        content = content.replace(
            'frappe.get_app_path("hrms", "hr", "doctype")',
            f'frappe.get_app_path("{APP}", "hrms", "doctype")')
        content = content.replace(
            'frappe.get_app_path("hrms"',
            f'frappe.get_app_path("{APP}", "hrms"')
        return content

    # --------------------------------------------------------------- copying
    MODULE_JSON_RE = None  # built in run()

    def copy_tree(self, src: Path, dst: Path, rewrite_module_field=False):
        if src.is_file():
            self.copy_file(src, dst, rewrite_module_field)
            return
        for item in sorted(src.rglob("*")):
            if item.is_file():
                self.copy_file(item, dst / item.relative_to(src),
                               rewrite_module_field)

    def copy_file(self, src: Path, dst: Path, rewrite_module_field=False):
        if dst.exists():
            raise SystemExit(f"[-] destination collision: {dst} (from {src})")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in SUBSTITUTABLE:
            rel = str(src.relative_to(self.pkg))
            content = self.rewrite_text(read_text(src), rel,
                                        src.suffix == ".py")
            content = self.apply_remaps(content, rel)
            if rewrite_module_field and src.suffix == ".json":
                content = self.MODULE_JSON_RE.sub(
                    '"module": "{module_name}"', content)
            write_text(dst, content)
        else:
            shutil.copy2(src, dst)

    def apply_remaps(self, content, rel):
        """Apply the SETUP_REMAPS/ROKCT_FIXES rules for one upstream-relative
        path. Anchors are exact-match, exactly-once."""
        for old, new in self.remaps.get(rel, ()):
            n = content.count(old)
            if n != 1:
                raise SystemExit(f"[-] remap anchor matched {n}x "
                                 f"(expected exactly 1) in {rel}:\n{old}")
            content = content.replace(old, new)
        if rel in self.remaps:
            self.remapped.add(rel)
        return content

    def _merge_duplicate_record(self, mod, src_dir: Path, dst_dir: Path):
        """Same-named artifact dirs exporting the SAME record merge (last
        module in modules.txt order wins — erp precedent); same-named dirs
        holding *different* records are a hard error."""
        primary = src_dir / f"{src_dir.name}.json"
        existing = dst_dir / f"{dst_dir.name}.json"
        if not (primary.exists() and existing.exists()):
            raise SystemExit(f"[-] duplicate artifact dir without primary "
                             f"JSON: {src_dir} vs {dst_dir}")
        new_name = json.loads(read_text(primary)).get("name")
        old_name = json.loads(read_text(existing)).get("name")
        if new_name != old_name:
            raise SystemExit(f"[-] artifact dir name collision with "
                             f"DIFFERENT records: {src_dir} ({new_name!r}) "
                             f"vs existing ({old_name!r})")
        shutil.rmtree(dst_dir)
        self.copy_tree(src_dir, dst_dir, rewrite_module_field=True)
        self.report.setdefault("merged_duplicates", []).append(
            f"{src_dir.relative_to(self.pkg)} replaced earlier same-named "
            f"record {new_name!r} (modules.txt order, last wins)")

    # ------------------------------------------------------------------- run
    def run(self):
        self.known_top = self._known_top()
        self.loose_doctype_files = {
            (mod, f.stem)
            for mod in self.module_dirs
            if (self.pkg / mod / "doctype").is_dir()
            for f in (self.pkg / mod / "doctype").iterdir()
            if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"}
        module_labels = [line.strip() for line
                         in (self.pkg / "modules.txt").read_text().splitlines()
                         if line.strip()]
        self.MODULE_JSON_RE = re.compile(
            r'"module":\s*"(?:' + "|".join(re.escape(x) for x in module_labels)
            + r')"')

        # wipe generated output (manifest.json, doctype/, src/) — the port is
        # regenerated wholesale on every run.
        for target in (DEST / "doctype", DEST / "src"):
            if target.exists():
                shutil.rmtree(target)
        (DEST / "doctype").mkdir(parents=True)
        (DEST / "src").mkdir(parents=True)

        # pre-compute which artifact subdirs move, so the dotted-path mapper
        # knows them before any file content is rewritten.
        for art in ARTIFACT_SUBDIR_ONLY + ARTIFACT_FULL:
            moved = set()
            for mod in self.module_dirs:
                d = self.pkg / mod / art
                if d.is_dir():
                    moved |= {p.name for p in d.iterdir() if p.is_dir()}
            if moved:
                self.moved_artifacts[art] = moved

        # 1. module dirs
        for mod in self.module_dirs:
            mod_dir = self.pkg / mod
            for entry in sorted(mod_dir.iterdir()):
                name = entry.name
                if name == "doctype":
                    for dt in sorted(entry.iterdir()):
                        if dt.is_dir():
                            if not (dt / f"{dt.name}.json").exists():
                                self.report.setdefault(
                                    "skipped_doctype_stubs", []).append(
                                    str(dt.relative_to(self.pkg)))
                                continue
                            self.copy_tree(dt, DEST / "doctype" / dt.name,
                                           rewrite_module_field=True)
                        elif dt.name != "__init__.py":
                            # loose module-level helper. The composer only
                            # copies DIRS out of an SDK's doctype/, so these
                            # keep their upstream package path under src/.
                            self.copy_file(
                                dt, DEST / "src" / mod / "doctype" / dt.name)
                    continue
                if name in ARTIFACT_SUBDIR_ONLY:
                    for sub in sorted(entry.iterdir()):
                        if sub.is_dir():
                            self.copy_tree(sub, DEST / "src" / name / sub.name,
                                           rewrite_module_field=True)
                        else:
                            self.copy_file(
                                sub, DEST / "src" / mod / name / sub.name)
                    continue
                if name in ARTIFACT_FULL:
                    for sub in sorted(entry.iterdir()):
                        if sub.name == "__init__.py":
                            continue
                        dst = DEST / "src" / name / sub.name
                        if sub.is_dir() and dst.exists():
                            self._merge_duplicate_record(mod, sub, dst)
                            continue
                        self.copy_tree(sub, dst, rewrite_module_field=True)
                    continue
                if name.endswith("_dashboard") and entry.is_dir():
                    for sub in sorted(entry.iterdir()):
                        if sub.name == "__init__.py":
                            continue
                        self.copy_tree(
                            sub, DEST / "src" / "hrms_dashboard" / sub.name,
                            rewrite_module_field=True)
                    continue
                self.copy_tree(entry, DEST / "src" / mod / name)

        # 2. top-level package entries
        for entry in sorted(self.pkg.iterdir()):
            name = entry.name
            if name in EXCLUDE_TOP or name in self.module_dirs:
                continue
            if name == "__init__.py":
                self.copy_file(entry, DEST / "src" / "hrms_init.py")
                continue
            self.copy_tree(entry, DEST / "src" / name)

        # 2b. patches/post_install -> src/patches_post_install (see LAYOUT):
        # after_install's run_post_install_patches() needs these on every
        # fresh composed site; setup.py's runner is re-pointed by
        # SETUP_REMAPS. The rest of patches/ stays excluded.
        post = self.pkg / "patches" / "post_install"
        self.copy_tree(post, DEST / "src" / "patches_post_install")
        self.report["patches_post_install"] = sorted(
            p.name for p in post.iterdir() if p.suffix == ".py")
        self.report["notes"].append(
            "patches_post_install: hrms/patches/post_install/* ported as "
            "src/patches_post_install/ (the composer redirects src/patches "
            "app-level, flat) because after_install runs them on every "
            "install; setup.py's f-string patch runner is re-pointed by "
            "SETUP_REMAPS. patches/v*/ and patches.txt (migration history "
            "for pre-existing Frappe HR DBs) are excluded, erp-precedent.")

        # 3. manifest.json from hooks.py
        manifest = self.build_manifest()
        write_text(DEST / "manifest.json",
                   json.dumps(manifest, indent=2) + "\n")

        # 4. static subtree files
        self.write_static()

        # 5. post-port lint: code that calls a package-level helper through
        # the bare `hrms`/`erpnext` name (hrms.refetch_resource(...),
        # erpnext.get_company_currency(...)) only works when the file holds
        # the rewritten alias import. Anything else still spelling
        # `<pkg>.<known attr>` in code is a porting bug.
        alias_missing = []
        checks = (
            ("hrms", self.init_attrs),
            ("erpnext", self.erp.init_attrs),
        )
        attr_res = [
            (pkg, re.compile(
                r"(?<![\w.\"'])" + pkg + r"\.(?:"
                + "|".join(re.escape(a) for a in sorted(attrs)) + r")\b"))
            for pkg, attrs in checks]
        for py in list((DEST / "src").rglob("*.py")) + list(
                (DEST / "doctype").rglob("*.py")):
            if py == DEST / "src" / "hrms_init.py":
                continue  # its own docstrings show `@hrms.allow_regional`
            c = read_text(py)
            for pkg, attr_re in attr_res:
                if attr_re.search(c) and f"as {pkg}" not in c:
                    alias_missing.append(f"{py.relative_to(DEST)} ({pkg})")
        if alias_missing:
            raise SystemExit("[-] files reference a bare package attr "
                             "without the init alias import:\n  "
                             + "\n  ".join(sorted(alias_missing)))

        # 6. verify every remap file was visited, then ledger them.
        missed = sorted(set(self.remaps) - self.remapped)
        if missed:
            raise SystemExit("[-] remap entries never applied (upstream "
                             "file moved/renamed?):\n  " + "\n  ".join(missed))
        self.report["setup_remaps"] = {
            rel: len(rules) for rel, rules in sorted(SETUP_REMAPS.items())}
        self.report["rokct_fixes"] = {
            rel: {
                "rules": len(rules),
                "origin": "Frappenize/hrms@rokct commit 74d81739875f3c6fec9"
                          "368a77ff1ce50cf720067 (fix(postgres): properly "
                          "cast return_amount bounds to boolean), archived "
                          "on branch rokct-archive-2026-03",
            } for rel, rules in sorted(ROKCT_FIXES.items())}

        self.report["doctype_count"] = (
            len(self.doctypes)
            - len(self.report.get("skipped_doctype_stubs", [])))
        self.report["doctypes"] = sorted(
            set(self.doctypes)
            - {Path(s).name for s
               in self.report.get("skipped_doctype_stubs", [])})
        self.report["unmapped_dotted_paths"] = sorted(self.unmapped)
        self.report["unmapped_detail"] = {
            p: sorted(files)[:5] for p, files in sorted(self.unmapped.items())}
        self.report["notes"].append(
            "unmapped erpnext.patches.* entries are EXPECTED: setup.py's "
            "get_post_install_patches() lists historical patch NAMES whose "
            "basenames alone are resolved (against the ported "
            "patches_post_install package) — the erpnext-rooted spellings "
            "are inert site-history labels, kept verbatim.")
        self.report["notes"].append(
            "hrms composes only alongside erp: upstream requires the "
            "erpnext app (required_apps) and imports it unguarded, so "
            "there is no graceful no-erp degradation to port. The "
            "'lending' app checks stay verbatim upstream behavior "
            "(graceful skip — no lending SDK module exists in the fleet).")
        self.report["notes"].append(
            "js string literals that spell a mappable dotted path are "
            "rewritten even when they name a CLIENT-side JS namespace "
            "(e.g. frappe.provide(\"erpnext.accounts.dimensions\") -> "
            "frappe.provide(\"{app_name}.erp.accounts.dimensions\")) — "
            "byte-for-byte the erp port's own behavior (see the erp "
            "tree's doctype/asset/asset.js). Unquoted client-namespace "
            "js refs (hrms.HierarchyChart, erpnext.utils.*, ...) are left "
            "alone and appear in unmapped_dotted_paths; they resolve "
            "against the bundled JS assets, which compose inert for now "
            "(same erp-port limitation).")
        self.report["notes"].append(
            "src/templates/, src/public/ and the workspace_sidebar/, "
            "desktop_icon/ data dirs compose under the module dir, but "
            "frappe serves web templates, portal pages and public assets "
            "from app-level paths only — like the erp port they are "
            "carried python-importable/data-complete but inert as web "
            "pages/assets until the composer grows an app-level channel. "
            "The hrms/roster PWA (repo-root frontend/ + roster/ Vue apps, "
            "served via the excluded www/ pages) is NOT part of the python "
            "package and is not ported.")
        write_text(HERE / "port_report.json",
                   json.dumps(self.report, indent=2, sort_keys=True) + "\n")
        n_files = sum(1 for p in DEST.rglob("*") if p.is_file())
        print(f"[+] Ported {self.report['doctype_count']} doctypes from "
              f"{self.report['module_count']} upstream modules; "
              f"{n_files} files under hrms/frappe/.")
        if self.unmapped:
            print(f"[!] {len(self.unmapped)} unmapped dotted paths left "
                  f"verbatim (see port_report.json).")

    # -------------------------------------------------------------- manifest
    def build_manifest(self):
        hooks_ns = {}
        exec(compile(read_text(self.pkg / "hooks.py"), "hooks.py", "exec"),
             hooks_ns)
        hooks_ns.pop("__builtins__", None)

        def map_str(v, strict=True):
            if isinstance(v, str) and v.startswith(("hrms.", "erpnext.")):
                mapped, _ = self.map_dotted(v)
                if mapped is None:
                    if strict:
                        raise SystemExit(f"[-] cannot map hook value {v}")
                    return v  # e.g. asset filenames like hrms.bundle.js
                return mapped
            return v

        def map_val(v):
            # best-effort mapping for the UNSUPPORTED-hooks report only
            if isinstance(v, str):
                return map_str(v, strict=False)
            if isinstance(v, list):
                return [map_val(x) for x in v]
            if isinstance(v, dict):
                return {str(k): map_val(x) for k, x in v.items()}
            return v

        supported = {}

        # doc_events — expand tuple keys, merge per doctype. Handlers that
        # live in erp (e.g. validate_employee_role) stay declared here:
        # hrms's manifest hooks them, erp's code serves them — the composer
        # merges doc_events additively across modules.
        doc_events = {}
        for key, evts in hooks_ns.get("doc_events", {}).items():
            keys = key if isinstance(key, tuple) else (key,)
            for k in keys:
                bucket = doc_events.setdefault(k, {})
                for evt, handlers in evts.items():
                    hl = [handlers] if isinstance(handlers, str) else list(handlers)
                    merged = bucket.setdefault(evt, [])
                    for h in hl:
                        h = map_str(h)
                        if h not in merged:
                            merged.append(h)
        supported["doc_events"] = doc_events

        # scheduler_events — keep cron dict buckets, drop empty lists.
        sched = {}
        for bucket, tasks in hooks_ns.get("scheduler_events", {}).items():
            if isinstance(tasks, dict):
                cron = {expr: [map_str(t) for t in jobs]
                        for expr, jobs in tasks.items() if jobs}
                if cron:
                    sched[bucket] = cron
            elif tasks:
                sched[bucket] = [map_str(t) for t in tasks]
        supported["scheduler_events"] = sched

        # upstream override_whitelisted_methods -> manifest
        # whitelisted_methods (none upstream today; carried structurally so
        # a re-run against a future source that adds them keeps working).
        owm = {k: map_str(v) for k, v in
               hooks_ns.get("override_whitelisted_methods", {}).items()}
        supported["whitelisted_methods"] = owm

        # Install/lifecycle hooks are deliberately NOT declared (see module
        # docstring: composer merge_hooks() appends to the shell scaffold's
        # after_install *string* and crashes hooks.py at import — erp
        # precedent). Recorded here so nothing is silently dropped.
        for k in ("before_install", "after_install", "before_uninstall",
                  "after_uninstall", "after_migrate", "after_app_install",
                  "before_app_uninstall", "setup_wizard_complete"):
            if k in hooks_ns:
                self.report["install_hooks_not_declared"][k] = map_str(
                    hooks_ns[k])
        self.report["notes"].append(
            "install/lifecycle hooks NOT declared in manifest (composer "
            "merge_hooks() after_install string-append bug, erp precedent). "
            "Run `bench --site <site> execute "
            "{app}.hrms.install.after_install` once per fresh site — it "
            "creates the HR custom fields on erp doctypes, fixtures, "
            "role profiles and runs the ported post-install patches; "
            "{app}.hrms.uninstall.before_uninstall removes the "
            "customizations. after_migrate "
            "({app}.hrms.setup.update_select_perm_after_install) and the "
            "lending-app integration hooks (after_app_install/"
            "before_app_uninstall) are likewise manual until the composer "
            "supports them.")

        # composer-supported keys actually used
        self.report["hooks_supported"] = {
            "doc_events": f"{len(doc_events)} doctype keys",
            "scheduler_events": {k: (len(v) if isinstance(v, list) else
                                     {e: len(j) for e, j in v.items()})
                                 for k, v in sched.items()},
            "whitelisted_methods": list(owm),
        }

        # everything else in hooks.py the composer cannot express.
        composer_keys = {
            "doc_events", "scheduler_events", "override_whitelisted_methods",
            "override_doctype_class", "fixtures", "auth_hooks",
            "before_install", "after_install", "before_uninstall",
            "after_uninstall", "after_migrate", "after_app_install",
            "before_app_uninstall", "setup_wizard_complete", "commands",
        }
        unsupported = {}
        for k, v in sorted(hooks_ns.items()):
            if k in composer_keys or k.startswith("_"):
                continue
            if callable(v):
                continue
            unsupported[k] = map_val(v) if isinstance(v, (str, list, dict)) else str(v)
        self.report["hooks_unsupported"] = unsupported
        # override_doctype_class is composer-supported per the erp/gateways
        # precedent's composer_keys, but hrms is the first port to USE it —
        # carry it in the report too so the landing review wires or
        # hand-writes it deliberately rather than finding it missing.
        self.report["hooks_unsupported"]["override_doctype_class"] = map_val(
            hooks_ns.get("override_doctype_class", {}))
        self.report["notes"].append(
            "hooks_unsupported keys are NOT wired by the composer; a shell "
            "can hand-write any of them above its hooks.py fence. Their "
            "dotted values are pre-mapped to composed paths here for that "
            "purpose. LOAD-BEARING ones for HR correctness: "
            "override_doctype_class (EmployeeMaster/EmployeeTimesheet/"
            "EmployeePaymentEntry/EmployeeProject extend erp doctype "
            "classes), doctype_js (HR buttons on Employee/Company/... "
            "forms), regional_overrides (India payroll), "
            "has_upload_permission, override_doctype_dashboards, jinja "
            "methods, period_closing/accounting_dimension/"
            "bank_reconciliation/advance_payment_payable/invoice doctype "
            "registrations consumed by erp, and website_route_rules/"
            "website_generators for the excluded www/portal surfaces.")

        # python dependencies from upstream pyproject.toml ([project] has
        # none today; bench frappe-dependencies recorded separately).
        deps = []
        pyproject = read_text(self.source / "pyproject.toml")
        m = re.search(r"^dependencies\s*=\s*\[(.*?)\]", pyproject,
                      re.S | re.M)
        if m:
            deps = re.findall(r'"([^"]+)"', m.group(1))
        self.report["dependencies"] = deps
        m = re.search(r"\[tool\.bench\.frappe-dependencies\](.*?)(\n\[|\Z)",
                      pyproject, re.S)
        if m:
            self.report["frappe_dependencies"] = {
                k.strip(): v.strip().strip('"') for k, v in
                (line.split("=", 1) for line in m.group(1).splitlines()
                 if "=" in line)}

        return {
            "name": MODULE_NAME,
            "description": (
                "Modular SDK for HR & Payroll: Frappe HR port (employee "
                "lifecycle, leaves, attendance, shifts, recruitment, "
                "appraisals, expense claims, salary structures, payroll "
                "entry and more) flattened into a single composed frappe "
                "module. Composes ONLY alongside the erp module — the "
                "Employee master and accounting doctypes live in erp, and "
                "every upstream erpnext reference resolves to "
                "{app_name}.erp (or {app_name}.crm for the excluded crm "
                "module). Fork of frappe/hrms (GPL-3.0) via "
                "Frappenize/hrms@rokct-hotfix."),
            "dependencies": deps,
            "hooks": {
                "doc_events": supported["doc_events"],
                "scheduler_events": supported["scheduler_events"],
                "whitelisted_methods": supported["whitelisted_methods"],
            },
        }

    # ---------------------------------------------------------------- static
    def write_static(self):
        shutil.copy2(self.source / "license.txt", HERE.parent / "LICENSE")
        write_text(HERE.parent / "README.md", README)
        erp_gitignore = self.erp.root / ".gitignore"
        write_text(DEST / ".gitignore",
                   erp_gitignore.read_text() if erp_gitignore.exists()
                   else GITIGNORE_FALLBACK)
        for stack in ("dart", "nextjs"):
            write_text(HERE.parent / stack / ".gitignore",
                       "# placeholder — no {} SDK for hrms yet\n"
                       .format(stack))


README = """\
# hrms — Frappe HR as a composable frappe SDK module

**Provenance:** fork of [frappe/hrms](https://github.com/frappe/hrms)
at the **version-16-hotfix** tip (commit `6985c687d`), taken via
`Frappenize/hrms@rokct-hotfix`. Upstream tags releases on `version-16`
only; this hotfix tip carries fixes not yet in any tagged release —
notably the employee_leave_balance report permission fix (restrict the
report to permitted employees) — and does not descend from the tag
lineage, hence the dedicated `rokct-hotfix` branch (erp precedent). When
upstream cuts the next release containing these fixes, the port returns
to tag-tracking via `rokct`.

**License: GPL-3.0** (see [LICENSE](LICENSE), copied verbatim from upstream
`license.txt`). Every ported file keeps its upstream copyright/license
header verbatim; nothing is re-stamped. This subtree is intentionally
excluded from the repo's MIT header check (`.licenserc.yaml`), same as
`erp/**`.

The `frappe/` tree is generated by `port/port_hrms.py` — a deterministic,
re-runnable transform of the upstream source. Do not hand-edit ported
files; change the script and re-run it. See the script's docstring for the
full layout rationale and `port/port_report.json` for what was and wasn't
carried. Upstream's two Frappe modules (**HR** and **Payroll**, 160
doctypes) flatten into this single `hrms` module, erp-precedent style.

**hrms composes ONLY alongside `erp`** (upstream declares
`required_apps = ["frappe/erpnext"]` and imports erpnext unguarded): the
Employee master and its family (department, designation, branch,
holiday_list, ...) live in erp's tree, and the port rewrites every
`erpnext.*` reference against the generated erp SDK tree —
`{app_name}.erp.doctype.employee.employee`,
`{app_name}.erp.accounts.utils`, `{app_name}.erp.erp_init` for the
package-level API, and `{app_name}.crm.*` for erp's excluded crm module.
The hrms doctype dir names were verified collision-free against erp's 501
and every other fleet module's at port time (checked against the erp tree
on every run — hard error).

A site composing `hrms` must NOT also have the upstream `hrms` app
installed — doctype names are kept verbatim, so the two would
double-define every doctype (erp/crm-precedent exclusivity rule).

**Install hooks:** upstream's `after_install` (HR custom fields on erp
doctypes, fixtures, role profiles, post-install patches),
`before_uninstall`, `after_migrate`, the lending-app integration hooks and
`setup_wizard_complete` are NOT declared in the manifest — the composer's
`merge_hooks()` appends manifest `after_install` entries to the shell
scaffold's after_install *string* and crashes the generated hooks.py at
import (erp precedent). Fresh sites run once:

    bench --site <site> execute <app>.hrms.install.after_install

(`<app>.hrms.uninstall.before_uninstall` is the uninstall counterpart.)
The upstream post-install patches this runs are ported to
`src/patches_post_install/` and include the Frappenize rokct fork's
postgres fix for `update_employee_advance_status` (original commit
`74d817398`, archived on `rokct-archive-2026-03`); see
`port_report.json["rokct_fixes"]`.

Also NOT wired by the composer (carried pre-mapped in
`port_report.json["hooks_unsupported"]`, hand-writable above a shell's
hooks.py fence): `override_doctype_class` (the EmployeeMaster/Timesheet/
PaymentEntry/Project extensions of erp classes), `doctype_js`,
`regional_overrides` (India payroll), `override_doctype_dashboards`, and
the doctype-registration lists erp consumes (`period_closing_doctypes`,
`accounting_dimension_doctypes`, `bank_reconciliation_doctypes`,
`advance_payment_payable_doctypes`, `invoice_doctypes`).

The hrms/roster PWA (upstream repo-root `frontend/` + `roster/` Vue apps
served via `www/`) is not part of the python package and is not ported;
`dart/` and `nextjs/` are placeholders (no manifest) until those SDK
halves are actually built.
"""

GITIGNORE_FALLBACK = "__pycache__/\n*.py[cod]\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="/workspace/hrms",
                    help="path to a Frappenize/hrms checkout @ "
                         f"{SOURCE_BRANCH} (commit {SOURCE_COMMIT[:10]})")
    ap.add_argument("--erp-tree",
                    default=str(HERE.parent.parent / "erp" / "frappe"),
                    help="path to the GENERATED erp SDK tree "
                         "(<pay repo>/erp/frappe) used as the erpnext.* "
                         "mapping target")
    args = ap.parse_args()
    Porter(Path(args.source).resolve(),
           Path(args.erp_tree).resolve()).run()


if __name__ == "__main__":
    main()
