# API Reference: checkout

Source file: `paas/whatsapp/api/checkout.py`

## Documented Module Functions

### `def handle_checkout_action(session, action, payload=None)`
Router for checkout actions.

### `def save_checkout_data(session, data)`
Helper to update checkout_data JSON.

### `def start_checkout(session)`
Step 1: Ask for Delivery Address

### `def select_payment_method(session)`
Step 2: Select Payment Method

### `def handle_payment_selection(session, payload)`
Store payment choice and ask for confirmation.

### `def confirm_order_summary(session)`
Step 3: Final Confirmation
