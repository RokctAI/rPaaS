import frappe
import json


@frappe.whitelist(allow_guest=True)
def get_languages(active=True):
    """
    Retrieves list of languages.
    """
    filters = {}
    if active:
        filters["active"] = 1

    return frappe.get_list(
        "PaaS Language",
        filters=filters,
        fields=[
            "name",
            "title",
            "locale",
            "backward",
            "default",
            "active",
            "img",
        ],
    )


@frappe.whitelist(allow_guest=True)
def get_default_language():
    """
    Retrieves the default language.
    """
    return frappe.get_doc("PaaS Language", {"default": 1}).as_dict()


@frappe.whitelist(allow_guest=True)
def get_translations(locale, group=None):
    """
    Retrieves translations for a specific locale, optionally filtered by group.
    Returns a dictionary mapping keys to values, as expected by many frontends.
    """
    filters = {"locale": locale, "status": 1}
    if group:
        filters["group"] = group

    translations = frappe.get_list(
        "PaaS Translation", filters=filters, fields=["key", "value", "group"]
    )

    # Transform into nested dict if needed, or flat key-value pairs
    result = {}
    for t in translations:
        if group:
            result[t.key] = t.value
        else:
            if t.group not in result:
                result[t.group] = {}
            result[t.group][t.key] = t.value

    return result
