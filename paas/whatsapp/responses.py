# Tenant context: session.user validation
# Copyright (c) 2025, ROKCT and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from paas.whatsapp.utils import get_whatsapp_config


def send_message(wa_id, payload):
    """
    Sends a payload to the Meta Graph API.
    """
    config = get_whatsapp_config()
    if not config:
        return

    url = f"https://graph.facebook.com/v21.0/{config.phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {config.access_token}",
        "Content-Type": "application/json"
    }

    # Ensure 'to' is set
    payload['to'] = wa_id
    payload['messaging_product'] = "whatsapp"

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        frappe.log_error(f"Meta API Error: {str(e)}", "WhatsApp Send Failed")


def send_text(wa_id, text):
    payload = {
        "recipient_type": "individual",
        "type": "text",
        "text": {"body": text}
    }
    send_message(wa_id, payload)


def send_shop_list(wa_id, shops):
    """
    Sends a List Message with available shops.
    """
    if not shops:
        send_text(wa_id, "🚫 No shops found in your area.")
        return

    # Meta Limit: 10 rows per section
    # We will just show the top 10 for now.
    rows = []
    for shop in shops[:10]:
        rows.append({
            "id": f"shop_{shop['uuid']}",
            "title": shop['name'][:24],  # Max 24 chars
            "description": shop.get('description', '')[:72]  # Max 72 chars
        })

    payload = {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "Select a Shop"
            },
            "body": {
                "text": f"We found {len(shops)} shops near you."
            },
            "footer": {
                "text": "Powered by ROKCT"
            },
            "action": {
                "button": "View Shops",
                "sections": [
                    {
                        "title": "Nearby Shops",
                        "rows": rows
                    }
                ]
            }
        }
    }
    send_message(wa_id, payload)


def send_category_list(wa_id, categories, shop_id):
    """
    Sends a List Message with shop categories.
    """
    rows = []
    # Assuming categories have 'uuid' and 'name'
    for cat in categories[:10]:
        rows.append({
            "id": f"cat_{cat['uuid']}_{shop_id}",
            "title": cat['name'][:24]
        })

    payload = {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {
                "text": "Select a Category"
            },
            "action": {
                "button": "Menu",
                "sections": [
                    {
                        "title": "Categories",
                        "rows": rows
                    }
                ]
            }
        }
    }
    send_message(wa_id, payload)


def send_product_list(wa_id, products):
    """
    Sends a List Message with products.
    """
    rows = []
    for p in products[:10]:
        price = p.get('standard_rate', 0)
        rows.append({
            "id": f"prod_{p['name']}",  # Using Item Name/Code as ID
            "title": p['item_name'][:24],
            "description": f"R{price} - {p.get('description', '')[:60]}"
        })

    payload = {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "Menu"
            },
            "body": {
                "text": "Select an item to view details"
            },
            "action": {
                "button": "View Items",
                "sections": [
                    {
                        "title": "Products",
                        "rows": rows
                    }
                ]
            }
        }
    }
    send_message(wa_id, payload)


def send_product_card(wa_id, product):
    """
    Sends an Image Message with Buttons (Add, Customize).
    """
    # Construct Image URL (Assuming public access or hosted)
    image_url = product.get('image')
    if image_url and image_url.startswith("/"):
        site_url = frappe.utils.get_url()
        image_url = f"{site_url}{image_url}"
    elif not image_url:
        # Fallback image or just send text?
        # For now, let's assume image exists or we send text card
        pass

    caption = f"*{product['item_name']}*\n\n{product.get('description',
                                                         '')}\n\n*Price: R{product.get('standard_rate',
                                                                                       0)}*"

    interactive = {
        "type": "button",
        "body": {
            "text": "Select an option:" if not image_url else None
        },
        "action": {
            "buttons": [
                {
                    "type": "reply",
                    "reply": {
                        "id": f"add_{product['name']}",
                        "title": "🛒 Add to Cart"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "back_cat",  # Simplified back
                        "title": "🔙 Back to Menu"
                    }
                }
            ]
        }
    }

    if image_url:
        payload = {
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {
                    "type": "image",
                    "image": {"link": image_url}
                },
                "body": {
                    "text": caption
                },
                "action": interactive['action']
            }
        }
    else:
        # Text Only Card
        payload = {
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": caption},
                "action": interactive['action']
            }
        }

    send_message(wa_id, payload)


def send_product_flow(wa_id, product, flow_id):
    """
    Sends a WhatsApp Flow for product customization.
    """
    _config = get_whatsapp_config()

    # Construct the initial screen data (if your flow expects it)
    # This depends on how the Flow is built in Meta Flow Builder.
    # Assuming standard "product_customizer" flow with "screen_0"

    # Simple flow invocation
    payload = {
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "flow",
            "header": {
                "type": "text",
                "text": f"Customize {product.get('item_name')}"
            },
            "body": {
                "text": "Please select your options below."
            },
            "footer": {
                "text": "Rokct AI"
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_message_version": "3",
                    # Pass Product ID in token
                    "flow_token": f"prod_{product.get('name')}",
                    "flow_id": flow_id,
                    "flow_cta": "Customize",
                    "flow_action": "navigate",
                    "flow_action_payload": {
                        "screen": "screen_0",  # Default start screen
                        "data": {
                            "product_name": product.get('item_name'),
                            "price": str(product.get('standard_rate'))
                            # Add extras/options here if Flow supports dynamic
                            # data
                        }
                    }
                }
            }
        }
    }

    send_message(wa_id, payload)


def send_cart_summary(wa_id, session):
    """
    Sends a text summary of the cart with a 'Checkout' button.
    """
    cart = json.loads(session.cart_items) if session.cart_items else []

    if not cart:
        send_text(wa_id, "🛒 Your cart is empty.")
        return

    # Build Message
    msg_lines = ["🛒 *Your Cart*"]
    total = 0.0

    for item in cart:
        line_total = item['qty'] * item['price']
        total += line_total

        # Format options if any
        opts_str = ""
        if item.get('options'):
            # Simplify options display
            opt_list = []
            for k, v in item['options'].items():
                if k not in ['product_name', 'price']:  # Filter internal keys
                    # If generic object structure from flow
                    if isinstance(v, list):
                        vals = [x.get('title', x) for x in v]
                        opt_list.append(f"{', '.join(vals)}")
                    else:
                        opt_list.append(str(v))
            if opt_list:
                opts_str = f" _({', '.join(opt_list)})_"

        msg_lines.append(
            f"• {item['qty']}x *{item['name']}*{opts_str} - {frappe.fmt_money(line_total)}")

    msg_lines.append(f"\n*Total: {frappe.fmt_money(total)}*")

    body_text = "\n".join(msg_lines)

    # Interactive Message with Checkout Button
    payload = {
        "recipient_type": "individual",
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": body_text
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "cart_checkout",
                            "title": "✅ Checkout"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "cart_clear",
                            "title": "❌ Clear Cart"
                        }
                    }
                ]
            }
        }
    }

    send_message(wa_id, payload)


def send_static_map_confirmation(wa_id, lat, long):
    """
    Generates and sends a static map image for location confirmation.
    """
    from staticmap import StaticMap, CircleMarker

    # 1. Generate Map
    m = StaticMap(
        400,
        400,
        url_template='http://a.tile.openstreetmap.org/{z}/{x}/{y}.png')
    marker = CircleMarker((float(long), float(lat)), 'red', 18)
    m.add_marker(marker)

    # 2. Save to Public File
    filename = f"map_{wa_id}.png"
    # Ensure /files exists in public folder?
    # Better to use frappe.save_file logic but here we render to bytes usually.
    # StaticMap renders to PIL Image.
    image = m.render(zoom=15)

    # Save as Frappe File to get public URL
    # Convert PIL to bytes
    from io import BytesIO
    byte_io = BytesIO()
    image.save(byte_io, format='PNG')

    saved_file = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "is_private": 0,
        "content": byte_io.getvalue()
    })
    saved_file.save(ignore_permissions=True)

    image_url = f"{frappe.utils.get_url()}{saved_file.file_url}"

    # 3. Send Image with Buttons
    payload = {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {
                "type": "image",
                "image": {"link": image_url}
            },
            "body": {
                "text": "📍 We pinned your location here. Is this accurate?"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "loc_confirm",
                            "title": "✅ Yes, Confirm"
                        }
                    },
                    {
                        "type": "reply",
                        "reply": {
                            "id": "loc_retry",
                            "title": "🔄 Retry"
                        }
                    }
                ]
            }
        }
    }
    send_message(wa_id, payload)
