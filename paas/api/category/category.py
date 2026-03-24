import frappe
import json
import uuid


@frappe.whitelist()
def get_categories(
    limit_start: int = 0,
    limit_page_length: int = 10,
    order_by: str = "name",
    order: str = "desc",
    parent: bool = False,
    select: bool = False,
    **kwargs,
):
    """
    Retrieves a list of categories with pagination and filters.
    """
    filters = {}
    if parent:
        filters["parent_category"] = ""

    if kwargs.get("type"):
        filters["type"] = kwargs.get("type")

    if kwargs.get("shop_id"):
        filters["shop"] = kwargs.get("shop_id")

    if kwargs.get("active"):
        filters["active"] = int(kwargs.get("active"))

    fields = ["name", "uuid", "type", "image", "active", "status", "shop"]
    if select:
        fields = ["name", "uuid"]

    categories = frappe.get_list(
        "Category",
        fields=fields,
        filters=filters,
        offset=limit_start,
        limit=limit_page_length,
        order_by=f"{order_by} {order}",
    )

    return categories


@frappe.whitelist(allow_guest=True)
def get_category_types():
    """
    Returns a list of all available category types.
    """
    category_meta = frappe.get_meta("Category")
    type_field = category_meta.get_field("type")
    return type_field.options.split("\n")


@frappe.whitelist()
def get_children_categories(
    id: str, limit_start: int = 0, limit_page_length: int = 10
):
    """
    Retrieves the children of a given category.
    """
    categories = frappe.get_list(
        "Category",
        fields=["name", "uuid", "type", "image", "active", "status", "shop"],
        filters={"parent_category": id},
        limit_start=limit_start,
        limit_page_length=limit_page_length,
        order_by="name desc",
    )

    return categories


@frappe.whitelist()
def search_categories(
    search: str, limit_start: int = 0, limit_page_length: int = 10
):
    """
    Searches for categories by a search term.
    """
    t_category = frappe.qb.DocType("Category")
    query = frappe.qb.from_(t_category).select(
        t_category.name,
        t_category.uuid,
        t_category.type,
        t_category.image,
        t_category.active,
        t_category.status,
        t_category.shop,
    )

    from frappe.query_builder.functions import Function

    to_tsvector = Function("to_tsvector")
    plainto_tsquery = Function("plainto_tsquery")
    query = query.where(
        to_tsvector("english", t_category.keywords).matches(
            plainto_tsquery("english", search)
        )
    )

    categories = (
        query.limit(limit_page_length)
        .offset(limit_start)
        .orderby(t_category.name, order=frappe.qb.desc)
        .run(as_dict=True)
    )

    return categories


@frappe.whitelist()
def get_category_by_uuid(uuid: str):
    """
    Retrieves a single category by its UUID.
    """
    category = frappe.get_doc("Category", {"uuid": uuid})
    return category.as_dict()


@frappe.whitelist()
def create_category(category_data):
    """
    Creates a new category.
    """
    if isinstance(category_data, str):
        category_data = json.loads(category_data)

    category_uuid = category_data.get("uuid") or str(uuid.uuid4())

    if not category_data.get("type"):
        frappe.throw("Category type is required.")

    if frappe.db.exists("Category", {"uuid": category_uuid}):
        frappe.throw("Category with this UUID already exists.")

    paas_settings = frappe.get_single("Permission Settings")
    initial_status = (
        "Approved" if paas_settings.auto_approve_categories else "Pending"
    )

    category = frappe.get_doc(
        {
            "doctype": "Category",
            "uuid": category_uuid,
            "slug": category_data.get("slug"),
            "keywords": category_data.get("keywords"),
            "parent_category": category_data.get("parent_category"),
            "type": category_data.get("type"),
            "image": category_data.get("image"),
            "active": category_data.get("active", 1),
            "status": initial_status,
            "shop": category_data.get("shop"),
            "input": category_data.get("input"),
        }
    )
    category.insert(ignore_permissions=True)
    return category.as_dict()


@frappe.whitelist()
def update_category(uuid, category_data):
    """
    Updates an existing category by its UUID.
    """
    if not uuid:
        frappe.throw("UUID is required to update a category.")

    if isinstance(category_data, str):
        category_data = json.loads(category_data)

    category_name = frappe.db.get_value("Category", {"uuid": uuid}, "name")
    if not category_name:
        frappe.throw("Category not found.")

    category = frappe.get_doc("Category", category_name)

    updatable_fields = [
        "slug",
        "keywords",
        "parent_category",
        "type",
        "image",
        "active",
        "status",
        "shop",
        "input",
    ]

    for key, value in category_data.items():
        if key in updatable_fields:
            category.set(key, value)

    category.save(ignore_permissions=True)
    return category.as_dict()


@frappe.whitelist()
def delete_category(uuid):
    """
    Deletes a category by its UUID.
    """
    if not uuid:
        frappe.throw("UUID is required to delete a category.")

    category_name = frappe.db.get_value("Category", {"uuid": uuid}, "name")
    if not category_name:
        frappe.throw("Category not found.")

    frappe.delete_doc("Category", category_name, ignore_permissions=True)

    return {"status": "success", "message": "Category deleted successfully."}
