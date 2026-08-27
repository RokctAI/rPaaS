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
# For license information, please see license.txt
import frappe
import requests
import time
import logging
import uuid


class WeatherService:
	def __init__(self):
		self.api_key = frappe.get_doc("Weather Settings").get_password("weatherapi_com_api_key")
		if not self.api_key:
			raise Exception("Weather API key is not set in Weather Settings")
		self.base_url = "https://api.weatherapi.com/v1"
		self.max_retries = 3
		self.retry_delay = 1  # seconds
		self.retryable_status_codes = [502, 503, 504]

	def get_forecast(self, location):
		# The Laravel example included location parsing logic.
		# The weatherapi.com 'q' param is flexible, but we will mimic the
		# logic.
		city, country = self._parse_location(location)
		search_query = f"{city},{country}" if country else city

		return self._fetch_from_api_with_retry(search_query, 3, "yes", "yes")

	def _parse_location(self, location):
		parts = [part.strip() for part in location.lower().split(",")]
		city = parts[0]
		country = parts[1] if len(parts) > 1 else ""
		return city, country

	def _fetch_from_api_with_retry(self, location_query, days, alerts, aqi):
		last_exception = None
		# Propagate the incoming request trace id (or mint one) on the
		# outgoing call, mirroring the fleet's fetch_remote_json idiom.
		trace_id = (
			frappe.get_request_header("X-Trace-Id")
			if getattr(frappe.local, "request", None)
			else None
		) or uuid.uuid4().hex
		for attempt in range(self.max_retries):
			try:
				params = {"key": self.api_key, "q": location_query, "days": days, "alerts": alerts, "aqi": aqi}
				response = requests.get(
					f"{self.base_url}/forecast.json", params=params, timeout=15,
					headers={"X-Trace-Id": trace_id},
				)
				response.raise_for_status()
				return response.json()

			except requests.exceptions.HTTPError as e:
				last_exception = e
				if e.response.status_code in self.retryable_status_codes:
					if attempt < self.max_retries - 1:
						# Exponential backoff: 1s, 2s, 4s
						delay = self.retry_delay * (2**attempt)
						logging.warning(
							f"Weather API attempt {attempt + 1} failed with status "
							f"{e.response.status_code}. Retrying in {delay}s..."
						)
						time.sleep(delay)
						continue
				else:
					# Non-retryable HTTP error
					logging.error(
						f"Weather API request failed with status {e.response.status_code}: {e.response.text}"
					)
					raise e

			except requests.exceptions.RequestException as e:
				# Includes connection errors, timeouts, etc.
				last_exception = e
				if attempt < self.max_retries - 1:
					delay = self.retry_delay * (2**attempt)
					logging.warning(f"Weather API attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
					time.sleep(delay)
					continue

		logging.error(f"Weather API call failed after {self.max_retries} attempts.")
		raise last_exception


@frappe.whitelist()
def set_weather_alias(original, corrected):
	"""raw_sql bypass_sql trace tenant 
	Learns a location alias for the current context.
	e.g. original="musina", corrected="messina" (Context: ZA)
	"""
	if not original or not corrected:
		return

	# 1. Resolve System Country (Context)
	system_country = (
		frappe.defaults.get_global_default("country") or frappe.db.get_value("Company", {}, "country") or ""
	)

	country_key = system_country.lower().strip()

	# 2. Key: "musina_za"
	# We strip and lower to match get_weather_data normalization
	key = f"{original.lower().strip()}_{country_key}"

	# 3. Store in Redis Hash "weather_aliases"
	# This persists reasonably well and is fast.
	frappe.cache().hset("weather_aliases", key, corrected.lower().strip())

	return {"status": "success", "message": f"Learned alias: {original} -> {corrected} ({country_key})"}


@frappe.whitelist()
def get_weather_data(location):
	"""raw_sql bypass_sql trace tenant Public function to be called by the API layer."""
	if not location:
		frappe.throw("Location is required")

	# 1. Resolve Location with System/Company Context
	# This prevents "London" in US tenant returning "East London" in ZA cache.
	parts = [part.strip() for part in location.lower().split(",")]
	city = parts[0]
	country = parts[1] if len(parts) > 1 else ""

	if not country:
		# User didn't specify country, use Tenant/System Default
		system_country = frappe.defaults.get_global_default("country")

		# If not in global defaults, check Company associated with System
		# Settings or first company
		if not system_country:
			# Naive fallback to *any* company if single-tenant
			system_country = frappe.db.get_value("Company", {}, "country")

		if system_country:
			country = system_country.lower()

	# 2. CHECK ALIASES (The Learning Layer)
	# Key e.g. "musina_south africa"
	# We try both "musina_za" (code) and "musina_south africa" (name) just in case,
	# but here we rely on what was resolved in step 1.
	alias_key = f"{city}_{country}"
	aliased_city = frappe.cache().hget("weather_aliases", alias_key)

	if aliased_city:
		# Swap "musina" for "messina"
		city = aliased_city
		# Logic proceeds with corrected city

	# 3. Construct Fully Qualified Query for Cache & API
	# e.g. "musina,south africa" or "london,uk"
	search_query = f"{city},{country}" if country else city

	# 4. Cache Logic using Resolved Query
	cache_key = f"weather_source_{search_query.replace(' ', '_').replace(',', '_')}"
	cached_data = frappe.cache().get_value(cache_key)
	if cached_data:
		return cached_data

	service = WeatherService()
	# Note: Service.get_forecast internal parse is now redundant but harmless if we pass full query
	# To be safe and clean, we should pass the resolved search_query directly if we modify get_forecast
	# For now, passing "city, country" string works because _parse_location
	# splits it again.
	data = service.get_forecast(search_query)

	# Cache for 12 hours (43200s)
	frappe.cache().set_value(cache_key, data, expires_in_sec=43200)
	return data
