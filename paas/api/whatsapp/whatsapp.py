# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import frappe


@frappe.whitelist(allow_guest=True)
def flow_endpoint():
    """
    Endpoint for WhatsApp Flows.
    """
    return {"status": "success"}


@frappe.whitelist(allow_guest=True)
def hook():
    """
    Webhook for WhatsApp updates.
    """
    return {"status": "success"}
