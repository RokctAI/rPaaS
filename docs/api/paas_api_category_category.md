# API Reference: category

Source file: `paas/api/category/category.py`

## Whitelisted API Endpoints

### `def get_categories(limit_start=0, limit_page_length=10, order_by='name', order='desc', parent=False, select=False, **kwargs)`
Retrieves a list of categories with pagination and filters.

### `def get_category_types()`
Returns a list of all available category types.

### `def get_children_categories(id, limit_start=0, limit_page_length=10)`
Retrieves the children of a given category.

### `def search_categories(search, limit_start=0, limit_page_length=10)`
Searches for categories by a search term.

### `def get_category_by_uuid(uuid)`
Retrieves a single category by its UUID.

### `def create_category(category_data)`
Creates a new category.

### `def update_category(uuid, category_data)`
Updates an existing category by its UUID.

### `def delete_category(uuid)`
Deletes a category by its UUID.
