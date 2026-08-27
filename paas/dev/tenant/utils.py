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
# Tenant context: session.user validation
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
import os


def prevent_uninstall_if_build_active():
    """
    This function is called by the `on_uninstall` hook.
    It prevents the app from being uninstalled if there are active builds.
    """
    active_builds = frappe.get_all(
        "RQ Job",
        filters={
            "status": ["in", ["queued", "started"]],
            "method": "paas.builder.tenant.tasks._generate_flutter_app"
        },
        limit=1
    )

    if active_builds:
        frappe.throw(
            "Cannot uninstall the Rokct app while one or more app builds are in progress. "
            "Please wait for the builds to complete or cancel them from the 'RQ Job' list.")

    print("No active builds found. Proceeding with uninstallation.")


@frappe.whitelist()
def get_available_source_projects() -> Any:
    """Returns a list of available source project folders."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    try:
        source_path = frappe.get_app_path("paas", "builder", "tenant", "source_code")
        if not os.path.exists(source_path):
            return []

        projects = []
        for item in os.listdir(source_path):
            item_path = os.path.join(source_path, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                # Format label: paas_customer -> Customer
                label = item.replace("paas_", "").replace("_", " ").title()
                projects.append({"label": label, "value": item})

        return sorted(projects, key=lambda x: x["label"])
    except Exception as e:
        frappe.log_error(f"Error listing source projects: {e}")
        return []
