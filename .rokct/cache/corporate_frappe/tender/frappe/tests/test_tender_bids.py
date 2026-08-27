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

# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# See license.txt

# This file uses the composer's literal {app_name} template placeholder in
# imports (fleet SDK convention, cf. polaris) - it only parses after
# composition substitutes the real app package name.
# compliance-ignore-file: syntax-error

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch

from {app_name}.tender.control.api.tenders import (
	claim_tender,
	get_my_bids,
	get_tender_detail,
	update_bid_status,
	update_checklist_item,
)
from {app_name}.tender.control.api.tenders.tender_entitlement import (
	get_generic_default_tasks,
	parse_enrichment_task,
)

TEST_SLUG = "ocds-test-0001"
TEST_META = {
	"last_sync": "2026-07-26T00:00:00",
	"global_defaults": ["Review Tender Documents", "Prepare Initial Response"],
	"advanced_enrichment": {
		TEST_SLUG: {
			"enrichment": "ADVANCED",
			"tasks": [
				"Complete and sign all mandatory forms: SBD 4, SBD 6 | 1",
				"Draft detailed methodology | 3",
			],
		}
	},
}
TEST_TENDERS = [
	{
		"title": "Test Tender",
		"tender_number": TEST_SLUG,
		"slug": TEST_SLUG,
		"institution": "Test Municipality",
		"closing_date": "2026-08-15",
	}
]


def mock_cached(opt_type):
	return TEST_META if opt_type == "meta" else (TEST_TENDERS if opt_type == "tenders" else [])


class TestTenderBids(FrappeTestCase):
	def setUp(self):
		frappe.conf.app_role = "control"
		frappe.set_user("Administrator")
		frappe.db.delete("Bid Checklist Item")
		frappe.db.delete("Tender Bid")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Bid Checklist Item")
		frappe.db.delete("Tender Bid")

	# ── helpers ──────────────────────────────────────────────────────────

	def test_parse_enrichment_task(self):
		self.assertEqual(
			parse_enrichment_task("Draft methodology | 3"),
			{"task_text": "Draft methodology", "weight": 3},
		)
		self.assertEqual(
			parse_enrichment_task("Review Tender Documents"),
			{"task_text": "Review Tender Documents", "weight": 0},
		)
		# a "|" without a numeric tail stays in the text
		self.assertEqual(
			parse_enrichment_task("Points for Price | Goals"),
			{"task_text": "Points for Price | Goals", "weight": 0},
		)

	def test_generic_defaults_list_shape(self):
		with patch(
			"{app_name}.tender.control.api.opportunity_utils.get_cached_opportunities",
			side_effect=mock_cached,
		):
			self.assertEqual(
				get_generic_default_tasks(),
				["Review Tender Documents", "Prepare Initial Response"],
			)

	# ── detail gating ────────────────────────────────────────────────────

	@patch("{app_name}.tender.control.api.opportunity_utils.get_cached_opportunities", side_effect=mock_cached)
	def test_detail_entitled_gets_advanced(self, _mock):
		# Administrator is entitled via the admin bypass
		result = get_tender_detail(TEST_SLUG)
		self.assertTrue(result["entitled"])
		self.assertEqual(result["enrichment_level"], "ADVANCED")
		self.assertTrue(result["advanced_available"])
		self.assertEqual(result["tasks"][0]["task_text"], "Complete and sign all mandatory forms: SBD 4, SBD 6")
		self.assertEqual(result["tasks"][1]["weight"], 3)

	@patch("{app_name}.tender.control.api.opportunity_utils.get_cached_opportunities", side_effect=mock_cached)
	def test_detail_guest_gets_teaser_only(self, _mock):
		frappe.set_user("Guest")
		try:
			result = get_tender_detail(TEST_SLUG)
		finally:
			frappe.set_user("Administrator")
		self.assertFalse(result["entitled"])
		self.assertEqual(result["enrichment_level"], "GENERIC")
		# the teaser must still advertise that a real checklist exists...
		self.assertTrue(result["advanced_available"])
		# ...but never contain it
		texts = [t["task_text"] for t in result["tasks"]]
		self.assertNotIn("Complete and sign all mandatory forms: SBD 4, SBD 6", texts)
		self.assertIn("Review Tender Documents", texts)

	@patch("{app_name}.tender.control.api.opportunity_utils.get_cached_opportunities", side_effect=mock_cached)
	def test_detail_unknown_slug_raises(self, _mock):
		with self.assertRaises(frappe.DoesNotExistError):
			get_tender_detail("no-such-tender")

	# ── claim + checklist lifecycle ──────────────────────────────────────

	@patch("{app_name}.tender.control.api.opportunity_utils.get_cached_opportunities", side_effect=mock_cached)
	def test_claim_seeds_checklist_and_is_idempotent(self, _mock):
		bid = claim_tender(TEST_SLUG)
		self.assertEqual(bid["tender_slug"], TEST_SLUG)
		self.assertEqual(bid["enrichment_level"], "ADVANCED")
		self.assertEqual(bid["status"], "Watching")
		self.assertEqual(len(bid["checklist"]), 2)
		self.assertEqual(bid["checklist"][0]["weight"], 1)

		again = claim_tender(TEST_SLUG)
		self.assertEqual(again["name"], bid["name"])
		self.assertEqual(frappe.db.count("Tender Bid"), 1)

	@patch("{app_name}.tender.control.api.opportunity_utils.get_cached_opportunities", side_effect=mock_cached)
	def test_claim_requires_entitlement(self, _mock):
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				claim_tender(TEST_SLUG)
		finally:
			frappe.set_user("Administrator")

	@patch("{app_name}.tender.control.api.opportunity_utils.get_cached_opportunities", side_effect=mock_cached)
	def test_checklist_toggle_and_progress(self, _mock):
		bid = claim_tender(TEST_SLUG)
		item = bid["checklist"][0]["name"]

		result = update_checklist_item(bid["name"], item, 1)
		self.assertEqual(result["status"], "Done")

		bids = get_my_bids()
		self.assertEqual(len(bids), 1)
		self.assertEqual(bids[0]["tasks_total"], 2)
		self.assertEqual(bids[0]["tasks_done"], 1)

		result = update_checklist_item(bid["name"], item, 0)
		self.assertEqual(result["status"], "Open")

	@patch("{app_name}.tender.control.api.opportunity_utils.get_cached_opportunities", side_effect=mock_cached)
	def test_status_lifecycle_and_ownership(self, _mock):
		bid = claim_tender(TEST_SLUG)

		updated = update_bid_status(bid["name"], "Submitted")
		self.assertEqual(updated["status"], "Submitted")
		self.assertIsNotNone(updated["submitted_on"])

		updated = update_bid_status(bid["name"], "Awarded", outcome_value=150000, outcome_notes="Won")
		self.assertEqual(updated["status"], "Awarded")

		with self.assertRaises(frappe.ValidationError):
			update_bid_status(bid["name"], "NotAStatus")

		# another user must not be able to touch this bid
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.PermissionError):
				update_bid_status(bid["name"], "Lost")
		finally:
			frappe.set_user("Administrator")
