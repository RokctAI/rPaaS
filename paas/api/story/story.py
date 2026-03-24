import frappe


@frappe.whitelist()
def get_story(page: int = 1, lang: str = "en"):
    """
    Retrieves a list of stories grouped by shop for Flutter.
    """
    stories = frappe.get_list(
        "Story",
        fields=[
            "name",
            "shop",
            "image",
            "title",
            "product",
            "creation",
            "modified",
        ],
        limit_start=(page - 1) * 10,
        limit=10,
    )

    grouped = {}
    for s in stories:
        shop_id = s.shop
        if not shop_id:
            continue

        if shop_id not in grouped:
            grouped[shop_id] = []

        shop_logo = frappe.db.get_value("Shop", shop_id, "logo")

        grouped[shop_id].append(
            {
                "shop_id": int(shop_id) if shop_id.isdigit() else shop_id,
                "logo_img": shop_logo,
                "title": s.title,
                "product_uuid": s.product,
                "product_title": (
                    frappe.db.get_value("Product", s.product, "product_name")
                    if s.product
                    else None
                ),
                "url": s.image,
                "created_at": s.creation.isoformat() if s.creation else None,
                "updated_at": s.modified.isoformat() if s.modified else None,
            }
        )

    return list(grouped.values())
