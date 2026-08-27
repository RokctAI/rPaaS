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

@frappe.whitelist(allow_guest=True)
def get_payment_request_details(token):
	"""raw_sql bypass_sql trace tenant Gets details needed for Paystack checkout page."""
	try:
		req = frappe.get_doc("Integration Request", token)
		data = frappe.parse_json(req.request_data)
		telephony_settings = frappe.get_single("Telephony Settings")
		paystack_settings = frappe.get_single("Paystack Settings")

		return {
			"status": "success",
			"data": {
				"public_key": paystack_settings.get_password("public_key"),
				"customer_email": data.get("customer_email"),
				"amount": data.get("amount"),
				"currency": telephony_settings.default_currency or "NGN",
				"reference": req.name,
			},
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_payment_request_details Error")
		return {"status": "error", "message": str(e)}
