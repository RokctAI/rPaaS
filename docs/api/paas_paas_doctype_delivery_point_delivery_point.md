# API Reference: delivery_point

Source file: `paas/paas/doctype/delivery_point/delivery_point.py`

## Classes

### class `DeliveryPoint`

## Whitelisted API Endpoints

### `def get_nearest_delivery_points(latitude, longitude, radius=20)`
Get nearest delivery points based on latitude and longitude.
:param latitude: User's latitude
:param longitude: User's longitude
:param radius: Search radius in kilometers (default: 20)
:return: List of nearest delivery points
