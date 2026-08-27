# Fork Lending Investigation: Findings & Recommendation

> Produced from `fork-lending-investigation-brief.md`. Audit only — no code changed. Read the brief
> first for framing; this report answers the four questions it poses.

## Top-line recommendation

**Stay dependent on the external `frappe/lending` app. Do not fork.**

The doctype/field inventory below shows `rlending` itself only touches a small surface (5 doctypes),
but every one of those doctypes is a thin view onto a much larger, financially load-bearing engine
(interest accrual, GL posting, security/collateral tracking, demand scheduling) that itself requires
`erpnext`. Forking "just the parts we use" is not achievable in isolation — the parts we use are entry
points into that engine, not self-contained records. Worse, `RokctAI_frontend`'s admin panel (part of
the live product, not explored in the original session) depends on **more** upstream doctypes and calls
upstream Python methods **directly by module path**, which means the real dependency surface to replace
is larger than `rlending`'s Python code alone suggests. Forking now would mean re-implementing a
loan-accounting engine (interest accrual, NPA/IRAC classification, security shortfall processing,
GL entries) inside Polaris, maintained by us, forever.

## 1. Doctype/field inventory — what `rlending` actually references today

Grepped every `.py` file under `corporate/polaris/frappe/src/rlending/` for `Loan`-prefixed doctype
strings and `lending.*` imports.

| File | Doctype(s) referenced | How |
|---|---|---|
| `overrides/loan_application.py` | `Loan Application` (via subclass), `CRM Lead` (not lending) | `from lending.loan_management.doctype.loan_application.loan_application import LoanApplication as BaseLoanApplication` — direct Python subclass import |
| `asset_realisation.py` | `Loan`, `Loan Write Off` | `from lending.loan_management.doctype.loan_repayment.loan_repayment import get_pending_principal_amount` — direct Python function import; also raw SQL `` `tabLoan` `` |
| `api/loan.py` | `Loan Application`, `Loan`, `Loan Disbursement` | `frappe.get_doc(...)` / `frappe.db.get_value(...)` / `frappe.get_doc({"doctype": ...})` — no Python import, doctype-name-only coupling |
| `api/lending_mocks.py` | `Loan Application`, `Loan Eligibility Check` (custom, not upstream) | `frappe.get_doc`/`frappe.get_list` — doctype-name-only |
| `api/product.py` | `Loan Product`, `Loan Charges` | `frappe.get_all` — doctype-name-only |
| `decision_engine/analyzers/paas_analyzer.py` | string literal `"Loan Disbursement"` (transaction-type tag, not a doctype call) | incidental |
| `wallet_integration.py` | none from Lending app — `Wallet`, `Wallet History` are `rlending`'s own | n/a (hook receiver for `Loan`/`Loan Repayment` submit events, but doesn't touch the doctypes itself) |

**Only two files have a hard Python import from `lending`:** `overrides/loan_application.py` (subclasses
`LoanApplication`) and `asset_realisation.py` (imports `get_pending_principal_amount`). Every other
reference is doctype-name-only (`frappe.get_doc("Loan", ...)` etc.), which is the *good* case — those
calls work against any app that registers a doctype with that name, they don't require the specific
upstream Python class.

**Net upstream doctypes touched by `rlending`:** `Loan`, `Loan Application`, `Loan Disbursement`,
`Loan Write Off`, `Loan Product`, `Loan Charges` (6 doctypes), plus one upstream utility function
(`get_pending_principal_amount`).

## 2. Forkability verdict per doctype

Checked each doctype's controller in `C:\Users\sinya\Desktop\Frappenize\lending\lending\loan_management\doctype\` for
size and internal imports (`from lending...`) to see what forking it in isolation would drag in.

| Doctype | Controller size | Verdict | Why |
|---|---|---|---|
| **Loan** | 2,148 lines | **Hard** | Imports `LoanController` (shared base), `loan_demand`, `loan_interest_accrual`, `loan_limit_change_log`, `loan_security_release`, `loan_management.utils`, `lending.utils`. Contains 8 references to GL Entry / accounting posting. This is the core accounting object — collateral, interest, demand schedule, write-offs all key off it. |
| **Loan Application** | 410 lines | **Medium** | Imports `Loan` itself, `loan_repayment_schedule`, `loan_security_price`. `rlending`'s override already subclasses this narrowly (KYC, ringfencing, auto-disburse) — the override pattern is proportionate to what's actually customized. Forking would still require carrying `Loan`'s dependencies transitively since Application creates/reads Loan records. |
| **Loan Disbursement** | 1,024 lines | **Hard** | Imports `LoanController`, `loan_demand`, `loan_limit_change_log`, `loan_repayment`, `loan_repayment_schedule.utils`, `loan_security_assignment`, `loan_security_release`, `process_loan_interest_accrual`, `loan_management.utils`. Posts GL entries on submit. |
| **Loan Repayment** | 3,497 lines | **Hard (largest of all)** | The single biggest file in the app. Imports `LoanController`, `loan_limit_change_log`, `loan_security_assignment`, `loan_security_shortfall`, `process_loan_interest_accrual`, `loan_management.utils`. Handles interest accrual reconciliation, charges, GL posting (5 refs), partial/full settlement logic. `rlending` only calls one utility function from it (`get_pending_principal_amount`) but that function is embedded in this 3.5k-line file's accounting logic — extracting it cleanly would mean auditing which of its internal helpers it silently depends on. |
| **Loan Write Off** | 666 lines | **Hard** | Imports `LoanController`, `loan_limit_change_log`, `loan_security_assignment`, `loan_security_shortfall`, `loan_management.utils`. Used by `asset_realisation.py`'s pawn-asset seizure flow — a real financial event (writes off principal, moves value to an asset account), not a simple record. |
| **Loan Product** | 208 lines | **Easy** | Only imports `loan_management.utils` (`loan_accounting_enabled` check). Mostly configuration (rate, charges, term flags). `rlending`'s `api/product.py` only reads it (`frappe.get_all`) — no writes, no submit/GL logic. Genuinely forkable in isolation if accounting integration is stubbed out. |
| **Loan Charges** | 31 lines | **Easy** | Trivial child-table doctype (charge_type, amount, percentage). Fork directly, no dependencies. |

**Shared blocker:** every "Hard" doctype above inherits from `LoanController`
(`lending/loan_management/controllers/loan_controller.py`) and, per `hooks.py`, the whole `lending` app
declares `required_apps = ["erpnext"]` — it posts to `GL Entry` / `Payment Entry` directly. Forking any
of the Hard doctypes without also forking (or stubbing) ERPNext's accounting integration means either
(a) silently losing GL posting — a correctness regression for a lending product — or (b) re-implementing
a chunk of ERPNext's accounting primitives inside Polaris. Neither is "fork the doctype JSON and go."

## 3. Does `RokctAI_frontend` have better fork material?

**No — it makes the dependency picture worse, not better.** `RokctAI_frontend` (a Next.js admin panel
under `app/handson/all/lending/*`) is a pure API-consumer layer, not portable backend logic. It calls
the Frappe backend via generic RPC (`frappe.client.get_list`, `.get`, `.insert`, `.submit`) and, in
several places, invokes upstream Lending-app Python methods **by their full module path**, e.g.:

- `lending.loan_management.doctype.loan.loan.unpledge_security`
- `lending.loan_management.doctype.process_loan_classification.process_loan_classification.create_process_loan_classification`
- `lending.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual.process_loan_interest_accrual_for_loans`
- `lending.loan_management.doctype.process_loan_security_shortfall.process_loan_security_shortfall.create_process_loan_security_shortfall`

And its service layer (`app/services/all/lending/*.ts`) reads/writes doctypes that `rlending`'s Python
backend never touches: `Loan Demand`, `Loan Refund`, `Loan Restructure`, `Loan Transfer`,
`Loan Balance Adjustment`, `Process Loan Classification`, `Process Loan Interest Accrual`,
`Process Loan Security Shortfall`. These are NPA/IRAC provisioning, interest-accrual batch processing,
and security-shortfall workflows — deep accounting-engine features, not UI-adjacent conveniences.

What `RokctAI_frontend` *does* add that's genuinely RokctAI-specific and valuable is a compliance
reporting layer on top of these doctypes — South African National Credit Act artifacts:
`reports/form-20`, `reports/section-129`, `reports/ncr-form-40`, `reports/compliance-report`,
`reports/assurance-report` (`app/templates/lending/Form20Template.tsx`,
`Section129Template.tsx`, `AssuranceReportTemplate.tsx`, `app/services/all/lending/ncr.ts`). This is
real, portable, RokctAI-specific IP — but it's a reporting/aggregation layer that *reads* Lending-app
data; it doesn't replace the underlying doctypes or reduce the dependency surface. If anything, it
raises the bar: any fork must still produce data shaped like `Loan`, `Loan Demand`, `Process Loan
Classification`, etc., for these NCR reports to keep working.

**Conclusion:** `RokctAI_frontend` is not a better fork target. It's evidence that the live product's
admin surface already leans on more of the upstream app (interest accrual processing, NPA
classification, security shortfall) than the backend code in `rlending` alone reveals.

## 4. The tradeoff, named explicitly

**Staying dependent (current state):**
- Gets upstream bug fixes, new features, and community maintenance on a genuinely complex domain
  (interest accrual, NPA/IRAC provisioning, collateral/security tracking, GL posting) for free.
- Keeps `erpnext` as a hard external dependency (`lending` itself requires it) — this was already true
  before this investigation and is orthogonal to the `lending` app specifically.
- Upgrade risk: upstream schema/behavior changes could break `rlending`'s two hard-import points
  (`LoanApplication` subclass, `get_pending_principal_amount`) — but this is a known, bounded surface
  (2 imports), not a diffuse one.
- Requires the `lending` app (and transitively `erpnext`) to be installed in every environment
  (dev, staging, prod) — operational overhead, but a one-time setup cost, not ongoing.

**Forking (what this investigation was scoping):**
- Removes the external app dependency, in principle — but per the analysis above, doing this correctly
  for the Hard doctypes (`Loan`, `Loan Disbursement`, `Loan Repayment`, `Loan Write Off`) means either
  forking large chunks of `LoanController` + GL-posting logic + `erpnext` accounting calls, or building
  Polaris's own accounting integration from scratch — a multi-month undertaking, not a refactor.
  `Loan Repayment` alone is 3,497 lines of interest/charge/settlement reconciliation logic.
  `RokctAI_frontend`'s dependence on `process_loan_interest_accrual`, `process_loan_classification`,
  and `process_loan_security_shortfall` means those batch-processing engines would need forking too, or
  the admin panel's NPA/provisioning/interest-accrual features silently break.
  Forking `Loan Product` and `Loan Charges` alone is cheap but doesn't remove the dependency — the
  hard doctypes still need `lending` installed, so the external app requirement isn't actually lifted
  unless *all* of it is forked.
- Loses upstream fixes silently and permanently on whatever is forked — no future `lending` release
  ever reaches forked code again. For financial/compliance logic (NPA classification, interest accrual)
  this is a real risk: bugs in interest calculation or IRAC provisioning have direct regulatory and
  financial-statement consequences, and Frappe's team actively maintains this domain.
  Any bug fixed upstream must be independently discovered and re-fixed in the fork.
- Ongoing maintenance burden shifts entirely onto the Polaris/RokctAI team indefinitely.

## Recommendation detail

Do **not** fork `Loan`, `Loan Disbursement`, `Loan Repayment`, or `Loan Write Off` — the dependency
depth (shared `LoanController`, GL posting, `erpnext` requirement, and — per `RokctAI_frontend` —
interest-accrual/NPA-classification batch processing already in use) makes this a from-scratch
accounting-engine build disguised as a "fork," not a low-risk extraction.

If reducing the *coupling surface* (not the dependency itself) is the real goal, a cheaper, lower-risk
alternative exists and is worth a separate, smaller pass:

1. **Fork `Loan Product` + `Loan Charges` only** (Easy verdict above) — these are read-mostly
   configuration doctypes with no accounting/GL logic. `api/product.py` already only reads them.
   This is genuinely low-risk and would let Polaris own its own product-config schema without touching
   the accounting-critical doctypes.
2. **Keep `Loan`, `Loan Application`, `Loan Disbursement`, `Loan Repayment`, `Loan Write Off` on the
   upstream `lending` app.** Continue the current override pattern (`overrides/loan_application.py`) —
   it's already narrowly scoped (KYC, ringfencing, auto-disburse) and proportionate to what's actually
   custom about Polaris's flow.
3. **Harden the two existing hard-import points** instead of removing them: pin the `lending` app to a
   known-good commit/tag in Polaris's app requirements (if not already done), and add a smoke test that
   exercises `LoanApplication.validate()`/`on_update()` and `get_pending_principal_amount()` so upstream
   upgrades that change these signatures fail CI instead of failing silently in production.
4. If `RokctAI_frontend`'s NCR compliance reports are core Polaris product (they look real and
   valuable), treat them as a codebase worth mining for report *logic*, not as leverage for a Lending-app
   fork — they should be verified in this repo's audit scope separately, since they weren't the primary
   target of this investigation.

No further fork execution should proceed from this report without the option-1 scope above being
separately confirmed as worth doing (Loan Product/Charges only) — no case for forking the accounting-
critical doctypes is supported by the evidence found here.
