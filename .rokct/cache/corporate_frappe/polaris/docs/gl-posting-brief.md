# Task Brief: Post Loan Money Movement to ERPNext's Real Ledger (GL Posting)

> Self-contained brief for a fresh session. Read in full; should not require the conversation that
> produced it. **This takes priority over `secured-lending-brief.md`** — it's a bookkeeping-integrity
> problem, not a feature gap. Real money already moves through real bank accounts when loans are
> disbursed and repaid. Right now that movement is tracked only in Polaris's own `Wallet`/`Wallet History`
> (a running balance), with zero corresponding entries in ERPNext's actual General Ledger. If ERPNext
> tracks the company's real bank account (confirm this — it likely does, since `Customer`/`Company` are
> permanent ERPNext dependencies per the fork-dependency ledger), every loan disbursement and repayment is
> currently invisible to it — meaning bank reconciliation against ERPNext's books will not match reality.
> This needs fixing regardless of investor/audit timing.

## Context — confirm before building

1. **Does ERPNext already track the company's real bank account(s)?** Check if there's a configured
   `Bank Account`/`Account` (type Bank) in the ERPNext instance this connects to, and whether any other
   part of the business already posts real transactions through it. If Polaris's loan disbursements
   literally originate from and repayments literally land in that same tracked account, this is the
   exact reconciliation gap described above — confirm this concretely, don't assume.
2. Read `corporate/polaris/frappe/src/rlending/wallet_integration.py` in full — this is where
   `credit_wallet_on_disbursement`/`debit_wallet_on_repayment` already fire on `on_submit` hooks
   (`corporate/polaris/frappe/manifest.json`'s `doc_events`). These are the exact points where a parallel
   GL-posting call needs to happen.
3. Read `corporate/polaris/frappe/src/rlending/asset_realisation.py` and the interest-accrual controller
   (`Loan Interest Accrual`, Phase 5) too, since accrued interest is also real (if unrealized) financial
   activity that likely needs its own GL treatment (interest income recognition), separate from the
   cash-movement postings.
4. Read the fork-dependency ledger's standing decision: Frappe/ERPNext are permanent dependencies. This
   means using ERPNext's real accounting doctypes (`Journal Entry`, `GL Entry`, `Account`) is not "adding
   a dependency" — it's using the foundation that's already there correctly, for the first time, in this
   specific area.

## What to actually build

1. **A GL-posting layer** triggered by the same events `wallet_integration.py` already hooks: on loan
   disbursement, create a real `Journal Entry` debiting a Loans Receivable-type account and crediting the
   disbursing bank account (or however the business's actual chart of accounts is structured — don't
   invent account names, find out what accounts exist or need to be created, matching real double-entry
   convention: every entry balances). On repayment, the reverse — debit bank, credit the receivable
   (splitting principal vs. interest income appropriately, since interest income is a P&L item and
   principal repayment is a balance-sheet movement, not the same thing).
2. **Interest accrual posting**: when `Loan Interest Accrual` runs (Phase 5, already ported), accrued
   interest should post as income recognized (even though no cash moved yet) — standard accrual
   accounting. Determine the correct account treatment (interest receivable / interest income) rather than
   guessing at account names — check what accounts already exist in a real ERPNext setup for lending-style
   income recognition, or flag clearly what needs to be created if nothing suitable exists.
3. **Write-off / NPA classification posting**: when a loan is written off or moves to non-performing
   status, determine whether that needs its own GL treatment (bad-debt expense) — check with real evidence
   whether this is expected now or can be deferred; don't assume without checking.
4. **A reconciliation check**: build a simple verification — for a given loan, does the sum of its GL
   entries match its `Wallet History` balance? This is the actual proof the fix works, not just "entries
   get created."

## What NOT to do

- Don't build GL provisioning/IRAC rate configuration — confirmed separately as not applicable to
  Polaris's current model (no formal loan-loss-provisioning requirement evidenced yet). Stay focused on
  posting *actual transactions*, not regulatory provisioning.
- Don't invent a chart-of-accounts structure from nothing — find out what accounts genuinely exist or
  need to be created via real evidence (check the ERPNext instance's existing `Account` tree if
  accessible, or flag clearly that this needs a real accountant's input on account naming/structure before
  finalizing, since that's a domain decision, not an engineering one).
- Don't retroactively backfill GL entries for loans that already moved money before this fix exists,
  without being explicit about it — that's a real decision (does historical activity need to be
  reconciled manually, or can GL posting start from "now" forward) that should be flagged to the user
  clearly, not decided silently.

## Deliverable

Real `Journal Entry` creation wired to loan disbursement, repayment, and interest accrual events, verified
by the reconciliation check (GL entries sum to match `Wallet History` for a test loan). An explicit,
flagged answer on whether historical (pre-fix) loan activity needs manual reconciliation. Report back with
evidence — a real test loan's full GL trail, not just "wired it up."
