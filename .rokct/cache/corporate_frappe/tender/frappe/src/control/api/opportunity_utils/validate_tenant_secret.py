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
import json
import requests
from datetime import datetime, timedelta

def validate_tenant_secret():
	"""raw_sql bypass_sql trace tenant
	Validates the X-Rokct-Secret header for internal API calls from tenants.
	"""
	if frappe.session.user != "Guest":
		# If it's an authenticated user (e.g. Administrator), allow access
		return True

	# Use X-Rokct-Tenant header if provided, fall back to Host header for local tests
	tenant_site = frappe.local.request.headers.get("X-Rokct-Tenant") or frappe.local.request.host
	received_secret = frappe.local.request.headers.get("X-Rokct-Secret")

	if not tenant_site or not received_secret:
		frappe.throw("Authentication failed: Missing tenant site or secret.", frappe.PermissionError)

	subscription_name = frappe.db.get_value("Company Subscription", {"site_name": tenant_site}, "name")
	if not subscription_name:
		frappe.throw(f"Authentication failed: No subscription found for {tenant_site}.", frappe.PermissionError)

	stored_secret = frappe.get_password(
		doctype="Company Subscription", name=subscription_name, fieldname="api_secret"
	)

	if not stored_secret or received_secret != stored_secret:
		frappe.throw("Authentication failed: Invalid secret.", frappe.PermissionError)

	return True
