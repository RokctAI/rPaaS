import frappe
import json
from ..utils import _get_seller_shop


@frappe.whitelist()
def get_seller_stories(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of stories for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    stories = frappe.get_list(
        "Story",
        filters={"shop": shop},
        fields=["name", "title", "image", "expires_at"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return stories


@frappe.whitelist()
def create_seller_story(story_data):
    """
    Creates a new story for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(story_data, str):
        story_data = json.loads(story_data)

    story_data["shop"] = shop

    new_story = frappe.get_doc({"doctype": "Story", **story_data})
    new_story.insert(ignore_permissions=True)
    return new_story.as_dict()


@frappe.whitelist()
def update_seller_story(story_name, story_data):
    """
    Updates a story for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(story_data, str):
        story_data = json.loads(story_data)

    story = frappe.get_doc("Story", story_name)

    if story.shop != shop:
        frappe.throw(
            "You are not authorized to update this story.",
            frappe.PermissionError,
        )

    story.update(story_data)
    story.save(ignore_permissions=True)
    return story.as_dict()


@frappe.whitelist()
def delete_seller_story(story_name):
    """
    Deletes a story for the current seller's shop.
    """
    user = frappe.session.user
    shop = _get_seller_shop(user)

    story = frappe.get_doc("Story", story_name)

    if story.shop != shop:
        frappe.throw(
            "You are not authorized to delete this story.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Story", story_name, ignore_permissions=True)
    return {"status": "success", "message": "Story deleted successfully."}
