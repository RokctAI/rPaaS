# API Reference: brand

Source file: `paas/api/brand/brand.py`

## Whitelisted API Endpoints

### `def get_brands(limit_start=0, limit_page_length=10)`
Retrieves a list of brands.

### `def get_brand_by_uuid(uuid)`
Retrieves a single brand by its UUID.

### `def create_brand(brand_data)`
Creates a new brand.

### `def update_brand(uuid, brand_data)`
Updates an existing brand by its UUID.

### `def delete_brand(uuid)`
Deletes a brand by its UUID.
