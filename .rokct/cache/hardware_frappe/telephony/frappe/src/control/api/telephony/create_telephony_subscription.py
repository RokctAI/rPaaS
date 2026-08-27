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
def create_telephony_subscription(plan: str, lines: int):
	"""raw_sql bypass_sql trace tenant 
	Creates a Telephony Subscription for the logged-in user.
	If a Telephony Customer does not exist for the user, it creates one.
	"""
	if not plan or not lines:
		frappe.throw("Plan and number of lines are required.", title="Missing Information")

	if not isinstance(lines, int) or lines <= 0:
		frappe.throw("Number of lines must be a positive integer.", title="Invalid Input")

	user_email = frappe.session.user
	if user_email == "Guest":
		frappe.throw("You must be logged in to create a subscription.", frappe.AuthenticationError)

	# Find or create the Telephony Customer
	customer_name = frappe.db.get_value("Telephony Customer", {"email": user_email})
	if not customer_name:
		customer = frappe.get_doc(
			{
				"doctype": "Telephony Customer",
				"customer_name": frappe.utils.get_fullname(user_email),
				"email": user_email,
			}
		).insert(ignore_permissions=True)
		customer_name = customer.name

	# Check for existing active/inactive subscriptions to the same plan
	if frappe.db.exists(
		"Telephony Subscription",
		{"customer": customer_name, "plan": plan, "status": ["in", ["Active", "Inactive"]]},
	):
		return {"status": "error", "error": "You already have an active subscription to this plan."}

	try:
		# Create the new subscription
		subscription = frappe.get_doc(
			{
				"doctype": "Telephony Subscription",
				"customer": customer_name,
				"plan": plan,
				"number_of_lines": lines,
				"status": "Inactive",  # Subscriptions start as Inactive until payment
			}
		).insert(ignore_permissions=True)

		frappe.db.commit()
		return {"status": "success", "subscription_id": subscription.name}

	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "Telephony Subscription Creation Failed")
		frappe.throw(f"An error occurred while creating the subscription: {str(e)}")
