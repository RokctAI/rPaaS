# gateways/local — Rokct-authored additions to the ported `gateways` module

Everything under `gateways/frappe/` is **generated** by
`gateways/port/port_payments.py`, which wipes and regenerates
`gateways/frappe/doctype/`, `gateways/frappe/src/` and
`gateways/frappe/manifest.json` from the pinned upstream
(Frappenize/payments@rokct) on every run.

This directory is the **source of truth for Rokct-authored files** that ship
inside that generated tree. The port script's final overlay step copies
`local/doctype/**` and `local/src/**` byte-for-byte into the corresponding
positions under `gateways/frappe/`, merges `local/manifest_hooks.json` into
the generated manifest's `hooks`, and records everything it overlaid in
`gateways/port/port_report.json["local_additions"]`. A path that collides
with a ported upstream file is a hard error.

So: **edit files here, then re-run the port script** — never hand-edit the
copies under `gateways/frappe/`, they are overwritten on the next run.

Current contents (moved from the retired `payments/frappe` module, composed
Frappe module name `pay`):

- `doctype/payfast_settings/` — **PayFast Settings** (singleton), rewritten
  to the upstream gateway-controller convention: `validate()` calls
  `create_payment_gateway("PayFast")` with no `gateway_controller` (so
  `get_payment_gateway_controller` resolves `frappe.get_doc("PayFast
  Settings")`), plus `supported_currencies` /
  `validate_transaction_currency` for erp's Payment Request.
- `doctype/paystack_settings/` — **Paystack Settings** (singleton), same
  convention.
- `src/templates/pages/paystack_checkout.{html,py}` — the Paystack inline-JS
  checkout page (`get_payment_url` returns `/paystack_checkout?token=...`).
- `src/tests/test_payfast_settings.py` — PayFast URL-generation test.
- `manifest_hooks.json` — DocType fixtures for both settings doctypes,
  merged into the generated `gateways/frappe/manifest.json`.

These files are Rokct-authored (MIT, RokctAI headers), unlike the ported
upstream files which keep Frappe Technologies' headers verbatim. The repo's
license-header check ignores `gateways/**` wholesale (`.licenserc.yaml`), so
both header styles coexist here unchecked.
