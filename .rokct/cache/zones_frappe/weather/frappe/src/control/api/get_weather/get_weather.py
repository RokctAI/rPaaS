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

import frappe

@frappe.whitelist()
def get_weather(location: str):
	"""raw_sql bypass_sql trace tenant 
	Get weather data for a given location, with caching.
	This endpoint is intended to be called by tenant sites and requires authentication.
	"""
	# This API should only ever run on the control panel.
	if frappe.conf.get("app_role") != "control":
		frappe.throw("This action can only be performed on the control panel.", title="Action Not Allowed")

	# 1. Authenticate the request
	tenant_site = frappe.local.request.headers.get("X-Rokct-Tenant") or frappe.local.request.host
	received_secret = frappe.local.request.headers.get("X-Rokct-Secret")


	if not tenant_site:
		frappe.throw("Could not identify tenant site from request.")
	if not received_secret:
		frappe.throw("Missing or invalid X-Rokct-Secret header.")

	subscription_name = frappe.db.get_value("Company Subscription", {"site_name": tenant_site}, "name")
	if not subscription_name:
		frappe.throw(f"No subscription found for site {tenant_site}")

	stored_secret = frappe.utils.get_password(
		doctype="Company Subscription", name=subscription_name, fieldname="api_secret"
	)

	if not stored_secret or received_secret != stored_secret:
		frappe.throw("Authentication failed.")

	# 2. Proceed with the API logic if authenticated
	if not location:
		frappe.throw("Location is a required parameter.")

	# Check for special cases to use default location, mimicking Laravel logic
	weather_settings = frappe.get_doc("Weather Settings")
	default_location = weather_settings.default_location or "messina,za"

	# Simple check for coordinates (e.g., "-25.2,31.4") or "messina" related
	# strings
	if "," in location or "messina" in location.lower() or "nancefield" in location.lower():
		location = default_location

	cache_key = f"weather_{location.lower().replace(' ', '_')}"
	cached_data = frappe.cache().get_value(cache_key)

	if cached_data:
		return cached_data

	try:
		# Relative to the composed module subpackage: {app}.weather.control.weather_service
		from ...weather_service import get_weather_data

		weather_data = get_weather_data(location)
		frappe.cache().set_value(cache_key, weather_data, expires_in_sec=43200)  # Cache for 12 hours
		return weather_data
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Weather API Error")
		frappe.throw(f"An error occurred while fetching weather data: {e}")
