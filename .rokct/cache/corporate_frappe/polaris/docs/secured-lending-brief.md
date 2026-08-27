# Task Brief: Purpose-Built Secured Lending (Single-Asset Repossession Model)

> Self-contained brief for a fresh session. Read in full; should not require the conversation that
> produced it. Real, near-term business need — Polaris will soon offer secured lending against a single
> financed physical asset (e.g. an aircon), with repossession on default. This is **not** a fork of
> upstream Frappe Lending's formal margined-securities/LTV system — that model assumes a portfolio of
> valued collateral instruments (shares, bonds, formally appraised assets) with ongoing mark-to-market
> shortfall checks. Polaris's actual need is much simpler: one asset, one loan, binary outcome (paid off →
> asset released; defaulted → asset repossessed). Build for the real model, don't port the complex one.

## What already exists (don't re-derive)

- `Loan Security Shortfall` (`corporate/polaris/frappe/doctype/loan_security_shortfall/`) — a record-only
  shell from Phase 5, deliberately built with no LTV/shortfall math since no evidence existed at the time.
  Read it — it may be a reasonable starting doctype, or may need to be replaced with something simpler.
  `Process Loan Security Shortfall` also exists alongside it, same status.
- `releaseSecurity()` in `RokctAI_frontend/app/services/all/lending/loan.ts` (and the mirrored copy in
  `corporate/polaris/nextjs/`) — currently points at the now-uninstalled external `lending` app, with an
  explanatory comment. This is the real, live frontend call site that needs a working backend behind it.
- The fork-dependency ledger (`The-Rokct-Protocol/core/docs/fork-dependency-ledger.md`) has this feature
  listed as a real near-term need — read its entry for the framing already agreed on.
- `Loan Product` (already forked) is where secured-vs-unsecured loan types would presumably be
  distinguished — check whether it already has a field for this or needs one added.

## What to actually build

1. **A pledged-asset doctype** (or a field set on an existing one — your call, but justify it): what asset
   is financed (description, identifying details — serial number if applicable, category), its declared
   value at loan origination, and its current status (pledged / released / repossessed). Keep this
   genuinely simple — a single asset per loan, not a portfolio structure. Don't build for multiple
   simultaneous pledges per loan unless there's real evidence that's needed.
2. **Loan origination**: when a secured loan is created, the pledged asset gets recorded and linked. Decide
   whether this belongs on `Loan Application` (at application time) or `Loan` (at disbursement) — trace
   how the real frontend flow would actually capture this (check `RokctAI_frontend`'s loan application
   pages for where asset/collateral info would naturally be entered, if anywhere yet) rather than
   guessing.
3. **Repossession trigger and workflow**: on default (tie this to the existing DPD/NPA classification from
   Phase 5 — `Loan Classification`/`Process Loan Classification` already compute overdue status, reuse
   that rather than inventing a parallel default-detection mechanism), the asset's status moves to
   "repossession triggered" and then "repossessed" — a real, auditable state transition, not just a status
   string with no history. Consider whether this needs its own approval gate (a human confirms
   repossession actually happened) rather than fully automatic — repossessing physical property is a real
   action with legal/practical implications, don't make it silently automatic without checking whether
   that's actually the intended business process.
4. **`releaseSecurity()`'s real implementation**: once the asset is fully paid off, it should be released
   (status → released) — implement the actual backend method this frontend call expects, replacing the
   pointer to the external app.
5. **Frontend wiring**: update `loan.ts` in both `RokctAI_frontend` and the `polaris/nextjs` SDK template
   (mirror the edit in both, matching the established pattern from prior phases) to call the new real
   backend method instead of the external app.

## What NOT to do

- Don't build LTV/mark-to-market/margin-call logic — there's no evidence Polaris's model needs ongoing
  asset revaluation, only a one-time declared value and a binary released/repossessed outcome.
- Don't build for multiple assets per loan or asset portfolios — single asset per loan is the real,
  current business model. If that changes later, it's a follow-up, not something to speculatively support
  now.
- Don't invent legal/collections-process details (how repossession is physically executed, what notice
  periods apply, etc.) — that's real-world process the system should record and gate, not simulate or
  assume. If a real process exists, ask; if not building beyond what's evidenced is fine, just make sure
  the doctype/workflow doesn't silently pretend to handle legal process it doesn't.
- Don't touch term-loan accrual, GL posting, or other explicitly-deferred items from the fork-dependency
  ledger — those are separate, deliberately out of scope here.

## Deliverable

A working, minimal secured-lending flow: pledge an asset at origination, track its status, trigger
repossession off the existing default/NPA classification (with a human confirmation gate unless evidence
says otherwise), and release it on payoff — `releaseSecurity()` actually implemented and both frontend
copies repointed. Real tests against mocked controller execution, same rigor as every other phase of this
fork. Report back with evidence, not just "built."
