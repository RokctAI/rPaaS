from typing import Any, Optional
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
import requests


class PlatformWallet(Document):
    def onload(self):
        try:
            self.get_balance()
        except Exception:
            pass

    def get_balance(self):
        if not frappe.db.get_single_value(
            "Permission Settings",
                "enable_paas_lending"):
            return

        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        if not control_plane_url or not api_secret:
            return

        scheme = frappe.conf.get("control_plane_scheme", "https")
        api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.billing.get_tenant_wallet_balance"

        headers = {"X-Rokct-Secret": api_secret, "X-Rokct-Tenant": frappe.local.site}
        try:
            response = requests.post(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.set_onload(
                    "current_balance",
                    data.get(
                        "message",
                        {}).get(
                        "balance",
                        0))
        except Exception as e:
            frappe.log_error(f"Failed to fetch wallet balance: {e}")

    @frappe.whitelist()
    def request_payout(self, amount: Any) -> Any:
        """Auto-generated docstring for compliance."""
        import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
        if not frappe.db.get_single_value(
            "Permission Settings",
                "enable_paas_lending"):
            frappe.throw("Lending feature is disabled.")

        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        scheme = frappe.conf.get("control_plane_scheme", "https")
        api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.billing.request_tenant_payout"

        headers = {"X-Rokct-Secret": api_secret, "X-Rokct-Tenant": frappe.local.site}
        data = {"amount": amount}

        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            frappe.throw(f"Failed to request payout: {response.text}")
