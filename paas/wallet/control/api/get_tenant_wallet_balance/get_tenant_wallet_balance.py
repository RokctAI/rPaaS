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
def get_tenant_wallet_balance():
	"""raw_sql bypass_sql trace tenant 
	Called by a tenant site to get its wallet balance.
	"""
	if frappe.conf.get("app_role") != "control":
		frappe.throw("This action can only be performed on the control panel.", title="Action Not Allowed")

	tenant_site = frappe.local.request.headers.get("X-Rokct-Tenant") or frappe.local.request.host
	received_secret = frappe.local.request.headers.get("X-Rokct-Secret")


	if not tenant_site or not received_secret:
		frappe.throw("Authentication failed: Missing credentials.")

	subscription_name = frappe.db.get_value("Company Subscription", {"site_name": tenant_site}, "name")
	if not subscription_name:
		frappe.throw(f"No subscription found for site {tenant_site}")

	stored_secret = frappe.utils.get_password(
		doctype="Company Subscription", name=subscription_name, fieldname="api_secret"
	)
	if received_secret != stored_secret:
		frappe.throw("Authentication failed.")

	subscription = frappe.get_doc("Company Subscription", subscription_name)
	customer = subscription.customer

	balance = frappe.db.get_value("Customer Wallet", {"customer": customer}, "balance") or 0.0
	return {"balance": balance, "currency": "ZAR"}
