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
# Copyright (c) 2025, ROKCT and contributors
# For license information, please see license.txt

import frappe
import json
from ..responses import send_text


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
