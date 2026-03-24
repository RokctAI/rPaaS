# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import uuid
from paas.api.utils import api_response


@frappe.whitelist()
def create_shop(shop_data):
    """
    Creates a new Shop document.
    Only users with 'System Manager' or 'Seller' roles can create a shop.
    """
    if "System Manager" not in frappe.get_roles(
    ) and "Seller" not in frappe.get_roles():
        frappe.throw(
            "You are not authorized to create a shop.",
            frappe.PermissionError)

    if not isinstance(shop_data, dict):
        frappe.throw("shop_data must be a dictionary.", frappe.ValidationError)

    # Set the current user as the owner if not specified
    if 'user' not in shop_data:
        shop_data['user'] = frappe.session.user

    # Generate UUID and slug
    shop_data['uuid'] = str(uuid.uuid4())
    shop_data['slug'] = frappe.utils.slug(shop_data.get('shop_name'))

    try:
        shop = frappe.get_doc({
            "doctype": "Shop",
            **shop_data
        })
        shop.insert(ignore_permissions=True)
        frappe.db.commit()
        return api_response(
            data=shop.as_dict(),
            message="Shop created successfully")
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Shop Creation Failed")
        frappe.throw(f"An error occurred while creating the shop: {e}")


@frappe.whitelist(allow_guest=True)
def get_shops(
        limit_start: int = 0,
        limit_page_length: int = 20,
        order_by: str = "name",
        order: str = "desc",
        latitude: float = None,
        longitude: float = None,
        **kwargs):
    """
    Retrieves a list of shops with pagination and filters. Supports geo-sorting.
    """
    from paas.api.utils import haversine
    import json

    filters = {
        "status": "approved",
        "visibility": 1,
        "open": 1
    }

    if kwargs.get("delivery"):
        filters["delivery"] = 1

    if kwargs.get("takeaway"):
        filters["pickup"] = 1

    # If we are sorting by distance, we might need to fetch more items or all items
    # and then paginate in Python. For simplicity, we'll fetch all matching and then slice.
    # For a few hundred shops, this is fine.
    # Note: Using get_all for potential performance if many shops.
    shops = frappe.get_all(
        "Shop",
        filters=filters,
        fields=[
            "name", "uuid", "slug", "user", "logo", "cover_photo", "phone",
            "address", "location", "status", "type", "min_amount", "tax",
            "delivery_time_type", "delivery_time_from", "delivery_time_to",
            "open", "visibility", "verify", "service_fee", "percentage",
            "enable_cod", "shop_type", "is_ecommerce"
        ]
    )

    # Calculate distance if coordinates provided
    if latitude and longitude:
        for shop in shops:
            loc = shop.get("location")
            if isinstance(loc, str) and loc:
                try:
                    loc_data = json.loads(loc)
                    s_lat = loc_data.get("latitude") or loc_data.get("lat")
                    s_lon = loc_data.get("longitude") or loc_data.get("long")
                    if s_lat and s_lon:
                        shop["distance"] = haversine(
                            float(latitude), float(longitude),
                            float(s_lat), float(s_lon)
                        )
                    else:
                        shop["distance"] = 99999.0
                except (ValueError, json.JSONDecodeError):
                    shop["distance"] = 99999.0
            else:
                shop["distance"] = 99999.0

    # Sort
    if order_by == "distance" and latitude and longitude:
        shops.sort(key=lambda x: x.get("distance", 99999.0))
    else:
        # Standard sorting
        rev = True if order.lower() == "desc" else False
        shops.sort(
            key=lambda x: str(
                x.get(
                    order_by or "name")).lower(),
            reverse=rev)

    # Paginate
    shops_slice = shops[limit_start: limit_start + limit_page_length]

    # Global COD Check
    cash_gateway = frappe.db.get_value(
        "PaaS Payment Gateway", {
            "gateway_controller": "Cash", "enabled": 1})
    is_global_cod_enabled = bool(cash_gateway)

    # Replicating the structure of the legacy ShopResource
    formatted_shops = []
    for shop in shops_slice:
        # Hierarchical COD: Global AND Shop
        is_cod = is_global_cod_enabled and (
            shop.enable_cod if shop.get('enable_cod') is not None else 1)

        formatted_shops.append(
            {
                'id': shop.name,
                'uuid': shop.uuid,
                'slug': shop.slug,
                'user_id': shop.user,
                'tax': shop.tax,
                'service_fee': shop.service_fee,
                'percentage': shop.percentage,
                'phone': shop.phone,
                'open': bool(
                    shop.open),
                'visibility': bool(
                    shop.visibility),
                'verify': bool(
                    shop.verify),
                'logo_img': shop.logo,
                'background_img': shop.cover_photo,
                'min_amount': shop.min_amount,
                'status': shop.status,
                'enable_cod': bool(is_cod),
                'type': shop.shop_type or shop.get('type'),
                'shop_type': shop.shop_type,
                'is_ecommerce': bool(
                    shop.is_ecommerce),
                'distance': shop.get("distance"),
                'delivery_time': {
                    'type': shop.delivery_time_type,
                    'from': shop.delivery_time_from,
                    'to': shop.delivery_time_to},
                'location': shop.location,
                'working_hours': frappe.get_all(
                    "Shop Booking Working Day",
                    filters={
                        "parent": shop.name},
                    fields=[
                        "day",
                        "from_time",
                        "to_time"]),
                'closed_dates': frappe.get_all(
                    "Shop Booking Closed Date",
                    filters={
                        "parent": shop.name},
                    fields=[
                        "date",
                        "reason"]),
                'translation': {
                    'title': shop.name,
                    'address': shop.address}})

    return api_response(data=formatted_shops)


@frappe.whitelist(allow_guest=True)
def get_shop_details(uuid: str):
    """
    Retrieves a single shop by its UUID.
    """
    shop = frappe.get_doc("Shop", {"uuid": uuid})

    if not shop:
        frappe.throw(
            f"Shop with UUID {uuid} not found.",
            frappe.DoesNotExistError)

    # Global COD Check
    cash_gateway = frappe.db.get_value(
        "PaaS Payment Gateway", {
            "gateway_controller": "Cash", "enabled": 1})
    is_global_cod_enabled = bool(cash_gateway)

    # Hierarchical COD: Global AND Shop
    # Note: shop object from get_doc has attributes directly
    is_cod = is_global_cod_enabled and (
        shop.enable_cod if shop.enable_cod is not None else 1)

    # Replicating the structure of the legacy ShopResource
    return api_response(data={
        'id': shop.name,
        'uuid': shop.uuid,
        'slug': shop.slug,
        'user_id': shop.user,
        'tax': shop.tax,
        'service_fee': shop.service_fee,
        'percentage': shop.percentage,
        'phone': shop.phone,
        'open': bool(shop.open),
        'visibility': bool(shop.visibility),
        'verify': bool(shop.verify),
        'logo_img': shop.logo,
        'background_img': shop.cover_photo,
        'min_amount': shop.min_amount,
        'status': shop.status,
        'enable_cod': bool(is_cod),
        'type': shop.shop_type or shop.type,  # Map new shop_type to legacy type field
        'shop_type': shop.shop_type,
        'is_ecommerce': bool(shop.is_ecommerce),
        'delivery_time': {
            'type': shop.delivery_time_type,
            'from': shop.delivery_time_from,
            'to': shop.delivery_time_to
        },
        'location': shop.location,
        'working_hours': [d.as_dict() for d in shop.booking_working_days],
        'closed_dates': [d.as_dict() for d in shop.booking_closed_dates],
        'translation': {
            'title': shop.name,
            'address': shop.address
        }
    })


@frappe.whitelist(allow_guest=True)
def search_shops(
        search: str,
        category_id: int = None,
        limit_start: int = 0,
        limit_page_length: int = 20):
    """
    Searches for shops by name, optionally filtered by category.
    """
    t_shop = frappe.qb.DocType("Shop")
    query = (
        frappe.qb.from_(t_shop) .select(
            t_shop.name,
            t_shop.uuid,
            t_shop.slug,
            t_shop.user,
            t_shop.logo,
            t_shop.cover_photo,
            t_shop.phone,
            t_shop.address,
            t_shop.location,
            t_shop.status,
            t_shop.type,
            t_shop.min_amount,
            t_shop.tax,
            t_shop.delivery_time_type,
            t_shop.delivery_time_from,
            t_shop.delivery_time_to,
            t_shop.open,
            t_shop.visibility,
            t_shop.verify,
            t_shop.service_fee,
            t_shop.percentage,
            t_shop.enable_cod,
            t_shop.shop_type,
            t_shop.is_ecommerce) .where(
            t_shop.open == 1) .where(
                t_shop.status == "approved") .where(
                    t_shop.visibility == 1))

    if category_id:
        query = query.where(t_shop.category == category_id)

    from frappe.query_builder.functions import Function
    to_tsvector = Function("to_tsvector")
    plainto_tsquery = Function("plainto_tsquery")
    query = query.where(
        to_tsvector(
            "english",
            t_shop.shop_name).matches(
            plainto_tsquery(
                "english",
                search)))

    shops = query.limit(limit_page_length).offset(
        limit_start).orderby(t_shop.shop_name).run(as_dict=True)

    # Global COD Check
    cash_gateway = frappe.db.get_value(
        "PaaS Payment Gateway", {
            "gateway_controller": "Cash", "enabled": 1})
    is_global_cod_enabled = bool(cash_gateway)

    formatted_shops = []
    for shop in shops:
        # Hierarchical COD: Global AND Shop
        is_cod = is_global_cod_enabled and (
            shop.enable_cod if shop.enable_cod is not None else 1)

        formatted_shops.append({
            'id': shop.name,
            'uuid': shop.uuid,
            'slug': shop.slug,
            'user_id': shop.user,
            'tax': shop.tax,
            'service_fee': shop.service_fee,
            'percentage': shop.percentage,
            'phone': shop.phone,
            'open': bool(shop.open),
            'visibility': bool(shop.visibility),
            'verify': bool(shop.verify),
            'logo_img': shop.logo,
            'background_img': shop.cover_photo,
            'min_amount': shop.min_amount,
            'status': shop.status,
            'enable_cod': bool(is_cod),
            'type': shop.shop_type or shop.type,  # Map new shop_type to legacy type field
            'shop_type': shop.shop_type,
            'is_ecommerce': bool(shop.is_ecommerce),
            'delivery_time': {
                'type': shop.delivery_time_type,
                'from': shop.delivery_time_from,
                'to': shop.delivery_time_to
            },
            'location': shop.location,
            'translation': {
                'title': shop.name,
                'address': shop.address
            }
        })

    return api_response(data=formatted_shops)


@frappe.whitelist(allow_guest=True)
def get_shop_types():
    """
    Retrieves all available Shop Types.
    """
    types = frappe.get_all(
        "Shop Type",
        fields=[
            "name",
            "title",
            "description",
            "icon"],
        order_by="title asc")
    return api_response(data=types)


@frappe.whitelist(allow_guest=True)
def get_nearby_shops(
        latitude: float,
        longitude: float,
        radius_km: float = 10,
        lang: str = "en"):
    """
    Retrieves a list of shops within a given radius.
    """
    if latitude is None or longitude is None:
        return get_shops()

    if latitude is None or longitude is None:
        return get_shops()

    try:
        lat = float(latitude)
        lon = float(longitude)
        # Convert km to meters for earth_distance
        radius = float(radius_km) * 1000
    except (ValueError, TypeError):
        return get_shops()

    # Use PostgreSQL earthdistance extension (requires cube + earthdistance)
    # We use earth_box for index scan + earth_distance for precise filtering
    # Note: earth_distance returns meters
    query = """
        SELECT name
        FROM "tabShop"
        WHERE
            latitude IS NOT NULL AND longitude IS NOT NULL
            AND earth_box(ll_to_earth(%s, %s), %s) @> ll_to_earth(latitude, longitude)
            AND earth_distance(ll_to_earth(%s, %s), ll_to_earth(latitude, longitude)) < %s
    """

    nearby_shops_data = frappe.db.sql(
        query, (lat, lon, radius, lat, lon, radius), as_dict=True)
    nearby_shop_ids = [s.name for s in nearby_shops_data]

    # Include Ecommerce shops (global reach)
    ecommerce_shops = frappe.get_all(
        "Shop", filters={
            "is_ecommerce": 1}, pluck="name")
    nearby_shop_ids.extend(ecommerce_shops)

    # Unique IDs
    nearby_shop_ids = list(set(nearby_shop_ids))

    # Now use generic get_shops_by_ids to return formatted data
    return get_shops_by_ids(shop_ids=nearby_shop_ids)


@frappe.whitelist()
def get_shops_recommend(latitude: float, longitude: float, lang: str = "en"):
    """
    Returns recommended shops based on location and rating.
    Currently aliases to get_nearby_shops as we lack a rating field.
    """
    return get_nearby_shops(latitude, longitude, radius_km=20, lang=lang)


@frappe.whitelist(allow_guest=True)
def check_driver_zone(shop_id=None, address=None):
    """
    Checks if the address is within the shop's delivery zone.
    Expects address as dict/json with latitude/longitude.
    """
    import json
    if isinstance(address, str):
        try:
            address = json.loads(address)
        except ValueError:
            frappe.throw("Invalid address format", frappe.ValidationError)

    if not address or not address.get(
            "latitude") or not address.get("longitude"):
        frappe.throw(
            "Address must contain latitude and longitude",
            frappe.ValidationError)

    user_lat = float(address.get("latitude"))
    user_lon = float(address.get("longitude"))

    # Get Shop Location
    shop = frappe.db.get_value(
        "Shop", shop_id, [
            "latitude", "longitude"], as_dict=True)
    if not shop or not shop.latitude or not shop.longitude:
        return api_response(
            data={
                "status": False,
                "message": "Shop location not found"})

    shop_lat = float(shop.latitude)
    shop_lon = float(shop.longitude)

    # Calculate distance using earthdistance
    query = """
        SELECT (earth_distance(ll_to_earth(%s, %s), ll_to_earth(%s, %s)) / 1000) as distance_km
    """
    distance_km = frappe.db.sql(
        query, (user_lat, user_lon, shop_lat, shop_lon))[0][0]

    # Default Max Radius: 50km (Can be made configurable in Shop settings
    # later)
    max_radius_km = 50.0

    return api_response(data={
        "status": distance_km <= max_radius_km,
        "distance": round(distance_km, 2)
    })


@frappe.whitelist(allow_guest=True)
def get_shops_by_ids(shop_ids: list = None, **kwargs):
    """
    Retrieves shops by a list of IDs.
    """
    _filters = {}  # noqa: F841
    ids_to_filter = shop_ids

    # Handle possible JSON string or alternative kwarg
    if kwargs.get("shops"):
        try:
            import json
            ids_to_filter = json.loads(
                kwargs.get("shops")) if isinstance(
                kwargs.get("shops"),
                str) else kwargs.get("shops")
        except Exception:
            ids_to_filter = None

    if not ids_to_filter:
        return api_response(data=[])

    shops = frappe.get_list(
        "Shop",
        filters={
            "name": [
                "in",
                ids_to_filter]},
        fields=[
            "name",
            "uuid",
            "slug",
            "user",
            "logo",
            "cover_photo",
            "phone",
            "address",
            "location",
            "status",
            "type",
            "min_amount",
            "tax",
            "delivery_time_type",
            "delivery_time_from",
            "delivery_time_to",
            "open",
            "visibility",
            "verify",
            "service_fee",
            "percentage",
            "enable_cod",
            "shop_type",
            "is_ecommerce"])

    # Simple formatter (reuse get_shops logic ideally, but keep simple here)
    formatted_shops = []
    for shop in shops:
        formatted_shops.append({
            'id': shop.name,
            'uuid': shop.uuid,
            'slug': shop.slug,
            'logo_img': shop.logo,
            'background_img': shop.cover_photo,
            'translation': {
                'title': shop.name,
                'address': shop.address
            }
        })

    return api_response(data=formatted_shops)


@frappe.whitelist()
def check_cashback(shop_id: str, amount: float, lang: str = "en"):
    """
    Checks the cashback for a given shop and amount based on defined rules.
    """
    cashback_rule = frappe.db.get_value(
        "Cashback Rule",
        filters={"shop": shop_id, "min_amount": ["<=", amount]},
        fieldname=["percentage"],
        order_by="min_amount desc",
    )

    if cashback_rule:
        cashback_amount = (amount * cashback_rule) / 100
        return {"cashback_amount": cashback_amount}

    return {"cashback_amount": 0}


@frappe.whitelist(allow_guest=True)
def get_nearest_delivery_points(
        latitude: float,
        longitude: float,
        radius_km: float = 50):
    """
    Retrieves a list of active Delivery Points within a given radius.
    """
    if latitude is None or longitude is None:
        frappe.throw(
            "Latitude and Longitude are required.",
            frappe.ValidationError)

    try:
        lat = float(latitude)
        lon = float(longitude)
        radius = float(radius_km) * 1000  # meters
    except ValueError:
        frappe.throw(
            "Invalid Latitude or Longitude format.",
            frappe.ValidationError)

    # Calculate distance in SQL: earth_distance(ll_to_earth(lat, lon), ll_to_earth(db_lat, db_lon))
    # We select fields matchng the original response
    query = """
        SELECT
            name, latitude, longitude, address, price, active,
            (earth_distance(ll_to_earth(%s, %s), ll_to_earth(latitude, longitude)) / 1000) as distance_km
        FROM "tabDelivery Point"
        WHERE
            active = 1
            AND latitude IS NOT NULL AND longitude IS NOT NULL
            AND earth_box(ll_to_earth(%s, %s), %s) @> ll_to_earth(latitude, longitude)
            AND earth_distance(ll_to_earth(%s, %s), ll_to_earth(latitude, longitude)) < %s
        ORDER BY distance_km ASC
    """

    nearby_points = frappe.db.sql(
        query, (lat, lon, lat, lon, radius, lat, lon, radius), as_dict=True)

    # Format explicitly if needed (frappe.db.sql returns dicts/values)
    # The original returned list of dicts.
    return nearby_points
