# TenderAssist Mock Sample Packs

Full worked outputs of the TenderAssist SDK (`tender/frappe` — deterministic,
fixtures-as-rules, **no AI**) for five real South African tenders, so the
output quality and value of the SDK can be judged end-to-end on real packs.

> **FICTIONAL COMPANY NOTICE.** The bidder in every sample is **Umzansi
> Infrastructure Group (Pty) Ltd — a FICTIONAL PROFILE FOR DEMO purposes**.
> No real company data exists anywhere in the repo, so a fictional
> multi-disciplinary profile was created (civil works division with CIDB 6CE,
> a small environmental/advisory unit, a PSIRA-registered security
> division, and — added for sample 4, extended for sample 5 with fictional
> cloud contact-centre capability — a small web/ICT unit, described in
> those samples' `02-bid-no-bid.md`). Every identifier is deliberately fake
> and non-colliding:
> registration `2015/999999/07`, CSD `MAAA0999999`, `555` phone exchange,
> reserved `.example` mail domain, ID numbers with `9999` sequences that fail
> the SA ID checksum. The profile carries **deliberate, realistic gaps**
> (no B-BBEE certificate expiry on file, no postal address, one director's
> tax reference missing, no linked pricing quotation on two of the bids) so
> the SDK's amber profile-gap blocks, red USER-INPUT blanks, fill-coverage
> statistics and fatal-gate warning page all appear in the generated packs —
> that gap rendering is part of what is being demonstrated.

## The five tenders and why they were chosen

| # | Tender | Buyer | Why chosen |
|---|--------|-------|-----------|
| 1 | **8/2/RNM0614** — Construction of Mgodlwa Bridge in Ward 8 (closing 2026-09-08) | Ray Nkonyeni Local Municipality (KZN) | Municipal construction: CIDB **6CE eligibility gate**, METHOD 4 evaluation (functionality 42/70 minimum, then 80/20), RNM/MBD municipal forms inside a CIDB T1/T2/C1–C3 document — the exact regime collision the SDK's one-regime-per-bid model has to face. |
| 2 | **DFFE-B005 26/27** — Triennial State of the Forests Report 2022–2024 (closing 2026-09-02) | Department of Forestry, Fisheries and the Environment | National professional services: clean SBD regime, three-phase evaluation with a **100-point functionality matrix and 75% threshold** — the best-case fit for the SDK's SBD fixture spread. |
| 3 | **VCW403/SECURE/25** — Total Security Solution, 60 months (closing 2026-09-03) | Vaal Central Water | The richest multi-gate regime in the corpus: **13 immediate-disqualification pre-qualifiers** (PSIRA company + director Grade B, PSSPF, COIDA, R15m public liability, CIPC, rates clearance, CIDB **4 SQ PE** on the works section), dual-section 75% functionality, unannounced site inspections, price tolerance band, supplier rotation — a deliberate stress test of where fixtures end and manual work begins. |
| 4 | **COR 01/2026/27** — Support, Maintenance, Development and Hosting of a Website, to 30 June 2029 (closing 2026-09-18) | Theewaterskloof Municipality (WC) | Municipal ICT/website services under a clean sub-R10m MBD regime — and the set's honest **thin-grounding case**: no municipal website tender in the registry has a full content pack (all four are advert-only records), so this sample shows what the SDK produces at its input floor, with pack collection itself modelled as a fatal gate. Also the set's only functionality PASS. |
| 5 | **TENDER 18-2025/26** — Interactive Cloud-Based Customer Service Ticketing and Helpdesk Management System, 3 years (closed 2026-05-11 — retrospective) | Musina Local Municipality (Limpopo) | The set's **best-grounded case**: the complete official 65-page pack, fetched directly from the buyer's website (client-linked), quoted end-to-end. Municipal cloud/SaaS services with **no scored functionality stage** (mandatory requirements are binary kills), buyer-authored Forms A–E alongside the standard MBD 4/6.1/8/9, two contradictory preference frameworks in one pack, POPIA as explicit spec text, and a genuinely fired deadline kill (window closed before the build). |

Each tender directory contains a per-tender `README.md` with a file-by-file
**GENERATED vs MOCKED** label, plus:

- `01-requirements-checklist.md` — gates, kill rules and returnables parsed
  from the real pack, mapped to SDK fixture rules.
- `02-bid-no-bid.md` — gate pass/fail for the fictional bidder, functionality
  outlook against the threshold, deadline/briefing tracking, recommendation.
- `03-bid-pack.html` + `03-bid-pack.manifest.json` — the **actual SDK
  output**: `pack_builder.py` run unmodified against the SDK's own regime and
  form-template fixtures. Open the HTML in a browser; it is the printable A4
  pack the product ships.
- `04-pack-structure.md` — how the physical submission is assembled per the
  tender's own returnables order and envelope instructions.
- `03-bid-pack*.pdf` — **GENERATED**: the same SDK HTML output rendered to
  print-ready **A4 PDF** (headless Chromium, one PDF per generated pack —
  six in total), byte-derived from the HTML with no content changes.
- `05-pricing-schedule.xlsx` (samples 2, 4 and 5) — **GENERATED for this
  sample set, hand-built**: an Excel workbook laid out to the pack's own
  pricing-schedule structure (DFFE's six Annexure A phase lines, TWK's
  5-year escalated grid, Musina's Year 1/2/3 once-off/monthly/annual grid
  plus unit call tariffs), carrying the fictional mock bid's numbers. These
  are NOT SDK output — the SDK has no spreadsheet export or multi-year
  pricing model (see coverage finding 8) — and every value is the mock bid.
  Samples 1 and 3 have no spreadsheet, honestly: neither bid carries a
  priced quotation — RNM's CIDB bills of quantities were never mocked
  (MBD1's total-price face field is the amber gap), and VCW's three-region
  BoQ is deliberately "not started" in the mock (an open KILL-09 gate) —
  so there are no numbers to tabulate without inventing them.

Directory 1 additionally contains `03-bid-pack-cidb-overlay.html` — a second
genuine SDK pack generated after flipping the same bid's regime to CIDB,
demonstrating the workaround for the regime-collision finding below.

> **Submission-format caveat.** The PDFs and spreadsheets make the samples
> reviewable in the formats a real bid desk works in, but a real submission
> additionally needs what no digital render carries: **wet-ink signatures**
> (and commissioner-of-oaths stamps where sworn), **initials on every page**,
> and **certified copies** of the supporting documents — usually assembled
> into the buyer's OFFICIAL issued forms (never a retyped substitute) and
> delivered per each pack's own channel rules (all five samples demand a
> physical sealed envelope to a tender box; see each `04-pack-structure.md`).

The set also includes **`company-profile/`** — the marketing-style "Company
Profile" document tender packs list as a returnable, genuinely generated for
the fictional Umzansi bidder with the **designer studio SDK**
(RokctAI/designer `designer-compliance` engine): a derived brand system, a
4-page A4 profile PDF and a press-ready tri-fold brochure from the SDK's own
z-fold template, with the engine's compliance audit scores alongside (see
that directory's README for its GENERATED vs STUBBED labels), plus
`company-profile/startup-os/` — the same profile compiled as content by the
startup_os engine (`business_profile.md` plus its `compliance_log.md`; the
engine's full ~30-document suite is reproducible via the committed runner —
see that directory's README).

**The company-profile returnable is now wired into the samples as
satisfied by that generated output.** The one sample whose returnables
carry such a slot — `cor-01-2026-27-twk-website` (derived technical
returnables; the ICT-CAPABILITY capability worksheet's pack family) —
shows it **SATISFIED** in its `04-pack-structure.md` (item 16) by
`company-profile/umzansi-company-profile-a4.pdf` (GENERATED, designer
engine) and `company-profile/startup-os/output/business_profile.md`
(GENERATED, startup_os engine), with the honest note that a real bid
substitutes the real company's profile and evidence. The other four packs
genuinely list no company-profile returnable — each sample README's
"Company-profile returnable" section quotes why (RNM's closed T2.1 list,
DFFE's letterhead-reference scoring, VCW's certificate pre-qualifiers,
Musina's exhaustively quoted page-2 checklist and §5.1 list) — so nothing
is forced there beyond an unscored-supporting-material pointer.

## What is genuinely SDK-generated vs hand-mocked

**GENERATED (real SDK code, run unmodified):**

- All six `03-bid-pack*.html` documents and their `*.manifest.json` files
  are the verbatim output of `src/control/pack_builder.py`
  (`build_pack` + `render_pack_html`), fed by the SDK's own fixtures
  (`tender_form_regimes.json`, `tender_form_templates.json`) — covers, fatal
  gate warning pages, pack index tables, per-form pages with kill notes,
  filled fields, amber gaps, red USER-INPUT blanks, signature slots,
  directors and pricing tables, initials strips, coverage statistics.
- The compliance-checklist rule sets cited in each `01-requirements-checklist.md`
  were derived by running the SDK's `compliance/rules.py` applicability
  matcher (`rule_applies`) over the shipped 54-rule fixture with each bid's
  real context (regime, estimated value, institution).
- The preference-system classification (80/20 vs 90/10), price-points worked
  examples and functionality pass/fail verdicts in each `02-bid-no-bid.md`
  come from running the SDK's `compliance/scoring.py`.

**MOCKED (hand-crafted to the SDK's designed shape):**

- The Umzansi business profile, bid contexts and the linked-quotation pricing
  lines (the SDK's endpoint would read these from Frappe doctypes; no bench
  exists in this environment, so they were supplied as the plain dicts the
  endpoint contract specifies).
- The open-fatal-gate strings rendered on the warning pages. In production
  they come from `submission_gate.validate_submission_readiness`; that module
  (like `checklist.py` and the API endpoints) imports via the composer's
  literal `{app_name}` placeholder and cannot be imported outside a composed
  bench. The strings were composed by hand to that function's exact output
  formats, using fixture `checklist_text`/`artifact_type` values where a
  fixture rule exists and `[manual]` rows where none does.
- The three-line checklist row assembly (rule → row dict) was mirrored from
  `checklist.py` for the same reason; the matching itself is imported SDK code.
- Everything in `01-*.md`, `02-*.md`, `04-*.md` and the READMEs: analyst-style
  documents written by hand, grounded in quoted text from the real tender
  packs (`/opportunities` registry, OCDS ids `ocds-9t57fa-164763`, `-164381`,
  `-164580`; sample 5's full 65-page pack fetched directly from
  musina.gov.za, no registry record exists for it) — except sample 4
  (`-165555`), where **no full pack exists in the registry** and only the
  advert-level record is quoted, with all derived/assumed material
  labelled as such — in the shape the product's checklist/bid-desk screens
  are designed to present. The SDK does not parse tender packs or write
  prose.

## Honest SDK coverage findings

These are the findings the samples surface — where the SDK carried the work
and where mocks papered over gaps.

**What the SDK produces well:**

1. **The pack document itself is genuinely strong.** Kill notes on every
   form, the never-silent fatal-gate warning page, amber "not in your
   profile" gaps, red tender-specific blanks with guidance, the
   official-forms/never-retype warning on every page, per-form and pack-level
   fill statistics, directors table with in-state-service and Persal columns,
   pricing table from a linked quotation, commissioner-of-oaths slots that
   are never stamped. Fill coverage on these samples: 91.8–97.1% of
   profile/bid-sourced fields auto-filled.
2. **The universal compliance spine holds on all five tenders.** All
   universal Fatal rules (CSD, TCS PIN, defaulters register, state employees,
   CIPC, KILL-01…KILL-25) attached to every bid and match real kill language
   in all four full packs almost clause-for-clause (sample 4 has no pack
   text to compare against) — e.g. KILL-09 vs RNM's
   unpriced-line rule, KILL-15 vs VCW's "Failure to attend the compulsory
   briefing session will deem the response non-Responsive", KILL-16 vs
   RNM's one-extra-copy disqualification, GATE-RATES vs Musina's
   directors-and-company rates-statement demand (near word-for-word), and
   KILL-01 vs Musina's "late … cannot be admitted for consideration" —
   the latter genuinely fired on sample 5's closed window.
3. **Scoring arithmetic is correct and data-driven.** 80/20 vs 90/10
   classification by value, `Ps = X(1-(Pt-Pmin)/Pmin)`, and functionality as
   an elimination gate reproduce each pack's printed formulas exactly.
4. **Conditional value triggers work — in both directions.** GATE-MBD5
   (municipal > R10m) attached itself to the R42.5m RNM bid from the
   estimated value alone — exactly matching returnable A17, the pack's
   "Declaration For Procurement Above R10 Million" — and correctly stayed
   OFF the R2.18m Theewaterskloof bid, where the MBD-conditional
   GATE-RATES and KILL-19 still attached from the regime alone. On that
   bid the linked quotation also filled MBD1's total-price face field
   (the one auto-fill the RNM run had to leave amber), giving the set's
   best coverage at 97.1%.

**Where mocks had to paper over gaps:**

1. **One regime per Tender Bid.** RNM needs the MBD declaration spread
   (A16–A19, A21, B2) *and* the CIDB overlay (C1.1 Form of Offer, T2.x
   schedules, H&S plan) — all mandatory in the same pack. The SDK regime
   model forces a choice; the sample uses MBD (more returnables covered,
   richer field templates) and a second regime-flipped CIDB pack as the
   workaround. Neither single pack is the whole submission.
2. **Forms are fixture-driven, not pack-parsed.** The MBD pack includes an
   MBD1 cover form the RNM pack does not use (its offer is CIDB C1.1), and
   none of the buyer-authored returnables exist as templates: RNM's A1–A15
   schedules (plant, key personnel, monthly expenditure, work carried out…),
   DFFE's Annexure A pricing schedule / Annexure B CV template / Annexure C
   consent form, VCW's returnable functionality schedules. The generic T2.x
   worksheet page and the checklist carry these instead.
3. **Conditional rule triggers are buyer-pattern fixtures, and none of these
   three buyers is in any pattern list (or in `buyer-profiles/`).**
   Consequences visible in the samples: GATE-SECTOR (PSIRA et al.) did not
   fire for a security tender with seven PSIRA-related pre-qualifiers, because
   its pattern list currently contains only "department of tourism";
   GATE-INSURANCE did not fire for VCW's R15m public-liability gate;
   GATE-RATES is modelled MBD-only, so VCW (an SBD-regime water board)
   demanding municipal rates clearance got no auto rule; GATE-CIDB and
   GATE-COIDA are CIDB-regime-only, so the RNM bid under MBD and the VCW
   Section 2 works gate both needed manual rows. On VCW, 5 of 6 fatal gates
   on the warning page are `[manual]`.
4. **Dual-section functionality does not fit the single
   `functionality_threshold`/`functionality_self_score` pair.** VCW scores
   Section 1 (≈335 pts) and Section 2 (165 pts) separately, each with its own
   75% kill; the bid record can hold one number. Per-criterion scoring
   matrices (DFFE's 6-criterion 100-point rubric, RNM's 70-point METHOD 4
   matrix) live entirely outside the SDK — the samples carry them as
   hand-built tables.
5. **Buyer quirks with no fixture representation**, grounded in pack text
   because no buyer-profile sheets exist for these buyers: RNM's
   locality-based specific goals (RNM 10 / Ugu 5 / KZN 1 — not B-BBEE),
   black-ink and original-plus-one-copy rules; DFFE's master-document + USB
   + bidder-drafted table of contents screening; VCW's −20%/+20% price
   tolerance band, R250m supplier-rotation threshold, and unannounced
   site-inspection phase.
6. **Environment caveat.** The Frappe endpoints (claim → checklist sync →
   submission gate → `generate_bid_pack`) require a composed bench and were
   not run; everything labelled GENERATED came from the standalone-importable
   modules (`pack_builder.py`, `rules.py`, `scoring.py`) fed by the fixtures.
7. **GATE-POPIA is invisible exactly where POPIA matters most** (new with
   sample 4, sharpened by sample 5). Its trigger is a buyer-pattern list
   (SANRAL/Transnet et al.), so on a municipal website-hosting tender —
   whose entire subject is processing residents' personal information — no
   POPIA rule attached. Sample 5 makes the miss starker: the Musina pack
   demands POPIA/PAIA compliance as **explicit specification text**
   (§4(c)), plus SA-only hosting ("Must be hosted in South Africa, by
   South Africans") and 18-month retention of call recordings — and still
   no rule fired. The optional POPIA *form* generates under the MBD
   regime, but nothing in the checklist demands or tracks it. Same
   pattern-list weakness as GATE-SECTOR/GATE-INSURANCE (finding 3), now
   shown on subject-matter and spec-text triggers rather than buyer ones.
8. **The SDK has no ICT/website capability surface — and no multi-year
   pricing/escalation model, which is a category-level gap, not an edge
   case** (new with sample 4, sharpened by client domain knowledge).
   The Tender Business Profile has no fields for portfolio/reference
   sites, hosting infrastructure, data residency, uptime SLA, security
   certifications or support tiers; no fixture rule or form template
   covers a website specification, hosting SLA or disaster-recovery
   returnable. On pricing: **per client domain knowledge, municipal
   website tenders mostly carry a 5-year maintenance term**, and every
   municipal website advert in the corpus bundles hosting into the
   contract (TWK `-165555`; Mnquma `-165060`, "hosting and maintenance
   … three years"; Umzinyathi `-165289`, "redesign, hosting, maintenance
   and disaster recovery … 36 months"; Laingsburg `-164801`, "email,
   domain and website hosting") — multi-year recurring pricing IS the
   category, yet the SDK has no contract-term field, no escalation/CPA
   rule and no year-by-year pricing model. Sample 4's quotation now
   carries the typical 5-year CPI-escalated schedule entirely as flat
   hand-built lines (and under MBD only the total reaches a form —
   `pricing_lines` renders solely on the SBD3.x template). Every
   website-specific gate, returnable and functionality criterion in
   sample 4 is hand-carried. **Sample 5 adds direct pack-text evidence**:
   Musina's official pricing schedule is itself a Year 1/2/3 grid
   (once-off/monthly/annual columns plus per-unit call tariffs, 3-year
   VAT-inclusive total) that the SDK cannot model — though its term is
   **3 years**, not 5: per client domain knowledge Musina terms were
   believed to run 5 years, and the first Musina pack on file states
   3 years/36 months throughout (recorded neutrally as pack evidence).
9. **Grounding floor: the catalog side bounds the compliance side** (new
   with sample 4). None of the four municipal website tenders in the
   `/opportunities` registry has a full content pack — all are advert-only
   records — so the checklist beyond the universal spine, the real
   functionality matrix and even the threshold cannot be confirmed from
   the data the SDK's own catalog layer serves. The sample keeps this
   honest by modelling "collect the official pack" as an open fatal gate
   rendered on the warning page, and by labelling the 70-point threshold
   ASSUMED (municipal corpus mode). Enrichment coverage upstream is as
   load-bearing as any fixture. Sample 5 is the mirror case: its tender
   has **no registry record at all** (the seven Musina records are
   unrelated RFQs) and the full pack had to be fetched from the buyer's
   own site — full-pack grounding and catalog coverage are independent
   axes.
10. **A full municipal pack can contradict itself — and dodge the scored
   model entirely** (new with sample 5). The Musina pack carries **two
   preference frameworks at once** (the pre-2011 HDI equity-ownership
   explanation and Form C, alongside the operative PPR 2022 MBD 6.1
   specific-goals table, plus a 1939-Ordinance local-content certificate),
   has **no scored functionality stage** (every §5.1 mandatory requirement
   is a binary Stage-1 kill; `functionality_threshold` is correctly
   "none" — a negative case for the single-pair model), demands audited
   AFS from every bidder **below** GATE-MBD5's R10m trigger, and requires
   a bank-rating letter [A to C] — a returnable no fixture models. Its
   buyer-authored Forms A–E (offer, signatory authorisation, legacy HDI
   declaration, local content, OHS s37(2)) have no templates, while
   MBD 4/6.1/8/9 match the fixtures exactly.

The net read: the SDK's document half and universal rule spine are shippable
and demonstrably map onto real packs; the per-buyer/per-pack half (buyer
trigger patterns, buyer-authored returnable templates, multi-section
functionality, regime overlays) is where a real bid still needs hands — or
the next round of fixtures.
