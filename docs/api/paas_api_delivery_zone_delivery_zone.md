# API Reference: delivery_zone

Source file: `paas/api/delivery_zone/delivery_zone.py`

## Whitelisted API Endpoints

### `def create_delivery_zone(data)`
Creates a new Delivery Zone.

### `def get_shop_delivery_zones(shop_id)`
Retrieves all Delivery Zones for a shop.

### `def update_delivery_zone(name, data)`
Updates a Delivery Zone.

### `def delete_delivery_zone(name)`
Deletes a Delivery Zone.

### `def check_delivery_availability(lat, lng, shop_id=None)`
Checks if a location is within any delivery zone.
If shop_id is provided, checks only that shop's zones.
Returns list of shops that deliver to this location.

## Documented Module Functions

### `def is_point_in_polygon(lat, lng, polygon)`
Ray-casting algorithm to check if point is in polygon.
Polygon is list of [lng, lat] coordinates (GeoJSON standard).
lat: Y, lng: X
