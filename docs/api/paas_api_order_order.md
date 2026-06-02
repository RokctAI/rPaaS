# API Reference: order

Source file: `paas/api/order/order.py`

## Whitelisted API Endpoints

### `def create_order(order_data)`
Creates a new order.

### `def list_orders(limit_start=0, limit_page_length=20)`
Retrieves a list of orders for the current user.

### `def get_order_details(order_id)`
Retrieves the details of a specific order.

### `def update_order_status(order_id, status)`
Updates the status of a specific order.

### `def add_order_review(order_id, rating, comment=None)`
Adds a review for a specific order.

### `def cancel_order(order_id)`
Cancels a specific order.

### `def get_order_statuses()`
Retrieves a list of active order statuses, formatted for frontend compatibility.

### `def get_calculate(cart_id, address=None, coupon_code=None, tips=0, delivery_type='Delivery')`
*No documentation provided.*

## Documented Module Functions

### `def deposit_to_wallet(user, amount, note)`
Helper to add balance to user's wallet and log the transaction.
