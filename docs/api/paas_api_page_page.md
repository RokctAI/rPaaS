# API Reference: page

Source file: `paas/api/page/page.py`

## Whitelisted API Endpoints

### `def get_page(route)`
Retrieves a single web page by its route.

### `def get_admin_pages(limit_start=0, limit_page_length=20)`
Retrieves a list of all web pages on the platform (for admins).

### `def get_admin_web_page(route)`
Retrieves a web page for admin management.

### `def update_admin_web_page(route, page_data)`
Updates a web page (for admins).

## Documented Module Functions

### `def _require_admin()`
Helper function to ensure the user has the System Manager role.
