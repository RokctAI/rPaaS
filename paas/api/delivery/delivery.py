import frappe


def is_point_in_polygon(point, polygon):
    """
    Checks if a point is inside a polygon using the Ray-Casting algorithm.
    `point` should be a dict with 'latitude' and 'longitude'.
    `polygon` should be a list of dicts, each with 'latitude' and 'longitude'.
    """
    x, y = point['latitude'], point['longitude']
    n = len(polygon)
    inside = False

    p1x, p1y = polygon[0]['latitude'], polygon[0]['longitude']
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]['latitude'], polygon[i % n]['longitude']
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


@frappe.whitelist(allow_guest=True)
def get_delivery_zone_by_shop(shop_id: str):
    """
    Retrieves the delivery zone for a given shop.
    """
    if not frappe.db.exists("Company", shop_id):
        frappe.throw("Shop not found.")

    delivery_zone = frappe.get_doc("Delivery Zone", {"shop": shop_id})
    return delivery_zone.as_dict()


@frappe.whitelist(allow_guest=True)
def check_delivery_zone(shop_id: str, latitude: float, longitude: float):
    """
    Checks if a given coordinate is within the delivery zone of a shop.
    """
    if not frappe.db.exists("Company", shop_id):
        frappe.throw("Shop not found.")

    delivery_zone = frappe.get_doc("Delivery Zone", {"shop": shop_id})
    polygon = delivery_zone.get("coordinates")
    point = {"latitude": latitude, "longitude": longitude}

    if is_point_in_polygon(point, polygon):
        return {
            "status": "success",
            "message": "Address is within the delivery zone."}
    else:
        return {
            "status": "error",
            "message": "Address is outside the delivery zone."}


@frappe.whitelist(allow_guest=True)
def get_delivery_points():
    """
    Retrieves a list of all active delivery points.
    """
    delivery_points = frappe.get_list(
        "Delivery Point",
        filters={"active": 1},
        fields=["name", "price", "address", "location", "img"]
    )
    return delivery_points


@frappe.whitelist(allow_guest=True)
def get_delivery_point(name):
    """
    Retrieves a single delivery point by its name.
    """
    return frappe.get_doc("Delivery Point", name).as_dict()


@frappe.whitelist(allow_guest=True)
def get_driver_location(driver_id: str):
    """
    Retrieves the current location of a driver.
    """
    order = frappe.db.get_value("Order", {"deliveryman": driver_id, "status": ["in", ["Accepted", "Shipped"]]}, "name")
    if order:
        loc = frappe.db.get_value("Driver Location", {"order": order}, ["latitude", "longitude"], as_dict=True)
        if loc:
            return {"latitude": loc.latitude, "longitude": loc.longitude}
    return {"latitude": 0.0, "longitude": 0.0}
