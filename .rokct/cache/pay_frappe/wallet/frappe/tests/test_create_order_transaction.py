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

"""create_order_transaction, unit-tested without a bench site.

The other suites in this directory are FrappeTestCase-based and need a
running bench. This one follows agent's rlms pattern instead — load the
module under test by file path — but payment.py, unlike the rlms rule
modules, is not frappe-free, so a minimal in-memory ``frappe`` stub is
installed first. The suite skips itself when the real frappe package is
importable (a bench context), where the FrappeTestCase suites are the
right tool and the stub must not shadow anything.

Run standalone:  python3 -m unittest wallet/frappe/tests/test_create_order_transaction.py
"""

import importlib.util
import json
import os
import sys
import types
import unittest
from datetime import datetime

HAVE_REAL_FRAPPE = importlib.util.find_spec("frappe") is not None

_MODULE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "tenant", "api", "payment", "payment.py"
)

# The wallet module composes into whatever host app the fleet builds (the
# "{app_name}" placeholder is substituted at compose time), so the harness
# uses a deliberately arbitrary app name to prove no shell name is assumed.
TEST_APP = "testapp"


class _Doc(types.SimpleNamespace):
    """Just enough of frappe.model.document.Document for the endpoint."""

    def get(self, key, default=None):
        return getattr(self, key, default)


def _install_stub_frappe():
    """Build stub frappe and host-app modules, register them, return the frappe stub."""
    frappe = types.ModuleType("frappe")

    class ValidationError(Exception):
        pass

    class DoesNotExistError(Exception):
        pass

    class StubPermissionError(Exception):
        pass

    frappe.ValidationError = ValidationError
    frappe.DoesNotExistError = DoesNotExistError
    frappe.PermissionError = StubPermissionError

    def whitelist(*args, **kwargs):
        def decorator(fn):
            return fn

        return decorator

    frappe.whitelist = whitelist

    def throw(msg, exc=ValidationError):
        raise exc(msg)

    frappe.throw = throw
    frappe.session = types.SimpleNamespace(user="Guest")
    frappe.utils = types.SimpleNamespace(
        now_datetime=lambda: datetime(2026, 1, 1, 12, 0, 0)
    )

    # Test-controlled storage.
    frappe._docs = {}  # (doctype, name) -> _Doc
    frappe._by_filters = {}  # (doctype, sorted filter items) -> value
    frappe._inserted = []

    def _filters_key(doctype, filters):
        return (doctype, tuple(sorted(filters.items())))

    def exists(doctype, name_or_filters):
        if isinstance(name_or_filters, dict):
            return frappe._by_filters.get(_filters_key(doctype, name_or_filters))
        if (doctype, name_or_filters) in frappe._docs:
            return name_or_filters
        return None

    def get_value(doctype, filters, fieldname=None, **kwargs):
        if isinstance(filters, dict):
            return frappe._by_filters.get(_filters_key(doctype, filters))
        doc = frappe._docs.get((doctype, filters))
        return getattr(doc, fieldname, None) if doc else None

    frappe.db = types.SimpleNamespace(exists=exists, get_value=get_value)

    def get_doc(*args):
        if len(args) == 1 and isinstance(args[0], dict):
            fields = dict(args[0])
            doc = _Doc(**fields)

            def insert(ignore_permissions=False, _doc=doc):
                _doc.name = f"TXN-{len(frappe._inserted) + 1:04d}"
                frappe._inserted.append(_doc)

            doc.insert = insert
            return doc
        doctype, name = args
        doc = frappe._docs.get((doctype, name))
        if doc is None:
            raise DoesNotExistError(f"{doctype} {name} not found")
        return doc

    frappe.get_doc = get_doc

    frappe_model = types.ModuleType("frappe.model")
    frappe_model_document = types.ModuleType("frappe.model.document")
    frappe_model_document.Document = _Doc
    frappe_model.document = frappe_model_document

    app = types.ModuleType(TEST_APP)
    app_base = types.ModuleType(f"{TEST_APP}.base")
    app_tenant = types.ModuleType(f"{TEST_APP}.base.tenant")
    app_api = types.ModuleType(f"{TEST_APP}.base.tenant.api")
    app_idempotency = types.ModuleType(f"{TEST_APP}.base.tenant.api.idempotency")
    app_idempotency.idempotent = lambda fn: fn
    app_api.idempotency = app_idempotency
    app_tenant.api = app_api
    app_base.tenant = app_tenant
    app.base = app_base

    def get_attr(path):
        # Mirror the composer's "{app_name}" substitution, then the real
        # frappe.get_attr's import-and-getattr resolution, so the stubbed
        # idempotency module above stays load-bearing.
        module_path, attr = path.replace("{app_name}", TEST_APP).rsplit(".", 1)
        return getattr(importlib.import_module(module_path), attr)

    frappe.get_attr = get_attr

    sys.modules["frappe"] = frappe
    sys.modules["frappe.model"] = frappe_model
    sys.modules["frappe.model.document"] = frappe_model_document
    if importlib.util.find_spec("requests") is None:
        # payment.py imports requests at module level for the gateway
        # calls; create_order_transaction never touches it.
        sys.modules["requests"] = types.ModuleType("requests")
    sys.modules[TEST_APP] = app
    sys.modules[f"{TEST_APP}.base"] = app_base
    sys.modules[f"{TEST_APP}.base.tenant"] = app_tenant
    sys.modules[f"{TEST_APP}.base.tenant.api"] = app_api
    sys.modules[f"{TEST_APP}.base.tenant.api.idempotency"] = app_idempotency
    return frappe


@unittest.skipIf(
    HAVE_REAL_FRAPPE,
    "real frappe importable — run the FrappeTestCase suites under bench instead",
)
class TestCreateOrderTransaction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frappe = _install_stub_frappe()
        spec = importlib.util.spec_from_file_location(
            "wallet_payment_under_test", _MODULE_PATH
        )
        cls.payment = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.payment)

    def setUp(self):
        f = self.frappe
        f.session.user = "customer@example.com"
        f._docs.clear()
        f._by_filters.clear()
        f._inserted.clear()
        f._docs[("Order", "ORD-0001")] = _Doc(
            name="ORD-0001",
            user="customer@example.com",
            shop="Test Shop",
            grand_total=150.0,
            total_price=140.0,
        )
        f._docs[("PaaS Payment Gateway", "1")] = _Doc(name="1")

    def test_guest_is_rejected(self):
        self.frappe.session.user = "Guest"
        with self.assertRaises(self.frappe.ValidationError):
            self.payment.create_order_transaction("ORD-0001", 1)

    def test_missing_order_is_a_clear_error(self):
        with self.assertRaises(self.frappe.DoesNotExistError) as ctx:
            self.payment.create_order_transaction("ORD-MISSING", 1)
        self.assertIn("ORD-MISSING", str(ctx.exception))

    def test_customer_records_transaction_from_order_fields(self):
        result = self.payment.create_order_transaction("ORD-0001", 1)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(self.frappe._inserted), 1)
        txn = self.frappe._inserted[0]
        self.assertEqual(result["transaction_id"], txn.name)
        # Amount and user come from the Order doc, never the client.
        self.assertEqual(txn.amount, 150.0)
        self.assertEqual(txn.user, "customer@example.com")
        self.assertEqual(txn.payable_type, "Order")
        self.assertEqual(txn.payable_id, "ORD-0001")
        self.assertEqual(txn.status, "Paid")
        self.assertEqual(txn.payment_gateway, "1")
        self.assertEqual(
            json.loads(txn.request_data),
            {"order_id": "ORD-0001", "payment_sys_id": 1},
        )

    def test_amount_falls_back_to_total_price(self):
        order = self.frappe._docs[("Order", "ORD-0001")]
        del order.grand_total
        self.payment.create_order_transaction("ORD-0001", 1)
        self.assertEqual(self.frappe._inserted[0].amount, 140.0)

    def test_unknown_gateway_still_records_without_link(self):
        self.payment.create_order_transaction("ORD-0001", 999)
        txn = self.frappe._inserted[0]
        self.assertIsNone(getattr(txn, "payment_gateway", None))
        self.assertEqual(
            json.loads(txn.request_data)["payment_sys_id"], 999
        )

    def test_existing_transaction_is_returned_not_duplicated(self):
        self.frappe._by_filters[
            (
                "Transaction",
                (
                    ("payable_id", "ORD-0001"),
                    ("payable_type", "Order"),
                    ("payment_gateway", "1"),
                ),
            )
        ] = "TXN-EXISTING"
        result = self.payment.create_order_transaction("ORD-0001", 1)
        self.assertEqual(result["transaction_id"], "TXN-EXISTING")
        self.assertTrue(result["duplicate"])
        self.assertEqual(self.frappe._inserted, [])

    def test_seller_of_the_orders_shop_is_allowed(self):
        f = self.frappe
        f.session.user = "seller@example.com"
        f._by_filters[("Shop", (("user", "seller@example.com"),))] = "Test Shop"
        result = self.payment.create_order_transaction("ORD-0001", 1)
        self.assertEqual(result["status"], "success")
        # The transaction is still attributed to the order's customer.
        self.assertEqual(f._inserted[0].user, "customer@example.com")

    def test_unrelated_user_is_rejected(self):
        f = self.frappe
        f.session.user = "other@example.com"
        f._by_filters[("Shop", (("user", "other@example.com"),))] = "Other Shop"
        with self.assertRaises(f.PermissionError):
            self.payment.create_order_transaction("ORD-0001", 1)
        self.assertEqual(f._inserted, [])


if __name__ == "__main__":
    unittest.main()
