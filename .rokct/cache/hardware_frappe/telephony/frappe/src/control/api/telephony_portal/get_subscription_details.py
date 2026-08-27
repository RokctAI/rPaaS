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
def get_subscription_details(subscription_name):
	"""raw_sql bypass_sql trace tenant Gets all details for a Telephony Subscription."""
	try:
		subscription = frappe.get_doc("Telephony Subscription", subscription_name)
		settings = frappe.get_single("Telephony Settings")

		details = subscription.as_dict()
		details["form_url"] = get_url_to_form("Telephony Subscription", subscription_name)

		sip_domain = settings.sip_domain or "sip.example.com"
		# Single-line f-string: multiline expressions inside f-strings are
		# Python 3.12+ (PEP 701) and fail to parse on 3.11.
		sip_uri = f"sip:{subscription.sip_username}@{sip_domain}"
		details["qr_code"] = f"https://api.qrserver.com/v1/create-qr-code/?data={sip_uri}&size=200x200"

		return {"status": "success", "data": details}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_subscription_details Error")
		return {"status": "error", "message": str(e)}
