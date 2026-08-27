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

# Tenant context: session.user validation
import frappe
from paas.api.repeating_order import create_repeating_order
from paas.api.payment.payment import tokenize_card, process_wallet_top_up
from frappe.utils import add_days, nowdate


def verify_flow():
    trace_id = None
    """
    Verify auto order flow with trace context.
    """
    frappe.set_user("Administrator")

    # 1. Create a Test Order
    order = frappe.get_doc(
        {
            "doctype": "Order",
            "user": "Administrator",
            "grand_total": 100,
            "items": [],  # Simplified
        }
    )
    order.flags.ignore_permissions = True
    order.insert()

    # 2. Create Saved Card
    card = tokenize_card("4242424242424242", "Test User", "12/25", "123")
    token = card["token"]
    print(f"Card Tokenized: {token}")

    # 3. Ensure Wallet is Empty
    user_doc = frappe.get_doc("User", "Administrator")
    user_doc.wallet_balance = 0
    user_doc.ringfenced_balance = 0
    user_doc.save(ignore_permissions=True)

    # 4. Attempt Create Repeating Order (Should Fail)
    print("\nAttempting Create Repeating Order (Expect Failure)...")
    try:
        create_repeating_order(
            original_order=order.name,
            cron_pattern="0 0 * * *",  # Daily
            start_date=nowdate(),
            end_date=add_days(nowdate(), 7),
            payment_method="Wallet",
            saved_card=None,
        )
        print("ERROR: Should have failed due to insufficient balance!")
    except Exception as e:
        if "Suggest Topup" in str(e):
            print(f"SUCCESS: Caught expected error: {e}")
        else:
            print(f"FAILURE: Caught unexpected error: {e}")

    # 5. Top Up Wallet
    print("\nProcessing Top Up...")
    process_wallet_top_up(amount=1000, token=token)

    user_doc.reload()
    print(f"New Wallet Balance: {user_doc.wallet_balance}")

    # 6. Retry Create Repeating Order (Should Success)
    print("\nRetrying Create Repeating Order...")
    try:
        data = create_repeating_order(
            original_order=order.name,
            cron_pattern="0 0 * * *",
            start_date=nowdate(),
            end_date=add_days(nowdate(), 7),
            payment_method="Wallet",
            saved_card=None,
        )
        print(f"SUCCESS: Auto Order Created: {data}")
    except Exception as e:
        print(f"FAILURE: {e}")

    frappe.db.rollback()  # Clean up


if __name__ == "__main__":
    verify_flow()
