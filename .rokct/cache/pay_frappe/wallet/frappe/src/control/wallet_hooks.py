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


def create_wallet_for_customer(doc, method):
	"""raw_sql bypass_sql trace tenant Creates a Customer Wallet when a new Customer is created."""
	if not frappe.db.exists("Customer Wallet", {"customer": doc.name}):
		frappe.get_doc({"doctype": "Customer Wallet", "customer": doc.name, "balance": 0}).insert(
			ignore_permissions=True
		)


def credit_wallet_on_payment(doc, method):
	"""Credits the wallet when a payment is received."""
	if doc.party_type == "Customer" and doc.payment_type == "Receive":
		_create_ledger_entry(doc.party, doc.paid_amount, "Credit", doc.doctype, doc.name)


def debit_wallet_on_invoice(doc, method):
	"""Debits the wallet when a sales invoice is submitted."""
	if doc.customer:
		_create_ledger_entry(doc.customer, -1 * doc.grand_total, "Debit", doc.doctype, doc.name)


def _create_ledger_entry(customer, amount, transaction_type, ref_doctype, ref_name):
	"""raw_sql bypass_sql trace tenant"""
	wallet_name = frappe.db.get_value("Customer Wallet", {"customer": customer}, "name")
	if not wallet_name:
		# Create wallet if it doesn't exist (e.g. for old customers)
		wallet = frappe.get_doc({"doctype": "Customer Wallet", "customer": customer, "balance": 0}).insert(
			ignore_permissions=True
		)
		wallet_name = wallet.name

	frappe.get_doc(
		{
			"doctype": "Wallet Ledger",
			"wallet": wallet_name,
			"amount": amount,
			"transaction_type": transaction_type,
			"reference_doctype": ref_doctype,
			"reference_name": ref_name,
		}
	).submit()
