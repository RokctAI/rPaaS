# Repeating Order API
import frappe
from croniter import croniter
from datetime import datetime


def calculate_ringfence_amount(
        cron_pattern,
        start_date_str,
        end_date_str,
        unit_price):
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    else:
        # Default to 4 weeks if no end date
        from datetime import timedelta

        end_date = start_date + timedelta(days=28)

    iter = croniter(cron_pattern, start_date)
    count = 0
    while True:
        next_dt = iter.get_next(datetime)
        if next_dt > end_date:
            break
        count += 1

    return count * unit_price


@frappe.whitelist()
def create_repeating_order(
    original_order: str,
    start_date: str,
    cron_pattern: str,
    end_date: str = None,
    payment_method: str = "Wallet",
    saved_card: str = None,
    lang: str = "en",
):
    """
    Creates a new repeating order with payment preferences and ringfencing.
    Note: Payment method is enforced to 'Wallet' for auto-orders.
    """
    user = frappe.session.user
    order_doc = frappe.get_doc("Order", original_order)

    # Enforce Wallet for Auto Orders
    payment_method = "Wallet"

    ringfenced_amount = 0
    if payment_method == "Wallet":
        ringfenced_amount = calculate_ringfence_amount(
            cron_pattern, start_date, end_date, order_doc.grand_total
        )
        user_doc = frappe.get_doc("User", user)

        balance = user_doc.get("wallet_balance") or 0.0
        if balance < ringfenced_amount:
            # Specific error message for frontend interception
            frappe.throw(
                f"Insufficient Wallet Balance. Required: {ringfenced_amount}, Available: {balance}. Suggest Topup")

        # Ringfence
        user_doc.set("wallet_balance", balance - ringfenced_amount)
        user_doc.set(
            "ringfenced_balance",
            (user_doc.get("ringfenced_balance") or 0.0) + ringfenced_amount,
        )
        user_doc.save(ignore_permissions=True)

        # Log Transaction
        transaction = frappe.get_doc(
            {
                "doctype": "Transaction",
                "user": user,
                "amount": -ringfenced_amount,
                "status": "Success",
                "type": "Wallet Reservation",
                "reference_doctype": "Order",
                "reference_docname": original_order,
            }
        )
        transaction.insert(ignore_permissions=True)

    repeating_order = frappe.get_doc(
        {
            "doctype": "Repeating Order",
            "user": frappe.session.user,
            "original_order": original_order,
            "start_date": start_date,
            "cron_pattern": cron_pattern,
            "end_date": end_date,
            "payment_method": payment_method,
            "saved_card": saved_card,
            "ringfenced_amount": ringfenced_amount,
            "is_active": 1,
        }
    )
    repeating_order.insert(ignore_permissions=True)
    return repeating_order.as_dict()


@frappe.whitelist()
def pause_repeating_order(repeating_order_id: str, lang: str = "en"):
    """
    Pauses a repeating order and releases ringfenced funds.
    """
    ro = frappe.get_doc("Repeating Order", repeating_order_id)
    if ro.is_active and ro.payment_method == "Wallet" and ro.ringfenced_amount > 0:
        user_doc = frappe.get_doc("User", ro.user)
        user_doc.set(
            "wallet_balance",
            (user_doc.get("wallet_balance") or 0.0) + ro.ringfenced_amount,
        )
        user_doc.set(
            "ringfenced_balance",
            (user_doc.get("ringfenced_balance") or 0.0) - ro.ringfenced_amount,
        )
        user_doc.save(ignore_permissions=True)

        # Log Release Transaction
        transaction = frappe.get_doc(
            {
                "doctype": "Transaction",
                "user": ro.user,
                "amount": ro.ringfenced_amount,
                "status": "Success",
                "type": "Wallet Release",
                "reference_doctype": "Repeating Order",
                "reference_docname": repeating_order_id,
            }
        )
        transaction.insert(ignore_permissions=True)

        ro.ringfenced_amount = 0

    ro.is_active = 0
    ro.save(ignore_permissions=True)
    return {"status": "success", "message": "Order paused and funds released"}


@frappe.whitelist()
def resume_repeating_order(repeating_order_id: str, lang: str = "en"):
    """
    Resumes a repeating order and re-ringfences funds.
    """
    ro = frappe.get_doc("Repeating Order", repeating_order_id)

    # Check for expiration before resuming
    if ro.end_date and ro.end_date < datetime.now().date():
        frappe.throw(
            "This auto-order schedule has already ended and cannot be resumed."
        )

    if not ro.is_active and ro.payment_method == "Wallet":
        order_doc = frappe.get_doc("Order", ro.original_order)
        # Re-calculate based on remaining schedule (from now)
        now_str = datetime.now().strftime("%Y-%m-%d")
        new_ringfence = calculate_ringfence_amount(
            ro.cron_pattern, now_str, ro.end_date, order_doc.grand_total
        )

        user_doc = frappe.get_doc("User", ro.user)
        balance = user_doc.get("wallet_balance") or 0.0

        if balance < new_ringfence:
            frappe.throw(
                "Insufficient Wallet Balance to resume this schedule.")

        user_doc.set("wallet_balance", balance - new_ringfence)
        user_doc.set(
            "ringfenced_balance",
            (user_doc.get("ringfenced_balance") or 0.0) + new_ringfence,
        )
        user_doc.save(ignore_permissions=True)

        ro.ringfenced_amount = new_ringfence

    ro.is_active = 1
    ro.save(ignore_permissions=True)
    return {"status": "success", "message": "Order resumed and funds reserved"}


@frappe.whitelist()
def delete_repeating_order(repeating_order_id: str, lang: str = "en"):
    """
    Deletes a repeating order and releases any remaining ringfenced funds.
    """
    ro = frappe.get_doc("Repeating Order", repeating_order_id)
    if ro.ringfenced_amount > 0 and ro.payment_method == "Wallet":
        user_doc = frappe.get_doc("User", ro.user)
        user_doc.set(
            "wallet_balance",
            (user_doc.get("wallet_balance") or 0.0) + ro.ringfenced_amount,
        )
        user_doc.set(
            "ringfenced_balance",
            (user_doc.get("ringfenced_balance") or 0.0) - ro.ringfenced_amount,
        )
        user_doc.save(ignore_permissions=True)

    frappe.delete_doc(
        "Repeating Order",
        repeating_order_id,
        ignore_permissions=True)
    return {"status": "success"}
