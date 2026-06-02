# API Reference: payment

Source file: `paas/api/payment/payment.py`

## Whitelisted API Endpoints

### `def get_payment_gateways()`
Retrieves a list of active payment gateways, formatted for frontend compatibility.

### `def get_payment_gateway(id)`
Retrieves a single active payment gateway.

### `def initiate_flutterwave_payment(order_id)`
*No documentation provided.*

### `def initiate_flutterwave_parcel_payment(order_id)`
*No documentation provided.*

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
*No documentation provided.*

### `def initiate_paypal_parcel_payment(order_id)`
*No documentation provided.*

### `def initiate_paystack_payment(order_id)`
*No documentation provided.*

### `def initiate_paystack_parcel_payment(order_id)`
*No documentation provided.*

### `def handle_paystack_callback()`
Handles the PayStack payment callback.

### `def log_payment_payload(payload)`
Logs a payment payload.

### `def handle_stripe_webhook()`
Handles the Stripe payment webhook.

### `def get_saved_cards()`
*No documentation provided.*

### `def tokenize_card(card_number, card_holder, expiry_date, cvc)`
*No documentation provided.*

### `def delete_card(card_name)`
*No documentation provided.*

### `def process_direct_card_payment(order_id, card_number, card_holder, expiry_date, cvc, save_card=False)`
*No documentation provided.*

### `def process_token_payment(order_id, token)`
*No documentation provided.*

### `def tip_process(order_id, tip_amount)`
Processes a tip for an order.

### `def process_wallet_top_up(amount, token=None)`
*No documentation provided.*

### `def process_wallet_payment(order_id)`
*No documentation provided.*

## Documented Module Functions

### `def _initiate_paypal_logic(doctype, docname)`
Internal logic for PayPal initiation across different doctypes.

### `def _initiate_paystack_logic(doctype, docname)`
Internal logic for PayStack initiation across different doctypes.

### `def _charge_card_token(token, amount, currency, description, user)`
Internal helper to charge a saved card token via the appropriate gateway.

### `def _charge_payfast_token(token, amount, currency, description)`
Executes a tokenized charge via PayFast (Ad Hoc Subscription pattern).
Uses the v1 subscriptions charge API with proper signature generation.
