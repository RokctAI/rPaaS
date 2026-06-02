# API Reference: utils

Source file: `paas/whatsapp/utils.py`

## Whitelisted API Endpoints

### `def get_admin_whatsapp_config()`
Returns the config for the Admin Settings page (even if disabled).

### `def save_whatsapp_config(enabled=0, phone_number_id=None, access_token=None, app_secret=None, verify_token=None)`
Updates the WhatsApp Tenant Config.

## Documented Module Functions

### `def get_whatsapp_config()`
Fetches the WhatsApp Tenant Configuration.
Assumes Single Tenant Config per Site.

### `def validate_signature(payload, signature, app_secret)`
Validates the X-Hub-Signature-256 header using the App Secret.
