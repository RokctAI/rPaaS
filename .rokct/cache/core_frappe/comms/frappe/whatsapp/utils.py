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


def get_whatsapp_config():
    """
    Fetches the WhatsApp Tenant Configuration.
    Assumes Single Tenant Config per Site.
    """
    config = frappe.get_single("WhatsApp Tenant Config")
    if not config.enabled:
        return None
    return config


@frappe.whitelist()
def get_admin_whatsapp_config() -> Any:
    """
    Returns the config for the Admin Settings page (even if disabled).
    """
    return frappe.get_single("WhatsApp Tenant Config")


@frappe.whitelist()
def save_whatsapp_config(enabled: Any=0, phone_number_id: Any=None, access_token: Any=None, app_secret: Any=None, verify_token: Any=None) -> Any:
    """
    Updates the WhatsApp Tenant Config.
    """
    doc = frappe.get_single("WhatsApp Tenant Config")
    doc.enabled = 1 if (enabled == 1 or enabled ==
                        "1" or enabled is True) else 0
    doc.phone_number_id = phone_number_id
    doc.access_token = access_token
    doc.app_secret = app_secret
    doc.verify_token = verify_token
    doc.save()
    return doc


def get_or_create_session(wa_id, phone_number=None, name=None):
    """
    Retrieves or creates a WhatsApp Session for the given wa_id.
    """
    session_name = frappe.db.get_value(
        "WhatsApp Session", {
            "wa_id": wa_id}, "name")

    if session_name:
        session = frappe.get_doc("WhatsApp Session", session_name)
    else:
        # Try to find existing user by phone
        # wa_id is usually '2782...' (No +)
        # User.phone might be '+27...' or '082...'
        # We try exact match or suffix match
        linked_user = None

        # Simple exact match first
        user_name = frappe.db.get_value("User", {"phone": wa_id}, "name")
        if not user_name:
            # Try with '+' prefix
            user_name = frappe.db.get_value(
                "User", {"phone": f"+{wa_id}"}, "name")

        linked_user = user_name

        session = frappe.get_doc({
            "doctype": "WhatsApp Session",
            "wa_id": wa_id,
            "phone_number": phone_number or wa_id,
            "linked_user": linked_user,
            "expiry": frappe.utils.add_lines(frappe.utils.now_datetime(), hours=24),
            "cart_items": "[]"
        })
        session.insert(ignore_permissions=True)
        frappe.db.commit()

        session.insert(ignore_permissions=True)
        frappe.db.commit()

    return session


def validate_signature(payload, signature, app_secret):
    """
    Validates the X-Hub-Signature-256 header using the App Secret.
    """
    import hmac
    import hashlib

    if not app_secret:
        # If no secret configured, we can't validate (or we fail secure? User choice. Let's log warning and pass for smooth transition if empty)
        # Security Best Practice: Fail if expected but missing.
        # But for MVP transition:
        return False

    # Signature format: "sha256=..."
    if not signature.startswith("sha256="):
        return False

    sig = signature.split("sha256=")[1]

    # Calculate HMAC
    calculated_sig = hmac.new(
        key=app_secret.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(sig, calculated_sig)
