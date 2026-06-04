# API Reference: seller_product

Source file: `paas/api/seller_product/seller_product.py`

## Whitelisted API Endpoints

### `def get_seller_products(limit_start=0, limit_page_length=20)`
Retrieves a list of products for the current seller's shop.

### `def create_seller_product(product_data)`
Creates a new product for the current seller's shop.

### `def update_seller_product(product_name, product_data)`
Updates a product for the current seller's shop.

### `def delete_seller_product(product_name)`
Deletes a product for the current seller's shop.

### `def get_seller_categories(limit_start=0, limit_page_length=20)`
Retrieves a list of categories for the current seller's shop.

### `def create_seller_category(category_data)`
Creates a new category for the current seller's shop.

### `def update_seller_category(uuid, category_data)`
Updates a category for the current seller's shop.

### `def delete_seller_category(uuid)`
Deletes a category for the current seller's shop.

### `def get_seller_brands(limit_start=0, limit_page_length=20)`
Retrieves a list of brands for the current seller's shop.

### `def create_seller_brand(brand_data)`
Creates a new brand for the current seller's shop.

### `def update_seller_brand(uuid, brand_data)`
Updates a brand for the current seller's shop.

### `def delete_seller_brand(uuid)`
Deletes a brand for the current seller's shop.

### `def get_seller_extra_groups(limit_start=0, limit_page_length=20)`
Retrieves a list of product extra groups for the current seller's shop.

### `def create_seller_extra_group(group_data)`
Creates a new product extra group for the current seller's shop.

### `def update_seller_extra_group(group_name, group_data)`
Updates a product extra group for the current seller's shop.

### `def delete_seller_extra_group(group_name)`
Deletes a product extra group for the current seller's shop.

### `def get_seller_extra_values(group_name, limit_start=0, limit_page_length=20)`
Retrieves a list of product extra values for a given group.

### `def create_seller_extra_value(value_data)`
Creates a new product extra value.

### `def update_seller_extra_value(value_name, value_data)`
Updates a product extra value.

### `def delete_seller_extra_value(value_name)`
Deletes a product extra value.

### `def get_seller_units(limit_start=0, limit_page_length=20)`
Retrieves a list of units for the current seller's shop.

### `def create_seller_unit(unit_data)`
Creates a new unit for the current seller's shop.

### `def update_seller_unit(unit_name, unit_data)`
Updates a unit for the current seller's shop.

### `def delete_seller_unit(unit_name)`
Deletes a unit for the current seller's shop.

### `def get_seller_tags(limit_start=0, limit_page_length=20)`
Retrieves a list of tags for the current seller's shop.

### `def create_seller_tag(tag_data)`
Creates a new tag for the current seller's shop.

### `def update_seller_tag(tag_name, tag_data)`
Updates a tag for the current seller's shop.

### `def delete_seller_tag(tag_name)`
Deletes a tag for the current seller's shop.
