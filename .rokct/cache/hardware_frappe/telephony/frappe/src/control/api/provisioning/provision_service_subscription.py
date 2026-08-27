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

# create_subscription_record (the Company Subscription billing-record factory)
# stays in the control app with provision_new_tenant — cross-app import kept
# absolute, same as the paystack_controller precedent (the control app remains
# installed on the hub). Fix-in-move: the control-side original called both
# helpers without importing them (latent NameError on execution).
from control.control.api.provisioning.create_subscription_record import create_subscription_record

from ._validate_provisioning_input import _validate_provisioning_input


@frappe.whitelist()
def provision_service_subscription(
	plan,
	email,
	password,
	first_name,
	last_name,
	company_name,
	currency,
	country,
	industry,
	domain=None,
	lines=1,
	area_code=None,
	voucher_code=None,
):
	"""raw_sql bypass_sql trace tenant 
	Unified API to provision generic service subscriptions (Hosting, Telephony, etc.).
	Uses Company Subscription as the billing engine without creating a Frappe Site.
	"""
	if frappe.conf.get("app_role") != "control":
		frappe.throw("This action can only be performed on the control panel.", title="Action Not Allowed")

	# 1. Validate inputs
	if not all([plan, email, password, company_name]):
		frappe.throw("Plan, email, password, and company name are required.", title="Missing Information")

	_validate_provisioning_input(
		plan, email, password, first_name, last_name, company_name, currency, country, industry, voucher_code
	)

	try:
		# 2. Determine Service Category
		subscription_plan = frappe.get_doc("Subscription Plan", plan)
		category = getattr(subscription_plan, "plan_category", None)

		# 3. Create User if not exists
		if not frappe.db.exists("User", email):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": first_name,
					"last_name": last_name,
					"send_welcome_email": 1,
					"user_type": "Website User",
				}
			)
			user.set("new_password", password)
			user.insert(ignore_permissions=True)

			if category == "Hosting":
				user.add_roles("Hosting Client")
			elif category == "Telephony":
				user.add_roles("Telephony Customer")
		else:
			existing_user = frappe.get_doc("User", email)
			if category == "Hosting":
				existing_user.add_roles("Hosting Client")
			elif category == "Telephony":
				existing_user.add_roles("Telephony Customer")

		# 4. Prepare Service Specifics (Validation & Reservation)
		# We DO NOT use site_name for these. It must be None to protect
		# Next.js.
		site_name = None
		did_number = None

		if category == "Hosting":
			# Domain is optional now, based on user feedback.
			# If provided, we validate it and create a website.
			if domain:
				# Check for domain conflict in Hosting Client
				# Assuming we create a website with this domain
				if frappe.db.exists("Hosted Website", {"domain": domain}):
					frappe.throw(
						f"The domain {domain} is already hosted on our platform.", title="Domain Taken"
					)
				site_name = domain
			else:
				# No domain provided, use generic identifier
				import random

				site_name = f"host-{company_name.replace(' ', '-').lower()}-{random.randint(1000, 9999)}"

		elif category == "Telephony":
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
						f"No available numbers for the selected area code: {area_code}",
						title="No Numbers Available",
					)

		# 5. Create Subscription (Billing Engine)
		# site_name passed as None
		subscription = create_subscription_record(
			plan, email, company_name, industry, None, currency, voucher_code
		)

		# Update user_quantity as proxy for quotas/lines
		if lines > 1:
			subscription.user_quantity = lines
			subscription.save(ignore_permissions=True)

		# 6. Instantiate Service Records (The "Technical" side)
		# We do this here because we have the transient params (domain, etc)

		if category == "Hosting":
			# Rely on control.control.hosting_integration logic, OR call it directly?
			# Integration logic creates Client.
			# We also want to add the Website.
			from control.control.hosting_integration import create_client_from_subscription

			# Ensure client exists
			create_client_from_subscription(subscription.name)

			# Now add the website
			# Need to fetch the created client name (mapped from customer)
			client_name = subscription.customer

			# Create Hosted Website
			if domain:
				website = frappe.get_doc(
					{"doctype": "Hosted Website", "client": client_name, "domain": domain, "status": "Active"}
				)
				website.insert(ignore_permissions=True)

		elif category == "Telephony":
			# Rely on telephony_integration logic?
			# It runs on hook, but doesn't know about DID (unless we hacked site_name).
			# Since we didn't set site_name, the hook won't set DID.
			# So we must update/create here.

			# Determine Customer Name (Email)
			t_customer_name = frappe.db.get_value("Telephony Customer", {"email": email})
			if not t_customer_name:
				# Should have been created by hook? Hook runs 'after_insert'.
				# So it might exist now.
				pass
			else:
				# Find the subscription created by hook?
				# Hook creates subscription based on Plan.
				# We need to find it and update DID.
				ts_name = frappe.db.get_value(
					"Telephony Subscription",
					{"customer": t_customer_name, "plan": plan, "status": "Active", "did_number": None},
				)

				if ts_name:
					ts = frappe.get_doc("Telephony Subscription", ts_name)
					ts.did_number = did_number
					ts.number_of_lines = lines
					ts.save(ignore_permissions=True)
				else:
					# Hook failed or didn't run? Create manually.
					# (Code duplication from hook, but safe)
					if not t_customer_name:
						# Create Customer
						tc = frappe.get_doc(
							{"doctype": "Telephony Customer", "customer_name": company_name, "email": email}
						)
						tc.insert(ignore_permissions=True)
						t_customer_name = tc.name

					ts = frappe.get_doc(
						{
							"doctype": "Telephony Subscription",
							"customer": t_customer_name,
							"plan": plan,
							"number_of_lines": lines,
							"status": "Active",
							"did_number": did_number,
						}
					)
					ts.insert(ignore_permissions=True)

		return {
			"status": "success",
			"message": "Service account provisioned successfully.",
			"subscription": subscription.name,
			"site_name": None,  # Explicitly return None
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Service Subscription Provisioning Failed")
		frappe.throw(f"Failed to provision service subscription: {e}")
