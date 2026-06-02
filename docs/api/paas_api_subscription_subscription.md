# API Reference: subscription

Source file: `paas/api/subscription/subscription.py`

## Whitelisted API Endpoints

### `def create_subscription(data)`
Create a new subscription.

### `def get_subscription(name)`
Get a subscription by name.

### `def list_subscriptions()`
List all subscriptions.

### `def update_subscription(name, data)`
Update a subscription.

### `def delete_subscription(name)`
Delete a subscription.

### `def assign_subscription_to_shop(shop, subscription, expired_at)`
Assign a subscription to a shop.

### `def get_shop_subscriptions(shop)`
Get all subscriptions for a shop.

### `def update_shop_subscription(name, data)`
Update a shop subscription.

### `def cancel_shop_subscription(name)`
Cancel a shop's subscription.

### `def get_my_shop_subscription()`
Get the current seller's shop subscription.

### `def subscribe_my_shop(subscription_id)`
Subscribe the seller's shop to a new plan.

## Documented Module Functions

### `def get_seller_shop()`
Get the shop associated with the current seller.
