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

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
"""
Bench-independent tests for the x-trace-id guard in scheduler-reachable code.

`frappe.request` is a module-level werkzeug LocalProxy, so
`hasattr(frappe, "request")` is always True — even in scheduler/bench
context where the proxy is unbound and any attribute access (e.g.
`.headers`) raises `RuntimeError: object is not bound`. The correct
defensive form (used in core) is:

    ... if (hasattr(frappe, "request") and frappe.request) else None ...

because LocalProxy.__bool__ returns False when the proxy is unbound.

These tests simulate an unbound proxy and verify that the scheduled task
entrypoints (orders.tasks / promotions.tasks) no longer crash on their
first line outside an HTTP request, and that the fixed guard still reads
the header when a request is bound.

Runs directly with `python3 orders/frappe/tests/test_trace_guard.py` --
frappe is stubbed only when it is not already importable, so this file is
also safe to collect inside a real bench environment.
"""

import sys
import types
import unittest
from pathlib import Path


class _UnboundRequestProxy:
    """Mimics an unbound werkzeug LocalProxy: falsy, and any attribute
    access raises RuntimeError — exactly what `frappe.request` does in
    scheduler/bench context."""

    def __bool__(self):
        return False

    def __getattr__(self, name):
        raise RuntimeError("object is not bound")


class _BoundRequest:
    """Mimics a bound request with headers."""

    def __init__(self, headers=None):
        self._headers = headers or {}

    def __bool__(self):
        return True

    @property
    def headers(self):
        return self._headers


def _stub_missing_modules():
    """Stub frappe/croniter just enough to import the task modules
    outside a bench."""
    if "frappe" not in sys.modules:
        try:
            import frappe  # noqa: F401
        except ImportError:
            frappe = types.ModuleType("frappe")
            frappe.whitelist = lambda *a, **k: (lambda f: f)
            frappe.request = _UnboundRequestProxy()
            frappe.conf = types.SimpleNamespace(get=lambda *a, **k: None)
            utils = types.ModuleType("frappe.utils")
            utils.now_datetime = lambda: None
            frappe.utils = utils
            sys.modules["frappe"] = frappe
            sys.modules["frappe.utils"] = utils

    if "croniter" not in sys.modules:
        try:
            import croniter  # noqa: F401
        except ImportError:
            croniter_mod = types.ModuleType("croniter")
            croniter_mod.croniter = object
            sys.modules["croniter"] = croniter_mod


_stub_missing_modules()

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ORDERS_TASKS = (
    _REPO_ROOT / "orders" / "frappe" / "src" / "tenant" / "tasks.py"
)
_PROMOTIONS_TASKS = (
    _REPO_ROOT / "promotions" / "frappe" / "src" / "tenant" / "tasks.py"
)
_REPEATING_ORDER = (
    _REPO_ROOT / "orders" / "frappe" / "src" / "tenant" / "api" / "repeating_order.py"
)


def _load(name, path):
    # src files are compose templates: the composer textually substitutes
    # {app_name} with the target app's package name when copying them into
    # an app, so mirror that substitution here before executing the
    # template.
    module = types.ModuleType(name)
    module.__file__ = str(path)
    source = Path(path).read_text().replace("{app_name}", "paas")
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


_orders_tasks = _load("_orders_tasks_under_test", _ORDERS_TASKS)
_promotions_tasks = _load("_promotions_tasks_under_test", _PROMOTIONS_TASKS)


class _FakeSchedulerFrappe:
    """frappe as seen from a scheduler worker: request proxy unbound,
    tenant check fails so the task returns right after the guard line."""

    def __init__(self, request=None):
        self.request = (
            request if request is not None else _UnboundRequestProxy()
        )
        self.conf = types.SimpleNamespace(get=lambda *a, **k: None)

    def whitelist(self, *args, **kwargs):
        return lambda fn: fn


class TestSchedulerTraceGuard(unittest.TestCase):
    """The scheduled entrypoints must survive their first (trace-id
    boilerplate) line when frappe.request is an unbound proxy."""

    def setUp(self):
        self._origs = [
            (_orders_tasks, _orders_tasks.frappe),
            (_promotions_tasks, _promotions_tasks.frappe),
        ]

    def tearDown(self):
        for module, orig in self._origs:
            module.frappe = orig

    def test_remove_expired_stories_unbound_request(self):
        # promotions/frappe/manifest.json schedules this daily.
        _promotions_tasks.frappe = _FakeSchedulerFrappe()
        # Non-tenant app_role short-circuits right after the guard line,
        # so reaching the return without RuntimeError proves the guard.
        self.assertIsNone(_promotions_tasks.remove_expired_stories())

    def test_process_repeating_orders_unbound_request(self):
        # orders/frappe/manifest.json schedules this hourly. With a
        # stubbed/absent croniter the function returns early; the guard
        # line executes first either way.
        _orders_tasks.frappe = _FakeSchedulerFrappe()
        try:
            _orders_tasks.process_repeating_orders()
        except RuntimeError as exc:
            self.fail(
                "trace-id guard crashed in scheduler context: %s" % exc
            )
        except Exception:
            # Downstream failures from stubbed frappe internals are not
            # what this test is about; RuntimeError on line one is.
            pass

    def test_orders_remove_expired_stories_unbound_request(self):
        # Same function also exists in orders/tasks.py.
        _orders_tasks.frappe = _FakeSchedulerFrappe()
        self.assertIsNone(_orders_tasks.remove_expired_stories())


class TestGuardExpression(unittest.TestCase):
    """The guard expression itself, in both contexts."""

    def _guard(self, frappe):
        return (
            frappe.request.headers.get("x-trace-id")
            if (hasattr(frappe, "request") and frappe.request)
            else None
        )

    def test_unbound_proxy_returns_none(self):
        frappe = types.SimpleNamespace(request=_UnboundRequestProxy())
        self.assertIsNone(self._guard(frappe))

    def test_bound_request_reads_header(self):
        frappe = types.SimpleNamespace(
            request=_BoundRequest({"x-trace-id": "trace-123"})
        )
        self.assertEqual(self._guard(frappe), "trace-123")

    def test_old_guard_form_would_have_crashed(self):
        # Documents the bug being fixed: hasattr alone does not guard,
        # because the proxy exists as a module attribute even unbound.
        frappe = types.SimpleNamespace(request=_UnboundRequestProxy())
        self.assertTrue(hasattr(frappe, "request"))
        with self.assertRaises(RuntimeError):
            (
                frappe.request.headers.get("x-trace-id")
                if hasattr(frappe, "request")
                else None
            )


class TestSourceGuardForm(unittest.TestCase):
    """Regression scan: no scheduler-reachable file may reintroduce the
    ineffective `if hasattr(frappe, "request") else` guard form."""

    BROKEN = 'if hasattr(frappe, "request") else'
    FIXED = 'if (hasattr(frappe, "request") and frappe.request) else'

    def _check(self, path, expected_fixed_count):
        source = Path(path).read_text()
        self.assertNotIn(
            self.BROKEN,
            source,
            "%s still uses the ineffective hasattr-only guard" % path,
        )
        self.assertEqual(
            source.count(self.FIXED),
            expected_fixed_count,
            "%s: unexpected number of fixed guards" % path,
        )

    def test_orders_tasks(self):
        self._check(_ORDERS_TASKS, 2)

    def test_promotions_tasks(self):
        self._check(_PROMOTIONS_TASKS, 2)

    def test_repeating_order(self):
        self._check(_REPEATING_ORDER, 4)


if __name__ == "__main__":
    unittest.main()
