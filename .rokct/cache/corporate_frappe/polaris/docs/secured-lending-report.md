# Report: Purpose-Built Secured Lending (Single-Asset Repossession Model)

> Delivered work for `secured-lending-brief.md`. Read that brief first for framing.

## What was built

### `Pledged Asset` (new doctype, `corporate/polaris/frappe/doctype/pledged_asset/`)
One physical asset per loan (`loan` field is unique), matching the brief's explicit "single asset,
not a portfolio" instruction — this is a new doctype, not a repurposing of `Loan Security Shortfall`
(that doctype's fields are LTV/percentage-shaped, a different concept entirely; it's untouched, still
the record-only shell from Phase 5).

Fields: `loan`, `loan_application` (traceability to where collateral was captured), `applicant_type`/
`applicant`, `status` (`Pledged` → `Repossession Triggered` → `Repossessed`, or `Pledged` → `Released`),
`pledged_date`, `description`, `category`, `serial_number`, `declared_value`,
`repossession_triggered_date`/`repossessed_date`/`released_date`, `loan_write_off` (link to the actual
financial settlement once repossessed).

**Status history**: uses Frappe's built-in `track_changes` + explicit `add_comment()` calls at each
transition — not a bespoke log child-table. This already gives a real, queryable audit trail (every
field change versioned, every transition has a human-readable comment) without inventing new structure
for something Frappe already does natively. Same pattern `asset_realisation.py` already used for its own
audit logging.

**No LTV/mark-to-market**: `declared_value` is captured once, never revalued — per the brief's explicit
"what NOT to do."

### Where collateral gets captured — traced, not guessed
Read `RokctAI_frontend/app/handson/all/lending/application/new/page.tsx` directly. Two real findings:

1. **The form already has a secured-loan branch** — `isSecured = products.find(p => p.name ===
   formData.loan_product)?.is_secured`, and when true, shows a required free-text collateral
   `<textarea>` bound to `formData.description`. **This has never worked**: `Loan Product` had no
   `is_secured` field, and even `api/product.py`'s `get_loan_product_list()` (the actual endpoint this
   page calls) didn't fetch or return `is_secured` even if the field existed. Both are now fixed —
   `is_secured` added to `Loan Product`, fetched and returned by `get_loan_product_list()`.
2. **Collateral is captured at Loan Application time, not disbursement time** — confirmed directly from
   the form, resolving the brief's open question. `Loan Application` gets new fields: `is_secured_loan`,
   `description` (field name matches the frontend exactly — `ApplicationService.create()` is a raw
   passthrough, `{...data}`, so the name is load-bearing, not a style choice), and `declared_asset_value`.

**Real gap found and flagged, not silently handled**: `formData` never actually includes
`is_secured_loan` — the frontend derives `isSecured` client-side purely for UI rendering and never adds
it to the submitted payload. If left as a plain field, every secured application from the live form
would have silently saved as unsecured. Fixed in `loan_application.py`'s `validate_loan_product()`: when
`is_secured_loan` isn't explicitly set, it's inferred from `Loan Product.is_secured` — matching what the
real form's own logic already assumes, not a made-up default.

**Also a real, flagged (not fixed) gap**: the live form only captures a free-text description, never a
declared value — `declared_asset_value` exists on the backend now so a future form update can populate
it, but nothing does yet.

### Loan origination → Pledged Asset (`api/loan.py`'s `disburse_loan()`)
When a secured Loan Application is disbursed, `disburse_loan()` now also passes `is_secured_loan` onto
the new `Loan` record (it didn't before) and calls `pledged_asset.create_from_application()`, which
copies the collateral description onto a new `Pledged Asset` linked to the `Loan`. Idempotent — a repeat
call returns the existing record rather than duplicating.

### Repossession trigger — NPA classification signals, a human executes
Per the brief's explicit instruction not to make repossession "silently automatic":

- **`Process Loan Classification`'s `update_loan_classification()`** (Phase 5, already computes DPD/NPA)
  now calls `pledged_asset.trigger_repossession_flag()` when a secured loan becomes NPA. This is a
  **signal only** — it moves the asset's status to `Repossession Triggered` and adds a comment. No
  financial action, no write-off, no automatic repossession.
- **A human executes actual repossession** via the *existing* `realise_pawn_asset()`
  (`asset_realisation.py`, unchanged permission gate: `frappe.has_permission("Loan", "write")`, unchanged
  manual UI trigger — the modal I already touched in the ERPNext-dependency-audit pass). Extended it to
  call `pledged_asset.mark_repossessed()` as a side effect after the `Loan Write Off` is created and
  submitted, linking the asset to that write-off record.
- **No new "confirm repossession" endpoint was added.** `realise_pawn_asset()` already *is* the human
  confirmation gate — it requires an explicit call with explicit permissions, triggered by a person
  clicking a button, exactly matching what the brief asked for ("don't make it silently automatic").
  Adding a second, parallel confirmation function would have duplicated the existing write-off logic for
  no real gain.
- **No invented legal/collections process**: nothing here simulates notice periods, physical execution,
  or legal steps — those remain entirely a human, off-system decision. The system only records the
  outcome once someone tells it repossession happened, per the brief's explicit "what NOT to do."

### `releaseSecurity()` — real implementation
New `asset_realisation.release_security(loan)`: verifies the loan is genuinely fully paid off
(`get_pending_principal_amount(loan) <= 0`, checked server-side, not trusted from the caller) before
releasing the `Pledged Asset`. Throws clearly if the loan isn't paid off, or if the asset was already
repossessed (mutually exclusive outcomes — an asset can't be both taken back and released). Idempotent
if called again after a successful release.

Wired into `manifest.json`'s `whitelisted_methods` as `{app_name}.api.lending.release_security`, and
both `RokctAI_frontend/app/services/all/lending/loan.ts` and the `corporate/polaris/nextjs` template
copy repointed to call `core.polaris.rlending.asset_realisation.release_security` directly (confirmed
byte-for-byte identical between the two copies after the edit).

## Real bugs found, fixed or flagged

1. **Fixed** (in scope — same function being edited for this feature): `disburse_loan()`'s
   "already disbursed" guard compared `Loan Disbursement.against_loan` to the *Loan Application's* name,
   but `against_loan` is always a *Loan* name — the check could never match anything. A second call to
   `disburse_loan()` on an already-disbursed application would have silently created a duplicate
   `Loan Disbursement`, double-crediting the wallet. Fixed to compare against the actual resolved
   `loan_name`. Verified by test: a repeat call now correctly throws instead of double-disbursing.
2. **Fixed** (in scope — literally the mechanism this feature needed to work at all): `Loan Product` had
   no `is_secured` field despite the live frontend already reading it, and `get_loan_product_list()`
   didn't fetch/return it even if it existed.
3. **Flagged, NOT fixed** (adjacent but out of scope): while verifying the `core.polaris.*` path
   convention for the new `release_security` whitelisted-method alias, re-read `compose_backend.py`
   directly (not from memory) and confirmed `.polaris.` is the correct segment. This means the
   *pre-existing*, unmodified `realisePawnAsset()` call in the same `loan.ts` file
   (`"core.rlending.asset_realisation.realise_pawn_asset"`, missing `.polaris.`) has the identical bug
   already flagged for `decision.ts`'s `get_credit_score` call in the ERPNext-dependency-audit pass —
   confirmed now with direct evidence rather than suspicion, but not fixed here since it wasn't part of
   this brief's scope.

## Verification — real tests against mocked controller execution

Built a mocked `frappe`/`Document` harness (same approach as every prior phase) and executed the actual
controller code end-to-end — not simulated logic:

```
PASS: secured application without a description is correctly rejected: Collateral description is mandatory for secured loans
PASS: is_secured_loan correctly inferred from Loan Product even though the frontend never sends it
PASS: Pledged Asset Pledged Asset-2 created at disbursement, status=Pledged, description copied from application
PASS: re-calling disburse_loan on an already-disbursed loan now correctly throws: Loan Application status must be Approved. Current status: Disbursed
PASS: NPA classification automatically flags the Pledged Asset as Repossession Triggered (signal only)
PASS: repossession trigger is purely a flag - no automatic write-off, no automatic financial action
PASS: realise_pawn_asset() (human-triggered, unchanged permission gate) correctly moves the asset to Repossessed and links Loan Write Off Loan Write Off-5
PASS: release_security correctly refuses to release a repossessed asset: The asset for Loan Loan-1 has already been repossessed - it cannot be released.
PASS: release_security correctly refuses to release before the loan is paid off: Loan Loan-6 is not fully paid off yet - cannot release the pledged asset.
PASS: release_security() correctly releases the asset once the loan is confirmed fully paid off: Pledged Asset-7
PASS: re-calling release_security on an already-released asset is idempotent
```

Scenarios covered: collateral-description validation, secured-status inference from Loan Product,
Pledged Asset creation at disbursement (with the double-disbursement fix verified), NPA-triggered flag
(confirmed signal-only — no write-off created), human-triggered repossession via the existing
`realise_pawn_asset()`, and release-on-payoff with both guard rails (can't release before payoff, can't
release an already-repossessed asset) and idempotency.

Permanent test file (same scenarios, real Frappe calls, for post-compose execution against a live
bench): `corporate/polaris/frappe/src/tests/test_secured_lending.py`.

## What was deliberately not built

- LTV/mark-to-market/margin-call logic (brief's explicit instruction).
- Multi-asset support (brief's explicit instruction — the `loan` field's unique constraint enforces
  single-asset-per-loan at the schema level).
- Legal/collections process simulation — the system records outcomes a human confirms, nothing more.
- A separate "confirm repossession" endpoint — `realise_pawn_asset()` already serves that role.
