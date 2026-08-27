# TenderAssist SDK — Improvement Findings from the Mock Sample Build

Release date: 2026-08-20. Audience: **the agent building/improving the
TenderAssist SDK** (`tender/frappe`). Sources: the five worked sample packs
in `tender/mock-samples/` (real tenders, fictional bidder, genuine SDK
output where the code could run), the `/opportunities` registry corpus, and
`rules-table.md` / `functionality-thresholds.md`. Every finding cites
concrete evidence — rule ids, fixture names, sample paths — so it can be
acted on without re-deriving the analysis. No speculation: everything below
was observed while building the samples.

Evidence base (read these alongside this doc):

- `tender/mock-samples/8-2-rnm0614-mgodlwa-bridge/` — R42.5m municipal
  bridge, MBD + CIDB collision case (two generated packs)
- `tender/mock-samples/dffe-b005-26-27-state-of-forests/` — national SBD
  professional services, 100-point functionality matrix
- `tender/mock-samples/vcw403-secure-25-total-security/` — 13
  immediate-disqualification pre-qualifiers, dual-section functionality
- `tender/mock-samples/cor-01-2026-27-twk-website/` — municipal website
  (advert-only grounding; 5-year maintenance/hosting pricing shape)
- `tender/mock-samples/18-2025-26-musina-helpdesk/` — municipal cloud
  helpdesk/ticketing SaaS (full official 65-page pack fetched from the
  buyer's site; no scored functionality stage; retrospective — closed
  2026-05-11)

## Open items for the builder (as of 2026-08-21)

Consolidated from the status notes below. Most of F-01…F-15 has been
delivered by merged PRs (see the per-finding status notes and the verify
suites at `tender/frappe/tests/verify/`); nothing marked delivered is
reopened here. This list is the complete set of what is still open **for
the SDK builder session** (`tender/frappe` only — studio/designer work is
a separate workstream, F-15 status notes).

### O-01 · F-02 residual: bare regime headings without title lines are still unparsed

PR #45's verified result on the real 65-page Musina 18-2025/26 PDF is
**18 of 21** returnables: the three misses are the bare headings
`MBD 6.1`, `MBD8` and `MBD 9` — regime codes standing alone with no title
text on or near the line, which none of the Form/lettered/list-mode regex
families accepts. Recommendation: extend the bare-form regex family to
regime codes with no title line (reusing the existing lookahead-title
join where a title does follow), validated against the real PDF via suite
pr_e (`tests/verify/verify_pr_e.py`) — target 21/21.

### O-02 · The ≥2-per-letter list-mode rule needs corpus calibration

The rule that lettered schedule lines only count in groups of ≥2 per
letter prefix carries an explicit CALIBRATION NOTE in
`tender/frappe/src/control/parsing/pack_parse.py` (inside
`_find_returnables`, ~line 530): it deliberately drops single-item
lettered schedules to avoid harvesting stray "A4 paper"-style lines, a
tradeoff calibrated against exactly one pack. Recommendation: measure
both failure modes (dropped one-row schedules vs harvested noise) across
the project's eTenders corpus (163k releases, 2021-2026) before moving
the threshold, and record the measured rates next to the note.

### O-03 · Broad-subject-pattern gate over-fire is flagged but unmeasured

The wave-1 review flagged that the subject-matter/description trigger
patterns added for F-03 likely over-fire on unrelated tenders (e.g. a
"hosting" keyword firing POPIA/ICT gates on non-ICT packs) — the reverse
failure mode of the too-narrow lists F-03 documented. The measurement is
planned for the upcoming full-corpus run over the project's eTenders
corpus (163k releases, 2021-2026); per standing instruction, generated
packs are NOT saved to the repo in that round unless the builder requests
specific ones. Recommendation: run the trigger patterns over the corpus,
report per-gate fire rates and false-positive samples, and tighten the
patterns that fire on unrelated categories.

### O-04 · F-15(b) follow-through: the attach/attest hook has never run end-to-end with a real artifact

The control-side hook is delivered (PR #45: `tender_bid_returnable`
artifact fields, `attach_returnable_artifact` attach→attest,
`[RETURNABLE-ARTIFACT-UNATTESTED]` lint, worksheet artifact states) but
has only been exercised against synthetic files. The generation side is
merged in startup_os (The-Rokct-Protocol `f6b885f`), and the studio-side
wiring that produces and attaches `business_profile` + `compliance_log`
is owned by the startupos session. Once that wiring lands, the builder
should add and run an end-to-end smoke: attach `business_profile` +
`compliance_log` files to a bid, attest, confirm the
`[RETURNABLE-ARTIFACT-UNATTESTED]` lint clears and the worksheet renders
SATISFIED BY GENERATED ARTIFACT.

### O-05 · Cosmetic: in-tree verify runs leave `__pycache__` litter

Running the verify suites in-tree leaves `__pycache__/` directories under
`tender/frappe/src/` (observed: `src/control/__pycache__` after a suite
run). `tender/frappe/.gitignore` already covers `__pycache__/`, so there
is no commit risk — this is working-tree litter only. Recommendation:
set `sys.dont_write_bytecode = True` in the shared verify harness (or run
with `PYTHONDONTWRITEBYTECODE=1`), or clean up on suite exit.

### O-06 · Bench-only tests cannot serve as the verification harness

`tender/frappe/tests/test_bid_pack.py` imports via the composer's literal
`{app_name}` placeholder (line 40) and so requires a composed bench — it
cannot run in this environment; the in-tree suites at
`tender/frappe/tests/verify/` (frappe stubbed in-memory, real modules
loaded with the placeholder substituted) are the runnable harness.
Recommendation: any future finding-verification must extend
`tests/verify/`, not only the bench tests — a check that exists only in a
bench-only test is unverifiable here (the original F-02 follow-up's
"68/68 not re-runnable" problem).

### Open-items table

| open_id | severity | evidence | recommendation |
|---|---|---|---|
| O-01 | medium | F-02 residual: real Musina 18-2025/26 PDF parses 18/21 returnables (PR #45 verified); misses = bare `MBD 6.1`/`MBD8`/`MBD 9` headings with no title line, unmatched by any current regex family | Extend the bare-form regex family to titleless regime codes (reuse lookahead-title join); validate 21/21 via suite pr_e against the real PDF |
| O-02 | medium | ≥2-per-letter rule in `src/control/parsing/pack_parse.py` (`_find_returnables`, ~line 530) carries a CALIBRATION NOTE: drops single-item lettered schedules by design, calibrated on one pack | Measure drop-vs-harvest rates across the project's eTenders corpus (163k releases, 2021-2026) before moving the threshold; record rates next to the note |
| O-03 | medium | Wave-1 review flag: F-03's subject/description trigger patterns likely over-fire on unrelated tenders; unmeasured — full-corpus run planned (generated packs NOT saved to the repo in that round unless the builder requests specific ones, per standing instruction) | Corpus run reporting per-gate fire rates + false-positive samples; tighten patterns that fire on unrelated categories |
| O-04 | medium | F-15(b) hook (PR #45) never exercised end-to-end with a real generated artifact; generation side merged in protocol `f6b885f`; studio-side wiring owned by the startupos session | Once wiring lands: e2e smoke — attach `business_profile` + `compliance_log` to a bid, attest, confirm `[RETURNABLE-ARTIFACT-UNATTESTED]` clears and worksheet shows SATISFIED BY GENERATED ARTIFACT |
| O-05 | low | In-tree verify runs leave `__pycache__` under `tender/frappe/src/` (working-tree litter; already git-ignored by `tender/frappe/.gitignore`) | `sys.dont_write_bytecode` / `PYTHONDONTWRITEBYTECODE=1` in the verify harness, or cleanup on exit |
| O-06 | low | `tests/test_bid_pack.py` needs a composed bench (`{app_name}` imports, line 40) — unrunnable here; `tests/verify/` suites are the runnable harness | Future finding-verification must extend `tests/verify/`, not only bench tests |

## What the SDK already does WELL — do not churn this

These behaviours were verified against real pack text across the samples.
They are the product's spine; improvements below should extend them, not
rework them.

1. **Auto-fill is genuinely strong: 91.8–97.1%** of profile/bid-sourced
   fields filled across the six generated packs (VCW 56/61 = 91.8% low
   end; TWK and Musina each 66/68 = 97.1% high end), with amber "not in
   your profile" gaps and red USER-INPUT blanks rendered rather than
   silently skipped.
2. **Fatal gates are never silent.** Every generated pack renders the
   warning page whenever any fatal gate is open, and the pack cover
   declares "N FATAL compliance gate(s) still open". The VCW pack
   correctly declares itself not submission-ready with six open gates.
3. **Value/regime conditional triggers fire correctly in BOTH
   directions.** GATE-MBD5 (municipal > R10m) attached to the R42.5m RNM
   bid — exactly matching the pack's real returnable A17 ("Declaration
   For Procurement Above R10 Million") — and correctly stayed OFF the
   R2.18m TWK bid, where MBD-regime conditionals GATE-RATES and KILL-19
   still attached from the regime alone.
4. **Scoring arithmetic is exact and data-driven.** 80/20 vs 90/10
   classification by value, `Ps = X(1-(Pt-Pmin)/Pmin)`, and functionality
   as an elimination gate (`passes_functionality`) reproduce each pack's
   printed formulas; the universal Fatal rule spine (GATE-CSD, GATE-TCS,
   GATE-DEFAULTERS, GATE-STATE-EMP, GATE-CIPC, KILL-01…KILL-25) matched
   real kill language in all four full packs nearly clause-for-clause
   (e.g. KILL-09 vs RNM's unpriced-line rule, KILL-15 vs VCW's briefing
   non-responsiveness clause, GATE-RATES vs Musina's
   directors-and-company rates demand, KILL-01 vs Musina's "late …
   cannot be admitted for consideration" — genuinely fired on the
   retrospective sample's closed window).
5. **Quotation linkage works.** The linked-quotation contract
   (`quotation_link.py` shape) filled MBD1's total-price face field on
   the TWK pack — the one auto-fill the RNM run had to leave amber.

## Findings — prose

### F-01 · One regime per Tender Bid cannot represent real municipal construction packs

RNM 8/2/RNM0614 demands the MBD declaration spread (A16–A19, A21, B2)
AND the CIDB overlay (C1.1 Form of Offer, T2.x returnable schedules, H&S
plan) as mandatory returnables in the same submission. The SDK's
one-regime-per-bid model forces a choice; the sample's workaround is two
genuine packs (`03-bid-pack.html` under MBD plus
`03-bid-pack-cidb-overlay.html` after flipping the regime to CIDB), and
neither is the whole submission. Recommendation: allow a bid to carry a
base regime plus overlay regime(s), with the form set as the union and
the pack index merged.

### F-02 · Form sets are fixture-driven, not pack-parsed

The pack generator emits the regime fixture's form list regardless of
what the buyer actually issued: the RNM MBD pack includes an MBD1 cover
its real pack does not use (its offer form is CIDB C1.1), and none of the
buyer-authored returnables exist as templates — RNM's A1–A15 schedules
(plant, key personnel, monthly expenditure, work carried out…), DFFE's
Annexure A pricing schedule / Annexure B CV template / Annexure C consent
form, VCW's returnable functionality schedules. The generic worksheet
page and manual checklist rows carry all of these. The Musina full pack
(sample 5) gives the cleanest quantification yet: of its nine returnable
forms, **four match SDK templates exactly** (MBD 4, 6.1, 8, 9) while the
five buyer-authored ones have no representation — Form A Form of Bid
(the pack's actual offer form; the generated MBD1 is unused again),
Form B Signatory Authorisation, Form C legacy HDI Declaration of
Interest, Form D Local Content/SABS certificate (1939 Ordinance), Form E
OHS Act s37(2) contract — plus twelve §5.1 mandatory technical
returnables (project plan, 3 references with appointment letters, risk
plan, training plan, bank rating letter A–C, 48-hour-resolution support
documentation…) none of which any fixture rule or template covers.
Recommendation: keep fixtures as the fallback, add a per-pack returnable
list (parsed or hand-captured) that overrides the fixture form set, and
a template capture path for recurring buyer-authored forms.

#### F-02 follow-up (post-PR #43 verification)

An independent verification of PR #43's pack parser against the REAL
Musina buyer PDF (65 pp, full text layer — sample 5's source document)
found the scalar extractors working: closing date/time, the 80/20 split,
the physical submission channel and the wet-ink rule all came back QUOTED
from pack text, and functionality was correctly reported NOT-FOUND (this
pack has no scored stage). But **returnable extraction produced 0 items on
that same real pack, and the tender number was missed**, for four
concrete, cheap-to-fix reasons:

1. The pack lists its §5.1 items as **"a." dot-style**, while the
   paren-letter regex requires **"a)"**.
2. **"Form A" appears on its own line** with its title ("FORM OF BID") a
   few lines below; the Form regex requires same-line titles — a lookahead
   join to the following non-empty line would fix it.
3. **"TENDER\nNUMBER 18-2025/26" wraps across two lines**, and both
   tender-number regexes are single-line.
4. **template_code linking matches only the ref_code** (A2, Form B)
   against template codes, while the MBD/SBD token lives in the item
   *title* — so on the documented styles it can never fire; also
   exact-match a leading "MBD n / SBD n(.n)" token from the title.

Two smaller notes: the ≥2-per-letter rule silently drops single-item
lettered schedules (a deliberate tradeoff, but worth documenting in the
parser), and the PR's claimed verification suite (68/68 passing) is not
committed to the tree, so the result could not be re-run.

**Status note (2026-08-21):** PR #45 (merged 2026-08-21, head `f18afae`)
delivered all four fixes, independently verified against the refetched
real 65-page Musina 18-2025/26 PDF: returnable extraction went **0 → 18
of 21** (the 5.1(a)–(l) items, Forms A–E, and Annexure C linked to MBD4
by exact match), the tender number went NOT-FOUND → QUOTED, all other
scalars are unregressed (base-vs-head comparison), and pack builds are
byte-identical. Remaining known gap: three bare `MBD 6.1`/`MBD8`/`MBD 9`
headings are still unparsed. The "not committed" caveat above is also
closed: the verification suites are now committed in-tree at
`tender/frappe/tests/verify/` (58/58 for pr_e with the real PDF).

### F-03 · Buyer-pattern trigger lists are too narrow — all five sample buyers missed

None of the five buyers (Ray Nkonyeni LM, DFFE, Vaal Central Water,
Theewaterskloof LM, Musina LM) appears in any fixture pattern list or in
`buyer-profiles/`. Observed consequences: GATE-SECTOR did not fire on a
security tender with seven PSIRA-related pre-qualifiers (its pattern list
currently contains only "department of tourism"); GATE-INSURANCE did not
fire on VCW's R15m public-liability disqualifier; GATE-POPIA is
pattern-scoped to SANRAL/Transnet-style buyers, so on a municipal
website-HOSTING tender — whose entire subject is processing residents'
personal information — no POPIA rule attached (the optional POPIA form
still generated, but nothing demands or tracks it). Sample 5 upgrades the
POPIA miss from inference to quotation: the Musina helpdesk pack demands
"compliance with POPIA, PAIA, and related legislations" as **explicit
specification text** (§4(c)), requires SA-only hosting ("Must be hosted
in South Africa, by South Africans") and 18-month retention of recorded
citizen calls — and still no POPIA rule attached. Net effect on the
stress-test sample: **9 of VCW403's 13 immediate-disqualification
pre-qualifiers had no auto rule** and needed hand-added manual rows, and
5 of the 6 fatal gates on its warning page are `[manual]`.
Recommendation: add subject-matter/content triggers (tender description
and specification keywords) alongside buyer patterns, and expand the
pattern lists from the corpus rather than hand-curating single buyers.

### F-04 · Regime-scoped rules leak across regimes

GATE-RATES is modelled MBD-only, but VCW (an SBD-regime water board)
demands municipal rates clearance — no auto rule fired. GATE-CIDB and
GATE-COIDA are CIDB-regime-only, so the RNM bid run under MBD and VCW's
Section 2 works gate (CIDB 4 SQ PE) both needed manual rows. Value
triggers fence the same way: GATE-MBD5's `estimated_value_over:
10000000` correctly stayed off the ≈R2.57m Musina bid, yet the Musina
pack demands newest financials from **every** bidder (page-2 checklist)
and audited AFS for the previous 3 years as mandatory requirement
5.1(i) — an AFS demand decoupled from the R10m convention that had to be
a manual row. Recommendation: express these as demand-driven rules
(trigger on pack content/buyer type) rather than hard regime or value
scoping; regime and value should be priors, not fences.

### F-05 · Single-field functionality cannot hold multi-section or matrix evaluation

The bid record holds one `functionality_threshold` / `functionality_
self_score` pair. VCW scores Section 1 (≈335 pts) and Section 2 (165 pts)
separately, each with its own 75% kill — one number cannot represent it.
DFFE's 6-criterion 100-point rubric and RNM's METHOD 4 70-point matrix
(42/70 minimum) live entirely outside the SDK as hand-built tables. The
Musina pack (sample 5) supplies the missing **negative case**: it has no
scored functionality stage at all — Stage 1 is administrative compliance
plus pass/fail mandatory requirements, Stage 2 goes straight to 80/20
price + specific goals — so the correct per-tender value is "no
threshold", which the current single pair can only express as an
ambiguous zero. Recommendation: a child table of scored
sections/criteria (label, max, threshold, self-score), with the existing
pair kept as the single-section degenerate case and an explicit
"no scored functionality" state.

### F-06 · No multi-year term or escalation model — a CATEGORY-level gap for municipal website/maintenance tenders

Per client domain knowledge, municipal website support tenders **mostly
carry a 5-year maintenance term and include hosting**. Corpus check: the
hosting-inclusive scope is corroborated by **all four** municipal website
adverts in `/opportunities` (TWK `ocds-9t57fa-165555`; Mnquma `-165060`
"hosting and maintenance of municipal website for a period of three
years"; Umzinyathi `-165289` "website redesign, hosting, maintenance and
disaster recovery services … thirty-six (36) months"; Laingsburg
`-164801` "email, domain and website hosting services"). The 5-year term
itself is not yet corpus-verified — stated terms where given are 3
years/36 months, and a Musina website tender believed to exist was NOT
found in the corpus (the seven Musina records are unrelated RFQs:
tools of trade, road-marking materials, diaries, a battery protection
unit, toilet paper, a mouldboard cylinder, building repair) — so the
norm is carried as client domain knowledge. **Update (sample 5): the
first full Musina pack is now on file** — Tender 18-2025/26 (cloud
helpdesk/ticketing, client-linked, fetched from musina.gov.za; still no
registry record). Per client domain knowledge Musina terms were believed
to run 5 years; **this pack states 3 years/36 months throughout** (title,
ToR §1, pricing instruction §6(a)) — recorded neutrally as pack
evidence, one pack being one data point. More importantly it supplies
**direct pack-text proof of the pricing-model gap**: the official
pricing schedule is a year-by-year grid (Once-Off / Monthly / Annual
columns per Year 1–3 plus per-unit call tariffs, "the actual variable
value thereof will be dependent on call activity over the term period")
— a structure the SDK cannot represent; the sample's 12-line 3-year
schedule (R2,573,750.00) is again flat hand-built quotation lines.
Either way, multi-year recurring pricing IS this category, and the SDK
has **no contract-term field, no CPI/CPA escalation rule, and no
year-by-year pricing model**: the TWK sample's typical-shape 5-year
escalated schedule (R2,179,056.00, mock 5.0% p.a.) had to be hand-built
as flat quotation lines. Note also KILL-ALT-OFFER (rules-table):
substituting fixed rates where a pack prescribes a CPA formula is a
disqualifier — escalation is compliance-relevant, not just
pricing-relevant. Recommendation: add contract term (start/end/years) to
the bid context, an escalation provision field (none/CPI/CPA-formula,
rate), a year-by-year schedule in the quotation link (with unit-tariff
lines), and a rule that flags fixed pricing on multi-year terms /
prescribed-formula packs.

### F-07 · No ICT/website capability surface in the Tender Business Profile

The profile has no fields for portfolio/reference sites, hosting
infrastructure, data residency, uptime SLA, security certifications or
support tiers; no fixture rule or form template covers a website
specification, hosting SLA or disaster-recovery returnable. Every
website-specific gate, returnable and functionality criterion in the TWK
sample is hand-carried. Recommendation: a sector-extensible capability
child table (type + fields) rather than one hardcoded ICT block, so
security (PSIRA grades, PSSPF) and construction (plant, key personnel)
gaps close the same way.

### F-08 · Catalog grounding floor: advert-only categories bound the compliance layer

No municipal website tender in the registry has a full content pack —
all four are advert-only records (~1.7KB each) — so the checklist beyond
the universal spine, the real functionality matrix, and even the
threshold cannot be confirmed from data the SDK's own catalog layer
serves. The TWK sample models "collect the official pack" as an open
fatal gate and labels its threshold ASSUMED. Recommendation: treat
enrichment coverage as a first-class metric; auto-attach a
pack-collection fatal gate whenever a bid is created from an advert-only
record; surface per-category enrichment stats so thin categories are
visible before bid/no-bid.

### F-09 · `{app_name}` placeholder imports block standalone use of the endpoint layer

`tasks.py`, `submission_gate.py`, `checklist.py` and the API endpoints
import via the composer's literal `{app_name}` template placeholder
(fleet convention) and cannot be imported outside a composed bench —
`tasks.py` even carries `compliance-ignore-file: syntax-error`. Building
the samples, only `pack_builder.py`, `rules.py` and `scoring.py` could
run; the open-fatal-gate strings had to be hand-composed to
`validate_submission_readiness`'s output formats and the checklist row
assembly mirrored from `checklist.py`. Anything downstream (tests, demos,
CI, sample generation, this very evaluation) pays the same tax.
Recommendation: move business logic into composition-independent modules
(relative imports) with thin `{app_name}` endpoint shims, so the gate
and checklist layers are importable and testable standalone.

### F-10 · `pricing_lines` renders only on SBD3.x — MBD/CIDB packs show no pricing schedule

`TABLE_COLUMNS`/`PRICING_COLUMNS` in `pack_builder.py` are wired to a
single fixture field: the only template with `source_field:
pricing_lines` is SBD3.x. Under the MBD regime the linked quotation
surfaces solely as MBD1's total-price face value — the TWK pack renders
no line-item table at all despite an 8-line quotation. Recommendation:
add an MBD pricing-schedule worksheet template (and a CIDB T2.x priced
variant) sourcing `pricing_lines`, so every regime shows the schedule
that must be re-keyed onto the official form.

### F-11 · Recurring buyer quirks have no fixture representation

Grounded in pack text across the samples: RNM's locality-based specific
goals (RNM 10 / Ugu 5 / KZN 1 — not B-BBEE), black-ink and
original-plus-one-copy rules; DFFE's master-document + USB +
bidder-drafted table-of-contents screening; VCW's −20%/+20% price
tolerance band, R250m supplier-rotation threshold and unannounced
site-inspection phase; Musina's initial-EVERY-page-at-the-bottom rule,
attachments "at the back of the official bid document (i.e. After the
Councils price schedule)", submit-as-a-whole/no-pages-removed rule,
tender-box hours (07:30–16:00 weekdays, Room 53), written-queries-only
enquiries, and toll-free retention of the existing call-centre number.
None can be expressed as fixture rules today and no `buyer-profiles/`
sheet exists for any of the five buyers. Recommendation: extend
`buyer-profiles/` with sheets for buyers the product actually bids to,
and add a per-buyer quirk rule type the checklist can render as auto
rows.

### F-12 · One live pack can carry contradictory preference frameworks — the SDK assumes one

The Musina pack simultaneously contains: (a) the operative **PPR 2022
MBD 6.1** specific-goals table (80/20; HDI 51% black-owned 10 / women's
equity 51% 4 / disability 3 / youth 3), matching its "Information to
bidders" evaluation page; (b) the **pre-2011 HDI equity-ownership
framework** — a full Preference Point Explanation section under the
PPPFA 2000 regulations (NEP = NOP × EP/100) and a buyer-authored Form C
claiming "HDI Equity Ownership …% = … Points out of 20 (<R1 000 000)";
and (c) a **Local Government Ordinance 1939** local-content/SABS
preference certificate (Form D). A bidder must complete all three —
Form C and Form D each state that non-completion forfeits the
preference — while only one framework actually scores. The SDK models
exactly one preference system per bid (MBD 6.1-shaped), which is correct
for the operative scoring but cannot represent, track or warn about the
legacy forms that still must be filled and signed. Recommendation: treat
this as a returnables problem, not a scoring problem — per-pack
returnable capture (F-02) should list the legacy preference forms as
mandatory returnables even when the scoring model ignores them, and a
lint-style warning ("pack contains conflicting preference frameworks;
operative system: X") would surface the contradiction to the bid desk.

### F-13 · Auto-dispatch: email the completed pack to the buyer (feature, per client request)

The requested end state (per client request) is a low-effort pipeline:
find tenders → accept one → do the quote → the SDK generates the pack
**and emails it to the buyer**. The last hop does not exist today. The
SDK's only outbound email is `frappe.sendmail` in
`src/control/compliance/artifact_expiry.py` (line 52) — an opt-in weekly
notification to the *owning user* about expiring compliance artifacts —
so the Frappe email queue is available at framework level and is simply
never invoked buyer-ward: `generate_bid_pack.py` returns the rendered
pack to the caller and stops, and no endpoint in
`src/control/api/tenders/` sends anything anywhere. The buyer-side
address is already in the data: registry/corpus records carry Contact
Person and Email fields (rendered on the opportunity detail page,
`nextjs/templates/control/app/opportunities/[type]/[slug]/page.tsx`
lines 192–193/248–249) — displayed today, used for nothing.

Two hard gates must precede any dispatch: (1) the SDK's own submission
gate — `validate_submission_readiness` returns no fatal gate failures
and every mandatory returnable is satisfied (a pack whose cover says
"N FATAL compliance gate(s) still open" must be undispatchable); and
(2) explicit user confirmation per send — nothing leaves the system
automatically.

The honest domain caveat, grounded in the five samples: **all five
sample tenders require physical sealed-envelope submission to a tender
box** (RNM original-plus-one-copy sealed envelope; DFFE and TWK sealed
envelopes endorsed with the bid number; VCW sealed envelope with public
opening; Musina tender box, Room 53, 07:30–16:00 weekdays — see each
sample's `04-pack-structure.md`), and SA public-procurement packs
commonly reject emailed competitive bids outright (the KILL-01 family:
wrong channel = late = "cannot be admitted for consideration").
Emailing a full bid pack to a buyer who demanded a sealed envelope is
not a submission — at several buyers it could even breach
communication rules. Recommendation, in three tiers: **(a)** full email
submission only where the pack explicitly allows it — common for
RFQs/quotations (the corpus's Musina records are RFQ-shaped, exactly
this class); **(b)** where it does not, use the same machinery for
correspondence the packs DO allow to the named contact: written
clarification questions (Musina is written-queries-only), briefing
attendance confirmations, CSD verification correspondence — and the
post-submission cure-window watch already makes the named contact email
operationally central (KILL-CURE-MISS); **(c)** a per-tender
submission-channel field (physical-box / portal / email-allowed) on the
tender/bid record so the SDK knows which mode applies and can render
"how this pack must actually be delivered" instead of guessing.

### F-14 · eTenders bulk-list API silently drops records — ingest by ocid ID enumeration, never list pagination (complete corpus now on file)

Verified 2026-08-20 during a full-corpus fetch: the eTenders OCDS list
endpoint (`GET https://ocds-api.etenders.gov.za/api/OCDSReleases?dateFrom=..
&dateTo=..`) has unstable OFFSET pagination. The same 2-week window
returned **182 unique releases at PageSize=100 vs 149 at PageSize=1000**,
with duplicates *within* a single run and a union (234) larger than either
pass — rows shift between pages as the underlying result order changes, so
some fall into the gaps. PageSize=10000 returned only 1,365 rows for a
range that holds far more; 20000 times out. Any ingestion built on this
endpoint silently misses tenders — no error, no signal, just an
incomplete catalog.

The reliable alternative is proven: ocids embed a sequential integer
(`ocds-9t57fa-{N}`), and enumerating the single-release endpoint
(`GET /api/OCDSReleases/release/ocds-9t57fa-{N}`) is deterministic and
complete. Max ID was 166,392 on 2026-08-20; of the ID space, 3,147 IDs
return a stable `{}` (never published) and 32 return persistent HTTP 500
(server-side corrupt) — both classes are stable and enumerable. The
resulting **complete corpus — 163,321 unique releases, 2021-04 → 2026-08,
~50 MB gzipped — now lives in the project's shared file storage at
`/mnt/project-files/etenders-corpus/`** (30 half-year JSONL shards +
`manifest.json` + `SUMMARY.md` + `ocids.txt.gz` + a `README.md`
documenting the incremental resume pattern: binary-search the new max ID
upward, then fetch the gap). Per client instruction the corpus must NOT
be committed to a git repo — reference it by path only.

How this touches the SDK today: the SDK itself never calls the eTenders
API. Its live path is the daily scheduler hook (`manifest.json`
`scheduler_events.daily`, line 50) → `src/control/tasks.py:29
refresh_opportunities_cache` → `refresh_all_data.py:32` →
`fetch_remote_json.py`, which pulls the **pre-synced published catalog**
from `BASE_URL = "https://raw.githubusercontent.com/RokctAI/opportunities/
main/published/api/"` (`opportunity_utils/__init__.py:26`). So the silent
loss applies to *whatever feeds that catalog* — if the upstream
`/opportunities` sync uses list-endpoint pagination, the catalog the whole
SDK serves is silently incomplete (which would also compound F-08's
enrichment-floor problem). And the SDK is one step from importing the bug
directly: `tests/test_tender_fetching.py:46–110` already specifies a
direct fetcher (`_fetch_and_cache_tenders_on_control`, config key
`etenders_api_url`, paginate-until-empty-page into the existing
`Raw Tender Cache` doctype, `src/control/doctype/raw_tender_cache/`) that
is not yet implemented in `tasks.py` — the test spec canonises exactly
the pagination pattern now proven lossy. Recommendation: the
opportunity-cache/ingestion layer (and the upstream catalog sync) must
use ID enumeration — or at minimum cross-check list results against ID
continuity — never bare list-endpoint pagination; incremental sync =
fetch IDs above the last known max, **plus re-fetch of recent IDs**,
since releases are compiled snapshots that gain awards/amendments after
first publication; and the planned `_fetch_and_cache_tenders_on_control`
should be implemented against the single-release endpoint before the
test's pagination contract hardens into code.

### F-15 · studio ↔ TenderAssist integration gap: the Company Profile returnable has no generation path on either side (feature, per client discussion)

The company-profile mock build (`mock-samples/company-profile/`) exposed a
two-sided seam, raised in client discussion, between the studio SDK and
TenderAssist:

**(a) designer ships no A4 company-profile design template — studio's
Document→Design handoff has no visual target for the most commonly
demanded tender returnable.** The designer repo's shipped templates are
business cards, an A5 flyer, a pull-up banner, the z-fold A4 brochure, a
corporate folder, signboards, a pen barrel and 16:9 deck slides
(`examples/templates/`) — no multi-page A4 document; the mock had to
author its four A4 page templates by hand
(`mock-samples/company-profile/templates/*.svg`). The content side has the
mirror-image gap: startup_os's Document→Design handoff is its design-brief
export — `export_briefs` in The-Rokct-Protocol
`core/utils/startup_os/branding.py` (lines 599–769) — and `build_briefs`
emits exactly three brief types: **poster, pull-up banner and flyer**
(confirmed by the real run of
`mock-samples/company-profile/startup-os/run_startupos_profile.py`, which
emitted `poster.json`, `pullup-banner.json`, `flyer.json`; the briefs are
not committed — only the tender-relevant outputs are — but are
reproducible via that runner).
There is no company-profile brief, so even though startup_os *does* ship
the company-profile content template (`business_profile.md`, one of its 27
templates), nothing ever hands that document to the designer engine as a
design job.

**Status note (2026-08-21):** The studio/designer side of this finding —
including the A4 profile design template (part (a)) — is being handled in a
separate workstream. **The SDK builder should not touch the studio or
designer repos.** Only part (b), the TenderAssist-side hook (returnable row →
generated profile artifact attached to the bid), is in scope here.

**(b) TenderAssist demands "Company Profile" as a returnable but has no
hook to satisfy it from studio output.** The ICT-CAPABILITY form template
exists precisely for this class of returnable
(`fixtures/tender_form_templates.json`, "Website / Hosting Capability
Schedule", reached via a captured returnable's `template_code` —
`pack_builder.py` lines 260–268), and the captured-returnables path
carries rows like "Company profile and organogram" (mandatory,
`template_code: ICT-CAPABILITY` — `tests/test_bid_pack.py:463`). But the
row can only render a **worksheet to fill by hand**; there is no way to
attach, let alone generate, the actual profile document — even though the
ecosystem demonstrably produces one (the mock's designed A4 PDF from the
designer engine and the compliance-gated `business_profile.md` from
startup_os, now wired into the TWK sample's `04-pack-structure.md` item
16 as the satisfied slot).

**Status note (2026-08-21):** PR #45 delivered the TenderAssist-side hook
of part (b), control-side only: four new fields on
`tender_bid_returnable` (`studio_scope`, `generated_artifact` Attach,
`artifact_attested`, `artifact_attached_on`), an
`attach_returnable_artifact` endpoint (links only a File already attached
to the bid, entitlement-checked, two-step attach→attest), a
`[RETURNABLE-ARTIFACT-UNATTESTED]` submission-gate lint, and worksheet
rendering of the artifact state (SATISFIED BY GENERATED ARTIFACT / NOT
YET ATTESTED / GENERATE VIA STUDIO). It deliberately does not call
startup_os. The generation side is now available in startup_os
(The-Rokct-Protocol commit `f6b885f`, merged 2026-08-21): selective
generation via `compile_instance(..., only=["business_profile"])` plus a
per-artifact gap check (`check --for`, `--json`). The open item is the
studio-side wiring that produces `business_profile` + `compliance_log`
and attaches them to the bid — owned by the startupos session, not the
SDK builder.

Recommendation — a **returnable-generator integration**: a returnable row
of the company-profile class raises a studio **Document Request**
(startup_os compiles the compliance-gated content from the Tender Business
Profile / capability register) and optionally a **Design Request** (the
designer engine renders it against an A4 company-profile template), and
the generated artifact is attached to the bid as that returnable's
satisfying document. Gate it exactly like the other outputs: the artifact
inherits the profile's amber gaps and provenance/override log, counts
toward `validate_submission_readiness` only when generated-and-attested,
and never dispatches ungated (same discipline as F-13). Prerequisites on
the studio side: designer ships an A4 multi-page company-profile template,
and `export_briefs` grows a company-profile brief type so the
Document→Design handoff covers the document class tenders actually demand.

## Machine-readable findings table

| finding_id | type | severity | evidence | recommendation |
|---|---|---|---|---|
| F-01 | gap | high | RNM 8/2/RNM0614 needs MBD A16–A21/B2 AND CIDB C1.1/T2.x in one submission; workaround = two packs (`mock-samples/8-2-rnm0614-mgodlwa-bridge/03-bid-pack.html` + `03-bid-pack-cidb-overlay.html`), neither complete | Base regime + overlay regime(s) per Tender Bid; union form set, merged pack index |
| F-02 | gap | high | Fixture form set emitted regardless of pack: RNM MBD1 unused (real offer form C1.1); no templates for RNM A1–A15, DFFE Annexures A/B/C, VCW returnable functionality schedules — all carried by generic worksheet + manual rows; Musina full pack quantifies it: 4 of 9 returnable forms match templates exactly (MBD 4/6.1/8/9), buyer Forms A–E (offer, signatory auth, legacy HDI, 1939 local content, OHS s37(2)) + twelve §5.1 mandatory returnables (incl bank rating A–C) have none | Per-pack returnable list overrides fixture form set; capture path for recurring buyer-authored templates; STATUS 2026-08-21: follow-up parser calibration (4 fixes) delivered in PR #45 (merged, head `f18afae`), verified on the real Musina PDF — returnables 0 → 18/21, tender number QUOTED, other scalars unregressed, packs byte-identical; remaining gap: 3 bare `MBD 6.1`/`MBD8`/`MBD 9` headings; verify suites committed at `tender/frappe/tests/verify/` (58/58) |
| F-03 | fixture-delta | high | All 5 sample buyers in no pattern list; GATE-SECTOR list = "department of tourism" only (missed 7 PSIRA pre-qualifiers); GATE-INSURANCE missed VCW R15m public liability; GATE-POPIA scoped SANRAL/Transnet (missed municipal website-hosting AND Musina, where POPIA/PAIA compliance is explicit spec text §4(c) with SA-only hosting + 18-month call-recording retention); net: 9 of VCW403's 13 disqualifiers had no auto rule, 5 of 6 warning-page gates `[manual]` | Subject-matter/description/spec-text triggers alongside buyer patterns; corpus-driven pattern list expansion |
| F-04 | fixture-delta | high | GATE-RATES MBD-only but VCW (SBD water board) demands rates clearance; GATE-CIDB/GATE-COIDA CIDB-only but RNM-under-MBD and VCW works section both demanded them — manual rows in both samples; GATE-MBD5's >R10m value trigger correctly off at Musina's ≈R2.57m yet the pack demands audited 3-yr AFS from every bidder (5.1(i)) — manual row | Demand-driven triggers (content/buyer type); regime and value as priors, not fences |
| F-05 | gap | medium | Single `functionality_threshold`/`self_score` pair vs VCW dual sections (≈335 + 165 pts, each 75% kill), DFFE 6-criterion 100-pt rubric, RNM METHOD 4 42/70 — all hand-built outside the SDK; Musina negative case: NO scored functionality stage at all (mandatory requirements pass/fail → 80/20), inexpressible except as ambiguous zero | Child table of scored sections/criteria (label, max, threshold, self-score); current pair = single-section case; explicit "no scored functionality" state |
| F-06 | gap | high | Category norm (client domain knowledge): 5-year maintenance term incl hosting; corpus corroborates hosting in all 4 website adverts (`-165555`, `-165060` 3yrs, `-165289` 36mo, `-164801`); Musina website tender NOT in corpus (7 unrelated RFQs); UPDATE sample 5: first full Musina pack on file (Tender 18-2025/26 helpdesk) states **3 years/36 months** (5-yr belief per client domain knowledge not confirmed by this pack — one data point) and its official pricing schedule is a Year 1/2/3 once-off/monthly/annual grid + per-unit call tariffs the SDK cannot represent; SDK has no term field, no escalation rule, no year-by-year model — TWK 5-yr schedule (R2,179,056.00, mock 5.0% CPI) and Musina 3-yr schedule (R2,573,750.00) both hand-built as flat lines; KILL-ALT-OFFER makes escalation compliance-relevant | Term fields on bid context; escalation provision field; year-by-year quotation schedule incl unit-tariff lines; rule flagging fixed pricing on multi-year/prescribed-formula packs |
| F-07 | gap | medium | Tender Business Profile has no portfolio/hosting/data-residency/SLA/security-cert/support-tier fields; no website/SLA/DR rule or template; all TWK website evidence hand-carried (`mock-samples/cor-01-2026-27-twk-website/`) | Sector-extensible capability child table (works for ICT, PSIRA security, construction plant/personnel alike) |
| F-08 | data | high | Whole municipal-website category is advert-only in `/opportunities` (4 records, ~1.7KB each): checklist beyond universal spine, real matrix and threshold unconfirmable from the catalog the SDK serves | Enrichment coverage as first-class metric; auto pack-collection fatal gate on advert-only bids; per-category enrichment stats |
| F-09 | code-change | high | `tasks.py`, `submission_gate.py`, `checklist.py`, API endpoints import via literal `{app_name}` placeholder (`tasks.py` line ~39; `compliance-ignore-file: syntax-error`); unimportable outside a composed bench — sample build had to hand-compose gate strings and mirror checklist assembly | Composition-independent core modules with thin `{app_name}` endpoint shims; standalone importability = testability |
| F-10 | fixture-delta | medium | Only SBD3.x carries `source_field: pricing_lines` (`tender_form_templates.json`); MBD/CIDB packs render no line-item table — TWK 8-line quotation surfaces only as MBD1 total | MBD pricing-schedule worksheet + CIDB T2.x priced variant sourcing `pricing_lines` |
| F-11 | fixture-delta | medium | RNM locality goals (10/5/1, not B-BBEE), black-ink, original+1-copy; DFFE master-doc + USB + TOC screening; VCW ±20% price band, R250m rotation, unannounced inspections; Musina initial-every-page-bottom, attachments-after-price-schedule, submit-as-a-whole/no-pages-removed, tender-box hours, written-queries-only, toll-free number retention; no `buyer-profiles/` sheet for any sample buyer | Buyer-profile sheets for actively-bid buyers; per-buyer quirk rule type rendered as auto checklist rows |
| F-12 | fixture-delta | medium | Musina pack carries 3 preference frameworks at once: operative PPR 2022 MBD 6.1 specific goals (HDI 10/women 4/disability 3/youth 3) + pre-2011 HDI equity framework (PPPFA 2000 explanation, Form C "…% = … Points out of 20 (<R1 000 000)") + 1939-Ordinance local-content/SABS Form D; legacy forms must still be completed (non-completion forfeits preference) but only one framework scores; SDK models one preference system per bid | Per-pack returnable capture lists legacy preference forms as mandatory returnables; lint warning "pack contains conflicting preference frameworks; operative system: X" |
| F-13 | feature | medium | Per client request: generate pack → email buyer, with pack attached, to the tender record's Contact Person/Email (rendered `opportunities/[type]/[slug]/page.tsx` lines 192–193, never used to send); framework email exists (`frappe.sendmail` in `artifact_expiry.py:52`, user-facing only) but `generate_bid_pack.py` returns the pack and stops — no buyer-ward dispatch anywhere in `src/control/api/tenders/`; caveat: all 5 sample tenders demand physical sealed-envelope/tender-box submission (each sample's `04-pack-structure.md`; Musina Room 53 box hours) and SA packs commonly reject emailed competitive bids (KILL-01 family) | Auto-dispatch gated on `validate_submission_readiness` clean (no fatal gates, all mandatory returnables) AND explicit user confirmation per send; (a) full email submission only where the pack explicitly allows it (common for RFQs/quotations), (b) otherwise same machinery for allowed correspondence to the named contact (written clarification questions, briefing confirmations, CSD verification, cure-window replies), (c) per-tender submission-channel field (physical-box/portal/email-allowed) so the SDK knows which mode applies |
| F-14 | data | high | eTenders list endpoint (`/api/OCDSReleases?dateFrom=..&dateTo=..`) has unstable OFFSET pagination, verified 2026-08-20: same 2-week window = 182 unique releases at PageSize=100 vs 149 at PageSize=1000, duplicates within a run, union 234 > either pass; PageSize=10000 returns only 1,365 rows; 20000 times out — silent loss for any list-based ingestion. ID enumeration of `ocds-9t57fa-{N}` via `/api/OCDSReleases/release/` is deterministic and complete (max ID 166,392; 3,147 stable-`{}` never-published; 32 persistent-500). Complete corpus (163,321 releases, 2021-04→2026-08, ~50 MB gz) at `/mnt/project-files/etenders-corpus/` (30 JSONL shards + manifest + ocids + resume README; NOT for git, per client). SDK exposure: live path reads the pre-synced GitHub catalog (`opportunity_utils/__init__.py:26` BASE_URL; `tasks.py:29` daily) so the loss applies to whatever feeds it; `tests/test_tender_fetching.py:46–110` canonises paginate-until-empty against `etenders_api_url` for the unimplemented `_fetch_and_cache_tenders_on_control` → `Raw Tender Cache` | Ingestion (SDK and upstream catalog sync) uses ID enumeration, or at minimum cross-checks list results against ID continuity — never bare list pagination; incremental sync = fetch IDs above last known max + re-fetch recent IDs (releases are compiled snapshots that gain awards/amendments); implement the planned direct fetcher against the single-release endpoint before the test's pagination contract hardens into code |
| F-15 | feature | medium | Per client discussion: (a) designer ships no A4 company-profile design template (shipped `examples/templates/` = cards, A5 flyer, pull-up, z-fold A4, folder, signboards, pen, 16:9 slides; mock authored its own 4 A4 SVGs at `mock-samples/company-profile/templates/`), and startup_os's Document→Design handoff — `export_briefs`/`build_briefs` in protocol `core/utils/startup_os/branding.py` (599–769) — exports poster/pull-up/flyer briefs only (proven by the real run of `mock-samples/company-profile/startup-os/run_startupos_profile.py`; briefs reproducible via that runner, not committed), so the studio pipeline has no visual target for the most-demanded tender returnable despite startup_os shipping `business_profile.md`; (b) TenderAssist's captured returnables demand "Company Profile" (ICT-CAPABILITY template via `template_code`, `pack_builder.py:260–268`; `tests/test_bid_pack.py:463` "Company profile and organogram", mandatory) but render only a hand-fill worksheet — no hook to satisfy the row from studio output, though the mock proves the artifacts exist (designer A4 PDF + startup_os `business_profile.md`, wired as the satisfied slot in the TWK sample's `04-pack-structure.md` item 16) | Returnable-generator integration: company-profile-class returnable row → studio Document Request (startup_os content from the business profile/capability register) → optional Design Request (designer render on a new A4 profile template) → generated artifact attached to the bid as the satisfying document; gated like other outputs (inherits amber gaps + provenance log, counts toward `validate_submission_readiness` only generated-and-attested, never dispatches ungated per F-13); prerequisites: designer ships an A4 company-profile template, `export_briefs` adds a company-profile brief type (part (a) handled in a separate workstream); STATUS 2026-08-21: part (b) TenderAssist-side hook delivered in PR #45, control-side only — `tender_bid_returnable` artifact fields (`studio_scope`, `generated_artifact`, `artifact_attested`, `artifact_attached_on`), `attach_returnable_artifact` endpoint (attach→attest, entitlement-checked), `[RETURNABLE-ARTIFACT-UNATTESTED]` gate lint, worksheet artifact states; no startup_os call by design; generation side now available in startup_os (protocol `f6b885f`: `compile_instance(..., only=["business_profile"])`, `check --for`/`--json`); open: studio-side wiring to produce and attach `business_profile` + `compliance_log` (owned by the startupos session) |
| W-01 | data | n/a | Auto-fill 91.8% (VCW 56/61) to 97.1% (TWK and Musina, each 66/68) across six generated packs; amber/red gap rendering | Keep — extend, don't rework |
| W-02 | data | n/a | Fatal gates never silent: warning page + cover banner on every pack with open gates (VCW six-gate page) | Keep |
| W-03 | data | n/a | Negative/positive value triggers correct: GATE-MBD5 ON at R42.5m RNM (matches real A17), OFF at R2.18m TWK; GATE-RATES/KILL-19 attach from MBD regime alone | Keep |
| W-04 | data | n/a | Scoring exact: 80/20 vs 90/10 by value, price-points formula, functionality elimination; universal spine matches real kill language nearly clause-for-clause across all four full packs (incl Musina GATE-RATES near word-for-word; KILL-01 genuinely fired on sample 5's closed window) | Keep |
