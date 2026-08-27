# compliance-ignore-file: ztna-authz (static dashboard link config; no auth/API surface)
def get_data():
	return {
		"fieldname": "payment_gateway_account",
		"non_standard_fieldnames": {"Subscription Plan": "payment_gateway"},
		"transactions": [{"items": ["Payment Request"]}, {"items": ["Subscription Plan"]}],
	}
