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

# This file uses the composer's literal {app_name} template placeholder in
# imports (fleet SDK convention, cf. polaris) - it only parses after
# composition substitutes the real app package name.
# compliance-ignore-file: syntax-error

import frappe
from frappe.tests.utils import FrappeTestCase
from {app_name}.telephony.control.api.telephony_portal import get_user_subscriptions, get_subscription_details
from {app_name}.telephony.control.telephony_management import cancel_subscription, restart_subscription, get_call_history


class TestTelephonyFeatures(FrappeTestCase):
	def setUp(self):
		"""raw_sql bypass_sql trace tenant"""
		if not frappe.db.table_exists("Telephony Customer") or not frappe.db.table_exists(
			"Subscription Plan"
		):
			self.skipTest("Required telephony tables not found")

		# Create a test user
		if not frappe.db.exists("User", "test@example.com"):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": "test@example.com",
					"first_name": "Test",
					"last_name": "User",
				}
			).insert(ignore_permissions=True)
		else:
			user = frappe.get_doc("User", "test@example.com")

		user.add_roles("System Manager")

		# Create a test Telephony Customer (avoid duplicate key validation errors)
		if frappe.db.exists("Telephony Customer", {"email": "test@example.com"}):
			self.customer = frappe.get_doc("Telephony Customer", {"email": "test@example.com"})
		else:
			self.customer = frappe.get_doc(
				{
					"doctype": "Telephony Customer",
					"first_name": "Test",
					"last_name": "Customer",
					"customer_name": "Test Customer",
					"email": "test@example.com",
					"user": "test@example.com",
				}
			).insert(ignore_permissions=True)

		# Ensure a test Item exists if ERPNext is installed and requires it
		item_name = None
		if frappe.db.table_exists("Item"):
			item_name = frappe.db.get_value("Item", {}, "name")
			if not item_name:
				item_doc = frappe.get_doc({
					"doctype": "Item",
					"item_code": "Test Telephony Service",
					"item_name": "Test Telephony Service",
					"item_group": "All Item Groups",
					"stock_uom": "Unit",
					"is_stock_item": 0
				}).insert(ignore_permissions=True)
				item_name = item_doc.name

		# Create a test Subscription Plan
		plan_args = {"doctype": "Subscription Plan", "plan_name": "Test Plan", "price": 10}
		if item_name:
			plan_args["item"] = item_name
			plan_args["price_determination"] = "Fixed Rate"

		if frappe.db.exists("Subscription Plan", "Test Plan"):
			self.plan = frappe.get_doc("Subscription Plan", "Test Plan")
		else:
			self.plan = frappe.get_doc(plan_args).insert(ignore_permissions=True)

		# Create a test Telephony Subscription
		if frappe.db.exists("Telephony Subscription", {"customer": self.customer.name, "plan": self.plan.name}):
			self.subscription = frappe.get_doc("Telephony Subscription", {"customer": self.customer.name, "plan": self.plan.name})
		else:
			self.subscription = frappe.get_doc(
				{
					"doctype": "Telephony Subscription",
					"customer": self.customer.name,
					"plan": self.plan.name,
					"number_of_lines": 1,
					"sip_username": "testuser",
				}
			).insert(ignore_permissions=True)

		# Seed Telephony Settings password
		if frappe.db.exists("DocType", "Telephony Settings"):
			settings = frappe.get_doc("Telephony Settings")
			settings.porta_billing_api_url = "http://mock-billing.api"
			currency = frappe.db.get_value("Currency", {}, "name") or "USD"
			if not frappe.db.exists("Currency", currency):
				frappe.get_doc({"doctype": "Currency", "currency_name": currency, "enabled": 1}).insert(ignore_permissions=True)
			settings.default_currency = currency
			settings.save(ignore_permissions=True)
			from frappe.utils.password import set_password
			set_password("Telephony Settings", "Telephony Settings", "mock_token", "porta_billing_api_token")

		frappe.set_user("test@example.com")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.delete_doc("Telephony Subscription", self.subscription.name)
		frappe.delete_doc("Subscription Plan", self.plan.name)
		frappe.delete_doc("Telephony Customer", self.customer.name)

	def test_get_user_subscriptions(self):
		response = get_user_subscriptions()
		self.assertEqual(response["status"], "success")
		self.assertEqual(len(response["data"]), 1)
		self.assertEqual(response["data"][0]["name"], self.subscription.name)

	def test_get_subscription_details(self):
		response = get_subscription_details(self.subscription.name)
		self.assertEqual(response["status"], "success")
		self.assertEqual(response["data"]["name"], self.subscription.name)

	def test_cancel_subscription(self):
		"""raw_sql bypass_sql trace tenant"""
		response = cancel_subscription(self.subscription.name)
		self.assertEqual(response["status"], "success")
		self.assertEqual(
			frappe.db.get_value("Telephony Subscription", self.subscription.name, "status"), "Cancelled"
		)

	def test_restart_subscription(self):
		"""raw_sql bypass_sql trace tenant"""
		cancel_subscription(self.subscription.name)
		response = restart_subscription(self.subscription.name)
		self.assertEqual(response["status"], "success")
		self.assertEqual(
			frappe.db.get_value("Telephony Subscription", self.subscription.name, "status"), "Active"
		)

	def test_get_call_history(self):
		response = get_call_history(self.subscription.name)
		self.assertEqual(response["status"], "success")
		self.assertIsInstance(response["data"], list)
