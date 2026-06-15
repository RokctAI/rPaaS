from typing import Any, Optional
# Tenant context: session.user validation
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe


@frappe.whitelist()
def get_banners(page: int=1, limit_page_length: int=10) -> Any:
    """
    Fetches a paginated list of banners.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return frappe.get_all(
        "Banner",
        fields=["name", "title", "image", "url"],
        limit=limit_page_length,
        offset=(page - 1) * limit_page_length,
        order_by="creation desc"
    )


@frappe.whitelist()
def get_banner(id: str) -> Any:
    """
    Fetches a single banner.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return frappe.get_doc("Banner", id)


@frappe.whitelist()
def get_ads(page: int=1) -> Any:
    """
    Fetches a paginated list of banners that are marked as ads.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return frappe.get_all(
        "Banner",
        filters={"is_ad": 1, "is_active": 1},
        fields=["name", "title", "image", "link"],
        limit=10,
        offset=(page - 1) * 10,
    )


@frappe.whitelist()
def get_ad(id: str) -> Any:
    """
    Fetches a single banner that is marked as an ad.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return frappe.get_doc("Banner", id)


@frappe.whitelist()
def like_banner(id: str) -> Any:
    """
    Increments the 'likes' count on a banner.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    banner = frappe.get_doc("Banner", id)
    banner.likes = banner.likes + 1
    banner.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "success", "likes": banner.likes}
