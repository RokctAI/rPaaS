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
The get_calculate function calculates the total cost of a shopping cart, taking into account various factors such as product prices, taxes, discounts, delivery fees, and service fees. 

It accepts the following parameters: 
- cart_id: the unique identifier of the shopping cart
- address: the delivery address, which can be a string or a dictionary containing latitude and longitude coordinates
- coupon_code: a discount coupon code to apply to the order
- tips: the amount of tips to add to the order, defaulting to 0
- delivery_type: the type of delivery, defaulting to 'Delivery'

The function returns a dictionary containing the calculated totals, including the total tax, product price, shop tax, total price, discount, delivery fee, service fee, tips, and coupon price. 

This function is used to provide an accurate estimate of the total cost of an order, considering various factors that may affect the final price.
