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
<!-- e5ca9c881c07e6962fb8c0407260956406cfab71b991c407bc7c400a940230d2 -->
verify_phone_code(phone: str, otp: str) validates the one‑time password (OTP) that was sent to a user's phone number. It ensures both arguments are provided, retrieves the expected OTP from the cache, and compares it with the supplied value. If the OTP matches, the function locates the corresponding User record, marks the phone as verified, clears the cached OTP, generates new API credentials for the session, and returns a success response containing a token and the user's profile information. If the OTP is missing, expired, incorrect, or the user cannot be found, an appropriate error response is returned.

Parameters  
- **phone** – The user's phone number as a string; used as the lookup key for the cached OTP and the User document.  
- **otp** – The OTP string that the user received on their phone and must be verified.

### `def verify_email_code(email, otp)`
<!-- 16829115df5b6e8155a3bf0e84bdfe236c70b9d6e0f1230cc6660a4faf6c418b -->
The verify_email_code function is used to verify a user's email address using a 6-digit One-Time Password (OTP). It takes two parameters: email and otp, which represent the user's email address and the OTP to be verified, respectively. The function checks if the provided OTP matches the one stored in the cache for the given email address, and if they match, it marks the user as verified, generates new API keys, and returns a successful response with the user's profile data and authentication token. If the OTP is invalid or has expired, or if any other error occurs during the verification process, the function returns an error response with a corresponding status code.

### `def register_user(password, first_name, last_name, email=None, phone=None)`
<!-- 553fd79153230e074bd7c22683211961bc12433e19491cf9d79b57ee2503edec -->
The register_user function is used to create a new user account and send a verification code to the user's email or phone. It takes in several parameters: password, first_name, last_name, email, and phone. The email parameter is optional and defaults to None, while the phone parameter is also optional and defaults to None. If the email is not provided but a phone number is, the function will generate an email address in the format of phone_number@site_prefix.app. The function checks if the email address is already registered and returns an error if it is. It then creates a new user account, generates a 6-digit verification code, and sends it to the user's email or phone. The function returns a response with a message and the user's details.

### `def forgot_password(user)`
<!-- cbb7f516292a40a391753d174ed10cfe428e8254193ce9f4fd8be3019dabc872 -->
The forgot_password function initiates a password reset for a given user, handling both email and phone number inputs. It takes one parameter, user, which is a string representing the user's email address or phone number. The function generates a 6-digit one-time password (OTP) and stores it in the cache with a 10-minute expiration time. If the input is a phone number, it sends the OTP via SMS; otherwise, it sends the OTP via email to the user's registered email address. The function returns a success message, regardless of whether the user exists or not, for security purposes.

### `def forgot_password_confirm(email, verify_code, password=None)`
<!-- 5f997755857de5ee65c7805cd05c1a9a49e65219e2279bb86edf34e40b943396 -->
The forgot_password_confirm function is used to confirm a password reset using a verification code or token. It takes three parameters: email, verify_code, and an optional password. The email parameter can be either the email address or the phone number used for the password reset. The verify_code parameter is the verification code or token sent to the user. If the password parameter is provided, the function will update the user's password to the specified value after verifying the code. The function returns a response indicating whether the verification was successful, the password was updated, or an error occurred.

### `def login_with_google(email, display_name, id, avatar=None)`
<!-- 2b72025898b3507fb684717bcaf25cab141f278440bbaea341409967105af1b4 -->
The login_with_google function is a social login endpoint that links accounts by email or creates new ones. It takes four parameters: email, display_name, id, and an optional avatar. The email parameter is the user's email address, display_name is the user's full name, id is a unique identifier, and avatar is the user's profile picture. If the email address is not provided, the function returns an error response. If a user with the provided email address does not exist, a new user account is created with the provided information. If a user with the provided email address already exists, their account is updated with the provided avatar if it is not already set. The function then generates or retrieves a secret for API authentication and returns a login response with an access token and user information.

### `def search_user(name, page=1, limit=20, lang='en')`
Search for users by name, email, or phone.

### `def send_wallet_balance(amount, name_or_number, message=None, lang='en')`
<!-- f6844708de371c361c84d00763e938cd7d22d35d8447568f599927782928f225 -->
The send_wallet_balance function transfers the specified amount from the current user's wallet to another user's wallet. It takes four parameters: amount, which is the amount to be transferred as a float, name_or_number, which is the recipient's phone number or email address as a string, message, an optional string parameter for a custom message, and lang, an optional string parameter for the language, defaulting to English if not provided. The function first checks if the sender is logged in and has a wallet, then verifies the recipient's existence and wallet. It ensures the sender has sufficient balance before performing the transfer and logs the transaction history for both the sender and the recipient.

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
<!-- 467005f6d9a8c79c858e7dd978c0934bcf39598083874c6185ad0d4aa5bf4a93 -->
The update_user_profile function updates the profile information for the currently logged-in user. It takes one parameter, profile_data, which is a JSON string or a dictionary containing the new profile data. The function checks if the user is logged in and then updates the allowed fields in the user's profile, including first name, last name, phone, birth date, location, and gender. If the update is successful, it returns a dictionary with a status of success and a message indicating that the profile has been updated successfully.

### `def get_user_order_refunds(page=1)`
<!-- 4ee17c9ac7e042a2e827523c0844e0118d9814df4858975171e8035eb4c264e6 -->
The get_user_order_refunds function retrieves a list of order refunds associated with the currently logged-in user. It takes an optional page parameter, which defaults to 1, allowing for pagination of the results with 10 refunds per page. The function returns a list of refunds, each containing the refund name, order, cause, and status, sorted in descending order by creation date. If the user is not logged in, it throws an error requiring the user to log in to view their refunds.

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
