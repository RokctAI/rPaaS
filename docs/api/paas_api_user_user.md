# API Reference: user

Source file: `paas/api/user/user.py`

## Whitelisted API Endpoints

### `def logout()`
Log out the current user.

### `def login(usr, pwd)`
*No documentation provided.*

### `def get_profile()`
*No documentation provided.*

### `def update_profile(firstname=None, lastname=None, email=None, phone=None, images=None)`
*No documentation provided.*

### `def update_password(password, password_confirmation)`
*No documentation provided.*

### `def delete_account()`
*No documentation provided.*

### `def check_phone(phone)`
*No documentation provided.*

### `def send_phone_verification_code(phone)`
Generate and send a phone verification code (OTP).
This is used for both initial verification and resending.

### `def verify_phone_code(phone, otp)`
*No documentation provided.*

### `def verify_email_code(email, otp)`
*No documentation provided.*

### `def register_user(password, first_name, last_name, email=None, phone=None)`
*No documentation provided.*

### `def forgot_password(user)`
*No documentation provided.*

### `def forgot_password_confirm(email, verify_code, password=None)`
*No documentation provided.*

### `def login_with_google(email, display_name, id, avatar=None)`
*No documentation provided.*

### `def search_user(name, page=1, limit=20, lang='en')`
Search for users by name, email, or phone.

### `def send_wallet_balance(amount, name_or_number, message=None, lang='en')`
*No documentation provided.*

### `def update_profile_image(image)`
Updates the user's profile image.
Alias/Wrapper for update_profile logic specific to image.

### `def get_user_order_refunds(page=1, lang='en')`
Retrieves a list of order refunds for the current user.

### `def get_user_membership()`
Retrieves the active membership for the currently logged-in user.

### `def get_user_membership_history()`
Retrieves the membership history for the currently logged-in user.

### `def get_user_parcel_orders()`
Retrieves the parcel order history for the currently logged-in user.

### `def get_user_parcel_order(name)`
Retrieves a single parcel order for the currently logged-in user.

### `def get_user_addresses()`
Retrieves the list of addresses for the currently logged-in user.

### `def get_user_address(name)`
Retrieves a single address for the currently logged-in user.

### `def add_user_address(address_data)`
Adds a new address for the currently logged-in user.

### `def update_user_address(name, address_data)`
Updates an existing address for the currently logged-in user.

### `def delete_user_address(name)`
Deletes an address for the currently logged-in user.

### `def get_user_invites()`
Retrieves the list of invites for the currently logged-in user.

### `def create_invite(shop, user, role)`
Creates a new invite.

### `def update_invite_status(name, status)`
Updates the status of an invite.

### `def get_user_wallet()`
Retrieves the wallet for the currently logged-in user.

### `def get_wallet_history(start=0, limit=20)`
Retrieves the wallet history for the currently logged-in user.

### `def export_orders()`
Exports all orders for the current user to a CSV file.

### `def register_device_token(device_token, provider)`
Registers a new device token for the current user.

### `def get_user_transactions(start=0, limit=20)`
Retrieve the list of transactions for the currently logged-in user.

### `def get_user_shop()`
Retrieves the shop owned by the currently logged-in user.

### `def update_seller_shop(shop_data)`
Updates the shop owned by the currently logged-in seller.

### `def update_user_shop(shop_data)`
Alias for update_seller_shop (for backward compatibility/testing)

### `def get_user_request_models(start=0, limit=20)`
Retrieves the list of request models for the currently logged-in user.

### `def create_request_model(model_type, model_id, data)`
Creates a new request model.

### `def get_user_tickets(limit_start=0, limit_page_length=20)`
Retrieves the list of tickets for the currently logged-in user.

### `def get_user_ticket(name)`
Retrieves a single ticket and its replies for the currently logged-in user.

### `def create_ticket(subject, content, order_id=None)`
Creates a new ticket.

### `def reply_to_ticket(name, content)`
Adds a reply to an existing ticket.

### `def get_user_profile()`
*No documentation provided.*

### `def update_user_profile(profile_data)`
*No documentation provided.*

### `def get_user_order_refunds(page=1)`
*No documentation provided.*

### `def create_order_refund(order, cause)`
Creates a new order refund request.

### `def get_user_notifications(start=0, limit=20)`
Retrieves the list of notifications for the currently logged-in user.

### `def get_notification_count()`
Retrieves the count of unread notifications for the currently logged-in user.

### `def mark_notification_logs_as_read(ids=None)`
Marks specific notification logs as read.

### `def read_all_notifications()`
Marks all notifications as read for the current user.

### `def read_one_notification(name)`
Marks a single notification as read.
