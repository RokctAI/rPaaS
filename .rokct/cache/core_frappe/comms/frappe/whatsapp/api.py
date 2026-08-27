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

from typing import Any, Optional
# Copyright (c) 2025, ROKCT and contributors
# For license information, please see license.txt

import frappe
from .utils import get_whatsapp_config
from .handlers import handle_message


@frappe.whitelist(allow_guest=True)
def webhook() -> Any:
    """
    Main entry point for WhatsApp Webhooks.
    Handles verification (GET) and messages (POST).
    """
    if frappe.request.method == "GET":
        return verify_webhook()

    elif frappe.request.method == "POST":
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

    except Exception:
        frappe.log_error(frappe.get_traceback(), "WhatsApp Webhook Error")
        return "Error processing message", 500

    return "Processed", 200
