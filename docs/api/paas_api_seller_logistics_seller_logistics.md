# API Reference: seller_logistics

Source file: `paas/api/seller_logistics/seller_logistics.py`

## Whitelisted API Endpoints

### `def get_seller_delivery_man_delivery_zones(limit_start=0, limit_page_length=20)`
Retrieves a list of delivery zones for the deliverymen of the current seller's shop.

### `def adjust_seller_inventory(item_code, warehouse, new_qty)`
Adjusts the inventory for a specific item in a warehouse for the current seller's shop.
