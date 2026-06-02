# API Reference: product_extra

Source file: `paas/api/product_extra/product_extra.py`

## Whitelisted API Endpoints

### `def create_extra_group(data)`
Creates a new Product Extra Group.

### `def get_extra_groups(shop_id=None)`
Retrieves Extra Groups, optionally filtered by shop.

### `def update_extra_group(name, data)`
Updates an Extra Group.

### `def delete_extra_group(name)`
Deletes an Extra Group.

### `def create_extra_value(data)`
Creates a new Product Extra Value.

### `def get_extra_values(group_id)`
Retrieves Extra Values for a specific group.

### `def update_extra_value(name, data)`
Updates an Extra Value.

### `def delete_extra_value(name)`
Deletes an Extra Value.
