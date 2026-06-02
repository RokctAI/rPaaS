# API Reference: verification_utils

Source file: `paas/verification_utils.py`

## Documented Module Functions

### `def generate_verification_code(order_id, amount, shop_id)`
Generates a 5-digit verification code using SHA-256 and a shared secret.
This logic MUST match the Flutter PayVerificationHelper implementation.
