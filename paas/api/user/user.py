import frappe
import random
import json
import uuid
import csv
import io
from paas.utils import check_subscription_feature
from paas.api.utils import api_response


@frappe.whitelist()
def logout():
    """
    Log out the current user.
    """
    frappe.local.login_manager.logout()
    return api_response(message="User successfully logout")


@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
    """
    Login endpoint compatible with legacy Flutter app.
    Supports both email and phone number as the username.
    Returns API Key/Secret as Bearer token.
    """
    # If the username looks like a phone number, resolve it to an email
    if usr and (usr.startswith("+") or usr.isdigit()):
        phone_user = frappe.db.get_value("User", {"phone": usr}, "name")
        if phone_user:
            usr = phone_user

    try:
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()
    except frappe.AuthenticationError:
        return api_response(message="Invalid credentials", status_code=401)

    user = frappe.get_doc("User", frappe.session.user)

    # Generate API keys if missing
    api_secret = None
    if not user.api_key:
        api_secret = frappe.generate_hash(length=15)
        user.api_key = frappe.generate_hash(length=15)
        user.api_secret = api_secret
        user.save(ignore_permissions=True)
    else:
        # If keys exist, we cannot retrieve the secret.
        # We must regenerate them to provide a valid token.
        # WARNING: This invalidates previous sessions using the old key.
        api_secret = frappe.generate_hash(length=15)
        user.api_key = frappe.generate_hash(length=15)
        user.api_secret = api_secret
        user.save(ignore_permissions=True)

    token = f"{user.api_key}:{api_secret}"

    # Fetch shop details if available
    shop = None
    try:
        # Check if user has a shop linked via the 'user' field in Shop doctype
        shop_name = frappe.db.get_value("Shop", {"user": user.name}, "name")
        if shop_name:
            shop_doc = frappe.get_doc("Shop", shop_name)
            shop = {
                "id": shop_doc.name,
                "uuid": shop_doc.uuid,
                "name": shop_doc.shop_name,
                "logo": shop_doc.logo,
                "cover_photo": shop_doc.cover_photo,
                "active": shop_doc.open,
                "status": shop_doc.status,
            }
    except Exception:
        pass

    return api_response(
        message="Logged In",
        data={
            "access_token": token,
            "token_type": "Bearer",
            "user": {
                "id": user.name,  # Use email/name as ID
                "email": user.email,
                "firstname": user.first_name,
                "lastname": user.last_name,
                "phone": user.phone,
                "role": "user",  # Default role for mobile app
                "active": 1,
                "img": user.user_image,
                "shop": shop,
                "home_page": user.get_home_page(),
            },
        },
    )


@frappe.whitelist()
def get_profile():
    """
    Get the current user's profile details.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your profile.",
            frappe.AuthenticationError,
        )

    user_doc = frappe.get_doc("User", user)

    # Fetch shop details if available
    shop = None
    shop_name = frappe.db.get_value("Shop", {"user": user}, "name")
    if shop_name:
        try:
            shop_doc = frappe.get_doc("Shop", shop_name)
            shop = {
                "id": shop_doc.name,
                "uuid": shop_doc.uuid,
                "name": shop_doc.shop_name,
                "logo": shop_doc.logo,
                "cover_photo": shop_doc.cover_photo,
                "active": shop_doc.open,
                "status": shop_doc.status,
            }
        except Exception:
            pass

    return api_response(
        data={
            "id": user_doc.name,
            "email": user_doc.email,
            "firstname": user_doc.first_name,
            "lastname": user_doc.last_name,
            "phone": user_doc.phone,
            "role": "user",
            "active": 1,
            "img": user_doc.user_image,
            "shop": shop,
            "wallet": frappe.db.get_value(
                "Wallet", {"user": user_doc.name}, "balance"
            )
            or 0.0,
        }
    )


@frappe.whitelist()
def update_profile(
    firstname=None, lastname=None, email=None, phone=None, images=None
):
    """
    Update the current user's profile.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update your profile.",
            frappe.AuthenticationError,
        )

    user_doc = frappe.get_doc("User", user)

    if firstname:
        user_doc.first_name = firstname
    if lastname:
        user_doc.last_name = lastname
    if phone:
        user_doc.phone = phone

    # Handle Image Upload (expects list or single string URL)
    if images:
        if isinstance(images, list) and len(images) > 0:
            user_doc.user_image = images[0]
        elif isinstance(images, str):
            user_doc.user_image = images

    user_doc.save(ignore_permissions=True)
    return get_profile()


@frappe.whitelist()
def update_password(password, password_confirmation):
    """
    Update the current user's password.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update your password.",
            frappe.AuthenticationError,
        )

    if password != password_confirmation:
        frappe.throw("Password confirmation does not match.")

    user_doc = frappe.get_doc("User", user)
    user_doc.new_password = password
    user_doc.save(ignore_permissions=True)

    return api_response(message="Password updated successfully")


@frappe.whitelist()
def delete_account():
    """
    Deletes the currently logged-in user's account.
    If deletion fails due to linked documents, the account is deactivated instead.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to delete your account.",
            frappe.AuthenticationError,
        )

    try:
        # Attempt to delete the User document
        frappe.delete_doc("User", user, ignore_permissions=True)
        # Logout the session
        if hasattr(frappe.local, "login_manager"):
            frappe.local.login_manager.logout()
        return api_response(message="Account deleted successfully.")
    except (frappe.LinkExistsError, frappe.exceptions.LinkExistsError):
        # Fallback: Deactivate the user if linked documents exist
        frappe.db.set_value("User", user, "enabled", 0)
        if hasattr(frappe.local, "login_manager"):
            frappe.local.login_manager.logout()
        return api_response(message="Account deactivated successfully.")


@frappe.whitelist()
@check_subscription_feature("phone_verification")
def check_phone(phone: str):
    """
    Check if a phone number is already registered to a user.
    """
    if not phone:
        frappe.throw("Phone number is a required parameter.")

    if frappe.db.exists("User", {"phone": phone}):
        return api_response(
            message="Phone number already exists.", data={"status": "error"}
        )
    else:
        return api_response(
            message="Phone number is available.", data={"status": "success"}
        )


@frappe.whitelist()
@check_subscription_feature("phone_verification")
def send_phone_verification_code(phone: str):
    """
    Generate and send a phone verification code (OTP).
    This is used for both initial verification and resending.
    """
    if not phone:
        frappe.throw("Phone number is a required parameter.")

    # Generate a 6-digit OTP
    otp = "".join([str(random.randint(0, 9)) for _ in range(6)])

    # Store the OTP in cache for 10 minutes (600 seconds)
    cache_key = f"phone_otp:{phone}"
    frappe.cache.set_value(cache_key, otp, expires_in_sec=600)

    # Send SMS
    try:
        frappe.send_sms(
            receivers=[phone], message=f"Your verification code is: {otp}"
        )
    except Exception as e:
        frappe.log_error(
            f"Failed to send OTP SMS to {phone}: {e}", "SMS Sending Error"
        )
        frappe.throw(
            "Failed to send verification code. Please try again later."
        )

    return api_response(message="Verification code sent successfully.")


@frappe.whitelist()
@check_subscription_feature("phone_verification")
def verify_phone_code(phone: str, otp: str):
    """
    Verify the OTP sent to a user's phone.
    Note: This flow is designed for existing users verifying their number.
    For new user registration, the OTP should be verified before the User doc is created.
    """
    if not phone or not otp:
        frappe.throw("Phone number and OTP are required parameters.")

    cache_key = f"phone_otp:{phone}"
    cached_otp = frappe.cache.get_value(cache_key)

    if not cached_otp:
        return api_response(
            message="OTP expired or was not sent. Please request a new one.",
            status_code=400,
        )

    if otp != cached_otp:
        return api_response(
            message="Invalid verification code.", status_code=400
        )

    # OTP is correct, find user and mark as verified
    try:
        user = frappe.get_doc("User", {"phone": phone})
        user.phone_verified_at = frappe.utils.now_datetime()
        user.save(ignore_permissions=True)
    except frappe.DoesNotExistError:
        return api_response(
            message="User with this phone number not found.", status_code=404
        )
    except Exception as e:
        frappe.log_error(
            f"Failed to update phone_verified_at for user with phone {phone}: {e}",
            "Phone Verification Error",
        )
        frappe.throw(
            "An error occurred while verifying your phone number. Please try again."
        )

    # Clear the OTP from cache
    frappe.cache.delete_value(cache_key)

    # Generate fresh API keys for the new session
    api_secret = frappe.generate_hash(length=15)
    user.api_key = frappe.generate_hash(length=15)
    user.api_secret = api_secret
    user.save(ignore_permissions=True)
    frappe.db.commit()

    # Get full profile data matching VerifyData/ProfileData structure
    user_info = {
        "id": user.name,
        "email": user.email,
        "firstname": user.first_name,
        "lastname": user.last_name,
        "phone": user.phone,
        "img": user.user_image,
    }

    return api_response(
        message="Phone number verified successfully.",
        data={"token": f"{user.api_key}:{api_secret}", "user": user_info},
    )


@frappe.whitelist(allow_guest=True)
def verify_email_code(email: str, otp: str):
    """
    Verify a user's email address using a 6-digit OTP.
    """
    if not email or not otp:
        return api_response(
            message="Email and OTP are required.", status_code=400
        )

    # Retrieve the OTP from cache
    cache_key = f"email_otp:{email}"
    stored_otp = frappe.cache.get_value(cache_key)

    if not stored_otp or str(stored_otp) != str(otp):
        return api_response(
            message="Invalid or expired verification code.", status_code=401
        )

    # Mark the user as verified
    try:
        user = frappe.get_doc("User", email)
        user.email_verified_at = frappe.utils.now_datetime()
        user.save(ignore_permissions=True)
        frappe.db.commit()

        # Generate fresh API keys for the new session
        api_secret = frappe.generate_hash(length=15)
        user.api_key = frappe.generate_hash(length=15)
        user.api_secret = api_secret
        user.save(ignore_permissions=True)
        frappe.db.commit()

        # Clear the OTP from cache
        frappe.cache.delete_value(cache_key)

        # Get full profile data matching VerifyData/ProfileData structure
        user_info = {
            "id": user.name,
            "email": user.email,
            "firstname": user.first_name,
            "lastname": user.last_name,
            "phone": user.phone,
            "img": user.user_image,
        }

        return api_response(
            message="Email verified successfully.",
            data={"token": f"{user.api_key}:{api_secret}", "user": user_info},
        )
    except frappe.DoesNotExistError:
        return api_response(message="User not found.", status_code=404)
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Email Verification Error")
        return api_response(message=f"An error occurred: {
            str(e)}", status_code=500)


@frappe.whitelist(allow_guest=True)
def register_user(password, first_name, last_name, email=None, phone=None):
    """
    Register a new user and send a verification code (OTP).
    Handles both email and phone registration.
    """
    # If email is missing but phone exists, use phone as the primary identifier
    if not email and phone:
        # Get the current site name prefix (e.g., 'spazafy' from
        # 'spazafy.tenant.rokct.ai')
        site_prefix = frappe.local.site.split(".")[0]
        email = f"{phone.strip('+')}@{site_prefix}.app"

    if not email:
        return api_response(
            message="Email or Phone is required.", status_code=400
        )

    if frappe.db.exists("User", email):
        return api_response(
            message="Email address already registered.", status_code=409
        )

    # Create the new user
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "send_welcome_email": 0,
            "roles": [{"role": "PaaS User"}, {"role": "user"}],
        }
    )
    user.set("new_password", password)

    # Generate a 6-digit OTP
    otp = "".join([str(random.randint(0, 9)) for _ in range(6)])

    # Store the OTP in cache for 10 minutes (600 seconds)
    # We use both email and phone in the key for redundancy
    cache_key = f"email_otp:{email}"
    frappe.cache.set_value(cache_key, otp, expires_in_sec=600)
    if phone:
        frappe.cache.set_value(f"phone_otp:{phone}", otp, expires_in_sec=600)

    # Store token in user doc for verification fallback/tests
    user.email_verification_token = otp
    user.insert(ignore_permissions=True)

    # Deliver OTP based on registration type
    is_phone_reg = "@spazafy.app" in email
    if is_phone_reg and phone:
        try:
            frappe.send_sms(
                receivers=[phone], message=f"Your verification code is: {otp}"
            )
        except Exception as e:
            frappe.log_error(f"SMS Send Error: {e}")
    else:
        # Send the verification email with the OTP
        email_context = {"first_name": user.first_name, "otp_code": otp}
        frappe.sendmail(
            recipients=[user.email],
            subject="Your Verification Code",
            template="New User Welcome",
            args=email_context,
            now=True,
        )

    return api_response(
        message="User registered successfully. Please check your "
        + ("phone" if is_phone_reg else "email")
        + " for the 6-digit verification code.",
        data={
            "user": {
                "email": user.email if not is_phone_reg else None,
                "firstname": user.first_name,
                "lastname": user.last_name,
                "phone": user.phone,
            }
        },
    )


@frappe.whitelist(allow_guest=True)
def forgot_password(user: str):
    """
    Initiate a password reset for a given user.
    Handles both email and phone number inputs.
    """
    try:
        is_phone = user.startswith("+") or user.isdigit()
        # Generate and store 6-digit OTP
        otp = "".join([str(random.randint(0, 9)) for _ in range(6)])
        frappe.cache.set_value(
            f"password_reset_otp:{user}", otp, expires_in_sec=600
        )

        if is_phone:
            try:
                frappe.send_sms(
                    receivers=[user],
                    message=f"Your password reset code is: {otp}",
                )
            except Exception as sms_error:
                frappe.log_error(
                    f"Failed to send password reset SMS to {user}: {sms_error}",
                    "SMS Reset Error",
                )
        else:
            # Send the OTP via email
            user_doc_name = frappe.db.get_value(
                "User", {"email": user}, "name"
            )
            if user_doc_name:
                user_doc = frappe.get_doc("User", user_doc_name)
                frappe.sendmail(
                    recipients=[user],
                    subject="Password Reset Code",
                    message=f"Hello {
                        user_doc.first_name}, your password reset code is: {otp}",
                    now=True,
                )

        return api_response(
            message="If a user with this email/phone exists, a password reset code has been sent.")
    except Exception:
        # For security, always return success
        return api_response(
            message="If a user with this email/phone exists, a password reset code has been sent.")


@frappe.whitelist(allow_guest=True)
def forgot_password_confirm(email, verify_code, password=None):
    """
    Confirm password reset using a verification code (OTP) or token.
    'email' can be the email address OR the phone number used for reset.
    """
    try:
        is_phone = email.startswith("+") or email.isdigit()
        cached_otp = frappe.cache.get_value(f"password_reset_otp:{email}")
        if not cached_otp or cached_otp != verify_code:
            return api_response(
                message="Invalid or expired verification code", status_code=400
            )

        if is_phone:
            user_name = frappe.db.get_value("User", {"phone": email}, "name")
        else:
            user_name = frappe.db.get_value("User", {"email": email}, "name")

        if not user_name:
            return api_response(message="User not found", status_code=404)

        if password:
            user_doc = frappe.get_doc("User", user_name)
            user_doc.set("new_password", password)
            user_doc.reset_password_key = None  # Clear token after use
            user_doc.save(ignore_permissions=True)
            if is_phone:
                frappe.cache.delete_value(f"password_reset_otp:{email}")
            return api_response(message="Password updated successfully")

        return api_response(message="Code verified")
    except Exception as e:
        return api_response(message=str(e), status_code=500)


@frappe.whitelist(allow_guest=True)
def login_with_google(email, display_name, id, avatar=None):
    """
    Social login endpoint. Links accounts by email or creates new ones.
    """
    if not email:
        return api_response(message="Email is required", status_code=400)

    user_name = frappe.db.get_value("User", {"email": email}, "name")

    if not user_name:
        # Create new user
        names = display_name.split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""

        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "user_image": avatar,
                "enabled": 1,
                "send_welcome_email": 0,
                "roles": [{"role": "PaaS User"}, {"role": "user"}],
            }
        )
        # Generate a random password for social users
        user.set("new_password", frappe.generate_hash(length=12))
        user.insert(ignore_permissions=True)
        user_name = user.name
    else:
        user = frappe.get_doc("User", user_name)
        if avatar and not user.user_image:
            user.user_image = avatar
            user.save(ignore_permissions=True)

    # Generate or retrieve secret for API authentication
    api_secret = user.get_password("api_secret")
    if not user.api_key or not api_secret:
        api_secret = frappe.generate_hash(length=15)
        user.api_key = frappe.generate_hash(length=15)
        user.api_secret = api_secret
        user.save(ignore_permissions=True)

    token = f"{user.api_key}:{api_secret}"

    return api_response(
        message="Logged In via Google",
        data={
            "access_token": token,
            "token_type": "Bearer",
            "user": {
                "id": user.name,
                "email": user.email,
                "firstname": user.first_name,
                "lastname": user.last_name,
                "phone": user.phone,
                "role": "user",
                "active": 1,
                "img": user.user_image,
            },
        },
    )


@frappe.whitelist()
def search_user(name: str, page: int = 1, limit: int = 20, lang: str = "en"):
    """
    Search for users by name, email, or phone.
    """
    t_user = frappe.qb.DocType("User")
    query = (
        frappe.qb.from_(t_user)
        .select(t_user.name, t_user.full_name, t_user.user_image)
        .where(t_user.enabled == 1)
        .where(t_user.name != "Guest")
        .where(t_user.name != "Administrator")
    )

    from frappe.query_builder.functions import Function

    to_tsvector = Function("to_tsvector")
    plainto_tsquery = Function("plainto_tsquery")
    tsq = plainto_tsquery("english", name)

    query = query.where(
        (to_tsvector("english", t_user.first_name).matches(tsq))
        | (to_tsvector("english", t_user.last_name).matches(tsq))
        | (to_tsvector("english", t_user.email).matches(tsq))
        | (to_tsvector("english", t_user.phone).matches(tsq))
    )

    users = query.limit(limit).offset((page - 1) * limit).run(as_dict=True)
    return api_response(data=users)


@frappe.whitelist()
def send_wallet_balance(
    amount: float, name_or_number: str, message: str = None, lang: str = "en"
):
    """
    Transfers wallet balance from current user to another user.
    """
    sender = frappe.session.user
    if sender == "Guest":
        frappe.throw("You must be logged in to transfer funds.")

    # Find recipient
    recipient = frappe.db.get_value("User", {"phone": name_or_number}, "name")
    if not recipient:
        recipient = frappe.db.get_value(
            "User", {"email": name_or_number}, "name"
        )

    if not recipient:
        frappe.throw("Recipient not found.")

    if recipient == sender:
        frappe.throw("You cannot send money to yourself.")

    # Ensure sender has a wallet
    sender_wallet_name = frappe.db.get_value(
        "Wallet", {"user": sender}, "name"
    )
    if not sender_wallet_name:
        frappe.throw("You do not have a wallet.")

    sender_wallet = frappe.get_doc("Wallet", sender_wallet_name)

    # Check balance
    amount_val = float(amount)
    if sender_wallet.balance < amount_val:
        frappe.throw("Insufficient balance.")

    # Ensure recipient has a wallet (get or create)
    recipient_wallet_name = frappe.db.get_value(
        "Wallet", {"user": recipient}, "name"
    )
    if not recipient_wallet_name:
        recipient_wallet = frappe.get_doc(
            {"doctype": "Wallet", "user": recipient, "balance": 0}
        ).insert(ignore_permissions=True)
        recipient_wallet_name = recipient_wallet.name
    else:
        recipient_wallet = frappe.get_doc("Wallet", recipient_wallet_name)

    # Atomic Transfer
    sender_wallet.balance -= amount_val
    recipient_wallet.balance += amount_val

    sender_wallet.save(ignore_permissions=True)
    recipient_wallet.save(ignore_permissions=True)

    # Log History – Sender
    frappe.get_doc(
        {
            "doctype": "Wallet History",
            "wallet": sender_wallet_name,
            "transaction_type": "Withdraw",
            "amount": amount_val,
            "status": "Processed",
            "description": f"Transfer to {recipient}",
        }
    ).insert(ignore_permissions=True)

    # Log History – Recipient
    frappe.get_doc(
        {
            "doctype": "Wallet History",
            "wallet": recipient_wallet_name,
            "transaction_type": "Topup",
            "amount": amount_val,
            "status": "Processed",
            "description": f"Transfer from {sender}",
        }
    ).insert(ignore_permissions=True)

    return {"status": "success", "message": "Funds transferred successfully."}


@frappe.whitelist()
def update_profile_image(image: str):
    """
    Updates the user's profile image.
    Alias/Wrapper for update_profile logic specific to image.
    """
    return update_profile(images=image)


@frappe.whitelist()
def get_user_order_refunds(page: int = 1, lang: str = "en"):
    """
    Retrieves a list of order refunds for the current user.
    """
    user = frappe.session.user
    refunds = frappe.get_list(
        "Order Refund",
        filters={"user": user},
        fields=["name", "amount", "reason", "status", "creation", "modified"],
        limit_start=None,  # Deprecated
        limit_page_length=None,  # Deprecated
        offset=(page - 1) * 10,
        limit=10,
        order_by="creation desc",
        ignore_permissions=True,
    )
    return refunds


@frappe.whitelist()
def get_user_membership():
    """
    Retrieves the active membership for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your membership.",
            frappe.AuthenticationError,
        )

    user_membership = frappe.get_all(
        "User Membership",
        filters={"user": user, "is_active": 1},
        fields=["name", "membership", "start_date", "end_date"],
        order_by="end_date desc",
        limit=1,
    )

    if not user_membership:
        return None

    return user_membership[0]


@frappe.whitelist()
def get_user_membership_history():
    """
    Retrieves the membership history for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your membership history.",
            frappe.AuthenticationError,
        )

    return frappe.get_all(
        "User Membership",
        filters={"user": user},
        fields=["name", "membership", "start_date", "end_date", "is_active"],
        order_by="end_date desc",
    )


@frappe.whitelist()
def get_user_parcel_orders():
    """
    Retrieves the parcel order history for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your parcel orders.",
            frappe.AuthenticationError,
        )

    return frappe.get_all(
        "Parcel Order",
        filters={"user": user},
        fields=["name", "status", "total_price", "delivery_date"],
        order_by="creation desc",
        ignore_permissions=True,
    )


@frappe.whitelist()
def get_user_parcel_order(name):
    """
    Retrieves a single parcel order for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your parcel orders.",
            frappe.AuthenticationError,
        )

    parcel_order = frappe.get_doc("Parcel Order", name)
    if parcel_order.user != user:
        frappe.throw(
            "You are not authorized to view this parcel order.",
            frappe.PermissionError,
        )

    return parcel_order.as_dict()


@frappe.whitelist()
def get_user_addresses():
    """
    Retrieves the list of addresses for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your addresses.",
            frappe.AuthenticationError,
        )

    return frappe.get_all(
        "User Address",
        filters={"user": user},
        fields=["name", "title", "address", "location", "active"],
    )


@frappe.whitelist()
def get_user_address(name):
    """
    Retrieves a single address for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your addresses.",
            frappe.AuthenticationError,
        )

    address = frappe.get_doc("User Address", name)
    if address.user != user:
        frappe.throw(
            "You are not authorized to view this address.",
            frappe.PermissionError,
        )

    return address.as_dict()


@frappe.whitelist()
def add_user_address(address_data):
    """
    Adds a new address for the currently logged-in user.
    """
    if isinstance(address_data, str):
        address_data = json.loads(address_data)

    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to add an address.",
            frappe.AuthenticationError,
        )

    address = frappe.get_doc(
        {
            "doctype": "User Address",
            "user": user,
            "title": address_data.get("title"),
            "address": json.dumps(address_data.get("address")),
            "location": json.dumps(address_data.get("location")),
            "active": address_data.get("active", 1),
        }
    )
    address.insert(ignore_permissions=True)
    return address.as_dict()


@frappe.whitelist()
def update_user_address(name, address_data):
    """
    Updates an existing address for the currently logged-in user.
    """
    if isinstance(address_data, str):
        address_data = json.loads(address_data)

    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update an address.",
            frappe.AuthenticationError,
        )

    address = frappe.get_doc("User Address", name)
    if address.user != user:
        frappe.throw(
            "You are not authorized to update this address.",
            frappe.PermissionError,
        )

    address.title = address_data.get("title", address.title)
    address.address = json.dumps(address_data.get("address", address.address))
    address.location = json.dumps(
        address_data.get("location", address.location)
    )
    address.active = address_data.get("active", address.active)
    address.save(ignore_permissions=True)
    return address.as_dict()


@frappe.whitelist()
def delete_user_address(name):
    """
    Deletes an address for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to delete an address.",
            frappe.AuthenticationError,
        )

    address = frappe.get_doc("User Address", name)
    if address.user != user:
        frappe.throw(
            "You are not authorized to delete this address.",
            frappe.PermissionError,
        )

    frappe.delete_doc("User Address", name, ignore_permissions=True)
    return {"status": "success", "message": "Address deleted successfully."}


@frappe.whitelist()
def get_user_invites():
    """
    Retrieves the list of invites for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your invites.",
            frappe.AuthenticationError,
        )

    return frappe.get_all(
        "Invitation",
        filters={"user": user},
        fields=["name", "shop", "role", "status"],
    )


@frappe.whitelist()
def create_invite(shop, user, role):
    """
    Creates a new invite.
    """
    # In a real application, we would have more permission checks here.
    # For example, only a shop owner or manager should be able to invite users.
    # For now, we will assume the user has the necessary permissions.

    invite = frappe.get_doc(
        {
            "doctype": "Invitation",
            "shop": shop,
            "user": user,
            "role": role,
            "status": "New",
        }
    )
    invite.insert(ignore_permissions=True)
    return invite.as_dict()


@frappe.whitelist()
def update_invite_status(name, status):
    """
    Updates the status of an invite.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update an invite.",
            frappe.AuthenticationError,
        )

    invite = frappe.get_doc("Invitation", name)
    if invite.user != user:
        frappe.throw(
            "You are not authorized to update this invite.",
            frappe.PermissionError,
        )

    if status not in ["Accepted", "Rejected"]:
        frappe.throw("Invalid status. Must be 'Accepted' or 'Rejected'.")

    invite.status = status
    invite.save(ignore_permissions=True)
    return invite.as_dict()


@frappe.whitelist()
def get_user_wallet():
    """
    Retrieves the wallet for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your wallet.",
            frappe.AuthenticationError,
        )

    wallet = frappe.get_doc("Wallet", {"user": user})
    return api_response(data=wallet.as_dict())


@frappe.whitelist()
def get_wallet_history(start=0, limit=20):
    """
    Retrieves the wallet history for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your wallet history.",
            frappe.AuthenticationError,
        )

    wallet = frappe.get_doc("Wallet", {"user": user})
    history = frappe.get_all(
        "Wallet History",
        filters={"wallet": wallet.name},
        fields=["name", "transaction_type", "amount", "status", "creation"],
        order_by="creation desc",
        offset=start,
        limit=limit,
    )
    return api_response(data=history)


@frappe.whitelist()
def export_orders():
    """
    Exports all orders for the current user to a CSV file.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to export orders.",
            frappe.AuthenticationError,
        )

    orders = frappe.get_all(
        "Order",
        filters={"user": user},
        fields=["name", "shop", "total_price", "status", "creation"],
        order_by="creation desc",
    )

    if not orders:
        return []

    # Create a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write the header row
    writer.writerow(["Order ID", "Shop", "Total Price", "Status", "Date"])

    # Write the data rows
    for order in orders:
        writer.writerow(
            [
                order.name,
                order.shop,
                order.total_price,
                order.status,
                order.creation,
            ]
        )

    # Set the response headers for CSV download
    frappe.local.response.filename = "orders.csv"
    frappe.local.response.filecontent = output.getvalue()
    frappe.local.response.type = "csv"


@frappe.whitelist()
def register_device_token(device_token: str, provider: str):
    """
    Registers a new device token for the current user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to register a device token.",
            frappe.AuthenticationError,
        )

    if not device_token or not provider:
        frappe.throw("Device token and provider are required.")

    if frappe.db.exists("Device Token", {"device_token": device_token}):
        return api_response(message="Device token already registered.")

    frappe.get_doc(
        {
            "doctype": "Device Token",
            "user": user,
            "device_token": device_token,
            "provider": provider,
        }
    ).insert(ignore_permissions=True)
    return api_response(message="Device token registered successfully.")


@frappe.whitelist()
def get_user_transactions(start=0, limit=20):
    """
    Retrieve the list of transactions for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your transactions.",
            frappe.AuthenticationError,
        )

    transactions = frappe.get_all(
        "Transaction",
        filters={"user": user},
        fields=[
            "name",
            "user",
            "amount",
            "status",
            "payable_type",
            "payable_id",
            "creation",
        ],
        order_by="creation desc, name desc",
        offset=start,
        limit=limit,
        ignore_permissions=True,
    )
    return api_response(data=transactions)


@frappe.whitelist()
def get_user_shop():
    """
    Retrieves the shop owned by the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your shop.",
            frappe.AuthenticationError,
        )

    try:
        shop_name = frappe.db.get_value("Shop", {"user": user}, "name")
        if not shop_name:
            return api_response(data=None)
        return api_response(data=frappe.get_doc("Shop", shop_name).as_dict())
    except frappe.DoesNotExistError:
        return api_response(data=None)


@frappe.whitelist()
def update_seller_shop(shop_data):
    """
    Updates the shop owned by the currently logged-in seller.
    """
    if isinstance(shop_data, str):
        shop_data = json.loads(shop_data)

    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update your shop.",
            frappe.AuthenticationError,
        )

    shop_name = frappe.db.get_value("Shop", {"user": user}, "name")
    if not shop_name:
        frappe.throw("You do not own a shop.", frappe.PermissionError)

    shop = frappe.get_doc("Shop", shop_name)

    # List of fields that a user is allowed to update
    updatable_fields = ["phone", "location", "open", "shop_name"]

    # Handle name change (Rename Doc) BEFORE other updates
    new_shop_name = shop_data.get("shop_name") or shop_data.get("title")
    if new_shop_name and new_shop_name != shop.name:
        # Switch to admin to bypass permission check for rename
        current_user = frappe.session.user
        frappe.set_user("Administrator")
        try:
            new_name = frappe.rename_doc("Shop", shop.name, new_shop_name)
            shop = frappe.get_doc("Shop", new_name)
        finally:
            frappe.set_user(current_user)

    for key, value in shop_data.items():
        if key in updatable_fields:
            shop.set(key, value)

    # Handle legacy title mapping
    if "title" in shop_data:
        shop.shop_name = shop_data.get("title")

    shop.save(ignore_permissions=True)
    return api_response(data=shop.as_dict())


@frappe.whitelist()
def update_user_shop(shop_data):
    """
    Alias for update_seller_shop (for backward compatibility/testing)
    """
    return update_seller_shop(shop_data)


@frappe.whitelist()
def get_user_request_models(start=0, limit=20):
    """
    Retrieves the list of request models for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your request models.",
            frappe.AuthenticationError,
        )

    models = frappe.get_all(
        "Request Model",
        filters={"created_by_user": user},
        fields=["name", "model_type", "model", "status", "created_at"],
        order_by="creation desc",
        offset=start,
        limit=limit,
    )
    return api_response(data=models)


@frappe.whitelist()
def create_request_model(model_type, model_id, data):
    """
    Creates a new request model.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to create a request model.",
            frappe.AuthenticationError,
        )

    request_model = frappe.get_doc(
        {
            "doctype": "Request Model",
            "model_type": model_type,
            "model": model_id,
            "data": data,
            "created_by_user": user,
            "status": "Pending",
        }
    )
    request_model.insert(ignore_permissions=True)
    return request_model.as_dict()


@frappe.whitelist()
def get_user_tickets(limit_start=0, limit_page_length=20):
    """
    Retrieves the list of tickets for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your tickets.",
            frappe.AuthenticationError,
        )

    return frappe.get_all(
        "Ticket",
        filters={"created_by_user": user, "parent_ticket": None},
        # Only get parent tickets
        fields=["name", "subject", "status", "creation"],
        order_by="creation desc",
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_user_ticket(name):
    """
    Retrieves a single ticket and its replies for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your tickets.",
            frappe.AuthenticationError,
        )

    ticket = frappe.get_doc("Ticket", name)
    if ticket.created_by_user != user:
        frappe.throw(
            "You are not authorized to view this ticket.",
            frappe.PermissionError,
        )

    replies = frappe.get_all(
        "Ticket",
        filters={"parent_ticket": name},
        fields=["name", "content", "created_by_user", "creation"],
    )

    ticket_dict = ticket.as_dict()
    ticket_dict["replies"] = replies
    return ticket_dict


@frappe.whitelist()
def create_ticket(subject, content, order_id=None):
    """
    Creates a new ticket.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to create a ticket.",
            frappe.AuthenticationError,
        )

    ticket = frappe.get_doc(
        {
            "doctype": "Ticket",
            "uuid": str(uuid.uuid4()),
            "subject": subject,
            "content": content,
            "order": order_id,
            "created_by_user": user,
            "user": user,
            "status": "Open",
            "type": "order" if order_id else "general",
        }
    )
    ticket.insert(ignore_permissions=True)
    return ticket.as_dict()


@frappe.whitelist()
def reply_to_ticket(name, content):
    """
    Adds a reply to an existing ticket.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to reply to a ticket.",
            frappe.AuthenticationError,
        )

    parent_ticket = frappe.get_doc("Ticket", name)
    if (
        parent_ticket.created_by_user != user
        and "System Manager" not in frappe.get_roles(user)
    ):
        frappe.throw(
            "You are not authorized to reply to this ticket.",
            frappe.PermissionError,
        )

    reply = frappe.get_doc(
        {
            "doctype": "Ticket",
            "uuid": str(uuid.uuid4()),
            "parent_ticket": name,
            "subject": f"Re: {parent_ticket.subject}",
            "content": content,
            "created_by_user": user,
            "user": user,
            "status": "Answered",
        }
    )
    reply.insert(ignore_permissions=True)

    # Update parent ticket status
    parent_ticket.status = "Answered"
    parent_ticket.save(ignore_permissions=True)

    return reply.as_dict()


@frappe.whitelist()
def get_user_profile():
    """
    Retrieves the profile information for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your profile.",
            frappe.AuthenticationError,
        )

    user_doc = frappe.get_doc("User", user)

    return {
        "first_name": user_doc.first_name,
        "last_name": user_doc.last_name,
        "email": user_doc.email,
        "phone": user_doc.phone,
        "birth_date": user_doc.birth_date,
        "location": user_doc.location,
        "gender": user_doc.gender,
        "ringfenced_balance": user_doc.ringfenced_balance or 0,
    }


@frappe.whitelist()
def update_user_profile(profile_data):
    """
    Updates the profile information for the currently logged-in user.
    """
    if isinstance(profile_data, str):
        profile_data = json.loads(profile_data)

    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update your profile.",
            frappe.AuthenticationError,
        )

    user_doc = frappe.get_doc("User", user)

    # List of fields that a user is allowed to update
    updatable_fields = [
        "first_name",
        "last_name",
        "phone",
        "birth_date",
        "location",
        "gender",
    ]

    for key, value in profile_data.items():
        if key in updatable_fields:
            user_doc.set(key, value)

    user_doc.save(ignore_permissions=True)

    return {"status": "success", "message": "Profile updated successfully."}


@frappe.whitelist()
def get_user_order_refunds(page=1):  # noqa: F811
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to view your refunds.")

    refunds = frappe.get_list(
        "Order Refund",
        filters={"user": user},
        fields=["name", "order", "cause", "status"],
        offset=(int(page) - 1) * 10,
        limit=10,
        order_by="creation desc",
    )
    return refunds


@frappe.whitelist()
def create_order_refund(order, cause):
    """
    Creates a new order refund request.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to request a refund.",
            frappe.AuthenticationError,
        )

    # Check if the user owns the order
    order_doc = frappe.get_doc("Order", order)
    if order_doc.user != user:
        frappe.throw(
            "You are not authorized to request a refund for this order.",
            frappe.PermissionError,
        )

    refund = frappe.get_doc(
        {
            "doctype": "Order Refund",
            "user": user,
            "order": order,
            "cause": cause,
            "status": "Pending",
        }
    )
    refund.insert(ignore_permissions=True)
    return refund.as_dict()


@frappe.whitelist()
def get_user_notifications(start=0, limit=20):
    """
    Retrieves the list of notifications for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your notifications.",
            frappe.AuthenticationError,
        )

    # The Notification doctype in Frappe is complex.
    # It is used for email alerts and other system notifications.
    # A simple way to get user-specific notifications is to look at the
    # Notification Log, which records when a notification is sent to a user.

    return frappe.get_all(
        "Notification Log",
        filters={"user": user},
        fields=[
            "name",
            "subject",
            "document_type",
            "document_name",
            "creation",
            "read",
        ],
        order_by="creation desc",
        offset=start,
        limit=limit,
    )


@frappe.whitelist()
def get_notification_count():
    """
    Retrieves the count of unread notifications for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        return api_response(data={"count": 0})

    count = frappe.db.count("Notification Log", {"user": user, "read": 0})
    return api_response(data={"count": count})


@frappe.whitelist()
def mark_notification_logs_as_read(ids=None):
    """
    Marks specific notification logs as read.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in.", frappe.AuthenticationError)

    if isinstance(ids, str):
        ids = json.loads(ids)

    if not ids:
        return api_response(message="No IDs provided")

    for name in ids:
        if frappe.db.exists("Notification Log", name):
            doc = frappe.get_doc("Notification Log", name)
            if doc.for_user == user or doc.owner == user:  # Check ownership
                doc.read = 1
                doc.save(ignore_permissions=True)

    return api_response(message="Notifications marked as read")


@frappe.whitelist()
def read_all_notifications():
    """
    Marks all notifications as read for the current user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in.", frappe.AuthenticationError)

    logs = frappe.get_all(
        "Notification Log", filters={"for_user": user, "read": 0}
    )
    for log in logs:
        frappe.db.set_value("Notification Log", log.name, "read", 1)

    return api_response(message="All notifications marked as read")


@frappe.whitelist()
def read_one_notification(name):
    """
    Marks a single notification as read.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in.", frappe.AuthenticationError)

    if frappe.db.exists("Notification Log", name):
        doc = frappe.get_doc("Notification Log", name)
        # Verify it belongs to user ( Notification Log uses 'for_user' usually,
        # but sometimes owner)
        if hasattr(doc, "for_user") and doc.for_user == user:
            doc.read = 1
            doc.save(ignore_permissions=True)
        elif doc.owner == user:
            doc.read = 1
            doc.save(ignore_permissions=True)

    return api_response(message="Notification marked as read")
