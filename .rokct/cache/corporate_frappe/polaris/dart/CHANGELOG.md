## 1.1.1

* Routed the loans repository's broken `paas.api.*` call strings through
  base_sdk's universal platform gateway (`PlatformGateway`, per the
  2026-08-15 fleet rule). The lending endpoints
  (`create_loan_application`, `check_loan_eligibility`,
  `check_loan_history_eligibility`, `mark_application_as_rejected`,
  `check_financial_eligibility`, `save_incomplete_loan_application`,
  `fetch_saved_application`, `fetch_saved_applications`, `disburse_loan`,
  `get_my_loan_applications`) become prefix-free `api.lending.*` gateway
  cmds mirroring polaris's own `manifest.json` whitelisted-method keys —
  the old short `paas.api.<fn>` strings were not registered names and
  404'd on composed backends. Wallet history moves to
  `api.user.get_wallet_history` (users manifest key) instead of the
  unregistered `paas.api.user.user.get_wallet_history`, and PayFast
  settings to `api.payment.get_payfast_settings` (pay wallet manifest
  key) instead of `paas.api.payment.payment.get_payfast_settings`.
* `request_payout` is left untouched: no lending payout endpoint exists
  server-side (the only registered `request_payout` is the merchants
  seller payout, which takes `amount`, not `loan_application`) — needs a
  backend before the client string can be fixed.

## 0.0.1

* TODO: Describe initial release.
