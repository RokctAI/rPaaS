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

# Phase-2 control->SDK extraction (2026-08-24): moved here verbatim from
# control/control/seeds/scripts/seed_paas_payments.py (RokctAI/control).
# The Laravel-era juvo seed DUMPS (control/control/seeds/*.json, ~380k lines)
# deliberately REMAIN in the control repo, pending Ray's archive/delete
# decision. This script does not read those dumps - the legacy payments.sql /
# payment_payloads.sql data was already migrated into the inline gateway list
# below, and credentials come from site config (frappe.conf). NOTE: this
# seeder touches pay/gateways-owned settings doctypes (Paystack Settings,
# PayFast Settings, Mpesa Settings) - flagged for pay/gateways review.

import frappe


def get_conf_credential(key):
    """Read a credential from site config, failing loudly if it is missing."""
    value = frappe.conf.get(key)
    if not value:
        frappe.throw(
            f"Missing required site config key '{key}'. "
            f"Add it to site_config.json (or common_site_config.json) before running this seed."
        )
    return value


def execute():
    # Seed Gateways on ALL sites, but only seed Credentials on 'juvo.tenant.rokct.ai'
    is_juvo_site = frappe.local.site == "juvo.tenant.rokct.ai"

    print("--- Seeding Payment Gateways ---")

    # Gateway data migrated from legacy payments.sql and payment_payloads.sql.
    # Credentials are read from site config (frappe.conf) and are only required
    # on the Juvo site, where they get seeded into the settings doctypes.
    gateways = [
        {"gateway": "Cash", "active": 1, "sandbox": 0, "settings": {}},
        {"gateway": "Wallet", "active": 1, "sandbox": 0, "settings": {}},
        {"gateway": "PayPal", "active": 0, "sandbox": 0, "settings": {}},
        {"gateway": "Stripe", "active": 0, "sandbox": 0, "settings": {}},
        {
            "gateway": "Paystack",
            "active": 0,
            "sandbox": 0,
            "settings": {
                "doctype": "Paystack Settings",
                "public_key": lambda: get_conf_credential("paystack_public_key"),
                "secret_key": lambda: get_conf_credential("paystack_secret_key")
            }
        },
        {
            "gateway": "PayFast",
            "active": 1,
            "sandbox": 1,
            "settings": {
                "doctype": "PayFast Settings",
                "merchant_id": lambda: get_conf_credential("payfast_merchant_id"),
                "merchant_key": lambda: get_conf_credential("payfast_merchant_key"),
                "passphrase": lambda: get_conf_credential("payfast_passphrase"),
                "is_sandbox": 1 # Syncing with active/sandbox status
            }
        },
        {"gateway": "Mpesa", "active": 0, "sandbox": 0, "settings": {"doctype": "Mpesa Settings", "sandbox": 0}},
        {"gateway": "Braintree", "active": 0, "sandbox": 0, "settings": {}}
    ]

    for g in gateways:
        gateway_name = g["gateway"]
        active = g["active"]
        # sandbox is used in settings update logic
        settings = g.get("settings", {})

        try:
            # 1. Create/Update Payment Gateway Registry (Runs on ALL sites)
            if not frappe.db.exists("Payment Gateway", gateway_name):
                doc = frappe.get_doc({
                    "doctype": "Payment Gateway",
                    "gateway": gateway_name,
                    "active": active
                })
                doc.insert(ignore_permissions=True)
                print(f"Created Payment Gateway: {gateway_name} (Active: {active})")
            else:
                doc = frappe.get_doc("Payment Gateway", gateway_name)
                if doc.active != active:
                    doc.active = active
                    doc.save()
                    print(f"Updated Payment Gateway: {gateway_name} (Active: {active})")

            # 2. Update Settings DocType (Credentials ONLY on Juvo site)
            if is_juvo_site and settings and "doctype" in settings:
                settings_doctype = settings.pop("doctype")
                if not frappe.db.exists("DocType", settings_doctype):
                    continue

                doc = frappe.get_doc(settings_doctype)
                updated = False
                for key, val in settings.items():
                    if callable(val):
                        # Credential values are deferred site-config reads;
                        # resolve them only here, on the site that seeds them.
                        val = val()
                    if str(doc.get(key)) != str(val):
                        doc.set(key, val)
                        updated = True

                if updated:
                    doc.save()
                    print(f"Updated {settings_doctype} configuration.")

        except Exception as e:
            print(f"Error processing gateway {gateway_name}: {e}")

    frappe.db.commit()
