# Task Brief: Full Fork of Frappe Lending → `rlending` Owns It, No External Dependency

> Self-contained brief for a fresh session. Supersedes the "mini-fork" recommendation in
> `fork-lending-investigation-report.md` — read that report first for the full evidence trail, but the
> decision has been made to go further than it recommended: **fork everything, drop the external
> `lending` app dependency entirely.** This is the user's explicit call, made with the report's risk
> assessment in hand, not a case of the report being wrong.

## What the investigation found (accept as ground truth, don't re-derive)

- `rlending`'s own Python (`corporate/polaris/frappe/src/rlending/`) touches 6 upstream doctypes, 2 via
  hard Python import (`LoanApplication` subclass, `get_pending_principal_amount`).
- The live product's admin panel (`RokctAI_frontend`, `app/services/all/lending/operations.ts` and
  `lifecycle.ts`) goes considerably deeper: direct module-path calls into upstream interest-accrual,
  security-shortfall, and NPA/IRAC loan-classification engines, plus reads/writes against `Loan Demand`,
  `Loan Restructure`, `Loan Transfer`, `Loan Refund` — doctypes `rlending` itself never touches.
- All four "hard" doctypes (`Loan`, `Loan Disbursement`, `Loan Repayment`, `Loan Write Off`) share a
  controller chain that currently relies on ERPNext for GL (general ledger) posting.
- The investigation's own conclusion was: a *correct* full fork means rebuilding an accounting engine —
  interest accrual, NPA/IRAC classification, security shortfall, GL posting — in-house. That's real scope,
  not scare language. This brief exists to scope that work properly, not to minimize it.

## What "fork everything" actually requires

1. **Every doctype `RokctAI_frontend`'s admin panel and `rlending`'s backend touch**, forked into
   `rlending`'s own module — not just the 6 already known, but the full set surfaced by
   `operations.ts`/`lifecycle.ts`: `Loan`, `Loan Application`, `Loan Disbursement`, `Loan Repayment`,
   `Loan Write Off`, `Loan Demand`, `Loan Restructure`, `Loan Transfer`, `Loan Refund`, `Loan Product`,
   `Loan Charges`, plus whatever `Loan Interest Accrual`/`Loan Security Shortfall`/classification-related
   doctypes back those upstream whitelisted methods (confirm the full list by reading `operations.ts` and
   `lifecycle.ts` directly — the investigation traced the calls but the brief that produced this task
   didn't enumerate every backing doctype, verify before scoping the build).
2. **The GL-posting dependency on ERPNext** — decide and document explicitly: does Polaris's own backend
   already have (or need) a GL/ledger concept independent of ERPNext, or does dropping the Lending-app
   dependency mean ALSO dropping/replacing ERPNext-backed GL posting for loans specifically? This is the
   single biggest architectural fork in the whole task — don't let it be an implicit assumption.
3. **Interest accrual, NPA/IRAC classification, and security-shortfall logic** — these are real financial/
   regulatory algorithms (South African NCR context, same regime as the credit-risk algorithm doc). Port
   the actual upstream logic (read `Frappenize/lending`'s equivalent Python directly, don't reimplement
   from scratch/guess at the math) into `rlending`'s own module.
4. **`RokctAI_frontend`'s server actions/services** (`operations.ts`, `lifecycle.ts`, and the rest of
   `app/actions/handson/all/lending/` and `app/services/all/lending/`) need to be repointed from whatever
   upstream whitelisted-method paths they call today to `rlending`'s own equivalent endpoints once forked
   — this is a frontend change too, not backend-only. Cross-reference
   `corporate/polaris/docs/fork-lending-nextjs-report.md` (the Next.js fork investigation) since that work
   touches the same files.
5. Cross-reference `corporate/polaris/docs/credit-risk-algorithm.md` (the scoring-engine spec) — that
   work assumed the existing `ScoringEngine`/`Scoring Rule`/`Risk Profile` doctypes stay as-is; confirm
   nothing in this full fork changes that assumption.

## Sequencing recommendation (not mandatory, but don't skip the GL decision)

Resolve item 2 (the ERPNext/GL question) before writing a single doctype fork — every other piece of
scope depends on the answer. Then fork doctypes in dependency order: config-only ones first (`Loan
Product`, `Loan Charges` — already known to be safe, per the original mini-fork recommendation), then the
core loan lifecycle doctypes, then the accrual/classification/GL-posting logic last since it's the
highest-risk, highest-effort piece.

## Deliverable

Given the confirmed scope (multi-month per the investigation's own assessment), treat this as a
multi-session effort: produce a concrete phased plan first (which doctypes/logic in which order, and the
GL-posting decision made explicit and documented) before writing code, then execute phase by phase with
verification (clean recompose + analyze, and ideally a smoke test against real loan lifecycle scenarios)
after each phase — don't attempt the full fork in one pass.
