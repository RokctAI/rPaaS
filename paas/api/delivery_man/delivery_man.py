import frappe
import json


@frappe.whitelist()
def get_deliveryman_orders(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of orders assigned to the current deliveryman.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your orders.",
            frappe.AuthenticationError,
        )

    orders = frappe.get_list(
        "Order",
        filters={"deliveryman": user},
        fields=["name", "shop", "total_price", "status", "creation"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return orders


@frappe.whitelist()
def get_deliveryman_parcel_orders(
    limit_start: int = 0, limit_page_length: int = 20
):
    """
    Retrieves a list of parcel orders assigned to the current deliveryman.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your parcel orders.",
            frappe.AuthenticationError,
        )

    orders = frappe.get_list(
        "Parcel Order",
        filters={"deliveryman": user},
        fields=["name", "status", "total_price", "delivery_date"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return orders


@frappe.whitelist()
def get_deliveryman_settings():
    """
    Retrieves the settings for the current deliveryman.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your settings.",
            frappe.AuthenticationError,
        )

    if not frappe.db.exists("Deliveryman Settings", {"user": user}):
        return {}

    return frappe.get_doc("Deliveryman Settings", {"user": user}).as_dict()


@frappe.whitelist()
def update_deliveryman_settings(settings_data):
    """
    Updates the settings for the current deliveryman.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update your settings.",
            frappe.AuthenticationError,
        )

    if isinstance(settings_data, str):
        settings_data = json.loads(settings_data)

    if not frappe.db.exists("Deliveryman Settings", {"user": user}):
        settings = frappe.new_doc("Deliveryman Settings")
        settings.user = user
    else:
        settings = frappe.get_doc("Deliveryman Settings", {"user": user})

    settings.update(settings_data)
    settings.save(ignore_permissions=True)
    return settings.as_dict()


@frappe.whitelist()
def get_deliveryman_statistics():
    """
    Retrieves statistics for the current deliveryman.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your statistics.",
            frappe.AuthenticationError,
        )

    # Total completed orders
    completed_orders_count = frappe.db.count(
        "Order", filters={"deliveryman": user, "status": "Delivered"}
    )

    # Total completed parcel orders
    completed_parcel_orders_count = frappe.db.count(
        "Parcel Order", filters={"deliveryman": user, "status": "Delivered"}
    )

    # Total earnings from regular orders
    t_order = frappe.qb.DocType("Order")
    total_order_earnings = (
        frappe.qb.from_(t_order)
        .select(frappe.qb.fn.Sum(t_order.delivery_fee))
        .where(t_order.deliveryman == user)
        .where(t_order.status == "Delivered")
    ).run()[0][0] or 0

    # Total earnings from parcel orders
    t_parcel_order = frappe.qb.DocType("Parcel Order")
    total_parcel_earnings = (
        frappe.qb.from_(t_parcel_order)
        .select(frappe.qb.fn.Sum(t_parcel_order.delivery_fee))
        .where(t_parcel_order.deliveryman == user)
        .where(t_parcel_order.status == "Delivered")
    ).run()[0][0] or 0

    total_earnings = total_order_earnings + total_parcel_earnings

    return {
        "completed_orders": completed_orders_count,
        "completed_parcel_orders": completed_parcel_orders_count,
        "total_orders": completed_orders_count + completed_parcel_orders_count,
        "total_earnings": total_earnings,
    }


@frappe.whitelist()
def get_banned_shops():
    """
    Retrieves a list of shops from which the current deliveryman is banned.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your banned shops.",
            frappe.AuthenticationError,
        )

    banned_shops = frappe.get_all(
        "Shop Ban", filters={"deliveryman": user}, fields=["shop"]
    )
    return [d.shop for d in banned_shops]


@frappe.whitelist()
def get_payment_to_partners(limit_start: int = 0, limit_page_length: int = 20):
    """
    Retrieves a list of payments to partners (deliverymen) for the current user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your payments.",
            frappe.AuthenticationError,
        )

    payouts = frappe.get_list(
        "Payout",
        filters={"deliveryman": user},
        fields=["name", "amount", "payment_date", "status"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="payment_date desc",
    )
    return payouts


@frappe.whitelist()
def get_deliveryman_order_report(from_date: str, to_date: str):
    """
    Retrieves a report of orders and parcel orders for the current deliveryman within a date range.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your order report.",
            frappe.AuthenticationError,
        )

    orders = frappe.get_all(
        "Order",
        filters={
            "deliveryman": user,
            "status": "Delivered",
            "creation": ["between", [from_date, to_date]],
        },
        fields=["name", "shop", "total_price", "status", "creation"],
        order_by="creation desc",
    )

    parcel_orders = frappe.get_all(
        "Parcel Order",
        filters={
            "deliveryman": user,
            "status": "Delivered",
            "creation": ["between", [from_date, to_date]],
        },
        fields=["name", "status", "total_price", "delivery_date"],
        order_by="creation desc",
    )

    return {"orders": orders, "parcel_orders": parcel_orders}


@frappe.whitelist()
def get_deliveryman_delivery_zones():
    """
    Retrieves a list of delivery zones assigned to the current deliveryman.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your delivery zones.",
            frappe.AuthenticationError,
        )

    delivery_zones = frappe.get_all(
        "Deliveryman Delivery Zone",
        filters={"deliveryman": user},
        fields=["delivery_zone"],
    )
    return [d.delivery_zone for d in delivery_zones]
