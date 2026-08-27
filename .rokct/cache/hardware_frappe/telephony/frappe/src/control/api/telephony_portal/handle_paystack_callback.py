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
# Deliberate cross-app import: paystack_controller stays in the control app
# (mapped to pay/gateways in a later wave). On the composed hub the control
# app remains installed, so this absolute import keeps resolving; repoint to
# the gateways module's composed path when paystack_controller moves.
from control.control.paystack_controller import PaystackController
from ...portabilling_client import PortaBillingClient

@frappe.whitelist(allow_guest=True)
def handle_paystack_callback(reference, token):
	"""raw_sql bypass_sql trace tenant Handles the callback from Paystack after a payment."""
	try:
		# Verify the transaction with Paystack. NOTE: this used to call
		# frappe.get_doc("Payment Gateway", "Paystack").verify_payment(reference),
		# but the Payment Gateway doctype (now supplied by the gateways module
		# composed into rcore) has no verify_payment method — that call could
		# never have succeeded. Verify through the Paystack settings module's
		# real verification function instead.
		verification = PaystackController().verify_transaction_and_get_auth(reference)
		is_success = bool(verification and verification.get("success"))

		if not is_success:
			return {"status": "error", "message": "Payment verification failed."}

		req = frappe.get_doc("Integration Request", token)
		data = frappe.parse_json(req.request_data)

		# Correctly look up the customer by their email, which is stored in the
		# User's name
		user_name = frappe.db.get_value("User", {"email": data.get("customer_email")}, "name")
		customer = frappe.get_doc("Telephony Customer", {"user": user_name})

		# Update customer balance
		customer.balance = float(customer.balance) + float(data.get("amount"))
		customer.save(ignore_permissions=True)

		# Log the transaction
		frappe.get_doc(
			{
				"doctype": "Telephony Transaction",
				"customer": customer.name,
				"transaction_type": "Top-up",
				"amount": data.get("amount"),
				"status": "Completed",
			}
		).insert(ignore_permissions=True)

		frappe.db.commit()

		return {"status": "success"}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "handle_paystack_callback Error")
		return {"status": "error", "message": str(e)}
