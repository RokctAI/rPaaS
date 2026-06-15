# API Reference: parcel

Source file: `paas/api/parcel/parcel.py`

## Whitelisted API Endpoints

### `def create_parcel_order(order_data)`
Auto-generated docstring for compliance.

### `def get_parcel_orders(limit=20, offset=0, status=None)`
Retrieves a paginated list of parcel orders for the current user.

### `def get_user_parcel_order(name)`
Retrieves a single parcel order for the current user.

### `def update_parcel_status(parcel_order_id, status)`
Updates the status of a specific parcel order with state machine validation and role checks.

### `def get_types()`
Retrieves all available Parcel Types (Parcel Order Settings).

### `def calculate_price(type_id, address_from, address_to)`
Calculates the delivery price based on distance and parcel type settings.
address_from/to: JSON strings or dicts with latitude/longitude.

### `def add_parcel_review(parcel_id, rating, review=None)`
Adds a review to a completed parcel order.
