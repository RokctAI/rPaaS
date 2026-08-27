#!/usr/bin/env python3
# Copyright (c) 2026 RokctAI
# License: MIT. This script is part of the `gateways/` subtree, which is a
# fork of frappe/payments and preserves its MIT license verbatim (see
# gateways/LICENSE). Upstream file headers are never altered by this script.
"""
port_payments.py — deterministic, re-runnable port of the frappe/payments
app into the `gateways` frappe SDK module (erp/port_erpnext.py precedent,
composed by the-rokct-protocol's core/utils/frappe/compose_backend.py).

SOURCE:  a checkout of Frappenize/payments @ rokct
         (= stock upstream frappe/payments develop,
         commit 86fefa9faf8ad825fe6f08c4753acfe44817900b).
DEST:    <pay repo>/gateways/frappe/  (this script lives at
         <pay repo>/gateways/port/).

Run:     python3 gateways/port/port_payments.py [--source /workspace/payments]

The whole transformation is done here, never by hand-editing ported files:
to change the port, change this script and re-run it. The script wipes and
regenerates gateways/frappe/doctype/, gateways/frappe/src/ and
gateways/frappe/manifest.json on every run and emits a machine-readable
summary to gateways/port/port_report.json.

========================== LOCAL OVERLAY ==============================

Rokct-authored files that ship inside the generated tree live in
gateways/local/ (the source of truth — currently the PayFast/Paystack
gateway doctypes, the paystack_checkout page and their test, moved from the
retired `payments/frappe` module). After the upstream copy + remaps, run()
copies local/doctype/** and local/src/** byte-for-byte into the same
positions under gateways/frappe/, and build_manifest() merges
local/manifest_hooks.json into the generated manifest's "hooks" (fixtures
for the two settings doctypes). Because the source of truth is outside the
wiped trees, the overlay survives re-runs by construction; a local path
that collides with a ported upstream file, or a local hook entry that
collides with a generated one, is a hard error. Everything overlaid is
ledgered in port_report.json["local_additions"]. Local files are authored
in final composed form ({app_name} tokens, doctype JSON "module":
"{module_name}") — no dotted-path rewriting is applied to them.

=========================== LAYOUT DECISION ===========================

The composer's model is: one SDK module == one Frappe module ("Module Def").
compose_module() copies <sdk>/doctype/* to <app>/<module>/doctype/*, rewrites
every primary DocType JSON "module" to the manifest name, and copies
<sdk>/src/* to <app>/<module>/*. Frappe resolves a doctype's disk path as
    get_module_path(doc.module) / "doctype" / scrub(doctype_name)
so with module == "gateways" every doctype MUST live at
<app>/gateways/doctype/<dt>/.

frappe/payments has 2 upstream Frappe modules ("Payments" with the Payment
Gateway doctype, "Payment Gateways" with the 9 gateway-settings/mandate
doctypes) and 10 doctypes. Exactly like the erp port, they flatten into the
single "gateways" module — ZERO composer changes needed:

  gateways/frappe/doctype/<dt_snake>/     all 10 doctypes, upstream doctype
                                          NAMES kept verbatim (callers
                                          resolve by doctype name). Doctype
                                          dir names are globally unique in
                                          frappe, so flattening cannot
                                          collide within the app (verified
                                          at runtime — hard error otherwise).
  gateways/frappe/src/<upstream_module>/  everything else in a module dir
                                          (payment_gateways/paymob/,
                                          payment_gateways/
                                          stripe_integration.py, ...) keeps
                                          its upstream package structure, so
                                          `payments.X` maps 1:1 to
                                          `{app_name}.gateways.X`.
  gateways/frappe/src/<top-level>/        top-level packages (config/,
                                          overrides/, public/, templates/,
                                          tests/, utils/) keep their
                                          upstream package structure.
  gateways/frappe/src/gateways_init.py    payments/__init__.py's content
                                          (the composer overwrites the
                                          composed module's __init__.py with
                                          a stub, so package-level API must
                                          live in a named submodule).
                                          `import payments` is rewritten to
                                          `from {app_name}.gateways import
                                          gateways_init as payments`.

The top-level directory is `gateways/` (NOT `payments/`): when the port was
written the pay repo's `payments/` dir still hosted its own composed Frappe
module (name `pay`) and the module names `pay`, `payments`, `wallet` and
`erp` were all taken. That module has since been unified into `gateways`
via the local overlay above; `payments/` now carries only the dart
payments_sdk client.

Import/dotted-path rewrite (applied to .py code, and to string literals in
.py/.js/.json/.html — the composer substitutes {app_name} in all of these,
in both doctype/ and src/ trees):
  payments.<mod>.doctype.<dt>...  -> {app_name}.gateways.doctype.<dt>...
  payments.<anything else known>  -> {app_name}.gateways.<same path>
  payments.<pkg __init__ attr>    -> {app_name}.gateways.gateways_init.<attr>
                                     (string literals only; code references
                                     resolve through the import alias)
  frappe.* / third-party imports  -> untouched
In .js/.json/.html only string literals (server-side dotted paths, e.g.
frappe.call methods) are rewritten. Upstream's references to the separate
`erpnext` app (payments/tests/utils.py, the mpesa runtime imports guarded
by erpnext_app_import_guard, the installed-app checks) are re-pointed at
pay's own composed `erp` SDK module by the ERP_REMAPS rules below, so a
composed site never needs a real `erpnext` app; files whose text still
mentions erpnext afterwards (docs links, comments, retained helper names)
are listed in port_report.json["erpnext_references"].

NOT PORTED (nothing is dropped silently — every category below is also
emitted into port_report.json):
  - hooks.py (translated to manifest.json; keys the composer cannot express
    are carried into port_report.json["hooks_unsupported"] verbatim, with
    dotted values pre-mapped)
  - modules.txt, patches.txt (empty upstream)
  - install/uninstall hooks (before_install, after_install,
    before_uninstall) are deliberately NOT declared in the manifest: the
    composed shell scaffold defines `after_install` as a plain *string* and
    merge_hooks() appends manifest entries with list.append(), crashing the
    generated hooks.py at import (empirically confirmed in the erp port).
    Fresh sites run the custom-field setup once instead:
      bench --site <site> execute <app>.gateways.utils.make_custom_fields
    See port_report.json["install_hooks_not_declared"].
"""

import argparse
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEST = HERE.parent / "frappe"
LOCAL = HERE.parent / "local"  # Rokct-authored overlay (see docstring)

SUBSTITUTABLE = (".py", ".js", ".html", ".json")

# Top-level package entries excluded from the port (see module docstring).
EXCLUDE_TOP = {
    "hooks.py",
    "modules.txt",
    "patches.txt",
}

MODULE_NAME = "gateways"  # the manifest "name" == composed Frappe Module Def
APP = "{app_name}"  # composer token, resolved at compose time

# ---------------------------------------------------------------------------
# erp-module remap (self-containment): upstream frappe/payments integrates
# with the separate `erpnext` app at runtime (guarded imports, installed-app
# checks, test fixtures). The pay repo carries ERPNext as its own composed
# `erp` SDK module (erp/port/port_erpnext.py), so the ported gateways module
# resolves those references against the composed app instead — a site
# composing gateways alongside erp never needs a real `erpnext` app, and a
# site composing gateways WITHOUT erp degrades exactly as gracefully as
# upstream did without erpnext (mirror of port_erpnext.py's
# PAYMENTS_REMAPS; pay PR #22 follow-up).
#
# Mechanics (crm-excision precedent — targeted remap rules, never hand-edits
# of ported files): exact-string rewrite rules keyed by path relative to the
# upstream package, applied AFTER the payments.* dotted rewrite (so anchors
# are spelled in post-rewrite {app_name} form where that rewrite touches
# them). Each `old` must occur exactly once and every listed file must be
# visited, or the port aborts — upstream drift surfaces loudly instead of
# silently shipping a stale remap.
#
# Placement rules:
#   - src/-tree files may carry the composer's {app_name} token.
#   - doctype/-tree files must NOT introduce cross-module {app_name} paths:
#     cross-module references resolve from __name__ via importlib instead
#     (designer design_system.py / productivity crm-port precedent).
#
# NOT remapped (verbatim upstream, recorded in erpnext_references):
#   - payment_gateways/doctype/paytm_settings/paytm_settings.js — the only
#     erpnext mention is an erpnext.com docs URL in a dashboard headline.
#   - templates/pages/gocardless_confirmation.py — `erpnext_customer` is a
#     plain local variable name; no import, nothing to repoint.
ERP_REMAPS = {
    "utils/utils.py": [
        # helper needs find_spec
        (
            "from contextlib import contextmanager\n",
            "from contextlib import contextmanager\n"
            "from importlib.util import find_spec\n",
        ),
        # make_custom_fields: erpnext-app check -> composed-erp-module check
        (
            '\tif "erpnext" in frappe.get_installed_apps():\n'
            "\t\tcustom_fields = {",
            "\tif erp_module_available():\n"
            "\t\tcustom_fields = {",
        ),
        # the import guard: same graceful frappe.throw on ImportError, but
        # the missing dependency is now the composed erp module. Also adds
        # the erp_module_available() helper the checks above resolve to.
        (
            "@contextmanager\n"
            "def erpnext_app_import_guard():\n"
            "\tmarketplace_link = '<a href=\"https://frappecloud.com/"
            "marketplace/apps/erpnext\">Marketplace</a>'\n"
            "\tgithub_link = '<a href=\"https://github.com/frappe/erpnext\">"
            "GitHub</a>'\n"
            '\tmsg = _("erpnext app is not installed. Please install it '
            'from {} or {}").format(\n'
            "\t\tmarketplace_link, github_link\n"
            "\t)\n"
            "\ttry:\n"
            "\t\tyield\n"
            "\texcept ImportError:\n"
            '\t\tfrappe.throw(msg, title=_("Missing ERPNext App"))\n',
            "def erp_module_available():\n"
            '\t"""True when the composed `erp` module (pay SDK\'s ERPNext '
            'port) is part\n'
            "\tof this app. Replaces upstream's check for the separate "
            "`erpnext` app\n"
            "\t(ROKCT self-containment remap).\"\"\"\n"
            "\ttry:\n"
            '\t\treturn find_spec("{app_name}.erp") is not None\n'
            "\texcept (ImportError, ValueError):\n"
            "\t\treturn False\n"
            "\n"
            "\n"
            "@contextmanager\n"
            "def erpnext_app_import_guard():\n"
            '\tmsg = _(\n'
            '\t\t"The erp module (pay SDK\'s ERPNext port) is not part of '
            'this app. "\n'
            '\t\t"Compose the erp module alongside gateways to enable this '
            'feature."\n'
            "\t)\n"
            "\ttry:\n"
            "\t\tyield\n"
            "\texcept ImportError:\n"
            '\t\tfrappe.throw(msg, title=_("Missing erp Module"))\n',
        ),
    ],
    "utils/__init__.py": [
        # re-export the new helper next to the guard
        (
            "\tdelete_custom_fields,\n\terpnext_app_import_guard,\n",
            "\tdelete_custom_fields,\n\terp_module_available,\n"
            "\terpnext_app_import_guard,\n",
        ),
    ],
    "tests/utils.py": [
        (
            "from erpnext.tests.utils import ERPNextTestSuite\n",
            "# ROKCT: the erpnext test-suite base class resolves against "
            "the composed erp\n"
            "# module (pay SDK's ERPNext port) instead of the separate "
            "erpnext app.\n"
            "from {app_name}.erp.tests.utils import ERPNextTestSuite\n",
        ),
    ],
    "payment_gateways/doctype/mpesa_settings/mpesa_settings.py": [
        (
            "from {app_name}.gateways.utils import "
            "erpnext_app_import_guard\n",
            "from {app_name}.gateways.utils import erp_module_available, "
            "erpnext_app_import_guard\n",
        ),
        (
            '\t\tif "erpnext" in frappe.get_installed_apps():\n'
            "\t\t\tcreate_custom_pos_fields()\n",
            "\t\tif erp_module_available():\n"
            "\t\t\tcreate_custom_pos_fields()\n",
        ),
        (
            "\twith erpnext_app_import_guard():\n"
            "\t\tfrom erpnext import get_default_company\n",
            "\twith erpnext_app_import_guard():\n"
            "\t\t# ROKCT: cross-module import into the composed erp module, "
            "resolved from\n"
            "\t\t# __name__ — doctype-tree files must not carry the "
            "composer's app-name\n"
            "\t\t# token for cross-module paths (crm-port precedent). "
            "Upstream imported\n"
            "\t\t# from the separate erpnext app; the guard still catches "
            "ImportError.\n"
            "\t\tfrom importlib import import_module\n"
            "\n"
            "\t\tget_default_company = import_module(\n"
            '\t\t\t__name__.split(".gateways.doctype.", 1)[0] + '
            '".erp.erp_init"\n'
            "\t\t).get_default_company\n",
        ),
    ],
    "payment_gateways/doctype/mpesa_settings/test_mpesa_settings.py": [
        (
            "from erpnext.accounts.doctype.payment_entry.test_payment_entry "
            "import create_customer\n"
            "from erpnext.accounts.doctype.pos_invoice.test_pos_invoice "
            "import create_pos_invoice\n"
            "from erpnext.accounts.doctype.pos_opening_entry."
            "test_pos_opening_entry import create_opening_entry\n"
            "from erpnext.accounts.doctype.pos_profile.test_pos_profile "
            "import make_pos_profile\n",
            "# ROKCT: cross-module test imports into the composed erp "
            "module, resolved\n"
            "# from __name__ — doctype-tree files must not carry the "
            "composer's app-name\n"
            "# token for cross-module paths (crm-port precedent). Upstream "
            "imported from\n"
            "# the separate erpnext app; the erp port flattens doctypes to\n"
            "# <app>.erp.doctype.<dt>.\n"
            "from importlib import import_module as _import_module\n"
            "\n"
            '_ERP = __name__.split(".gateways.doctype.", 1)[0] + ".erp"\n'
            "create_customer = _import_module(_ERP + "
            '".doctype.payment_entry.test_payment_entry").create_customer\n'
            "create_pos_invoice = _import_module(_ERP + "
            '".doctype.pos_invoice.test_pos_invoice").create_pos_invoice\n'
            "create_opening_entry = _import_module(\n"
            '\t_ERP + ".doctype.pos_opening_entry.test_pos_opening_entry"\n'
            ").create_opening_entry\n"
            "make_pos_profile = _import_module(_ERP + "
            '".doctype.pos_profile.test_pos_profile").make_pos_profile\n',
        ),
    ],
}

# ---------------------------------------------------------------------------
# Upstream bug-fix remaps — same mechanics as ERP_REMAPS (exact-string
# anchors, exactly-once, every listed file must be visited or the port
# aborts), applied in the same pass but kept in their own table because they
# fix upstream frappe/payments bugs rather than re-pointing app references.
#
#   paytm_settings.py — upstream frappe/payments issue #181: Paytm retired
#   the securegw-stage.paytm.in staging host in its paytm.in ->
#   paytmpayments.com domain migration, so test-mode ("staging" checkbox)
#   payment initiation dead-ends. The staging endpoints now live at
#   securestage.paytmpayments.com (per the issue and Paytm's current docs);
#   both the order-process and order-status staging URLs move — they share
#   the dead host. Production URLs are untouched (not reported broken).
UPSTREAM_FIX_REMAPS = {
    "payment_gateways/doctype/paytm_settings/paytm_settings.py": [
        (
            '\t\t\t\turl="https://securegw-stage.paytm.in/order/process",\n'
            '\t\t\t\ttransaction_status_url='
            '"https://securegw-stage.paytm.in/order/status",\n',
            '\t\t\t\turl='
            '"https://securestage.paytmpayments.com/order/process",\n'
            '\t\t\t\ttransaction_status_url='
            '"https://securestage.paytmpayments.com/order/status",\n',
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


class Porter:
    def __init__(self, source: Path):
        self.source = source
        self.pkg = source / "payments"
        if not (self.pkg / "hooks.py").exists():
            raise SystemExit(f"[-] {self.pkg} does not look like the "
                             f"frappe/payments package (no hooks.py).")
        self.module_dirs = self._module_dirs()
        self.doctypes = self._doctype_dirs()
        self.report = {
            "source": str(source),
            "module_count": len(self.module_dirs),
            "doctype_count": len(self.doctypes),
            "doctypes": sorted(self.doctypes),
            "excluded": sorted(EXCLUDE_TOP),
            "hooks_supported": {},
            "hooks_unsupported": {},
            "install_hooks_not_declared": {},
            "local_additions": [],
            "erpnext_references": [],
            "unmapped_dotted_paths": [],
            "notes": [],
        }
        self.init_attrs = self._init_attrs()
        self.unmapped = {}
        self.remapped = set()  # ERP_REMAPS keys actually applied
        self.fix_remapped = set()  # UPSTREAM_FIX_REMAPS keys actually applied

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

    def _init_attrs(self):
        names = set()
        for m in re.finditer(r"^(?:def|class)\s+(\w+)|^(\w+)\s*=",
                             read_text(self.pkg / "__init__.py"), re.M):
            names.add(m.group(1) or m.group(2))
        return names

    # ------------------------------------------------------- dotted rewriting
    def _known_top(self):
        # every python-importable top-level name that survives under src/
        # with its upstream name (module dirs + loose top-level packages
        # and modules).
        tops = set(self.module_dirs)
        for p in self.pkg.iterdir():
            if p.name in EXCLUDE_TOP or p.name == "__init__.py":
                continue
            if p.is_dir():
                tops.add(p.name)
            elif p.suffix == ".py":
                tops.add(p.stem)
        return tops

    def map_dotted(self, path):
        """Map a 'payments.x.y...' dotted path to its composed location.

        Returns (mapped, string_only) or (None, False) when unknown.
        """
        parts = path.split(".")
        assert parts[0] == "payments"
        t = parts[1:]
        if not t:
            return None, False
        if t[0] in self.module_dirs and len(t) >= 2 and t[1] == "doctype":
            if len(t) >= 3 and t[2] in self.doctypes:
                return f"{APP}.gateways.doctype." + ".".join(t[2:]), False
            return None, False
        if t[0] in self.known_top:
            return f"{APP}.gateways." + ".".join(t), False
        if t[0] in self.init_attrs:
            return f"{APP}.gateways.gateways_init." + ".".join(t), True
        return None, False

    DOTTED_RE = re.compile(r"(?<![\w.])payments((?:\.[A-Za-z_][A-Za-z0-9_]*)+)")

    def rewrite_text(self, content, rel, is_python):
        """Rewrite payments dotted paths. For python, import statements are
        handled structurally first; then all dotted occurrences are mapped
        (init-attr paths only inside string literals). For js/json/html only
        string literals (quote-preceded) are rewritten."""
        if is_python:
            content = self._rewrite_imports(content, rel)
            content = self._rewrite_special_calls(content)

        def sub(m):
            full = "payments" + m.group(1)
            start = m.start()
            prev = content[start - 1] if start else ""
            in_string_start = prev in "\"'"
            mapped, string_only = self.map_dotted(full)
            if mapped is None:
                self.unmapped.setdefault(full, set()).add(rel)
                return full
            if is_python:
                if string_only and not in_string_start:
                    return full  # code ref via `import ... as payments` alias
                return mapped
            # js / json / html: only rewrite whole-string server paths
            return mapped if in_string_start else full

        return self.DOTTED_RE.sub(sub, content)

    def _rewrite_imports(self, content, rel):
        out = []
        for line in content.split("\n"):
            m = re.match(r"^(\s*)import payments(\s*(#.*)?)?$", line)
            if m:
                out.append(f"{m.group(1)}from {APP}.gateways import "
                           f"gateways_init as payments{m.group(2) or ''}")
                continue
            m = re.match(r"^(\s*)from payments import (.+)$", line)
            if m:
                indent, names_s = m.group(1), m.group(2)
                names = [n.strip() for n in names_s.split(",")]
                top, initial = [], []
                for n in names:
                    base = n.split(" as ")[0].strip()
                    (top if base in self.known_top else initial).append(n)
                lines = []
                if top:
                    lines.append(f"{indent}from {APP}.gateways import "
                                 + ", ".join(top))
                if initial:
                    lines.append(f"{indent}from {APP}.gateways.gateways_init "
                                 f"import " + ", ".join(initial))
                out.extend(lines)
                continue
            out.append(line)
        return "\n".join(out)

    def _rewrite_special_calls(self, content):
        # frappe.get_app_path("payments", ...) resolves against the composed
        # APP, whose gateways module content lives one level down. (No
        # upstream file currently uses it; kept for re-run robustness.)
        content = content.replace(
            'frappe.get_app_path("payments"',
            f'frappe.get_app_path("{APP}", "gateways"')
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
            content = self.apply_erp_remaps(content, rel)
            if rewrite_module_field and src.suffix == ".json":
                content = self.MODULE_JSON_RE.sub(
                    '"module": "{module_name}"', content)
            write_text(dst, content)
        else:
            shutil.copy2(src, dst)

    def apply_erp_remaps(self, content, rel):
        """Apply the ERP_REMAPS and UPSTREAM_FIX_REMAPS rules for one
        upstream-relative path (see the tables' comments). Anchors are
        exact-match, exactly-once."""
        for name, table, applied in (
                ("ERP_REMAPS", ERP_REMAPS, self.remapped),
                ("UPSTREAM_FIX_REMAPS", UPSTREAM_FIX_REMAPS,
                 self.fix_remapped)):
            for old, new in table.get(rel, ()):
                n = content.count(old)
                if n != 1:
                    raise SystemExit(f"[-] {name} anchor matched {n}x "
                                     f"(expected exactly 1) in {rel}:\n{old}")
                content = content.replace(old, new)
            if rel in table:
                applied.add(rel)
        return content

    # ---------------------------------------------------------- local overlay
    LOCAL_TREES = ("doctype", "src")
    LOCAL_META = ("manifest_hooks.json", "README.md")

    def overlay_local(self):
        """Copy gateways/local/** into the generated tree (see docstring).

        Local files are Rokct-authored in final composed form; they are
        byte-copied (no dotted-path rewriting) and ledgered in
        port_report.json["local_additions"]. Collisions with ported upstream
        paths, and unexpected top-level entries in local/, are hard errors.
        """
        if not LOCAL.is_dir():
            return
        for entry in sorted(LOCAL.iterdir()):
            if entry.name in self.LOCAL_META:
                continue
            if entry.name not in self.LOCAL_TREES:
                raise SystemExit(
                    f"[-] unexpected entry in gateways/local/: {entry.name} "
                    f"(only {self.LOCAL_TREES} trees and {self.LOCAL_META} "
                    f"are recognized)")
        for tree in self.LOCAL_TREES:
            root = LOCAL / tree
            if not root.is_dir():
                continue
            for f in sorted(root.rglob("*")):
                if not f.is_file():
                    continue
                rel = f.relative_to(LOCAL)
                dst = DEST / rel
                if dst.exists():
                    raise SystemExit(f"[-] local overlay collision with "
                                     f"ported upstream file: {rel}")
                if f.suffix in SUBSTITUTABLE:
                    read_text(f)  # UTF-8 gate, same as ported files
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                self.report["local_additions"].append(str(rel))
        self.report["local_additions"].sort()
        self.report["notes"].append(
            "local_additions: Rokct-authored files overlaid from "
            "gateways/local/ (the source of truth — PayFast/Paystack "
            "settings doctypes, the paystack_checkout page and their test, "
            "moved from the retired payments/frappe `pay` module) plus the "
            "manifest hook keys merged from local/manifest_hooks.json. "
            "Byte-copied after the upstream port; collisions with ported "
            "paths are hard errors. Edit gateways/local/ and re-run this "
            "script — never the copies under gateways/frappe/.")

    def merge_local_hooks(self, manifest):
        """Merge gateways/local/manifest_hooks.json into the generated
        manifest's "hooks" (list keys extend, dict keys union; a key/entry
        collision with a generated hook is a hard error). Merged keys are
        ledgered in local_additions as 'manifest_hooks.json:<key>'."""
        hooks_file = LOCAL / "manifest_hooks.json"
        if not hooks_file.exists():
            return
        local_hooks = json.loads(read_text(hooks_file))
        for key, val in sorted(local_hooks.items()):
            cur = manifest["hooks"].get(key)
            if cur is None:
                manifest["hooks"][key] = val
            elif isinstance(cur, list) and isinstance(val, list):
                cur.extend(val)
            elif isinstance(cur, dict) and isinstance(val, dict):
                for k, v in val.items():
                    if k in cur:
                        raise SystemExit(f"[-] local manifest hook "
                                         f"'{key}.{k}' collides with a "
                                         f"generated hook entry")
                    cur[k] = v
            else:
                raise SystemExit(f"[-] local manifest hook '{key}' has "
                                 f"incompatible type vs the generated hook")
            self.report["local_additions"].append(
                f"manifest_hooks.json:{key}")
        self.report["local_additions"].sort()

    # ------------------------------------------------------------------- run
    def run(self):
        self.known_top = self._known_top()
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
                self.copy_tree(entry, DEST / "src" / mod / name)

        # 2. top-level package entries
        for entry in sorted(self.pkg.iterdir()):
            name = entry.name
            if name in EXCLUDE_TOP or name in self.module_dirs:
                continue
            if name == "__init__.py":
                self.copy_file(entry, DEST / "src" / "gateways_init.py")
                continue
            self.copy_tree(entry, DEST / "src" / name)

        # 2b. Rokct-authored local overlay (see LOCAL OVERLAY in docstring):
        # copy gateways/local/{doctype,src}/** into the freshly generated
        # tree. Runs after the upstream copies so a collision with a ported
        # file fails loudly; survives re-runs by construction because the
        # source of truth lives outside the wiped trees.
        self.overlay_local()

        # 3. manifest.json from hooks.py, plus the local hooks fragment
        manifest = self.build_manifest()
        self.merge_local_hooks(manifest)
        write_text(DEST / "manifest.json",
                   json.dumps(manifest, indent=2) + "\n")

        # 4. static subtree files
        self.write_static()

        # 5. post-port lint: code that references a package-level attr
        # through the bare `payments` name only works when the file holds the
        # rewritten alias import. Anything else still spelling
        # `payments.<known attr>` in code is a porting bug.
        alias_missing = []
        attr_re = re.compile(
            r"(?<![\w.\"'])payments\.(?:"
            + "|".join(re.escape(a) for a in sorted(self.init_attrs)) + r")\b")
        for py in list((DEST / "src").rglob("*.py")) + list(
                (DEST / "doctype").rglob("*.py")):
            if py == DEST / "src" / "gateways_init.py":
                continue
            c = read_text(py)
            if attr_re.search(c) and "as payments" not in c:
                alias_missing.append(str(py.relative_to(DEST)))
        if alias_missing:
            raise SystemExit("[-] files reference bare `payments.` without "
                             "the gateways_init alias import:\n  "
                             + "\n  ".join(sorted(alias_missing)))

        # 6. verify every ERP_REMAPS file was visited, then record files
        # whose text still mentions erpnext (docs URLs, comments, retained
        # helper names like erpnext_app_import_guard). Deliberately a plain
        # substring scan so any regression back to a real erpnext-app
        # dependency surfaces here.
        missed = sorted(set(ERP_REMAPS) - self.remapped)
        if missed:
            raise SystemExit("[-] ERP_REMAPS entries never applied (upstream "
                             "file moved/renamed?):\n  " + "\n  ".join(missed))
        self.report["erp_remaps"] = {
            rel: len(rules) for rel, rules in sorted(ERP_REMAPS.items())}
        missed = sorted(set(UPSTREAM_FIX_REMAPS) - self.fix_remapped)
        if missed:
            raise SystemExit("[-] UPSTREAM_FIX_REMAPS entries never applied "
                             "(upstream file moved/renamed, or upstream "
                             "fixed the bug itself?):\n  "
                             + "\n  ".join(missed))
        self.report["upstream_fix_remaps"] = {
            rel: len(rules)
            for rel, rules in sorted(UPSTREAM_FIX_REMAPS.items())}
        self.report["notes"].append(
            "upstream_fix_remaps: targeted fixes for upstream "
            "frappe/payments bugs not yet merged upstream — currently the "
            "dead Paytm staging host (issue #181): "
            "securegw-stage.paytm.in -> securestage.paytmpayments.com for "
            "the test-mode order-process and order-status endpoints. Drop "
            "each rule once upstream ships its own fix (the exactly-once "
            "anchor check will flag it loudly).")
        for f in sorted(DEST.rglob("*")):
            if f.is_file() and f.suffix in SUBSTITUTABLE:
                if "erpnext" in read_text(f):
                    self.report["erpnext_references"].append(
                        str(f.relative_to(DEST)))
        self.report["notes"].append(
            "erpnext_references: files whose text still mentions `erpnext` "
            "AFTER the ERP_REMAPS pass re-pointed every runtime import and "
            "installed-app check at the composed erp module "
            "({app_name}.erp). What remains is inert: docs URLs "
            "(erpnext.com), comments, and the retained "
            "erpnext_app_import_guard/ERPNextTestSuite names (kept so ported "
            "call sites stay byte-stable). No composed site needs a real "
            "`erpnext` app; gateways composed WITHOUT erp degrades exactly "
            "as upstream did without erpnext (guarded frappe.throw / "
            "skipped custom fields).")

        self.report["doctype_count"] = (
            len(self.doctypes)
            - len(self.report.get("skipped_doctype_stubs", [])))
        self.report["unmapped_dotted_paths"] = sorted(self.unmapped)
        self.report["unmapped_detail"] = {
            p: sorted(files)[:5] for p, files in sorted(self.unmapped.items())}
        write_text(HERE / "port_report.json",
                   json.dumps(self.report, indent=2, sort_keys=True) + "\n")
        n_files = sum(1 for p in DEST.rglob("*") if p.is_file())
        print(f"[+] Ported {self.report['doctype_count']} doctypes from "
              f"{self.report['module_count']} upstream modules; "
              f"{n_files} files under gateways/frappe/.")
        n_local = len(self.report["local_additions"])
        if n_local:
            print(f"[+] Overlaid {n_local} local additions from "
                  f"gateways/local/ (see port_report.json).")
        if self.unmapped:
            print(f"[!] {len(self.unmapped)} unmapped payments.* dotted "
                  f"paths left verbatim (see port_report.json).")

    # -------------------------------------------------------------- manifest
    def build_manifest(self):
        hooks_ns = {}
        # hooks.py opens with `from . import __version__ as app_version`,
        # which exec() cannot resolve outside the package. Seed the
        # namespace from __init__.py and rewrite that one line to use it.
        exec(compile(read_text(self.pkg / "__init__.py"), "__init__.py",
                     "exec"), hooks_ns)
        hooks_src = read_text(self.pkg / "hooks.py").replace(
            "from . import __version__ as app_version",
            "app_version = __version__", 1)
        exec(compile(hooks_src, "hooks.py", "exec"), hooks_ns)
        hooks_ns.pop("__builtins__", None)
        hooks_ns.pop("__version__", None)

        def map_str(v, strict=True):
            if isinstance(v, str) and v.startswith("payments."):
                mapped, _ = self.map_dotted(v)
                if mapped is None:
                    if strict:
                        raise SystemExit(f"[-] cannot map hook value {v}")
                    return v
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

        # doc_events — upstream declares none today; carried structurally so
        # a re-run against a future source that adds them keeps working.
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
        # whitelisted_methods (the composer emits the pair under BOTH
        # whitelisted_methods and override_whitelisted_methods).
        owm = {k: map_str(v) for k, v in
               hooks_ns.get("override_whitelisted_methods", {}).items()}
        supported["whitelisted_methods"] = owm

        # Install/uninstall hooks are deliberately NOT declared (see module
        # docstring: composer merge_hooks() appends to the shell scaffold's
        # after_install *string* and crashes hooks.py at import — erp
        # precedent). Recorded here so nothing is silently dropped.
        for k in ("before_install", "after_install", "before_uninstall"):
            if k in hooks_ns:
                self.report["install_hooks_not_declared"][k] = map_str(
                    hooks_ns[k])
        self.report["notes"].append(
            "install/uninstall hooks NOT declared in manifest (composer "
            "merge_hooks() after_install string-append bug, erp precedent). "
            "Run `bench --site <site> execute "
            "{app}.gateways.utils.make_custom_fields` once per fresh site "
            "to create the Web Form payment custom fields; "
            "{app}.gateways.utils.delete_custom_fields removes them.")

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
            "before_install", "before_uninstall", "after_install", "commands",
        }
        unsupported = {}
        for k, v in sorted(hooks_ns.items()):
            if k in composer_keys or k.startswith("_"):
                continue
            if callable(v):
                continue
            unsupported[k] = map_val(v) if isinstance(v, (str, list, dict)) else str(v)
        self.report["hooks_unsupported"] = unsupported
        self.report["notes"].append(
            "hooks_unsupported keys are NOT wired by the composer; a shell "
            "can hand-write any of them above its hooks.py fence. Their "
            "dotted values are pre-mapped to composed paths here for that "
            "purpose. Notably extend_doctype_class (the Web Form "
            "PaymentWebForm extension) is a different frappe hook from the "
            "composer-supported override_doctype_class and is carried here "
            "rather than silently converted.")
        self.report["notes"].append(
            "src/templates/ (checkout pages + includes) and src/public/ "
            "compose under the module dir, but frappe serves "
            "templates/pages, jinja includes and public assets from "
            "app-level paths only — like the erp port, they are carried "
            "python-importable but inert as web pages/assets until the "
            "composer grows an app-level channel. The whitelisted methods "
            "inside the checkout page modules remain fully callable.")

        # python dependencies from upstream pyproject.toml
        deps = []
        m = re.search(r"^dependencies\s*=\s*\[(.*?)\]", read_text(
            self.source / "pyproject.toml"), re.S | re.M)
        if m:
            deps = re.findall(r'"([^"]+)"', m.group(1))
        self.report["dependencies"] = deps

        return {
            "name": MODULE_NAME,
            "description": (
                "Modular SDK for payment gateway integrations: full "
                "frappe/payments port (Payment Gateway doctype plus "
                "Braintree, GoCardless, Mpesa, Paymob, PayPal, Paytm, "
                "Razorpay and Stripe gateway settings) flattened into a "
                "single composed frappe module, plus Rokct's own PayFast "
                "and Paystack gateways (gateways/local overlay). Fork of "
                "frappe/payments (MIT) via Frappenize/payments@rokct."),
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
        erp_gitignore = HERE.parent.parent / "erp" / "frappe" / ".gitignore"
        write_text(DEST / ".gitignore",
                   erp_gitignore.read_text() if erp_gitignore.exists()
                   else GITIGNORE_FALLBACK)
        for stack in ("dart", "nextjs"):
            write_text(HERE.parent / stack / ".gitignore",
                       "# placeholder — no {} SDK for gateways yet\n"
                       .format(stack))


README = """\
# gateways — frappe/payments as a composable frappe SDK module

**Provenance:** fork of [frappe/payments](https://github.com/frappe/payments)
at **develop** (commit `86fefa9faf8ad825fe6f08c4753acfe44817900b`), taken via
`Frappenize/payments@rokct`.

**License: MIT** (see [LICENSE](LICENSE), copied verbatim from upstream
`license.txt` — Copyright Frappe Technologies Pvt. Ltd.). Every ported file
keeps its upstream copyright/license header verbatim; nothing is re-stamped.
Because the upstream headers carry Frappe's copyright (not RokctAI's), this
subtree is excluded from the repo's MIT header check (`.licenserc.yaml`),
same as `erp/**`.

The module is named `gateways` (not `payments`): when the port was written
the repo's `payments/` directory still hosted its own composed Frappe module
(name `pay`), and `pay`, `payments`, `wallet` and `erp` were all taken. That
module has since been unified into `gateways` (see below); `payments/` now
carries only the dart payments_sdk client. Upstream's two Frappe modules
(**Payments** and **Payment Gateways**, 10 doctypes) flatten into this
single `gateways` module, erp-precedent style.

The `frappe/` tree is generated by `port/port_payments.py` — a deterministic,
re-runnable transform of the upstream source. Do not hand-edit ported files;
change the script and re-run it. See the script's docstring for the full
layout rationale and `port/port_report.json` for what was and wasn't carried.

**Rokct-authored additions** live in `local/` (source of truth) and are
overlaid into the generated tree by the port script's final step: the
PayFast Settings and Paystack Settings gateway doctypes (upstream
gateway-controller convention, singleton style), the `paystack_checkout`
page, their test, and the DocType fixtures merged from
`local/manifest_hooks.json`. They are ledgered in
`port_report.json["local_additions"]`; see `local/README.md`. Unlike the
ported files these carry RokctAI MIT headers, not Frappe's — the repo's
header check ignores `gateways/**` either way.

**Install hooks:** upstream declares `before_install`, `after_install`
(Web Form payment custom fields) and `before_uninstall`. None are declared
in the manifest — the composer's `merge_hooks()` appends manifest
`after_install` entries to the shell scaffold's after_install *string* and
crashes the generated hooks.py at import (empirically confirmed in the erp
port). Fresh sites run once instead:

    bench --site <site> execute <app>.gateways.utils.make_custom_fields

(`<app>.gateways.utils.delete_custom_fields` is the uninstall counterpart.)

A site composing `gateways` must NOT also have the upstream `payments` app
installed — doctype names are kept verbatim, so the two would double-define
every doctype (erp/crm-precedent exclusivity rule).

Upstream's runtime references to the separate `erpnext` app (guarded
imports, installed-app checks, test fixtures) are re-pointed at pay's own
composed `erp` module by the port script's `ERP_REMAPS` rules: composing
`gateways` alongside `erp` needs no real erpnext app, and composing
`gateways` without `erp` degrades exactly as gracefully as upstream did
without erpnext. The mirror wiring (erp -> gateways) lives in
`erp/port/port_erpnext.py`'s `PAYMENTS_REMAPS`.

`dart/` and `nextjs/` are placeholders (no manifest) until those SDK halves
are actually built.
"""

GITIGNORE_FALLBACK = "__pycache__/\n*.py[cod]\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="/workspace/payments",
                    help="path to a Frappenize/payments checkout @ rokct")
    args = ap.parse_args()
    Porter(Path(args.source).resolve()).run()


if __name__ == "__main__":
    main()
