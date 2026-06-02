# Tenant context: session.user validation
# Copyright (c) 2025, ROKCT and contributors
# For license information, please see license.txt

import frappe
import json
from paas.whatsapp.responses import send_text


def add_to_cart(session, item_code, options=None):
    """
    Adds an item to the session cart.
    """
    # Parse existing cart
    cart = json.loads(session.cart_items) if session.cart_items else []

    # Check if exists (Simple check: matches item_code AND options)
    # If options differ, it's a new line item.
    found = False
    for item in cart:
        if item['item_code'] == item_code:
            # Check options equality (simplified)
            existing_opts = item.get('options', {})
            new_opts = options or {}
            if existing_opts == new_opts:
                item['qty'] += 1
                found = True
                break

    if not found:
        item = frappe.get_doc("Item", item_code)
        cart.append({
            "item_code": item_code,
            "qty": 1,
            "price": item.standard_rate,
            "name": item.item_name,
            "options": options or {}
        })

    session.cart_items = json.dumps(cart)
    session.save(ignore_permissions=True)

    send_text(session.wa_id, f"✅ Added to cart! You have {len(cart)} items.")
