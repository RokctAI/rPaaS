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

# This file uses the composer's literal {app_name} template placeholder in
# imports (fleet SDK convention, cf. polaris) - it only parses after
# composition substitutes the real app package name.
# compliance-ignore-file: syntax-error

import frappe
import json
import requests
from datetime import datetime, timedelta
from {app_name}.tender.control.api.opportunity_utils import get_cached_opportunities

def get_opportunities_from_json(opportunity_type, filters=None, public=False):
	"""
	Reads and filters opportunities from the opportunities repository on GitHub.
	Implements caching with meta.json validation.
	"""
	data = get_cached_opportunities(opportunity_type)
	meta = get_cached_opportunities("meta")

	# Global defaults can be indexed by slug, but we also want a generic fallback.
	global_defaults = meta.get("global_defaults") if isinstance(meta.get("global_defaults"), dict) else {}
	generic_tasks = meta.get("generic_defaults", {}).get("tasks", [])

	processed_data = []
	for item in data:
		# Clone item to avoid modifying cached data
		item = item.copy()

		if public:
			# Hide advanced enrichment for public/frontend use
			item.pop("advanced_enrichment", None)

		# Metadata merging: Inject slug if missing
		if "slug" not in item:
			item["slug"] = item.get("tender_number") or item.get("ocid")

		slug = item.get("slug")

		# Task Merging:
		# 1. Item's own tasks (priority)
		# 2. Slug-specific tasks from global_defaults
		# 3. Generic fallback tasks
		if not item.get("tasks"):
			slug_defaults = global_defaults.get(slug) if isinstance(global_defaults, dict) else None
			if isinstance(slug_defaults, dict) and slug_defaults.get("tasks"):
				item["tasks"] = slug_defaults.get("tasks")
			else:
				item["tasks"] = generic_tasks

		processed_data.append(item)

	data = processed_data

	if not filters:
		return data

	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except json.JSONDecodeError:
			return data

	filtered_data = []

	recent_only = filters.pop("recent_only", False)
	limit_date = None
	if recent_only:
		limit_date = datetime.now() - timedelta(days=3)

	for item in data:
		match = True

		if limit_date:
			last_verified = item.get("last_verified")
			if last_verified:
				try:
					item_date = datetime.strptime(last_verified, "%Y-%m-%d")
					if item_date < limit_date:
						match = False
				except ValueError:
					pass

		if match:
			for key, value in filters.items():
				item_value = item.get(key)

				# Support for "like" filters: {"title": ["like", "%query%"]}
				if isinstance(value, list) and len(value) == 2 and value[0] == "like":
					search_term = value[1].replace("%", "").lower()
					if not item_value or search_term not in str(item_value).lower():
						match = False
						break
				elif item_value != value:
					match = False
					break

		if match:
			filtered_data.append(item)

	return filtered_data
