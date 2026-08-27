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
from frappe.utils import get_url_to_form
from ...portabilling_client import PortaBillingClient

@frappe.whitelist()
def initiate_top_up(amount):
	"""raw_sql bypass_sql trace tenant Initiates a top-up payment and returns a checkout URL."""
	try:
		if frappe.session.user == "Guest":
			return {"status": "error", "message": "You must be logged in."}

		if not float(amount) > 0:
			return {"status": "error", "message": "Amount must be greater than 0."}

		customer = frappe.get_doc("Telephony Customer", {"user": frappe.session.user})

		integration_request = frappe.new_doc("Integration Request")
		integration_request.integration_type = "Remote"
		integration_request.integration_request_service = "Paystack"
		integration_request.request_data = frappe.as_json(
			{
				"amount": amount,
				"customer_email": customer.email,
				"description": f"Top-up for Telephony Customer {customer.name}",
			}
		)
		integration_request.insert(ignore_permissions=True)
		frappe.db.commit()

		# Assuming get_payment_url now returns a tokenized URL to our checkout
		# page
		checkout_url = f"/paystack_checkout?token={integration_request.name}"

		return {"status": "success", "data": {"checkout_url": checkout_url}}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "initiate_top_up Error")
		return {"status": "error", "message": str(e)}
