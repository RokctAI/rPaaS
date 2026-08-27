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

# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import frappe
from frappe.utils.data import nowdate
# Composed paths: this file lands at {app}/telephony/control/telephony_management.py
# while the composer relocates persona doctypes to the module root
# ({app}/telephony/doctype/...), hence the differing relative depths.
from ..doctype.telephony_subscription.telephony_subscription import TelephonySubscription
from .portabilling_client import PortaBillingClient


@frappe.whitelist()
def cancel_subscription(subscription_name):
	"""raw_sql bypass_sql trace tenant Cancels a Telephony Subscription."""
	try:
		subscription = frappe.get_doc("Telephony Subscription", subscription_name)
		if subscription.status != "Cancelled":
			subscription.status = "Cancelled"
			subscription.cancellation_date = nowdate()
			subscription.save(ignore_permissions=True)
			return {"status": "success", "message": f"Subscription {subscription_name} has been cancelled."}
		else:
			return {"status": "error", "message": "Subscription is already cancelled."}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "cancel_subscription Error")
		return {"status": "error", "message": str(e)}


@frappe.whitelist()
def restart_subscription(subscription_name):
	"""raw_sql bypass_sql trace tenant Restarts a previously cancelled Telephony Subscription."""
	try:
		subscription = frappe.get_doc("Telephony Subscription", subscription_name)
		if subscription.status == "Cancelled":
			if hasattr(subscription, "cancellation_date") and subscription.cancellation_date:
				from frappe.utils import date_diff, nowdate

				if date_diff(nowdate(), subscription.cancellation_date) <= 90:
					subscription.status = "Active"
					subscription.cancellation_date = None
					subscription.save(ignore_permissions=True)
					return {
						"status": "success",
						"message": f"Subscription {subscription_name} has been restarted.",
					}
				else:
					return {
						"status": "error",
						"message": "Subscription cannot be restarted after 3 months of cancellation.",
					}
			else:
				# If there's no cancellation_date, we just restart it.
				subscription.status = "Active"
				subscription.save(ignore_permissions=True)
				return {
					"status": "success",
					"message": f"Subscription {subscription_name} has been restarted.",
				}
		else:
			return {"status": "error", "message": "Subscription is not cancelled."}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "restart_subscription Error")
		return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_call_history(subscription_name):
	"""raw_sql bypass_sql trace tenant Gets the call history for a Telephony Subscription."""
	try:
		subscription = frappe.get_doc("Telephony Subscription", subscription_name)
		if not subscription.sip_username:
			return {"status": "error", "message": "SIP username not found for this subscription."}

		settings = frappe.get_single("Telephony Settings")
		client = PortaBillingClient(
			api_url=settings.porta_billing_api_url, token=settings.get_password("porta_billing_api_token")
		)
		call_history = client.get_xdr_list(subscription.sip_username)

		return {"status": "success", "data": call_history}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_call_history Error")
		return {"status": "error", "message": str(e)}
