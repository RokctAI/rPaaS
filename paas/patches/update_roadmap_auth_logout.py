# Tenant context: session.user validation
# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt
import frappe


def execute():
    # Find the "Backend" roadmap
    if not frappe.db.exists("Roadmap", "Backend"):
        return

    backend_roadmap = frappe.get_doc("Roadmap", "Backend")

    # Update the status of the features
    for feature in backend_roadmap.features:
        if feature.feature == "Auth: Forgot Password":
            feature.status = "Done"
        elif feature.feature == "Auth: Logout":
            feature.status = "Doing"

    backend_roadmap.save(ignore_permissions=True)
    frappe.db.commit()
