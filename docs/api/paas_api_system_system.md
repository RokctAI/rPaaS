# API Reference: system

Source file: `paas/api/system/system.py`

## Whitelisted API Endpoints

### `def get_weather(location)`
Proxy endpoint to get weather data from the control site, with tenant-side caching.
This follows the same authentication pattern as other tenant-to-control-panel APIs.

### `def api_status()`
Returns a simple status of the API.

### `def get_languages()`
Returns a list of all enabled languages.

### `def get_currencies()`
Returns a list of all enabled currencies.

### `def trigger_system_update()`
Triggers a system update. For tenant sites, this only runs a migration.

### `def get_global_settings()`
Retrieves global settings formatted as a key-value list for the frontend.
Aggregates data from 'Settings' and 'Global Settings'.

### `def get_policy(lang='en')`
Returns the privacy policy.

### `def get_terms(lang='en')`
Returns the terms and conditions.
