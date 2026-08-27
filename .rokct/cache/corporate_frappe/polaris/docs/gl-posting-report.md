# Report: GL Posting for Loan Money Movement

> Findings and delivered work for `gl-posting-brief.md`. Read that brief first for framing.

## Read this first — one behavioral consequence that needs your sign-off

**Loan disbursements and repayments will now be BLOCKED (the transaction throws and rolls back) if
the Loan Product's GL accounts aren't configured.** This matches real upstream Frappe Lending's own
`make_gl_entries()` behavior (it throws under the same condition) and is the financially correct
default — but it means **every loan disbursement/repayment against every existing Loan Product will
fail starting the moment this code is deployed**, until an accountant fills in three new fields per
product (`loan_account`, `interest_income_account`, `interest_accrued_account` — see §3). This wasn't
explicitly requested in the brief; it's the logical consequence of "don't invent chart-of-accounts
structure, throw if unconfigured" applied to the actual hook points. If you'd rather GL posting fail
soft (log an error, let the wallet/business transaction proceed) until accounts are configured, that's
a one-line change (catch the exception in `wallet_integration.py` instead of letting it propagate) —
flagging this as a decision, not deciding it silently.

## 1. Does ERPNext track the company's real bank account? — structurally yes, live status unconfirmed

ERPNext's `Company` doctype (verified against `Frappenize/erp/erpnext/setup/doctype/company/company.json`)
has a real `default_bank_account` field — this is the standard, built-in ERPNext mechanism for
"the company's real bank account." `gl_posting.py`'s `get_bank_account()` reads this field.

**What I could not confirm**: whether `Company.default_bank_account` is actually *populated* in the
real, deployed ERPNext instance this system connects to. This workspace is a static source-code
checkout with no live bench, no site database, no `site_config.json`, and no fixture data anywhere
describing a real Company record's field values (confirmed by the same search done for the ERPNext/HRMS
dependency audit — see `erpnext-hrms-dependency-audit-report.md` §5, "no deployed/production Polaris
site is reachable from this local checkout"). If that field is unset in the real instance,
`get_bank_account()` throws a clear error naming exactly what's missing — it does not guess or fall
back to a made-up account name.

**This needs live-site confirmation from whoever has bench/database access**, not something resolvable
from source code alone.

## 2. What was built

### `corporate/polaris/frappe/src/rlending/gl_posting.py` (new)
- `get_bank_account(company, loan_product=None)` — resolves the real bank account: Loan Product's
  optional override first, then `Company.default_bank_account`. Throws if neither is set.
- `get_loan_gl_accounts(loan_product)` — reads `loan_account`/`interest_income_account`/
  `interest_accrued_account` from Loan Product. Throws naming exactly which fields are missing if any
  are unset.
- `make_journal_entry(...)` — creates and submits a real `Journal Entry`. Balance validation is NOT
  reimplemented here — ERPNext's own Journal Entry controller rejects an unbalanced entry, which is the
  safety net actually wanted (this module doesn't need to trust its own arithmetic).
- `post_disbursement(disbursement_doc)` — Debit Loans Receivable, Credit Bank.
- `post_repayment(repayment_doc)` — Debit Bank (full `amount_paid`), Credit Loans Receivable
  (`principal_amount_paid`), Credit Interest Receivable (`interest_payable`, if any — this *reduces*
  the receivable set up at accrual time, it does not re-recognize income, since income was already
  recognized when the interest accrued). Validates `principal_amount_paid + interest_payable ==
  amount_paid` before posting, since an unbalanced split would otherwise silently corrupt the GL entry
  through rounding rather than fail loudly.
- `post_interest_accrual(accrual_doc)` — Debit Interest Receivable, Credit Interest Income. Standard
  accrual accounting: income recognized as earned even though no cash has moved yet.
- `cancel_journal_entry(name)` — cancels the linked Journal Entry; called from each doctype's existing
  `on_cancel()`.
- `reconcile_loan_gl_vs_wallet(loan_name)` — the brief's explicit reconciliation-check ask. Returns
  both totals and every constituent GL row, so a caller gets a full trail, not just a boolean.

### Hook wiring
- `wallet_integration.py`'s `credit_wallet_on_disbursement`/`debit_wallet_on_repayment` — GL posting now
  runs **first**, before any wallet balance is touched. If GL posting throws, the wallet update never
  happens and the exception propagates up through the `on_submit` doc_event, aborting the whole
  submission transaction (Frappe wraps doc_events in the same DB transaction as submit) — GL and wallet
  either both happen or neither does, never a partial, inconsistent state.
- `Loan Interest Accrual.on_submit()` calls `gl_posting.post_interest_accrual(self)` directly (it isn't
  hooked through `wallet_integration.py` since Polaris's own doctype controls its own submit).
- `Loan Disbursement`/`Loan Repayment`/`Loan Interest Accrual`'s existing `on_cancel()` methods now also
  call `gl_posting.cancel_journal_entry(self.journal_entry)`.

### New fields
- **`Loan Product`**: `loan_account`, `interest_income_account`, `interest_accrued_account` (all
  `Link -> Account`, blank by default) and an optional `default_bank_account` override. See §3 for why
  these are left blank.
- **`Loan`**: mirrors of the same three accounts, `read_only`, copied from Loan Product when the Loan is
  created (not looked up fresh each time) — matches how account resolution works in real double-entry
  systems: if Loan Product's configuration changes later, existing loans keep referencing what was
  configured when they were created. Also `bank_account`.
- **`Loan Disbursement` / `Loan Repayment` / `Loan Interest Accrual`**: a `journal_entry` `Link ->
  Journal Entry` field, set by `gl_posting.py` on successful posting, for traceability.

## 3. Chart of accounts — not invented, flagged for accountant input

Per the brief's explicit instruction, no account names were invented. The three new `Loan Product`
fields (`loan_account`, `interest_income_account`, `interest_accrued_account`) are **left blank**. GL
posting throws a clear, specific error (naming exactly which field is missing) rather than guessing —
see §1's consequence note above for what that means operationally.

**An accountant needs to determine and enter real account names before this goes live**, specifically:
- **Loans Receivable Account**: an asset account distinct from any generic trade Accounts Receivable —
  loan principal owed by borrowers is a different balance-sheet line from customer invoice AR, and
  should not be commingled with it.
- **Interest Income Account**: a P&L income account for interest earned on loans.
- **Interest Receivable Account**: an asset account for interest that's been recognized as earned
  (accrued) but not yet collected in cash.

Whether these should be brand-new accounts created in the chart of accounts, or existing accounts
already used for something adjacent, is a real accounting-structure decision this pass deliberately did
not make.

## 4. Write-off / NPA GL treatment — deferred, not built

Per the brief's explicit "what NOT to do" #1, and given zero evidence anywhere (no accountant input, no
existing bad-debt-expense account reference in any doc, config, or fixture found in this workspace) of
what write-off/NPA GL treatment should look like, **no GL posting was added for `Loan Write Off` or NPA
classification (`Loan`/`Process Loan Classification`)**. `Loan Write Off` and NPA status changes
continue to update Polaris's own sub-ledger balances (Phase 3/5 work) exactly as before — untouched by
this pass. If/when write-off needs its own bad-debt-expense GL treatment, that's real evidence-gathering
work (does the business want to recognize a loss immediately on write-off, or handle it through
provisioning instead — a materially different accounting treatment), not something to guess at.

## 5. Historical (pre-fix) loan activity — explicit decision needed, not made here

**Any loan disbursed or repaid before this GL-posting code is deployed has zero corresponding Journal
Entries and will not be retroactively backfilled by anything in this pass.** Per the brief's explicit
instruction, this was not decided silently. The real options, concretely:

- **(a) Start from now forward, reconcile the gap manually.** Whoever has bank statements and
  accounting access does a one-time manual journal entry (or entries) bringing the GL up to date with
  actual historical bank activity, informed by real bank statements — not reconstructed from `Wallet
  History`, since Wallet History was never designed as an accounting source of truth and may not be
  complete or accurate for this purpose.
- **(b) Backfill programmatically from `Wallet History`.** A script could walk every existing
  `Loan Disbursement`/`Loan Repayment`/`Loan Interest Accrual` record and create matching historical
  Journal Entries dated to match. This is mechanically straightforward (the same `gl_posting.py`
  functions could run against historical docs), but assumes `Wallet History`'s existing balances are
  actually correct and complete — an assumption that itself needs verification before trusting it as a
  backfill source.
- **(c) Do nothing retroactively; treat pre-fix history as a known, documented gap.** Simplest, but
  means bank reconciliation will never fully match for the historical period — a real, permanent
  discrepancy an auditor would need to be told about explicitly.

**This decision is yours, not something to infer from the brief's framing.** Option (a) is the
financially safest (grounded in actual bank statements, not a system that was never built to be an
accounting source of truth), but is manual work for whoever owns the books.

## 6. Verification — full GL trail evidence (mocked, executed, not simulated)

No live Frappe/ERPNext site was available in this source repo (same constraint noted throughout this
fork's earlier phases). Built a mocked `frappe`/`Document`/`Journal Entry` harness that exercises the
**actual controller code** (not reimplemented logic) end-to-end, including real double-entry balance
validation (a Journal Entry that doesn't balance is rejected, matching ERPNext's own controller
behavior). Four scenarios, all executed:

**Scenario A — GL accounts NOT configured:**
```
PASS: disbursement correctly BLOCKED when GL accounts unconfigured: Loan Product PROD-UNCONFIGURED is
missing GL account configuration: Loans Receivable Account, Interest Income Account, Interest
Receivable Account. An accountant must set these... before this loan can post to the General Ledger.
```
Confirms the blocking behavior in §1's consequence note actually works, and that the wallet/loan
balance was left untouched (no partial state).

**Scenario B — full lifecycle, accounts configured, disbursement → interest accrual → repayment with
explicit principal/interest split → payoff → cancellation reversal:**
```
PASS: disbursement posted to GL, Journal Entry JE-1
PASS: interest accrual posted to GL, Journal Entry JE-2
PASS: repayment posted to GL (split principal/interest), Journal Entry JE-3
PASS: loan correctly closes after full payoff (sub-ledger logic unaffected by GL changes)
PASS: cancelling the repayment correctly cancels its Journal Entry JE-3
```

**Reconciliation check (the brief's explicit deliverable) — real test loan, full GL trail:**
```
--- RECONCILIATION CHECK: LOAN-1 ---
Bank account: Business Bank Account - Acme
GL bank-side net: -203.84
Wallet-side net (disbursed - repaid): -203.84
Reconciled: True

--- FULL GL TRAIL: LOAN-1 ---
  JE-1 | DR   10000.00 | Loans Receivable - Acme        | ref: Loan Disbursement DISB-1 | Loan Disbursement against LOAN-1
  JE-1 | CR   10000.00 | Business Bank Account - Acme   | ref: Loan Disbursement DISB-1 | Loan Disbursement against LOAN-1
  JE-2 | DR     203.84 | Interest Receivable - Acme     | ref: Loan Interest Accrual ACCRUAL-1 | Interest accrued on Loan LOAN-1
  JE-2 | CR     203.84 | Interest Income - Acme         | ref: Loan Interest Accrual ACCRUAL-1 | Interest accrued on Loan LOAN-1
  JE-4 | DR   10203.84 | Business Bank Account - Acme   | ref: Loan Repayment REPAY-1 | Loan Repayment against LOAN-1
  JE-4 | CR   10000.00 | Loans Receivable - Acme        | ref: Loan Repayment REPAY-1 | Loan Repayment against LOAN-1
  JE-4 | CR     203.84 | Interest Receivable - Acme     | ref: Loan Repayment REPAY-1 | Loan Repayment against LOAN-1
```
Every Journal Entry balances (debits sum to credits on every line pair), and the GL bank-side net
(-203.84, meaning net cash *collected* since more was repaid than disbursed on this loan once interest
is included) exactly matches the Wallet-side net computed independently from `Loan.disbursed_amount`/
`total_amount_paid`.

**Scenario C — the CURRENT real-world default repayment path** (`RokctAI_frontend/repayment.ts` only
ever sends `against_loan`/`amount_paid` today, never an explicit principal/interest split — confirmed in
the earlier Phase-4/5 investigations):
```
PASS: default (no interest-split) repayment posts a clean 2-line GL entry, JE-6
PASS: LOAN-2 (default repayment path) also reconciles correctly
```
Confirms the common case (no explicit split) posts a correct, balanced, plain Bank/Receivable entry —
not just the more elaborate split case.

Permanent test file (same scenarios, real Frappe/ERPNext calls, for post-compose execution against a
live bench): `corporate/polaris/frappe/src/tests/test_gl_posting.py`.

## Summary of open items requiring your input

1. **Blocking vs. soft-fail** on missing GL configuration (§1/consequence note) — confirm the blocking
   default is acceptable, or ask for soft-fail instead.
2. **Real account names** for the three new Loan Product fields (§3) — accountant input needed.
3. **Whether `Company.default_bank_account` is actually configured** in the live instance (§1) — needs
   whoever has site/database access to check.
4. **Write-off/NPA GL treatment** (§4) — deferred; scope as a follow-up once there's a real answer on
   what treatment is wanted.
5. **Historical backfill** (§5) — pick option (a), (b), or (c), or specify something else.
