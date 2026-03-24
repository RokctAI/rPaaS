import frappe


@frappe.whitelist()
def attach_subscription(subscription_data=None):
    return {"status": True}


@frappe.whitelist()
def get_subscriptions(limit_start=0, limit_page_length=20):
    if frappe.db.exists("DocType", "Subscription"):
        return frappe.get_all("Subscription", fields=["*"])
    return []


@frappe.whitelist()
def create_subscription_transaction(transaction_data=None):
    return {"status": True}
