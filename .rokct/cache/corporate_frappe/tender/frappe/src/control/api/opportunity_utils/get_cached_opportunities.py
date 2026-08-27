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
from {app_name}.tender.control.api.opportunity_utils import CACHE_TTL, fetch_remote_json, refresh_all_data

def get_cached_opportunities(opt_type):
	cache = frappe.cache()
	cache_key = f"opp_data_{opt_type}"
	meta_cache = "opp_data_meta"
	last_check_cache = "opp_last_check"

	data = cache.get_value(cache_key)
	cached_meta = cache.get_value(meta_cache)
	last_check = cache.get_value(last_check_cache)

	now = datetime.now()

	should_refresh = False
	if (not data and opt_type != "meta") or not cached_meta or not last_check:
		should_refresh = True
	elif (now - datetime.fromisoformat(last_check)).total_seconds() > CACHE_TTL:
		# TTL expired, check if we need to refresh
		remote_meta = fetch_remote_json("meta")
		if remote_meta and remote_meta.get("last_sync") != cached_meta.get("last_sync"):
			should_refresh = True
		else:
			# Meta is same, just extend the check time
			cache.set_value(last_check_cache, now.isoformat())

	if should_refresh:
		refresh_all_data()
		data = cache.get_value(cache_key)

	if opt_type == "meta":
		return data or {}
	return data or []
