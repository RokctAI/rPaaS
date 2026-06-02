# API Reference: auth

Source file: `paas/api/auth/auth.py`

## Documented Module Functions

### `def validate(request=None)`
Custom authentication hook to support 'Bearer <api_key>:<api_secret>'
which is used by the legacy Flutter app.
Standard Frappe expects 'token <api_key>:<api_secret>'.
