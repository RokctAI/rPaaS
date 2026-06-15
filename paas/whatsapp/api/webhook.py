from typing import Any, Optional
# Copyright (c) 2025, ROKCT and contributors
# For license information, please see license.txt

import frappe
from paas.whatsapp.utils import get_whatsapp_config
from paas.whatsapp.api.message import handle_message
from paas.whatsapp.utils import validate_signature


@frappe.whitelist(allow_guest=True)
def webhook() -> Any:
    """
    Main entry point for WhatsApp Webhooks.
    Handles verification (GET) and messages (POST).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if frappe.request.method == "GET":
        return verify_webhook()

    elif frappe.request.method == "POST":
        # Signature Verification
        config = get_whatsapp_config()
        if config and config.app_secret:
            signature = frappe.request.headers.get("X-Hub-Signature-256")
            if not signature:
                frappe.throw("Missing Signature", frappe.PermissionError)

            # frappe.request.get_data() gives raw bytes needed for HMAC
            if not validate_signature(
                    frappe.request.get_data(),
                    signature,
                    config.get_password('app_secret')):
                frappe.throw("Invalid Signature", frappe.PermissionError)

        return process_webhook()


def verify_webhook():
    """
    Handles the Meta Webhook Verification Challenge.
    """
    hub_mode = frappe.request.args.get("hub.mode")
    hub_challenge = frappe.request.args.get("hub.challenge")
    hub_verify_token = frappe.request.args.get("hub.verify_token")

    config = get_whatsapp_config()
    if not config:
        frappe.throw(
            "WhatsApp is not configured for this tenant.",
            frappe.AuthenticationError)

    if hub_mode == "subscribe" and hub_verify_token == config.verify_token:
        frappe.response.status_code = 200
        frappe.response.raw = int(hub_challenge)
        return

    frappe.response.status_code = 403
    return "Verification token mismatch"


def process_webhook():
    """
    Processes incoming messages from Meta.
    """
    data = frappe.request.json
    if not data:
        return

    try:
        # Check if it's a message or status update
        entry = data.get('entry', [])[0]
        changes = entry.get('changes', [])[0]
        value = changes.get('value', {})

        if 'messages' in value:
            message = value['messages'][0]
            # Extract contact info for wa_id/phone
            contact = value.get('contacts', [{}])[0]
            profile_name = contact.get('profile', {}).get('name')

            # Use 'wa_id' from contacts if available, else from message 'from'
            wa_id = contact.get('wa_id') or message['from']

            handle_message(message, wa_id, profile_name)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "WhatsApp Webhook Error")
        return "Error processing message", 500

    return "Processed", 200
