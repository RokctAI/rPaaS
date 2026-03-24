import frappe
from frappe.utils.password import check_password


def validate(request=None):
    """
    Custom authentication hook to support 'Bearer <api_key>:<api_secret>'
    which is used by the legacy Flutter app.
    Standard Frappe expects 'token <api_key>:<api_secret>'.
    """
    auth_header = frappe.get_request_header("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ")[1].strip()
        if ":" in token:
            try:
                api_key, api_secret = token.split(":")
                user = frappe.db.get_value(
                    "User", {"api_key": api_key}, "name"
                )
                if user:
                    if check_password(user, api_secret):
                        frappe.set_user(user)
                        return user
            except Exception:
                pass
    return None
