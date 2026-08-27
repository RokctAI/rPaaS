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

"""Unit tests for list_orders' status/page parameters
(src/tenant/api/order/order.py).

The dart client (src/common/infrastructure/repositories/
orders_repository.dart, getOrders) sends
{"page": N, "limit_page_length": 10, "status": "delivered"|"accepted"?}
through the platform gateway. These tests pin the server-side contract:

  * page is 1-based and translates to
    limit_start = (page - 1) * limit_page_length;
  * status filters the query, matched case-insensitively against the
    Order doctype's Select options (dart sends lowercase);
  * both are optional - callers that omit them keep the pre-existing
    limit_start/limit_page_length behavior byte-for-byte.

Reuses the offline stub harness of test_weather_order_notice.py (no
bench, no network); the bench-only sibling test_api_order.py keeps
exercising the endpoint against a real site.
"""

import types
import unittest

from test_weather_order_notice import order_api


STATUS_OPTIONS = "New\nAccepted\nShipped\nDelivered\nCancelled\nPaid\nFailed"


class ListOrdersParamsCase(unittest.TestCase):
    def setUp(self):
        self._orig_frappe = order_api.frappe
        self._orig_notice = getattr(order_api, "order_weather_notice", None)
        # keep the weather hook quiet: these tests are about params only
        order_api.order_weather_notice = None
        self.calls = []

        def get_list(doctype, **kwargs):
            self.calls.append((doctype, kwargs))
            return []

        meta_field = types.SimpleNamespace(options=STATUS_OPTIONS)
        meta = types.SimpleNamespace(get_field=lambda name: meta_field)
        self.fake = types.SimpleNamespace(
            session=types.SimpleNamespace(user="customer@example.com"),
            get_list=get_list,
            get_meta=lambda doctype: meta,
        )
        order_api.frappe = self.fake

    def tearDown(self):
        order_api.frappe = self._orig_frappe
        order_api.order_weather_notice = self._orig_notice

    def kwargs(self):
        self.assertEqual(len(self.calls), 1)
        doctype, kwargs = self.calls[0]
        self.assertEqual(doctype, "Order")
        return kwargs

    # ------------------------------------------------------------------ #
    # back-compat: omitted params keep the old query exactly
    # ------------------------------------------------------------------ #

    def test_omitting_both_keeps_the_legacy_query(self):
        order_api.list_orders()
        kwargs = self.kwargs()
        self.assertEqual(kwargs["filters"], {"user": "customer@example.com"})
        self.assertEqual(kwargs["offset"], 0)
        self.assertEqual(kwargs["limit"], 20)

    def test_legacy_limit_start_still_honored_without_page(self):
        order_api.list_orders(limit_start=40, limit_page_length=10)
        kwargs = self.kwargs()
        self.assertEqual(kwargs["offset"], 40)
        self.assertEqual(kwargs["limit"], 10)

    # ------------------------------------------------------------------ #
    # page: the dart client's 1-based pagination
    # ------------------------------------------------------------------ #

    def test_page_one_starts_at_offset_zero(self):
        order_api.list_orders(page=1, limit_page_length=10)
        self.assertEqual(self.kwargs()["offset"], 0)

    def test_page_translates_to_limit_start(self):
        order_api.list_orders(page=3, limit_page_length=10)
        kwargs = self.kwargs()
        self.assertEqual(kwargs["offset"], 20)
        self.assertEqual(kwargs["limit"], 10)

    def test_page_overrides_limit_start(self):
        order_api.list_orders(limit_start=999, page=2, limit_page_length=10)
        self.assertEqual(self.kwargs()["offset"], 10)

    def test_string_page_from_form_data_is_coerced(self):
        order_api.list_orders(page="2", limit_page_length="10")
        self.assertEqual(self.kwargs()["offset"], 10)

    def test_malformed_page_keeps_limit_start_as_passed(self):
        order_api.list_orders(limit_start=5, page="junk")
        self.assertEqual(self.kwargs()["offset"], 5)

    def test_page_below_one_clamps_to_first_page(self):
        order_api.list_orders(page=0, limit_page_length=10)
        self.assertEqual(self.kwargs()["offset"], 0)

    # ------------------------------------------------------------------ #
    # status: the dart client's lowercase filter values
    # ------------------------------------------------------------------ #

    def test_lowercase_status_normalized_to_select_option(self):
        order_api.list_orders(status="delivered")
        self.assertEqual(
            self.kwargs()["filters"],
            {"user": "customer@example.com", "status": "Delivered"})

    def test_exact_case_status_passes_through(self):
        order_api.list_orders(status="Accepted")
        self.assertEqual(self.kwargs()["filters"]["status"], "Accepted")

    def test_unknown_status_filters_on_raw_value(self):
        order_api.list_orders(status="teleported")
        self.assertEqual(self.kwargs()["filters"]["status"], "teleported")

    def test_missing_meta_falls_back_to_raw_value(self):
        del self.fake.get_meta  # stub shells may have no meta at all
        order_api.list_orders(status="delivered")
        self.assertEqual(self.kwargs()["filters"]["status"], "delivered")

    def test_empty_status_adds_no_filter(self):
        order_api.list_orders(status="")
        self.assertEqual(
            self.kwargs()["filters"], {"user": "customer@example.com"})

    def test_status_and_page_combine(self):
        order_api.list_orders(page=2, limit_page_length=10, status="accepted")
        kwargs = self.kwargs()
        self.assertEqual(kwargs["offset"], 10)
        self.assertEqual(kwargs["filters"]["status"], "Accepted")


if __name__ == "__main__":
    unittest.main()
