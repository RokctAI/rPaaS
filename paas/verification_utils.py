import hashlib


def generate_verification_code(order_id, amount, shop_id):
    """
    Generates a 5-digit verification code using SHA-256 and a shared secret.
    This logic MUST match the Flutter PayVerificationHelper implementation.
    """
    # Fetch shop-specific secret from DB, fallback to legacy if not set
    shared_secret = frappe.db.get_value("Shop", shop_id, "shared_secret")
    if not shared_secret:
        frappe.throw(
            f"Shop {shop_id} does not have a secure secret configured.")

    # Normalize amount to 2 decimal places as string
    normalized_amount = "{:.2f}".format(float(amount))

    # Create the raw string: "order_id|amount|shop_id|secret"
    raw_string = f"{order_id}|{normalized_amount}|{shop_id}|{shared_secret}"

    # Generate SHA-256 hash
    digest = hashlib.sha256(raw_string.encode('utf-8')).digest()

    # Take the first 4 bytes and convert to big-endian integer (matching
    # Flutter)
    hash_int = int.from_bytes(digest[:4], byteorder='big')

    # Use modulo and absolute value to get 5 digits, pad with zeros
    # Note: Python's int.from_bytes from big endian is always positive, but we
    # use abs for safety
    code = abs(hash_int) % 100000

    return str(code).zfill(5)
