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

BASE_URL = "https://raw.githubusercontent.com/RokctAI/opportunities/main/published/api/"
CACHE_TTL = 86400  # 24 hours in seconds


def get_catalog_base_url():
	"""The published-catalog base URL the fetch layer reads from.

	Tender Control Settings.catalog_base_url when set, else the shipped
	BASE_URL default (plan #3 of tender/SDK-Assessment-2026-08-24.md: the
	light data-source seam - staging/test catalogs without code edits; a
	full forex-style provider abstraction is deliberately NOT built for one
	national feed). Stub-safe: any lookup failure (no site context,
	standalone verify runs) means the shipped default. Always returns a
	trailing slash so '{file_name}.json' appends cleanly.
	"""
	try:
		import frappe

		configured = frappe.db.get_single_value("Tender Control Settings", "catalog_base_url")
	except Exception:
		configured = None
	url = str(configured or "").strip() or BASE_URL
	return url if url.endswith("/") else url + "/"

from {app_name}.tender.control.api.opportunity_utils.get_opportunities_from_json import get_opportunities_from_json
from {app_name}.tender.control.api.opportunity_utils.get_cached_opportunities import get_cached_opportunities
from {app_name}.tender.control.api.opportunity_utils.refresh_all_data import refresh_all_data
from {app_name}.tender.control.api.opportunity_utils.fetch_remote_json import fetch_remote_json
from {app_name}.tender.control.api.opportunity_utils.validate_tenant_secret import validate_tenant_secret

