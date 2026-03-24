import frappe


def get_context(context):
    marketing_site_url = frappe.conf.get("marketing_site_url")

    if marketing_site_url:
        site_name = frappe.local.site
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = (
            f"{marketing_site_url}/?site_name={site_name}"
        )
