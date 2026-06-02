# API Reference: cook

Source file: `paas/api/cook/cook.py`

## Whitelisted API Endpoints

### `def get_cook_orders(limit_start=0, limit_page_length=20)`
Retrieves a list of orders assigned to the current cook.

### `def get_cook_order_report(from_date, to_date)`
Retrieves a report of orders for the current cook within a date range.
