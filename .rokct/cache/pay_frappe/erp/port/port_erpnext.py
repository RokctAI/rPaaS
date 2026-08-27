#!/usr/bin/env python3
# Copyright (c) 2026 RokctAI
# License: GPL-3.0. This script is part of the `erp/` GPLv3 subtree (see
# erp/LICENSE); it transforms GPLv3 ERPNext sources and is licensed GPL-3.0
# to keep the subtree license-uniform.
"""
port_erpnext.py — deterministic, re-runnable port of ERPNext into the `erp`
frappe SDK module (crm precedent, composed by the-rokct-protocol's
core/utils/frappe/compose_backend.py).

SOURCE:  a checkout of Frappenize/erpnext @ rokct-hotfix
         (= stock upstream frappe/erpnext version-16-hotfix tip,
         commit f813774f63 — carries security fixes not yet released on
         the tag-bearing version-16 branch; see SOURCE_COMMIT below).
DEST:    <pay repo>/erp/frappe/  (this script lives at <pay repo>/erp/port/).

Run:     python3 erp/port/port_erpnext.py [--source /workspace/erpnext]

The whole transformation is done here, never by hand-editing ported files:
to change the port, change this script and re-run it. The script wipes and
regenerates erp/frappe/doctype/, erp/frappe/src/ and erp/frappe/manifest.json
on every run and emits a machine-readable summary to erp/port/port_report.json.

=========================== LAYOUT DECISION ===========================

The composer's model is: one SDK module == one Frappe module ("Module Def").
compose_module() copies <sdk>/doctype/* to <app>/<module>/doctype/*, rewrites
every primary DocType JSON "module" to the manifest name, and copies <sdk>/src/*
to <app>/<module>/* (with src/www and src/patches redirected app-level).
Frappe resolves a doctype's disk path as
    get_module_path(doc.module) / "doctype" / scrub(doctype_name)
so with module == "erp" every doctype MUST live at <app>/erp/doctype/<dt>/.

ERPNext has 21 upstream Frappe modules and 531 doctypes. The chosen design —
which needs ZERO composer changes — flattens them into the single "erp"
module:

  erp/frappe/doctype/<dt_snake>/          all 531 doctypes, upstream doctype
                                          NAMES kept verbatim (crm precedent;
                                          callers resolve by doctype name).
                                          Doctype dir names are globally
                                          unique in frappe, so flattening
                                          cannot collide within ERPNext
                                          (verified at runtime by this
                                          script — hard error otherwise).
  erp/frappe/src/<artifact>/<name>/       module-owned record/code artifacts
                                          frappe locates via the SAME
                                          get_module_path(module)/<artifact>/
                                          rule (report, page, print_format,
                                          workspace, notification, web_form,
                                          dashboard_chart, number_card,
                                          onboarding, form_tour, ...): also
                                          flattened, name-collision-checked.
  erp/frappe/src/erp_dashboard/           frappe's dashboard sync reads
                                          <module>/<module>_dashboard/ — all
                                          upstream <mod>_dashboard dirs merge
                                          here.
  erp/frappe/src/<upstream_module>/       everything else in a module dir
                                          (utils.py, party.py, country packs,
                                          setup wizard, ...) keeps its
                                          upstream package structure, so
                                          most `erpnext.X` imports map 1:1 to
                                          `{app_name}.erp.X`.
  erp/frappe/src/erp_init.py              erpnext/__init__.py's content. The
                                          composer overwrites the composed
                                          module's __init__.py with a stub,
                                          so the upstream package-level API
                                          (get_default_company, ...) must
                                          live in a named submodule.
                                          `import erpnext` is rewritten to
                                          `from {app_name}.erp import
                                          erp_init as erpnext`.

Import/dotted-path rewrite (applied to .py code, and to string literals in
.py/.js/.json/.html — the composer substitutes {app_name} in all of these,
in both doctype/ and src/ trees):
  erpnext.<mod>.doctype.<dt>...   -> {app_name}.erp.doctype.<dt>...
  erpnext.<mod>.<artifact>.<x>... -> {app_name}.erp.<artifact>.<x>...
                                     (only when <x> was actually flattened;
                                     loose module files under report/ and
                                     page/ stay at src/<mod>/<artifact>/)
  erpnext.<anything else known>   -> {app_name}.erp.<same path>
  erpnext.<pkg __init__ attr>     -> {app_name}.erp.erp_init.<attr>
                                     (string literals only; code references
                                     resolve through the import alias)
  frappe.* / third-party imports  -> untouched
In .js/.json/.html only string literals (server-side dotted paths, e.g.
frappe.call methods) are rewritten; unquoted `erpnext.*` in JS is the
CLIENT-side JS namespace and is left alone.

Rejected alternative: a composer extension mapping one SDK to many Module
Defs. Not needed — the flattening verifiably satisfies frappe's module->path
math at this scale with the composer exactly as it is today, and keeps every
existing module's behavior byte-identical by construction.

NOT PORTED (nothing is dropped silently — every category below is also
emitted into port_report.json):
  - crm/, projects/, support/ (EXCLUDE_MODULES): upstream modules owned by
                       their own composed SDK modules in the productivity
                       repo — the merged crm module (28 doctypes), and the
                       projects (15 doctypes) / support (11 doctypes)
                       modules excised in the erp-breakup — each composing
                       at {app_name}/<mod>/ with the upstream layout. erp's
                       dotted references remap
                       erpnext.<mod>.X -> {app_name}.<mod>.X; hooks whose
                       handlers live in an excluded module are dropped from
                       erp's manifest and reported under
                       port_report.json["excluded_modules"]["hooks_reassigned"].
  - locale/           (~100MB translations; frappe loads them app-level only,
                       the composer has no app-level asset channel)
  - www/              (composer's www merge handles flat files only, and the
                       portal pages need app-level templates/ which the
                       composer cannot place)
  - patches/ + patches.txt (upstream migration history for pre-existing
                       ERPNext databases; a composed shell starts fresh and
                       frappe marks patches completed-without-running on
                       fresh installs. The composer also only supports flat,
                       globally-unique patch filenames.)
  - change_log/, hooks.py (translated to manifest.json), modules.txt
  - hooks.py keys the composer cannot express — carried into
    port_report.json["hooks_unsupported"] verbatim.
  - fleet-collision doctypes (EXCLUDE_FLEET_DOCTYPES): Branch, Brand,
    Delivery Settings, Subscription and Subscription Settings (plus the
    dependent Process Subscription and Subscription Invoice) — their
    doctype dir names collide with doctypes owned by other fleet SDK
    modules (base, products, delivery, subscriptions) and the composer
    hard-fails duplicate doctypes. Excluded rather than renamed
    (crm-excision precedent; reversible one-line change). Ledgered in
    port_report.json["excluded_fleet_collisions"]; sources preserved
    verbatim under port/exports/fleet_collisions/; surviving python
    callers guarded via FLEET_COLLISION_REMAPS + fleet_shims.py.
  - dead doctypes (EXCLUDE_DOCTYPES) + the youtube_interactions report
    (EXCLUDE_ARTIFACT_RECORDS): orphaned website child tables the v16 port
    left without any inbound reference, and the desk-only "learn via
    YouTube" Video feature. Ledgered in
    port_report.json["excluded_doctypes"]; sources preserved verbatim under
    port/exports/dead_doctypes/.
  - desk furniture (EXCLUDE_FIXTURE_ARTIFACTS / EXCLUDE_TOP_FIXTURES /
    EXCLUDE_DASHBOARD_FIXTURES): Frappe-desk fixture records (workspaces,
    sidebars, desktop icons, onboarding, dashboard charts/cards, form
    tours, dashboards, report center) — the platform's product surfaces
    are Flutter + Next.js shells, not the Frappe desk. Ledgered in
    port_report.json["excluded_fixture_records"]; every excluded record is
    preserved verbatim under port/exports/desk_fixtures/ for reuse (e.g.
    rebuilding charts/KPIs/onboarding in the Next.js SDK). Functional desk
    pages (page/, incl. point_of_sale), *_settings singles, print formats,
    notifications and web forms are NOT furniture and stay ported.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Pinned upstream provenance. The port is only reproducible against exactly
# this commit of Frappenize/erpnext (branch `rokct-hotfix`); the script
# hard-errors if the --source checkout is at any other commit.
SOURCE_COMMIT = "f813774f63c9ad437bebe351746daf76e59a4130"
SOURCE_BRANCH = "rokct-hotfix"

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
DEST = HERE.parent / "frappe"

SUBSTITUTABLE = (".py", ".js", ".html", ".json")

# ---------------------------------------------------------------------------
# Persona layout (persona wave phase 1, pay#30): every frappe module's src
# code and doctype trees live under src/tenant/ and the manifest declares
# both personas (tenant populated, control: {}). The composer relocates
# persona doctype dirs (src/tenant/doctype/<dt>) to <app>/<module>/doctype/
# at compose time, so doctype dotted paths keep the module-root form
# ({app_name}.erp.doctype.<dt>...), while module src code composes to
# <app>/<module>/tenant/... and its dotted paths gain the .tenant. segment
# ({app_name}.erp.tenant.<mod>...). The composer's carve-outs keep
# src/templates/ (and src/www/ where present) top-level, so
# {app_name}.erp.templates... paths stay tenant-less.
PERSONA = "tenant"
# top-level source entries that stay OUTSIDE src/tenant/ (composer carve-outs
# plus repo lint config).
PERSONA_TOP_CARVEOUTS = {"templates", ".stylelintrc"}
# EXCLUDE_MODULES whose owning SDK module is itself persona-ized (its module
# src composes at {app_name}/<mod>/tenant/...): non-doctype dotted refs into
# it gain the .tenant. segment. projects/support in the productivity repo are
# NOT persona-ized (their src stays at {app_name}/<mod>/...).
PERSONA_SDK_MODULES = {"crm"}

# Module-dir artifact types frappe resolves via get_module_path(module)/<type>/
# and that are therefore flattened to src/<type>/ (composing to
# <app>/erp/<type>/). "report" and "page" flatten SUBDIRECTORIES only: loose
# helper modules under them (accounts/report/financial_statements.py,
# */report/test_reports.py — the latter name collides across modules) keep
# their upstream package path under src/<mod>/report/.
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

# Upstream Frappe MODULES excluded from the port wholesale — their doctype
# dirs, module src code and module-owned artifacts (report/, workspace/,
# dashboard_chart/, number_card/, <mod>_dashboard/, ...) are NOT ported,
# because their content is owned by a different composed SDK module. Dotted
# references INTO an excluded module are remapped 1:1 onto that module's own
# composed namespace instead of erp's:
#   erpnext.<mod>.<x>...  ->  {app_name}.<mod>.<x>...
# (the excluded modules' SDK homes — all in the productivity repo: the
# merged crm module, and the projects/support modules excised in the
# erp-breakup — compose at {app_name}/<mod>/ keeping the upstream package
# layout and the identical doctype dir names: lead, project, task,
# timesheet, issue, warranty_claim, ...). Hooks whose handlers live in an
# excluded module are dropped from erp's manifest and reported under
# port_report.json["excluded_modules"]["hooks_reassigned"] so the owning
# module's manifest can declare them instead.
EXCLUDE_MODULES = {"crm", "projects", "support"}

# Top-level package entries excluded from the port (see module docstring).
EXCLUDE_TOP = {
    "locale",
    "www",
    "patches",
    "change_log",
    "hooks.py",
    "modules.txt",
    "patches.txt",
}

# Individual doctypes excluded from the port (doctype DIR names) — a
# doctype-level sibling of EXCLUDE_MODULES for modules that are otherwise
# ported. These are dead surfaces with ZERO inbound references anywhere in
# the ported tree (re-verified at every run: any dotted reference to them
# surfaces in unmapped_dotted_paths, and hooks targeting them are dropped
# loudly into the ledger):
#   - bom_website_item / bom_website_operation / item_website_specification /
#     website_attribute / website_filter_field / website_item_group —
#     orphaned website child tables (istable=1) whose parents lost the
#     embedding Table fields in the v14 e-commerce split; remnants of the
#     pre-webshop website portal.
#   - video / video_settings — the Frappe-desk "learn via YouTube" feature
#     (YouTube stats sync). Its scheduler hook and the youtube_interactions
#     report die with it (see EXCLUDE_ARTIFACT_RECORDS).
# Excluded sources are preserved verbatim under port/exports/dead_doctypes/
# and ledgered in port_report.json["excluded_doctypes"].
EXCLUDE_DOCTYPES = {
    "bom_website_item",
    "bom_website_operation",
    "item_website_specification",
    "video",
    "video_settings",
    "website_attribute",
    "website_filter_field",
    "website_item_group",
}

# Fleet-collision doctypes excluded from the port (doctype DIR names) — the
# erp fork keeps upstream doctype names verbatim, and five of them collide
# with doctype dirs owned by OTHER fleet SDK modules; the composer hard-fails
# a strict build on any duplicate doctype, so erp could never compose beside
# those modules (base, products, delivery, subscriptions). Decision
# (crm-excision precedent): EXCLUDE the colliding erpnext doctypes rather
# than rename them — reversible by removing an entry here and re-running the
# port. Sources are preserved verbatim under port/exports/fleet_collisions/
# and ledgered in port_report.json["excluded_fleet_collisions"]. Link fields
# pointing at the doctype NAMES stay: a Link stores only the name, which in
# a composed shell resolves to the fleet owner's doctype of that name.
# Python references INTO the excluded controllers are guarded via
# FLEET_COLLISION_REMAPS below; hooks targeting them are dropped loudly into
# the ledger by build_manifest().
EXCLUDE_FLEET_DOCTYPES = {
    # dir name -> the fleet owner of the colliding doctype name
    "branch": "core repo, base module (shop-location Branch)",
    "brand": "commerce repo, products module (marketplace Brand)",
    "delivery_settings": "zones repo, delivery module (Delivery Settings)",
    "subscription": "agent repo, subscriptions module (Subscription)",
    "subscription_settings":
        "agent repo, subscriptions module (Subscription Settings)",
    # dependents that die with the Subscription feature:
    "process_subscription":
        "dependent: imports the excluded subscription controller and "
        "enqueues its process_all",
    "subscription_invoice":
        "dependent: child table whose only parent doctype (Subscription) "
        "is excluded",
}

# Reference guards for the fleet-collision exclusion — same exact-anchor,
# exactly-once, every-file-visited mechanics as PAYMENTS_REMAPS, but applied
# BEFORE the erpnext.* dotted rewrite (anchors are spelled in UPSTREAM
# form): the guarded references must never reach the dotted mapper, which
# can no longer map them (the excluded doctypes are popped from the map so
# any straggler surfaces loudly in unmapped_dotted_paths). Ledgered in
# port_report.json["excluded_fleet_collisions"]["remapped_references"].
_BRAND_IMPORT = ("from erpnext.setup.doctype.brand.brand import "
                 "get_brand_defaults\n")
_BRAND_SHIM = (
    "# ROKCT fleet-collision excision: the erpnext Brand master is "
    "excluded (its\n"
    "# doctype name collides with the commerce repo's products module); "
    "brand-level\n"
    "# item defaults are neutralized (see port/port_erpnext.py "
    "EXCLUDE_FLEET_DOCTYPES).\n"
    "from {app_name}.erp.tenant.fleet_shims import get_brand_defaults\n")
FLEET_COLLISION_REMAPS = {
    "controllers/stock_controller.py": [(_BRAND_IMPORT, _BRAND_SHIM)],
    "assets/doctype/asset_capitalization/asset_capitalization.py": [
        (_BRAND_IMPORT, _BRAND_SHIM)],
    "subcontracting/doctype/subcontracting_receipt/"
    "subcontracting_receipt.py": [(_BRAND_IMPORT, _BRAND_SHIM)],
    "stock/doctype/material_request/material_request.py": [
        (_BRAND_IMPORT, _BRAND_SHIM)],
    "stock/doctype/stock_entry/stock_entry.py": [
        (_BRAND_IMPORT, _BRAND_SHIM)],
    "stock/get_item_details.py": [(_BRAND_IMPORT, _BRAND_SHIM)],
    "accounts/doctype/payment_request/payment_request.py": [
        (
            'def get_subscription_details(reference_doctype, '
            'reference_name):\n'
            '\tif reference_doctype == "Sales Invoice":\n'
            '\t\tsubscriptions = frappe.db.sql(\n'
            '\t\t\t"""SELECT parent as sub_name FROM `tabSubscription '
            'Invoice` WHERE invoice=%s""",\n'
            '\t\t\treference_name,\n'
            '\t\t\tas_dict=1,\n'
            '\t\t)\n'
            '\t\tsubscription_plans = []\n'
            '\t\tfor subscription in subscriptions:\n'
            '\t\t\tplans = frappe.get_doc("Subscription", '
            'subscription.sub_name).plans\n'
            '\t\t\tfor plan in plans:\n'
            '\t\t\t\tsubscription_plans.append(plan)\n'
            '\t\treturn subscription_plans\n',
            'def get_subscription_details(reference_doctype, '
            'reference_name):\n'
            '\t# ROKCT fleet-collision excision: the erpnext Subscription '
            'feature\n'
            '\t# (Subscription, Subscription Settings, Subscription '
            'Invoice, Process\n'
            '\t# Subscription) is excluded from the port — its doctype '
            'names collide\n'
            '\t# with the agent repo\'s subscriptions module (see '
            'port/port_erpnext.py\n'
            '\t# EXCLUDE_FLEET_DOCTYPES). Invoices are never '
            'subscription-generated in a\n'
            '\t# composed shell; keep the whitelisted endpoint '
            '(payment_request.js calls\n'
            '\t# it) but report no subscription plans.\n'
            '\treturn []\n',
        ),
    ],
}

# Generated stand-in module for the fleet-collision excision (written to
# src/tenant/fleet_shims.py on every run; FLEET_COLLISION_REMAPS points the
# surviving callers at it).
FLEET_SHIMS_PY = '''\
# Copyright (c) 2026 RokctAI
# License: GPL-3.0 (part of the erp/ GPLv3 subtree). Generated by
# port/port_erpnext.py — do not hand-edit; change the script and re-run.
"""Neutral stand-ins for ERPNext features excluded from the erp port
because their DocType names collide with doctype names owned by other
fleet SDK modules (see port_report.json["excluded_fleet_collisions"] and
EXCLUDE_FLEET_DOCTYPES in port/port_erpnext.py). Each stand-in keeps its
callers\' contract while the feature itself is excised; restoring a
feature means removing its entry from EXCLUDE_FLEET_DOCTYPES (and its
shim here) and re-running the port.
"""

import frappe


def get_brand_defaults(item, company):
\t"""Stand-in for erpnext.setup.doctype.brand.brand.get_brand_defaults.

\tThe erpnext Brand master is excluded from the port (its doctype name
\tcollides with the commerce repo\'s products module), and brand-level
\titem defaults are gone with it: report no defaults, so callers fall
\tthrough to the item-group / company default chain exactly as upstream
\tdoes for items without a brand."""
\treturn frappe._dict()
'''

# Individual module-owned artifact records excluded from the port
# (artifact type -> subdir names). youtube_interactions is the Video
# doctype's report and dies with it.
EXCLUDE_ARTIFACT_RECORDS = {
    "report": {"youtube_interactions"},
}

# Desk furniture: Frappe-desk fixture records excluded from the port
# wholesale — the platform's product surfaces are Flutter + Next.js shells,
# not the Frappe desk. Excluded records are preserved VERBATIM (raw upstream
# bytes, no rewrites) under port/exports/desk_fixtures/ so their content
# (chart/KPI/onboarding definitions especially) can be reused by the
# Next.js SDK, and ledgered with counts in
# port_report.json["excluded_fixture_records"].
# NOT furniture (still ported): page/ desk pages (point_of_sale is
# functional), *_settings singles, print_format, notification, web_form,
# web_template, print_format_field_template, financial_report_template.
EXCLUDE_FIXTURE_ARTIFACTS = {
    "dashboard_chart",
    "dashboard_chart_source",
    "form_tour",
    "module_onboarding",
    "number_card",
    "onboarding_step",
    "workspace",
}
# upstream <mod>_dashboard/ dirs (composed erp_dashboard/) are furniture too
EXCLUDE_DASHBOARD_FIXTURES = True
# top-level fixture dirs the Frappenize fork carries (flat record JSONs /
# record subdirs copied by the top-level pass): desk furniture as well.
EXCLUDE_TOP_FIXTURES = {
    "desktop_icon",
    "report_center",
    "workspace_sidebar",
}

EXPORTS = HERE / "exports"

MODULE_NAME = "erp"  # the manifest "name" == composed Frappe Module Def
APP = "{app_name}"  # composer token, resolved at compose time

# ---------------------------------------------------------------------------
# payments-app remap (self-containment): upstream ERPNext integrates with the
# separate `payments` app (frappe/payments) at runtime — the Payment Request
# gateway-controller/stripe imports and the "payments"-installed checks. The
# pay repo carries that app as its own composed `gateways` SDK module
# (gateways/port/port_payments.py), so the ported erp module resolves those
# references against the composed app instead — a shell composing erp
# alongside gateways never needs the upstream `payments` python package, and
# a shell composing erp WITHOUT gateways degrades exactly as gracefully as
# upstream did without payments (mirror of port_payments.py's ERP_REMAPS;
# pay PR #22 follow-up).
#
# Mechanics (crm-excision precedent — targeted remap rules, never hand-edits
# of ported files): exact-string rewrite rules keyed by path relative to the
# upstream package, applied AFTER the erpnext.* dotted rewrite (so anchors
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
PAYMENTS_REMAPS = {
    "utilities/__init__.py": [
        # helper needs find_spec
        (
            "from contextlib import contextmanager\n",
            "from contextlib import contextmanager\n"
            "from importlib.util import find_spec\n",
        ),
        # the import guard: same pre-check + graceful frappe.throw on
        # ImportError, but the missing dependency is now the composed
        # gateways module. Also adds the gateways_module_available() helper
        # this guard and templates/pages/order.py resolve to.
        (
            "@contextmanager\n"
            "def payment_app_import_guard():\n"
            "\tmarketplace_link = '<a href=\"https://frappecloud.com/"
            "marketplace/apps/payments\">Marketplace</a>'\n"
            "\tgithub_link = '<a href=\"https://github.com/frappe/payments/"
            "\">GitHub</a>'\n"
            '\tmsg = _("payments app is not installed. Please install it '
            'from {} or {}").format(\n'
            "\t\tmarketplace_link, github_link\n"
            "\t)\n"
            "\n"
            '\tif "payments" not in frappe.get_installed_apps():\n'
            '\t\tfrappe.throw(msg, title=_("Missing Payments App"), '
            "exc=frappe.AppNotInstalledError)\n"
            "\n"
            "\ttry:\n"
            "\t\tyield\n"
            "\texcept ImportError:\n"
            '\t\tfrappe.throw(msg, title=_("Missing Payments App"), '
            "exc=frappe.AppNotInstalledError)\n",
            "def gateways_module_available():\n"
            '\t"""True when the composed `gateways` module (pay SDK\'s '
            "frappe/payments\n"
            "\tport) is part of this app. Replaces upstream's check for the "
            "separate\n"
            "\t`payments` app (ROKCT self-containment remap).\"\"\"\n"
            "\ttry:\n"
            '\t\treturn find_spec("{app_name}.gateways") is not None\n'
            "\texcept (ImportError, ValueError):\n"
            "\t\treturn False\n"
            "\n"
            "\n"
            "@contextmanager\n"
            "def payment_app_import_guard():\n"
            "\tmsg = _(\n"
            '\t\t"The gateways module (pay SDK\'s frappe/payments port) is '
            'not part of this app. "\n'
            '\t\t"Compose the gateways module alongside erp to enable '
            'payment gateway features."\n'
            "\t)\n"
            "\n"
            "\tif not gateways_module_available():\n"
            '\t\tfrappe.throw(msg, title=_("Missing gateways Module"), '
            "exc=frappe.AppNotInstalledError)\n"
            "\n"
            "\ttry:\n"
            "\t\tyield\n"
            "\texcept ImportError:\n"
            '\t\tfrappe.throw(msg, title=_("Missing gateways Module"), '
            "exc=frappe.AppNotInstalledError)\n",
        ),
    ],
    "accounts/doctype/payment_request/payment_request.py": [
        (
            "def _get_payment_gateway_controller(*args, **kwargs):\n"
            "\twith payment_app_import_guard():\n"
            "\t\tfrom payments.utils import get_payment_gateway_controller\n"
            "\n"
            "\treturn get_payment_gateway_controller(*args, **kwargs)\n",
            "def _get_payment_gateway_controller(*args, **kwargs):\n"
            "\t# ROKCT: the upstream `payments` app is carried by the "
            "composed gateways\n"
            "\t# module; the import is resolved from __name__ because "
            "doctype-tree files\n"
            "\t# must not carry the composer's app-name token for "
            "cross-module paths\n"
            "\t# (crm-port precedent). The guard still catches "
            "ImportError.\n"
            "\twith payment_app_import_guard():\n"
            "\t\tfrom importlib import import_module\n"
            "\n"
            "\t\tget_payment_gateway_controller = import_module(\n"
            '\t\t\t__name__.split(".erp.doctype.", 1)[0] + '
            '".gateways.utils"\n'
            "\t\t).get_payment_gateway_controller\n"
            "\n"
            "\treturn get_payment_gateway_controller(*args, **kwargs)\n",
        ),
        (
            '\t\tif payment_provider == "stripe":\n'
            "\t\t\twith payment_app_import_guard():\n"
            "\t\t\t\tfrom payments.payment_gateways.stripe_integration "
            "import create_stripe_subscription\n"
            "\n"
            "\t\t\treturn create_stripe_subscription(gateway_controller, "
            "data)\n",
            '\t\tif payment_provider == "stripe":\n'
            "\t\t\t# ROKCT: gateways-module import resolved from __name__ "
            "(crm-port\n"
            "\t\t\t# precedent — no composer token in doctype-tree files).\n"
            "\t\t\twith payment_app_import_guard():\n"
            "\t\t\t\tfrom importlib import import_module\n"
            "\n"
            "\t\t\t\tcreate_stripe_subscription = import_module(\n"
            '\t\t\t\t\t__name__.split(".erp.doctype.", 1)[0]\n'
            '\t\t\t\t\t+ ".gateways.payment_gateways.stripe_integration"\n'
            "\t\t\t\t).create_stripe_subscription\n"
            "\n"
            "\t\t\treturn create_stripe_subscription(gateway_controller, "
            "data)\n",
        ),
    ],
    "templates/pages/order.py": [
        (
            "from {app_name}.erp.doctype.payment_request.payment_request "
            "import (\n"
            "\tALLOWED_DOCTYPES_FOR_PAYMENT_REQUEST,\n"
            "\tget_amount,\n"
            ")\n",
            "from {app_name}.erp.doctype.payment_request.payment_request "
            "import (\n"
            "\tALLOWED_DOCTYPES_FOR_PAYMENT_REQUEST,\n"
            "\tget_amount,\n"
            ")\n"
            "from {app_name}.erp.tenant.utilities import "
            "gateways_module_available\n",
        ),
        # pay-button gate: upstream disabled it when the payments app was
        # missing; the composed check is the gateways module instead.
        (
            '\t\t\t"payments" in frappe.get_installed_apps()\n',
            "\t\t\tgateways_module_available()\n",
        ),
    ],
}

# ---------------------------------------------------------------------------
# Upstream bug-fix remaps — same mechanics as PAYMENTS_REMAPS (exact-string
# anchors, exactly-once, every listed file must be visited or the port
# aborts), applied in the same pass but kept in their own table because they
# fix upstream ERPNext bugs rather than re-pointing app references.
#
#   payment_request.py — upstream frappe/payments issue #204: every gateway
#   controller in the composed gateways module finalizes a successful
#   payment with
#       frappe.get_doc(reference_doctype, reference_docname)
#           .run_method("on_payment_authorized", status)
#   but upstream ERPNext's PaymentRequest no longer implements
#   on_payment_authorized (it left with the v14 e-commerce split), so
#   run_method dispatches to nothing and a gateway success leaves the
#   Payment Request stuck at "Requested" with no Payment Entry. Reinstate
#   the handler, bridging to the existing set_as_paid()/set_failed() flows.
#   Success statuses cover what the gateway controllers actually pass:
#   Stripe/Braintree/GoCardless/Mpesa/Paytm/PayPal/Paymob/PayFast send
#   "Completed", Razorpay sends "Authorized" or "Verified" (issue #204's
#   literal proposal covers only "Completed"; including Razorpay's success
#   statuses matches the pre-split handler). Unlike the issue's snippet the
#   handler deliberately returns None, not set_as_paid()'s Payment Entry:
#   gateway finalize_request() treats a truthy return as a custom redirect
#   URL and would urlencode the document into the redirect.
UPSTREAM_FIX_REMAPS = {
    "accounts/doctype/payment_request/payment_request.py": [
        (
            "\tdef set_failed(self):\n"
            "\t\tpass\n",
            "\tdef on_payment_authorized(self, payment_status=None):\n"
            '\t\t"""Gateway-controller callback (run_method) after an '
            "external payment\n"
            "\t\tattempt; bridges the gateway result to the Payment Request "
            "lifecycle\n"
            "\t\t(ROKCT reinstatement of the pre-ecommerce-split handler; "
            "upstream\n"
            '\t\tfrappe/payments#204). Returns None on purpose: gateway\n'
            "\t\tfinalize_request() treats a truthy return as a custom "
            'redirect URL."""\n'
            '\t\tif payment_status in ("Authorized", "Verified", '
            '"Completed"):\n'
            '\t\t\tif self.status != "Paid":\n'
            "\t\t\t\tself.set_as_paid()\n"
            '\t\telif payment_status in ("Failed", "Cancelled"):\n'
            "\t\t\tself.set_failed()\n"
            "\n"
            "\tdef set_failed(self):\n"
            "\t\tpass\n",
        ),
    ],
}

# ROKCT feature fixes baked into the fork — same mechanics as
# PAYMENTS_REMAPS/UPSTREAM_FIX_REMAPS (exact-string anchors, exactly-once,
# every listed file must be visited or the port aborts), kept in their own
# table because they carry ROKCT features on top of the pinned upstream
# source rather than re-pointing references or fixing upstream bugs
# (port_hrms.py ROKCT_FIXES precedent). Ledgered in
# port_report.json["rokct_fixes"].
#
#   employee.py / employee.json — rewire of the retired `rhrms` overlay
#   (rokctai/core@451e00a base/frappe/src/rhrms/, dead since the core->base
#   module rename): South-Africa-specific Employee hardening and the
#   HR-Settings-aware employee naming method, applied to the fork that owns
#   the Employee master (Ray, 2026-08-19: "overlay should survive in the
#   fork directly").
#
#   - Fields: id_number (SA national ID, Personal Details tab),
#     bank_account_no + bank_branch_code (Bank Details section). The pay
#     frontend already binds all three
#     (erp/nextjs/templates/app/actions/handson/all/hrms/me/types.ts) —
#     until now they existed nowhere server-side. Upstream's bank_ac_no /
#     iban fields are left untouched.
#   - Validation: 13-digit + Luhn checksum + 18-years-minimum age on
#     id_number; digit/length sanity checks on bank_account_no and
#     bank_branch_code. rhrms ran these unconditionally in an SA-only
#     deployment; the fork gates them on the employee's company country
#     being South Africa so other markets (and IBAN users) stay correct.
#   - autoname: honor HR Settings "Employee Naming By" (Naming Series /
#     Employee Number / Full Name) — the behavior of upstream hrms's
#     EmployeeMaster.autoname override, which the hrms port carries
#     UNWIRED (override_doctype_class deliberately deferred; see
#     hrms/port/port_report.json["hooks_unsupported"]). Baked here
#     directly, with a graceful fallback to the stock naming series when
#     the hrms module is not composed or the setting is unset (upstream
#     EmployeeMaster throws instead — a composed erp-only shell must not).
ROKCT_FIXES = {
    "setup/doctype/employee/employee.py": [
        # imports for the SA validations
        (
            "from frappe.utils import cint, cstr, getdate, today, "
            "validate_email_address\n",
            "from frappe.utils import (\n"
            "\tcint,\n"
            "\tcstr,\n"
            "\tdate_diff,\n"
            "\tgetdate,\n"
            "\tnowdate,\n"
            "\ttoday,\n"
            "\tvalidate_email_address,\n"
            ")\n",
        ),
        # auto-generated type annotations for the added fields
        (
            "\t\tbank_ac_no: DF.Data | None\n"
            "\t\tbank_name: DF.Data | None\n",
            "\t\tbank_ac_no: DF.Data | None\n"
            "\t\tbank_account_no: DF.Data | None\n"
            "\t\tbank_branch_code: DF.Data | None\n"
            "\t\tbank_name: DF.Data | None\n",
        ),
        (
            "\t\tiban: DF.Data | None\n"
            "\t\timage: DF.AttachImage | None\n",
            "\t\tiban: DF.Data | None\n"
            "\t\tid_number: DF.Data | None\n"
            "\t\timage: DF.AttachImage | None\n",
        ),
        # HR-Settings-aware autoname (rhrms/EmployeeMaster rewire)
        (
            "\tdef autoname(self):\n"
            "\t\tset_name_by_naming_series(self)\n"
            "\t\tself.employee = self.name\n",
            "\tdef autoname(self):\n"
            "\t\t# ROKCT fix(hr): honor HR Settings' \"Employee Naming By\" "
            "choice (rhrms\n"
            "\t\t# rewire — upstream hrms's EmployeeMaster.autoname, baked "
            "into the fork;\n"
            "\t\t# see port/port_erpnext.py). Falls back to the stock "
            "naming series when\n"
            "\t\t# the hrms module is not composed or the setting is "
            "unset.\n"
            "\t\tnaming_method = None\n"
            '\t\tif frappe.db.exists("DocType", "HR Settings"):\n'
            "\t\t\tnaming_method = frappe.db.get_single_value("
            '"HR Settings", "emp_created_by")\n'
            '\t\tif naming_method == "Employee Number":\n'
            "\t\t\tself.name = self.employee_number\n"
            '\t\telif naming_method == "Full Name":\n'
            "\t\t\tself.set_employee_name()\n"
            "\t\t\tself.name = self.employee_name\n"
            "\t\telse:\n"
            "\t\t\tset_name_by_naming_series(self)\n"
            "\t\tself.employee = self.name\n",
        ),
        # run the SA validations with the standard validate() chain
        (
            "\t\tself.set_preferred_email()\n"
            "\t\tself.validate_preferred_email()\n",
            "\t\tself.set_preferred_email()\n"
            "\t\tself.validate_preferred_email()\n"
            "\t\tself.validate_sa_id_number()\n"
            "\t\tself.validate_sa_bank_details()\n",
        ),
        # the SA validation methods themselves (rhrms
        # EmployeeMaster.validate_id_number/validate_bank_details rewire)
        (
            "\tdef after_rename(self, old, new, merge):\n",
            "\tdef validate_sa_id_number(self):\n"
            "\t\t# ROKCT fix(hr): South African 13-digit ID validation — "
            "length, Luhn\n"
            "\t\t# checksum and an 18-years-minimum age derived from the "
            "encoded date\n"
            "\t\t# of birth (rhrms rewire; see port/port_erpnext.py).\n"
            '\t\tif not self.get("id_number") or not self.is_sa_company():\n'
            "\t\t\treturn\n"
            "\n"
            "\t\tif len(self.id_number) != 13 or not "
            "self.id_number.isdigit():\n"
            '\t\t\tfrappe.throw(_("ID Number must be exactly 13 digits"), '
            'title=_("Invalid ID"))\n'
            "\n"
            "\t\tchecksum = 0\n"
            "\t\tfor i, digit in enumerate(cint(d) for d in "
            "reversed(self.id_number)):\n"
            "\t\t\tif i % 2 == 1:\n"
            "\t\t\t\tdigit *= 2\n"
            "\t\t\t\tif digit > 9:\n"
            "\t\t\t\t\tdigit -= 9\n"
            "\t\t\tchecksum += digit\n"
            "\t\tif checksum % 10 != 0:\n"
            '\t\t\tfrappe.throw(_("Invalid ID Number checksum"), '
            'title=_("Invalid ID"))\n'
            "\n"
            "\t\tdob = self.get_dob_from_id_number()\n"
            "\t\tif dob and date_diff(nowdate(), dob) < 18 * 365.25:\n"
            "\t\t\tfrappe.throw(\n"
            '\t\t\t\t_("Employee must be at least 18 years old"), '
            'title=_("Age Restriction")\n'
            "\t\t\t)\n"
            "\n"
            "\tdef get_dob_from_id_number(self):\n"
            '\t\t"""Date of birth encoded in a South African ID number '
            '(YYMMDD prefix)."""\n'
            "\t\tfrom datetime import date\n"
            "\n"
            '\t\tif not self.get("id_number") or len(self.id_number) < 6:\n'
            "\t\t\treturn None\n"
            "\n"
            "\t\tyy, mm, dd = self.id_number[:2], self.id_number[2:4], "
            "self.id_number[4:6]\n"
            "\t\tcentury = 1900 if cint(yy) > cint(nowdate()[:4]) % 100 "
            "else 2000\n"
            "\t\ttry:\n"
            "\t\t\treturn date(century + cint(yy), cint(mm), cint(dd))\n"
            "\t\texcept ValueError:\n"
            "\t\t\treturn None\n"
            "\n"
            "\tdef validate_sa_bank_details(self):\n"
            "\t\t# ROKCT fix(hr): SA bank detail sanity checks (rhrms "
            "rewire; see\n"
            "\t\t# port/port_erpnext.py). Upstream's bank_ac_no/iban are "
            "not touched.\n"
            "\t\tif not self.is_sa_company():\n"
            "\t\t\treturn\n"
            "\n"
            '\t\tif self.get("bank_account_no") and (\n'
            "\t\t\tlen(self.bank_account_no) < 7 or not "
            "self.bank_account_no.isdigit()\n"
            "\t\t):\n"
            '\t\t\tfrappe.throw(_("Invalid Bank Account Number"), '
            'title=_("Invalid Bank Details"))\n'
            "\n"
            '\t\tif self.get("bank_branch_code") and (\n'
            "\t\t\tlen(self.bank_branch_code) < 5 or not "
            "self.bank_branch_code.isdigit()\n"
            "\t\t):\n"
            '\t\t\tfrappe.throw(_("Invalid Bank Branch Code"), '
            'title=_("Invalid Bank Details"))\n'
            "\n"
            "\tdef is_sa_company(self):\n"
            '\t\t"""ROKCT (rhrms rewire): gate the SA-specific HR '
            "hardening on the\n"
            "\t\temployee's company being South African — rhrms ran the "
            "checks\n"
            "\t\tunconditionally in an SA-only deployment; the fork must "
            "stay correct\n"
            '\t\tfor other markets."""\n'
            "\t\tif not self.company:\n"
            "\t\t\treturn False\n"
            "\t\treturn ("
            'frappe.get_cached_value("Company", self.company, "country") '
            '== "South Africa")\n'
            "\n"
            "\tdef after_rename(self, old, new, merge):\n",
        ),
    ],
    "setup/doctype/employee/employee.json": [
        # field_order: bank_account_no + bank_branch_code after bank_ac_no
        (
            '  "bank_ac_no",\n'
            '  "iban",\n',
            '  "bank_ac_no",\n'
            '  "bank_account_no",\n'
            '  "bank_branch_code",\n'
            '  "iban",\n',
        ),
        # field_order: id_number opens the Personal Details tab
        (
            '  "personal_details",\n'
            '  "marital_status",\n',
            '  "personal_details",\n'
            '  "id_number",\n'
            '  "marital_status",\n',
        ),
        # field definitions: the two bank fields after upstream bank_ac_no
        (
            "  {\n"
            '   "depends_on": "eval:doc.salary_mode == \'Bank\'",\n'
            '   "fieldname": "bank_ac_no",\n'
            '   "fieldtype": "Data",\n'
            '   "label": "Bank A/C No.",\n'
            '   "oldfieldname": "bank_ac_no",\n'
            '   "oldfieldtype": "Data"\n'
            "  },\n",
            "  {\n"
            '   "depends_on": "eval:doc.salary_mode == \'Bank\'",\n'
            '   "fieldname": "bank_ac_no",\n'
            '   "fieldtype": "Data",\n'
            '   "label": "Bank A/C No.",\n'
            '   "oldfieldname": "bank_ac_no",\n'
            '   "oldfieldtype": "Data"\n'
            "  },\n"
            "  {\n"
            '   "depends_on": "eval:doc.salary_mode == \'Bank\'",\n'
            '   "fieldname": "bank_account_no",\n'
            '   "fieldtype": "Data",\n'
            '   "label": "Bank Account No."\n'
            "  },\n"
            "  {\n"
            '   "depends_on": "eval:doc.salary_mode == \'Bank\'",\n'
            '   "fieldname": "bank_branch_code",\n'
            '   "fieldtype": "Data",\n'
            '   "label": "Bank Branch Code"\n'
            "  },\n",
        ),
        # field definition: id_number in the Personal Details tab
        (
            "  {\n"
            '   "collapsible": 1,\n'
            '   "fieldname": "personal_details",\n'
            '   "fieldtype": "Tab Break",\n'
            '   "label": "Personal Details"\n'
            "  },\n",
            "  {\n"
            '   "collapsible": 1,\n'
            '   "fieldname": "personal_details",\n'
            '   "fieldtype": "Tab Break",\n'
            '   "label": "Personal Details"\n'
            "  },\n"
            "  {\n"
            '   "fieldname": "id_number",\n'
            '   "fieldtype": "Data",\n'
            '   "label": "ID Number"\n'
            "  },\n",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Fleet SDK compliance remaps — the pay-repo compliance sweep (pay#33,
# "resolve all 137 error-severity SDK compliance findings") folded into the
# port so the generated tree carries it deterministically. Same mechanics as
# PAYMENTS_REMAPS (exact-string anchors spelled in post-rewrite form,
# exactly-once, every listed file must be visited or the port aborts).
# Content: `# compliance-ignore` suppression comments with inline reasons,
# requests timeouts (http-timeout findings), frappe.db.escape'd IN-lists in
# sales_payment_summary (sql-injection hardening). Ledgered in
# port_report.json["compliance_remaps"].
COMPLIANCE_REMAPS = {
    '__init__.py': [
        (
            '\tif company not in frappe.flags.company_currency:\n\t\tfrappe.flags.company_currency[company] = frappe.db.get_value(',
            '\tif company not in frappe.flags.company_currency:\n\t\t# compliance-ignore: obs-db-tracing (internal server-side ORM lookup; no inbound request trace context to propagate)\n\t\tfrappe.flags.company_currency[company] = frappe.db.get_value(',
        ),
        (
            '\n\tcompany = frappe.get_doc("Company", company)',
            '\n\t# compliance-ignore: obs-db-tracing (internal server-side ORM lookup; no inbound request trace context to propagate)\n\tcompany = frappe.get_doc("Company", company)',
        ),
    ],
    'accounts/custom/address.py': [
        (
            '\t\tfilters = {"customer_primary_address": self.name}\n\t\tcustomers = frappe.db.get_all("Customer", filters=filters, as_list=True)\n\t\tfor customer_name in customers:\n\t\t\tfrappe.db.set_value("Customer", customer_name[0], "primary_address", address_display)',
            '\t\tfilters = {"customer_primary_address": self.name}\n\t\t# compliance-ignore: obs-db-tracing (internal server-side ORM lookup; no inbound request trace context to propagate)\n\t\tcustomers = frappe.db.get_all("Customer", filters=filters, as_list=True)\n\t\tfor customer_name in customers:\n\t\t\t# compliance-ignore: obs-db-tracing (internal server-side ORM lookup; no inbound request trace context to propagate)\n\t\t\tfrappe.db.set_value("Customer", customer_name[0], "primary_address", address_display)',
        ),
    ],
    'accounts/doctype/account_category/account_category.py': [
        (
            '# For license information, please see license.txt\nimport json',
            "# For license information, please see license.txt\n# compliance-ignore-file: path-traversal (joins app module path with the constant filename 'account_categories.json'; no user-controlled segments)\nimport json",
        ),
    ],
    'accounts/doctype/bank_transaction/auto_match_party.py': [
        (
            '\t\t# If no party is found, search in Employee (since it has bank account details)\n\t\tif employee_result := frappe.db.get_all(',
            '\t\t# If no party is found, search in Employee (since it has bank account details)\n\t\t# compliance-ignore: obs-db-tracing (internal server-side ORM lookup; no inbound request trace context to propagate)\n\t\tif employee_result := frappe.db.get_all(',
        ),
    ],
    'accounts/doctype/chart_of_accounts_importer/chart_of_accounts_importer.py': [
        (
            '\nimport csv',
            "\n# compliance-ignore-file: path-traversal (joins this module's own dir with the constant sample filename 'coa_sample_template.csv'; no user-controlled segments)\nimport csv",
        ),
    ],
    'accounts/doctype/currency_exchange_settings/currency_exchange_settings.py': [
        (
            '\nimport frappe',
            '\n# compliance-ignore-file: obs-python-trace (outgoing call targets the tenant-configured external exchange-rate API; third-party host outside our trace domain)\nimport frappe',
        ),
    ],
    'accounts/doctype/financial_report_template/financial_report_template.py': [
        (
            '\nimport os',
            "\n# compliance-ignore-file: path-traversal (developer-mode-only module-template export/delete; paths rooted in the doc's own module dir with frappe.scrub'd names, gated on frappe.conf.developer_mode)\nimport os",
        ),
    ],
    'accounts/doctype/loyalty_point_entry/loyalty_point_entry.py': [
        (
            '\n\treturn frappe.db.sql(',
            '\n\t# compliance-ignore: sql-injection (fully parameterized query; raw SQL needed for join/aggregate shape)\n\treturn frappe.db.sql(',
        ),
        (
            '\treturn frappe._dict(\n\t\tfrappe.db.sql(',
            '\treturn frappe._dict(\n\t\t# compliance-ignore: sql-injection (fully parameterized query; raw SQL needed for join/aggregate shape)\n\t\tfrappe.db.sql(',
        ),
    ],
    'accounts/doctype/payment_entry/payment_entry.py': [
        (
            '\nimport json',
            "\n# compliance-ignore-file: obs-python-trace (no outgoing HTTP in this file; checker substring-matched 'requests.get' inside local variable 'references_open_payment_requests.get(...)')\nimport json",
        ),
    ],
    'accounts/doctype/payment_gateway_account/payment_gateway_account.py': [
        (
            '\nimport frappe',
            '\n# compliance-ignore-file: ztna-authz (DocType controller guarded by Frappe role permissions; not an API endpoint)\nimport frappe',
        ),
        (
            '\tdef autoname(self):\n\t\tabbr = frappe.db.get_value("Company", self.company, "abbr")',
            '\tdef autoname(self):\n\t\t# compliance-ignore: obs-db-tracing (internal server-side ORM lookup; no inbound request trace context to propagate)\n\t\tabbr = frappe.db.get_value("Company", self.company, "abbr")',
        ),
    ],
    'accounts/doctype/payment_gateway_account/payment_gateway_account_dashboard.py': [
        (
            'def get_data():',
            '# compliance-ignore-file: ztna-authz (static dashboard link config; no auth/API surface)\ndef get_data():',
        ),
    ],
    'accounts/report/sales_payment_summary/sales_payment_summary.py': [
        (
            '\tconditions = get_conditions(filters)\n\tresult = frappe.db.sql(',
            '\tconditions = get_conditions(filters)\n\t# compliance-ignore: sql-injection (conditions assembled from literal fragments containing only %(name)s placeholders; filters passed as params)\n\tresult = frappe.db.sql(',
        ),
        (
            'def get_sales_invoice_data(filters):\n\tconditions = get_conditions(filters)\n\treturn frappe.db.sql(\n\t\tf"""',
            'def get_sales_invoice_data(filters):\n\tconditions = get_conditions(filters)\n\t# compliance-ignore: sql-injection (conditions assembled from literal fragments containing only %(name)s placeholders; filters passed as params)\n\treturn frappe.db.sql(\n\t\tf"""',
        ),
        (
            '\tinvoice_list = get_invoices(filters)\n\tinvoice_list_names = ",".join("\'" + invoice["name"] + "\'" for invoice in invoice_list)\n\tif invoice_list:\n\t\tinv_mop = frappe.db.sql(',
            '\tinvoice_list = get_invoices(filters)\n\tinvoice_list_names = ",".join(frappe.db.escape(invoice["name"]) for invoice in invoice_list)\n\tif invoice_list:\n\t\t# compliance-ignore: sql-injection (IN-list built from frappe.db.escape\'d invoice names; remainder static)\n\t\tinv_mop = frappe.db.sql(',
        ),
        (
            '\tconditions = get_conditions(filters)\n\treturn frappe.db.sql(',
            '\tconditions = get_conditions(filters)\n\t# compliance-ignore: sql-injection (conditions assembled from literal fragments containing only %(name)s placeholders; filters passed as params)\n\treturn frappe.db.sql(',
        ),
        (
            '\tinvoice_list = get_invoices(filters)\n\tinvoice_list_names = ",".join("\'" + invoice["name"] + "\'" for invoice in invoice_list)\n\tif invoice_list:\n\t\tinv_mop_detail = frappe.db.sql(',
            '\tinvoice_list = get_invoices(filters)\n\tinvoice_list_names = ",".join(frappe.db.escape(invoice["name"]) for invoice in invoice_list)\n\tif invoice_list:\n\t\t# compliance-ignore: sql-injection (IN-list built from frappe.db.escape\'d invoice names; remainder static)\n\t\tinv_mop_detail = frappe.db.sql(',
        ),
        (
            '\n\t\tinv_change_amount = frappe.db.sql(',
            "\n\t\t# compliance-ignore: sql-injection (IN-list built from frappe.db.escape'd invoice names; remainder static)\n\t\tinv_change_amount = frappe.db.sql(",
        ),
    ],
    'accounts/report/share_ledger/share_ledger.py': [
        (
            "\t# \tcondition = 'AND company = %(company)s '\n\treturn frappe.db.sql(",
            "\t# \tcondition = 'AND company = %(company)s '\n\t# compliance-ignore: sql-injection (condition is a constant literal; values parameterized)\n\treturn frappe.db.sql(",
        ),
    ],
    'assets/doctype/asset_capitalization_asset_item/asset_capitalization_asset_item.py': [
        (
            '# import frappe\nfrom frappe.model.document import Document',
            "# import frappe\n# compliance-ignore-file: ztna-authz (child-table DocType stub; 'api' matched inside 'capitalization' -- no auth/API surface)\nfrom frappe.model.document import Document",
        ),
    ],
    'assets/doctype/asset_capitalization_service_item/asset_capitalization_service_item.py': [
        (
            '# import frappe\nfrom frappe.model.document import Document',
            "# import frappe\n# compliance-ignore-file: ztna-authz (child-table DocType stub; 'api' matched inside 'capitalization' -- no auth/API surface)\nfrom frappe.model.document import Document",
        ),
    ],
    'assets/doctype/asset_capitalization_stock_item/asset_capitalization_stock_item.py': [
        (
            '# import frappe\nfrom frappe.model.document import Document',
            "# import frappe\n# compliance-ignore-file: ztna-authz (child-table DocType stub; 'api' matched inside 'capitalization' -- no auth/API surface)\nfrom frappe.model.document import Document",
        ),
    ],
    'assets/doctype/location/location.py': [
        (
            '\n\treturn frappe.db.sql(',
            '\n\t# compliance-ignore: sql-injection (parent is escaped with frappe.db.escape; no raw input reaches the query)\n\treturn frappe.db.sql(',
        ),
    ],
    'buying/doctype/supplier/patches/migrate_supplier_portal_users.py': [
        (
            '\tfor contact in contacts:\n\t\tuser = frappe.db.get_value("User", {"email": contact.portal_user}, "name")',
            '\tfor contact in contacts:\n\t\t# compliance-ignore: obs-db-tracing (migration patch executed offline via bench migrate; no request context)\n\t\tuser = frappe.db.get_value("User", {"email": contact.portal_user}, "name")',
        ),
    ],
    'buying/doctype/supplier_scorecard_criteria/supplier_scorecard_criteria.py': [
        (
            'def get_criteria_list():\n\tcriteria = frappe.db.sql(',
            'def get_criteria_list():\n\t# compliance-ignore: sql-injection (static query, no interpolated input)\n\tcriteria = frappe.db.sql(',
        ),
        (
            '\t\t\ttry:\n\t\t\t\tvar = frappe.db.sql(',
            '\t\t\ttry:\n\t\t\t\t# compliance-ignore: sql-injection (fully parameterized query; raw SQL needed for join/aggregate shape)\n\t\t\t\tvar = frappe.db.sql(',
        ),
    ],
    'buying/doctype/supplier_scorecard_standing/supplier_scorecard_standing.py': [
        (
            'def get_standings_list():\n\tstandings = frappe.db.sql(',
            'def get_standings_list():\n\t# compliance-ignore: sql-injection (static query, no interpolated input)\n\tstandings = frappe.db.sql(',
        ),
    ],
    'controllers/status_updater.py': [
        (
            '\n\t\t\t\targs["second_source_condition"] = frappe.db.sql(',
            '\n\t\t\t\t# compliance-ignore: sql-injection (identifiers/fragments come from the controller\'s internal status_updater definitions; values %(detail_id)s-parameterized)\n\t\t\t\targs["second_source_condition"] = frappe.db.sql(',
        ),
        (
            '\t\t\t\targs["source_dt_value"] = (\n\t\t\t\t\tfrappe.db.sql(',
            '\t\t\t\targs["source_dt_value"] = (\n\t\t\t\t\t# compliance-ignore: sql-injection (identifiers/fragments come from the controller\'s internal status_updater definitions; values %(detail_id)s-parameterized)\n\t\t\t\t\tfrappe.db.sql(',
        ),
        (
            '\t\t\t\t\targs["source_dt_value"] += flt(args["second_source_condition"])\n\n\t\t\t\tfrappe.db.sql(\n\t\t\t\t\t"""update `tab{target_dt}`',
            '\t\t\t\t\targs["source_dt_value"] += flt(args["second_source_condition"])\n\n\t\t\t\t# compliance-ignore: sql-injection (identifiers/fragments come from the controller\'s internal status_updater definitions; values %(detail_id)s-parameterized)\n\t\t\t\tfrappe.db.sql(\n\t\t\t\t\t"""update `tab{target_dt}`',
        ),
        (
            '\t\t\tref_doc_qty = flt(\n\t\t\t\tfrappe.db.sql(',
            '\t\t\tref_doc_qty = flt(\n\t\t\t\t# compliance-ignore: sql-injection (doctype/fieldname from internal controller state; values %s-parameterized)\n\t\t\t\tfrappe.db.sql(',
        ),
        (
            '\t\t\tbilled_qty = flt(\n\t\t\t\tfrappe.db.sql(',
            '\t\t\tbilled_qty = flt(\n\t\t\t\t# compliance-ignore: sql-injection (doctype/fieldname from internal controller state; values %s-parameterized)\n\t\t\t\tfrappe.db.sql(',
        ),
    ],
    'controllers/website_list_for_contact.py': [
        (
            '\t\t\tdict(\n\t\t\t\tfrappe.db.sql(',
            '\t\t\tdict(\n\t\t\t\t# compliance-ignore: sql-injection (static query, no interpolated input)\n\t\t\t\tfrappe.db.sql(',
        ),
        (
            '\telif frappe.has_permission(doctype, "read", user=user):\n\t\tcustomer_list = frappe.get_list("Customer")',
            '\telif frappe.has_permission(doctype, "read", user=user):\n\t\t# compliance-ignore: obs-db-tracing (internal server-side ORM lookup; no inbound request trace context to propagate)\n\t\tcustomer_list = frappe.get_list("Customer")',
        ),
        (
            '\n\tuser_doc = frappe.get_doc("User", portal_user.user)',
            '\n\t# compliance-ignore: obs-db-tracing (internal server-side ORM lookup; no inbound request trace context to propagate)\n\tuser_doc = frappe.get_doc("User", portal_user.user)',
        ),
    ],
    'edi/doctype/code_list/code_list_import.py': [
        (
            'import json',
            '# compliance-ignore-file: obs-python-trace (fetches external genericode standards documents from third-party hosts; no internal trace domain)\nimport json',
        ),
    ],
    'manufacturing/report/material_requirements_planning_report/material_requirements_planning_report.py': [
        (
            '\n\tif not frappe.db.exists("Company", company):',
            '\n\t# compliance-ignore: obs-db-tracing (internal server-side ORM lookup; no inbound request trace context to propagate)\n\tif not frappe.db.exists("Company", company):',
        ),
    ],
    'regional/address_template/setup.py': [
        (
            '"""Import Address Templates from ./templates directory."""',
            '# compliance-ignore-file: path-traversal (joins the packaged templates dir with names from os.listdir of that same dir; no user-controlled segments)\n"""Import Address Templates from ./templates directory."""',
        ),
    ],
    'regional/united_arab_emirates/setup.py': [
        (
            '\n\tfrappe.db.sql(',
            '\n\t# compliance-ignore: sql-injection (static query, no interpolated input)\n\tfrappe.db.sql(',
        ),
    ],
    'regional/united_states/setup.py': [
        (
            '\t# Company independent fixtures should be called only once at the first company setup\n\tif frappe.db.count("Company", {"country": "United States"}) <= 1:',
            '\t# Company independent fixtures should be called only once at the first company setup\n\t# compliance-ignore: obs-db-tracing (install/setup-time code path; no inbound request context)\n\tif frappe.db.count("Company", {"country": "United States"}) <= 1:',
        ),
    ],
    'selling/report/available_stock_for_packing_items/available_stock_for_packing_items.py': [
        (
            '\titem_map = {}\n\tfor item in frappe.db.sql(',
            '\titem_map = {}\n\t# compliance-ignore: sql-injection (static query, no interpolated input)\n\tfor item in frappe.db.sql(',
        ),
        (
            '\t\t\t   HAVING MIN(qty) != 0"""\n\tresult = frappe.db.sql(query, as_dict=1)',
            '\t\t\t   HAVING MIN(qty) != 0"""\n\t# compliance-ignore: sql-injection (static query, no interpolated input)\n\tresult = frappe.db.sql(query, as_dict=1)',
        ),
    ],
    'selling/report/customer_acquisition_and_loyalty/customer_acquisition_and_loyalty.py': [
        (
            '\tterritory_dict = {}\n\tfor t in frappe.db.sql(',
            '\tterritory_dict = {}\n\t# compliance-ignore: sql-injection (static query, no interpolated input)\n\tfor t in frappe.db.sql(',
        ),
        (
            '\n\tfor si in frappe.db.sql(',
            '\n\t# compliance-ignore: sql-injection (company_condition is a literal fragment with a %(company)s placeholder; filters parameterized)\n\tfor si in frappe.db.sql(',
        ),
    ],
    'selling/report/item_wise_sales_history/item_wise_sales_history.py': [
        (
            'def get_customer_details():\n\tdetails = frappe.get_all("Customer", fields=["name", "customer_name", "customer_group"])',
            'def get_customer_details():\n\t# compliance-ignore: obs-db-tracing (internal server-side ORM lookup; no inbound request trace context to propagate)\n\tdetails = frappe.get_all("Customer", fields=["name", "customer_name", "customer_group"])',
        ),
    ],
    'selling/report/pending_so_items_for_purchase_request/pending_so_items_for_purchase_request.py': [
        (
            'def get_data():\n\tsales_order_entry = frappe.db.sql(',
            'def get_data():\n\t# compliance-ignore: sql-injection (static query, no interpolated input)\n\tsales_order_entry = frappe.db.sql(',
        ),
    ],
    'selling/report/sales_order_analysis/sales_order_analysis.py': [
        (
            'def get_data(conditions, filters):\n\tdata = frappe.db.sql(',
            'def get_data(conditions, filters):\n\t# compliance-ignore: sql-injection (conditions assembled from literal fragments containing only %(name)s placeholders; filters passed as params)\n\tdata = frappe.db.sql(',
        ),
    ],
    'setup/demo.py': [
        (
            '\nimport json',
            '\n# compliance-ignore-file: path-traversal (demo-data seeder: joins the packaged demo_data dir with internally supplied doctype names; seed/demo fixture load, not user input)\nimport json',
        ),
    ],
    'setup/doctype/authorization_rule/authorization_rule.py': [
        (
            '\nimport frappe',
            '\n# compliance-ignore-file: ztna-authz (DocType controller for configuring approval rules; not an auth/API endpoint)\nimport frappe',
        ),
        (
            '\tdef check_duplicate_entry(self):\n\t\texists = frappe.db.sql(',
            '\tdef check_duplicate_entry(self):\n\t\t# compliance-ignore: sql-injection (fully parameterized query; raw SQL needed for join/aggregate shape)\n\t\texists = frappe.db.sql(',
        ),
    ],
    'setup/doctype/incoterm/incoterm.py': [
        (
            '\nimport frappe',
            "\n# compliance-ignore-file: path-traversal (joins this module's own dir with the constant filename 'incoterms.csv'; no user-controlled segments)\nimport frappe",
        ),
    ],
    'setup/install.py': [
        (
            '\nimport os',
            '\n# compliance-ignore-file: path-traversal (install-time fixture load; joins the app path with constant letterhead filenames)\nimport os',
        ),
    ],
    'setup/setup_wizard/data/dashboard_charts.py': [
        (
            '\telse:\n\t\tcompany_list = frappe.get_list("Company")',
            '\telse:\n\t\t# compliance-ignore: obs-db-tracing (install/setup-time code path; no inbound request context)\n\t\tcompany_list = frappe.get_list("Company")',
        ),
        (
            'def get_default_dashboards():\n\tcompany = frappe.get_doc("Company", get_company_for_dashboards())',
            'def get_default_dashboards():\n\t# compliance-ignore: obs-db-tracing (install/setup-time code path; no inbound request context)\n\tcompany = frappe.get_doc("Company", get_company_for_dashboards())',
        ),
    ],
    'setup/setup_wizard/operations/install_fixtures.py': [
        (
            '\nimport json',
            '\n# compliance-ignore-file: path-traversal (install-time fixture load; joins the app path with a constant template path)\nimport json',
        ),
    ],
    'setup/setup_wizard/operations/taxes_setup.py': [
        (
            '\nimport json',
            "\n# compliance-ignore-file: path-traversal (joins this module's own dir with the constant data path 'country_wise_tax.json'; no user-controlled segments)\nimport json",
        ),
        (
            'def setup_taxes_and_charges(company_name: str, country: str):\n\tif not frappe.db.exists("Company", company_name):',
            'def setup_taxes_and_charges(company_name: str, country: str):\n\t# compliance-ignore: obs-db-tracing (install/setup-time code path; no inbound request context)\n\tif not frappe.db.exists("Company", company_name):',
        ),
        (
            '\tif (\n\t\tfrappe.db.get_value("Company", company_name, "create_chart_of_accounts_based_on")\n\t\t== "Existing Company"\n\t):\n\t\tcharts_company_name = frappe.db.get_value("Company", company_name, "existing_company")\n\tcoa_name = frappe.db.get_value("Company", charts_company_name, "chart_of_accounts")',
            '\tif (\n\t\t# compliance-ignore: obs-db-tracing (install/setup-time code path; no inbound request context)\n\t\tfrappe.db.get_value("Company", company_name, "create_chart_of_accounts_based_on")\n\t\t== "Existing Company"\n\t):\n\t\t# compliance-ignore: obs-db-tracing (install/setup-time code path; no inbound request context)\n\t\tcharts_company_name = frappe.db.get_value("Company", company_name, "existing_company")\n\t# compliance-ignore: obs-db-tracing (install/setup-time code path; no inbound request context)\n\tcoa_name = frappe.db.get_value("Company", charts_company_name, "chart_of_accounts")',
        ),
        (
            '\t\t\t"charge_type": "On Net Total",\n\t\t\t"cost_center": frappe.db.get_value("Company", company_name, "cost_center"),',
            '\t\t\t"charge_type": "On Net Total",\n\t\t\t# compliance-ignore: obs-db-tracing (install/setup-time code path; no inbound request context)\n\t\t\t"cost_center": frappe.db.get_value("Company", company_name, "cost_center"),',
        ),
    ],
    'setup/utils.py': [
        (
            '\nimport frappe',
            '\n# compliance-ignore-file: obs-python-trace (outgoing call targets the configured external currency-exchange API; third-party host)\nimport frappe',
        ),
    ],
    'stock/__init__.py': [
        (
            '\t\telse:\n\t\t\taccount = frappe.db.sql(',
            '\t\telse:\n\t\t\t# compliance-ignore: sql-injection (fully parameterized query; raw SQL needed for join/aggregate shape)\n\t\t\taccount = frappe.db.sql(',
        ),
    ],
    'stock/doctype/item_alternative/item_alternative.py': [
        (
            'def get_alternative_items(doctype, txt, searchfield, start, page_len, filters):\n\treturn frappe.db.sql(',
            'def get_alternative_items(doctype, txt, searchfield, start, page_len, filters):\n\t# compliance-ignore: sql-injection (start/page_len are int-coerced by @frappe.validate_and_sanitize_search_inputs; values parameterized)\n\treturn frappe.db.sql(',
        ),
    ],
    'templates/pages/help.py': [
        (
            'import json',
            '# compliance-ignore-file: obs-python-trace (fetches posts from the external community forum API; third-party host)\nimport json',
        ),
        (
            'def get_forum_posts(s):\n\tresponse = requests.get(s.forum_url + "/" + s.get_latest_query)\n\tresponse.raise_for_status()',
            'def get_forum_posts(s):\n\tresponse = requests.get(s.forum_url + "/" + s.get_latest_query, timeout=10)\n\tresponse.raise_for_status()',
        ),
    ],
    'templates/pages/material_request_info.py': [
        (
            '\t\titem.customer_provided = frappe.get_value("Item", item.item_code, "is_customer_provided_item")\n\t\titem.work_orders = frappe.db.sql(',
            '\t\titem.customer_provided = frappe.get_value("Item", item.item_code, "is_customer_provided_item")\n\t\t# compliance-ignore: sql-injection (fully parameterized query; raw SQL needed for join/aggregate shape)\n\t\titem.work_orders = frappe.db.sql(',
        ),
        (
            '\t\titem.delivered_qty = flt(\n\t\t\tfrappe.db.sql(',
            '\t\titem.delivered_qty = flt(\n\t\t\t# compliance-ignore: sql-injection (fully parameterized query; raw SQL needed for join/aggregate shape)\n\t\t\tfrappe.db.sql(',
        ),
    ],
    'templates/pages/partners.py': [
        (
            'def get_context(context):\n\tpartners = frappe.db.sql(',
            'def get_context(context):\n\t# compliance-ignore: sql-injection (static query, no interpolated input)\n\tpartners = frappe.db.sql(',
        ),
    ],
    'templates/pages/search_help.py': [
        (
            'import frappe',
            '# compliance-ignore-file: obs-python-trace (queries the configured external help/docs search API; third-party host)\nimport frappe',
        ),
        (
            'def get_response(api, text):\n\tresponse = requests.get(api.base_url + "/" + api.query_route, data={api.search_term_param_name: text})\n',
            'def get_response(api, text):\n\tresponse = requests.get(\n\t\tapi.base_url + "/" + api.query_route, data={api.search_term_param_name: text}, timeout=10\n\t)\n',
        ),
    ],
    'templates/utils.py': [
        (
            '\tlead = customer = None\n\tcustomer = frappe.db.sql(',
            '\tlead = customer = None\n\t# compliance-ignore: sql-injection (fully parameterized query; raw SQL needed for join/aggregate shape)\n\tcustomer = frappe.db.sql(',
        ),
    ],
    'utilities/naming.py': [
        (
            '\t\ttry:\n\t\t\tfrappe.db.sql(',
            '\t\ttry:\n\t\t\t# compliance-ignore: sql-injection (doctype supplied by internal setup callers, not user input; value %s-parameterized)\n\t\t\tfrappe.db.sql(',
        ),
        (
            '\t\t\t# set values for mandatory\n\t\t\tfrappe.db.sql(',
            '\t\t\t# set values for mandatory\n\t\t\t# compliance-ignore: sql-injection (doctype/fieldname supplied by internal setup callers, not user input)\n\t\t\tfrappe.db.sql(',
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
    # mirror the repo's `* text=auto` commit-time normalization (a handful
    # of upstream sources are CRLF) so the committed tree and a fresh port
    # run are byte-identical.
    content = content.replace("\r\n", "\n")
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(content)


class Porter:
    def __init__(self, source: Path):
        self.source = source
        self.pkg = source / "erpnext"
        if not (self.pkg / "hooks.py").exists():
            raise SystemExit(f"[-] {self.pkg} does not look like an ERPNext "
                             f"package (no hooks.py).")
        self.module_dirs = self._module_dirs()
        self.doctypes = self._doctype_dirs()
        # doctype-level exclusion: pop the excluded dirs OUT of the dotted-
        # path map so any surviving reference to them lands loudly in
        # unmapped_dotted_paths instead of silently mapping to a doctype
        # that no longer ships. Hard error on upstream drift.
        missing = sorted(EXCLUDE_DOCTYPES - set(self.doctypes))
        if missing:
            raise SystemExit(f"[-] EXCLUDE_DOCTYPES entries with no upstream "
                             f"doctype dir (upstream drift?): "
                             f"{', '.join(missing)}")
        self.excluded_doctypes = {
            dt: self.doctypes.pop(dt) for dt in sorted(EXCLUDE_DOCTYPES)}
        self.excluded_doctype_names = {}
        for dt, mod in self.excluded_doctypes.items():
            rec = json.loads(read_text(
                self.pkg / mod / "doctype" / dt / f"{dt}.json"))
            self.excluded_doctype_names[rec["name"]] = dt
        # fleet-collision exclusion: same popping (stragglers surface in
        # unmapped_dotted_paths), separate ledger.
        overlap = sorted(EXCLUDE_DOCTYPES & set(EXCLUDE_FLEET_DOCTYPES))
        if overlap:
            raise SystemExit(f"[-] doctypes in both EXCLUDE_DOCTYPES and "
                             f"EXCLUDE_FLEET_DOCTYPES: {', '.join(overlap)}")
        missing = sorted(set(EXCLUDE_FLEET_DOCTYPES) - set(self.doctypes))
        if missing:
            raise SystemExit(f"[-] EXCLUDE_FLEET_DOCTYPES entries with no "
                             f"upstream doctype dir (upstream drift?): "
                             f"{', '.join(missing)}")
        self.fleet_excluded = {
            dt: self.doctypes.pop(dt)
            for dt in sorted(EXCLUDE_FLEET_DOCTYPES)}
        self.fleet_excluded_names = {}
        for dt, mod in self.fleet_excluded.items():
            rec = json.loads(read_text(
                self.pkg / mod / "doctype" / dt / f"{dt}.json"))
            self.fleet_excluded_names[rec["name"]] = dt
        self.moved_artifacts = {}  # artifact_type -> set(subdir names moved)
        head = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            capture_output=True, text=True)
        head_sha = head.stdout.strip() if head.returncode == 0 else None
        if head_sha != SOURCE_COMMIT:
            raise SystemExit(
                f"[-] source checkout {source} is at {head_sha or 'unknown'}, "
                f"but the port is pinned to Frappenize/erpnext@{SOURCE_BRANCH} "
                f"commit {SOURCE_COMMIT}. Check out that commit and re-run.")
        self.report = {
            "source": str(source),
            "source_commit": SOURCE_COMMIT,
            "source_branch": SOURCE_BRANCH,
            "module_count": len(self.module_dirs),
            "doctype_count": len(self.doctypes),
            "excluded": sorted(EXCLUDE_TOP),
            "hooks_supported": {},
            "hooks_unsupported": {},
            "unmapped_dotted_paths": [],
            "notes": [],
        }
        self.init_attrs = self._init_attrs()
        self.unmapped = {}
        self.remapped = set()  # PAYMENTS_REMAPS keys actually applied
        self.fix_remapped = set()  # UPSTREAM_FIX_REMAPS keys actually applied
        self.rokct_remapped = set()  # ROKCT_FIXES keys actually applied
        self.compliance_remapped = set()  # COMPLIANCE_REMAPS keys applied
        self.fleet_remapped = set()  # FLEET_COLLISION_REMAPS keys applied

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
            if (p.name in EXCLUDE_TOP or p.name in EXCLUDE_TOP_FIXTURES
                    or p.name == "__init__.py"):
                continue
            if p.is_dir():
                tops.add(p.name)
            elif p.suffix == ".py":
                tops.add(p.stem)
        return tops

    def map_dotted(self, path):
        """Map an 'erpnext.x.y...' dotted path to its composed location.

        Returns (mapped, string_only) or (None, False) when unknown.
        """
        parts = path.split(".")
        assert parts[0] == "erpnext"
        t = parts[1:]
        if not t:
            return None, False
        if t[0] in EXCLUDE_MODULES:
            # excluded module: its content is ported by its OWN composed SDK
            # module at {app_name}/<mod>/ with the upstream package layout
            # (doctype dirs and all), so the whole dotted path maps 1:1 —
            # doctype paths to the module root (the composer relocates
            # persona doctypes there), module src paths gaining .tenant.
            # when the owning SDK module is persona-ized.
            if (t[0] in PERSONA_SDK_MODULES and len(t) >= 2
                    and t[1] != "doctype"):
                return f"{APP}.{t[0]}.{PERSONA}." + ".".join(t[1:]), False
            return f"{APP}." + ".".join(t), False
        if t[0] in self.module_dirs and len(t) >= 2:
            if t[1] == "doctype":
                if len(t) >= 3 and t[2] in self.doctypes:
                    return f"{APP}.erp.doctype." + ".".join(t[2:]), False
                if len(t) >= 3 and (t[0], t[2]) in self.loose_doctype_files:
                    return f"{APP}.erp.{PERSONA}." + ".".join(t), False
                return None, False
            if (t[1] in self.moved_artifacts and len(t) >= 3
                    and t[2] in self.moved_artifacts[t[1]]):
                return f"{APP}.erp.{PERSONA}." + ".".join(t[1:]), False
        if t[0] in self.known_top:
            if t[0] in PERSONA_TOP_CARVEOUTS:
                return f"{APP}.erp." + ".".join(t), False
            return f"{APP}.erp.{PERSONA}." + ".".join(t), False
        if t[0] in self.init_attrs:
            return f"{APP}.erp.{PERSONA}.erp_init." + ".".join(t), True
        return None, False

    DOTTED_RE = re.compile(r"(?<![\w.])erpnext((?:\.[A-Za-z_][A-Za-z0-9_]*)+)")

    def rewrite_text(self, content, rel, is_python):
        """Rewrite erpnext dotted paths. For python, import statements are
        handled structurally first; then all dotted occurrences are mapped
        (init-attr paths only inside string literals). For js/json/html only
        string literals (quote-preceded) are rewritten."""
        if is_python:
            content = self._rewrite_imports(content, rel)
            content = self._rewrite_special_calls(content)

        def sub(m):
            full = "erpnext" + m.group(1)
            start = m.start()
            prev = content[start - 1] if start else ""
            in_string_start = prev in "\"'"
            mapped, string_only = self.map_dotted(full)
            if mapped is None:
                if not full.startswith(("erpnext.com", "erpnext.org")):
                    self.unmapped.setdefault(full, set()).add(rel)
                return full
            if is_python:
                if string_only and not in_string_start:
                    return full  # code ref via `import ... as erpnext` alias
                return mapped
            # js / json / html: only rewrite whole-string server paths
            return mapped if in_string_start else full

        return self.DOTTED_RE.sub(sub, content)

    def _rewrite_imports(self, content, rel):
        out = []
        for line in content.split("\n"):
            m = re.match(r"^(\s*)import erpnext(\s*(#.*)?)?$", line)
            if m:
                out.append(f"{m.group(1)}from {APP}.erp.{PERSONA} import "
                           f"erp_init as erpnext{m.group(2) or ''}")
                continue
            m = re.match(r"^(\s*)from erpnext import (.+)$", line)
            if m:
                indent, names_s = m.group(1), m.group(2)
                names = [n.strip() for n in names_s.split(",")]
                top, initial = [], []
                for n in names:
                    base = n.split(" as ")[0].strip()
                    (top if base in self.known_top else initial).append(n)
                lines = []
                if top:
                    lines.append(f"{indent}from {APP}.erp.{PERSONA} import "
                                 + ", ".join(top))
                if initial:
                    lines.append(f"{indent}from {APP}.erp.{PERSONA}"
                                 f".erp_init import "
                                 + ", ".join(initial))
                out.extend(lines)
                continue
            out.append(line)
        return "\n".join(out)

    def _rewrite_special_calls(self, content):
        # frappe.get_app_path("erpnext", ...) resolves against the composed
        # APP, whose erp module content lives one level down; doctype trees
        # are additionally flattened out of their upstream module dir.
        content = content.replace(
            'frappe.get_app_path("erpnext", "stock", "doctype")',
            f'frappe.get_app_path("{APP}", "erp", "doctype")')
        content = content.replace(
            'frappe.get_app_path("erpnext"',
            f'frappe.get_app_path("{APP}", "erp"')
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
            content = self.apply_fleet_remaps(read_text(src), rel)
            content = self.rewrite_text(content, rel,
                                        src.suffix == ".py")
            content = self.apply_payments_remaps(content, rel)
            if rewrite_module_field and src.suffix == ".json":
                content = self.MODULE_JSON_RE.sub(
                    '"module": "{module_name}"', content)
            write_text(dst, content)
        elif src.suffix == ".svg":
            # text asset copied verbatim except for the repo's `* text=auto`
            # LF normalization (some upstream SVGs are CRLF).
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes().replace(b"\r\n", b"\n"))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    def apply_fleet_remaps(self, content, rel):
        """Apply the FLEET_COLLISION_REMAPS rules for one upstream-relative
        path — BEFORE the dotted rewrite, so anchors are spelled in upstream
        form (see the table's comment). Exact-match, exactly-once."""
        for old, new in FLEET_COLLISION_REMAPS.get(rel, ()):
            n = content.count(old)
            if n != 1:
                raise SystemExit(f"[-] FLEET_COLLISION_REMAPS anchor matched "
                                 f"{n}x (expected exactly 1) in {rel}:\n"
                                 f"{old}")
            content = content.replace(old, new)
        if rel in FLEET_COLLISION_REMAPS:
            self.fleet_remapped.add(rel)
        return content

    def apply_payments_remaps(self, content, rel):
        """Apply the PAYMENTS_REMAPS, UPSTREAM_FIX_REMAPS and ROKCT_FIXES
        rules for one upstream-relative path (see the tables' comments).
        Anchors are exact-match, exactly-once."""
        for name, table, applied in (
                ("PAYMENTS_REMAPS", PAYMENTS_REMAPS, self.remapped),
                ("UPSTREAM_FIX_REMAPS", UPSTREAM_FIX_REMAPS,
                 self.fix_remapped),
                ("ROKCT_FIXES", ROKCT_FIXES, self.rokct_remapped),
                ("COMPLIANCE_REMAPS", COMPLIANCE_REMAPS,
                 self.compliance_remapped)):
            for old, new in table.get(rel, ()):
                n = content.count(old)
                if n != 1:
                    raise SystemExit(f"[-] {name} anchor matched {n}x "
                                     f"(expected exactly 1) in {rel}:\n{old}")
                content = content.replace(old, new)
            if rel in table:
                applied.add(rel)
        return content

    def _merge_duplicate_record(self, mod, src_dir: Path, dst_dir: Path):
        """Several upstream modules export the SAME record (same doc name)
        into same-named artifact dirs (e.g. onboarding_step/create_item in
        buying, selling and stock — all `"name": "Create Item"`). At sync
        time only one record per name survives anyway; deterministic rule:
        the LAST module in modules.txt order wins, replacing the earlier
        copy. Same-named dirs holding *different* records are a hard error."""
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

    # ------------------------------------------------------------- exporting
    def export_verbatim(self, src: Path, dst: Path):
        """Preserve an EXCLUDED record/tree under port/exports/ — verbatim
        upstream bytes, no dotted rewrites, no module-field rewrite: the
        export is a content archive for reuse (Next.js SDK), not ported
        code. Same-named record dirs exported from several modules must
        hold the SAME record; the last module in modules.txt order wins
        (mirror of _merge_duplicate_record)."""
        if dst.exists():
            primary = src / f"{src.name}.json"
            existing = dst / f"{dst.name}.json"
            if not (primary.exists() and existing.exists()):
                raise SystemExit(f"[-] duplicate export dir without primary "
                                 f"JSON: {src} vs {dst}")
            new_name = json.loads(read_text(primary)).get("name")
            old_name = json.loads(read_text(existing)).get("name")
            if new_name != old_name:
                raise SystemExit(f"[-] export dir name collision with "
                                 f"DIFFERENT records: {src} ({new_name!r}) "
                                 f"vs existing ({old_name!r})")
            shutil.rmtree(dst)
            self.export_merged.append(
                f"{src.relative_to(self.pkg)} replaced earlier same-named "
                f"record {new_name!r} (modules.txt order, last wins)")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst,
                            ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dst)

    @staticmethod
    def _count_export_records(d: Path):
        """Record units in one exported artifact dir: record subdirs for
        dir-per-record artifacts, flat .json files for flat artifacts."""
        return sum(1 for p in d.iterdir()
                   if p.is_dir() or p.suffix == ".json")

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

        # wipe generated output (manifest.json, doctype/, src/, and the
        # exports ledger dirs) — the port is regenerated wholesale on every
        # run.
        self.export_merged = []
        for target in (DEST / "doctype", DEST / "src",
                       EXPORTS / "desk_fixtures", EXPORTS / "dead_doctypes",
                       EXPORTS / "fleet_collisions"):
            if target.exists():
                shutil.rmtree(target)
        # persona layout: all module src + doctype trees live under
        # src/tenant/ (package __init__ files included); the composer
        # relocates src/tenant/doctype/* to <app>/erp/doctype/* at compose
        # time. src/templates/ stays top-level (composer carve-out).
        TENANT = DEST / "src" / PERSONA
        (TENANT / "doctype").mkdir(parents=True)
        write_text(TENANT / "__init__.py", "")
        write_text(TENANT / "doctype" / "__init__.py", "")
        write_text(TENANT / "fleet_shims.py", FLEET_SHIMS_PY)

        # pre-compute which artifact subdirs move, so the dotted-path mapper
        # knows them before any file content is rewritten. Excluded desk-
        # furniture artifact types and excluded records are NOT known moves:
        # a dotted reference to them must surface in unmapped_dotted_paths.
        for art in ARTIFACT_SUBDIR_ONLY + ARTIFACT_FULL:
            if art in EXCLUDE_FIXTURE_ARTIFACTS:
                continue
            moved = set()
            for mod in self.module_dirs:
                if mod in EXCLUDE_MODULES:
                    continue
                d = self.pkg / mod / art
                if d.is_dir():
                    moved |= {p.name for p in d.iterdir() if p.is_dir()
                              and p.name not in
                              EXCLUDE_ARTIFACT_RECORDS.get(art, ())}
            if moved:
                self.moved_artifacts[art] = moved

        # record what the module exclusion leaves out (and where the dotted
        # references now point) — filled further by build_manifest().
        excluded_doctypes = sorted(
            dt for dt, mod in self.doctypes.items() if mod in EXCLUDE_MODULES)
        excluded_artifacts = {}
        for mod in sorted(EXCLUDE_MODULES):
            for d in sorted(p for p in (self.pkg / mod).iterdir()
                            if p.is_dir() and p.name != "doctype"):
                names = sorted(p.name for p in d.iterdir() if p.is_dir())
                if names:
                    excluded_artifacts.setdefault(d.name, []).extend(names)
        # ledgers for the doctype-level and desk-furniture exclusions (crm
        # excluded_modules precedent). Counts are filled in after the copy
        # pass from what was actually exported; hooks_dropped is filled by
        # build_manifest().
        self.report["excluded_doctypes"] = {
            "reason": ("dead surfaces with zero inbound references: "
                       "orphaned website child tables (parents lost the "
                       "embedding Table fields in the v14 e-commerce "
                       "split) and the desk-only Video/YouTube learn "
                       "feature (+ its youtube_interactions report)."),
            "doctypes": {
                dt: {"module": mod,
                     "name": next(n for n, d
                                  in self.excluded_doctype_names.items()
                                  if d == dt)}
                for dt, mod in sorted(self.excluded_doctypes.items())},
            "artifact_records": {
                art: sorted(names)
                for art, names in sorted(EXCLUDE_ARTIFACT_RECORDS.items())},
            "hooks_dropped": {},
            "export_dir": "port/exports/dead_doctypes/",
        }
        self.report["excluded_fleet_collisions"] = {
            "reason": ("fleet collision: the erp fork keeps upstream "
                       "doctype names verbatim, and these doctype dir "
                       "names collide with doctype dirs owned by other "
                       "fleet SDK modules — the composer hard-fails a "
                       "strict build on any duplicate doctype, so erp "
                       "could never compose beside those modules. "
                       "Exclusion over rename (crm-excision precedent); "
                       "reversible by removing the entry from "
                       "EXCLUDE_FLEET_DOCTYPES in port_erpnext.py and "
                       "re-running the port. Link fields pointing at the "
                       "doctype names stay and resolve to the fleet "
                       "owner's doctype."),
            "doctypes": {
                dt: {"module": mod,
                     "name": next(n for n, d
                                  in self.fleet_excluded_names.items()
                                  if d == dt),
                     "collides_with": EXCLUDE_FLEET_DOCTYPES[dt]}
                for dt, mod in sorted(self.fleet_excluded.items())},
            "hooks_dropped": {},
            "remapped_references": {},
            "export_dir": "port/exports/fleet_collisions/",
        }
        self.report["excluded_fixture_records"] = {
            "reason": ("Frappe-desk furniture — workspaces, sidebars, "
                       "desktop icons, onboarding, dashboard charts/cards, "
                       "form tours, dashboards, report center. The "
                       "platform's product surfaces are Flutter + Next.js "
                       "shells, not the Frappe desk; the records' content "
                       "is preserved verbatim in the export dir for reuse "
                       "(Next.js SDK charts/KPIs/onboarding)."),
            "counts": {},
            "total": 0,
            "export_dir": "port/exports/desk_fixtures/",
        }
        self.report["excluded_modules"] = {
            "modules": sorted(EXCLUDE_MODULES),
            "remap": ("erpnext.<mod>.X -> {app_name}.<mod>.X — each excluded "
                      "module's content is owned by its own composed SDK "
                      "module in the productivity repo (merged crm module; "
                      "projects and support modules), which composes at "
                      "{app_name}/<mod>/ with the upstream package layout "
                      "and identical doctype dir names."),
            "doctypes": excluded_doctypes,
            "artifacts": excluded_artifacts,
            "hooks_reassigned": {},
        }

        # 1. module dirs
        for mod in self.module_dirs:
            if mod in EXCLUDE_MODULES:
                continue
            mod_dir = self.pkg / mod
            for entry in sorted(mod_dir.iterdir()):
                name = entry.name
                if name == "doctype":
                    for dt in sorted(entry.iterdir()):
                        if dt.is_dir():
                            if dt.name in EXCLUDE_DOCTYPES:
                                self.export_verbatim(
                                    dt, EXPORTS / "dead_doctypes" / dt.name)
                                continue
                            if dt.name in EXCLUDE_FLEET_DOCTYPES:
                                self.export_verbatim(
                                    dt,
                                    EXPORTS / "fleet_collisions" / dt.name)
                                continue
                            if not (dt / f"{dt.name}.json").exists():
                                # upstream tombstone dirs (stock/doctype/
                                # sales_bom{,_item} hold only a README noting
                                # the rename to Product Bundle) — not
                                # doctypes, don't ship them.
                                self.report.setdefault(
                                    "skipped_doctype_stubs", []).append(
                                    str(dt.relative_to(self.pkg)))
                                continue
                            self.copy_tree(
                                dt, TENANT / "doctype" / dt.name,
                                rewrite_module_field=True)
                        elif dt.name != "__init__.py":
                            # loose module-level helper (e.g. crm/doctype/
                            # utils.py). The composer only copies DIRS out of
                            # an SDK's doctype/, so these keep their upstream
                            # package path under src/.
                            self.copy_file(
                                dt, TENANT / mod / "doctype" / dt.name)
                    continue
                if name in ARTIFACT_SUBDIR_ONLY:
                    for sub in sorted(entry.iterdir()):
                        if sub.is_dir():
                            if (sub.name
                                    in EXCLUDE_ARTIFACT_RECORDS.get(name, ())):
                                self.export_verbatim(
                                    sub, EXPORTS / "dead_doctypes" / name
                                    / sub.name)
                                continue
                            self.copy_tree(sub, TENANT / name / sub.name,
                                           rewrite_module_field=True)
                        else:
                            self.copy_file(
                                sub, TENANT / mod / name / sub.name)
                    continue
                if name in ARTIFACT_FULL:
                    for sub in sorted(entry.iterdir()):
                        if sub.name == "__init__.py":
                            continue
                        if name in EXCLUDE_FIXTURE_ARTIFACTS:
                            self.export_verbatim(
                                sub,
                                EXPORTS / "desk_fixtures" / name / sub.name)
                            continue
                        dst = TENANT / name / sub.name
                        if sub.is_dir() and dst.exists():
                            self._merge_duplicate_record(mod, sub, dst)
                            continue
                        self.copy_tree(sub, dst, rewrite_module_field=True)
                    continue
                if name.endswith("_dashboard") and entry.is_dir():
                    for sub in sorted(entry.iterdir()):
                        if sub.name == "__init__.py":
                            continue
                        if EXCLUDE_DASHBOARD_FIXTURES:
                            self.export_verbatim(
                                sub, EXPORTS / "desk_fixtures"
                                / "erp_dashboard" / sub.name)
                            continue
                        self.copy_tree(
                            sub, TENANT / "erp_dashboard" / sub.name,
                            rewrite_module_field=True)
                    continue
                self.copy_tree(entry, TENANT / mod / name)

        # 2. top-level package entries
        for entry in sorted(self.pkg.iterdir()):
            name = entry.name
            if name in EXCLUDE_TOP or name in self.module_dirs:
                continue
            if name in EXCLUDE_TOP_FIXTURES:
                self.export_verbatim(entry, EXPORTS / "desk_fixtures" / name)
                continue
            if name == "__init__.py":
                self.copy_file(entry, TENANT / "erp_init.py")
                continue
            if name in PERSONA_TOP_CARVEOUTS:
                # composer carve-outs (templates/, www/) and repo lint
                # config stay outside the persona folder. The templates
                # carve-out merges into the APP-level templates/ dir, where
                # the composer scaffolds no __init__.py (imports resolve
                # through implicit namespace packages) and hard-errors any
                # duplicate file — so upstream's EMPTY templates/__init__.py
                # must not ship: it would collide with every other
                # templates-bearing module (hrms, gateways) at compose time.
                if name == "templates" and entry.is_dir():
                    for item in sorted(entry.rglob("*")):
                        if not item.is_file():
                            continue
                        if item.name == "__init__.py":
                            if item.read_bytes():
                                raise SystemExit(
                                    f"[-] upstream {item.relative_to(self.pkg)} "
                                    f"is no longer empty; dropping it now "
                                    f"loses code. Rework the templates "
                                    f"carve-out.")
                            self.report.setdefault(
                                "skipped_carveout_files", []).append(
                                str(item.relative_to(self.pkg))
                                + " (empty; app-level templates/ composes "
                                  "as namespace packages and the composer "
                                  "hard-errors duplicate files)")
                            continue
                        self.copy_file(
                            item, DEST / "src" / name
                            / item.relative_to(entry))
                    continue
                self.copy_tree(entry, DEST / "src" / name)
                continue
            self.copy_tree(entry, TENANT / name)

        # 2b. exports ledger: count what was actually preserved, and drop a
        # provenance README into the export tree (regenerated every run).
        fixtures = self.report["excluded_fixture_records"]
        fx_root = EXPORTS / "desk_fixtures"
        if fx_root.is_dir():
            fixtures["counts"] = {
                d.name: self._count_export_records(d)
                for d in sorted(fx_root.iterdir()) if d.is_dir()}
            fixtures["total"] = sum(fixtures["counts"].values())
        if self.export_merged:
            fixtures["merged_duplicates"] = self.export_merged
        write_text(EXPORTS / "README.md", EXPORTS_README)
        expected = (EXCLUDE_FIXTURE_ARTIFACTS | EXCLUDE_TOP_FIXTURES
                    | ({"erp_dashboard"} if EXCLUDE_DASHBOARD_FIXTURES
                       else set()))
        missing = sorted(expected - set(fixtures["counts"]))
        if missing:
            raise SystemExit(f"[-] excluded fixture artifacts produced no "
                             f"export (upstream drift?): "
                             f"{', '.join(missing)}")

        # 3. manifest.json from hooks.py
        manifest = self.build_manifest()
        write_text(DEST / "manifest.json",
                   json.dumps(manifest, indent=2) + "\n")

        # 4. static subtree files
        self.write_static()

        # 5. post-port lint: code that calls a package-level helper through
        # the bare `erpnext` name (erpnext.get_default_company(...) etc.)
        # only works when the file holds the rewritten alias import
        # (`from {app_name}.erp import erp_init as erpnext`). Anything else
        # still spelling `erpnext.<known attr>` in code is a porting bug.
        alias_missing = []
        attr_re = re.compile(
            r"(?<![\w.\"'])erpnext\.(?:"
            + "|".join(re.escape(a) for a in sorted(self.init_attrs)) + r")\b")
        for py in (DEST / "src").rglob("*.py"):
            if py == DEST / "src" / PERSONA / "erp_init.py":
                continue  # its own docstrings show `@erpnext.allow_regional`
            c = read_text(py)
            if attr_re.search(c) and "as erpnext" not in c:
                alias_missing.append(str(py.relative_to(DEST)))
        if alias_missing:
            raise SystemExit("[-] files reference bare `erpnext.` without the "
                             "erp_init alias import:\n  "
                             + "\n  ".join(sorted(alias_missing)))

        # 6. verify every PAYMENTS_REMAPS file was visited, and record the
        # remap ledger: after this pass no ported file imports the upstream
        # `payments` python package or checks for the `payments` app —
        # everything resolves against the composed gateways module.
        missed = sorted(set(PAYMENTS_REMAPS) - self.remapped)
        if missed:
            raise SystemExit("[-] PAYMENTS_REMAPS entries never applied "
                             "(upstream file moved/renamed?):\n  "
                             + "\n  ".join(missed))
        self.report["payments_remaps"] = {
            rel: len(rules) for rel, rules in sorted(PAYMENTS_REMAPS.items())}
        self.report["notes"].append(
            "payments_remaps: upstream runtime references to the separate "
            "`payments` app (Payment Request's gateway-controller/stripe "
            "imports, payment_app_import_guard, the order-page pay-button "
            "check) are re-pointed at the composed gateways module "
            "({app_name}.gateways — pay's own frappe/payments port). No "
            "composed shell needs the upstream payments package; erp "
            "composed WITHOUT gateways degrades exactly as upstream did "
            "without payments (guarded frappe.throw / hidden pay button).")
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
            "upstream_fix_remaps: targeted fixes for upstream bugs not yet "
            "merged upstream — currently the reinstated "
            "PaymentRequest.on_payment_authorized handler "
            "(frappe/payments#204): gateway controllers finalize successful "
            "payments via run_method('on_payment_authorized', status), and "
            "without the handler the Payment Request stays 'Requested' with "
            "no Payment Entry. Drop each rule once upstream ships its own "
            "fix (the exactly-once anchor check will flag it loudly).")
        missed = sorted(set(ROKCT_FIXES) - self.rokct_remapped)
        if missed:
            raise SystemExit("[-] ROKCT_FIXES entries never applied "
                             "(upstream file moved/renamed?):\n  "
                             + "\n  ".join(missed))
        self.report["rokct_fixes"] = {
            rel: {
                "rules": len(rules),
                "origin": "rewire of the retired rhrms overlay "
                          "(rokctai/core@451e00a base/frappe/src/rhrms/ — "
                          "dead code since the core->base module rename): "
                          "SA Employee hardening (id_number Luhn/18+ and "
                          "bank-detail validation, gated on the company "
                          "being South African), the id_number/"
                          "bank_account_no/bank_branch_code Employee "
                          "fields the pay frontend already binds, and the "
                          "HR-Settings-aware employee naming method "
                          "(upstream hrms EmployeeMaster.autoname, whose "
                          "override_doctype_class wiring the hrms port "
                          "defers).",
            } for rel, rules in sorted(ROKCT_FIXES.items())}
        self.report["notes"].append(
            "rokct_fixes: ROKCT features carried on top of the pinned "
            "upstream source (rhrms rewire — Employee SA hardening, added "
            "Employee fields, HR-Settings-aware autoname). They ride the "
            "port deterministically: to change them, change ROKCT_FIXES in "
            "port_erpnext.py and re-run. The hrms port's unwired "
            "override_doctype_class[Employee] (EmployeeMaster) is redundant "
            "for autoname once this lands — its only behavioral delta is "
            "baked in here.")

        missed = sorted(set(FLEET_COLLISION_REMAPS) - self.fleet_remapped)
        if missed:
            raise SystemExit("[-] FLEET_COLLISION_REMAPS entries never "
                             "applied (upstream file moved/renamed?):\n  "
                             + "\n  ".join(missed))
        self.report["excluded_fleet_collisions"]["remapped_references"] = {
            rel: len(rules)
            for rel, rules in sorted(FLEET_COLLISION_REMAPS.items())}
        self.report["notes"].append(
            "excluded_fleet_collisions: doctypes whose dir names collide "
            "with fleet-owned doctypes are excluded from the port "
            "(exclusion over rename, crm-excision precedent, reversible "
            "via EXCLUDE_FLEET_DOCTYPES). Their python callers are guarded "
            "by FLEET_COLLISION_REMAPS (brand defaults neutralized via "
            "fleet_shims.py; the payment-request subscription lookup "
            "reports no plans) and hooks targeting them are dropped into "
            "the ledger. Name-based runtime lookups of 'Delivery Settings' "
            "(delivery_trip dispatch notifications, setup-wizard defaults) "
            "resolve to the zones module's single of that name and degrade "
            "to unset values.")

        missed = sorted(set(COMPLIANCE_REMAPS) - self.compliance_remapped)
        if missed:
            raise SystemExit("[-] COMPLIANCE_REMAPS entries never applied "
                             "(upstream file moved/renamed?):\n  "
                             + "\n  ".join(missed))
        self.report["compliance_remaps"] = {
            rel: len(rules)
            for rel, rules in sorted(COMPLIANCE_REMAPS.items())}
        self.report["notes"].append(
            "compliance_remaps: the fleet SDK compliance sweep (pay#33) "
            "folded into the port — compliance-ignore suppressions with "
            "inline reasons, requests timeouts, and escaped IN-lists in "
            "sales_payment_summary. Re-audit the suppressions when the "
            "compliance scanner or the upstream source changes.")

        self.report["doctype_count"] = (
            len(self.doctypes)
            - len(self.report.get("skipped_doctype_stubs", []))
            - len(self.report["excluded_modules"]["doctypes"]))
        self.report["unmapped_dotted_paths"] = sorted(
            {p: sorted(files) for p, files in self.unmapped.items()})
        self.report["unmapped_detail"] = {
            p: sorted(files)[:5] for p, files in sorted(self.unmapped.items())}
        write_text(HERE / "port_report.json",
                   json.dumps(self.report, indent=2, sort_keys=True) + "\n")
        n_files = sum(1 for p in DEST.rglob("*") if p.is_file())
        print(f"[+] Ported {self.report['doctype_count']} doctypes from "
              f"{self.report['module_count']} upstream modules "
              f"(excluded modules: {', '.join(sorted(EXCLUDE_MODULES))}; "
              f"excluded doctypes: {len(self.excluded_doctypes)}; "
              f"fleet-collision doctypes: {len(self.fleet_excluded)}; "
              f"excluded desk-fixture records: "
              f"{self.report['excluded_fixture_records']['total']} "
              f"-> port/exports/); "
              f"{n_files} files under erp/frappe/.")
        if self.unmapped:
            print(f"[!] {len(self.unmapped)} unmapped erpnext.* dotted paths "
                  f"left verbatim (see port_report.json).")

    # -------------------------------------------------------------- manifest
    def build_manifest(self):
        hooks_ns = {}
        exec(compile(read_text(self.pkg / "hooks.py"), "hooks.py", "exec"),
             hooks_ns)
        hooks_ns.pop("__builtins__", None)

        def map_str(v, strict=True):
            if isinstance(v, str) and v.startswith("erpnext."):
                mapped, _ = self.map_dotted(v)
                if mapped is None:
                    if strict:
                        raise SystemExit(f"[-] cannot map hook value {v}")
                    return v  # e.g. asset filenames like erpnext.bundle.css
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

        # Hooks whose (already remapped) handler lives inside an excluded
        # module do NOT belong in erp's manifest — they are dropped here and
        # reported under excluded_modules.hooks_reassigned so the owning
        # module's manifest declares them (the composer merges doc_events /
        # scheduler_events additively across modules).
        reassigned = self.report["excluded_modules"]["hooks_reassigned"]

        def excluded_target(v):
            return isinstance(v, str) and any(
                v == f"{APP}.{m}" or v.startswith(f"{APP}.{m}.")
                for m in EXCLUDE_MODULES)

        # Hooks whose handler lives inside an EXCLUDE_DOCTYPES dir (or whose
        # doc_events key IS an excluded doctype) are dropped from the
        # manifest entirely — the code they point at no longer ships — and
        # ledgered under excluded_doctypes.hooks_dropped. Checked on the
        # ORIGINAL erpnext.* dotted path, before map_str (map_dotted cannot
        # map these anymore: the doctypes were popped from the map).
        dropped_hooks = self.report["excluded_doctypes"]["hooks_dropped"]
        fleet_dropped = (
            self.report["excluded_fleet_collisions"]["hooks_dropped"])

        def excluded_doctype_ledger(v):
            """The hooks_dropped ledger this handler path belongs to (dead
            doctype vs fleet collision), or None when it targets no
            excluded doctype."""
            if not (isinstance(v, str) and v.startswith("erpnext.")):
                return None
            parts = v.split(".")
            if len(parts) >= 4 and parts[2] == "doctype":
                if parts[3] in self.excluded_doctypes:
                    return dropped_hooks
                if parts[3] in self.fleet_excluded:
                    return fleet_dropped
            return None

        # doc_events — expand tuple keys (JSON manifests cannot carry them),
        # merge per doctype.
        doc_events = {}
        for key, evts in hooks_ns.get("doc_events", {}).items():
            keys = key if isinstance(key, tuple) else (key,)
            for k in keys:
                key_ledger = (
                    dropped_hooks if k in self.excluded_doctype_names
                    else fleet_dropped if k in self.fleet_excluded_names
                    else None)
                if key_ledger is not None:
                    dropped = key_ledger.setdefault("doc_events", {})
                    dropped[k] = "entire key: doctype excluded"
                    continue
                bucket = doc_events.setdefault(k, {})
                for evt, handlers in evts.items():
                    hl = [handlers] if isinstance(handlers, str) else list(handlers)
                    merged = bucket.setdefault(evt, [])
                    for h in hl:
                        led = excluded_doctype_ledger(h)
                        if led is not None:
                            (led.setdefault("doc_events", {})
                             .setdefault(k, {}).setdefault(evt, [])
                             .append(h))
                            continue
                        h = map_str(h)
                        if excluded_target(h):
                            moved = (reassigned.setdefault("doc_events", {})
                                     .setdefault(k, {}).setdefault(evt, []))
                            if h not in moved:
                                moved.append(h)
                            continue
                        if h not in merged:
                            merged.append(h)
        doc_events = {k: {e: hs for e, hs in evts.items() if hs}
                      for k, evts in doc_events.items()}
        doc_events = {k: evts for k, evts in doc_events.items() if evts}
        supported["doc_events"] = doc_events

        # scheduler_events — keep cron dict buckets, drop empty lists.
        def keep_jobs(jobs, where):
            kept = []
            for j in jobs:
                led = excluded_doctype_ledger(j)
                if led is not None:
                    (led.setdefault("scheduler_events", {})
                     .setdefault(where, []).append(j))
                    continue
                j = map_str(j)
                if excluded_target(j):
                    moved = (reassigned.setdefault("scheduler_events", {})
                             .setdefault(where, []))
                    if j not in moved:
                        moved.append(j)
                else:
                    kept.append(j)
            return kept

        sched = {}
        for bucket, tasks in hooks_ns.get("scheduler_events", {}).items():
            if isinstance(tasks, dict):
                cron = {expr: kj for expr, jobs in tasks.items()
                        if jobs and (kj := keep_jobs(jobs, f"{bucket}:{expr}"))}
                if cron:
                    sched[bucket] = cron
            elif tasks:
                kept = keep_jobs(tasks, bucket)
                if kept:
                    sched[bucket] = kept
        supported["scheduler_events"] = sched

        # upstream override_whitelisted_methods -> manifest
        # whitelisted_methods (the composer emits the pair under BOTH
        # whitelisted_methods and override_whitelisted_methods).
        owm = {}
        for k, v in hooks_ns.get("override_whitelisted_methods", {}).items():
            led = excluded_doctype_ledger(v)
            if led is not None:
                led.setdefault("whitelisted_methods", {})[k] = v
                continue
            v = map_str(v)
            if excluded_target(v):
                reassigned.setdefault("whitelisted_methods", {})[k] = v
                continue
            owm[k] = v
        supported["whitelisted_methods"] = owm

        # NOTE: after_install is deliberately NOT declared. The composed
        # shell scaffold defines `after_install = "<app>.install.after_install"`
        # as a plain string, and merge_hooks() appends manifest entries with
        # list.append() — composing an after_install manifest hook makes the
        # generated hooks.py raise AttributeError at import time (verified
        # against compose_backend.py during this port; see PR). Fresh sites
        # run erp setup manually:
        #   bench --site <site> execute <app>.erp.setup.install.after_install
        self.report["notes"].append(
            "after_install NOT declared in manifest: composer merge_hooks() "
            "would append to the shell scaffold's after_install *string* and "
            "crash hooks.py at import. Run "
            "`bench --site <site> execute {app}.erp.setup.install.after_install`"
            " once per fresh site instead.")

        # composer-supported keys actually used
        self.report["hooks_supported"] = {
            "doc_events": f"{len(doc_events)} doctype keys (tuple key over "
                          f"{len(hooks_ns.get('period_closing_doctypes', []))}"
                          f" period-closing doctypes expanded)",
            "scheduler_events": {k: (len(v) if isinstance(v, list) else
                                     {e: len(j) for e, j in v.items()})
                                 for k, v in sched.items()},
            "whitelisted_methods": list(owm),
        }

        # everything else in hooks.py the composer cannot express.
        composer_keys = {
            "doc_events", "scheduler_events", "override_whitelisted_methods",
            "override_doctype_class", "fixtures", "auth_hooks",
            "before_uninstall", "after_install", "commands",
        }
        unsupported = {}
        for k, v in sorted(hooks_ns.items()):
            if k in composer_keys or k.startswith("_"):
                continue
            if callable(v) or k in ("naming_series_variables_list",
                                    "period_closing_doctypes"):
                continue
            unsupported[k] = map_val(v) if isinstance(v, (str, list, dict)) else str(v)
        self.report["hooks_unsupported"] = unsupported
        self.report["notes"].append(
            "hooks_unsupported keys are NOT wired by the composer; a shell "
            "can hand-write any of them above its hooks.py fence. Their "
            "dotted values are pre-mapped to composed paths here for that "
            "purpose.")

        # python dependencies from upstream pyproject.toml
        deps = []
        m = re.search(r"^dependencies\s*=\s*\[(.*?)\]", read_text(
            self.source / "pyproject.toml"), re.S | re.M)
        if m:
            deps = re.findall(r'"([^"]+)"', m.group(1))
        self.report["dependencies"] = deps

        # persona manifest (persona wave phase 1): all hooks and
        # dependencies live in the tenant flavor block; the control persona
        # is declared but empty.
        return {
            "name": MODULE_NAME,
            "description": (
                "Modular SDK for core ERP: ERPNext v16.32.1 port "
                "(accounts, stock, selling, buying, manufacturing, "
                "assets, regional and more) flattened into a "
                "single composed frappe module. The upstream crm, projects "
                "and support modules are excluded — they are carried by "
                "their own SDK modules in the productivity repo "
                "({app_name}.crm, {app_name}.projects, {app_name}.support), "
                "which erp's references to them resolve to. "
                "Fork of frappe/erpnext (GPL-3.0) via Frappenize/erpnext@"
                "rokct."),
            "app_type": {
                PERSONA: {
                    "hooks": {
                        "doc_events": supported["doc_events"],
                        "scheduler_events": supported["scheduler_events"],
                        "whitelisted_methods":
                            supported["whitelisted_methods"],
                    },
                    "dependencies": deps,
                },
                "control": {},
            },
        }

    # ---------------------------------------------------------------- static
    def write_static(self):
        shutil.copy2(self.source / "license.txt", HERE.parent / "LICENSE")
        write_text(HERE.parent / "README.md", README)
        write_text(DEST / ".gitignore",
                   (Path("/home/user/productivity/crm/frappe/.gitignore")
                    .read_text()
                    if Path("/home/user/productivity/crm/frappe/.gitignore")
                    .exists() else GITIGNORE_FALLBACK))
        for stack in ("dart", "nextjs"):
            write_text(HERE.parent / stack / ".gitignore",
                       "# placeholder — no {} SDK for erp yet\n".format(stack))


README = """\
# erp — ERPNext as a composable frappe SDK module

**Provenance:** fork of [frappe/erpnext](https://github.com/frappe/erpnext)
at the **version-16-hotfix** tip (commit `f813774f63`), taken via
`Frappenize/erpnext@rokct-hotfix`. Upstream tags releases on `version-16`
only; this hotfix tip carries security fixes (XSS escaping, whitelisted
endpoint permission checks) not yet in any tagged release, and does not
descend from the tag lineage — hence the dedicated `rokct-hotfix` branch.
When upstream cuts the next release containing these fixes, the port
returns to tag-tracking via `rokct`.

**License: GPL-3.0** (see [LICENSE](LICENSE), copied verbatim from upstream
`license.txt`). Every ported file keeps its upstream copyright/license header
verbatim. This subtree is intentionally excluded from the repo's MIT header
check (`.licenserc.yaml`).

The `frappe/` tree is generated by `port/port_erpnext.py` — a deterministic,
re-runnable transform of the upstream source. Do not hand-edit ported files;
change the script and re-run it. See the script's docstring for the full
layout rationale and `port/port_report.json` for what was and wasn't carried.

A site composing `erp` must NOT also have the upstream `erpnext` app
installed — doctype names are kept verbatim, so the two double-define every
doctype (crm-precedent exclusivity rule).

Five upstream doctypes are excluded because their names collide with
doctypes owned by other fleet SDK modules — Branch (base), Brand
(products), Delivery Settings (delivery), Subscription and Subscription
Settings (subscriptions) — plus the dependent Process Subscription and
Subscription Invoice. Excluded, not deleted: the sources are preserved
under `port/exports/fleet_collisions/`, the decision is ledgered in
`port/port_report.json["excluded_fleet_collisions"]`, and removing an
entry from the port script's `EXCLUDE_FLEET_DOCTYPES` and re-running the
port restores the feature (which then requires renaming one side of the
collision).

Upstream's runtime integration with the separate `payments` app (Payment
Request's gateway-controller/stripe imports, `payment_app_import_guard`,
the order-page pay-button check) is re-pointed at pay's own composed
`gateways` module by the port script's `PAYMENTS_REMAPS` rules: composing
`erp` alongside `gateways` needs no upstream payments package, and
composing `erp` without `gateways` degrades exactly as gracefully as
upstream did without payments. The mirror wiring (gateways -> erp) lives in
`gateways/port/port_payments.py`'s `ERP_REMAPS`.

`dart/` and `nextjs/` are placeholders (no manifest) until those SDK halves
are actually built.
"""

GITIGNORE_FALLBACK = "__pycache__/\n*.py[cod]\n"

EXPORTS_README = """\
# port/exports — records excluded from the erp port, preserved verbatim

Generated by `port/port_erpnext.py` on every run (wiped + rewritten, like
`erp/frappe/`); committed so the content survives without the upstream
checkout. Files are VERBATIM upstream bytes from the pinned
Frappenize/erpnext source — no dotted-path rewrites, no module-field
rewrite — because this tree is a content archive, not ported code.

- `desk_fixtures/` — Frappe-desk furniture records excluded from the port
  (workspace, workspace_sidebar, desktop_icon, module_onboarding,
  onboarding_step, dashboard_chart, dashboard_chart_source, number_card,
  form_tour, erp_dashboard, report_center). Kept for reuse: the dashboard
  chart / number card / onboarding definitions are the raw material for
  Next.js SDK charts, KPIs and onboarding flows. Same-named record dirs
  exported from several upstream modules are deduplicated last-module-wins
  (mirror of the port's merge rule; see
  port_report.json["excluded_fixture_records"]).
- `dead_doctypes/` — sources of the doctypes excluded via EXCLUDE_DOCTYPES
  (orphaned website child tables + the Video/YouTube desk feature) and the
  youtube_interactions report that dies with Video. Archived for the
  record; see port_report.json["excluded_doctypes"].
- `fleet_collisions/` — sources of the doctypes excluded via
  EXCLUDE_FLEET_DOCTYPES because their dir names collide with doctypes
  owned by other fleet SDK modules (branch/base, brand/products,
  delivery_settings/delivery, subscription + subscription_settings/
  subscriptions, plus the dependent process_subscription and
  subscription_invoice). Excluded, not deleted: removing the entry from
  the port script's exclusion list and re-running the port restores the
  feature. See port_report.json["excluded_fleet_collisions"].

Counts and reasons are ledgered in `port_report.json` under
`excluded_doctypes` and `excluded_fixture_records`.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="/workspace/erpnext",
                    help="path to a Frappenize/erpnext checkout @ "
                         f"{SOURCE_BRANCH} (commit {SOURCE_COMMIT[:10]})")
    args = ap.parse_args()
    # deliberately NOT .resolve()d: port_report.json records the source path
    # as given, so the canonical /workspace/erpnext location stays stable in
    # the committed report even when that path is a symlink on the machine
    # running the port.
    Porter(Path(args.source)).run()


if __name__ == "__main__":
    main()
