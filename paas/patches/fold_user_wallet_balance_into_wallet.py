# Copyright (c) 2026 RokctAI
#
# One-shot ledger fold for installs whose wallet top-ups landed on the
# legacy `User.wallet_balance` custom field (#33). Before the alignment,
# `process_wallet_top_up` credited only that User field while every
# spender — rlms lesson checkout, users' transfers, wallet payments —
# reads the `Wallet` doctype's `balance`, so topped-up money existed but
# was never spendable.
#
# The fold moves each user's legacy balance into their canonical Wallet
# row (created if absent), writes one audit row, and leaves the User
# field holding the same figure it did before — from here on it is a
# delta-shifted mirror of the canonical ledger (see
# `payment._shift_legacy_user_balance`). Ringfenced funds are untouched:
# commerce moves them OUT of `wallet_balance` into `ringfenced_balance`
# at ringfence time, so whatever sits in `wallet_balance` is genuinely
# unreserved money.
#
# Additive on purpose: a Wallet row funded by refunds or transfers holds
# money the legacy field never saw, so the two stores are summed, not
# reconciled to the larger of the two.

import frappe


def execute():
    if not frappe.db.table_exists("Wallet"):
        return
    if not frappe.get_meta("User").has_field("wallet_balance"):
        return

    rows = frappe.get_all(
        "User",
        filters=[["wallet_balance", ">", 0]],
        fields=["name", "wallet_balance"],
    )
    for row in rows:
        legacy = float(row.wallet_balance or 0)
        if legacy <= 0:
            continue

        wallet_name = frappe.db.get_value("Wallet", {"user": row.name}, "name")
        if wallet_name:
            wallet = frappe.get_doc("Wallet", wallet_name)
        else:
            wallet = frappe.get_doc(
                {"doctype": "Wallet", "user": row.name, "balance": 0}
            )
            wallet.insert(ignore_permissions=True)

        wallet.balance = float(wallet.balance or 0) + legacy
        wallet.save(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": "Wallet History",
                "wallet": wallet.name,
                "transaction_type": "Topup",
                "amount": legacy,
                "status": "Processed",
                "description": (
                    "Legacy User.wallet_balance folded into the Wallet "
                    "ledger (#33 alignment)"
                ),
            }
        ).insert(ignore_permissions=True)
