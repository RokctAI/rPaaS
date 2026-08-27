# Polaris Credit Risk & Underwriting Algorithm

> **Revised after reading the actual backend** (`corporate/polaris/frappe/src/rlending/`). The first
> version of this spec assumed no scoring engine existed and proposed writing one from scratch — wrong.
> A real, well-architected engine already exists: `decision_engine/engine.py`'s `ScoringEngine` (reads
> `Scoring Rule` / `Risk Profile` doctypes — data-driven, not hardcoded) and
> `decision_engine/analyzers/paas_analyzer.py`'s `PaasOrderAnalyzer` (alternative-data metrics from the
> applicant's own wallet transaction history). The whole `rlending` module is a customization layer on
> top of Frappe's official open-source **Lending** app (`Loan`, `Loan Application`, `Loan Disbursement`
> are its standard doctypes, not custom-built here) — loan lifecycle fundamentals are already backed by
> a maintained app; `rlending` adds KYC/ringfencing/wallet-integration/scoring on top.
>
> **What's actually missing** is three things, not a whole algorithm: (1) `Scoring Rule`/`Risk Profile`
> doctype *records* — the engine has nowhere to read rules from yet, it's empty configuration, not
> missing code; (2) a repayment-history analyzer parallel to `PaasOrderAnalyzer` — nothing currently
> computes a borrower's own past-loan repayment behavior, only their wallet spending; (3) wiring —
> `api/decision.py`'s `get_credit_score()` is a hardcoded stub (`return {"score": 0, "decision":
> "Pending", ...}`) that never actually calls `ScoringEngine`, and `api/lending_mocks.py`'s
> `check_loan_eligibility`/`check_financial_eligibility`/etc. are entirely placeholder (`is_eligible:
> True`, always) — likely an earlier, cruder pass superseded by the `ScoringEngine` approach but never
> removed; worth confirming which of the two code paths the Dart client (`PolarisRepositoryFacade`) and
> `LoanApplication.validate()` are actually meant to call before wiring anything.
>
> The scoring *substance* below (weights, gates, cold-start handling) is unchanged from the first draft
> and still the right design — it's now framed as **`Scoring Rule` data + one new analyzer + wiring the
> stub**, not new algorithm code.

## Why a rules + scorecard model, not machine learning

This is a new lending product with no historical labeled default dataset yet — there's no repayment
outcome data to train a statistical model on, and trying to force one now would mean fitting noise, not
signal. A transparent, weighted rules-based scorecard is the correct choice at this stage for three
concrete reasons: (1) it works from day one with zero historical data, (2) it's auditable — a regulator,
or a declined applicant, can be told exactly why a decision was made, which a black-box model can't
easily provide, and (3) it's the industry-standard approach for exactly this situation ("cold start"
credit scoring) — you graduate to a statistical/ML model later, once enough real repayment outcomes
accumulate to train one honestly. Revisit this decision once `LoanTransaction` history across many
borrowers reaches meaningful volume (a few thousand closed loans, as a rough industry rule of thumb).

## Regulatory gate first (National Credit Act / NCR)

Before any scoring happens, these are hard rejects — no score can override them. `LoanCalculator`'s
`PolarisConfig` already encodes NCR-style fee caps (`maxInitiationFee`), so this system is already
operating with NCA compliance in mind; the underwriting gate needs to match that seriousness:

1. **KYC completeness**: `idNumber`, `idDocumentFront`, `idDocumentBack`, `selfie` must all be present
   and (per whatever verification step already exists or gets added) internally consistent (selfie
   plausibly matches ID photo, ID number format valid for the jurisdiction). Missing or failing any of
   these → immediate decline, `reason: "KYC verification incomplete"`. Do not let a high affordability
   score override missing identity verification — that's a fraud/compliance risk, not a credit risk, and
   the two must never trade off against each other.
2. **No concurrent active loan**: if `getActiveLoan(userId)` returns non-null, decline outright
   (`reason: "Existing active loan must be settled first"`). Multiple concurrent loans to the same
   borrower is textbook reckless lending and a real regulatory exposure, not just a business risk.
3. **Affordability floor (mandatory, not advisory)**: reject if `monthlyIncome - monthlyExpenses` is
   below a configured minimum disposable-income threshold (add this as a new field on `PolarisConfig`,
   e.g. `minDisposableIncome`), and reject if the loan's own repayment burden would breach affordability
   — see the debt-service ratio check below. This is the National Credit Act's core mandatory
   affordability-assessment requirement; it is not a "nice to have" risk-reduction measure, it's the law
   in the jurisdiction these fee caps already reference.

Only applicants clearing all three gates proceed to scoring.

## Scoring model

A single score, 0–100, built from four weighted components. Weights are a starting point — they need
recalibration once real repayment outcome data exists (see `LoanTransaction` history below), but they
reflect standard microlending risk-factor ordering: repayment track record dominates every other signal
in real-world default prediction, so it's weighted accordingly.

### 1. Repayment history score — weight 45% (0 if no history — see "cold start applicants" below)

Pulled from `getLoanHistory(userId)` → `List<LoanTransaction>`. For each historical loan (group
transactions by `loanId`), determine:
- Was it repaid in full, and was the final `repayment` transaction on or before the loan's `dueDate`
  (cross-reference against the corresponding `ActiveLoan.dueDate` at the time, or reconstruct from
  `disbursedAt` + term if the loan record itself isn't retained after closure — flag this as something
  to confirm with whoever owns loan-record retention, since scoring needs it)?
- On-time full repayment: full credit for that loan.
- Late but eventually repaid: partial credit, scaled down by how many days late.
- Partial repayment / never fully repaid / defaulted: zero or negative credit for that loan — a single
  genuine default should weigh heavily negative, not just "less positive," since past default is the
  single strongest predictor of future default in real underwriting data.

Aggregate across all historical loans (weight more recent loans more heavily than older ones — a
borrower who defaulted two loans ago but has since repaid three on time is a different risk than one
who just defaulted last month).

### 2. Affordability ratio score — weight 30%

Debt-service-to-income style ratio: take the proposed loan's periodic repayment burden (derive from
`LoanCalculator.calculateBreakdown()`'s `totalRepayable` divided across the term) as a fraction of
`monthlyIncome - monthlyExpenses`. Lower ratio (loan repayment is a small fraction of disposable income)
scores higher. This is where the mandatory affordability *gate* above and this *scored* affordability
signal differ: the gate is a hard floor (can you afford this at all), the score is graduated (how
comfortably can you afford it) — a borderline-pass on the gate should still score worse here than an
easy-pass, since "technically affordable" and "comfortably affordable" are different risk levels.

### 3. Requested-amount-relative-to-income score — weight 15%

Separate from affordability of repayment: is the requested loan amount itself large relative to the
applicant's income, independent of term? A borrower requesting a small loan relative to their income
carries less exposure if something goes wrong (job loss, medical emergency) than one requesting a large
loan relative to income, even if the calculated repayment technically clears the affordability ratio
above. This protects against over-leveraging a borrower even when the math on paper looks affordable.

### 4. KYC/data-quality score — weight 10%

Not pass/fail (that's the gate above) but graduated: are all optional-but-useful fields present and
well-formed (address fields complete, phone number valid format, etc.)? Thin, low-quality applications
correlate with higher risk even when nothing is outright missing.

## Cold-start applicants (no loan history at all)

A first-time applicant can't be scored on component 1 at all — don't default this to a middling/neutral
score, since that would treat "unknown risk" the same as "known-average risk," which understates the
actual uncertainty. Instead:
- Redistribute component 1's weight into components 2 and 3 (i.e., first-time applicants are scored more
  heavily on affordability and exposure, since that's all that's actually knowable about them).
- Cap `maxAllowedAmount` at a conservative ceiling regardless of what the overall score would otherwise
  allow — e.g., never more than a configured `firstLoanMaxAmount` (add to `PolarisConfig`), independent
  of income. This is the standard "start small, prove reliability, then extend more credit" progressive
  lending pattern — it protects against granting large exposure to someone with zero track record on this
  platform, no matter how good their stated income looks.

## Score-to-outcome mapping

Translate the 0–100 score into `LoanEligibility`'s existing fields — no new model needed:

| Score range | `isEligible` | `maxAllowedAmount` |
|---|---|---|
| 0–39 | `false` | 0 |
| 40–59 | `true` | reduced fraction of the requested/config max (conservative) |
| 60–79 | `true` | requested amount, up to `PolarisConfig.maxLoanAmount` |
| 80–100 | `true` | requested amount, and consider this borrower eligible for a higher tier if/when a tiered `PolarisConfig` is introduced later (graduated credit limits for proven-reliable repeat borrowers — a natural extension of the cold-start capping logic above, letting good repayment history actually pay off for the borrower over time) |

Exact thresholds/weights above are a defensible starting point, not tuned constants — once real
`LoanTransaction` outcome data accumulates, revisit both the weights and the score bands against actual
observed default rates, the same way any real underwriting model gets recalibrated over time.

## Where this plugs in — backend (the real implementation site)

1. **Seed `Scoring Rule` records** translating this spec's gates and weighted components into rows the
   existing `ScoringEngine` already knows how to consume (`metric_name`, `condition`, `threshold`,
   `weight`, `is_knockout`):
   - Regulatory gates → `is_knockout=1` rules: `kyc_complete` (Equals 1), `has_active_loan` (Equals 0),
     `disposable_income` (Greater Than `minDisposableIncome`).
   - The four weighted components → `is_knockout=0` rules with weights 45/30/15/10 as designed above,
     against metric names like `repayment_history_score`, `affordability_ratio_score`,
     `amount_to_income_score`, `kyc_quality_score` — each pre-computed (0–100) by the analyzer/wiring
     step below before being handed to `ScoringEngine`, since `_apply_rules()` expects numeric metrics
     to compare against a threshold, not to compute the sub-scores itself.
   - Seed matching `Risk Profile` records for the score-to-decision bands in the table below, rather
     than relying on `_get_risk_profile()`'s generic 70/40 fallback, which isn't tailored to this
     product's actual risk tolerance.

2. **Write `LoanHistoryAnalyzer`** (new file, `decision_engine/analyzers/loan_history_analyzer.py`,
   parallel in shape to `PaasOrderAnalyzer`) — queries this specific applicant's own past `Loan` /
   `Loan Repayment` records (the standard Lending-app doctypes `rlending` already overrides/extends) and
   computes the repayment-history metric described above (on-time vs. late vs. defaulted, recency-
   weighted). This is the one component with no existing analyzer at all today.

3. **Wire `api/decision.py`'s `get_credit_score()`** to actually: load the `Loan Application` doc (already
   does this), run `PaasOrderAnalyzer(applicant).analyze()` for wallet-based metrics, run the new
   `LoanHistoryAnalyzer(applicant).analyze()` for repayment-history metrics, combine with the
   application's own income/expense/KYC fields into one `metrics` dict, feed that into
   `ScoringEngine(metrics).calculate_score()`, and return the real result instead of the hardcoded
   `{"score": 0, "decision": "Pending"}` stub.

4. **Reconcile with `lending_mocks.py`**: before touching it, confirm with whoever owns this module
   whether `check_loan_eligibility`/`check_financial_eligibility`/`check_loan_history_eligibility` are
   dead code superseded by `get_credit_score()`, or whether the Dart client / `LoanApplication.validate()`
   actually calls into these specific endpoints today — if the latter, they need the same real wiring
   (or need redirecting to call `get_credit_score()` instead of duplicating logic).

## Where this plugs in — Dart client

`PolarisRepositoryFacade.checkEligibility()`'s real implementation (replacing
`mock_polaris_repository_impl.dart`) should call whichever backend endpoint ends up being the real one
per item 4 above, and map its response into the existing `LoanEligibility` type — no new Dart models
needed either.

## Open items needing a decision before implementation, not assumptions

1. ~~Which backend code path is actually live today~~ — **resolved**: `lending_mocks.py` and
   `decision.py`/`ScoringEngine` are not two competing systems, they're two passes at the same feature,
   the second unfinished. Evidence: `disburse_loan()` exists in both `loan.py` (real — creates actual
   `Loan`/`Loan Disbursement` records, checks status, prevents double-disbursement) and
   `lending_mocks.py` (stub — `return {"status": "success"}` for a function that already has a real
   implementation elsewhere). `lending_mocks.py` was the earlier, shallow-but-complete sketch of the
   whole loan flow; `ScoringEngine`/`PaasOrderAnalyzer`/`loan.py`'s real `disburse_loan()` are the later,
   more serious pass that started replacing individual mocked pieces but never finished (`get_credit_score()`
   is still a stub too). **Direction**: `lending_mocks.py`'s scoring functions
   (`check_loan_eligibility`, `check_financial_eligibility`, `check_loan_history_eligibility`) should be
   retired and redirected to call `get_credit_score()` once it's wired, not maintained as separate logic.
   Its CRUD functions (`save_incomplete_loan_application`, `fetch_saved_application(s)`,
   `create_loan_application`, `get_my_loan_applications`) show no evidence of a better replacement
   elsewhere — they're likely still the real, live implementation, just poorly housed in a file named
   "mocks" that undersells that part of it is real. Worth renaming that file once the scoring functions
   are removed from it, so "mocks" stops being a misleading name for what's left.
2. Where does the affordability floor (`minDisposableIncome`) and `firstLoanMaxAmount` config value
   actually come from — a new `Scoring Rule`/config doctype field, or hardcoded default in
   `PolarisConfig`?
3. Is `Loan`/`Loan Repayment` history retained indefinitely by the underlying Lending app, or archived/
   purged after some period? `LoanHistoryAnalyzer` needs multi-loan history to be meaningful over time —
   confirm retention doesn't quietly drop old records before this becomes a real problem.
4. Should cross-SDK payment reliability beyond wallet history (e.g. subscription payment history, if this
   app also runs Supacharge-style subscriptions) ever feed into this score? If so, on the Dart side it
   must go through the same consumer-owned-interface + host-app-DI-adapter pattern already established
   for cross-SDK dependencies (ADR-005) — `polaris_sdk` should never import another feature SDK directly.
   On the backend, `PaasOrderAnalyzer`'s existing pattern (query another doctype directly via
   `frappe.db.exists`/`frappe.get_all`) is presumably the established precedent for backend-side
   cross-module reads — confirm this is the accepted backend convention before assuming it carries the
   same restriction as the Dart-side rule.
