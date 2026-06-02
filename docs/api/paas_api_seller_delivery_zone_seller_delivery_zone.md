# API Reference: seller_delivery_zone

Source file: `paas/api/seller_delivery_zone/seller_delivery_zone.py`

## Whitelisted API Endpoints

### `def get_seller_delivery_zones(limit_start=0, limit_page_length=20)`
Retrieves a list of delivery zones for the current seller's shop.

### `def get_seller_delivery_zone(zone_name)`
Retrieves a single delivery zone with its coordinates for the current seller's shop.

### `def create_seller_delivery_zone(zone_data)`
Creates a new delivery zone for the current seller's shop.

### `def update_seller_delivery_zone(zone_name, zone_data)`
Updates a delivery zone for the current seller's shop.

### `def delete_seller_delivery_zone(zone_name)`
Deletes a delivery zone for the current seller's shop.

### `def check_delivery_fee(lat, lng)`
Checks if a location is within any of the seller's delivery zones and returns the fee.

## Documented Module Functions

### `def is_point_in_polygon(point, polygon)`
Ray-casting algorithm to check if point is in polygon.
Polygon is expected to be a list of dicts with 'lat' and 'lng' or list of lists.
