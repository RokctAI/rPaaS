# API Reference: delivery_man

Source file: `paas/api/delivery_man/delivery_man.py`

## Whitelisted API Endpoints

### `def get_deliveryman_orders(limit_start=0, limit_page_length=20)`
Retrieves a list of orders assigned to the current deliveryman.

### `def get_deliveryman_parcel_orders(limit_start=0, limit_page_length=20)`
Retrieves a list of parcel orders assigned to the current deliveryman.

### `def get_deliveryman_settings()`
Retrieves the settings for the current deliveryman.

### `def update_deliveryman_settings(settings_data)`
Updates the settings for the current deliveryman.

### `def get_deliveryman_statistics()`
Retrieves statistics for the current deliveryman.

### `def get_banned_shops()`
Retrieves a list of shops from which the current deliveryman is banned.

### `def get_payment_to_partners(limit_start=0, limit_page_length=20)`
Retrieves a list of payments to partners (deliverymen) for the current user.

### `def get_deliveryman_order_report(from_date, to_date)`
Retrieves a report of orders and parcel orders for the current deliveryman within a date range.

### `def get_deliveryman_delivery_zones()`
Retrieves a list of delivery zones assigned to the current deliveryman.
