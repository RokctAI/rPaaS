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

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""Shared offline harness for the sw6 delivery-assurance tests.

NOT a test module (no test_ prefix): it provides the frappe stub, the
package loader (same "wmod" convention as the sibling sw2/sw4 tests, so
one unittest-discover process shares the loaded modules), and an in-memory
FakeLedgerDB implementing exactly the frappe DB surface the sw6 modules
use - get_all filter operators included. No bench, no network.
"""
from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FRAPPE_MODULE_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
COMMON_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "warnings_engine")
TENANT_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "tenant")


def ensure_frappe_stub():
    """Install (or augment) the minimal frappe stub.

    Another sibling test file may already have installed its own stub in
    this discover process - only fill in what is missing, never replace.
    """
    try:
        import frappe
    except ImportError:
        frappe = types.ModuleType("frappe")
        sys.modules["frappe"] = frappe

    if "frappe.utils" not in sys.modules:
        sys.modules["frappe.utils"] = types.ModuleType("frappe.utils")
    utils = sys.modules["frappe.utils"]

    def cint(value):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    if not hasattr(utils, "cint"):
        utils.cint = cint
    if not hasattr(utils, "get_datetime"):
        utils.get_datetime = lambda v: v
    frappe.utils = utils

    defaults = {
        "conf": {},
        "db": MagicMock(),
        "cache": MagicMock(),
        "get_doc": MagicMock(),
        "get_all": MagicMock(return_value=[]),
        "get_roles": MagicMock(return_value=[]),
        "get_traceback": MagicMock(return_value="traceback"),
        "log_error": MagicMock(),
        "make_get_request": MagicMock(),
        "whitelist": lambda *a, **k: (lambda f: f),
        "session": SimpleNamespace(user="Guest"),
        "PermissionError": type("PermissionError", (Exception,), {}),
    }
    for attr, value in defaults.items():
        if not hasattr(frappe, attr):
            setattr(frappe, attr, value)
    return frappe


def _load_pkg(name, pkg_dir):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name,
        os.path.join(pkg_dir, "__init__.py"),
        submodule_search_locations=[pkg_dir],
    )
    pkg = importlib.util.module_from_spec(spec)
    sys.modules[name] = pkg
    spec.loader.exec_module(pkg)
    return pkg


def load_modules():
    """Load and return the sw6 module set (shared "wmod" package)."""
    ensure_frappe_stub()
    if "wmod" not in sys.modules:
        parent = types.ModuleType("wmod")
        parent.__path__ = []
        sys.modules["wmod"] = parent
    _load_pkg("wmod.warnings_engine", COMMON_DIR)
    _load_pkg("wmod.tenant", TENANT_DIR)
    mods = SimpleNamespace()
    mods.messages = importlib.import_module("wmod.warnings_engine.messages")
    mods.push = importlib.import_module("wmod.warnings_engine.push")
    mods.delivery = importlib.import_module("wmod.tenant.delivery")
    mods.push_sync = importlib.import_module("wmod.tenant.push_sync")
    mods.sms_fallback = importlib.import_module("wmod.tenant.sms_fallback")
    mods.escalation = importlib.import_module("wmod.tenant.escalation")
    mods.proxy = importlib.import_module(
        "wmod.tenant.api.get_weather_warnings.get_weather_warnings")
    mods.ack_api = importlib.import_module(
        "wmod.tenant.api.ack_weather_notice.ack_weather_notice")
    mods.esc_ack_api = importlib.import_module(
        "wmod.tenant.api.ack_weather_escalation.ack_weather_escalation")
    mods.stats_api = importlib.import_module(
        "wmod.tenant.api.get_weather_notice_stats.get_weather_notice_stats")
    return mods


# --------------------------------------------------------------------------- #
# in-memory DB
# --------------------------------------------------------------------------- #

def _matches(row, key, cond):
    value = row.get(key)
    if isinstance(cond, (list, tuple)):
        op = cond[0]
        if op == "in":
            return value in cond[1]
        if op == "not in":
            return value not in cond[1]
        if op == "between":
            low, high = cond[1]
            return value is not None and low <= value <= high
        if op == ">=":
            return value is not None and value >= cond[1]
        if op == "<=":
            return value is not None and value <= cond[1]
        if op == "is":
            empty = value in (None, "")
            return empty if cond[1] == "not set" else not empty
        raise AssertionError(f"unsupported filter op: {op!r}")
    return value == cond


class FakeLedgerDB:
    """The frappe DB surface the sw6 modules touch, in memory."""

    def __init__(self):
        self.tables = {}
        self.singles = {}
        self._counter = 0

    # -- storage helpers ---------------------------------------------------- #
    def rows(self, doctype):
        return self.tables.setdefault(doctype, [])

    def seed(self, doctype, **fields):
        row = dict(fields)
        if "name" not in row:
            self._counter += 1
            row["name"] = f"{doctype[:3].upper()}-{self._counter:05d}"
        self.rows(doctype).append(row)
        return row

    def by_name(self, doctype, name):
        for row in self.rows(doctype):
            if row.get("name") == name:
                return row
        return None

    # -- frappe.get_all ----------------------------------------------------- #
    def get_all(self, doctype, filters=None, fields=None, order_by=None,
                limit_page_length=None, **kwargs):
        rows = [row for row in self.rows(doctype)
                if all(_matches(row, k, c)
                       for k, c in (filters or {}).items())]
        if order_by:
            for part in reversed([p.strip() for p in order_by.split(",")]):
                bits = part.split()
                key = bits[0]
                reverse = len(bits) > 1 and bits[1].lower() == "desc"
                rows.sort(key=lambda r: (r.get(key) is None, r.get(key)),
                          reverse=reverse)
        limit = kwargs.get("limit", limit_page_length)
        if limit:
            rows = rows[:limit]
        wanted = fields or None
        return [dict(row) if wanted is None
                else {f: row.get(f) for f in wanted} for row in rows]

    # -- frappe.db ---------------------------------------------------------- #
    def get_value(self, doctype, filters=None, fieldname=None, as_dict=False,
                  **kwargs):
        if isinstance(filters, str):
            row = self.by_name(doctype, filters)
        else:
            row = next((r for r in self.rows(doctype)
                        if all(_matches(r, k, c)
                               for k, c in (filters or {}).items())), None)
        if row is None:
            return None
        names = fieldname if isinstance(fieldname, (list, tuple)) else [
            fieldname or "name"]
        if as_dict:
            return SimpleNamespace(**{f: row.get(f) for f in names})
        if len(names) == 1:
            return row.get(names[0])
        return tuple(row.get(f) for f in names)

    def set_value(self, doctype, name, updates, *args, **kwargs):
        row = self.by_name(doctype, name)
        if row is None:
            raise KeyError(f"{doctype} {name} not found")
        if not isinstance(updates, dict):
            updates = {updates: args[0]}
        row.update(updates)

    def get_single_value(self, doctype, field):
        return self.singles.get((doctype, field))

    # -- frappe.get_doc ----------------------------------------------------- #
    def get_doc(self, data):
        db = self

        class _Doc:
            def __init__(self, payload):
                self._payload = dict(payload)
                self.name = None

            def insert(self, ignore_permissions=False):
                payload = dict(self._payload)
                doctype = payload.pop("doctype")
                row = db.seed(doctype, **payload)
                self.name = row["name"]
                return self

        return _Doc(data)


class Sw6TestCase(unittest.TestCase):
    """Base case: fake DB + captured admin log + clean config per test."""

    def setUp(self):
        self.mods = load_modules()
        import frappe
        self.frappe = frappe
        self.db = FakeLedgerDB()

        self._saved = {
            "conf": frappe.conf,
            "db": frappe.db,
            "get_all": frappe.get_all,
            "get_doc": frappe.get_doc,
            "cache": getattr(frappe, "cache", None),
            "get_roles": getattr(frappe, "get_roles", None),
            "get_attr": getattr(frappe, "get_attr", None),
            "session": getattr(frappe, "session", None),
        }
        frappe.conf = {}
        frappe.db = SimpleNamespace(
            get_value=self.db.get_value,
            set_value=self.db.set_value,
            get_single_value=self.db.get_single_value,
        )
        frappe.get_all = self.db.get_all
        frappe.get_doc = self.db.get_doc
        frappe.session = SimpleNamespace(user="Guest")

        self.admin_logs = []
        self._saved_log_fns = []
        log = lambda title, message=None: self.admin_logs.append(
            (title, message))
        for mod in (self.mods.delivery, self.mods.push_sync,
                    self.mods.sms_fallback, self.mods.escalation,
                    self.mods.push, self.mods.ack_api, self.mods.esc_ack_api,
                    self.mods.stats_api):
            if hasattr(mod, "log_admin_error"):
                self._saved_log_fns.append((mod, mod.log_admin_error))
                mod.log_admin_error = log

    def tearDown(self):
        frappe = self.frappe
        frappe.conf = self._saved["conf"]
        frappe.db = self._saved["db"]
        frappe.get_all = self._saved["get_all"]
        frappe.get_doc = self._saved["get_doc"]
        for attr in ("get_roles", "get_attr", "session", "cache"):
            saved = self._saved[attr]
            if saved is None:
                if hasattr(frappe, attr):
                    delattr(frappe, attr)
            else:
                setattr(frappe, attr, saved)
        for mod, fn in self._saved_log_fns:
            mod.log_admin_error = fn


# stub frappe at import time so test modules can `import frappe` safely
# whichever file unittest discovery loads first.
ensure_frappe_stub()

NOON = dt.datetime(2026, 8, 20, 12, 0, 0)
CELL = "-25.75,28.25"
USER = "farmer@example.com"
WARNING_ID = "SWW-2026-00042"


def active_warning(warning_id=WARNING_ID, severity="heads_up",
                   event_class="flash_flood"):
    """A control-plane warning dict as served by fetch_cell_warnings."""
    labels = {"heads_up": "Heads-up", "warning": "Please take care",
              "advisory": "Worth knowing"}
    return {
        "id": warning_id,
        "event_class": event_class,
        "severity": severity,
        "severity_label": labels.get(severity, "Heads-up"),
        "headline": "Flash flooding possible near Pretoria",
        "message": ("Heavy rain could cause fast-rising water around "
                    "Pretoria in the next day or so. If you're near "
                    "streams or low-lying roads, keep an eye out."),
        "onset": "2026-08-20T06:00:00Z",
        "valid_until": "2026-08-21T06:00:00Z",
        "issued_at": "2026-08-20T07:00:00Z",
    }
