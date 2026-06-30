import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import MagicMock


class TestRcoreIntegration(FrappeTestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test_rcore_user@example.com"):
            self.user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_rcore_user@example.com",
                    "first_name": "Test",
                    "last_name": "Rcore User",
                    "roles": [{"role": "Customer"}],
                }
            ).insert(ignore_permissions=True)
        else:
            self.user = frappe.get_doc("User", "test_rcore_user@example.com")

        # Create a test customer linked to user
        if not frappe.db.exists("Customer", "Test Rcore Customer"):
            if not frappe.db.exists("Customer Group", "Individual"):
                frappe.get_doc(
                    {
                        "doctype": "Customer Group",
                        "customer_group_name": "Individual",
                        "is_group": 0,
                        "parent_customer_group": "All Customer Groups",
                    }
                ).insert(ignore_permissions=True)

            self.customer = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": "Test Rcore Customer",
                    "customer_type": "Individual",
                    "customer_group": "Individual",
                    "territory": "All Territories",
                }
            ).insert(ignore_permissions=True)

            # Manually set user if field exists, else ignore (mock scenario)
            if self.customer.meta.has_field("user"):
                self.customer.db_set("user", self.user.name)
        else:
            self.customer = frappe.get_doc("Customer", "Test Rcore Customer")
            # Ensure link exists
            if self.customer.meta.has_field("user") and not self.customer.user:
                self.customer.db_set("user", self.user.name)

    def tearDown(self):
        # Cleanup
        if hasattr(self, "user"):
            frappe.db.delete(
                "Wallet History",
                {
                    "wallet": [
                        "in",
                        frappe.get_all(
                            "Wallet", {"user": self.user.name}, pluck="name"
                        ),
                    ]
                },
            )
            frappe.db.delete("Wallet", {"user": self.user.name})
            # Clean up Loan Docs too? Maybe later.

    def test_loan_disbursement_wallet_integration(self):
        # 1. Create a Loan Disbursement mock doc
        # 1. Create a Loan Disbursement mock doc
        # We Mock this because Loan Disbursement might not exist in the test
        # env
        loan_doc = MagicMock()
        loan_doc.doctype = "Loan Disbursement"
        loan_doc.applicant_type = "Customer"
        loan_doc.applicant = self.customer.name
        loan_doc.disbursed_amount = 5000
        loan_doc.name = "TEST-LOAN-DISB-001"

        # Import from rcore (cross-app call)
        try:
            from rcore.rlending.wallet_integration import credit_wallet_on_disbursement
        except ImportError:
            self.skipTest("Rcore app not installed")
            return

        credit_wallet_on_disbursement(loan_doc, "on_submit")

        # Verify wallet exists and balance is 5000 (Query by User now)
        wallet = frappe.get_doc("Wallet", {"user": self.user.name})
        self.assertEqual(wallet.balance, 5000)

        # Verify history record
        history = frappe.get_all(
            "Wallet History",
            filters={"wallet": wallet.name},
            fields=["transaction_type", "amount"],
        )
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].transaction_type, "Loan Disbursement")
        self.assertEqual(history[0].amount, 5000)

    def test_loan_repayment_wallet_integration(self):
        # 1. Ensure wallet exists with balance
        wallet = frappe.get_doc(
            {"doctype": "Wallet", "user": self.user.name, "balance": 1000}
        ).insert(ignore_permissions=True)

        try:
            from rcore.rlending.wallet_integration import debit_wallet_on_repayment
        except ImportError:
            self.skipTest("Rcore app not installed")
            return

        repayment_doc = MagicMock()
        repayment_doc.doctype = "Loan Repayment"
        repayment_doc.applicant_type = "Customer"
        repayment_doc.applicant = self.customer.name
        repayment_doc.amount_paid = 200
        repayment_doc.name = "TEST-LOAN-REPAY-001"

        debit_wallet_on_repayment(repayment_doc, "on_submit")

        wallet.reload()
        self.assertEqual(wallet.balance, 800)
