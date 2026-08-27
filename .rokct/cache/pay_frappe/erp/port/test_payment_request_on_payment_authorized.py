#!/usr/bin/env python3
# Copyright (c) 2026 RokctAI
# License: MIT.
"""Standalone regression test for the reinstated
PaymentRequest.on_payment_authorized handler (upstream frappe/payments
issue #204), which port_erpnext.py's UPSTREAM_FIX_REMAPS injects into the
generated erp/frappe/doctype/payment_request/payment_request.py.

Every gateway controller in the composed gateways module finalizes a
successful external payment with

    frappe.get_doc(reference_doctype, reference_docname)
        .run_method("on_payment_authorized", status)

so without the handler a gateway success leaves the Payment Request stuck
at "Requested" with no Payment Entry.

The FrappeTestCase suites need a running bench; this suite instead loads
the GENERATED payment_request.py by file path with a minimal in-memory
``frappe`` stub installed first (wallet/frappe/tests/
test_fail_honest_payments.py pattern), mirroring the composer's
"{app_name}" substitution with a deliberately arbitrary app name. It
skips itself when the real frappe package is importable, where the bench
suites are the right tool and the stub must not shadow anything.

Covered:
- success statuses ("Authorized", "Verified", "Completed") call
  set_as_paid() exactly once;
- an already-Paid request is left alone (idempotent double-fire:
  webhook + redirect);
- "Failed"/"Cancelled" route to set_failed(), never set_as_paid();
- unknown/None statuses do nothing;
- the handler returns None for every status — gateway
  finalize_request() treats a truthy return as a custom redirect URL,
  so returning set_as_paid()'s Payment Entry would corrupt the
  redirect (deliberate deviation from issue #204's literal snippet).

Run standalone:
    python3 -m unittest erp/port/test_payment_request_on_payment_authorized.py
"""

import importlib.util
import os
import sys
import types
import unittest

HAVE_REAL_FRAPPE = importlib.util.find_spec("frappe") is not None

_GENERATED = os.path.join(
    os.path.dirname(__file__), "..", "frappe", "doctype",
    "payment_request", "payment_request.py",
)

# The erp module composes into whatever host app the fleet builds (the
# "{app_name}" placeholder is substituted at compose time); an arbitrary
# name proves no shell name is assumed.
TEST_APP = "testapp"


def _register(name, **attrs):
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    for k, v in attrs.items():
        setattr(mod, k, v)
    parent, _, child = name.rpartition(".")
    if parent:
        setattr(sys.modules[parent], child, mod)
    return mod


def _install_stubs():
    """Register just enough of frappe + the composed erp app for the
    module-level imports of payment_request.py to resolve."""

    class Document:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, key, default=None):
            return getattr(self, key, default)

    def whitelist(*args, **kwargs):
        def decorator(fn):
            return fn

        return decorator

    frappe = _register("frappe", _=lambda s: s, whitelist=whitelist)
    _register("frappe.model")
    _register("frappe.model.document", Document=Document)
    _register("frappe.query_builder")
    _register("frappe.query_builder.functions", Sum=object)
    _register("frappe.utils", flt=float, nowdate=lambda: "2026-01-01")
    _register("frappe.utils.background_jobs", enqueue=lambda *a, **k: None)

    app = f"{TEST_APP}"
    _register(app)
    _register(f"{app}.erp")
    _register(f"{app}.erp.erp_init", get_company_currency=lambda *a: "USD")
    _register(f"{app}.erp.doctype")
    _register(
        f"{app}.erp.doctype.accounting_dimension"
    )
    _register(
        f"{app}.erp.doctype.accounting_dimension.accounting_dimension",
        get_accounting_dimensions=lambda *a, **k: [],
    )
    _register(f"{app}.erp.doctype.bank_account")
    _register(
        f"{app}.erp.doctype.bank_account.bank_account",
        get_party_bank_account=lambda *a, **k: None,
    )
    _register(f"{app}.erp.doctype.payment_entry")
    _register(
        f"{app}.erp.doctype.payment_entry.payment_entry",
        get_payment_entry=lambda *a, **k: None,
    )
    _register(f"{app}.erp.doctype.subscription_plan")
    _register(
        f"{app}.erp.doctype.subscription_plan.subscription_plan",
        get_plan_rate=lambda *a, **k: 0,
    )
    _register(f"{app}.erp.accounts")
    _register(
        f"{app}.erp.accounts.party",
        get_party_account=lambda *a, **k: None,
    )
    _register(
        f"{app}.erp.accounts.utils",
        get_account_currency=lambda *a, **k: "USD",
        get_advance_payment_doctypes=lambda *a, **k: [],
        get_currency_precision=lambda *a, **k: 2,
    )
    _register(
        f"{app}.erp.utilities",
        payment_app_import_guard=lambda: None,
    )
    return frappe


def _load_payment_request():
    with open(_GENERATED, encoding="utf-8") as fh:
        source = fh.read().replace("{app_name}", TEST_APP)
    mod = types.ModuleType("erp_payment_request_under_test")
    mod.__file__ = _GENERATED
    exec(compile(source, _GENERATED, "exec"), mod.__dict__)
    return mod


@unittest.skipIf(
    HAVE_REAL_FRAPPE,
    "real frappe importable — run the FrappeTestCase suites under bench "
    "instead",
)
class OnPaymentAuthorizedTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _install_stubs()
        cls.mod = _load_payment_request()

    def _make_pr(self, status="Requested"):
        pr = self.mod.PaymentRequest()
        pr.status = status
        pr.calls = []
        pr.set_as_paid = lambda: pr.calls.append("set_as_paid")
        pr.set_failed = lambda: pr.calls.append("set_failed")
        return pr

    def test_handler_exists(self):
        # The remap regenerated correctly: the run_method target of every
        # gateway controller is a real method again (frappe's run_method
        # silently dispatches to nothing when the method is missing).
        self.assertTrue(callable(
            getattr(self.mod.PaymentRequest, "on_payment_authorized", None)))

    def test_success_statuses_set_as_paid(self):
        for status in ("Authorized", "Verified", "Completed"):
            pr = self._make_pr()
            result = pr.on_payment_authorized(status)
            self.assertEqual(pr.calls, ["set_as_paid"], status)
            self.assertIsNone(result, status)

    def test_already_paid_is_idempotent(self):
        pr = self._make_pr(status="Paid")
        result = pr.on_payment_authorized("Completed")
        self.assertEqual(pr.calls, [])
        self.assertIsNone(result)

    def test_failure_statuses_set_failed(self):
        for status in ("Failed", "Cancelled"):
            pr = self._make_pr()
            result = pr.on_payment_authorized(status)
            self.assertEqual(pr.calls, ["set_failed"], status)
            self.assertIsNone(result, status)

    def test_unknown_statuses_do_nothing(self):
        for status in (None, "", "Pending", "Refunded"):
            pr = self._make_pr()
            result = pr.on_payment_authorized(status)
            self.assertEqual(pr.calls, [], repr(status))
            self.assertIsNone(result, repr(status))


if __name__ == "__main__":
    unittest.main()
