# TenderAssist SDK — Assessment and Ranked Improvement Plan

Date: 2026-08-24. Point-in-time, read-only assessment of the tender module
at commit `e8a0348` (merge of PR #57); no code changes accompany this
document. Companion to `SDK-Improvement-Findings.md` (the F-01…F-15 /
O-01…O-06 ledger), which it takes as delivered baseline.

## 1. Where it lives

- **Not a dedicated repo.** The tender SDK is a module at **`RokctAI/corporate` → `tender/`**. It was extracted from `control` (control PR #134 / corporate PR #25, 2026-08-18); zero tender code remains in control (`control/hooks.py` defers to the SDK manifest). SDK_ECOSYSTEM.md records it as the first executed control-flavor extraction.
- **No Flutter half — by explicit owner decision** (2026-07-26): TenderAssist v1 is Frappe (`control` persona) + Next.js only. An earlier draft proposing a `tender_sdk` Flutter package was corrected by the owner. ADR-005 dart rules are therefore N/A.
- Halves:
  - `tender/frappe/` — backend package, composer manifest (`manifest.json`, name "tender"), all code under `src/control/` (control-persona only; `tenant: {}` is declared empty). Deps: requests, Pillow, pypdf.
  - `tender/nextjs/` — frontend package (polaris_sdk pattern: `manifest.json` name "tender_sdk" + `install.py` + `templates/control/`), 32 files: opportunities pages, bids/checklist UI, admin (handson) CRUD page, services/actions.
  - Research corpus docs at module root: SA-Tender-Completion-Guide (v2, corpus-verified vs ~1,198 packs), rules-table (65 rules), functionality-thresholds (238 observations), buyer-profiles/ (19 buyers), Award-Outcomes-Research (32,589 published awards), Suitability-Scoring-Model/Research, CSD-API-Findings, Auto-Submission-Feasibility-Report, Corpus-1200-Findings-Report, SDK-Improvement-Findings (F-01…F-15 + O-01…O-06), and 5 worked mock-sample packs.

## 2. What it actually does

Deterministic, **no-AI** SA public-sector tendering assistant, control-plane-side:

- **Opportunity catalog layer**: daily scheduler → `tasks.py:refresh_opportunities_cache` pulls the pre-synced published catalog from `https://raw.githubusercontent.com/RokctAI/opportunities/main/published/api/` (hardcoded `BASE_URL`, 24h TTL). A **direct eTenders fetcher** (`_fetch_and_cache_tenders_on_control`) is implemented with **sequential ocid ID enumeration** (never list pagination — F-14's proven-lossy endpoint), gated by `Tender Control Settings` (`section_direct_fetch`, `last_fetched_release_id`, `refetch_window_ids`, `max_ids_per_run`) into the `Raw Tender Cache` doctype.
- **23 doctypes** (`src/control/doctype/`): Tender Bid (with overlay_regime, contract_term_months, escalation fields, submission_channel, outcome_value/notes), Tender Bid Returnable (artifact attach/attest fields), Tender Business Profile (+directors, witnesses, capability items), functionality sections, pricing periods, compliance rules/regimes/form templates (shipped as fixtures — rule edits are data edits), renewal watch/event, workflow templates/tasks, compliance artifacts, raw tender cache, Intelligent Task Set / Generated Tender Task (admin-CRUD'd from the handson page; backend code never touches them).
- **22 whitelisted endpoints** (21 in `src/control/api/tenders/` + `api/external/get_public_opportunities`): catalog (get_relevant_tenders/grants/equity, get_tender_detail), bid lifecycle (claim, get_my_bids, update_bid_status with gate enforcement on Submitted, update_checklist_item), pack pipeline (parse_tender_pack, seed_bid_returnables, generate_bid_pack incl. signature stamping, get_pack_status, attach_returnable_artifact attach→attest, dispatch_bid_pack — 3-tier email dispatch gated on submission readiness + explicit confirm), quotation (create_bid_quotation, year-by-year pricing), intelligence (get_tender_suitability two-stage gates+fit-score, get_renewal_radar, get_low_competition_tenders, get_buyer_dossier, get_enrichment_stats), entitlement via `Subscription Plan.enable_tenders`.
- **Compliance layer** (`src/control/compliance/`, 17 modules): fixture-driven rules (universal fatal spine GATE-*/KILL-*), scoring (80/20 vs 90/10, price-points formula, functionality elimination incl. multi-section child table + explicit "no scored functionality" state), submission gate, checklist sync, pack lints, preference frameworks (multi-framework packs), pricing bands, market context + buyer dossiers (precomputed from the awards dataset, committed JSON with drift-check), suitability, renewal ledger math, enrichment gate (advert-only records ⇒ pack-collection fatal gate), artifact expiry sweep.
- **Deterministic pack parser** (`src/control/parsing/`): scalar extraction (closing date/time, tender number across line wraps, splits, submission channel, wet-ink) + returnable extraction (Form/Annexure/lettered-list/bare-regime-heading regex families with lookahead title joins). Verified 21/21 returnables on the real 65-page Musina PDF (O-01 closed).
- **Pack builder** (`pack_builder.py`): HTML bid pack, auto-fill 91.8–97.1% verified across mock packs, amber/red gap rendering, fatal-gate warning page, per-regime pricing schedules.
- **Next.js half**: all calls go through the platform gateway (`platformCall` / `ControlBaseService.call`) with canonical `control:` cmd names matching manifest aliases — gateway-compliant; a comment in bids.ts records that unprefixed cmds "never existed on the gateway and failed silently."

## 3. Health

**Tests: strong and honest.**

- 15 standalone verify suites (`tender/frappe/tests/verify/`), frappe stubbed in-memory, real modules loaded with `{app_name}` substituted. **All 15 pass: 803/803 checks** (buyer_dossiers 48, competition 62, market_context 41, o4_smoke 19, pr_c 46, pr_d 68, pr_e 63, preference_delivery 29, pricing_bands 46, renewal 77, suitability 116, wave1 61, wave2_pr_a 51, wave2_pr_b 46, wave3 30; without pypdf installed pr_d's real-PDF smoke degrades to a single SKIP check — pr_d 67, total 802). market_context additionally rebuilds committed JSON from the committed awards CSV and fails on drift (compute-once with drift-check — genuinely good).
- Caveat: `verify_wave2_pr_b` shells `git show 686850c:` for a byte-identity baseline — it fails on shallow clones until the history is deepened. `verify_pr_e`'s real-PDF section and `verify_o4_smoke`'s engine-provenance section SKIP (not fail) without the uncommitted Musina PDF / real StartupOS artifacts.
- 4 bench tests (`tests/test_*.py`) require a composed bench — unrunnable standalone (known: O-06).

**Hygiene: clean with one real bug.**

- No CRLF anywhere in the module. `__pycache__` handled (O-05 closed: suites set `dont_write_bytecode`). MIT headers everywhere. Fixtures well-formed.
- **Bug: 13 endpoints log a literal `{trace_id}`** — `print(f"[tender.api] ... trace_id={{trace_id}}", file=sys.stderr)` double-braces the variable inside an f-string, so the trace id never prints (get_renewal_radar, get_tender_workflow_template, get_my_bids, get_low_competition_tenders, get_tender_suitability, get_enrichment_stats, update_checklist_item, get_relevant_equity/tenders/grants, get_tender_detail, get_buyer_dossier, get_public_opportunities). Others (e.g. update_bid_status) do it correctly. The composer does plain `str.replace("{app_name}", ...)` and never touches generic braces, so the doubling serves no purpose. Trivial 13-line fix.
- Telemetry generally is bare `print` to stderr (all 22 endpoints) — works, but no structured/admin telemetry like the mature SDKs.
- **F-09 largely resolved**: compliance/parsing/pack_builder core is composition-independent (no `{app_name}`; most modules import no frappe at all). Only `computed_fields.py`, `renewal_sync.py`, `tasks.py`, `tender_business_profile.py` + the 22 thin endpoint shims and their `api/` helpers (`opportunity_utils/`, `tender_entitlement.py`) still carry `{app_name}` imports (fleet convention for shims).
- No dead code found: Intelligent Task Set / Generated Tender Task look orphaned backend-side but are CRUD'd by the nextjs handson admin page via `frappe.client`; Tender Profile Witness and Tender Workflow Task are live child tables.
- `docs/api/` exists for both halves (26 + 12 md files) but covers only a subset of source files.

**Findings ledger status (vs SDK-Improvement-Findings.md):** F-01 (overlay regime), F-02 incl. parser calibration (21/21), F-03/F-04 (wave1), F-05 (sections), F-06 (term/escalation/year-by-year pricing), F-07 (capability items), F-08 (enrichment gate + stats), F-10, F-11 (quirks), F-12 (preference frameworks), F-13 (3-tier dispatch + submission_channel), F-14 (ID-enumeration fetcher), F-15(b) (attach/attest hook) — **all delivered and verified**. O-01 closed (21/21). Still open: **O-02** (≥2-per-letter calibration), **O-03** (gate-pattern over-fire measurement) — both need the 163k-release corpus run; **O-04** (real-artifact e2e — blocked on studio-side wiring owned by the startupos workstream); O-06 (bench-test limitation, mitigated by verify suites).

## 4. Comparison with mature SDKs (forex, weather)

| Pattern | forex (rforex) | tender | Verdict |
|---|---|---|---|
| Pure rule modules, frappe-free, unit-tested | yes (161 tests, `python -m unittest`) | yes — compliance/parsing core is frappe-free; 803-check verify harness | at parity; tender's harness is arguably richer (real-PDF, drift checks) |
| Swappable data-source seam | `rates/provider.py` + frankfurter impl + cache | partial: two sources exist (published catalog / direct eTenders) but `BASE_URL` is hardcoded and there's no provider abstraction | worth a light seam; full provider abstraction is overkill for one national feed |
| Compute-once caching | rates cache | market_context.json + buyer_dossiers.json precomputed from awards CSV, drift-checked; 24h catalog cache | at parity — a genuinely good implementation |
| Manifest↔code agreement test | yes (both directions) | no equivalent for the 66-alias whitelist map | cheap win |
| Outcome/honesty machinery | strategy versions immutable, checksummed; upgrade offers never auto-act | honesty excellent (amber/red gaps, ASSUMED labels, no_bid without fake score, fatal gates never silent); **outcome capture exists (Awarded/Lost + outcome_value) but nothing aggregates or feeds it back** | the gap is the outcome LEDGER, not honesty |
| Immutability/checksums | spec checksums freeze published versions | none — dispatch regenerates the pack at send time; only dispatched_on/to recorded | genuine gap (see plan #11) |
| Admin telemetry | structured | print-to-stderr, 13 of them broken | modest gap |

Doesn't apply to tender: broker credentials/margin machinery, tenant-persona proxying (tender is control-only by design until a tenant split, which README notes is a manifest decision, not a code move).

## 5. Ranked improvement plan

### (a) Fixes / hygiene

**1. Fix the 13 broken `{{trace_id}}` log lines.** They print the literal string `{trace_id}` instead of the request's X-Trace-Id — the one concrete bug found. Mechanical find-replace, and the correct single-brace form already exists in-tree (update_bid_status.py) as the pattern to match. Fold in a lint/verify check that no `{{` survives in f-string log lines so it can't regress.

**2. Snapshot verify_wave2_pr_b's baseline out of git history.** The suite runs `git show 686850c:tender/frappe/src/control/pack_builder.py` for its byte-identity check, so it fails on any shallow clone (CI runners, fresh shallow checkouts) with a subprocess error that looks like a real failure. Commit the baseline snapshot under `tests/verify/data/` (or degrade to SKIP when the commit is absent, matching the suite family's existing SKIP discipline).

**3. Make the catalog `BASE_URL` a setting.** `api/opportunity_utils/__init__.py:26` hardcodes the GitHub raw URL for the published catalog; `Tender Control Settings` already governs the direct-fetch path, so a `catalog_base_url` field with the current value as default completes the data-source seam the mature SDKs have — and makes staging/test catalogs possible without code edits. A full forex-style provider abstraction is not warranted for one national feed.

**4. Run the two open calibration measurements (O-02, O-03) against the 163k-release corpus.** The ≥2-per-letter returnable rule and the F-03 subject-pattern gates are both calibrated on single packs, with CALIBRATION NOTEs admitting it; the complete eTenders corpus (163,321 releases) exists precisely for this. Record measured drop-vs-harvest and per-gate fire rates next to the notes. *Blocked on Ray: the corpus lives in another workstream's storage (`etenders-corpus`, not committed by instruction) — needs access or a re-fetch decision.*

**5. Structured telemetry instead of bare stderr prints.** All 22 endpoints `print()` to stderr; once #1 is fixed the lines are at least correct, but converting to `frappe.logger()`/a small telemetry helper would match fleet practice and make trace ids actually queryable. Low urgency, pairs naturally with #1.

**6. Manifest↔code agreement test.** `manifest.json` maps 66 aliases (public, `control:`, and legacy dotted names) to 22 endpoint dotted paths by hand; forex ships a test asserting manifest and code agree in both directions. A verify suite that walks the manifest, substitutes `{app_name}`, and asserts every target function exists (and every whitelisted function is mapped) would catch alias drift — the exact class of silent-failure bug the bids.ts comment says already happened once.

### (b) Features likely wanted next

**7. Close the O-04 loop when studio wiring lands.** The attach→attest returnable-artifact hook is delivered and smoke-tested against synthetic files; the startupos workstream owns producing real `business_profile` + `compliance_log`. When that lands, run the committed o4 smoke in real-files mode and wire the end-to-end path. *Blocked on Ray/startupos workstream — nothing for the SDK builder to do yet except keep the suite green.*

**8. Portal-channel submission support.** `submission_channel` now distinguishes physical-box / portal / email-allowed, and dispatch covers the email tier — but portal (eTenders online submission) is unautomated, and the Auto-Submission-Feasibility-Report is explicit that channels, legality, and credentials vary. Even without automation, the bid record could carry portal URL + per-channel "how this must actually be delivered" rendering (partially present) plus a portal-submission checklist row. *Full automation blocked on Ray: legal review + portal credentials; CSD has no supplier-facing API (CSD-API-Findings).*

**9. Suitability calibration from live cards, on a schedule.** The suitability model was calibrated once against 1,990 live cards (2026-08-23). Cards churn; a periodic recalibration report (distribution drift of gates fired, bands, confidence) using the existing enrichment-stats machinery would keep the fit score honest over time. Cheap because the scoring is deterministic and the catalog is already cached.

### (c) Suggestions possibly not yet on the roadmap (each grounded in existing code)

**10. Bid deadline watcher.** Every claimed bid carries `closing_date`, statuses Watching/Preparing, and open-gate state — but nothing watches the clock: the only scheduled user notification is the weekly compliance-artifact expiry email. A daily sweep — "bids closing within N days that still have open fatal gates / unattested returnables / unsatisfied mandatory returnables" — reusing `artifact_expiry.py`'s exact sendmail + `User.receive_tender_notifications` opt-in pattern is nearly free and attacks the #1 real-world kill rule (KILL-01: late = cannot be admitted). Extend to briefing dates: suitability already parses `briefing_date_and_time` and gates on *missed* compulsory briefings — a reminder *before* the briefing converts a post-mortem gate into a save.

**11. Dispatch checksum / immutability ledger.** `dispatch_bid_pack` **regenerates** the pack at send time (`generate_bid_pack(bid, sign=...)`), so the pack the user reviewed and the pack the buyer received can differ if the profile or quotation changed in between — and nothing records what was actually sent beyond `dispatched_on`/`dispatched_to`. Store the sha256 of the dispatched HTML + manifest (and attach the sent bytes as a File on the bid) in an append-only dispatch log. This is the forex "published version is checksummed and frozen" discipline applied where it matters most here: disputes about what was submitted, under rule families where alterations disqualify (KILL-ALT-OFFER). Same mechanism extends to attested returnable artifacts (hash at attest time, so later file edits are detectable).

**12. Award-outcome ledger.** The bid already captures Awarded/Lost + `outcome_value`/`outcome_notes`, and Award-Outcomes-Research proves the public feed carries award blocks (winner, value) for ~20% of releases, gained via later re-fetch — which the ingest design already does (`refetch_window_ids`). Two composable pieces: (i) aggregate the user's own outcomes (win rate by buyer/category/value band, quoted-vs-awarded value against the pricing bands they were shown); (ii) auto-match claimed tenders' ocids against re-fetched releases to record who actually won and at what value, even when the user forgets to update status. The research doc's own caveat is the design constraint: this is market-context calibration, never win-probability prediction — no fake numbers, matching the SDK's no-score-without-comparability doctrine. The dataset's own numbers bound what (ii) can deliver: award blocks name a winner 99.98% of the time but carry a usable value less often (72.01% non-zero; 22,311 of 32,589 rows survive the `amount_flag` exclusions — 9,123 zero, 825 <R100, 330 >R10bn, flagged in the committed CSV, never dropped); publication is heavily buyer-skewed (SARS 75.74% and Justice 71.96% of releases carry awards vs ESKOM 9.87% and Tshwane/Joburg/Mnquma 0.00% — a claimed tender at a non-publishing buyer will simply never match, and that means "no award published", never "lost"); and the feed carries no award dates (nor tenderer counts or contract periods), so award lag is unmeasurable and no finite `refetch_window_ids` trailing window can be tuned from data — awards that surface after the window has passed are only recoverable by re-enumerating old IDs.

**13. Unified compliance calendar.** Four date streams exist in four silos: compliance-artifact expiries (weekly email only), bid closing dates, briefing dates, and renewal-watch expected-advertisement windows (renewal radar). One `get_compliance_calendar` endpoint merging them into a dated feed — plus a calendar panel in the nextjs bids UI — turns the SDK from per-tender tooling into a bid-desk operating rhythm. All data already computed; this is assembly, not new logic. One honesty note for the renewal stream: the research doc's validation confirmed only 2 of 12 sampled due predictions as unambiguous same-service returns (both within ±2.2 months of schedule), so the calendar should render expected-advertisement windows as watch items, never as commitments.

**14. Notification seam.** Outbound comms are two direct `frappe.sendmail` call sites (artifact expiry, dispatch); #10 and #13 would add more. A single `notify()` helper (channel-pluggable: email now, the core `comms` module or others later) keeps the graceful-degradation pattern (try/except + log_error, audit only on accepted send) in one place instead of copied per feature.

**15. Wire or retire `tender_country`.** `Tender Control Settings.tender_country` exists but nothing reads it — the fixture layer is SA-specific throughout. Either scope the SA regime/rule fixtures behind the country value (the fixtures-as-data architecture already makes "a country is a fixture pack" the natural internationalization story), or drop the field until that's real. As-is it implies configurability that doesn't exist — the one place the module's otherwise excellent honesty discipline slips.

## 6. Blocked on Ray

- **Corpus access** for O-02/O-03 calibration runs (`etenders-corpus`, another workstream's storage, not committable by instruction).
- **Studio-side wiring** for O-04 real-artifact e2e (startupos workstream owns it).
- **Portal auto-submission**: legal position + portal credentials (Auto-Submission-Feasibility-Report); CSD offers no supplier API.
- **Outgoing Email Account** on the bench — dispatch and any watcher emails degrade gracefully but silently without one.
- **Tenant-facing split** of the nextjs surface (README: a manifest/config decision) — product call, not code.
