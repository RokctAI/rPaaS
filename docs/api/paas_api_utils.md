# API Reference: utils

Source file: `paas/api/utils.py`

## Documented Module Functions

### `def _require_admin()`
Helper function to ensure the user has the System Manager role.

### `def _get_seller_shop(user_id)`
Helper function to get the shop for a given user.

### `def api_response(data=None, message=None, status_code=200)`
Standard API response wrapper.

### `def haversine(lat1, lon1, lat2, lon2)`
Calculates the great-circle distance between two points on Earth (in km).
