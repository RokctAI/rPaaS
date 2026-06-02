# Tenant context: session.user validation
# Copyright (c) 2025, ROKCT and contributors
# For license information, please see license.txt

import frappe
from paas.whatsapp.responses import (
    send_text, send_shop_list, send_category_list,
    send_product_list, send_product_card, send_product_flow,
    send_cart_summary
)
from paas.whatsapp.utils import get_whatsapp_config
from paas.whatsapp.api.cart import add_to_cart
from paas.api.shop.shop import get_shops
from paas.api.product.product import get_products_by_category


def handle_interactive(reply, session):  # noqa: C901
    """
    Handles List Selections, Button Clicks, and Flow Responses.
    """
    type_ = reply['type']

    if type_ == 'nfm_reply':
        # WhatsApp Flow Response
        response_json = reply['nfm_reply']['response_json']
        flow_data = frappe.parse_json(response_json)

        # We encoded product ID in flow_token or flow_data?
        # Typically flow_token is passed back in the webhook payload, not inside nfm_reply directly?
        # Actually nfm_reply is inside the 'interactive' object.
        # But wait, did we store the item_code?
        # Let's assume flow_data contains hidden field 'item_code' or we parse it from somewhere.
        # Or simplistic: The flow response returns selected options.

        # NOTE: For this implementation we will assume the Context is lost unless passed in Flow Data.
        # Ideally we should store "current_product_view" in Session.

        # Let's fetch the last viewed product from session or rely on flow data returning it.
        # Adding a temporary fallback.
        item_code = flow_data.get('item_code')  # Must be hidden field in Flow
        if item_code:
            add_to_cart(session, item_code, options=flow_data)
        else:
            send_text(
                session.wa_id,
                "❌ Error processing selection. Please try again.")

    elif type_ == 'list_reply':
        item_id = reply['list_reply']['id']

        if item_id.startswith("addr_"):
            from paas.whatsapp.api.checkout import handle_checkout_action
            # Handle Address Select
            if item_id == "addr_new":
                # Trigger manual input
                from paas.whatsapp.responses import send_text
                send_text(
                    session.wa_id,
                    "📍 Please type your full delivery address:")
                session.current_flow = "checkout_address_input"
                session.save(ignore_permissions=True)
            elif item_id == "addr_location":
                handle_checkout_action(session, 'address_location')
            else:
                handle_checkout_action(
                    session, 'address_selected', payload=item_id)

        elif item_id.startswith("shop_"):
            shop_uuid = item_id.split("_")[1]
            session.current_shop = frappe.db.get_value(
                "Shop", {"uuid": shop_uuid}, "name")
            session.save(ignore_permissions=True)

            # Fetch Categories (Simplistic Fetch)
            categories = frappe.get_list("Category", fields=["name", "uuid"])
            send_category_list(session.wa_id, categories, shop_uuid)

        elif item_id.startswith("cat_"):
            parts = item_id.split("_")
            cat_uuid = parts[1]

            # Fetch Products
            products = get_products_by_category(cat_uuid, limit_page_length=10)
            send_product_list(session.wa_id, products)

        elif item_id.startswith("prod_"):
            # Product List Selection -> Show Card
            prod_name = item_id.split("prod_")[1]
            product = frappe.get_doc("Item", prod_name).as_dict()

            # Check for Flows Config
            config = get_whatsapp_config()
            # Check if product has variants (mock check for now)
            has_variants = False  # product.get('has_variants')

            # If Config has Flow ID and Product needs it, send Flow
            if config.flow_id and has_variants:
                send_product_flow(session.wa_id, product, config.flow_id)
            else:
                send_product_card(session.wa_id, product)

        elif item_id == "cmd_view_cart":
            send_cart_summary(session.wa_id, session)

    elif type_ == 'button_reply':
        btn_id = reply['button_reply']['id']

        if btn_id == 'loc_confirm':
            # Location Confirmed -> Show Shops
            config = get_whatsapp_config()

            if config.is_multi_vendor:
                # Mocking Geo Search
                all_shops = get_shops(limit_page_length=20)
                # Filter out Ecommerce shops for WhatsApp
                shops = [s for s in all_shops if s.get(
                    'shop_type') != 'Ecommerce' and not s.get('is_ecommerce')]
                send_shop_list(session.wa_id, shops[:10])
            else:
                # Single Vendor -> Go to Default Shop
                session.current_shop = config.default_shop
                session.save(ignore_permissions=True)
                categories = frappe.get_list(
                    "Category", fields=["name", "uuid"])
                send_category_list(session.wa_id, categories, "default")

        elif btn_id == 'loc_retry':
            send_text(session.wa_id, "Please send your location again.")

        elif btn_id.startswith("add_"):
            prod_name = btn_id.split("add_")[1]
            add_to_cart(session, prod_name)

        elif btn_id == 'cart_checkout':
            from paas.whatsapp.api.checkout import handle_checkout_action
            handle_checkout_action(session, 'start')

        elif btn_id == 'cart_clear':
            session.cart_items = "[]"
            session.save(ignore_permissions=True)
            send_text(session.wa_id, "Cart cleared.")

        elif btn_id == 'cmd_place_order':
            from paas.whatsapp.api.checkout import handle_checkout_action
            handle_checkout_action(session, 'place_order')

        elif btn_id.startswith('pay_'):
            from paas.whatsapp.api.checkout import handle_checkout_action
            handle_checkout_action(session, 'payment_selected', payload=btn_id)
