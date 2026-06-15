from typing import Any, Optional
# Tenant context: session.user validation
import frappe


@frappe.whitelist()
def get_tags(lang: str='en') -> Any:
    """
    Retrieves all tags.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return frappe.get_list("Tag", fields=["name", "description"])
