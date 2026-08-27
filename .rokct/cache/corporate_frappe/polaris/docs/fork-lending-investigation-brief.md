# Investigation Brief: Fork Frappe Lending → Remove External Dependency

> Self-contained task brief for a fresh session (written because the session that produced it was
> near its context limit). Read this file in full; it should not require the conversation that
> produced it.

## Goal

`corporate/polaris/frappe/src/rlending/overrides/loan_application.py` currently does:
```python
from lending.loan_management.doctype.loan_application.loan_application import (
    LoanApplication as BaseLoanApplication,
)
```
This means Polaris's backend depends on installing Frappe's official open-source **Lending** app
(`github.com/frappe/lending`) as an external Frappe app dependency, and only *overrides* pieces of it
(KYC validation, ringfencing, auto-disburse — see that file). Determine what can be **forked directly
into `rlending`'s own doctypes/modules** instead, so Polaris no longer needs the external `lending` app
installed at all — a real fork, not just an override layer on top of someone else's app.

## Two source locations to compare

1. **`C:\Users\sinya\Desktop\Frappenize\lending`** — the actual Frappe Lending app source. Confirmed
   structure: `lending/loan_management/`, `lending/loan_origination/`, plus `config/`, `fixtures/`,
   `overrides/`, `patches/`, `api.py`, `hooks.py`. This is the real upstream source to fork *from* —
   read its actual doctypes (`Loan`, `Loan Application`, `Loan Disbursement`, `Loan Repayment`, etc.)
   before assuming what's in them.
2. **`C:\Users\sinya\Desktop\RokctAI\RokctAI_frontend`** — has existing lending + **compliance**-related
   code under `app/actions`, `app/handson`, `app/services`, `app/templates`, `components/`, and
   generated API docs under `docs/api/app_a...` (names were truncated in the initial scan — read the
   actual directory listing yourself, don't trust this brief's paraphrase). This wasn't explored in
   depth — check whether it already has a working lending/compliance implementation that's more directly
   portable into `rlending` than forking Frappe's Lending app from scratch, since it may already be
   RokctAI-specific rather than generic.

## What's already known about Polaris (from the current session — verify it's still accurate, don't just trust it)

- `corporate/polaris/frappe/src/rlending/` structure: `api/{decision.py, lending_mocks.py, loan.py,
  product.py}`, `decision_engine/{engine.py, analyzers/paas_analyzer.py}`, `overrides/loan_application.py`,
  `wallet_integration.py`, `asset_realisation.py`.
- `decision_engine/engine.py`'s `ScoringEngine` is a real, data-driven rules engine (reads `Scoring Rule`/
  `Risk Profile` doctypes) — genuinely good, keep it regardless of what happens with the Lending-app fork.
- `api/decision.py`'s `get_credit_score()` is a stub (hardcoded return) — needs wiring to `ScoringEngine`,
  separate task, see `corporate/polaris/docs/credit-risk-algorithm.md` (full spec already written, read
  it — this fork investigation and that spec are related but distinct pieces of work).
- `api/lending_mocks.py`'s CRUD functions (save/fetch/create loan application, list applications) are
  likely the real, live implementation despite the file's name; its scoring-related functions are dead
  code superseded by the `ScoringEngine` approach — see that spec's "open item #1" for the reasoning.
- The Dart client side (`corporate/polaris/dart`) has its own independent model types
  (`LoanApplicationPayload`, `LoanEligibility`, `ActiveLoan`, `LoanTransaction` in
  `lib/src/models/customer/polaris_models.dart`) — these don't depend on the Frappe Lending app directly,
  only the backend does. This fork work is backend-only.

## What to actually determine

1. Which specific doctypes/fields from Frappe's Lending app does `rlending` actually use today? (Grep
   `rlending` for every `frappe.get_doc("Loan...", ...)`, `frappe.get_all("Loan...", ...)` call and every
   doctype name referenced, not just the one Python import already found.)
2. For each, is it simple enough to fork directly (copy the doctype JSON + relevant Python logic into
   `rlending`'s own module, drop the `lending` app dependency for that piece), or does it depend on
   deeper Lending-app internals (workflow states, report scripts, other doctypes) that would need to come
   along too?
3. Does `RokctAI_frontend` already have equivalent logic that's a better fork target than Frappe's
   original (e.g., already adapted to this platform's actual compliance requirements)?
4. What's lost by forking vs. staying dependent on the real Lending app (upstream bug fixes, new
   features, community support) — this is a real tradeoff to name explicitly, not just execute past.

## Deliverable

A decision + plan, not necessarily the fork itself in the same pass — given the risk of quietly
diverging from a maintained open-source app, treat this the same way earlier work in this project treated
large architecture changes: audit and report first, execute only after the plan is confirmed.
