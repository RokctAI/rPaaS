# API Reference: delivery

Source file: `paas/api/delivery/delivery.py`

## Whitelisted API Endpoints

### `def get_delivery_zone_by_shop(shop_id)`
<!-- 3136027afc203a9f32f0a7a060ce2982004c413b6bb52d5eef5cae60511a7fac -->
The get_delivery_zone_by_shop function retrieves the delivery zone associated with a specific shop. It takes one parameter, shop_id, which is a string representing the unique identifier of the shop. The function first checks if the provided shop_id exists in the database, throwing an error if it does not. If the shop exists, it retrieves the corresponding delivery zone document and returns it as a dictionary.

### `def check_delivery_zone(shop_id, latitude, longitude)`
<!-- 17f6907f7881f017e054bcc9f3a78adbf4a8e55185e5593dc7bfe9a33b1e9c16 -->
The check_delivery_zone function determines whether a specific geographic location falls within the designated delivery area of a particular shop. It takes three parameters: shop_id, which is a unique string identifier for the shop, and latitude and longitude, which are floating-point values representing the coordinates of the location to be checked. The function returns a dictionary containing a status indicator and a corresponding message, indicating whether the location is within the delivery zone of the specified shop.

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
