# Copyright (c) 2025, ROKCT and contributors
# For license information, please see license.txt

import frappe
import json
from paas.whatsapp.utils import get_or_create_session, get_whatsapp_config
from paas.whatsapp.responses import (
    send_text, send_shop_list, send_category_list,
    send_product_list, send_product_card, send_static_map_confirmation
)
from paas.api.shop.shop import get_shops
from paas.api.product.product import get_products_by_category


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


def handle_text(text, session):
    if text in ['hi', 'hello', 'menu', 'start']:
        send_text(
            session.wa_id,
            "👋 Hello! Please share your location to find shops near you.\n\nTap 📎 -> Location -> Send Current Location.")
    else:
        # Default fallback
        send_text(
            session.wa_id,
            "I didn't understand that. Type 'Hi' to start.")


def handle_location(lat, long, session):
    # 1. Update Session Location
    session.location = json.dumps({"lat": lat, "long": long})
    session.save(ignore_permissions=True)

    # 2. Send Confirmation Map
    send_static_map_confirmation(session.wa_id, lat, long)


def handle_interactive(reply, session):
    type_ = reply['type']

    if type_ == 'list_reply':
        item_id = reply['list_reply']['id']
        _title = reply['list_reply']['title']

        if item_id.startswith("shop_"):
            shop_uuid = item_id.split("_")[1]
            shop_name = frappe.db.get_value(
                "Shop", {"uuid": shop_uuid}, "name")
            session.current_shop = shop_name
            session.save(ignore_permissions=True)

            # Fetch Categories that actually have items in this shop
            category_names = frappe.get_all(
                "Item",
                filters={"shop": shop_name, "disabled": 0},
                pluck="item_group",
                distinct=True
            )
            categories = frappe.get_list(
                "Category",
                filters={"name": ["in", category_names]},
                fields=["name", "uuid"]
            )
            send_category_list(session.wa_id, categories, shop_uuid)

        elif item_id.startswith("cat_"):
            parts = item_id.split("_")
            cat_uuid = parts[1]
            # shop_id = parts[2] # If passed

            # Fetch Products
            products = get_products_by_category(cat_uuid, limit_page_length=10)
            send_product_list(session.wa_id, products)

        elif item_id.startswith("prod_"):
            # Product List Selection -> Show Card
            # item_name or name? list uses name if unique
            prod_name = item_id.split("prod_")[1]
            # Fetch full details
            product = frappe.get_doc("Item", prod_name).as_dict()
            send_product_card(session.wa_id, product)

    elif type_ == 'button_reply':
        btn_id = reply['button_reply']['id']

        if btn_id == 'loc_confirm':
            # Location Confirmed -> Show Shops
            config = get_whatsapp_config()

            if config.is_multi_vendor:
                # Geo Search using session location
                loc = json.loads(session.location) if session.location else {}
                shops = get_shops(
                    limit_page_length=10,
                    latitude=loc.get("lat"),
                    longitude=loc.get("long"),
                    order_by="distance"
                )
                send_shop_list(session.wa_id, shops)
            else:
                # Single Vendor -> Go to Default Shop
                session.current_shop = config.default_shop
                session.save(ignore_permissions=True)
                # Send Categories
                categories = frappe.get_list(
                    "Category", fields=["name", "uuid"])
                send_category_list(session.wa_id, categories, "default")

        elif btn_id == 'loc_retry':
            send_text(session.wa_id, "Please send your location again.")

        elif btn_id.startswith("add_"):
            prod_name = btn_id.split("add_")[1]
            add_to_cart(session, prod_name)


def add_to_cart(session, item_code):
    # Parse existing cart
    cart = json.loads(session.cart_items) if session.cart_items else []

    # Check if exists
    found = False
    for item in cart:
        if item['item_code'] == item_code:
            item['qty'] += 1
            found = True
            break

    if not found:
        item = frappe.get_doc("Item", item_code)
        cart.append({
            "item_code": item_code,
            "qty": 1,
            "price": item.standard_rate,
            "name": item.item_name
        })

    session.cart_items = json.dumps(cart)
    session.save(ignore_permissions=True)

    send_text(session.wa_id, f"✅ Added to cart! You have {len(cart)} items.")
