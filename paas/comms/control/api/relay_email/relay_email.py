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

import frappe
import json
import subprocess


@frappe.whitelist()
def relay_email(recipients, subject, message):
    """raw_sql bypass_sql trace tenant
    Securely relays an email from a tenant site through the control panel.
    Authenticates the tenant using their site name and API secret.
    """
    # This API should only ever run on the control panel.
    if frappe.conf.get("app_role") != "control":
        frappe.throw(
            "This action can only be performed on the control panel.",
            title="Action Not Allowed",
        )

    # 1. Get tenant identity and secret from request
    tenant_site = (
        frappe.local.request.headers.get("X-Rokct-Tenant") or frappe.local.request.host
    )
    received_secret = frappe.local.request.headers.get("X-Rokct-Secret")

    if not tenant_site or not received_secret:
        frappe.throw(
            "Authentication failed: Missing credentials.", frappe.AuthenticationError
        )

    # 2. Find the subscription and validate the secret
    subscription_name = frappe.db.get_value(
        "Company Subscription", {"site_name": tenant_site}, "name"
    )
    if not subscription_name:
        frappe.throw(
            f"No subscription found for site {tenant_site}", frappe.AuthenticationError
        )

    stored_secret = frappe.utils.get_password(
        doctype="Company Subscription", name=subscription_name, fieldname="api_secret"
    )
    if received_secret != stored_secret:
        frappe.throw(
            "Authentication failed: Invalid credentials.", frappe.AuthenticationError
        )

    # 3. If authenticated, send the email
    try:
        # Set a flag to prevent this from being logged by the Brain module
        frappe.flags.is_email_relay = True
        frappe.sendmail(
            recipients=recipients, subject=subject, message=message, now=True
        )
        return {"status": "success", "message": "Email relayed successfully."}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Email Relay Failed")
        # Do not throw here, as we don't want to break the tenant's UI.
        # Just return an error status.
        return {"status": "error", "message": str(e)}
