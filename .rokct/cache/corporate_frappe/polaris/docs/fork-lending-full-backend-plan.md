# Phased Plan: Full Fork of Frappe Lending into `rlending`

> Plan-only deliverable per `fork-lending-full-backend-brief.md`. No doctype forks written yet.
> Builds on `fork-lending-investigation-report.md` (evidence trail) and
> `fork-lending-nextjs-report.md` (frontend file inventory, packaging convention still unresolved
> there — see Phase 5).

## 0. The GL-posting decision — resolved, not deferred

**Finding:** Polaris has no GL/ledger concept of its own. `wallet_integration.py` maintains a single
running balance per user (`Wallet.balance` + `Wallet History` audit rows) — it is not double-entry,
has no chart-of-accounts concept, and never touches `GL Entry`. Nothing else in `rlending` posts
accounting entries.

**Finding:** Even in the real upstream app, GL posting is optional per Company — gated behind
`Company.enable_loan_accounting` (`loan_management/utils.py:321-322`). The blocker isn't that GL
posting is mandatory; it's that the four core doctypes (`Loan`, `Loan Disbursement`, `Loan Repayment`,
`Loan Write Off`) hard-inherit `erpnext.controllers.accounts_controller.AccountsController` at the
Python class level, so the *import* requires `erpnext` regardless of whether the flag is ever turned on.

**Decision: fork the sub-ledger, not the GL.** Rewrite every forked core doctype as a plain
`frappe.model.document.Document` subclass. Port the per-loan bookkeeping logic that upstream keeps in
`Loan Demand`, `Loan Repayment Detail`, `Loan Interest Accrual`, and running-balance fields on `Loan`
itself (principal outstanding, interest accrued, total paid) — this is real, needed math for NCR
reporting and loan lifecycle correctness. Do **not** port `process_gl_map`, `make_reverse_gl_entries`,
or any call into `erpnext.accounts.general_ledger` — these are downstream, optional side-effects in
the source app, and Polaris doesn't consume them today (no code path in `rlending` or
`RokctAI_frontend` reads `GL Entry`). This removes both `lending` and `erpnext` as hard dependencies
and matches current usage exactly — nothing Polaris uses today is lost.

**Consequence to flag explicitly:** if Polaris ever needs real double-entry accounting for loans
(e.g. statutory financial statements, auditor requirements), that becomes a separate, later project —
building a ledger from scratch, not reconnecting to ERPNext. Documenting this now so it isn't
rediscovered as a surprise gap during an audit.

## 1. Full doctype/logic inventory (confirmed by reading source, not the brief's paraphrase)

**Backing `RokctAI_frontend`'s `operations.ts` (3 upstream whitelisted methods):**
| Method | Backing doctype(s) | Controller size |
|---|---|---|
| `process_loan_interest_accrual_for_loans` | `Process Loan Interest Accrual` (orchestrator, 81 lines) → `Loan Interest Accrual` (real math, 1,256 lines) | 1,337 combined |
| `create_process_loan_security_shortfall` | `Process Loan Security Shortfall` (48 lines) → `Loan Security Shortfall` (260 lines) | 308 combined |
| `create_process_loan_classification` | `Process Loan Classification` (147 lines) → `Loan Classification` (21 lines, mostly config) | 168 combined |

**Backing `lifecycle.ts` and the rest of `app/services/all/lending/*.ts`:**
| Doctype | Controller size | Notes |
|---|---|---|
| `Loan Write Off` | 666 | already known |
| `Loan Restructure` | 1,007 | new — not in original 6-doctype inventory |
| `Loan Transfer` | 239 | new |
| `Loan Refund` | 185 | new |
| `Loan Demand` | 665 | new — the actual balance/demand-schedule engine |
| `Loan Repayment Schedule` | 1,151 | new — amortization schedule generator, imported by `Loan Application` itself |

**Core transactional doctypes (already known, confirmed):**
| Doctype | Controller size |
|---|---|
| `Loan` | 2,148 |
| `Loan Disbursement` | 1,024 |
| `Loan Repayment` | 3,497 |
| `Loan Application` | 410 |

**Config-only (already known, cheap):** `Loan Product` (208), `Loan Charges` (31).

**Not yet in scope, confirm before Phase 4** — `loan_security_assignment` (252) and
`loan_security_release` (243) are imported by `Loan`/`Loan Disbursement`/`Loan Write Off` internally;
`loan_irac_provisioning_configuration` (26) backs NPA/IRAC classification thresholds referenced by
`Loan Classification`. These weren't named in the brief's method list but are transitively required by
doctypes that are in scope — pull them in at the same phase as their parent doctype, not separately.

**Explicitly out of scope (RokctAI_frontend's admin panel doesn't reference these; skip):** `Loan
Security`, `Loan Security Type`, `Loan Security Price`, `Pledge`/`Unpledge`/`Proposed Pledge`,
`Loan Partner*` (co-lending), `Bulk Repayment Log`, `Days Past Due Log`, `Loan Import Details`,
everything under `loan_origination/` (`Loan Lead`, `Loan Co-Applicants`, document upload doctypes —
these are pre-application lead-gen features RokctAI's own `handson` flow doesn't use, per
`fork-lending-nextjs-report.md`'s file inventory).

## 2. Build order (dependency-first, highest-risk last)

**Phase 1 — config, no behavior:** `Loan Product`, `Loan Charges`. Copy JSON, trim unused fields, no
controller logic needed beyond basic validation. (Matches the original mini-fork recommendation —
already low-risk.)

**Phase 2 — application + amortization:** `Loan Application` (own controller, ~410 lines) +
`Loan Repayment Schedule` (amortization math the application depends on at creation time, 1,151
lines — port the calculation, not the ERPNext-adjacent scheduling bureaucracy). Fold
`overrides/loan_application.py`'s KYC/ringfencing logic directly into the new controller — no more
base class to subclass. **Verification:** unit tests comparing generated schedules against known
upstream output for a handful of fixed inputs (principal, rate, term) before trusting the port.

**Phase 3 — core loan lifecycle (the big one):** `Loan`, `Loan Disbursement`, `Loan Repayment`,
`Loan Demand`, `Loan Write Off`. Rewrite each as a plain `Document` subclass per the Phase 0 decision:
keep balance/demand/repayment-allocation math, strip `AccountsController`/GL calls entirely. This is
where the bulk of the ~8,700 combined lines gets triaged line-by-line into "real bookkeeping logic to
port" vs. "GL/ERPNext plumbing to drop." Budget this as the majority of the total effort.
**Verification:** smoke-test a full loan lifecycle (application → disbursement → several repayments →
payoff, and separately → write-off) against known-good amounts computed by hand or against the
upstream app's output for the same inputs, run before Phase 4 starts.

**Phase 4 — restructure/transfer/refund + security-assignment support:** `Loan Restructure`,
`Loan Transfer`, `Loan Refund`, plus `loan_security_assignment`/`loan_security_release` insofar as
`Loan`/`Loan Disbursement`/`Loan Write Off` reference them internally (confirm at this point whether
Phase 3's rewrite actually needs them, or whether they were only reachable through GL-adjacent code
paths that got dropped — likely the latter, verify before porting).

**Phase 5 — interest accrual, security shortfall, classification (regulatory-sensitive):**
`Loan Interest Accrual` + orchestrator, `Loan Security Shortfall` + orchestrator, `Loan Classification`
+ orchestrator + `loan_irac_provisioning_configuration`. Port the actual upstream math (NPA/IRAC
thresholds, accrual formulas) verbatim from source, don't re-derive — this is regulatory-adjacent
(South African NCR / IRAC provisioning) and the investigation report already flagged this as carrying
real compliance risk if silently wrong. **Verification:** run the ported logic against upstream's own
output for the same fixture data before switching `operations.ts` over.

**Phase 6 — frontend repoint:** Update `RokctAI_frontend/app/services/all/lending/operations.ts` and
`lifecycle.ts` (and siblings: `application.ts`, `demand.ts`, `transfer.ts`, `refund.ts`, `repayment.ts`,
`product.ts`) from upstream Frappe dotted-paths (`lending.loan_management.doctype....`) to `rlending`'s
own whitelisted endpoints. Cross-reference `fork-lending-nextjs-report.md` §5 — this was already
flagged there as a follow-up. Note that report's packaging-convention question (no `nextjs/` SDK
installer exists yet) is a separate, unresolved problem from this repoint — repointing method paths in
the live `RokctAI_frontend` repo doesn't require that installer to exist; only *packaging it as a
distributable `polaris_sdk`* does. Don't block the repoint on that unrelated open question.

**Phase 7 — cutover:** Remove `lending` (and `erpnext`, if nothing else in the Polaris site depends on
it — check separately, this plan only confirms `rlending` doesn't) from the Frappe site's installed
apps. Re-run the doctype/import grep from the investigation report to confirm zero remaining
`from lending...`/`from erpnext...` references anywhere in `rlending`.

## 3. Explicitly deferred / out of scope for this plan

- `credit-risk-algorithm.md`'s `ScoringEngine`/`Scoring Rule`/`Risk Profile` doctypes are untouched by
  this fork — confirmed nothing in the phases above reads or writes them. That work's stub
  (`api/decision.py:get_credit_score()`) remains a separate task.
- Full double-entry GL/accounting for loans, if ever needed (see §0's consequence note).
- NCR report template logic (`Form20Template.tsx` etc.) — already confirmed real and portable by the
  Next.js report; not backend logic, no change needed here beyond Phase 6's method-path repoint for
  `ncr.ts`.
- Packaging `rlending`'s Dart/Next.js-facing SDK — orthogonal to this backend fork.

## 4. Sizing summary

| Phase | Core new/ported lines (rough) | Risk |
|---|---|---|
| 1 | ~250 (mostly JSON) | Low |
| 2 | ~1,500 | Low-medium |
| 3 | ~4,000-5,000 (triaged from ~8,700 source lines) | High — largest phase |
| 4 | ~1,900 | Medium |
| 5 | ~1,800 | High — regulatory correctness risk |
| 6 | frontend-only, ~12 files repointed | Medium |
| 7 | cutover + verification | Low effort, high consequence if skipped |

Consistent with the investigation's "multi-month" framing — Phase 3 and Phase 5 alone are substantial
individual efforts, not something to compress into one session.

## Next step

This plan is ready for confirmation. On approval, execute Phase 1 first (lowest risk, fastest to
verify) and report back before starting Phase 2 — per the brief's "don't attempt the full fork in one
pass" instruction.
