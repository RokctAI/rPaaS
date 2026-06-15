from typing import Any, Optional
# Copyright (c) 2025, ROKCT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


class WhatsAppTenantConfig(Document):
    @frappe.whitelist()
    def generate_keys(self) -> Any:
        """
        Generates RSA 2048 Key Pair for WhatsApp Flows Encryption.
        """
        import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
        if self.private_key and self.public_key:
            frappe.throw(
                "Keys already exist. Clear them first if you want to regenerate functionality.")

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Serialize Private Key
        pem_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Serialize Public Key
        public_key = private_key.public_key()
        pem_public = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        self.private_key = pem_private.decode('utf-8')
        self.public_key = pem_public.decode('utf-8')
        self.save()
        return "Keys Generated Successfully"


@frappe.whitelist(allow_guest=True)
def get_config() -> Any:
    """
    Returns public configuration for the WhatsApp / Flutter Tenant.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    try:
        config = frappe.get_single("WhatsApp Tenant Config")
        return {
            "is_multi_vendor": bool(config.is_multi_vendor),
            "default_shop": config.default_shop
        }
    except Exception:
        return {
            "is_multi_vendor": True,  # Default to safe fallback
            "default_shop": None
        }
