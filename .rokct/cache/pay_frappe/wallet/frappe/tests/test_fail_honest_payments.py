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

"""Fail-honest behavior of the money paths in payment.py, unit-tested
without a bench site.

The FrappeTestCase suites in this directory need a running bench. This
suite instead loads the module under test by file path with a minimal
in-memory ``frappe`` stub installed first (the same pattern as
test_create_order_transaction.py). It skips itself when the real frappe
package is importable, where the FrappeTestCase suites are the right
tool and the stub must not shadow anything.

Covered:
- Stripe webhook signature verification accept/reject (dummy secret).
- Stripe webhook fail-closed when no secret is configured.
- Unhandled Stripe events are logged durably and acknowledged honestly.
- Not-implemented money paths raise instead of returning fake success.

Run standalone:
    python3.12 -m unittest wallet/frappe/tests/test_fail_honest_payments.py
"""

import hashlib
import hmac
import importlib.util
import json
import os
import sys
import time
import types
import unittest

HAVE_REAL_FRAPPE = importlib.util.find_spec("frappe") is not None

_MODULE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "tenant", "api", "payment", "payment.py"
)

# An obviously fake signing secret for tests only. Never a real credential.
DUMMY_SECRET = "whsec_TEST_DUMMY_SECRET_DO_NOT_USE_0000"  # compliance-ignore: py-hardcoded-secret (obviously fake test-only signing secret, never a real credential)

# The wallet module composes into whatever host app the fleet builds (the
# "{app_name}" placeholder is substituted at compose time), so the harness
# uses a deliberately arbitrary app name to prove no shell name is assumed.
TEST_APP = "testapp"


class _Doc(types.SimpleNamespace):
    """Just enough of frappe.model.document.Document for the endpoints."""

    def get(self, key, default=None):
        return getattr(self, key, default)


def _install_stub_frappe():
    """Build stub frappe modules, register them, return the frappe stub."""
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
    frappe.conf = {}
    frappe.local = types.SimpleNamespace(response={})

    # Test-controlled storage.
    frappe._docs = {}  # (doctype, name) -> _Doc
    frappe._by_filters = {}  # (doctype, sorted filter items) -> value
    frappe._inserted = []
    frappe._error_log = []  # (message, title) tuples from log_error

    def log_error(message=None, title=None):
        frappe._error_log.append((message, title))

    frappe.log_error = log_error

    def _filters_key(doctype, filters):
        return (doctype, tuple(sorted(filters.items())))

    def exists(doctype, name_or_filters):
        if isinstance(name_or_filters, dict):
            return frappe._by_filters.get(
                _filters_key(doctype, name_or_filters)
            )
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
        if len(args) == 1:
            doc = frappe._docs.get((args[0], args[0]))
            if doc is None:
                raise DoesNotExistError(f"{args[0]} not found")
            return doc
        doctype, name = args
        if isinstance(name, dict):
            resolved = frappe._by_filters.get(_filters_key(doctype, name))
            doc = frappe._docs.get((doctype, resolved))
        else:
            doc = frappe._docs.get((doctype, name))
        if doc is None:
            raise DoesNotExistError(f"{doctype} {name} not found")
        return doc

    frappe.get_doc = get_doc

    frappe_model = types.ModuleType("frappe.model")
    frappe_model_document = types.ModuleType("frappe.model.document")
    frappe_model_document.Document = _Doc
    frappe_model.document = frappe_model_document

    sys.modules["frappe"] = frappe
    sys.modules["frappe.model"] = frappe_model
    sys.modules["frappe.model.document"] = frappe_model_document
    if (
        "requests" not in sys.modules
        and importlib.util.find_spec("requests") is None
    ):
        sys.modules["requests"] = types.ModuleType("requests")
    if (
        TEST_APP not in sys.modules
        and importlib.util.find_spec(TEST_APP) is None
    ):
        # payment.py imports the composed {app_name}.base.tenant.api.idempotency at
        # module level; stub it as a passthrough decorator outside a bench.
        app = types.ModuleType(TEST_APP)
        app_base = types.ModuleType(f"{TEST_APP}.base")
        app_tenant = types.ModuleType(f"{TEST_APP}.base.tenant")
        app_api = types.ModuleType(f"{TEST_APP}.base.tenant.api")
        app_idem = types.ModuleType(f"{TEST_APP}.base.tenant.api.idempotency")
        app_idem.idempotent = lambda fn: fn
        app_api.idempotency = app_idem
        app_tenant.api = app_api
        app_base.tenant = app_tenant
        app.base = app_base
        sys.modules.setdefault(TEST_APP, app)
        sys.modules.setdefault(f"{TEST_APP}.base", app_base)
        sys.modules.setdefault(f"{TEST_APP}.base.tenant", app_tenant)
        sys.modules.setdefault(f"{TEST_APP}.base.tenant.api", app_api)
        sys.modules.setdefault(f"{TEST_APP}.base.tenant.api.idempotency", app_idem)

    def get_attr(path):
        # Mirror the composer's "{app_name}" substitution, then the real
        # frappe.get_attr's import-and-getattr resolution, so the stubbed
        # idempotency module above stays load-bearing.
        module_path, attr = path.replace("{app_name}", TEST_APP).rsplit(".", 1)
        return getattr(importlib.import_module(module_path), attr)

    frappe.get_attr = get_attr
    return frappe


def _sign(payload: bytes, secret: str, timestamp: int) -> str:
    """Builds a valid Stripe-Signature header for payload with secret."""
    signed_payload = str(timestamp).encode("utf-8") + b"." + payload
    signature = hmac.new(
        secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


@unittest.skipIf(
    HAVE_REAL_FRAPPE,
    "real frappe importable — run the FrappeTestCase suites under bench instead",
)
class FailHonestPaymentTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frappe = _install_stub_frappe()
        spec = importlib.util.spec_from_file_location(
            "wallet_payment_fail_honest_under_test", _MODULE_PATH
        )
        cls.payment = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.payment)

    def setUp(self):
        f = self.frappe
        f.session.user = "customer@example.com"
        f.conf = {}
        f.local.response = {}
        f._docs.clear()
        f._by_filters.clear()
        f._inserted.clear()
        f._error_log.clear()

    # -- helpers ---------------------------------------------------------

    def _set_webhook_request(self, payload: bytes, signature_header=None):
        headers = {}
        if signature_header is not None:
            headers["Stripe-Signature"] = signature_header
        self.frappe.request = types.SimpleNamespace(
            headers=headers, get_data=lambda: payload
        )

    def _configure_secret(self):
        self.frappe.conf = {"stripe_webhook_secret": DUMMY_SECRET}

    def _log_titles(self):
        return [title for _msg, title in self.frappe._error_log]


class TestStripeSignatureVerification(FailHonestPaymentTestCase):
    def test_valid_signature_is_accepted(self):
        payload = json.dumps({"id": "evt_1", "type": "ping"}).encode()
        header = _sign(payload, DUMMY_SECRET, int(time.time()))
        ok, reason = self.payment._verify_stripe_signature(
            payload, header, DUMMY_SECRET
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_wrong_secret_is_rejected(self):
        payload = b'{"id": "evt_1"}'
        header = _sign(
            payload, "whsec_TEST_OTHER_DUMMY_SECRET_1111", int(time.time())
        )
        ok, reason = self.payment._verify_stripe_signature(
            payload, header, DUMMY_SECRET
        )
        self.assertFalse(ok)
        self.assertIn("does not match", reason)

    def test_tampered_payload_is_rejected(self):
        payload = b'{"amount": 100}'
        header = _sign(payload, DUMMY_SECRET, int(time.time()))
        ok, _reason = self.payment._verify_stripe_signature(
            b'{"amount": 999999}', header, DUMMY_SECRET
        )
        self.assertFalse(ok)

    def test_missing_header_is_rejected(self):
        ok, reason = self.payment._verify_stripe_signature(
            b"{}", None, DUMMY_SECRET
        )
        self.assertFalse(ok)
        self.assertIn("Missing", reason)

    def test_malformed_header_is_rejected(self):
        ok, reason = self.payment._verify_stripe_signature(
            b"{}", "not-a-stripe-header", DUMMY_SECRET
        )
        self.assertFalse(ok)
        self.assertIn("Malformed", reason)

    def test_non_hex_v1_value_is_rejected_not_crashed(self):
        # hmac.compare_digest raises TypeError on non-ASCII str input;
        # the header is attacker-controlled, so garbage must yield a
        # clean rejection, never an exception (HTTP 500).
        payload = b"{}"
        now = int(time.time())
        for bad in ("café", "not-hex", "abc"):
            ok, reason = self.payment._verify_stripe_signature(
                payload, f"t={now},v1={bad}", DUMMY_SECRET
            )
            self.assertFalse(ok)
            self.assertIn("does not match", reason)

    def test_multiple_v1_signatures_any_match_accepted(self):
        # Stripe sends multiple v1 entries during secret rollover.
        payload = b"{}"
        now = int(time.time())
        good = _sign(payload, DUMMY_SECRET, now).split("v1=")[1]
        header = f"t={now},v1={'0' * 64},v1={good}"
        ok, reason = self.payment._verify_stripe_signature(
            payload, header, DUMMY_SECRET
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_stale_timestamp_is_rejected(self):
        payload = b"{}"
        stale = int(time.time()) - 301
        header = _sign(payload, DUMMY_SECRET, stale)
        ok, reason = self.payment._verify_stripe_signature(
            payload, header, DUMMY_SECRET
        )
        self.assertFalse(ok)
        self.assertIn("tolerance", reason)

    def test_stale_timestamp_accepted_within_custom_tolerance(self):
        payload = b"{}"
        stale = int(time.time()) - 301
        header = _sign(payload, DUMMY_SECRET, stale)
        ok, _reason = self.payment._verify_stripe_signature(
            payload, header, DUMMY_SECRET, tolerance_seconds=600
        )
        self.assertTrue(ok)


class TestStripeWebhookHandler(FailHonestPaymentTestCase):
    def test_no_secret_configured_fails_closed(self):
        payload = json.dumps({"id": "evt_1", "type": "ping"}).encode()
        self._set_webhook_request(
            payload, _sign(payload, DUMMY_SECRET, int(time.time()))
        )
        # No secret in conf and no Stripe gateway doc.
        result = self.payment.handle_stripe_webhook()
        self.assertEqual(result["status"], "error")
        self.assertEqual(
            self.frappe.local.response["http_status_code"], 400
        )
        self.assertIn("Stripe Webhook Rejected", self._log_titles())

    def test_invalid_signature_is_rejected_with_400_and_logged(self):
        self._configure_secret()
        payload = b'{"id": "evt_1", "type": "ping"}'
        self._set_webhook_request(
            payload,
            _sign(payload, "whsec_TEST_OTHER_DUMMY_SECRET_1111", int(time.time())),
        )
        result = self.payment.handle_stripe_webhook()
        self.assertEqual(result["status"], "error")
        self.assertEqual(
            self.frappe.local.response["http_status_code"], 400
        )
        self.assertIn("Stripe Webhook Rejected", self._log_titles())

    def test_missing_signature_header_is_rejected_with_400(self):
        self._configure_secret()
        self._set_webhook_request(b"{}", signature_header=None)
        result = self.payment.handle_stripe_webhook()
        self.assertEqual(result["status"], "error")
        self.assertEqual(
            self.frappe.local.response["http_status_code"], 400
        )

    def test_unhandled_event_is_logged_and_acknowledged_honestly(self):
        self._configure_secret()
        payload = json.dumps(
            {"id": "evt_42", "type": "payment_intent.succeeded"}
        ).encode()
        self._set_webhook_request(
            payload, _sign(payload, DUMMY_SECRET, int(time.time()))
        )
        result = self.payment.handle_stripe_webhook()
        # Honest body: never {"status": "success"} for work not done.
        self.assertEqual(
            result,
            {"status": "unhandled", "event": "payment_intent.succeeded"},
        )
        # No error status set: Stripe gets a 200 and stops retrying.
        self.assertNotIn(
            "http_status_code", self.frappe.local.response
        )
        # Durably logged.
        self.assertIn("Stripe Webhook Unhandled", self._log_titles())
        message, _title = self.frappe._error_log[-1]
        self.assertIn("payment_intent.succeeded", message)
        self.assertIn("evt_42", message)

    def test_secret_from_gateway_settings_doc_is_used(self):
        payload = json.dumps({"id": "evt_9", "type": "ping"}).encode()
        self.frappe._docs[("PaaS Payment Gateway", "Stripe")] = _Doc(
            name="Stripe",
            settings=[
                types.SimpleNamespace(
                    key="webhook_secret", value=DUMMY_SECRET
                )
            ],
        )
        self._set_webhook_request(
            payload, _sign(payload, DUMMY_SECRET, int(time.time()))
        )
        result = self.payment.handle_stripe_webhook()
        self.assertEqual(result["status"], "unhandled")

    def test_signed_but_invalid_json_is_rejected_with_400(self):
        self._configure_secret()
        payload = b"this is not json"
        self._set_webhook_request(
            payload, _sign(payload, DUMMY_SECRET, int(time.time()))
        )
        result = self.payment.handle_stripe_webhook()
        self.assertEqual(result["status"], "error")
        self.assertEqual(
            self.frappe.local.response["http_status_code"], 400
        )


class TestNotImplementedMoneyPaths(FailHonestPaymentTestCase):
    def test_payfast_token_payment_raises_not_implemented(self):
        with self.assertRaises(self.frappe.ValidationError) as ctx:
            self.payment.process_payfast_token_payment("ORD-0001", "tok_x")
        self.assertIn("not implemented", str(ctx.exception))
        self.assertIn("ORD-0001", str(ctx.exception))

    def test_direct_card_payment_raises_and_writes_nothing(self):
        self.frappe._docs[("Order", "ORD-0001")] = _Doc(
            name="ORD-0001",
            user="customer@example.com",
            grand_total=150.0,
            status="Pending",
        )
        with self.assertRaises(self.frappe.ValidationError) as ctx:
            self.payment.process_direct_card_payment(
                "ORD-0001", "4111111111111111", "Test User", "12/30", "123"
            )
        self.assertIn("not implemented", str(ctx.exception))
        # Nothing was recorded and the order was not marked paid.
        self.assertEqual(self.frappe._inserted, [])
        order = self.frappe._docs[("Order", "ORD-0001")]
        self.assertEqual(order.status, "Pending")

    def test_charge_card_token_unsupported_gateway_raises(self):
        f = self.frappe
        f._by_filters[
            (
                "Saved Card",
                (("token", "tok_x"), ("user", "customer@example.com")),
            )
        ] = "CARD-0001"
        f._docs[("Saved Card", "CARD-0001")] = _Doc(
            name="CARD-0001", gateway="Unknown Gateway", token="tok_x"
        )
        with self.assertRaises(f.ValidationError) as ctx:
            self.payment._charge_card_token(
                "tok_x", 100.0, "ZAR", "test charge", "customer@example.com"
            )
        self.assertIn("No charge was performed", str(ctx.exception))
        self.assertIn("Payment Error", self._log_titles())


if __name__ == "__main__":
    unittest.main()
