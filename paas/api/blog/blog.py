from typing import Any, Optional
# Tenant context: session.user validation
import frappe
import json
from frappe.utils import now_datetime
from paas.api.utils import api_response


@frappe.whitelist()
def create_blog(data: Any) -> Any:
    """
    Creates a new Blog post.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc({"doctype": "Blog", **data})
    doc.insert()
    return api_response(
        data=doc.as_dict(), message="Blog created successfully."
    )


@frappe.whitelist(allow_guest=True)
def get_blogs(type: Any=None, limit: Any=10, start: Any=0) -> Any:
    """
    Retrieves Blogs, optionally filtered by type.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    filters = {"active": 1, "published_at": ["<=", now_datetime()]}
    if type:
        filters["type"] = type

    runs = frappe.get_list(
        "Blog",
        filters=filters,
        fields=[
            "name",
            "title",
            "short_description",
            "img",
            "published_at",
            "author",
            "type",
        ],
        order_by="published_at desc",
        offset=start,
        limit=limit,
    )
    return api_response(data=runs)


@frappe.whitelist(allow_guest=True)
def get_blog_details(name: Any) -> Any:
    """
    Retrieves full details of a Blog post.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return api_response(data=frappe.get_doc("Blog", name).as_dict())


@frappe.whitelist()
def update_blog(name: Any, data: Any) -> Any:
    """
    Updates a Blog post.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Blog", name)
    doc.update(data)
    doc.save()
    return api_response(
        data=doc.as_dict(), message="Blog updated successfully."
    )


@frappe.whitelist()
def delete_blog(name: Any) -> Any:
    """
    Deletes a Blog post.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    frappe.delete_doc("Blog", name)
    return api_response(message="Blog deleted successfully.")


@frappe.whitelist()
def get_admin_blogs(page: int=1, limit: int=10, lang: str='en') -> Any:
    """
    Retrieves all Blogs for Admin (including inactive).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    blogs = frappe.get_list(
        "Blog",
        fields=[
            "name",
            "title",
            "short_description",
            "img",
            "published_at",
            "author",
            "type",
            "active",
        ],
        order_by="creation desc",
        offset=(page - 1) * limit,
        limit=limit,
    )
    return api_response(data=blogs)


# --- Admin Aliases ---
@frappe.whitelist()
def create_admin_blog(data: Any) -> Any:
    """
    Alias for create_blog (Admin usage).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return create_blog(data)


@frappe.whitelist()
def update_admin_blog(name: Any, data: Any) -> Any:
    """
    Alias for update_blog (Admin usage).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return update_blog(name, data)


@frappe.whitelist()
def delete_admin_blog(name: Any) -> Any:
    """
    Alias for delete_blog (Admin usage).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return delete_blog(name)


@frappe.whitelist(allow_guest=True)
def get_blog(name: Any) -> Any:
    """
    Alias for get_blog_details.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return get_blog_details(name)
