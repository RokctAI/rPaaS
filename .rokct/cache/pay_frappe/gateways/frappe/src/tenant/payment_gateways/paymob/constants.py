class AcceptCallbackTypes:
	TRANSACTION = "TRANSACTION"
	CARD_TOKEN = "TOKEN"  # compliance-ignore: py-hardcoded-secret (Paymob callback-type enum label, not a credential)
	DELIVERY_STATUS = "DELIVERY_STATUS"
