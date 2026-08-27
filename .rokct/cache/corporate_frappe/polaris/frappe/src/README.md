# Polaris Frappe Module — Source Layout

Backend source for the Polaris lending module. Source is organised by
persona folder (`src/tenant/`, with an empty `control` flavor declared in
`../manifest.json`). At compose time (`compose_backend.py`), persona content
is copied into the composed app's module package with the persona segment in
the dotted path, so a file here at `src/tenant/api/loan.py` becomes
importable as `<app>.polaris.tenant.api.loan`. Doctypes under
`src/tenant/doctype/` are relocated to module root
(`<app>.polaris.doctype.*`) per the composer doctype-relocation convention.

## Layout (under `tenant/`)

- **`api/`** — Whitelisted endpoint modules. Clients never call these dotted
  paths directly for the lending flows: the platform gateway resolves the
  stable command keys (`{app_name}.api.lending.*`, declared in
  `../manifest.json`) to these implementations.
  - `decision.py` — credit-score endpoint (`get_credit_score`).
  - `loan.py` — disbursement (`disburse_loan`).
  - `product.py` — loan product listing.
  - `lending_mocks.py` — eligibility/application flow endpoints.
- **`decision_engine/`** — Credit-scoring engine: `scorecard.py` (pure-python
  scoring core, unit-tested locally), `analyzers/` (loan-history and PaaS
  order analyzers), `seeds.py` (Scoring Rule / Risk Profile seed data),
  `engine.py`.
- **`gl_posting.py`** — General-ledger posting helpers used by the loan
  doctypes and wallet integration.
- **`wallet_integration.py`** — `doc_events` handlers (Loan Disbursement /
  Loan Repayment `on_submit`) that credit/debit the customer wallet.
- **`asset_realisation.py`** — Pledged-asset realisation and release
  (`release_security` is also exposed via a manifest command key).
- **`tests/`** — Test suites. Most are FrappeTestCase suites with templated
  `{app_name}` imports that only run post-compose against a bench;
  `test_credit_scorecard.py` is pure python and runs directly in this repo.
- **`fixtures/`** — Seed fixtures (subscription plans, items).

## History

This code originally lived in a separate `rlending/` overlay directory here,
because it extended the upstream `frappe/lending` app we did not own. Polaris
is now our owned fork of that lending stack, so the overlay was folded into
the module proper and the `rlending/` directory removed. The API contract was
not changed by that fold: the manifest command keys
(`{app_name}.api.lending.*`) and `doc_events` are identical — only the
implementation dotted paths moved (`<app>.polaris.rlending.*` →
`<app>.polaris.*`, now `<app>.polaris.tenant.*` after the persona-folder
move).
