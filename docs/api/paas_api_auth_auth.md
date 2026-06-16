# API Reference: auth

Source file: `paas/api/auth/auth.py`

## Documented Module Functions

### `def validate(request=None)`
Custom authentication hook to support 'Bearer <api_key>:<api_secret>'
with token expiry check.
