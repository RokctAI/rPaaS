# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import frappe


@frappe.whitelist()
def get_tags(lang: str = "en"):
    """
    Retrieves all tags.
    """
    return frappe.get_list("Tag", fields=["name", "description"])
