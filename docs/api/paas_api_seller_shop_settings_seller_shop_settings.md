# API Reference: seller_shop_settings

Source file: `paas/api/seller_shop_settings/seller_shop_settings.py`

## Whitelisted API Endpoints

### `def get_seller_shop_working_days()`
Retrieves the working days for the current seller's shop.

### `def update_seller_shop_working_days(working_days_data)`
Updates the working days for the current seller's shop.

### `def get_seller_shop_closed_days()`
Retrieves the closed days for the current seller's shop.

### `def add_seller_shop_closed_day(date)`
Adds a closed day for the current seller's shop.

### `def delete_seller_shop_closed_day(date)`
Deletes a closed day for the current seller's shop.

### `def get_shop_users(limit_start=0, limit_page_length=20)`
Retrieves a list of users for the current seller's shop.

### `def add_shop_user(user_email, role)`
<!-- adeb1631882a6f3c17e5736a238fb7d7c09fce58ca47b05a3c8e5eed7753ac2f -->
The add_shop_user function is used to add a user to the current seller's shop with a specific role. It takes two parameters: user_email, which is the email address of the user to be added, and role, which defines the user's role within the shop. The function first checks if the user exists and if they are not already a member of the shop, then adds the user to the shop with the specified role. If the operation is successful, it returns a success status with a corresponding message.

### `def remove_shop_user(user_to_remove)`
Removes a user from the current seller's shop.

### `def get_seller_branches(limit_start=0, limit_page_length=20)`
Retrieves a list of branches for the current seller's shop.

### `def create_seller_branch(branch_data)`
Creates a new branch for the current seller's shop.

### `def update_seller_branch(branch_name, branch_data)`
Updates a branch for the current seller's shop.

### `def delete_seller_branch(branch_name)`
Deletes a branch for the current seller's shop.

### `def get_seller_deliveryman_settings()`
Retrieves the deliveryman settings for the current seller's shop.

### `def update_seller_deliveryman_settings(settings_data)`
Updates the deliveryman settings for the current seller's shop.
