# API Reference: seller_operations

Source file: `paas/api/seller_operations/seller_operations.py`

## Whitelisted API Endpoints

### `def get_seller_kitchens(limit_start=0, limit_page_length=20)`
Retrieves a list of kitchens for the current seller's shop.

### `def create_seller_kitchen(kitchen_data)`
Creates a new kitchen for the current seller's shop.

### `def update_seller_kitchen(kitchen_name, kitchen_data)`
Updates a kitchen for the current seller's shop.

### `def delete_seller_kitchen(kitchen_name)`
Deletes a kitchen for the current seller's shop.

### `def get_seller_inventory_items(limit_start=0, limit_page_length=20, item_code=None)`
Retrieves inventory items (Bin entries) for the current seller's shop.
Can be filtered by a specific item.

### `def adjust_seller_inventory(item_code, warehouse, new_qty)`
Adjusts the inventory for a specific item in a warehouse for the current seller's shop.

### `def get_seller_menus(limit_start=0, limit_page_length=20)`
Retrieves a list of menus for the current seller's shop.

### `def get_seller_menu(menu_name)`
Retrieves a single menu with its items for the current seller's shop.

### `def create_seller_menu(menu_data)`
Creates a new menu for the current seller's shop.

### `def update_seller_menu(menu_name, menu_data)`
Updates a menu for the current seller's shop.

### `def delete_seller_menu(menu_name)`
Deletes a menu for the current seller's shop.

### `def get_seller_receipts(limit_start=0, limit_page_length=20)`
Retrieves a list of receipts for the current seller's shop.

### `def create_seller_receipt(receipt_data)`
Creates a new receipt for the current seller's shop.

### `def update_seller_receipt(receipt_name, receipt_data)`
Updates a receipt for the current seller's shop.

### `def delete_seller_receipt(receipt_name)`
Deletes a receipt for the current seller's shop.

### `def get_seller_combos(limit_start=0, limit_page_length=20)`
Retrieves a list of combos for the current seller's shop.

### `def get_seller_combo(combo_name)`
Retrieves a single combo with its items for the current seller's shop.

### `def create_seller_combo(combo_data)`
Creates a new combo for the current seller's shop.

### `def update_seller_combo(combo_name, combo_data)`
Updates a combo for the current seller's shop.

### `def delete_seller_combo(combo_name)`
Deletes a combo for the current seller's shop.

### `def get_seller_sections(limit_start=0, limit_page_length=20)`
*No documentation provided.*

### `def create_seller_section(section_data=None)`
*No documentation provided.*

### `def get_seller_tables(limit_start=0, limit_page_length=20)`
*No documentation provided.*

### `def delete_seller_tables(table_id=None)`
*No documentation provided.*

### `def get_table_disable_dates()`
*No documentation provided.*

### `def get_booking_working_days()`
*No documentation provided.*

### `def create_seller_booking(booking_data=None)`
*No documentation provided.*

### `def update_booking_status(booking_id=None, status=None)`
*No documentation provided.*
