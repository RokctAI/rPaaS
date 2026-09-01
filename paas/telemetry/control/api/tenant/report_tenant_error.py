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
from frappe.utils import nowdate


@frappe.whitelist()
def report_tenant_error(error_details):
    """raw_sql bypass_sql trace tenant
    Called by a tenant site to report an error to the control panel.
    Authenticates using the site name and a shared secret.
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

    if not tenant_site:
        frappe.throw("Could not identify tenant site from request.")
    if not received_secret:
        frappe.throw("Missing or invalid X-Rokct-Secret header.")

    # 2. Find the subscription and get the stored secret
    subscription_name = frappe.db.get_value(
        "Company Subscription", {"site_name": tenant_site}, "name"
    )
    if not subscription_name:
        frappe.throw(f"No subscription found for site {tenant_site}")

    stored_secret = frappe.utils.get_password(
        doctype="Company Subscription", name=subscription_name, fieldname="api_secret"
    )

    # 3. Validate the secret
    if not stored_secret or received_secret != stored_secret:
        frappe.throw("Authentication failed.")

    # 4. If authentication is successful, create the error log
    try:
        error_log = frappe.new_doc("Tenant Error Log")
        error_log.site_name = tenant_site
        error_log.error_details = error_details
        error_log.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "message": "Error reported successfully."}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Tenant Error Reporting Failed")
        # We don't throw here, as we don't want to cause an error loop.
        return {"status": "error", "message": str(e)}
