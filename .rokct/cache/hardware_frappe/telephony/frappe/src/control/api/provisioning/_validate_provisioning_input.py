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

# DUPLICATED (pending common/ promotion): this validator also exists as
# control/control/api/provisioning/_validate_provisioning_input.py, where the
# staying provision_new_tenant flow uses it. Duplicated here for SDK
# self-containment rather than importing cross-app; keep the two copies in
# sync. Promotion to a shared common/ home needs Ray's sign-off.


def _validate_provisioning_input(
	plan, email, password, first_name, last_name, company_name, currency, country, industry, voucher_code=None
):
	"""raw_sql bypass_sql trace tenant Helper function to validate inputs for the provisioning API."""
	# Check for required fields
	if not all([plan, email, password, company_name, currency, country, industry]):
		frappe.throw(
			"Required fields are missing. Please provide plan, email, password, company name, currency, country, and industry.",
			title="Missing Information",
		)

	# Validate password length
	if len(password) < 8:
		frappe.throw("Password must be at least 8 characters long.", title="Weak Password")

	# Validate email format
	try:
		validate_email_address(email, throw=True)
	except frappe.exceptions.ValidationError:
		frappe.throw("You must provide a valid email address.", title="Invalid Email")

	# Check if a user with this email already exists on the control panel
	if frappe.db.exists("User", {"email": email}):
		frappe.throw("A user with this email address already exists.", title="Email Already Registered")

	# Check if a customer with this email already exists
	if frappe.db.exists("Customer", {"customer_primary_email": email}):
		frappe.throw(
			"A customer account with this email address already exists.", title="Email Already Registered"
		)

	# Check if the subscription plan exists
	if not frappe.db.exists("Subscription Plan", plan):
		frappe.throw(f"Subscription Plan '{plan}' not found.", title="Invalid Plan")

	# Check if the currency exists (relaxed validation: does not check for
	# 'enabled')
	if not frappe.db.exists("Currency", currency):
		frappe.throw(f"Currency '{currency}' does not exist.", title="Invalid Currency")

	# Check for non-empty strings for other fields
	if not all(
		isinstance(s, str) and s.strip() for s in [first_name, last_name, company_name, country, industry]
	):
		frappe.throw(
			"First name, last name, company name, country, and industry must be non-empty strings.",
			title="Invalid Input",
		)

	# Early validation for voucher if provided
	if voucher_code:
		if not frappe.db.exists("Subscription Voucher", voucher_code):
			frappe.throw(f"Voucher code '{voucher_code}' does not exist.", title="Invalid Voucher")

		voucher = frappe.get_doc("Subscription Voucher", voucher_code)
		if not voucher.is_active:
			frappe.throw(f"Voucher code '{voucher_code}' is inactive.", title="Voucher Inactive")

		from frappe.utils import getdate, nowdate

		if voucher.expiry_date and getdate(voucher.expiry_date) < getdate(nowdate()):
			frappe.throw(f"Voucher code '{voucher_code}' has expired.", title="Voucher Expired")

		if voucher.max_uses and voucher.used_count >= voucher.max_uses:
			frappe.throw(
				f"Voucher code '{voucher_code}' has reached its maximum uses.", title="Voucher Depth Reached"
			)
