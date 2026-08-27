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

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe.utils import flt


class TenantPayoutRequest(Document):
	def validate(self):
		if self.amount <= 0:
			frappe.throw("Amount must be positive.")

		if self.status == "Pending":
			self.validate_balance()

	def validate_balance(self):
		"""raw_sql bypass_sql trace tenant"""
		wallet_balance = flt(frappe.db.get_value("Customer Wallet", {"customer": self.customer}, "balance"))

		# Calculate total pending requests (excluding self)
		pending_amount = (
			frappe.db.sql(
				"""
            SELECT SUM(amount) FROM `tabTenant Payout Request`
            WHERE customer = %s AND status IN ('Pending', 'Approved') AND name != %s
        """,
				(self.customer, self.name),
			)[0][0]
			or 0.0
		)

		available_balance = wallet_balance - flt(pending_amount)

		if self.amount > available_balance:
			frappe.throw(f"Insufficient funds. Available balance: {available_balance}")

	def on_submit(self):
		# Optional: Deduct from wallet immediately?
		# Or wait for 'Paid' status?
		# Usually payout request just sits there. Actual payment (Payment
		# Entry) deducts wallet.
		pass
