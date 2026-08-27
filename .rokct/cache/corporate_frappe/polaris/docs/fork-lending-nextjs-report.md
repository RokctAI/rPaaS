# Report: Forking RokctAI_frontend's Lending Module into `polaris_sdk`'s Next.js SDK

> Findings + plan pass per `fork-lending-nextjs-brief.md`. Execution status: **plan only, fork not
> executed** — see "Packaging convention" below for why.

## 1. Packaging convention — UNRESOLVED, no working example exists

The brief's premise was "find a working `nextjs/` SDK example among `corporate/*` siblings and verify the
installer before assuming the Dart convention carries over." I checked all four sibling workspaces:

```
corporate/corporate/nextjs/   -> only .gitignore
corporate/dev/nextjs/         -> only .gitignore
corporate/polaris/nextjs/     -> only .gitignore
corporate/revenue/nextjs/     -> only .gitignore
```

Every `nextjs/` folder in every `corporate/*` sub-project is empty. There is no forked/installed Next.js
SDK anywhere in this workspace to use as a model.

I then traced the Dart installer mechanism to find its shared implementation, to see whether an analogous
Next.js one exists anywhere else in the broader `RokctAI` workspace (not just under `corporate/`):

- `corporate/polaris/dart/install.py` does `sys.path.append('.rokct'); import sdk_installer_base;
  sdk_installer_base.install_sdk_files_and_routes('polaris_sdk')`. This confirms Dart SDKs use a
  filesystem-copy installer (`manifest.json` `"installs"` array of `{from, to}` pairs, copied via
  `shutil.copytree`/`copy2`, with `${package}` placeholder substitution) into a host Flutter app — not an
  npm/pub dependency.
- The canonical/master copy of that installer logic lives at
  `The-Rokct-Protocol/core/utils/flutter/sdk_installer_base.py` — i.e. it is explicitly namespaced
  `utils/flutter/`.
- `The-Rokct-Protocol/core/utils/` contains exactly five sibling installer domains:
  `agent_deligation`, `flutter`, `frappe`, `opportunities`, `startup_os`. **There is no `nextjs`
  (or `react`/`web`) entry.**
- A working, already-installed copy of the Flutter installer confirms the pattern in practice:
  `supacharge/.rokct/sdk_installer_base.py` (installed copy) uses `manifest.json`'s `"installs": [{from,
  to}]`, resolves a `home_sdk` flag, copies files/directories from the SDK's own tree into the host app's
  `lib/`, and tracks state in `.rokct/install_state.json`.

**Conclusion:** the installable-SDK convention for Dart is real and verifiable, but the equivalent for
Next.js **does not exist yet anywhere in this workspace** — not in `corporate/*/nextjs/`, not in
`core/utils/`, and no `sdk_installer_base`-equivalent script or `manifest.json` schema for a Next.js target
was found anywhere. Per the brief's explicit instruction not to guess through the packaging question, I am
not inventing one. This needs a deliberate design decision (likely: define
`core/utils/nextjs/sdk_installer_base.py` following the same `manifest.json` `{from, to}` copy pattern as
Flutter, since Next.js apps — like Flutter apps — are "install into a folder to form a whole app," not npm
dependencies per the brief's own framing) before any files are physically forked into
`corporate/polaris/nextjs/`.

## 2. `handson/all/lending/` vs `platform/lending/` — RESOLVED: fork `handson/all/`, exclude `platform/`

This is unambiguous once you check which side of the split is actually wired to a page and which side is
unreferenced.

**`app/handson/all/lending/` — the real, live implementation.** Confirmed by direct call chain:
`app/handson/all/lending/operations/page.tsx` → `app/actions/handson/all/lending/operations.ts`
(`triggerLoanInterestAccrual`, `triggerLoanSecurityShortfall`, `triggerLoanClassification`,
`getProcessLogs`, each gated by `verifyLendingRole()`) → `app/services/all/lending/operations.ts`
(`OperationsService`) → `BaseService.call(...)` with real Frappe dotted-path method names, e.g.
`lending.loan_management.doctype.process_loan_interest_accrual.process_loan_interest_accrual.process_loan_interest_accrual_for_loans`.
This is genuine, connected, backend-calling code.

**`app/actions/platform/lending/operations.ts` (+ its `services/platform/...`, `components/platform/...`,
`lib/platform/...` siblings) — orphaned generator scaffolding, not a parallel canonical implementation.**
Evidence:
- The file header literally says `Author: ROKCT Code Generator` — it's templated output, not hand-written.
- `grep`-ing the entire `RokctAI_frontend/app` tree for any import of
  `actions/platform/lending/operations`, `services/platform/lending/operations`,
  `components/platform/forms/lending/operations`, or `lib/platform/validators/lending/operations` finds
  **zero references** outside the generated cluster's own internal imports (the component imports the
  action, the action imports the service — a self-contained, unreferenced chain). No page renders it, no
  route calls it.
- It targets a structurally different backend dispatch convention
  (`gateway = "rcore.platform.api.control" | "rcore.platform.api.tenant"`, `cmd: "lending:operations:..."`)
  versus the live code's direct Frappe dotted-path calls — consistent with it being scaffolding from a
  newer/alternate code-generator pass (an `rcore` gateway-command style) that was generated once and never
  wired up, rather than a second in-use variant.

**Verdict:** fork only the `handson/all/lending/` tree (pages, actions, services) plus the
non-`platform`-prefixed supporting files (`app/templates/lending/*`, `lib/platform/validators/lending/`
and `components/platform/forms/lending/` are *misleadingly path-named* `platform/` but — checked
individually — the `operations.ts`/`operations.tsx` variants under those two paths are the same orphaned
generated pair as above and should be excluded; there is no other validator/component file for lending
outside this generated pair, so lending forms/validation logic in the live app is evidently inlined in the
page components themselves rather than centralized — confirm this by reading the live `operations/page.tsx`
before assuming a validator gap needs filling).

## 3. HRMS staff loans — confirmed unrelated, correctly excluded

`app/actions/handson/all/hrms/loans.ts` calls `LoanService` from `app/services/all/hrms/loans` (a
different service file, not shared with lending) and revalidates `/handson/all/hrms/loan` — an entirely
separate HR/payroll staff-loan feature with no shared services, actions, or components with customer
lending. Correctly out of scope, confirmed by code inspection rather than filename alone.

## 4. NCR report templates — confirmed real, compliance-critical, legible

`app/templates/lending/Form20Template.tsx` (read in full, 357 lines) is a real South African National
Credit Act Form 20 "Pre-Agreement Statement & Quotation" — includes NCRCP license number field, principal/
interest/service-fee/initiation-fee/VAT/insurance cost breakdown, early-settlement rights disclosure,
default administration cost disclosure, marketing opt-out disclosure, asset-backed security pledge vs.
affordability declaration branching, and a consumer signature block. This is genuinely legally-significant
content, not a generic invoice template — confirms the brief's warning to treat it carefully. Did not
alter it. `AssuranceReportTemplate.tsx` and `Section129Template.tsx` (Section 129 = NCA default notice) were
not read in full this pass but are named after equally real NCA provisions and should get the same
"read before touching" treatment when the fork is actually executed.

`app/services/all/lending/ncr.ts` (189 lines) and `app/actions/handson/all/lending/ncr_reports.ts` (24
lines) exist and sit under the `all/` (i.e. live) tree, not `platform/` — in scope for forking, not
excluded by the handson/platform resolution above.

## 5. Cross-references for future backend integration (not reconciled this pass)

- `corporate/polaris/docs/credit-risk-algorithm.md` documents the Frappe-side `rlending` customization
  layer (`ScoringEngine`, `PaasOrderAnalyzer`) on top of the official Lending app, and flags that
  `api/decision.py`'s `get_credit_score()` is currently a hardcoded stub and `api/lending_mocks.py` is
  entirely placeholder. Whatever Next.js SDK forked here will eventually need its decision-engine-calling
  action (`app/actions/handson/all/lending/decision_engine.ts`) pointed at the real scoring wiring once
  that backend gap is closed — not yet, per that doc's own "worth confirming" note.
- `corporate/polaris/docs/fork-lending-investigation-brief.md` (+ its companion
  `fork-lending-investigation-report.md`, already present in the same `docs/` folder) is the parallel
  Frappe-backend fork investigation. This Next.js fork's server actions/services currently call Frappe
  dotted-paths belonging to the *official* Lending app installation
  (`lending.loan_management.doctype....`) — once the backend fork changes those paths/method names, the
  forked Next.js services will need a corresponding update. Full reconciliation deferred as a follow-up per
  the brief.

## 6. Proposed structure for `corporate/polaris/nextjs/` (plan only — not executed)

Once the packaging convention from §1 is actually decided (most likely: a new
`core/utils/nextjs/sdk_installer_base.py` + `manifest.json` `{from, to}` copy-into-host-app pattern
mirroring Flutter's), the resolved file set from §2–§4 maps as:

```
corporate/polaris/nextjs/
  manifest.json                  # {name: "polaris_sdk", installs: [...], routes: [...]}
  install.py                     # mirrors dart/install.py: import sdk_installer_base (nextjs variant)
  templates/                     # files copied verbatim into the host Next.js app
    app/handson/all/lending/
      layout.tsx, page.tsx
      adjustments/, application/{new,[id]}/, demand/, loan/{[id]}/, operations/, product/,
      repayment/, restructure/, transfer/, write-off/, templates/debicheck/,
      reports/{assurance-report,compliance-report,form-20/[id],ncr-form-40,section-129/[id]}/
    app/actions/handson/all/lending/
      application.ts, decision_engine.ts, demand.ts, lifecycle.ts, loan.ts, ncr_reports.ts,
      operations.ts, product.ts, refund.ts, repayment.ts, reports.ts, seed_product.ts, transfer.ts
    app/services/all/lending/
      application.ts, decision.ts, demand.ts, lifecycle.ts, loan.ts, ncr.ts, operations.ts,
      product.ts, refund.ts, repayment.ts, reports.ts, transfer.ts
    app/templates/lending/
      AssuranceReportTemplate.tsx, Form20Template.tsx, Section129Template.tsx
```

Excluded from the fork: `app/actions/platform/lending/operations.ts`,
`app/services/platform/lending/operations.ts`, `components/platform/forms/lending/operations.tsx`,
`lib/platform/validators/lending/operations.ts` (orphaned generator scaffolding, §2), and
`app/actions/handson/all/hrms/loans.ts` / `app/handson/all/hrms/loan/` (unrelated HRMS domain, §3).

## Why execution stopped here

Per the brief: "Only execute the actual file fork/copy into `corporate/polaris/nextjs/` if both the
packaging convention and the handson/platform resolution are clear from evidence; otherwise stop at the
plan." The handson/platform split is clear (§2, resolved with evidence). The packaging convention is
**not** clear — no working Next.js SDK installer exists anywhere in this workspace to verify against (§1).
Copying files into `corporate/polaris/nextjs/` without first deciding (with the user/a follow-up session)
whether a `sdk_installer_base`-for-Next.js needs to be written first, and what its `manifest.json` shape
should be, would be guessing through the exact question the brief said not to guess through. Stopping at
this plan.
