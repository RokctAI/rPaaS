# API Reference: career

Source file: `paas/api/career/career.py`

## Whitelisted API Endpoints

### `def get_careers(limit_start=0, limit_page_length=20)`
Retrieves a list of active careers, formatted for frontend compatibility.

### `def get_career(id)`
Retrieves a single career by its ID (name).

### `def get_admin_careers(limit_start=0, limit_page_length=20)`
Retrieves a list of all careers on the platform (for admins).

## Documented Module Functions

### `def _require_admin()`
Helper function to ensure the user has the System Manager role.
