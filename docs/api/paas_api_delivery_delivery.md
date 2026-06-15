# API Reference: delivery

Source file: `paas/api/delivery/delivery.py`

## Whitelisted API Endpoints

### `def get_delivery_zone_by_shop(shop_id)`
Auto-generated docstring for compliance.

### `def check_delivery_zone(shop_id, latitude, longitude)`
Auto-generated docstring for compliance.

### `def get_delivery_points()`
Retrieves a list of all active delivery points.

### `def get_delivery_point(name)`
Retrieves a single delivery point by its name.

### `def get_driver_location(driver_id)`
Retrieves the current location of a driver.

## Documented Module Functions

### `def is_point_in_polygon(point, polygon)`
Checks if a point is inside a polygon using the Ray-Casting algorithm.
`point` should be a dict with 'latitude' and 'longitude'.
`polygon` should be a list of dicts, each with 'latitude' and 'longitude'.
