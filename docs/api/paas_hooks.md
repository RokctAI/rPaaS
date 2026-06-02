# API Reference: hooks

Source file: `paas/hooks.py`

## Documented Module Functions

### `def get_safe_scheduler_events()`
Safely get scheduler events by checking if frappe.conf exists.
This prevents crashes during installation where frappe.conf is not yet available.
