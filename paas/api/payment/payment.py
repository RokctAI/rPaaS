from typing import Any, Optional
import frappe
import json
import requests
from frappe.model.document import Document


@frappe.whitelist(allow_guest=True)
def get_payment_gateways() -> Any:
    """
    Retrieves a list of active payment gateways, formatted for frontend compatibility.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    gateways = frappe.get_list(
        "PaaS Payment Gateway",
        filters={"enabled": 1},
        fields=[
            "name",
            "gateway_controller",
            "is_sandbox",
            "creation",
            "modified",
        ],
    )

    formatted_gateways = []
    for gw in gateways:
        formatted_gateways.append(
            {
                "id": gw.name,
                "tag": gw.gateway_controller,
                "sandbox": bool(gw.is_sandbox),
                "active": True,
                "created_at": gw.creation.strftime("%Y-%m-%d %H:%M:%S") + "Z",
                "updated_at": gw.modified.strftime("%Y-%m-%d %H:%M:%S") + "Z",
            }
        )

    return formatted_gateways


@frappe.whitelist(allow_guest=True)
def get_payment_gateway(id: str) -> Any:
    """
    Retrieves a single active payment gateway.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    gw = frappe.db.get_value(
        "PaaS Payment Gateway",
        filters={"name": id, "enabled": 1},
        fieldname=[
            "name",
            "gateway_controller",
            "is_sandbox",
            "creation",
            "modified",
        ],
        as_dict=True,
    )

    if not gw:
        frappe.throw("PaaS Payment Gateway not found or not active.")

    return {
        "id": gw.name,
        "tag": gw.gateway_controller,
        "sandbox": bool(gw.is_sandbox),
        "active": True,
        "created_at": gw.creation.strftime("%Y-%m-%d %H:%M:%S") + "Z",
        "updated_at": gw.modified.strftime("%Y-%m-%d %H:%M:%S") + "Z",
    }


@frappe.whitelist()
def initiate_flutterwave_payment(order_id: str) -> Any:
    """
    The initiate_flutterwave_payment function initiates a payment transaction through Flutterwave for a specified order. It takes one parameter, order_id, which is a string representing the unique identifier of the order for which the payment is being initiated. This function serves as a wrapper around the core payment logic, providing a simplified interface for triggering payments.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return _initiate_flutterwave_logic("Order", order_id)


@frappe.whitelist()
def initiate_flutterwave_parcel_payment(order_id: str) -> Any:
    """
    Initiate flutterwave parcel payment API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return _initiate_flutterwave_logic("Parcel Order", order_id)


def _initiate_flutterwave_logic(doctype: str, docname: str):  # noqa: C901
    trace_id = None
    """
    Internal logic for Flutterwave initiation across different doctypes.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to make a payment.")

    try:
        doc = frappe.get_doc(doctype, docname)
        # Check authorization - for Order it's 'user', for Parcel Order it's
        # 'user'
        if doc.user != user:
            frappe.throw(
                "You are not authorized to pay for this document.",
                frappe.PermissionError,
            )

        if doc.payment_status == "Paid":
            frappe.throw("This document has already been paid for.")

        flutterwave_settings = frappe.get_doc("Flutterwave Settings")
        if not flutterwave_settings.enabled:
            frappe.throw("Flutterwave payments are not enabled.")

        # Prepare the request to Flutterwave
        tx_ref = f"{doc.name}-{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}"

        # Get customer details
        customer_email = frappe.db.get_value("User", user, "email")
        customer_phone = frappe.db.get_value("User", user, "phone")
        customer_full_name = frappe.db.get_value("User", user, "full_name")

        # Handle potential grand_total vs total_price naming differences
        amount = doc.get("grand_total") or doc.get("total_price") or 0

        payload = {
            "tx_ref": tx_ref,
            "amount": amount,
            "currency": doc.get("currency") or frappe.db.get_single_value(
                "System Settings",
                "currency"),
            "redirect_url": f"{
                frappe.utils.get_url()}/api/method/paas.api.flutterwave_callback",
            "customer": {
                "email": customer_email,
                "phonenumber": customer_phone,
                "name": customer_full_name,
            },
            "customizations": {
                "title": f"Payment for {doctype} {
                    doc.name}",
                "logo": frappe.get_website_settings("website_logo"),
            },
        }

        headers = {
            "Authorization": f"Bearer {
                flutterwave_settings.get_password('secret_key')}",
            "Content-Type": "application/json",
        }

        # Make the request to Flutterwave
        response = requests.post(
            "https://api.flutterwave.com/v3/payments",
            json=payload,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        response_data = response.json()

        if response_data.get("status") == "success":
            # Update the document with the transaction reference
            doc.custom_payment_transaction_id = tx_ref
            doc.save(ignore_permissions=True)
            frappe.db.commit()

            return {"payment_url": response_data["data"]["link"]}
        else:
            frappe.log_error(f"Flutterwave initiation failed: {
                response_data.get('message')}", "Flutterwave Error")
            frappe.throw("Failed to initiate payment with Flutterwave.")

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(), "Flutterwave Payment Initiation Failed"
        )
        frappe.throw(f"An error occurred during payment initiation: {e}")


@frappe.whitelist(allow_guest=True)
def flutterwave_callback() -> Any:
    """
    Handles the callback from Flutterwave after a payment attempt.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    args = frappe.request.args
    status = args.get("status")
    tx_ref = args.get("tx_ref")
    transaction_id = args.get("transaction_id")

    flutterwave_settings = frappe.get_doc("Flutterwave Settings")
    success_url = (
        flutterwave_settings.success_redirect_url or "/payment-success"
    )
    failure_url = (
        flutterwave_settings.failure_redirect_url or "/payment-failed"
    )

    if not tx_ref:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = (
            failure_url + "?reason=tx_ref_missing"
        )
        return

    try:
        order_id = tx_ref.split("-")[0]
        order = frappe.get_doc("Order", order_id)

        if status == "successful":
            headers = {"Authorization": f"Bearer {
                flutterwave_settings.get_password('secret_key')}"}
            verify_url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
            response = requests.get(verify_url, headers=headers, timeout=10)
            response.raise_for_status()
            verification_data = response.json()

            if (
                verification_data.get("status") == "success"
                and verification_data["data"]["tx_ref"] == tx_ref
                and verification_data["data"]["amount"] >= order.grand_total
            ):

                order.payment_status = "Paid"
                order.custom_payment_transaction_id = transaction_id
                order.save(ignore_permissions=True)
                frappe.db.commit()

                frappe.local.response["type"] = "redirect"
                frappe.local.response["location"] = success_url
                return

            else:
                order.payment_status = "Failed"
                order.save(ignore_permissions=True)
                frappe.db.commit()
                frappe.log_error(
                    f"Flutterwave callback verification failed for order {order_id}. Data: {verification_data}",
                    "Flutterwave Error",
                )
                frappe.local.response["type"] = "redirect"
                frappe.local.response["location"] = (
                    failure_url + "?reason=verification_failed"
                )
                return

        else:  # Status is 'cancelled' or 'failed'
            order.payment_status = "Failed"
            order.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.local.response["type"] = "redirect"
            frappe.local.response["location"] = (
                failure_url + f"?reason={status}"
            )
            return

    except Exception:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Flutterwave Callback Failed")
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = (
            failure_url + "?reason=internal_error"
        )


@frappe.whitelist()
def get_payfast_settings() -> Any:
    """
    Returns the PayFast settings.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    payfast_settings = frappe.get_doc("PaaS Payment Gateway", "PayFast")
    settings = {s.key: s.value for s in payfast_settings.settings}
    return {
        "merchant_id": settings.get("merchant_id"),
        "merchant_key": settings.get("merchant_key"),
        "pass_phrase": settings.get("pass_phrase"),
        "is_sandbox": payfast_settings.is_sandbox,
        "success_redirect_url": payfast_settings.success_redirect_url
        or "/payment-success",
        "failure_redirect_url": payfast_settings.failure_redirect_url
        or "/payment-failed",
    }


@frappe.whitelist(allow_guest=True)
def handle_payfast_callback() -> Any:
    """
    Handles the PayFast payment callback.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    data = frappe.form_dict

    transaction_id = data.get("m_payment_id")
    if not transaction_id:
        frappe.log_error(
            "PayFast callback received without m_payment_id", data
        )
        return

    transaction = frappe.get_doc(
        "Transaction", {"payment_reference": transaction_id}
    )

    payfast_settings = frappe.get_doc("PaaS Payment Gateway", "PayFast")
    settings = {s.key: s.value for s in payfast_settings.settings}

    passphrase = settings.get("pass_phrase")

    pf_param_string = ""
    for key in sorted(data.keys()):
        if key != "signature":
            pf_param_string += f"{key}={data[key]}&"

    pf_param_string = pf_param_string[:-1]

    if passphrase:
        pf_param_string += f"&passphrase={passphrase}"

    signature = frappe.utils.md5_hash(pf_param_string)

    if signature != data.get("signature"):
        frappe.log_error("PayFast callback signature mismatch", data)
        transaction.status = "Failed"
        transaction.save(ignore_permissions=True)
        return

    if data.get("payment_status") == "COMPLETE":
        transaction.status = "Paid"
        order = frappe.get_doc("Order", transaction.payable_id)
        order.status = "Paid"
        order.save(ignore_permissions=True)
    elif data.get("payment_status") == "FAILED":
        transaction.status = "Failed"
    else:
        transaction.status = "Canceled"

    transaction.save(ignore_permissions=True)


@frappe.whitelist()
def process_payfast_token_payment(order_id: str, token: str) -> Any:
    """
    Processes a payment using a saved PayFast token.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    frappe.throw("Token payment not yet implemented.")


@frappe.whitelist()
def save_payfast_card(token: str, card_details: str) -> Any:
    """
    Saves a PayFast card token.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to save a card.")

    if isinstance(card_details, str):
        card_details = json.loads(card_details)

    frappe.get_doc(
        {
            "doctype": "Saved Card",
            "user": user,
            "token": token,
            "last_four": card_details.get("last_four"),
            "card_type": card_details.get("card_type"),
            "expiry_date": card_details.get("expiry_date"),
            "card_holder_name": card_details.get("card_holder_name"),
        }
    ).insert(ignore_permissions=True)
    return {"status": "success", "message": "Card saved successfully."}


@frappe.whitelist()
def get_saved_payfast_cards() -> Any:
    """
    Retrieves a list of saved cards for the current user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to view your saved cards.")

    return frappe.get_all(
        "Saved Card",
        filters={"user": user},
        fields=["name", "last_four", "card_type", "expiry_date"],
    )


@frappe.whitelist()
def delete_payfast_card(card_name: str) -> Any:
    """
    Deletes a saved card.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to delete a card.")

    card = frappe.get_doc("Saved Card", card_name)
    if card.user != user:
        frappe.throw(
            "You are not authorized to delete this card.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Saved Card", card_name, ignore_permissions=True)
    return {"status": "success", "message": "Card deleted successfully."}


@frappe.whitelist(allow_guest=True)
def handle_paypal_callback() -> Any:
    """
    Handles the PayPal payment callback.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    data = frappe.form_dict

    token = data.get("token")
    if not token:
        frappe.log_error("PayPal callback received without token", data)
        return

    transaction = frappe.get_doc("Transaction", {"payment_reference": token})

    paypal_settings_doc = frappe.get_doc("PaaS Payment Gateway", "PayPal")
    settings = {s.key: s.value for s in paypal_settings_doc.settings}
    success_url = (
        paypal_settings_doc.success_redirect_url or "/payment-success"
    )
    failure_url = paypal_settings_doc.failure_redirect_url or "/payment-failed"

    auth_url = (
        "https://api-m.sandbox.paypal.com/v1/oauth2/token"
        if settings.get("paypal_mode") == "sandbox"
        else "https://api-m.paypal.com/v1/oauth2/token"
    )
    client_id = (
        settings.get("paypal_sandbox_client_id")
        if settings.get("paypal_mode") == "sandbox"
        else settings.get("paypal_live_client_id")
    )
    client_secret = (
        settings.get("paypal_sandbox_client_secret")
        if settings.get("paypal_mode") == "sandbox"
        else settings.get("paypal_live_client_secret")
    )

    auth_response = requests.post(
        auth_url,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    auth_response.raise_for_status()
    access_token = auth_response.json()["access_token"]

    order_url = (
        f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{token}"
        if settings.get("paypal_mode") == "sandbox"
        else f"https://api-m.paypal.com/v2/checkout/orders/{token}"
    )

    order_response = requests.get(
        order_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        timeout=10,
    )
    order_response.raise_for_status()
    paypal_order = order_response.json()

    if paypal_order.get("status") == "COMPLETED":
        transaction.status = "Paid"
        order = frappe.get_doc("Order", transaction.payable_id)
        order.status = "Paid"
        order.save(ignore_permissions=True)
        transaction.save(ignore_permissions=True)
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = success_url
    else:
        transaction.status = "Failed"
        transaction.save(ignore_permissions=True)
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = failure_url


@frappe.whitelist()
def initiate_paypal_payment(order_id: str) -> Any:
    """
    The initiate_paypal_payment function initiates a PayPal payment for a specific order. It takes one parameter, order_id, which is a string representing the unique identifier of the order for which the payment is being initiated. This function serves as a wrapper around the core PayPal payment logic, providing a simple and straightforward way to start the payment process for a given order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return _initiate_paypal_logic("Order", order_id)


@frappe.whitelist()
def initiate_paypal_parcel_payment(order_id: str) -> Any:
    """
    Initiate paypal parcel payment API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return _initiate_paypal_logic("Parcel Order", order_id)


def _initiate_paypal_logic(doctype: str, docname: str):
    """
    Internal logic for PayPal initiation across different doctypes.
    """
    doc = frappe.get_doc(doctype, docname)

    paypal_settings_doc = frappe.get_doc("PaaS Payment Gateway", "PayPal")
    settings = {s.key: s.value for s in paypal_settings_doc.settings}
    success_url = paypal_settings_doc.success_redirect_url or f"{
        frappe.utils.get_url()}/api/method/paas.api.handle_paypal_callback"
    failure_url = paypal_settings_doc.failure_redirect_url or f"{
        frappe.utils.get_url()}/api/method/paas.api.handle_paypal_callback"

    auth_url = (
        "https://api-m.sandbox.paypal.com/v1/oauth2/token"
        if settings.get("paypal_mode") == "sandbox"
        else "https://api-m.paypal.com/v1/oauth2/token"
    )
    client_id = (
        settings.get("paypal_sandbox_client_id")
        if settings.get("paypal_mode") == "sandbox"
        else settings.get("paypal_live_client_id")
    )
    client_secret = (
        settings.get("paypal_sandbox_client_secret")
        if settings.get("paypal_mode") == "sandbox"
        else settings.get("paypal_live_client_secret")
    )

    auth_response = requests.post(
        auth_url,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    auth_response.raise_for_status()
    access_token = auth_response.json()["access_token"]

    order_url = (
        "https://api-m.sandbox.paypal.com/v2/checkout/orders"
        if settings.get("paypal_mode") == "sandbox"
        else "https://api-m.paypal.com/v2/checkout/orders"
    )

    amount = doc.get("total_price") or doc.get("grand_total") or 0
    currency = doc.get("currency") or "USD"

    order_payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {"amount": {"currency_code": currency, "value": str(amount)}}
        ],
        "experience_context": {
            "return_url": success_url,
            "cancel_url": failure_url,
        },
    }

    order_response = requests.post(
        order_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json=order_payload,
        timeout=10,
    )
    order_response.raise_for_status()
    paypal_order = order_response.json()

    frappe.get_doc(
        {
            "doctype": "Transaction",
            "payable_type": doctype,
            "payable_id": doc.name,
            "payment_reference": paypal_order["id"],
            "amount": amount,
            "status": "Pending",
        }
    ).insert(ignore_permissions=True)

    approval_link = next(
        (
            link["href"]
            for link in paypal_order["links"]
            if link["rel"] == "approve"
        ),
        None,
    )

    if not approval_link:
        frappe.throw("Could not find PayPal approval link.")

    return {"redirect_url": approval_link}


@frappe.whitelist()
def initiate_paystack_payment(order_id: str) -> Any:
    """
    The initiate_paystack_payment function initiates a payment process through Paystack for a specific order. It takes one parameter, order_id, which is a string representing the unique identifier of the order for which the payment is being initiated. This function serves as a gateway to trigger the underlying payment logic, passing the order type as "Order" and the provided order_id to the _initiate_paystack_logic function for further processing.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return _initiate_paystack_logic("Order", order_id)


@frappe.whitelist()
def initiate_paystack_parcel_payment(order_id: str) -> Any:
    """
    Initiate paystack parcel payment API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return _initiate_paystack_logic("Parcel Order", order_id)


def _initiate_paystack_logic(doctype: str, docname: str):
    """
    Internal logic for PayStack initiation across different doctypes.
    """
    doc = frappe.get_doc(doctype, docname)

    paystack_settings = frappe.get_doc("PaaS Payment Gateway", "PayStack")
    settings = {s.key: s.value for s in paystack_settings.settings}

    headers = {
        "Authorization": f"Bearer {settings.get('paystack_sk')}",
        "Content-Type": "application/json",
    }

    amount = doc.get("total_price") or doc.get("grand_total") or 0

    body = {
        "email": frappe.session.user,
        "amount": int(
            amount * 100),
        "currency": doc.get("currency") or "ZAR",
        "callback_url": f"{
            frappe.utils.get_url()}/api/method/paas.api.handle_paystack_callback",
    }

    response = requests.post(
        "https://api.paystack.co/transaction/initialize",
        headers=headers,
        json=body,
        timeout=10,
    )
    response.raise_for_status()
    paystack_data = response.json()

    # Create a new transaction
    frappe.get_doc(
        {
            "doctype": "Transaction",
            "payable_type": doctype,
            "payable_id": doc.name,
            "payment_reference": paystack_data["data"]["reference"],
            "amount": amount,
            "status": "Pending",
        }
    ).insert(ignore_permissions=True)

    return {"redirect_url": paystack_data["data"]["authorization_url"]}


@frappe.whitelist(allow_guest=True)
def handle_paystack_callback() -> Any:
    """
    Handles the PayStack payment callback.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    data = frappe.form_dict
    reference = data.get("reference")

    if not reference:
        frappe.log_error("PayStack callback received without reference", data)
        return

    paystack_settings = frappe.get_doc("PaaS Payment Gateway", "PayStack")
    settings = {s.key: s.value for s in paystack_settings.settings}

    headers = {
        "Authorization": f"Bearer {settings.get('paystack_sk')}",
    }

    response = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    paystack_data = response.json()

    if paystack_data["data"]["status"] == "success":
        transaction = frappe.get_doc(
            "Transaction", {"payment_reference": reference}
        )
        transaction.status = "Paid"
        transaction.save(ignore_permissions=True)

        order = frappe.get_doc("Order", transaction.payable_id)
        order.status = "Paid"
        order.save(ignore_permissions=True)
    else:
        transaction = frappe.get_doc(
            "Transaction", {"payment_reference": reference}
        )
        transaction.status = "Failed"
        transaction.save(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def log_payment_payload(payload: Any) -> Any:
    """
    Logs a payment payload.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    frappe.get_doc({"doctype": "Payment Payload", "payload": payload}).insert(
        ignore_permissions=True
    )
    return {"status": "success"}


@frappe.whitelist(allow_guest=True)
def handle_stripe_webhook() -> Any:
    """
    Handles the Stripe payment webhook.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    # TODO: Implement Stripe webhook logic
    return {"status": "success"}


@frappe.whitelist()
def get_saved_cards() -> Any:
    """
    The get_saved_cards function retrieves a list of saved credit cards associated with the currently logged-in user. It first checks if the user is logged in, throwing an error if they are a guest. If the user is authenticated, it queries the system for a list of saved cards linked to the user's account, returning a list of card objects containing details such as the card name, payment gateway, token, last four digits, card type, expiry date, and card holder's name.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to view your saved cards.")

    cards = frappe.get_list(
        "Saved Card",
        filters={"user": user},
        fields=[
            "name",
            "gateway",
            "token",
            "last_four",
            "card_type",
            "expiry_date",
            "card_holder_name",
        ],
    )
    return cards


@frappe.whitelist()
def tokenize_card(card_number: Any, card_holder: Any, expiry_date: Any, cvc: Any) -> Any:
    """
    The tokenize_card function is used to securely store a user's credit card information. It takes four parameters: card_number, card_holder, expiry_date, and cvc, which represent the credit card number, card holder's name, expiration date, and card verification code, respectively. The function generates a unique token for the saved card and returns a dictionary containing the token, saved card name, last four digits of the card number, card type, and expiration date. The function requires the user to be logged in and automatically detects the card type based on the card number.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to save a card.")

    import uuid

    token = str(uuid.uuid4())

    def detect_card_type(card_number):
        if card_number.startswith("4"):
            return "Visa"
        elif card_number.startswith(("51", "52", "53", "54", "55")):
            return "Mastercard"
        elif card_number.startswith(("34", "37")):
            return "American Express"
        else:
            return "Card"

    card_type = detect_card_type(card_number)
    last_four = card_number[-4:]

    saved_card = frappe.get_doc(
        {
            "doctype": "Saved Card",
            "user": user,
            "token": token,
            "last_four": last_four,
            "card_type": card_type,
            "expiry_date": expiry_date,
            "card_holder_name": card_holder,
        }
    )
    saved_card.insert(ignore_permissions=True)

    return {
        "token": token,
        "name": saved_card.name,
        "last_four": last_four,
        "card_type": card_type,
        "expiry_date": expiry_date,
    }


@frappe.whitelist()
def delete_card(card_name: Any) -> Any:
    """
    The delete_card function is used to remove a saved card from the system. It takes one parameter, card_name, which specifies the name of the card to be deleted. The function first checks if the current user is logged in, throwing an error if they are a guest. It then verifies that the user attempting to delete the card is the same user who saved it, throwing a permission error if they are not authorized. If both checks pass, the function deletes the specified card and returns a success status.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to delete a card.")

    card = frappe.get_doc("Saved Card", card_name)
    if card.user != user:
        frappe.throw(
            "You are not authorized to delete this card.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Saved Card", card_name, ignore_permissions=True)
    return {"status": "success"}


@frappe.whitelist()
def process_direct_card_payment(order_id: Any, card_number: Any, card_holder: Any, expiry_date: Any, cvc: Any, save_card: Any=False) -> Any:
    """
    The process_direct_card_payment function facilitates direct card payments for a specific order. It takes in several parameters: order_id, which identifies the order being paid for, card_number, card_holder, expiry_date, and cvc, which are the card details used for payment. The save_card parameter is optional and defaults to False, indicating whether the card should be saved for future transactions. The function first verifies the user's login status and order ownership, then creates a new transaction record, updates the order status to Paid, and optionally tokenizes the card for future use. It returns a dictionary containing the status of the payment and the transaction ID.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to make a payment.")

    order = frappe.get_doc("Order", order_id)
    if order.user != user:
        frappe.throw(
            "You can only pay for your own orders.", frappe.PermissionError
        )

    transaction = frappe.get_doc(
        {
            "doctype": "Transaction",
            "user": user,
            "payable_type": "Order",
            "payable_id": order_id,
            "amount": order.grand_total,
            "status": "Paid",
        }
    )
    transaction.insert(ignore_permissions=True)

    if save_card:
        tokenize_card(card_number, card_holder, expiry_date, cvc)

    order.status = "Paid"
    order.save()

    return {"status": "success", "transaction_id": transaction.name}


def _charge_card_token(token, amount, currency, description, user):
    """
    Internal helper to charge a saved card token via the appropriate gateway.
    """
    saved_card_name = frappe.db.get_value(
        "Saved Card", {"token": token, "user": user}
    )
    if not saved_card_name:
        frappe.throw("Invalid or unauthorized token.", frappe.PermissionError)

    saved_card = frappe.get_doc("Saved Card", saved_card_name)
    gateway_name = (
        saved_card.gateway or "PayFast"
    )  # Default to PayFast for legacy

    if gateway_name == "Flutterwave":
        return _charge_flutterwave_token(
            token, amount, currency, description, user
        )
    elif gateway_name == "PayFast":
        return _charge_payfast_token(token, amount, currency, description)
    else:
        # Fallback to local simulation if no production gateway is matched,
        # but log a warning as this shouldn't happen in production.
        frappe.log_error(
            f"Unsupported gateway {gateway_name} for token charge.",
            "Payment Warning",
        )
        return {
            "status": "success",
            "message": "Simulated success (Unconfigured Gateway)",
        }


def _charge_flutterwave_token(token, amount, currency, description, user):
    trace_id = None
    """
    Executes a tokenized charge via Flutterwave.
    """
    settings = frappe.get_doc("Flutterwave Settings")
    if not settings.enabled:
        frappe.throw("Flutterwave payments are not enabled.")

    url = "https://api.flutterwave.com/v3/tokenized-charges"
    headers = {
        "Authorization": f"Bearer {settings.get_password('secret_key')}",
        "Content-Type": "application/json",
    }

    user_email = frappe.db.get_value("User", user, "email")

    payload = {
        "token": token,
        "currency": currency,
        "amount": amount,
        "email": user_email,
        "tx_ref": f"pay-{frappe.utils.generate_hash()[:10]}",
        "narrative": description,
    }

    try:
        response = requests.post(
            url, json=payload, headers=headers, timeout=30
        )
        response.raise_for_status()
        res_data = response.json()
        if res_data.get("status") == "success":
            return res_data
        else:
            frappe.throw(f"Flutterwave Error: {res_data.get('message')}")
    except Exception:
        frappe.log_error(
            frappe.get_traceback(), "Flutterwave Token Charge Failed"
        )
        frappe.throw(
            "Card payment failed. Please check your card balance or try another card."
        )


def _charge_payfast_token(token, amount, currency, description):
    """
    Executes a tokenized charge via PayFast (Ad Hoc Subscription pattern).
    Uses the v1 subscriptions charge API with proper signature generation.
    """
    settings = get_payfast_settings()
    is_sandbox = settings.get("is_sandbox", True)
    base_url = (
        "api.payfast.co.za" if not is_sandbox else "sandbox.payfast.co.za"
    )

    merchant_id = settings.get("merchant_id")
    _merchant_key = settings.get("merchant_key")  # noqa: F841
    pass_phrase = settings.get("pass_phrase")

    # Ad-hoc charge endpoint
    url = f"https://{base_url}/subscriptions/{token}/adhoc"
    if is_sandbox and not url.endswith(
        "/api"
    ):  # Sandbox API is usually under /api
        url = f"https://sandbox.payfast.co.za/api/subscriptions/{token}/adhoc"

    # PayFast API requires amount in cents for adhoc charges
    amount_in_cents = int(float(amount) * 100)

    # 1. Prepare base parameters
    params = {
        "merchant-id": merchant_id,
        "version": "v1",
        "timestamp": frappe.utils.now_datetime().strftime("%Y-%m-%dT%H:%M:%S"),
    }

    # 2. Add body parameters (these are also signed)
    body = {
        "amount": amount_in_cents,
        "item_name": description,
        "m_payment_id": frappe.utils.generate_hash()[:10],
    }

    # 3. Generate Signature
    # According to PayFastCardService.php:
    # a) Merge base params with body
    all_params = {**params, **body}
    # b) Initial Sort
    _keys_sorted = sorted(all_params.keys())  # noqa: F841

    # c) Add passphrase (if exists) after initial sort but then sort AGAIN
    signature_params = all_params.copy()
    if pass_phrase:
        signature_params["passphrase"] = pass_phrase

    final_sorted_keys = sorted(signature_params.keys())

    # d) Build query string
    from urllib.parse import urlencode

    # PayFast expects standard urlencoding for the signature string
    signature_string = "&".join(
        [
            f"{k}={urlencode(str(signature_params[k]))}"
            for k in final_sorted_keys
        ]
    )

    import hashlib

    # nosec B324 - PayFast API requires MD5
    signature = hashlib.md5(signature_string.encode("utf-8")).hexdigest()

    # 4. Prepare Headers
    headers = {
        "merchant-id": merchant_id,
        "version": "v1",
        "timestamp": params["timestamp"],
        "signature": signature,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(url, json=body, headers=headers, timeout=30)
        res_data = response.json() if response.text else {}

        if (
            response.status_code in [200, 202]
            and res_data.get("status") == "success"
        ):
            return res_data
        else:
            error_msg = res_data.get("data", {}).get(
                "response", "Unknown PayFast Error"
            )
            frappe.log_error(f"PayFast API Error ({
                response.status_code}): {
                response.text}", "PayFast Token Charge Failed")
            frappe.throw(f"Payment failed: {error_msg}")

    except Exception:
        frappe.log_error(
            frappe.get_traceback(), "PayFast Token Charge Exception"
        )
        frappe.throw("Error connecting to payment gateway.")


@frappe.whitelist()
def process_token_payment(order_id: Any, token: Any) -> Any:
    """
    The process_token_payment function facilitates payment processing for a specific order using a provided token. It takes two parameters: order_id, which identifies the order being paid for, and token, which represents the payment method. The function first verifies that the user is logged in and has permission to pay for the specified order. It then initiates a payment charge using the provided token and updates the order status to "Paid" if the payment is successful. The function returns the result of the payment processing operation.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to make a payment.")

    order = frappe.get_doc("Order", order_id)
    if order.user != user:
        frappe.throw(
            "You can only pay for your own orders.", frappe.PermissionError
        )

    currency = (
        frappe.db.get_single_value("System Settings", "currency") or "ZAR"
    )
    description = f"Payment for Order {order_id}"

    # Call the internal helper to process the charge
    result = _charge_card_token(
        token=token,
        amount=order.grand_total,
        currency=currency,
        description=description,
        user=user,
    )

    # If successful, update order status
    if result.get("status") == "success":
        order.payment_status = "Paid"
        order.save(ignore_permissions=True)
        frappe.db.commit()

    return result


@frappe.whitelist()
def tip_process(order_id: str, tip_amount: float) -> Any:
    """
    Processes a tip for an order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to leave a tip.")

    order = frappe.get_doc("Order", order_id)
    if order.user != user:
        frappe.throw(
            "You are not authorized to tip for this order.",
            frappe.PermissionError,
        )

    if (
        order.status == "Delivered"
    ):  # Tipping usually AFTER delivery or during rating
        # Logic to add tip to order or create a separate transaction
        # For now, we update the order's tip field
        order.tip_amount = tip_amount
        order.total_price += tip_amount  # Update total? Or keep separate?
        order.save(ignore_permissions=True)

        # If already paid, might need to charge the tip separately.
        # This implementation assumes it's added before payment or just recorded.
        # If separate charge needed:
        # charge_token(user_token, tip_amount)

        return {"status": "success", "message": "Tip added successfully."}
    else:
        frappe.throw(
            "Tips can only be added to delivered orders (conceptually)."
        )

    transaction = frappe.get_doc(
        {
            "doctype": "Transaction",
            "user": user,
            "reference_doctype": "Order",
            "reference_docname": order_id,
            "amount": order.grand_total,
            "status": "Success",
        }
    )
    transaction.insert(ignore_permissions=True)

    order.status = "Paid"
    order.save()

    return {"status": "success", "transaction_id": transaction.name}


@frappe.whitelist()
def process_wallet_top_up(amount: Any, token: Any=None) -> Any:
    """
    The process_wallet_top_up function is used to top up a user's wallet with a specified amount. It takes two parameters: amount, which is the amount to be added to the wallet, and token, which is the payment token used for the transaction. The token parameter is optional but required to complete the top-up process. If the token is not provided, the function will throw an error. The function first checks if the user is logged in and then executes the charge via a payment gateway. After a successful charge, it creates a new transaction record and updates the user's wallet balance. The function returns a dictionary with a status of 'success' and the transaction ID.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to top up your wallet.")

    if not token:
        frappe.throw("A payment token is required to top up your wallet.")

    # Execute actual charge via gateway
    _charge_card_token(
        token=token,
        amount=amount,
        currency=frappe.db.get_single_value("System Settings", "currency")
        or "ZAR",
        description=f"Wallet Top-up for {user}",
        user=user,
    )

    transaction = frappe.get_doc(
        {
            "doctype": "Transaction",
            "user": user,
            "reference_doctype": "User",
            "reference_docname": user,
            "amount": amount,
            "status": "Success",
            "type": "Wallet Top-up",
        }
    )
    transaction.insert(ignore_permissions=True)

    user_doc = frappe.get_doc("User", user)
    user_doc.set(
        "wallet_balance", (user_doc.get("wallet_balance") or 0) + float(amount)
    )
    user_doc.save()

    return {"status": "success", "transaction_id": transaction.name}


@frappe.whitelist()
def process_wallet_payment(order_id: Any) -> Any:
    """
    The process_wallet_payment function is used to deduct payment from a user's wallet for a specific order. It takes one parameter, order_id, which is the unique identifier of the order being paid for. The function first checks if the user is logged in and has permission to pay for the order, then verifies if the user's wallet balance is sufficient to cover the order's grand total. If the balance is sufficient, it deducts the payment amount from the user's wallet, creates a new transaction record, and updates the order's payment status to "Paid".
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Deducts payment from User's wallet.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in.")

    order = frappe.get_doc("Order", order_id)
    if order.user != user:
        frappe.throw("Unauthorized.", frappe.PermissionError)

    user_doc = frappe.get_doc("User", user)
    balance = user_doc.wallet_balance or 0.0

    if balance < order.grand_total:
        frappe.throw("Insufficient Wallet Balance.")

    # Deduct
    user_doc.wallet_balance = balance - order.grand_total
    user_doc.save(ignore_permissions=True)

    # Transaction
    transaction = frappe.get_doc(
        {
            "doctype": "Transaction",
            "user": user,
            "reference_doctype": "Order",
            "reference_docname": order_id,
            "amount": -order.grand_total,
            "status": "Success",
            "type": "Debit",
        }
    )
    transaction.insert(ignore_permissions=True)

    order.payment_status = "Paid"
    order.save()

    return {"status": "success"}
