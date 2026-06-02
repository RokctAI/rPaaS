# API Reference: product

Source file: `paas/api/product/product.py`

## Whitelisted API Endpoints

### `def get_products(limit_start=0, limit_page_length=20, category_id=None, brand_id=None, shop_id=None, order_by=None, rating=None, search=None)`
Retrieves a list of products (Items) with pagination, advanced filters, and sorting.

### `def most_sold_products(limit_start=0, limit_page_length=20)`
Retrieves a list of most sold products.

### `def get_discounted_products(limit_start=0, limit_page_length=20)`
Retrieves a list of products with active discounts.

### `def get_products_by_ids(ids, **kwargs)`
Retrieves a list of products by their IDs.

### `def get_product_by_uuid(uuid)`
Retrieves a single product by its UUID.

### `def get_product_by_slug(slug)`
Retrieves a single product by its slug.

### `def read_product_file(uuid)`
Reads a product file.

### `def get_product_reviews(uuid, limit_start=0, limit_page_length=20)`
Retrieves reviews for a specific product by its UUID.

### `def order_products_calculate(products)`
Calculates the total price of a list of products.

### `def get_products_by_brand(brand_id, limit_start=0, limit_page_length=20)`
Retrieves a list of products for a given brand.

### `def products_search(search, limit_start=0, limit_page_length=20)`
Searches for products by a search term.

### `def get_products_by_category(uuid, limit_start=0, limit_page_length=20)`
Retrieves a list of products for a given category.

### `def get_products_by_shop(shop_id, limit_start=0, limit_page_length=20)`
Retrieves a list of products for a given shop.

### `def add_product_review(uuid, rating, comment=None)`
Adds a review for a product by its UUID, but only if the user has purchased it.

### `def get_product_history(limit_start=0, limit_page_length=20)`
Retrieves the viewing history for the current user, specific to products (Items).

### `def get_product_by_uuid(uuid)`
Retrieves a single product by UUID.

### `def calculate_product_price(products)`
Calculates prices for products.
Expects 'products' as a list of dicts: [{'id': ..., 'quantity': ...}] or JSON string.

### `def add_product_review(product_uuid, rating, comment=None, images=None)`
Adds a review for a product by its UUID, verifying ownership if enabled.

### `def get_suggest_price(item_code=None, lang='en', currency='ZAR')`
Retrieves a suggested price range based on similar items in the same category.

### `def get_product_calculations(item_code, quantity, lang='en')`
Calculates the price for a single product.
