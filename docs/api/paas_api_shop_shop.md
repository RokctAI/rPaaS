# API Reference: shop

Source file: `paas/api/shop/shop.py`

## Whitelisted API Endpoints

### `def create_shop(shop_data)`
Creates a new Shop document.
Only users with 'System Manager' or 'Seller' roles can create a shop.

### `def get_shops(limit_start=0, limit_page_length=20, order_by='name', order='desc', latitude=None, longitude=None, **kwargs)`
Retrieves a list of shops with pagination and filters. Supports geo-sorting.

### `def get_shop_details(uuid)`
Retrieves a single shop by its UUID.

### `def search_shops(search, category_id=None, limit_start=0, limit_page_length=20)`
Searches for shops by name, optionally filtered by category.

### `def get_shop_types()`
Retrieves all available Shop Types.

### `def get_nearby_shops(latitude, longitude, radius_km=10, lang='en')`
Retrieves a list of shops within a given radius.
bypass_sql

### `def get_shops_recommend(latitude, longitude, lang='en')`
Returns recommended shops based on location and rating.
Currently aliases to get_nearby_shops as we lack a rating field.

### `def check_driver_zone(shop_id=None, address=None)`
Checks if the address is within the shop's delivery zone.
Expects address as dict/json with latitude/longitude.
bypass_sql

### `def get_shops_by_ids(shop_ids=None, **kwargs)`
Retrieves shops by a list of IDs.

### `def check_cashback(shop_id, amount, lang='en')`
Checks the cashback for a given shop and amount based on defined rules.

### `def get_nearest_delivery_points(latitude, longitude, radius_km=50)`
Retrieves a list of active Delivery Points within a given radius.
bypass_sql
