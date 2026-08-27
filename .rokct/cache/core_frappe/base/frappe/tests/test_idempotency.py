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
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime

from {app_name}.api.idempotency import (
    IDEMPOTENCY_HEADER,
    get_idempotency_key,
    idempotent,
)
from {app_name}.api.utils import api_response


class _FakeRequest:
    """Stands in for frappe.local.request so the guard sees a header."""

    def __init__(self, headers=None):
        self.headers = headers or {}


_calls = {"count": 0}


@idempotent
def _create_widget(value):
    """A write endpoint stand-in: counts real executions."""
    _calls["count"] += 1
    return api_response(data={"value": value}, message="created")


class TestIdempotencyGuard(FrappeTestCase):
    KEY = "11111111-2222-3333-4444-555555555555"

    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.delete("Idempotency Key", {"idempotency_key": self.KEY})
        _calls["count"] = 0
        self._had_request = hasattr(frappe.local, "request")
        self._old_request = getattr(frappe.local, "request", None)

    def tearDown(self):
        if self._had_request:
            frappe.local.request = self._old_request
        elif hasattr(frappe.local, "request"):
            del frappe.local.request
        frappe.db.delete("Idempotency Key", {"idempotency_key": self.KEY})

    def _set_header(self, key):
        frappe.local.request = _FakeRequest({IDEMPOTENCY_HEADER: key})

    def test_no_header_executes_every_time(self):
        frappe.local.request = _FakeRequest({})
        _create_widget(1)
        _create_widget(1)
        self.assertEqual(_calls["count"], 2)

    def test_header_is_read_from_request(self):
        self._set_header(self.KEY)
        self.assertEqual(get_idempotency_key(), self.KEY)

    def test_oversized_key_is_rejected(self):
        self._set_header("x" * 200)
        self.assertRaises(frappe.ValidationError, get_idempotency_key)

    def test_repeat_key_replays_stored_response(self):
        self._set_header(self.KEY)

        first = _create_widget(42)
        self.assertEqual(_calls["count"], 1)
        self.assertNotIn("idempotent_replay", first)

        second = _create_widget(42)
        # The endpoint body did NOT run again ...
        self.assertEqual(_calls["count"], 1)
        # ... and the caller got the original payload, marked as a replay.
        self.assertTrue(second["idempotent_replay"])
        self.assertEqual(second["data"]["value"], 42)
        self.assertEqual(second["message"], "created")

    def test_key_is_scoped_to_user(self):
        self._set_header(self.KEY)
        _create_widget(1)

        frappe.set_user("Guest")
        try:
            self.assertRaises(frappe.ValidationError, _create_widget, 1)
        finally:
            frappe.set_user("Administrator")
        # The other user's attempt must not have executed the endpoint.
        self.assertEqual(_calls["count"], 1)

    def test_purge_drops_only_expired_keys(self):
        from {app_name}.base.tenant.core.tasks import purge_expired_idempotency_keys

        self._set_header(self.KEY)
        _create_widget(1)

        # Age the row past retention, then purge.
        frappe.db.set_value(
            "Idempotency Key",
            self.KEY,
            "creation",
            add_days(now_datetime(), -31),
            update_modified=False,
        )
        purge_expired_idempotency_keys()
        self.assertFalse(frappe.db.exists("Idempotency Key", self.KEY))

        # A fresh key survives the purge.
        _create_widget(2)
        purge_expired_idempotency_keys()
        self.assertTrue(frappe.db.exists("Idempotency Key", self.KEY))
