import frappe
from paas.verification_utils import generate_verification_code

def get_context(context):
    """
    Context generator for the /pay web page.
    Expects order_id, amount, and shop_id in query parameters.
    """
    order_id = frappe.form_dict.get('order_id')
    amount = frappe.form_dict.get('amount')
    shop_id = frappe.form_dict.get('shop_id')
    
    if not all([order_id, amount, shop_id]):
        context.error = "Invalid Payment Link. Please scan the QR code at the counter again."
        return

    try:
        # Generate the OTP that the customer should show the shop manager
        otp = generate_verification_code(order_id, amount, shop_id)
        
        context.otp = otp
        context.order_id = order_id
        context.amount = float(amount)
        context.shop_id = shop_id
        
        # Lookup shop name for better UX
        context.shop_name = frappe.db.get_value("Shop", shop_id, "name_1") or "Spazafy Merchant"
        
        context.status = "Success"
        
    except Exception as e:
        frappe.log_error(f"OTP Generation Error: {str(e)}", "Payment Verification")
        context.error = "An error occurred while processing your verification code."
