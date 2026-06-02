# API Reference: admin_data

Source file: `paas/api/admin_data/admin_data.py`

## Whitelisted API Endpoints

### `def get_all_units(limit_start=0, limit_page_length=20)`
Retrieves a list of all shop units on the platform (for admins).

### `def get_all_tags(limit_start=0, limit_page_length=20)`
Retrieves a list of all shop tags on the platform (for admins).

### `def get_all_points(limit_start=0, limit_page_length=20)`
Retrieves a list of all points on the platform (for admins).

### `def create_point(point_data)`
Creates a new point record (for admins).

### `def update_point(point_name, point_data)`
Updates a point record (for admins).

### `def delete_point(point_name)`
Deletes a point record (for admins).

### `def get_all_translations(limit_start=0, limit_page_length=20)`
Retrieves a list of all translations on the platform (for admins).

### `def get_all_referrals(limit_start=0, limit_page_length=20)`
Retrieves a list of all referrals on the platform (for admins).

### `def create_referral(referral_data)`
Creates a new referral (for admins).

### `def delete_referral(referral_name)`
Deletes a referral (for admins).

### `def get_all_shop_tags(limit_start=0, limit_page_length=20)`
Retrieves a list of all shop tags on the platform (for admins).

### `def get_all_product_extra_groups(limit_start=0, limit_page_length=20)`
Retrieves a list of all product extra groups on the platform (for admins).

### `def get_all_product_extra_values(limit_start=0, limit_page_length=20)`
Retrieves a list of all product extra values on the platform (for admins).
