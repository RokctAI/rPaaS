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

# Copyright (c) 2026 ROKCT Holdings
# For license information, please see license.txt
#
# Frappe-free pure-logic tests for the wallet module's create_transaction
# (composed as {app_name}.api.payment.payment.create_transaction).
# These run with plain `python3 -m unittest` (no bench/site required): the
# frappe module is stubbed before payment.py is loaded from its file path.

import importlib.util
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock

MODULE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "src", "tenant", "api", "payment", "payment.py"
    )
)

# The wallet module composes into whatever host app the fleet builds (the
# "{app_name}" placeholder is substituted at compose time), so the harness
# uses a deliberately arbitrary app name to prove no shell name is assumed.
TEST_APP = "testapp"


class FrappeThrow(Exception):
    pass


class FrappePermissionError(FrappeThrow):
    pass


def _build_fake_frappe():
    fake = MagicMock()
    fake.PermissionError = FrappePermissionError

    def _throw(message, exc=None, *args, **kwargs):
        exc_type = exc if isinstance(exc, type) else FrappeThrow
        raise exc_type(message)

    fake.throw = MagicMock(side_effect=_throw)
    # @frappe.whitelist() must be a passthrough decorator, not a MagicMock,
    # so the decorated functions remain callable module functions.
    fake.whitelist = lambda *args, **kwargs: (lambda fn: fn)

    def _get_attr(path):
        # Mirror the composer's "{app_name}" substitution, then the real
        # frappe.get_attr's import-and-getattr resolution, so the stubbed
        # idempotency module stays load-bearing (a MagicMock here would
        # swallow the decorated functions).
        module_path, attr = path.replace("{app_name}", TEST_APP).rsplit(".", 1)
        return getattr(importlib.import_module(module_path), attr)

    fake.get_attr = _get_attr
    return fake


def _load_payment_module(fake_frappe):
    saved = {
        name: sys.modules.get(name)
        for name in ("frappe", "frappe.model", "frappe.model.document", "requests")
    }
    sys.modules["frappe"] = fake_frappe
    fake_model = MagicMock()
    sys.modules["frappe.model"] = fake_model
    fake_document = MagicMock()
    sys.modules["frappe.model.document"] = fake_document
    if saved["requests"] is None:
        sys.modules["requests"] = MagicMock()
    if (
        TEST_APP not in sys.modules
        and importlib.util.find_spec(TEST_APP) is None
    ):
        # payment.py imports the composed {app_name}.base.tenant.api.idempotency at
        # module level; stub it as a passthrough decorator outside a bench.
        import types as _types

        _app = _types.ModuleType(TEST_APP)
        _app_base = _types.ModuleType(f"{TEST_APP}.base")
        _app_tenant = _types.ModuleType(f"{TEST_APP}.base.tenant")
        _app_api = _types.ModuleType(f"{TEST_APP}.base.tenant.api")
        _app_idem = _types.ModuleType(f"{TEST_APP}.base.tenant.api.idempotency")
        _app_idem.idempotent = lambda fn: fn
        _app_api.idempotency = _app_idem
        _app_tenant.api = _app_api
        _app_base.tenant = _app_tenant
        _app.base = _app_base
        sys.modules.setdefault(TEST_APP, _app)
        sys.modules.setdefault(f"{TEST_APP}.base", _app_base)
        sys.modules.setdefault(f"{TEST_APP}.base.tenant", _app_tenant)
        sys.modules.setdefault(f"{TEST_APP}.base.tenant.api", _app_api)
        sys.modules.setdefault(f"{TEST_APP}.base.tenant.api.idempotency", _app_idem)
    try:
        spec = importlib.util.spec_from_file_location(
            "payment_module_under_test", MODULE_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, mod in saved.items():
            if name == "frappe":
                continue  # keep the fake installed while tests run
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod


class TestCreateTransaction(unittest.TestCase):
    def setUp(self):
        self.frappe = _build_fake_frappe()
        self.payment = _load_payment_module(self.frappe)

        self.frappe.session.user = "customer@example.com"

        self.order = MagicMock()
        self.order.name = "ORD-0001"
        self.order.user = "customer@example.com"
        self.order.grand_total = 150.0

        self.gateway = MagicMock()
        self.gateway.name = "payfast"
        self.gateway.gateway_controller = "payfast"
        self.gateway.enabled = 1

        self.inserted_docs = []

        def _get_doc(arg, *args, **kwargs):
            if isinstance(arg, dict):
                self.inserted_docs.append(arg)
                doc = MagicMock()
                doc.name = "TXHASH001"
                doc.status = arg.get("status")
                doc.creation = datetime(2026, 1, 2, 3, 4, 5)
                doc.modified = datetime(2026, 1, 2, 3, 4, 5)
                return doc
            if arg == "Order":
                return self.order
            if arg == "PaaS Payment Gateway":
                return self.gateway
            raise AssertionError("unexpected get_doc(%r)" % (arg,))

        self.frappe.get_doc = MagicMock(side_effect=_get_doc)

    def tearDown(self):
        sys.modules.pop("frappe", None)
        sys.modules.pop("payment_module_under_test", None)

    def test_guest_is_rejected(self):
        self.frappe.session.user = "Guest"
        with self.assertRaises(FrappeThrow):
            self.payment.create_transaction("ORD-0001", "payfast")
        self.assertEqual(self.inserted_docs, [])

    def test_other_users_order_is_rejected(self):
        self.order.user = "someone_else@example.com"
        with self.assertRaises(FrappePermissionError):
            self.payment.create_transaction("ORD-0001", "payfast")
        self.assertEqual(self.inserted_docs, [])

    def test_disabled_gateway_is_rejected(self):
        self.gateway.enabled = 0
        with self.assertRaises(FrappeThrow):
            self.payment.create_transaction("ORD-0001", "payfast")
        self.assertEqual(self.inserted_docs, [])

    def test_success_creates_pending_transaction_from_order_amount(self):
        result = self.payment.create_transaction("ORD-0001", "payfast")

        self.assertEqual(len(self.inserted_docs), 1)
        doc = self.inserted_docs[0]
        self.assertEqual(doc["doctype"], "Transaction")
        self.assertEqual(doc["payable_type"], "Order")
        self.assertEqual(doc["payable_id"], "ORD-0001")
        self.assertEqual(doc["amount"], 150.0)
        self.assertEqual(doc["status"], "Pending")
        self.assertEqual(doc["payment_gateway"], "payfast")
        self.assertEqual(doc["user"], "customer@example.com")

    def test_success_response_shape_matches_mobile_parser(self):
        result = self.payment.create_transaction("ORD-0001", "payfast")

        self.assertIs(result["status"], True)
        self.assertEqual(result["message"], "Transaction created")
        self.assertEqual(result["timestamp"], "2026-01-02 03:04:05Z")

        data = result["data"]
        self.assertEqual(data["transaction_id"], "TXHASH001")
        self.assertEqual(data["user"], "customer@example.com")
        self.assertEqual(data["price"], 150.0)
        self.assertEqual(data["status"], "Pending")
        self.assertEqual(data["created_at"], "2026-01-02 03:04:05Z")
        self.assertEqual(data["updated_at"], "2026-01-02 03:04:05Z")
        self.assertEqual(data["payment_system"]["tag"], "payfast")
        self.assertEqual(data["details"], [])
        # Frappe ids are string hashes; the numeric id the mobile model
        # declares must not be fabricated, nor rates/currency conversions.
        self.assertNotIn("id", data)
        self.assertNotIn("rate", data)
        self.assertNotIn("currency_price", data)

    def test_helper_includes_payment_reference_for_gateway_flows(self):
        transaction = self.payment._create_pending_transaction(
            payable_type="Order",
            payable_id="ORD-0002",
            amount=99.5,
            payment_reference="PSP-REF-1",
        )
        self.assertEqual(len(self.inserted_docs), 1)
        doc = self.inserted_docs[0]
        self.assertEqual(doc["payment_reference"], "PSP-REF-1")
        self.assertEqual(doc["status"], "Pending")
        self.assertNotIn("user", doc)
        self.assertNotIn("payment_gateway", doc)
        self.assertEqual(transaction.name, "TXHASH001")


if __name__ == "__main__":
    unittest.main()
