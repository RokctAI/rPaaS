# API Reference: cart

Source file: `paas/api/cart/cart.py`

## Whitelisted API Endpoints

### `def get_cart(shop_id)`
Retrieves the active cart for the current user and a given shop.

### `def add_to_cart(qty, shop_id, item_code=None, stock_id=None, addons=None, alternative_product=None)`
Adds an item to the user's cart. Support multi-cart by shop_id.
accepts item_code (ProductId) or stock_id (Variant).
addons: JSON string of addons list.

### `def remove_from_cart(cart_detail_name)`
Removes an item from the cart.
`cart_detail_name` is the name of the Cart Detail row.

### `def remove_product_cart(cart_detail_id)`
Alias for remove_from_cart, used by Flutter app.

### `def create_cart(cart, lang='en')`
Creates a new cart.

### `def insert_cart(cart, lang='en')`
Inserts items into an existing cart.

### `def insert_cart_with_group(cart, lang='en')`
Inserts items into an existing group cart.

### `def create_and_cart(cart, lang='en')`
Creates a new cart and adds items to it.

### `def get_cart_in_group(cart_id, shop_id, cart_uuid, lang='en')`
Retrieves a group cart.

### `def delete_cart(cart_id, lang='en')`
Deletes a cart.

### `def change_status(user_uuid, cart_id, lang='en')`
Changes the status of a user in a group cart.

### `def delete_user(cart_id, user_id, lang='en')`
Deletes a user from a group cart.

### `def join_order(cart_id, user_name, lang='en')`
Allows a user to join a group order.

## Documented Module Functions

### `def calculate_cart_totals(cart_name)`
Helper function to recalculate the total price of a cart.
