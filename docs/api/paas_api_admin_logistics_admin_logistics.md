# API Reference: admin_logistics

Source file: `paas/api/admin_logistics/admin_logistics.py`

## Whitelisted API Endpoints

### `def get_deliveryman_global_settings()`
Retrieves the global deliveryman settings (for admins).

### `def update_deliveryman_global_settings(settings_data)`
Updates the global deliveryman settings (for admins).

### `def get_parcel_order_settings(limit_start=0, limit_page_length=20)`
Retrieves a list of all parcel order settings (for admins).

### `def create_parcel_order_setting(setting_data)`
Creates a new parcel order setting (for admins).

### `def update_parcel_order_setting(setting_name, setting_data)`
Updates a parcel order setting (for admins).

### `def delete_parcel_order_setting(setting_name)`
Deletes a parcel order setting (for admins).

### `def get_all_delivery_zones(limit_start=0, limit_page_length=20)`
Retrieves a list of all delivery zones on the platform (for admins).

### `def get_delivery_vehicle_types(limit_start=0, limit_page_length=20)`
Retrieves a list of all delivery vehicle types on the platform (for admins).

### `def create_delivery_vehicle_type(type_data)`
Creates a new delivery vehicle type (for admins).

### `def update_delivery_vehicle_type(type_name, type_data)`
Updates a delivery vehicle type (for admins).

### `def delete_delivery_vehicle_type(type_name)`
Deletes a delivery vehicle type (for admins).

### `def get_all_delivery_man_delivery_zones(limit_start=0, limit_page_length=20)`
Retrieves a list of all delivery man delivery zones on the platform (for admins).

### `def get_all_shop_working_days(limit_start=0, limit_page_length=20)`
Retrieves a list of all shop working days on the platform (for admins).

### `def get_all_shop_closed_days(limit_start=0, limit_page_length=20)`
Retrieves a list of all shop closed days on the platform (for admins).
