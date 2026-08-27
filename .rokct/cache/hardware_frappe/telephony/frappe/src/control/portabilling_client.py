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


class PortaBillingClient:
	def __init__(self, api_url, token):
		self.api_url = api_url.rstrip("/")
		self.token = token
		self.session = requests.Session()
		self.session.headers.update(
			{"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
		)

	def add_customer(self, customer_data):
		# Correct endpoint for adding a customer
		endpoint = f"{self.api_url}/v1/customers"

		payload = {"customer_info": customer_data}

		try:
			response = self.session.post(endpoint, json=payload)
			response.raise_for_status()

			result = response.json()
			if result and result.get("i_customer"):
				return {"i_customer": result["i_customer"]}
			else:
				frappe.log_error(f"PortaBilling Error: Unexpected response {result}", "PortaBilling Client")
				return {"error": "Unexpected response from PortaBilling API"}

		except requests.exceptions.HTTPError as err:
			error_details = err.response.text
			frappe.log_error(f"HTTP error occurred: {err} - {error_details}", "PortaBilling Client")
			frappe.throw(f"Failed to add customer to PortaBilling: {err}")
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "PortaBilling Client")
			frappe.throw(f"An unexpected error occurred during PortaBilling API call: {e}")

	def get_xdr_list(self, account_id, limit=100):
		"""Gets a list of xDRs (call logs) for a specific account."""
		endpoint = f"{self.api_url}/v1/accounts/{account_id}/xdrs"
		params = {"limit": limit}

		try:
			response = self.session.get(endpoint, params=params)
			response.raise_for_status()
			return response.json().get("xdrs", [])
		except requests.exceptions.HTTPError as err:
			error_details = err.response.text
			frappe.log_error(
				f"HTTP error occurred while fetching xDRs: {err} - {error_details}", "PortaBilling Client"
			)
			return []  # Return empty list on error to avoid breaking the frontend
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "PortaBilling Client - get_xdr_list")
			return []
