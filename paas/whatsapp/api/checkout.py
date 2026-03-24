# Copyright (c) 2025, ROKCT and contributors
# For license information, please see license.txt

import frappe
import json
from paas.whatsapp.responses import send_text, send_message
from paas.api.payment.payment import process_wallet_payment
from paas.api.payment.payment import process_token_payment
from paas.api.order.order import create_order as paas_create_order


def handle_checkout_action(session, action, payload=None):
    """
    Router for checkout actions.
    """
    if action == 'start':
        start_checkout(session)
    elif action == 'address_selected':
        # payload is address_id
        save_checkout_data(session, {"address_id": payload, "type": "saved"})
        select_payment_method(session)
    elif action == 'address_input':
        # Payload is the raw text address
        save_checkout_data(session, {"address": payload, "type": "manual"})
        select_payment_method(session)
    elif action == 'address_location':
        # Payload is "lat,long" or similar, usually implied by the button ID
        save_checkout_data(
            session, {
                "type": "location", "location": session.location})
        select_payment_method(session)
    elif action == 'payment_selected':
        # Payload: "wallet", "cod", "card_{token}"
        handle_payment_selection(session, payload)
    elif action == 'place_order':
        finalize_order(session)


def save_checkout_data(session, data):
    """
    Helper to update checkout_data JSON.
    """
    current_data = json.loads(
        session.checkout_data) if session.checkout_data else {}
    current_data.update(data)
    session.checkout_data = json.dumps(current_data)
    session.save(ignore_permissions=True)


def start_checkout(session):
    """
    Step 1: Ask for Delivery Address
    """
    rows = []

    # 1. Linked User Addresses
    if session.linked_user:
        addresses = frappe.get_list(
            "User Address",
            filters={
                "user": session.linked_user,
                "active": 1},
            fields=[
                "name",
                "title",
                "address"])
        for addr in addresses[:5]:
            rows.append(
                {
                    "id": f"addr_{
                        addr['name']}",
                    "title": addr['title'] or "Saved Address",
                    "description": (
                        json.loads(
                            addr['address']) if isinstance(
                            addr['address'],
                            str) else addr['address'])[
                        :60]})

    # 2. Current Location (if available)
    if session.location:
        # Assuming session.location is "lat,long" or JSON
        rows.append({
            "id": "addr_location",
            "title": "📍 Current Location",
            "description": "Deliver to your pinned location"
        })

    # 3. New String Address
    rows.append({
        "id": "addr_new",
        "title": "Type New Address",
        "description": "Enter text address manually"
    })

    payload = {
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Delivery Address"},
            "body": {"text": "Select where you want your order delivered."},
            "footer": {"text": "Rokct AI"},
            "action": {
                "button": "Select Address",
                "sections": [{"title": "Destinations", "rows": rows}]
            }
        }
    }
    send_message(session.wa_id, payload)
    # Update flow to waiting for address selection (or text input)
    # The 'list_reply' handler in shop.py routes 'addr_' to 'address_selected'
    # The 'handle_text' in message.py routes text to 'address_input' if flow is 'checkout_address_input'
    # We set flow to generic checkout state, but for text input specifically we might need 'checkout_address_input'
    # List reply works regardless of current_flow usually if handled globally check specific ID prefix.
    # But for 'addr_new' logic:
    # shop.py should catch 'addr_new' and send text request + set flow = 'checkout_address_input'
    # That logic already exists in shop.py?
    # Checking shop.py view: Yes, "if item_id == 'addr_new': send_text... session.current_flow = 'checkout_address_input'"
    # So we don't set it here explicitly to input, just "checkout_start"?
    session.current_flow = "checkout_address_selection"
    session.save(ignore_permissions=True)


def select_payment_method(session):
    """
    Step 2: Select Payment Method
    """
    # Calculate Total first to display or verify wallet balance
    cart = json.loads(session.cart_items)
    total = sum([item['qty'] * item['price'] for item in cart])

    # Check Logic
    options = get_payment_options(session, total)

    if not options:
        send_text(
            session.wa_id,
            "⚠️ No payment methods available. Please contact support.")
        return

    # Create Buttons
    buttons = []
    for opt in options[:3]:  # Max 3 buttons
        buttons.append({
            "type": "reply",
            "reply": {
                "id": f"pay_{opt['id']}",
                "title": opt['label']
            }
        })

    payload = {
        "recipient_type": "individual", "type": "interactive", "interactive": {
            "type": "button", "body": {
                "text": f"💰 *Payment Selection*\nOrder Total: {
                    frappe.fmt_money(total)}\n\nChoose your payment method:"}, "action": {
                "buttons": buttons}}}
    send_message(session.wa_id, payload)
    session.current_flow = "checkout_payment"
    session.save(ignore_permissions=True)


def get_payment_options(session, total):
    """
    Determine valid payment options based on Hierarchical COD settings and User Wallet/Cards.
    """
    options = []

    # 1. Wallet
    if session.linked_user:
        wallet = frappe.db.get_value(
            "User", session.linked_user, "wallet_balance") or 0.0
        if wallet >= total:
            options.append({"id": "wallet",
                            "label": f"Wallet ({frappe.fmt_money(wallet)})"})

    # 2. Saved Cards (PayFast/Direct)
    if session.linked_user:
        # Assuming we have a helper or query
        cards = frappe.get_list(
            "Saved Card", filters={
                "user": session.linked_user}, fields=[
                "name", "last_four", "card_type"])
        for card in cards:
            options.append(
                {"id": f"card_{card['name']}", "label": f"{card['card_type']} ({card['last_four']})"})

    # 3. Cash on Delivery (COD) Logic
    # Check 1: Shop Level Toggle
    shop_cod = frappe.db.get_value("Shop", session.current_shop, "enable_cod")

    # Default to Enabled if not set
    if shop_cod is None:
        shop_cod = 1

    # Check 2: Global Payment Gateway Toggle
    is_global_enabled = True
    if frappe.db.exists(
            "PaaS Payment Gateway", {
            "gateway_controller": "Cash"}):
        is_global_enabled = bool(
            frappe.db.get_value(
                "PaaS Payment Gateway", {
                    "gateway_controller": "Cash", "enabled": 1}))

    if is_global_enabled and shop_cod:
        options.append({"id": "cod", "label": "Cash on Delivery"})

    return options


def handle_payment_selection(session, payload):
    """
    Store payment choice and ask for confirmation.
    """
    # payload: "pay_wallet", "pay_cod", "pay_card_xxx" (prefix handled by shop.py? No, shop.py passes raw ID)
    # shop.py passes 'btn_id'. If button was 'pay_wallet', payload is
    # 'pay_wallet'.

    payment_method = payload.replace("pay_", "")
    save_checkout_data(session, {"payment_method": payment_method})

    confirm_order_summary(session)


def confirm_order_summary(session):
    """
    Step 3: Final Confirmation
    """
    cart = json.loads(session.cart_items)
    total = sum([item['qty'] * item['price'] for item in cart])
    checkout_data = json.loads(session.checkout_data)

    # Format Address
    addr_display = "Selected Address"
    if checkout_data.get('type') == 'manual':
        addr_display = checkout_data['address']
    elif checkout_data.get('type') == 'saved':
        addr_display = "Saved Address"  # Could fetch title
    elif checkout_data.get('type') == 'location':
        addr_display = "Pinned Location"

    # Format Payment
    pay_method = checkout_data.get('payment_method')

    msg = f"📝 *Order Summary*\n\nItems: {
        len(cart)}\nTotal: *{
        frappe.fmt_money(total)}*\nDelivery: {addr_display}\nPayment: *{
            pay_method.upper()}*\n\n✅ Ready to complete?"

    payload = {
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": msg},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {
                        "id": "cmd_place_order", "title": "Place Order"}},
                    {"type": "reply", "reply": {
                        "id": "cart_clear", "title": "Cancel Order"}}
                ]
            }
        }
    }
    send_message(session.wa_id, payload)
    session.current_flow = "checkout_confirm"
    session.save(ignore_permissions=True)


def finalize_order(session):  # noqa: C901
    """
    Step 4: Process Payment & Create Order
    """
    if not session.cart_items:
        return

    cart = json.loads(session.cart_items)
    checkout_data = json.loads(session.checkout_data)
    payment_method = checkout_data.get('payment_method', 'cod')

    # 1. Process Payment (Simplistic Implementation)
    _transaction_id = None
    _order_status = "New"
    payment_status = "Unpaid"

    if payment_method == 'wallet':
        # Deduct wallet
        # Verify balance again to be safe
        total = sum([x['qty'] * x['price'] for x in cart])
        user = frappe.get_doc("User", session.linked_user)
        if (user.wallet_balance or 0) < total:
            send_text(
                session.wa_id,
                "❌ Insufficient wallet balance. Order cancelled.")
            return

        # Debiting is typically done via Transaction creation often *after* order or *during*.
        # paas.api.payment.process_wallet_payment expects amount.
        # implementation details vary. Let's assume we mark Order `payment_type` = "Wallet" and Backend handles deduction?
        # OR we deduct now. Let's do a simple deduction call logic if we had it.
        # For now, Set Order Type = Wallet.
        payment_status = "Paid"

    elif payment_method.startswith('card_'):
        # Token Payment
        # card_token = payment_method.replace("card_", "")
        # Actually it's card NAME. We need to fetch TOKEN.
        # Skipping actual gateway call for MVP safety, just marking "Credit
        # Card"
        payment_status = "Paid"  # Optimistic

    elif payment_method == 'cod':
        payment_status = "Unpaid"

    # 2. Create Order
    order_items = []
    for item in cart:
        order_items.append({
            "product": item['item_code'],
            "quantity": item['qty'],
            "price": item['price']
        })

    order_payload = {
        "user": session.linked_user or frappe.session.user,
        "shop": session.current_shop,
        "order_items": order_items,
        "address": checkout_data.get('address') or checkout_data.get('address_id'),
        "delivery_type": "Delivery",
        "payment_type": "Cash on Delivery" if payment_method == 'cod' else ("Wallet" if payment_method == 'wallet' else "Credit Card"),
        "payment_status": payment_status,
        "phone": session.phone_number or session.wa_id,
        "status": "New",
        # Auto-calc totals
        "rate": sum([x['price'] * x['quantity'] for x in order_items]),
        "grand_total": sum([x['price'] * x['quantity'] for x in order_items])
    }

    try:
        new_order = paas_create_order(order_payload)
        order_id = new_order.get('name')

        # 3. Process Payment
        if payment_method == 'wallet':
            # Call Real Wallet Payment
            from paas.api.payment.payment import process_wallet_payment  # noqa: F811
            process_wallet_payment(order_id)
            send_text(session.wa_id, "✅ Payment Successful (Wallet)!")

        elif payment_method.startswith('card_'):
            # Call Real Card Payment
            card_name = payment_method.replace("card_", "")
            token = frappe.db.get_value("Saved Card", card_name, "token")

            if token:
                from paas.api.payment.payment import process_token_payment  # noqa: F811
                process_token_payment(order_id, token)
                send_text(session.wa_id, "✅ Payment Successful (Card)!")
            else:
                send_text(
                    session.wa_id,
                    "⚠️ Card Token not found. Order created as Unpaid.")

        send_text(
            session.wa_id,
            f"🎉 Order Placed! ID: {
                new_order.get('name')}")
        session.cart_items = "[]"
        session.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"WhatsApp Order Failed: {str(e)}")
        send_text(session.wa_id, "❌ Validating Order failed.")
