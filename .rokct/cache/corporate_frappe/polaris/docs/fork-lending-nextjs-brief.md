# Task Brief: Fork RokctAI_frontend's Lending Module into `polaris_sdk`'s Next.js SDK

> Self-contained brief for a fresh session (context-limited handoff). Read in full; should not require
> the conversation that produced it. Related but separate from `fork-lending-investigation-brief.md`
> (that one is about the Frappe/Python backend forking away from the official Lending app; this one is
> about the Next.js frontend).

## Critical architecture fact — confirm before assuming anything

**Next.js SDKs in this workspace are installed into a folder to form a whole app — they are NOT consumed
as an npm package dependency**, unlike Dart SDKs (which mix both patterns: `pubspec.yaml` path deps for
importable code, plus a separate `templates/` folder for files that get physically copied into the host
app). Before writing anything, find a working example of how an existing `nextjs/` SDK folder is
structured and how its installer (if one exists, likely mirroring the Dart `install.py`/`manifest.json`
pattern) actually installs it into a host app. Do not assume the Dart convention carries over unchanged —
verify by example first.

## Goal

`corporate/polaris/nextjs/` currently contains nothing but a `.gitignore`. `RokctAI_frontend` already has
a full, real, regulation-aware Next.js lending implementation. Fork/restructure it into `polaris_sdk`'s
own Next.js SDK so it can be installed into any Next.js host app, not remain hardcoded inside
`RokctAI_frontend` specifically.

## Full source inventory (confirmed real, already gathered — don't re-discover, just verify still current)

Pages (`app/handson/all/lending/`): `layout.tsx`, `page.tsx`, and subfolders `adjustments/`,
`application/` (+ `new/`, `[id]/`), `demand/`, `loan/` (+ `[id]/`), `operations/`, `product/`,
`repayment/`, `restructure/`, `transfer/`, `write-off/`, `templates/debicheck/`, and `reports/` (+
`assurance-report/`, `compliance-report/`, `form-20/[id]/`, `ncr-form-40/`, `section-129/[id]/`) — the
`reports/` subtree is the regulatory compliance surface, treat it as its own coherent unit, not generic
CRUD pages.

Server actions (`app/actions/handson/all/lending/`): `application.ts`, `decision_engine.ts`, `demand.ts`,
`lifecycle.ts`, `loan.ts`, `ncr_reports.ts`, `operations.ts`, `product.ts`, `refund.ts`, `repayment.ts`,
`reports.ts`, `seed_product.ts`, `transfer.ts`. Also `app/actions/platform/lending/operations.ts` (note:
different location, `platform/` not `handson/all/` — figure out what distinguishes these two locations
before assuming they're duplicates or which one is canonical).

Services (`app/services/all/lending/`): `application.ts`, `decision.ts`, `demand.ts`, `lifecycle.ts`,
`loan.ts`, `ncr.ts`, `operations.ts`, `product.ts`, `refund.ts`, `repayment.ts`, `reports.ts`,
`transfer.ts`. Also `app/services/platform/lending/operations.ts` (same handson-vs-platform split as
actions — resolve this before forking, don't fork both blindly if one is dead/superseded).

Report templates (`app/templates/lending/`): `AssuranceReportTemplate.tsx`, `Form20Template.tsx`,
`Section129Template.tsx` — these are named after actual South African NCR (National Credit Regulator)
regulatory forms. Treat these as legally-significant, not stylistic templates — do not alter their
structure/fields without understanding what each form is actually required to contain.

Components: `components/platform/forms/lending/operations.tsx`.

Validators: `lib/platform/validators/lending/operations.ts`.

Generated docs (if useful for understanding intent quickly without reading every file):
`docs/api/app_actions_handson_all_lending_*.md`, `docs/api/app_services_all_lending_*.md`,
`docs/api/app_handson_all_lending_*_page.md` (one per source file above, auto-generated — check these
first, they may already summarize each file's purpose faster than reading raw source).

Note: `app/actions/handson/all/hrms/loans.ts` and `app/handson/all/hrms/loan/` also exist — this is HRMS
(HR/payroll) staff loans, a *different* domain from customer lending. Do not fork this into `polaris_sdk`
by mistake just because it also matches "loan" — confirm it's genuinely unrelated before excluding it,
don't just assume from the filename.

## What to actually do

1. Read the generated `docs/api/*.md` files first for a fast overview, then the real source for anything
   load-bearing (especially the NCR report templates and `ncr_reports.ts`/`ncr.ts` — get these right,
   they're compliance-critical).
2. Resolve the `handson/all/lending/` vs `platform/lending/` duplication/split — don't fork both without
   understanding why two locations exist.
3. Determine (per the architecture fact above) how this should actually be packaged as an installable
   Next.js SDK — study a working example first.
4. Fork the resolved, understood set into `corporate/polaris/nextjs/`, following whatever installable-SDK
   convention you found in step 3.
5. Cross-reference with `corporate/polaris/docs/credit-risk-algorithm.md` (the Frappe-backend scoring
   design) and `fork-lending-investigation-brief.md` (the Frappe-backend Lending-app fork) — this Next.js
   frontend should ultimately talk to whatever backend API surface those produce, though reconciling that
   integration in detail can be its own follow-up if it's too much for one pass.

## Deliverable

Same posture as the other Polaris briefs: report/plan what you found and propose the fork structure
before executing a large restructure, if anything is genuinely ambiguous (especially the handson/platform
split and the installable-SDK packaging question) — don't guess through open questions on a
regulation-adjacent feature.
