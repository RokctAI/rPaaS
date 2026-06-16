# API Reference: tasks

Source file: `paas/tasks.py`

## Whitelisted API Endpoints

### `def remove_expired_stories()`
Find and delete stories that have expired.
This is run daily by the scheduler on tenant sites.

### `def process_repeating_orders()`
The process_repeating_orders function is designed to process repeating orders that are due for execution. It fetches active repeating orders where the next execution is due or not set, and then attempts to create a new order based on the original order associated with the repeating order. The function processes payment for the new order using either the user's wallet or a saved card, and updates the order status accordingly. If payment fails, the function notifies the user. The function also calculates the next execution date for the repeating order and updates the repeating order's last execution and next execution dates. Additionally, the function cleans up any expired repeating orders by setting their status to inactive. The function does not take any parameters.
