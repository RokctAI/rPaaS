# API Reference: admin_management

Source file: `paas/api/admin_management/admin_management.py`

## Whitelisted API Endpoints

### `def get_all_shops(limit_start=0, limit_page_length=20)`
Retrieves a list of all shops on the platform (for admins).

### `def get_all_roles(limit_start=0, limit_page_length=20)`
Retrieves a list of all roles on the platform (for admins).

### `def create_shop(shop_data)`
Creates a new shop (for admins).

### `def update_shop(shop_name, shop_data)`
Updates a shop (for admins).

### `def delete_shop(shop_name)`
Deletes a shop (for admins).

### `def get_all_users(limit_start=0, limit_page_length=20)`
The get_all_users function retrieves a list of all users on the platform, intended for administrative use. It accepts two parameters: limit_start, which specifies the starting point of the result set, defaulting to 0, and limit_page_length, which determines the number of users to return, defaulting to 20. The function returns a list of user objects, each containing the user's name, full name, email, and enabled status.
