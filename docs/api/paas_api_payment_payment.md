# API Reference: payment

Source file: `paas/api/payment/payment.py`

## Whitelisted API Endpoints

### `def get_payment_gateways()`
Retrieves a list of active payment gateways, formatted for frontend compatibility.

### `def get_payment_gateway(id)`
Retrieves a single active payment gateway.

### `def initiate_flutterwave_payment(order_id)`
Auto-generated docstring for compliance.

### `def flutterwave_callback()`
Handles the callback from Flutterwave after a payment attempt.

### `def get_payfast_settings()`
Returns the PayFast settings.

### `def handle_payfast_callback()`
Handles the PayFast payment callback.

### `def process_payfast_token_payment(order_id, token)`
Processes a payment using a saved PayFast token.

### `def save_payfast_card(token, card_details)`
Saves a PayFast card token.

### `def get_saved_payfast_cards()`
Retrieves a list of saved cards for the current user.

### `def delete_payfast_card(card_name)`
Deletes a saved card.

### `def handle_paypal_callback()`
Handles the PayPal payment callback.

### `def initiate_paypal_payment(order_id)`
Auto-generated docstring for compliance.

### `def initiate_paystack_payment(order_id)`
Auto-generated docstring for compliance.

### `def handle_paystack_callback()`
Handles the PayStack payment callback.

### `def log_payment_payload(payload)`
Logs a payment payload.

### `def handle_stripe_webhook()`
Handles the Stripe payment webhook.

### `def get_saved_cards()`
Auto-generated docstring for compliance.

### `def tokenize_card(card_number, card_holder, expiry_date, cvc)`
Auto-generated docstring for compliance.

### `def delete_card(card_name)`
Auto-generated docstring for compliance.

### `def process_direct_card_payment(order_id, card_number, card_holder, expiry_date, cvc, save_card=False)`
Auto-generated docstring for compliance.

### `def process_token_payment(order_id, token)`
Auto-generated docstring for compliance.

### `def tip_process(order_id, tip_amount)`
Processes a tip for an order.

### `def process_wallet_top_up(amount, token=None)`
Auto-generated docstring for compliance.

### `def process_wallet_payment(order_id)`
Auto-generated docstring for compliance.
