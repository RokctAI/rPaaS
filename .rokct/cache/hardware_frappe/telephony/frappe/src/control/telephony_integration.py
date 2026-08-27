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


def on_subscription_submit(doc, method):
	"""raw_sql bypass_sql trace tenant 
	Hook called when Company Subscription is (inserted via provision API).
	If the plan is a Telephony plan, create a Telephony Subscription.
	"""
	if doc.doctype != "Company Subscription":
		return

	try:
		# Check if plan is a Telephony plan
		plan = frappe.get_doc("Subscription Plan", doc.plan)

		is_telephony_plan = False
		if hasattr(plan, "plan_category") and plan.plan_category == "Telephony":
			is_telephony_plan = True

		if not is_telephony_plan and hasattr(plan, "modules"):
			for module in plan.modules:
				if module.module == "Telephony":
					is_telephony_plan = True
					break

		if not is_telephony_plan:
			return

		# It is a Telephony Plan, proceed to create Telephony artifacts
		customer_name = doc.customer

		# 1. Create Telephony Customer if not exists
		# We assume the main Customer already exists (Company Subscription
		# links to it)
		main_customer = frappe.get_doc("Customer", customer_name)

		# Check if Linked Telephony Customer exists?
		# Telephony Customer usually maps 1:1 to Customer or User?
		# Based on api/telephony.py, it maps to Email.
		# Let's check using Primary Email.
		email = main_customer.customer_primary_email

		t_customer_name = frappe.db.get_value("Telephony Customer", {"email": email})
		if not t_customer_name:
			# Create it
			tc = frappe.get_doc(
				{
					"doctype": "Telephony Customer",
					"customer_name": main_customer.customer_name,
					"email": email,
				}
			)
			tc.insert(ignore_permissions=True)
			t_customer_name = tc.name

		# 2. Create Telephony Subscription
		# Check if one already exists for this plan?
		# If we are provisioning a NEW one, we generally want a new record.
		# But Company Subscription is unique per site_name (which we use as UID
		# for telephony too).

		# Mapping:
		# number_of_lines <- user_quantity (if > 0, else 1)
		# did_number <- derived from site_name if it looks like a number? Or
		# passed via custom fields?

		lines = doc.user_quantity if doc.user_quantity > 0 else 1

		# doc.site_name might conduct the DID if we Provision that way.
		did_number = None
		if doc.site_name and doc.site_name.replace("+", "").isdigit():
			did_number = doc.site_name

		ts = frappe.get_doc(
			{
				"doctype": "Telephony Subscription",
				"customer": t_customer_name,
				"plan": doc.plan,
				"number_of_lines": lines,
				"status": "Active",  # Activate immediately or follow doc.status?
				"did_number": did_number,
			}
		)
		ts.insert(ignore_permissions=True)
		frappe.msgprint(f"Telephony Subscription created for {doc.site_name}")

	except Exception as e:
		frappe.log_error(f"Failed to create telephony subscription: {str(e)}")
		# We don't block the main subscription creation, but we log strictly.
