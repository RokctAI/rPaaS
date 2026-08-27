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
def get_customer_balance():
	"""raw_sql bypass_sql trace tenant Gets the balance for the current Telephony Customer."""
	try:
		if frappe.session.user == "Guest":
			return {"status": "error", "message": "You must be logged in."}

		customer_name = frappe.db.get_value("Telephony Customer", {"user": frappe.session.user}, "name")
		if not customer_name:
			return {"status": "error", "message": "Telephony customer not found."}

		balance = frappe.db.get_value("Telephony Customer", customer_name, "balance")
		return {"status": "success", "data": balance}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_customer_balance Error")
		return {"status": "error", "message": str(e)}
