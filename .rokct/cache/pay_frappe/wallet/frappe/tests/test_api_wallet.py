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

# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.user.user import get_user_wallet, get_wallet_history
import uuid


class TestWalletAPI(FrappeTestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test_wallet@example.com"):
            self.test_user = frappe.get_doc({
                "doctype": "User",
                "email": "test_wallet@example.com",
                "first_name": "Test",
                "last_name": "Wallet",
                "send_welcome_email": 0
            }).insert(ignore_permissions=True)
        else:
            self.test_user = frappe.get_doc("User", "test_wallet@example.com")
        self.test_user.add_roles("System Manager")

        # Create a wallet for the user
        if not frappe.db.exists("Wallet", {"user": self.test_user.name}):
            self.wallet = frappe.get_doc({
                "doctype": "Wallet",
                "uuid": str(uuid.uuid4()),
                "user": self.test_user.name,
                "currency": "USD",
                "price": 100.0
            }).insert(ignore_permissions=True)
        else:
            self.wallet = frappe.get_doc(
                "Wallet", {"user": self.test_user.name})

        # Create wallet history
        if not frappe.db.exists(
            "Wallet History", {
                "wallet": self.wallet.name, "transaction_type": "Topup"}):
            frappe.get_doc({
                "doctype": "Wallet History",
                "uuid": str(uuid.uuid4()),
                "wallet": self.wallet.name,
                "transaction_type": "Topup",
                "amount": 100.0,
                "status": "Paid"
            }).insert(ignore_permissions=True)

        # Log in as the test user
        frappe.set_user(self.test_user.name)

    def tearDown(self):
        # Log out
        frappe.set_user("Administrator")
        frappe.db.delete("Wallet History", {"wallet": self.wallet.name})
        try:
            self.wallet.delete(ignore_permissions=True)
        except Exception:
            pass

        if frappe.db.exists("User", self.test_user.name):
            try:
                self.test_user.delete(ignore_permissions=True)
            except frappe.exceptions.LinkExistsError:
                frappe.db.set_value("User", self.test_user.name, "enabled", 0)

    def test_get_user_wallet(self):
        wallet = get_user_wallet()
        self.assertEqual(wallet["data"].get("user"), self.test_user.name)
        self.assertEqual(wallet["data"].get("balance"), 0.0)

    def test_get_wallet_history_pagination(self):
        # Create a second history record
        if not frappe.db.exists(
            "Wallet History", {
                "wallet": self.wallet.name, "transaction_type": "Withdraw"}):
            frappe.get_doc({
                "doctype": "Wallet History",
                "uuid": str(uuid.uuid4()),
                "wallet": self.wallet.name,
                "transaction_type": "Withdraw",
                "amount": 50.0,
                "status": "Paid"
            }).insert(ignore_permissions=True)

        # Get the first page with a limit of 1
        history = get_wallet_history(limit=1)
        self.assertEqual(len(history["data"]), 1)
        self.assertEqual(
            history["data"][0].get("transaction_type"),
            "Withdraw")  # It's ordered by creation desc

        # Get the second page
        history = get_wallet_history(start=1, limit=1)
        self.assertEqual(len(history["data"]), 1)
        self.assertEqual(history["data"][0].get("transaction_type"), "Topup")
