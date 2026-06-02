# Tenant context: session.user validation
# Copyright (c) 2025, ROKCT and contributors
# For license information, please see license.txt

import frappe
from paas.whatsapp.utils import get_or_create_session
from paas.whatsapp.responses import send_text, send_cart_summary
from paas.whatsapp.api.location import handle_location
from paas.whatsapp.api.shop import handle_interactive


def handle_message(message, wa_id, profile_name):
    """
    Dispatches the message based on its type.
    """
    msg_type = message.get('type')
    session = get_or_create_session(wa_id)

    if msg_type == 'text':
        text = message['text']['body'].lower()
        handle_text(text, session)

    elif msg_type == 'location':
        loc = message['location']
        handle_location(loc['latitude'], loc['longitude'], session)

    elif msg_type == 'interactive':
        reply = message['interactive']
        handle_interactive(reply, session)


def handle_text(text, session):  # noqa: C901
    trace_id = None
    text = text.lower().strip()

    if text in ['hi', 'hello', 'menu', 'start']:
        greeting = "👋 Hello!"
        if session.linked_user:
            first_name = frappe.db.get_value(
                "User", session.linked_user, "first_name")
            if first_name:
                greeting = f"👋 Welcome back, {first_name}!"

        send_text(
            session.wa_id,
            f"{greeting} Please share your location to find shops near you.\n\nTap 📎 -> Location -> Send Current Location.")

    elif text in ['cart', 'checkout', 'basket']:
        send_cart_summary(session.wa_id, session)

    elif session.current_flow == 'checkout_address_input':
        # Routing text as Address Input
        from paas.whatsapp.api.checkout import handle_checkout_action
        handle_checkout_action(session, 'address_input', payload=text)

    else:
        # --- Advanced NLP Router ---
        from paas.whatsapp.api.ai_search import classify_intent, extract_entity, semantic_search, search_global_shops
        from paas.whatsapp.responses import send_shop_list

        # 1. Classify Intent
        intent, score = classify_intent(text)
        print(f"🧠 NLP: Text='{text}' -> Intent='{intent}' (Score={score:.2f})")

        # Threshold for high confidence
        if score < 0.4:
            intent = "unknown"

        # 2. Route based on Intent
        if intent == "action_buy":
            entity = extract_entity(text, intent)
            if not entity:
                send_text(
                    session.wa_id,
                    "What would you like to order? Type the product name.")
                return

            if session.current_shop:
                # Context: Inside Shop -> Search Products
                found_products = semantic_search(entity, session.current_shop)
                if found_products:
                    # Construct Custom List or Text for now
                    msg = f"🔍 *Found matching items for '{entity}':*\n\n"
                    for p in found_products:
                        # Price might need fetching
                        msg += f"• *{p['title']}* (R{p.get('price', '0')})\n"
                    msg += "\nType exact name to view."
                    send_text(session.wa_id, msg)
                else:
                    send_text(
                        session.wa_id,
                        f"🚫 No products found for '{entity}' in this shop.")
            else:
                # Context: No Shop -> Search Global Shops (selling this item)
                found_shops = search_global_shops(entity)
                if found_shops:
                    send_shop_list(session.wa_id, found_shops)
                else:
                    send_text(
                        session.wa_id,
                        f"🚫 No shops found selling '{entity}'. Try sending your location.")

        elif intent == "action_find":
            entity = extract_entity(text, intent)
            found_shops = search_global_shops(entity)
            if found_shops:
                send_shop_list(session.wa_id, found_shops)
            else:
                send_text(session.wa_id, f"🚫 No shops found for '{entity}'.")

        elif intent == "action_view_cart":
            send_cart_summary(session.wa_id, session)

        elif intent == "action_check_wallet":
            if session.linked_user:
                balance = frappe.db.get_value(
                    "User", session.linked_user, "wallet_balance") or 0.0
                send_text(session.wa_id,
                          f"💰 *Wallet Balance*: {frappe.fmt_money(balance)}")
            else:
                send_text(
                    session.wa_id,
                    "🔒 You need to link your account (by placing an order) to check your wallet.")

        elif intent == "action_track":
            if not session.linked_user:
                send_text(
                    session.wa_id,
                    "🔒 Please link your account (by placing an order) to track shipments.")
                return

            # Find active orders (Open, Confirmed, Preparing, On Delivery)
            # Excluding: Delivered, Canceled, Rejected
            orders = frappe.get_all("Order",
                                    filters={
                                        "user": session.linked_user,
                                        # Assuming 5=Delivered, 6=Canceled...
                                        # Checking status IDs later.
                                        "order_status_id": ["not in", [5, 6, 7]]
                                        # actually let's just get last 1 order
                                        # for now
                                    },
                                    order_by="creation desc",
                                    limit=1,
                                    fields=["name", "order_status_id", "total", "active"])

            if orders:
                order = orders[0]
                # Fetch Status Name
                status_name = frappe.db.get_value(
                    "Order Status", order.order_status_id, "title") or "Processing"

                msg = f"📦 *Order #{order.name}*\n"
                msg += f"📊 Status: *{status_name}*\n"
                msg += f"💰 Total: R{order.total}\n\n"
                msg += "We will notify you when it moves!"
                send_text(session.wa_id, msg)
            else:
                send_text(
                    session.wa_id,
                    "🤷‍♂️ You have no active orders to track.")

        elif intent == "misc_greeting":
            send_text(session.wa_id, "👋 Hello! Type 'Menu' to start.")

        else:
            send_text(
                session.wa_id,
                "I didn't understand that. You can range shops, buy items, or view your cart.")
