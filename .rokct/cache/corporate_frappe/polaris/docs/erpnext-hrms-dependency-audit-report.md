# Report: ERPNext/HRMS Dependency Audit (Post Lending-App Fork)

> Findings for `erpnext-hrms-dependency-audit-brief.md`. All doctype ownership claims below were
> verified against local source checkouts (`Frappenize/frappe`, `Frappenize/erp/erpnext`,
> `Frappenize/hrms`, `Frappenize/crm`), not asserted from memory.

## Answer to the core question

**Yes — Polaris still depends on ERPNext, via doctype-name reference, not Python import.** The Lending-
app fork (Phases 0-7) correctly eliminated every `lending.`/`erpnext.` Python import, but that only
covers *import-level* coupling. The fork's own forked doctypes (built in Phases 1-5) reintroduced
ERPNext doctype-name dependencies that were never audited against, because they were inherited
unexamined from upstream Frappe Lending's own field definitions when doctypes were trimmed rather than
rebuilt from a clean slate.

**HRMS: no dependency found anywhere**, backend or either frontend copy — see §3.

## 1. Doctype ownership, verified against local source

| Doctype | Owning app (verified) | Source path checked |
|---|---|---|
| `Customer` | **ERPNext** | `Frappenize/erp/erpnext/selling/doctype/customer` |
| `Company` | **ERPNext** | `Frappenize/erp/erpnext/setup/doctype/company` |
| `Employee` | **ERPNext** (not HRMS) | `Frappenize/erp/erpnext/setup/doctype/employee` |
| `Account` | **ERPNext** | (already disclosed pre-audit; chart of accounts) |
| `Branch` | Polaris's own platform (`core` app) — **not a gap** | `core/base/frappe/doctype/branch` (this workspace) |
| `Currency` | **Core Frappe framework** — **not a gap** | `Frappenize/frappe/frappe/geo/doctype/currency` (ships with every Frappe site) |
| `CRM Lead` | **Frappe CRM** (a *third*, previously undisclosed external app — not `lending`, not `erpnext`) | `Frappenize/crm/crm/fcrm/doctype/crm_lead` |

## 2. Where each real dependency actually lives

### `Customer` — the most pervasive finding
Used as the `applicant_type: "Customer"` Select option plus `Dynamic Link -> Customer` (`options:
"applicant_type"`) on essentially every core lending doctype forked in Phases 1-5: `Loan`,
`Loan Application`, `Loan Disbursement`, `Loan Repayment`, `Loan Write Off`, `Loan Demand`,
`Loan Restructure`, `Loan Refund`, `Loan Balance Adjustment`, `Loan Interest Accrual`,
`Loan Security Shortfall`. Also referenced directly:
- `corporate/polaris/frappe/doctype/loan_application/loan_application.py` (`validate_kyc`):
  `frappe.db.get_value("Customer", self.applicant, "email_id")` and `"mobile_no"`.
- `corporate/polaris/frappe/src/rlending/wallet_integration.py` (`update_wallet`):
  `frappe.db.get_value("Customer", customer, "user")`.

This is structural, not incidental — the entire applicant-identity model assumes ERPNext's `Customer`
doctype exists. Removing it would mean designing Polaris's own customer/applicant identity doctype, a
materially larger undertaking than anything scoped in the original fork plan.

### `Company` — nearly as pervasive
Every forked doctype has a `company: Link -> Company` field (multi-tenant/multi-branch scoping). Same
situation as `Customer`: inherited from upstream's field definitions without being questioned during the
trim-and-fork passes, because "keep company for tenant scoping" felt like an obviously-safe default at
the time (see Phase 3's own notes) rather than a dependency decision.

### `Employee` — present but dormant
Declared as the second `applicant_type` option (`"Customer\nEmployee"`) on the same doctype list as
`Customer` above, and Loan Application's original `overrides/loan_application.py` (pre-fork) had a
`validate_employee` branch that Phase 2 explicitly chose not to port, precisely because nothing in
`rlending` or `RokctAI_frontend` ever exercises the Employee path — confirmed again this pass: zero
matches for `"Employee"` combined with any staff-loan doctype (`Salary Slip`, `Leave Application`,
`Department`, `Designation`, `Attendance`, `HR Settings`) anywhere in `corporate/polaris` or
`RokctAI_frontend/app/services/all/lending`. Lower severity than `Customer`/`Company`: it's declared
schema surface, not active coupling. Could be dropped from the Select options entirely with no
behavioral change, if closing even dormant surface is wanted.

### `CRM Lead` — a third, previously undisclosed external app
`loan_application.py`'s `validate_kyc()` (ported verbatim from the pre-fork `overrides/loan_application.py`
in Phase 2) does:
```python
lead = frappe.db.get_value("CRM Lead", {"email": customer_email}, "name")
...
kyc_status = frappe.db.get_value("CRM Lead", lead, "kyc_status")
```
`CRM Lead` belongs to **Frappe CRM** (`frappecrm`), a separate installable app from `lending` and
`erpnext` entirely. This was present in the *original* pre-fork code and carried forward unexamined —
the original investigation's "removes the external `lending` app dependency" framing never accounted for
this, because it was never in scope for the `lending`-specific investigation. It's a real, live
dependency (KYC gate for withdrawable loans goes through it) that this whole fork effort never actually
addressed, positive or negative.

### `Account` — already disclosed, now resolved (see §4)

### `Branch`, `Currency` — false positives, confirmed clean
`Branch` is defined by this platform's own `core` app (`core/base/frappe/doctype/branch`) — Polaris's
`Loan.branch`/`Loan Transfer` fields resolve against that, not ERPNext's `erpnext/setup/doctype/branch`.
`Currency` ships with every Frappe site as a core framework doctype (`frappe/frappe/geo/doctype/currency`)
regardless of which apps are installed — using it isn't a dependency on anything beyond bare Frappe.

## 3. HRMS: zero dependency found

Grepped `corporate/polaris` (full tree) and `RokctAI_frontend/app/services/all/lending` for every HRMS-
specific doctype name (`Salary Slip`, `Leave Application`, `HR Settings`, `Department`, `Designation`,
`Attendance`) plus `Employee` in combination with any of them — zero matches anywhere. `Employee` itself
is ERPNext's, not HRMS's (verified in `Frappenize/erp/erpnext/setup/doctype/employee`, confirmed absent
from `Frappenize/hrms/hrms`). **HRMS was never actually a dependency** — the user's recollection likely
conflates ERPNext's `Employee`/`Company` (which Polaris's schema does reference, per §2) with HRMS
proper, which it never touches.

## 4. `getAssetAccounts()` / `asset_realisation.py` — traced and resolved, not just scoped

Traced the real caller chain: `RokctAI_frontend/app/handson/all/lending/loan/[id]/page.tsx` genuinely
renders a live admin UI (an "Asset Realisation" modal, gated behind `showAssetModal`) that calls
`getAssetAccounts(loan.company)` on open and feeds the selected value into `realisePawnAsset()` on
submit — **not dead code**, a reachable flow a real admin can trigger.

The mismatch: `getAssetAccounts()` queried ERPNext's `Account` doctype (`root_type: "Asset"`) to build a
dropdown, but Phase 3 of the Lending-app fork already made `Loan Write Off.write_off_account` (the field
this feeds) a plain free-text `Data` field — Polaris has no chart-of-accounts concept per the Phase 0
GL-posting decision. The dropdown never matched its own destination field's type after Phase 3, and
nobody caught it until this audit.

**Resolved, not just flagged**, since this was a clean fix fully within scope (matching UI to an already-
decided backend schema, not inventing new collateral/accounting logic):
- Removed `getAssetAccounts()` from `app/services/all/lending/loan.ts` and
  `app/actions/handson/all/lending/loan.ts` (both `RokctAI_frontend` and the `corporate/polaris/nextjs`
  SDK-fork template copy — kept identical, diffed to confirm).
- Replaced the modal's `<select>` (ERPNext Account picker) with a plain `<input type="text">`, matching
  `write_off_account`'s real type. `realisePawnAsset()`'s call signature is unchanged — it still takes a
  string, just no longer sourced from an ERPNext query.
- `asset_realisation.py` itself needed no changes — it already treats `write_off_account` as an opaque
  string (`wo.write_off_account = asset_account`), never validated it against ERPNext, and was already
  correctly ERPNext-free per the original Phase 3 audit.

This closes the `Account` doctype dependency entirely — it was the only ERPNext doctype referenced in
either frontend copy outside of the `Customer`/`Company`/`Employee` fields documented in §2.

**Residual, not fixed**: two auto-generated documentation files (`RokctAI_frontend/endpoints_part4.md`,
`RokctAI_frontend/docs/api/app_actions_handson_all_lending_loan.md`) still list `getAssetAccounts` in
their generated endpoint tables. These are generator output, not hand-maintained source — didn't hand-
edit them since whatever tool produces them should be re-run rather than patched by hand, but flagging
so they're not mistaken for evidence the function still exists.

## 5. "The original" — what was actually checked

Per the brief's instruction to determine what "the original" means before concluding the audit is
complete (and the explicit rule against citing `RokctApp/lib_backup`):

- **No deployed/production Polaris site is reachable from this local checkout.** Searched the entire
  `RokctAI` workspace for `apps.txt`, `site_config.json`, or any bench/site artifact describing a real
  installed-apps list — zero matches anywhere (not in `corporate`, not in `rcore`, not elsewhere).
- **No other branch holds a more complete lending implementation.** `corporate`'s only other branch is
  `main`, which sits at an older commit (`d07d86c`) predating even the `af60867` "Refork: rebuild SDK
  layer" commit this whole fork built on — diffing it shows only unrelated Dart test scaffolding changes,
  no additional lending/ERPNext/HRMS coupling. `RokctAI_frontend`'s other branches are dependabot
  dependency-bump branches and a footer-layout fix — none touch lending.
- **`RokctApp/lib_backup` was not consulted**, per the standing project rule.
- **The only "original" that could be meaningfully audited was the upstream Frappe Lending app source**
  (`Frappenize/lending`), which was already exhaustively read across Phases 1-5 of the fork itself, plus
  now `Frappenize/erp/erpnext`, `Frappenize/hrms`, and `Frappenize/crm` for this pass's doctype-ownership
  verification.

**Honest conclusion**: there is no discoverable "actual production/original" Polaris implementation
beyond what's in this local checkout and what's already been audited. If one exists outside this
workspace (a live bench, a separate private repo), it wasn't reachable from here, and no artifact in
this workspace points to where it might be.

## Summary for whoever picks this up next

| Item | Status |
|---|---|
| `lending`/`erpnext` Python imports | Zero (confirmed, unchanged from Phase 7) |
| `Account` (ERPNext) | **Resolved this pass** — picker replaced with free text |
| `Customer` (ERPNext) | **Open, structural** — load-bearing across nearly every forked doctype; removing it means designing Polaris's own applicant-identity doctype |
| `Company` (ERPNext) | **Open, structural** — same shape of dependency as `Customer`, same scope of work to close |
| `CRM Lead` (Frappe CRM) | **Open, newly disclosed** — live KYC-gate dependency, pre-existing in the original code, never previously in scope |
| `Employee` (ERPNext) | **Open, dormant** — declared but unused; cheap to drop if wanted |
| HRMS (any doctype) | **Not a dependency** — confirmed zero references anywhere |
| `Branch`, `Currency` | **Not dependencies** — false positives, resolved against this platform's own `core` app / core Frappe framework respectively |

Closing `Customer`/`Company`/`CRM Lead` would be a materially larger effort than the Lending-app fork
itself (they're identity/tenancy primitives referenced everywhere, not a bounded set of loan-lifecycle
doctypes) — scoping that is a decision for a dedicated follow-up brief, not something to fold into this
one silently.
