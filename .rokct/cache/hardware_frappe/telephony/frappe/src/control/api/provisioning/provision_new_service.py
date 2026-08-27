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
from frappe.utils import validate_email_address

@frappe.whitelist()
def provision_new_service(
	plan,
	email,
	password,
	first_name,
	last_name,
	company_name,
	currency,
	country,
	industry,
	lines=1,
	area_code=None,
):
	"""raw_sql bypass_sql trace tenant 
	Provision a new service-only subscription (e.g., Telephony) for a user.
	This creates a Telephony Customer and Subscription but does not create a new site.
	"""
	if frappe.conf.get("app_role") != "control":
		frappe.throw("This action can only be performed on the control panel.", title="Action Not Allowed")

	# Basic validation
	if not all([plan, email, password, company_name]):
		frappe.throw("Plan, email, password, and company name are required.", title="Missing Information")

	# Check if a user with this email already exists on the control panel
	if frappe.db.exists("User", {"email": email}):
		frappe.throw("A user with this email address already exists.", title="Email Already Registered")

	# Ensure the plan exists and is a service plan
	if not frappe.db.exists("Subscription Plan", plan):
		frappe.throw(f"Subscription Plan '{plan}' not found.", title="Invalid Plan")

	# Find or create the Telephony Customer
	customer_name = frappe.db.get_value("Telephony Customer", {"email": email})
	if not customer_name:
		customer = frappe.get_doc(
			{"doctype": "Telephony Customer", "customer_name": company_name, "email": email}
		).insert(ignore_permissions=True)
		customer_name = customer.name

	# Create the user
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"send_welcome_email": 1,
		}
	)
	user.set("new_password", password)
	user.insert(ignore_permissions=True)
	user.add_roles("Telephony Customer")

	# Link the user to the customer document
	customer_doc = frappe.get_doc("Telephony Customer", customer_name)
	customer_doc.user = user.name
	customer_doc.save(ignore_permissions=True)

	# Check for existing active/inactive subscriptions to the same plan
	if frappe.db.exists(
		"Telephony Subscription",
		{"customer": customer_name, "plan": plan, "status": ["in", ["Active", "Inactive"]]},
	):
		frappe.throw("You already have an active subscription to this plan.", title="Duplicate Subscription")

	# Assign a DID number
	did_number = None
	if area_code:
		available_did = frappe.get_all(
			"Available DID", filters={"is_assigned": 0, "area_code": area_code}, limit=1
		)
		if available_did:
			did_doc = frappe.get_doc("Available DID", available_did[0].name)
			did_doc.is_assigned = 1
			did_doc.save(ignore_permissions=True)
			did_number = did_doc.did_number
		else:
			frappe.throw(
				f"No available numbers for the selected area code: {area_code}", title="No Numbers Available"
			)

	try:
		# Create the new subscription
		subscription = frappe.get_doc(
			{
				"doctype": "Telephony Subscription",
				"customer": customer_name,
				"plan": plan,
				"number_of_lines": lines,
				"status": "Active",  # Activate service immediately
				"did_number": did_number,
			}
		).insert(ignore_permissions=True)

		frappe.db.commit()
		return {
			"status": "success",
			"message": f"Telephony service for {email} has been successfully provisioned.",
		}

	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "Service Provisioning Failed")
		frappe.throw(f"An error occurred during service provisioning: {str(e)}")
