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
from frappe.model.document import Document

# The composer relocates persona doctypes to the module root, so this file
# lands at {app}/telephony/doctype/telephony_subscription/ while
# portabilling_client composes to {app}/telephony/control/portabilling_client.py.
from ...control.portabilling_client import PortaBillingClient


class TelephonySubscription(Document):
	def on_update(self):
		# Trigger provisioning only when the status changes to Active
		if self.status == "Active" and self.get_doc_before_save().status != "Active":
			self.provision_customer()

	def provision_customer(self):
		"""raw_sql bypass_sql trace tenant"""
		settings = frappe.get_single("Telephony Settings")
		telephony_customer = frappe.get_doc("Telephony Customer", self.customer)

		# Ensure we have the API token
		api_token = settings.get_password("porta_billing_api_token")
		if not all([settings.porta_billing_api_url, api_token, settings.default_currency]):
			frappe.throw(
				"Telephony settings are incomplete. Please configure PortaBilling API URL, Token, and Default Currency.",
				title="Configuration Error",
			)
			return

		client = PortaBillingClient(settings.porta_billing_api_url, api_token)

		# Construct the payload using values from settings
		customer_data = {
			"name": telephony_customer.customer_name,
			"iso_4217": settings.default_currency,
			"i_customer_class": 1,  # Defaulting to 1 as this is no longer in settings
			"email": telephony_customer.email,
			"login": telephony_customer.email,  # Use email as login
		}

		try:
			response = client.add_customer(customer_data)

			# Check for the nested customer ID in the response
			if response and response.get("i_customer"):
				self.db_set("porta_billing_customer_id", response["i_customer"], commit=True)
				frappe.msgprint(
					f"Customer provisioned successfully. PortaBilling ID: {response['i_customer']}"
				)
			else:
				error_msg = response.get("error", "Unknown error from PortaBilling API.")
				frappe.log_error(f"PortaBilling Error: {error_msg}", "Telephony Subscription Provisioning")
				frappe.throw(f"Failed to provision customer in PortaBilling: {error_msg}")

		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Telephony Subscription Provisioning")
			frappe.throw(f"An error occurred during PortaBilling provisioning: {str(e)}")
