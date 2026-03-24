import frappe


@frappe.whitelist(allow_guest=True)
def check_coupon(code: str, shop_id: str, qty: int = 1):
    """
    Checks if a coupon is valid for a given shop.
    """
    if not code or not shop_id:
        frappe.throw("Code and shop ID are required.")

    coupon = frappe.db.get_value(
        "Coupon",
        filters={"code": code, "shop": shop_id},
        fieldname=["name", "expired_at", "quantity"],
        as_dict=True,
    )

    if not coupon:
        return {"status": "error", "message": "Invalid Coupon"}

    if (
        coupon.get("expired_at")
        and coupon.get("expired_at") < frappe.utils.now_datetime()
    ):
        return {"status": "error", "message": "Coupon expired"}

    if coupon.get("quantity") is not None and coupon.get("quantity") < qty:
        return {"status": "error", "message": "Coupon has been fully used"}

    # Check if the user has already used this coupon
    if frappe.session.user != "Guest" and frappe.db.exists(
        "Coupon Usage", {"user": frappe.session.user, "coupon": coupon.name}
    ):
        return {
            "status": "error",
            "message": "You have already used this coupon.",
        }

    return frappe.get_doc("Coupon", coupon.name).as_dict()
