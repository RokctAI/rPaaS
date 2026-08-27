# Tender module (TenderAssist)

The tender SDK module: research docs plus the composable `frappe/` and `nextjs/` halves.

## Module halves

- **[frappe/](frappe/)** — backend package: the tender doctypes (Tender Bid, checklists, workflow templates, opportunity cache) extracted from control, the tenders/opportunities API endpoints, and the deterministic SA-tender compliance layer. Rules ship as fixture data (`frappe/fixtures/`) mapped from the completion guide below — updating a rule is a fixture/desk edit with zero code changes; validators are plain field/date/set comparisons. **No AI anywhere in the pipeline.** Compose entry for consumers: `../corporate/tender/frappe`.
- **[nextjs/](nextjs/)** — frontend package (polaris_sdk pattern: `manifest.json` + `install.py` + `templates/`): the opportunities pages, bid/checklist UI, tender admin page, and their services/actions. These copies are the canonical, drift-fixed versions (gateway cmds carry the `control:` prefix; admin queries match the real doctype schemas).

## Persona layout (role-based composition)

Both halves declare the composer `app_type` personas `control` and `tenant` (the roles the frappe/nextjs composers strip on):

- **frappe** — hub-only code lives under `frappe/src/control/` (the `api/tenders` + `api/external` endpoints, the `api/opportunity_utils` fetch layer, and the daily refresh task); it composes only into control-role shells, whose manifest flavor block also carries the `whitelisted_methods` aliases (public `{app_name}.api.tenders.*` cmd names unchanged), the daily scheduler event, and the `requests` dependency. Everything else at `frappe/src/` top level is common to every role: the deterministic compliance layer (`src/compliance/` — validators, scoring, computed fields run wherever Tender Bid lives), the weekly artifact-expiry sweep, the `Tender Bid` doc_events wiring, and the fixtures. `doctype/` trees are not role-scoped by the composer — all roles get all doctypes.
- **nextjs** — the shell frontend is hub-only today, so the whole surface (admin CRUD, bids, public opportunities pages, services, the checklist component that imports control services) lives under `templates/control/` and installs only into control-role hosts via the manifest's `app_type.control` flavor block; the manifest top level is empty/common. A later tenant-facing split is a manifest/config decision, not a code move.

## Research docs

- **[SA-Tender-Completion-Guide.md](SA-Tender-Completion-Guide.md)** — a complete working guide (v2, corpus-verified against ~1,198 packs) to completing a South African tender pack (triage, forms, registrations, pricing, functionality, submission traps), written for a capable person or small business with no procurement-law background.
- **[Auto-Submission-Feasibility-Report.md](Auto-Submission-Feasibility-Report.md)** — feasibility report and architecture proposal for auto-submission in TenderAssist: which submission channels exist across SA tenders, what can legally and practically be automated, and a proposed architecture.
- **[CSD-API-Findings.md](CSD-API-Findings.md)** — research findings on whether South Africa's Central Supplier Database (CSD) exposes an API: machine interfaces exist but are restricted to organs of state; no supplier-facing API, with practical implications for TenderAssist.
- **[Corpus-1200-Findings-Report.md](Corpus-1200-Findings-Report.md)** — delta-verification report from analyzing ~1,200 fresh eTenders packs (2026-08-18) against the completion guide: 10 confirmed contradictions and 24 edits, feeding guide v2 (The-Rokct-Protocol PR #248).
- **[buyer-profiles/](buyer-profiles/)** — per-buyer quirk sheets from the 2026-08 ~1,198-pack corpus (14 buyers: metros, national departments, SOEs): submission channels, arrears windows, hard-copy rules, cure tiers, vetting, financial demands, and distinctive kill rules, with pack-level citations. See its README for the buyer index.
- **[rules-table.md](rules-table.md)** / **[rules-table.csv](rules-table.csv)** — machine-readable rules table (65 rows: rule id, gate/kill/score type, trigger, severity, source packs), the compliance-rule companion to the completion guide.
- **[functionality-thresholds.md](functionality-thresholds.md)** / **[functionality-thresholds.csv](functionality-thresholds.csv)** — observed minimum-functionality-threshold distribution across the corpus (238 explicit thresholds; mode/median 70, range 36–100).
- **[SDK-Improvement-Findings.md](SDK-Improvement-Findings.md)** — actionable findings for the agent building/improving the SDK, distilled from the four worked mock sample packs (`mock-samples/`): 11 gap/fixture/code findings with evidence and recommendations, plus what already works and must not be churned; prose + machine-readable table.

## Provenance

Built 2026-08-18 from a systematic analysis of ~37 real South African tender packs (municipal, provincial, national, and SOE), then recalibrated to the v2 guide after delta verification against ~1,198 eTenders packs (Corpus-1200-Findings-Report.md). The completion guide (v2) also ships in The-Rokct-Protocol `tender-assistant` skill (v1: PR #246; v2: PR #248); the compliance fixtures in `frappe/fixtures/` are mapped from v2.

Future tender research docs land in this directory.
