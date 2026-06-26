# Test Imports
try:
    import frappe
    import staticmap
    from paas.whatsapp.api import webhook
    from paas.whatsapp import utils

    print("✅ All modules imported successfully.")
except ImportError as e:
    print(f"❌ Import Error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")

# Verify Webhook Exposure
if hasattr(frappe, "whitelist"):
    # This is just a mock check, actual frappe environment needed to verify
    # whitelist registry
    pass

print("Test complete.")
