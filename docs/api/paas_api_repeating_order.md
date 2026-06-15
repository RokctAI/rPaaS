# API Reference: repeating_order

Source file: `paas/api/repeating_order.py`

## Whitelisted API Endpoints

### `def create_repeating_order(original_order, start_date, cron_pattern, end_date=None, payment_method='Wallet', saved_card=None, lang='en')`
<!-- d750fa8f5a178590ce1d095149f6e821b214dee70d9acac86494d282f6cccf3a -->
The create_repeating_order function creates a new repeating order based on an existing order, with specified payment preferences and ringfencing. It takes several parameters: original_order, the identifier of the original order; start_date, the date when the repeating order starts; cron_pattern, a cron expression defining the repetition schedule; end_date, an optional date when the repeating order ends; payment_method, the payment method to use, defaulting to 'Wallet'; saved_card, an optional saved card identifier; and lang, the language, defaulting to 'en'. The function enforces the use of the 'Wallet' payment method for auto-orders and handles ringfencing of the order amount in the user's wallet balance. It returns the newly created repeating order as a dictionary.

### `def pause_repeating_order(repeating_order_id, lang='en')`
<!-- b67bc6660922711a8516ecff1d84aeb6474382208049c8bc17739970e2e68a8e -->
pause_repeating_order pauses a specific repeating order and, if applicable, releases any funds that were ring‑fenced for that order back to the user’s wallet.  

Parameters  
- repeating_order_id (str): The unique identifier of the Repeating Order document to be paused.  
- lang (str, optional): Language code for any localized messages; defaults to 'en'.  

The function checks that the order is active, uses the wallet payment method, and has a positive ring‑fenced amount. When those conditions are met it transfers the ring‑fenced amount from the user’s ring‑fenced balance to their wallet balance, records a “Wallet Release” transaction, clears the ring‑fenced amount, deactivates the order, and returns a success response indicating the order has been paused and funds released.

### `def resume_repeating_order(repeating_order_id, lang='en')`
<!-- 535fc0ee416dea382f10e80a32afe86a768ef248d9770ef8ce23657f66d9426a -->
The resume_repeating_order function resumes a previously paused repeating order and re-ringfences the necessary funds. It takes two parameters: repeating_order_id, which is the unique identifier of the repeating order to be resumed, and lang, which specifies the language to be used and defaults to English if not provided. The function checks if the order has expired, and if the payment method is Wallet, it recalculates the ringfence amount based on the remaining schedule and updates the user's wallet balance accordingly. If the user's balance is insufficient, it throws an error. Otherwise, it resumes the order, saves the changes, and returns a success message.

### `def delete_repeating_order(repeating_order_id, lang='en')`
<!-- 6b62c27ec008c39c6d61f629c6ed88db717cad5e18963db5c3349437ebd721c1 -->
The delete_repeating_order function is used to delete a repeating order and release any remaining ringfenced funds associated with it. It takes two parameters: repeating_order_id, which is a string representing the ID of the repeating order to be deleted, and lang, which is an optional string parameter that specifies the language, defaulting to 'en' if not provided. The function retrieves the repeating order document, checks if there are any ringfenced funds, and if so, updates the user's wallet balance and ringfenced balance accordingly before deleting the repeating order document.
