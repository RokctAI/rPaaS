# API Reference: payment

Source file: `paas/api/payment/payment.py`

## Whitelisted API Endpoints

### `def get_payment_gateways()`
Retrieves a list of active payment gateways, formatted for frontend compatibility.

### `def get_payment_gateway(id)`
Retrieves a single active payment gateway.

### `def initiate_flutterwave_payment(order_id)`
The initiate_flutterwave_payment function initiates a payment transaction through Flutterwave for a specified order. It takes one parameter, order_id, which is a string representing the unique identifier of the order for which the payment is being initiated. This function serves as a wrapper around the core payment logic, providing a simplified interface for triggering payments.

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
The initiate_paypal_payment function initiates a PayPal payment for a specific order. It takes one parameter, order_id, which is a string representing the unique identifier of the order for which the payment is being initiated. This function serves as a wrapper around the core PayPal payment logic, providing a simple and straightforward way to start the payment process for a given order.

### `def initiate_paystack_payment(order_id)`
The initiate_paystack_payment function initiates a payment process through Paystack for a specific order. It takes one parameter, order_id, which is a string representing the unique identifier of the order for which the payment is being initiated. This function serves as a gateway to trigger the underlying payment logic, passing the order type as "Order" and the provided order_id to the _initiate_paystack_logic function for further processing.

### `def handle_paystack_callback()`
Handles the PayStack payment callback.

### `def log_payment_payload(payload)`
Logs a payment payload.

### `def handle_stripe_webhook()`
Handles the Stripe payment webhook.

### `def get_saved_cards()`
The get_saved_cards function retrieves a list of saved credit cards associated with the currently logged-in user. It first checks if the user is logged in, throwing an error if they are a guest. If the user is authenticated, it queries the system for a list of saved cards linked to the user's account, returning a list of card objects containing details such as the card name, payment gateway, token, last four digits, card type, expiry date, and card holder's name.

### `def tokenize_card(card_number, card_holder, expiry_date, cvc)`
The tokenize_card function is used to securely store a user's credit card information. It takes four parameters: card_number, card_holder, expiry_date, and cvc, which represent the credit card number, card holder's name, expiration date, and card verification code, respectively. The function generates a unique token for the saved card and returns a dictionary containing the token, saved card name, last four digits of the card number, card type, and expiration date. The function requires the user to be logged in and automatically detects the card type based on the card number.

### `def delete_card(card_name)`
The delete_card function is used to remove a saved card from the system. It takes one parameter, card_name, which specifies the name of the card to be deleted. The function first checks if the current user is logged in, throwing an error if they are a guest. It then verifies that the user attempting to delete the card is the same user who saved it, throwing a permission error if they are not authorized. If both checks pass, the function deletes the specified card and returns a success status.

### `def process_direct_card_payment(order_id, card_number, card_holder, expiry_date, cvc, save_card=False)`
The process_direct_card_payment function facilitates direct card payments for a specific order. It takes in several parameters: order_id, which identifies the order being paid for, card_number, card_holder, expiry_date, and cvc, which are the card details used for payment. The save_card parameter is optional and defaults to False, indicating whether the card should be saved for future transactions. The function first verifies the user's login status and order ownership, then creates a new transaction record, updates the order status to Paid, and optionally tokenizes the card for future use. It returns a dictionary containing the status of the payment and the transaction ID.

### `def process_token_payment(order_id, token)`
The process_token_payment function facilitates payment processing for a specific order using a provided token. It takes two parameters: order_id, which identifies the order being paid for, and token, which represents the payment method. The function first verifies that the user is logged in and has permission to pay for the specified order. It then initiates a payment charge using the provided token and updates the order status to "Paid" if the payment is successful. The function returns the result of the payment processing operation.

### `def tip_process(order_id, tip_amount)`
Processes a tip for an order.

### `def process_wallet_top_up(amount, token=None)`
The process_wallet_top_up function is used to top up a user's wallet with a specified amount. It takes two parameters: amount, which is the amount to be added to the wallet, and token, which is the payment token used for the transaction. The token parameter is optional but required to complete the top-up process. If the token is not provided, the function will throw an error. The function first checks if the user is logged in and then executes the charge via a payment gateway. After a successful charge, it creates a new transaction record and updates the user's wallet balance. The function returns a dictionary with a status of 'success' and the transaction ID.

### `def process_wallet_payment(order_id)`
The process_wallet_payment function is used to deduct payment from a user's wallet for a specific order. It takes one parameter, order_id, which is the unique identifier of the order being paid for. The function first checks if the user is logged in and has permission to pay for the order, then verifies if the user's wallet balance is sufficient to cover the order's grand total. If the balance is sufficient, it deducts the payment amount from the user's wallet, creates a new transaction record, and updates the order's payment status to "Paid".
