# API Reference: user

Source file: `paas/api/user/user.py`

## Whitelisted API Endpoints

### `def logout()`
Log out the current user.

### `def login(usr, pwd)`
<!-- baa1fbbf9520fd3a104059ab88a3749a1a57952aa1fe27343a11c1e9dc0e2d3b -->
The login function is used to authenticate a user and return an API key/secret as a Bearer token. It supports both email and phone number as the username. The function takes two parameters: usr, which is the username that can be either an email or a phone number, and pwd, which is the password for the given username. The function resolves phone numbers to their corresponding email addresses, authenticates the user, generates API keys if they do not exist, and returns a JSON response containing the access token and user details. If the authentication fails, it returns an error response with a 401 status code.

### `def get_profile()`
<!-- b9295f34da3d2d913e28c865cb4486a8cda099e5dcfb09fb0c78d91cc9fc1d70 -->
The get_profile function retrieves the current user's profile details. It does not accept any parameters. This function first checks if the user is logged in, throwing an AuthenticationError if they are not. It then fetches the user's details from the database and, if applicable, their associated shop details. The function returns a response containing the user's profile information, including their ID, email, name, phone number, role, and image, as well as their shop details and wallet balance.

### `def update_profile(firstname=None, lastname=None, email=None, phone=None, images=None)`
<!-- 784bf71b2c8c756fe79dd9b7f52fd13153ba189bd1ff62ff6336f06eb0c90f5f -->
The update_profile function updates the current user's profile information. It accepts several optional parameters: firstname, lastname, email, phone, and images, which correspond to the user's first name, last name, email address, phone number, and profile image, respectively. If any of these parameters are provided, the function will update the corresponding field in the user's profile. The function requires the user to be logged in and will throw an error if the user is a guest. The email parameter is currently not utilized in the function. The function returns the updated profile information.

### `def update_password(password, password_confirmation)`
<!-- 309606c10114d65ea385bb51a960f5dfb37b1db7a0c4db1611936ea5ffc66e39 -->
The update_password function is used to update the current user's password. It takes two parameters: password and password_confirmation. The password parameter is the new password to be set, while the password_confirmation parameter is used to verify that the new password was entered correctly. The function checks if the user is logged in and if the password and confirmation match, then updates the user's password and returns a success message.

### `def delete_account()`
<!-- 1567672da4f3bebbef3d2224b62f50d45f1d9e6a46d8e96a4a619c6378e6678d -->
The delete_account function is used to delete the currently logged-in user's account. If the account cannot be deleted due to linked documents, it will be deactivated instead. This function does not take any parameters, as it relies on the currently logged-in user's information. It first checks if the user is logged in, throwing an AuthenticationError if they are not. The function then attempts to delete the user's account, logging them out and returning a success message if successful. If deletion fails due to linked documents, it deactivates the account, logs the user out, and returns a message indicating that the account has been deactivated.

### `def check_phone(phone)`
<!-- 23bc27a28e6e4db0f221413f5fa3fb91c9182efe5a5150046b6db626d590e71f -->
The check_phone function checks if a given phone number is already registered to a user. It takes one parameter, phone, which is a string representing the phone number to be checked. The function returns an API response indicating whether the phone number is available or already exists, along with a status of success or error. If the phone parameter is empty, it throws an error as the phone number is a required parameter.

### `def send_phone_verification_code(phone)`
Generate and send a phone verification code (OTP).
This is used for both initial verification and resending.

### `def verify_phone_code(phone, otp)`
*No documentation provided (generation failed).*

### `def verify_email_code(email, otp)`
*No documentation provided (generation failed).*

### `def register_user(password, first_name, last_name, email=None, phone=None)`
*No documentation provided (generation failed).*

### `def forgot_password(user)`
*No documentation provided (generation failed).*

### `def forgot_password_confirm(email, verify_code, password=None)`
*No documentation provided (generation failed).*

### `def login_with_google(email, display_name, id, avatar=None)`
*No documentation provided (generation failed).*

### `def search_user(name, page=1, limit=20, lang='en')`
Search for users by name, email, or phone.

### `def send_wallet_balance(amount, name_or_number, message=None, lang='en')`
*No documentation provided (generation failed).*

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
<!-- edccbd9a9dacda2f83e5251fe29cab40b6c116fc747bfd38f6a5bf889e8f3e53 -->
The get_user_profile function retrieves the profile information for the currently logged-in user. It does not require any parameters to be passed. The function returns a dictionary containing the user's first name, last name, email, phone number, birth date, location, gender, and ringfenced balance. If the user is not logged in, it raises an AuthenticationError with a message prompting the user to log in.

### `def update_user_profile(profile_data)`
*No documentation provided (generation failed).*

### `def get_user_order_refunds(page=1)`
*No documentation provided (generation failed).*

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
