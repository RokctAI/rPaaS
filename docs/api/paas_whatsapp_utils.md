# API Reference: utils

Source file: `paas/whatsapp/utils.py`

## Documented Module Functions

### `def get_whatsapp_config()`
Fetches the WhatsApp Tenant Configuration.
Assumes Single Tenant Config per Site.

### `def validate_signature(payload, signature, app_secret)`
Validates the X-Hub-Signature-256 header using the App Secret.
