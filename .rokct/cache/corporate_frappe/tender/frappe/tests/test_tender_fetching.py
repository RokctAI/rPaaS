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
# See license.txt

# This file uses the composer's literal {app_name} template placeholder in
# imports (fleet SDK convention, cf. polaris) - it only parses after
# composition substitutes the real app package name.
# compliance-ignore-file: syntax-error

"""Contract tests for the direct eTenders fetcher (findings F-14).

These tests specify SINGLE-RELEASE ID ENUMERATION, never list pagination:
the eTenders list endpoint has unstable offset pagination that silently
drops records (verified live 2026-08-20), so _fetch_and_cache_tenders_on_control
enumerates GET {etenders_api_url}/release/ocds-9t57fa-{N} by sequential
integer id instead. The contract proven here:

- gap fetch: every id above the persisted max is fetched and cached
- trailing re-fetch: a window of recent ids below the max is re-fetched
  (compiled releases gain awards/amendments after first publication)
- "{}" responses (never-published ids) are skipped, and a run of them
  terminates the upward scan
- persistent 500 ids are skipped after bounded retries without ending the run
- Raw Tender Cache rows are deduped/upserted by ocid
- the new max id is persisted on Tender Control Settings
"""

import frappe
import json
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock
import importlib

has_app = importlib.util.find_spec("{app_name}") is not None

BASE_URL = "http://mock-api.com"


def release(n, title, amended=False):
	"""A minimal single-release payload for integer id n."""
	payload = {
		"ocid": f"ocds-9t57fa-{n}",
		"id": f"ocds-9t57fa-{n}-2026-08-20",
		"tag": ["compiled"],
		"tender": {"id": str(n), "title": title},
	}
	if amended:
		payload["tag"] = ["compiled", "tenderAmendment"]
	return payload


def single_release_endpoint(responses):
	"""Builds a requests.get side effect serving the SINGLE-RELEASE endpoint.

	``responses`` maps integer release id -> a release dict, {} (never
	published), or the string "500" (persistent server error). Ids not in the
	map answer the API's real beyond-the-max behaviour: a stable "{}".
	Also asserts the fetcher never touches the lossy list endpoint.
	"""

	def fake_get(url, *args, **kwargs):
		assert "?" not in url and "PageNumber" not in url, (
			"list-endpoint pagination is forbidden (findings F-14): " + url
		)
		assert url.startswith(f"{BASE_URL}/release/ocds-9t57fa-"), url
		release_id = int(url.rsplit("-", 1)[1])
		spec = responses.get(release_id, {})
		mock_response = MagicMock()
		if spec == "500":
			mock_response.status_code = 500
			mock_response.json.return_value = None
		else:
			mock_response.status_code = 200
			mock_response.json.return_value = spec
		fake_get.calls.append(release_id)
		return mock_response

	fake_get.calls = []
	return fake_get


class TestTenderFetching(FrappeTestCase):
	def setUp(self):
		if not has_app:
			self.skipTest("{app_name} app not installed")
		frappe.db.delete("Raw Tender Cache")
		frappe.db.set_single_value("Tender Control Settings", "last_fetched_release_id", 0)
		frappe.db.commit()

	def _run(self, responses, last_max, refetch_window=2):
		from {app_name}.tender.control.tasks import _fetch_and_cache_tenders_on_control

		frappe.db.set_single_value(
			"Tender Control Settings", "last_fetched_release_id", last_max
		)
		frappe.db.set_single_value(
			"Tender Control Settings", "refetch_window_ids", refetch_window
		)
		fake_get = single_release_endpoint(responses)
		with (
			patch("{app_name}.tender.control.tasks.requests.get", side_effect=fake_get),
			patch("{app_name}.tender.control.tasks.time.sleep"),
			patch.dict(
				frappe.conf,
				{"app_role": "control", "etenders_api_url": BASE_URL},
			),
		):
			stats = _fetch_and_cache_tenders_on_control()
		return stats, fake_get

	def test_gap_fetch_and_max_persistence(self):
		"""Ids above the persisted max are fetched; the new max is persisted."""
		stats, fake_get = self._run(
			{
				99: release(99, "Recent Tender 99"),
				100: release(100, "Recent Tender 100"),
				101: release(101, "New Tender 101"),
				102: release(102, "New Tender 102"),
				# 103.. answer "{}" - beyond the current max
			},
			last_max=100,
		)

		self.assertEqual(frappe.db.count("Raw Tender Cache"), 4)
		titles = [
			json.loads(t.data)["tender"]["title"]
			for t in frappe.get_all("Raw Tender Cache", fields=["data"])
		]
		self.assertIn("New Tender 101", titles)
		self.assertIn("New Tender 102", titles)
		self.assertEqual(stats["last_max_after"], 102)
		self.assertEqual(
			frappe.db.get_single_value("Tender Control Settings", "last_fetched_release_id"),
			102,
		)
		# trailing window (99, 100) was re-fetched before the gap scan
		self.assertEqual(fake_get.calls[:2], [99, 100])

	def test_trailing_refetch_upserts_amendments_by_ocid(self):
		"""A recent id already cached is re-fetched and UPDATED, not duplicated."""
		# first run caches ids 99-101
		self._run(
			{
				99: release(99, "Tender 99"),
				100: release(100, "Tender 100"),
				101: release(101, "Tender 101"),
			},
			last_max=100,
		)
		self.assertEqual(frappe.db.count("Raw Tender Cache"), 3)

		# second run: 101 gained an amendment; 102 is newly published
		stats, _ = self._run(
			{
				100: release(100, "Tender 100"),
				101: release(101, "Tender 101 AMENDED", amended=True),
				102: release(102, "Tender 102"),
			},
			last_max=101,
		)

		# ocid dedup: 99-102 -> 4 rows, never a second row per ocid
		self.assertEqual(frappe.db.count("Raw Tender Cache"), 4)
		self.assertEqual(stats["updated"], 2)  # 100 and 101 upserted in place
		row = frappe.get_all(
			"Raw Tender Cache",
			filters={"ocid": "ocds-9t57fa-101"},
			fields=["data"],
		)
		self.assertEqual(len(row), 1)
		self.assertEqual(
			json.loads(row[0].data)["tender"]["title"], "Tender 101 AMENDED"
		)

	def test_unpublished_holes_and_persistent_500s_are_skipped(self):
		"""'{}' ids and persistent-500 ids are skipped without ending the scan."""
		from {app_name}.tender.control import tasks as tasks_module

		stats, fake_get = self._run(
			{
				100: release(100, "Tender 100"),
				101: {},  # never published - a hole inside the id space
				102: "500",  # persistent server error - skip after retries
				103: release(103, "Tender 103"),
			},
			last_max=100,
			refetch_window=1,
		)

		titles = [
			json.loads(t.data)["tender"]["title"]
			for t in frappe.get_all("Raw Tender Cache", fields=["data"])
		]
		self.assertIn("Tender 103", titles)  # the scan continued past 101 and 102
		self.assertEqual(stats["errors"], 1)
		self.assertGreaterEqual(stats["unpublished"], tasks_module.EMPTY_RUN_LIMIT)
		self.assertEqual(stats["last_max_after"], 103)
		# the 500 id was retried, not abandoned on first failure
		self.assertEqual(
			len([c for c in fake_get.calls if c == 102]), tasks_module.RETRY_ATTEMPTS
		)

	def test_non_control_role_is_a_no_op(self):
		"""Like the sibling scheduled task, only the control hub fetches."""
		from {app_name}.tender.control.tasks import _fetch_and_cache_tenders_on_control

		fake_get = single_release_endpoint({})
		with (
			patch("{app_name}.tender.control.tasks.requests.get", side_effect=fake_get),
			patch.dict(frappe.conf, {"app_role": "tenant", "etenders_api_url": BASE_URL}),
		):
			result = _fetch_and_cache_tenders_on_control()

		self.assertIsNone(result)
		self.assertEqual(fake_get.calls, [])
		self.assertEqual(frappe.db.count("Raw Tender Cache"), 0)
