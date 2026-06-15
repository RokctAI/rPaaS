# API Reference: platform_wallet

Source file: `paas/paas/doctype/platform_wallet/platform_wallet.py`

## Classes

### class `PlatformWallet`

#### Whitelisted API Methods
##### `request_payout(self, amount)`
<!-- 163d933f11525f6b4ab9280b6e1df8a42bb27aca11ed3114f06d4f4c0528f945 -->
The request_payout function initiates a payout request for a specified amount. It takes two parameters: self, a reference to the instance of the class, and amount, the amount to be requested for payout. The function first checks if the lending feature is enabled in the system's Permission Settings. If enabled, it constructs an API request to the control plane URL with the provided amount and sends it using a POST request. The function returns the response from the API if the request is successful, or throws an error if the request fails.
