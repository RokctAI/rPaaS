# API Reference: seller_order

Source file: `paas/api/seller_order/seller_order.py`

## Whitelisted API Endpoints

### `def get_seller_orders(limit_start=0, limit_page_length=20, status=None, from_date=None, to_date=None)`
Retrieves a list of orders for the current seller's shop, with optional filters.

### `def get_seller_order_details(order_id)`
Retrieves full details of a specific order.

### `def update_seller_order_status(order_id, status)`
Updates the status of an order.

### `def get_seller_order_refunds(limit_start=0, limit_page_length=20)`
Retrieves a list of order refunds for the current seller's shop.

### `def update_seller_order_refund(refund_name, status, answer=None)`
Updates the status and answer of an order refund.

### `def get_seller_reviews(limit_start=0, limit_page_length=20)`
Retrieves a list of reviews for products in the current seller's shop.
