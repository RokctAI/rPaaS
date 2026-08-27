# Tender & Grant Suitability Scoring — Corpus Measurements and Proposed Fit Model

Release date: 2026-08-23. Audience: **the agent building the TenderAssist SDK**
(`tender/frappe`) and the opportunities-registry workstream. Sources: the
`/opportunities` registry corpus (1,990 tender cards, 416 grants, 1,212 equity
funders, 8 EEIP programmes, measured 2026-08-23), `rules-table.md` (17 gates /
17 kills / 8 score rules / 12 info), the 69 fixture records in
`tender/frappe/fixtures/tender_compliance_rules.json` (47 Fatal / 12 Curable /
10 Points-only), `functionality-thresholds.md` (238 explicit thresholds from a
~1,200-document scan), `SA-Tender-Completion-Guide.md` (PPR 2022 mechanics),
and `SDK-Improvement-Findings.md` (open items O-02/O-03). Every number below
was measured against the registry corpus or cited from a released document;
nothing is estimated. No implementation code ships with this report — the
worked example was produced by an analysis script kept outside the repo.

**One-paragraph summary.** The registry's tender cards carry 21 uniformly
populated structured labels but almost no pack-level detail: 83.2% of cards
are advert-only, and the factors that decide bids (preference system,
functionality threshold, CIDB grade, fees, submission channel) are extractable
on only 2.5–12.7% of the corpus. A suitability score built on this data can
therefore honestly predict **eligibility, functionality-gate survivability
(weakly, and only with pack text), and process feasibility — not award**. The
proposal is a two-stage deterministic scorer: hard gates that fire only on
positive evidence (never on unknowns), then a 0–100 weighted fit score
renormalised over the factors actually known, with a confidence tier (A =
pack-verified, B = advert-only). On 83% of cards the score's first job is
triage — ranking which packs to fetch — not bid selection. A worked run over
all 1,990 cards for one illustrative ICT-services SMME profile no-bids 494
cards (24.8%), 445 of them purely because a compulsory briefing has already
been held, and surfaces 35 strong-fit cards (1.8%).

---

## 1. Corpus measurements — what the cards actually carry

### 1.1 Shape of the corpus

- **1,990 tender cards**; 1,985 (99.7%) open at measurement date, 2 closed, 3
  with unparseable closing dates ("See Documents"). The registry prunes
  expired cards, so the corpus is a rolling window of live opportunities, not
  an archive — closing dates cluster in 2026-08 (845) and 2026-09 (1,094).
- **334 cards (16.8%) have OCR pack sidecars**; 1,656 (83.2%) are
  advert-only (the repo's own `source_record_class == "Advert-Only"`, the
  trigger for fixture rule GATE-PACK-COLLECT). Sidecar text: median 66,828
  chars, mean 86,200, max 968,388; 9 sidecars are under 1,000 chars
  (effectively empty).
- **21 card labels are populated on 100% of cards**: tender number,
  institution, source card, flag, tender type, province, date published,
  closing date, place required, briefing yes/no, briefing compulsory yes/no,
  briefing date/time, briefing venue, contact person, email, telephone,
  direct link, tender documents, status, data completeness, last verified.
  Informative rates are near-100% for all of these except briefing venue
  (52.8%) and the "Tender Documents" label itself (0% — document links live
  in the link fields, not under that label). This uniform structured layer
  is the only data present on every card, and it is what a scorer must
  run on.

### 1.2 Distributions on the universal labels

| Dimension | Distribution (n=1,990) |
|---|---|
| Province | Gauteng 407 (20.5%) · Western Cape 306 · KwaZulu-Natal 297 · Eastern Cape 244 · **National 218 (11.0%)** · Mpumalanga 172 · Limpopo 157 · North West 65 · Northern Cape 65 · Free State 59 |
| Buyer type | SOE/public entity 808 (40.6%) · municipality 631 (31.7%) · provincial dept 229 (11.5%) · national dept 160 (8.0%) · municipal entity 54 · other 46 · trust/NGO 30 · education 25 · health facility 7 |
| Tender type | Open tender 1,250 (62.8%) · RFQ 446 (22.4%) · RFP 231 (11.6%) · RFI 23 · EOI 13 · participation 10 · limited tender 7 · SITA contract 6 · sole source 3 · transversal 1 |
| Category rollup | services 1,235 (62.1%) · construction/built-env 375 (18.8%) · goods/supplies 296 (14.9%) · other 72 · disposals 12 |
| Briefing | session announced 1,063 (53.4%); **compulsory 757 (38.0%)** |
| Days to close | 0–7: 673 (33.9%) · 8–14: 556 (28.0%) · 15–30: 635 (32.0%) · 31–60: 110 · >60: 11 · already passed: 2 — **61.9% close within 14 days** |

Top institutions: ESKOM 158, Transnet SOC Ltd 44, PRASA 38, ACSA 37, City of
Cape Town 28, SANRAL 27, Public Works 27, Polokwane Municipality 25. No
duplicate tender numbers.

### 1.3 Factor availability — the sidecar cliff

The decisive bid factors exist almost exclusively in pack text. Measured
availability (whole corpus, then split advert-only vs sidecar):

| Factor | Whole corpus | Advert-only (n=1,656) | Sidecar (n=334) |
|---|---|---|---|
| Preference system stated 80/20 | 232 (11.7%) | 7 (0.4%) | 225 (67.4%) |
| Preference system stated 90/10 | 174 (8.7%) | 1 (0.1%) | 173 (51.8%) |
| Functionality mentioned | 236 (11.9%) | 36 (2.2%) | 200 (59.9%) |
| Functionality threshold numeric | 133 (6.7%) | ~2 | 131 (39.2%) |
| CIDB mentioned | 152 (7.6%) | 46 (2.8%) | 106 (31.7%) |
| CIDB grade extractable | 71 (3.6%) | 31 (1.9%) | 40 (12.0%) |
| B-BBEE mentioned | 262 (13.2%) | 88 (5.3%) | 174 (52.1%) |
| Contract duration stated | 819 (41.2%) | 564 (34.1%) | 255 (76.3%) |
| Document fee stated | 49 (2.5%) | 0 (0.0%) | 49 (14.7%) |
| Submission mode extractable | 252 (12.7%) | ~7 | 245 (73.4%) |
| Estimated value / budget | **1 (0.1%)** | — | — |

Detail on the extracted values:

- **Preference system**: 172 cards state both 80/20 and 90/10 (packs quoting
  the PPR 2022 rule in full, or deferring determination to after opening —
  the SCORE-SYSTEM-8020 pattern). Only 62 cards state exactly one system
  (60 state 80/20 alone, 2 state 90/10 alone).
- **Functionality thresholds** (133 cards): mode **70 (57 cards)**, then 51
  (29 — the "minimum of 51%" municipal phrasing), 60 (23), 75 (23), 80 (22),
  90 (8), 50 (7). This matches the released `functionality-thresholds.md`
  scan (238 of ~1,237 documents; mode 70, median 70.0, raw range 36–100 with
  the caveat that low-tail values are mostly raw points on non-100 scales).
- **CIDB grades** (71 cards): spread across 1–9 and classes CE/GB/EB/EP/ME/
  SO/SF/SH/SL/SI/SQ; 4GB and 5GB (8 each) the most common single demands.
- **Durations** (819 cards): 36 months dominant (483 mentions), then 60
  (348), 120 (183), 24 (159), 12 (150). Multi-year terms are the norm where
  a term is stated at all.
- **Fees** (49 cards): min R190, median R500, max R1,500 — consistent with
  DELTA-V2-24's "document fees run R300–R2,300+" from the pack corpus.
- **Submission modes** (252 cards): hand delivery 217, email 80, online
  portal 77, courier mentioned 64 (cards can state several).
- **Budget/estimated value appears on exactly 1 card of 1,990.** Estimated
  value can never be a scoring factor at advert stage; the fixture
  GATE-MBD5's `estimated_value_over: 10000000` trigger and the R50m 80/20
  boundary are only computable after pack fetch, if at all.

**B-BBEE over-enumeration warning.** 262 cards mention B-BBEE and 77 mention
specific levels, but the level histogram (Level 3: 22, Level 1: 16, Level 2:
9, …, Level 8: 5) shows what these mentions are: preference-point tables
enumerating *every* level's points, not eligibility bars. A scorer that gated
on "B-BBEE Level N appears in the text" would disqualify bidders from tenders
that merely publish a points table. Only an explicit pre-qualification
placement (the GATE-BBBEE-PREQUAL / DELTA-V2-01 pattern, buyer-specific,
Fatal) may gate; plain B-BBEE is Points-only (fixture GATE-BBBEE, Universal).

### 1.4 The O-03 discipline

`SDK-Improvement-Findings.md` O-03 records that keyword/subject substring
triggers have a documented but **unmeasured over-fire risk** (a "hosting"
keyword firing POPIA/ICT gates on non-ICT packs), and that the corpus history
runs first too-narrow buyer lists, then possibly too-broad subject patterns.
The scoring model below therefore keys on **structured fields only** —
category rollup, province, dates, briefing flags, tender type, buyer type —
and the extraction-based factors (CIDB grade, thresholds, fees, modes) enter
only where a value was positively extracted. Any future keyword-based factor
must ship with a measured fire rate over the project's eTenders corpus (163k
releases) before it is allowed to move a score.

---

## 2. Gates versus graded factors

The rules corpus splits cleanly into two behaviours, and a suitability score
must respect the split:

**Binary gates (fatal, non-compensable).** 47 of the 69 fixture rules are
Fatal; all 25 Disqualification Causes are Fatal. GATE-CSD, GATE-TCS,
GATE-DEFAULTERS, GATE-STATE-EMP, GATE-CIPC are Universal — they apply to
every public bid regardless of the card. GATE-CIDB is statutory: the exact
class and grade must be active at close (with a 21-working-day registration
grace at some buyers, DELTA-V2-05, and the lead-partner-within-one-grade JV
rule as the only softening). GATE-BRIEFING is pass/fail wherever the briefing
is compulsory, with lateness counting as absence. No amount of sector fit
compensates for a failed gate; averaging a gate into a weighted score would
report "62/100" on a bid that is legally dead.

**Graded factors (compensable).** Everything else on a card — sector
proximity, geography, time pressure, buyer burden, contract economics — is a
matter of degree, and the Points-only/Curable rules (10 + 12 of 69) behave
the same way: missing B-BBEE evidence zeroes points but the bid survives
(GATE-BBBEE, Universal Points-only); pricing and form defects are curable at
tiered-cure buyers (INFO-CURE-CULTURE).

Hence a two-stage design: Stage 0 gates return NO-BID with reasons; Stage 1
produces a 0–100 fit score only for cards that pass. The two outputs never
mix.

**Gates fire only on positive evidence.** This is the O-03 lesson applied to
scoring. On advert-only cards nearly every gate condition is unknowable:
absence of a CIDB mention does not mean no CIDB requirement; absence of a
briefing flag is meaningful (the label is universal) but absence of pack text
means nothing. A gate that fired on "unknown" would no-bid 83% of the corpus
for lack of information. So: unknown never fails a gate — it lowers the
confidence tier instead.

---

## 3. What a score can honestly predict

This section bounds the claim before the model is proposed. Under PPR 2022 as
documented in `SA-Tender-Completion-Guide.md` and `rules-table.md`:

1. **Price decides award, and price is unknowable pre-bid.** Lowest
   responsive price takes all 80 (or 90) points; everyone else scores on
   Ps = 80 × (1 − (Pt − Pmin)/Pmin) (SCORE-PRICE-FORMULA). Proximity to the
   lowest responsive *competitor* dominates the outcome, and no scorer sees
   competitors' prices.
2. **Preference points are buyer-specific.** Under the 2022 regulations every
   buyer defines its own specific-goals table: one SOE gives Level 1 only 5
   of 20 points, another gives Level 1 all 20, a third gives 20 points only
   to Levels 1–2 (guide §4.3). A profile's B-BBEE level cannot be converted
   to points without the individual pack.
3. **The applicable system itself can be deferred.** 80/20 applies up to and
   including R50m, 90/10 above — and some packs determine which applies only
   after opening (SCORE-SYSTEM-8020). Estimated value appears on 1 of 1,990
   cards.
4. **Winning on points is necessary, not sufficient.** The PPPFA s2(1)(f)
   objective-criteria stage lets buyers pass over the top-ranked bidder
   (INFO-OBJ-OVERRIDE), and post-scoring vetting (GATE-VETTING) can
   disqualify irrespective of points.
5. **There is no outcome data.** Neither the registry nor the repo holds
   award results, so no model can be fitted or validated against wins. This
   is why the proposal is deterministic with cited evidence per factor, not
   ML.

What the corpus *does* support predicting:

- **Eligibility** — the gate layer: timing, statutory registrations where
  stated, profile completeness. High confidence; the rules are documented
  and the trigger fields are structured.
- **Functionality-gate survivability** — weakly, and only at tier A: with a
  pack in hand, the stated threshold (mode 70) can be compared against the
  profile's capability-evidence coverage. SCORE-EVIDENCE makes this an
  evidence-counting exercise, which a capability register supports; but
  per-criterion sub-minimums exist (DELTA-V2-04 zero-on-any-criterion
  auto-DQ; several packs disqualify on a single criterion even when the
  overall threshold is met), so this remains an estimate.
- **Process feasibility** — whether the bidder can physically produce a
  compliant submission in time: days to close, compulsory briefing
  attendance, hand-delivery logistics, document fees.

The score is a **fit-and-feasibility score, not a win-probability**. Every
surface that displays it should say so.

---

## 4. Proposed model — two-stage deterministic scorer with confidence tier

### 4.1 Stage 0 — hard gates

Any failed gate → **NO-BID, score 0, all firing reasons listed**. Gates fire
only on positive evidence.

- **G1 · Timing** — closing date already passed; or a compulsory briefing
  (card label, 38.0% of cards) whose date/time (card label, 99.8%
  informative) has already passed unattended. With 61.9% of cards closing
  within 14 days and briefings typically scheduled within days of
  publication, this gate does most of the real work (measured in §6: 445 of
  494 no-bids). Placeholder briefing dates (0001-01-01, 37 cards among the
  compulsory subset) are unknowns and never fire.
- **G2 · CIDB** — a required grade/class was extracted (71 cards) and
  exceeds the profile's `cidb_grade` (a single free-text field on the Tender
  Business Profile; empty = no registration). Statutory per GATE-CIDB.
  One-grade-below-with-JV (GATE-JV lead-partner rule) should surface as a
  *conditional* outcome ("biddable via JV with a graded lead partner"), not
  a pass.
- **G3 · B-BBEE pre-qualification** — only where the buyer/pack places the
  certificate in a pass/fail table (GATE-BBBEE-PREQUAL, buyer-specific,
  Fatal; DELTA-V2-01). Never gate on level *mentions* (§1.3 warning). Plain
  B-BBEE stays Points-only.
- **G4 · Profile completeness for public bidding** — missing CSD MAAA
  number, TCS PIN, or CIPC registration on the bidder profile. This is a
  profile-side gate: it applies identically to every card (GATE-CSD,
  GATE-TCS, GATE-CIPC are Universal Fatal fixtures) and its remedy is
  fixing the profile, not skipping the tender — the UI should present it
  once, not per card.
- **G5 · In-state-service directors** — any director row with
  `in_state_service` checked, absent filed executive-authority approval
  (GATE-STATE-EMP, KILL-SBD4).

### 4.2 Stage 1 — graded fit, 0–100

Weighted sum over the factors **actually known** for the card, renormalised
over the known-factor weight so advert-only cards share the scale:

score = 100 × Σ(wᵢ·fᵢ) / Σ(wᵢ), over factors i with a known value

Universal factors (present on 100% of cards) carry the bulk of the weight,
because prevalence bounds usefulness: a perfectly discriminating factor
available on 2.5% of cards cannot rank the corpus.

| Factor | Weight | Source fields | Rationale |
|---|---|---|---|
| Sector/category match | 30 | `### Category` + rollup vs profile sectors + capability register | The biggest universal discriminator (services 62.1% / construction 18.8% / goods 14.9%); structured, immune to O-03 |
| Geography | 15 | Province label vs profile operating footprint | Universal; National (11.0%) fits every footprint; briefing/site logistics correlate |
| Process feasibility | 20 | Days-to-close bucket; compulsory-briefing travel burden by province; hand-delivery where extracted | 61.9% close ≤14 days — time pressure is the dominant practical constraint after sector |
| Buyer burden | 10 | Buyer type + known buyer-quirk fixture rules | Municipal buyers add rates-clearance (GATE-RATES, arrears windows 1–3 months buyer-specific) and single-shot cure culture; 12 QUIRK-* fixtures name specific buyers |
| Engagement economics | 10 | Tender type; stated duration | RFQ (22.4%) is lighter process than open tender (62.8%); 36/60-month terms (483/348 mentions) signal recurring-revenue fit |
| Pack-informed | 15 | Sidecar-only: functionality threshold vs capability-evidence coverage; preference regime; fee; submission mode | Scoreable on the 16.8% sidecar subset; drives the A/B tier split |

Starting weights are prevalence × judgment, pending the calibration round in
§9; the worked example (§6) sanity-checks that they produce a non-degenerate
distribution.

**Confidence tier**: **A** = pack-verified (sidecar present, pack-informed
factors in the denominator), **B** = advert-only (score computed on the
85-weight universal factor set). The tier is displayed with the score, always.

**Bands**: ≥80 strong fit · 60–79 worth review · 40–59 marginal · <40 poor ·
0 no-bid (with reasons).

### 4.3 Profile-side additions the model needs

The Tender Business Profile doctype currently holds identity, B-BBEE,
a single `cidb_grade`, directors, banking-on-CSD, and an 11-kind capability
register — but **no sector taxonomy, no geographic footprint, no turnover
figure** (only the EME/QSE/Generic band implied by `enterprise_type`).
Stage 1 cannot compute its two heaviest factors without:

1. `sectors` — a small multi-select aligned to the card category rollup plus
   the recurring specific categories (ICT, security, cleaning, construction
   classes, professional services, …);
2. `operating_provinces` — multi-select of the nine provinces + National;
3. `briefing_travel_radius` or per-province willingness — feeds the
   compulsory-briefing burden term in process feasibility.

These are additive profile fields; nothing in the existing doctype changes.

---

## 5. Advert-only handling

83.2% of cards are advert-only, and on them the pack-informed factor is
undefined. The model's answer is threefold:

1. **Renormalisation** — the score is computed over the 85 points of
   universal weight, so advert-only cards land on the same 0–100 scale
   rather than being capped at 85.
2. **Tier B labelling** — the consumer always sees that the score is
   advert-grade. A tier-B 78 and a tier-A 78 are different claims.
3. **Triage, not selection** — on advert-only cards the score's first job is
   to rank **which packs to fetch**. Every card carries a direct document
   link and eTenders documents download freely, so the pipeline is: score at
   tier B → fetch packs for the top band → OCR → re-score at tier A → then
   decide. This also progressively fixes the corpus itself: the 16.8%
   sidecar floor is not a law of nature, it is the current fetch backlog.

A tier-B score should never be presented as a bid/no-bid recommendation on
its own; GATE-PACK-COLLECT (Fatal, Conditional on Advert-Only class) already
encodes the repo's position that an unfetched pack is itself a blocking
condition for actual bidding.

---

## 6. Worked example — one profile over the full corpus

Illustrative SMME profile: **ICT services; operating footprint Gauteng +
National; B-BBEE Level 1 EME; no CIDB registration; CSD/TCS/CIPC complete; no
in-state-service directors.** Scored against all 1,990 cards on 2026-08-23
with the §4 gates, weights and bands. (Analysis script external to the repo;
weights are the §4.2 starting values.)

**Stage 0 — gate outcomes: 494 cards (24.8%) NO-BID.**

| Gate reason | Cards |
|---|---|
| G1: compulsory briefing already held (unattended) | 445 |
| G2: CIDB grade required, none on profile | 71 |
| G1: closing date passed | 2 |
| (cards firing more than one reason) | 24 |

Notes:

- The briefing gate dominates, exactly as the timing data predicts: of the
  757 compulsory-briefing cards, **445 (58.8%) had already held their
  briefing** at measurement date while still showing as open — every one of
  the 445 was killed by the briefing alone, not the closing date. A quarter
  of the "open" corpus is already un-biddable for a new entrant on any given
  day, which is the strongest argument for scoring cards on the day they are
  published.
- 37 compulsory-briefing cards carry placeholder briefing dates
  (0001-01-01): unknowns, so per the positive-evidence rule they passed G1
  and were graded instead.
- G2 fired on all 71 extractable-grade cards (the profile holds no CIDB
  grading); for a graded profile it would fire only above the held grade.
- G3/G4/G5 fired on zero cards for this profile (Level 1 passes any stated
  pre-qualification; the profile is complete and clean).

**Stage 1 — band distribution (n=1,990):**

| Band | Cards | Share |
|---|---|---|
| Strong (≥80) | 35 | 1.8% |
| Worth review (60–79) | 196 | 9.8% |
| Marginal (40–59) | 631 | 31.7% |
| Poor (<40) | 634 | 31.9% |
| No-bid (gated) | 494 | 24.8% |

Among the 1,496 graded cards: tier A 222, tier B 1,274; median score 42.9
(p25 33.5, p75 53.5, max 91.8). The distribution is non-degenerate — every
band is populated and the top band is appropriately scarce for a
single-sector profile against a whole-market corpus. No weight adjustment
was needed against the starting values; the concentration of mass in
marginal/poor is the expected signature of a specialist profile, not a
scale defect.

**Five top-scoring cards** (tender number · institution · one-line why):

1. **91.8 · RFP 3263-2026 · State Information Technology Agency** — ICT
   category, Gauteng, 60-month term, RFP process, closes 2026-09-11.
2. **91.8 · RFP 02/2026 · South African Revenue Service** — information &
   communication, National, national dept (low quirk burden), 60-month term.
3. **91.8 · HO3/2026 · Correctional Services** — information &
   communication, Gauteng, national dept, 60-month term, closes 2026-09-14.
4. **90.6 · GPAA 06/2026 · Government Pensions Administration Agency** —
   computer programming/consultancy, Gauteng, SITA-contract channel.
5. **90.6 · ADM/2026/005 · PSIRA** — information & communication, National,
   RFQ (light process), closes 2026-09-07.

Highest tier-A card: **86.8 · E3359CXMWP · ESKOM** (information &
communication, National, 80/20 stated in pack, 60/120-month terms) — the
pack-informed factor both confirms the fit and slightly tempers it (Eskom
process burden, hand-in modes).

**Caveat:** these weights are starting values pending the full-corpus
calibration round (§9); the example demonstrates scale behaviour and gate
mechanics, not tuned rankings.

---

## 7. Grants and equity extension

The same two-stage skeleton transfers; the factor sets do not.

**Grants (416 records).** Cards carry deadline, funding amount, focus area,
eligibility text, and links — all 100% populated. But only ~31 are
South-Africa-relevant; the rest are international programmes with
jurisdiction limits, so a **jurisdiction/eligibility gate leads** (again on
positive evidence: an explicit "US-based organisations only" gates, an
unstated jurisdiction lowers confidence). Stage 1 factors: focus-area match
vs profile sectors (heaviest), deadline feasibility, amount-vs-need band.
Amount is universal here (unlike tenders), so grant scoring is *less*
data-starved than tender scoring despite the smaller corpus. Eligibility is
free text — under O-03 discipline any keyword-driven eligibility factor
needs a measured fire rate first; until then eligibility parses to gate only
on explicit jurisdiction statements.

**Equity funders (1,212 records).** No deadlines exist — these are standing
counterparties, not expiring opportunities. Scoring them on an
opportunity scale would be a category error; the right shape is
**standing-fit matching**: industry × territory × funding-type × stage
against the profile, refreshed when the profile changes, surfaced as a
ranked shortlist rather than a scored pipeline. The universal labels
(Industry, Territory, Country, Funder Type, Funding Type — 100% populated)
support exactly this.

**EEIP (8 records).** Too small to model; a hand-curated checklist per
programme outperforms any scorer at n=8.

---

## 8. Machine-readable tables

### 8.1 Factor table

| factor_id | role | trigger / source field | weight | evidence |
|---|---|---|---|---|
| G1-TIMING | gate | Closing Date label (99.8% informative); Is it compulsory? + Briefing Date and Time labels (100% / 99.8%) | — | 61.9% close ≤14d; 38.0% compulsory briefings; worked run: 445/494 no-bids; GATE-BRIEFING, KILL-LATE |
| G2-CIDB | gate | extracted required grade (71 cards, 3.6%) vs profile `cidb_grade` | — | GATE-CIDB (Fatal, statutory), DELTA-V2-05 grace, GATE-JV one-grade-below → conditional outcome |
| G3-BBBEE-PREQUAL | gate | pack pass/fail table placement only (sidecar) | — | GATE-BBBEE-PREQUAL (Fatal, buyer-specific), DELTA-V2-01; level mentions over-enumerate (§1.3) |
| G4-PROFILE | gate | profile `csd_maaa_number`, `tcs_pin`, `company_registration_no` empty | — | GATE-CSD/GATE-TCS/GATE-CIPC Universal Fatal fixtures; card-independent |
| G5-STATE-EMP | gate | profile director `in_state_service` checked | — | GATE-STATE-EMP (Fatal, Universal), KILL-SBD4 |
| F-SECTOR | graded | `### Category` + `category_rollup` vs profile sectors/capabilities | 30 | universal; rollup services 62.1%/construction 18.8%/goods 14.9%; structured (O-03-safe) |
| F-GEO | graded | Province label vs profile `operating_provinces` | 15 | universal; National 11.0% fits all footprints |
| F-PROCESS | graded | days-to-close bucket; compulsory briefing × province; hand-delivery (217 cards) where extracted | 20 | 33.9% close ≤7d; 38.0% compulsory; KILL-CHANNEL/hand-in burden |
| F-BUYER | graded | buyer type; institution vs QUIRK-* fixture list | 10 | municipality 31.7% adds GATE-RATES (arrears 1–3mo buyer-specific), single-shot cure culture; 12 buyer-quirk fixtures |
| F-ECON | graded | Tender Type label; extracted duration (41.2% of cards) | 10 | RFQ 22.4% light-process; 36mo (483) / 60mo (348) terms = recurring fit |
| F-PACK | graded (tier A only) | sidecar extracts: functionality threshold (131), preference regime (225 80/20 / 173 90/10), fee (49), submission mode (245) | 15 | SCORE-FUNC-THRESH mode 70; SCORE-SYSTEM-8020; DELTA-V2-24 fees; defined on 16.8% of corpus |

Renormalisation: score = 100 × Σ(w·f known) / Σ(w known); tier A includes
F-PACK, tier B runs on the 85-weight universal set. Bands: ≥80 strong /
60–79 review / 40–59 marginal / <40 poor / 0 no-bid.

### 8.2 Factor availability (whole corpus, n=1,990)

| factor | availability | advert-only floor | sidecar availability |
|---|---|---|---|
| province / institution / type / category / dates / briefing flags / contacts / links | 100% | 100% | 100% |
| duration | 41.2% | 34.1% | 76.3% |
| B-BBEE mention | 13.2% | 5.3% | 52.1% |
| submission mode | 12.7% | ~0.4% | 73.4% |
| preference 80/20 | 11.7% | 0.4% | 67.4% |
| preference 90/10 | 8.7% | 0.1% | 51.8% |
| functionality threshold | 6.7% | ~0.1% | 39.2% |
| CIDB grade | 3.6% | 1.9% | 12.0% |
| document fee | 2.5% | 0.0% | 14.7% |
| estimated value | 0.1% | — | — |

### 8.3 Grants/equity factor sketch

| corpus | n | gate | graded factors | shape |
|---|---|---|---|---|
| grants | 416 | jurisdiction/eligibility (explicit statements only) | focus-area match; deadline feasibility; amount band | two-stage scored, ~31 SA-relevant |
| equity | 1,212 | none (no deadlines) | industry × territory × funding type × stage | standing-fit shortlist, not a score |
| EEIP | 8 | — | — | hand-curated per programme |

---

## 9. Open items

1. **Calibration round.** The §4.2 weights are starting values. The planned
   full-corpus run over the project's eTenders corpus (163k releases,
   2021–2026) should measure: per-factor value distributions across several
   contrasting profiles (construction QSE, security firm, generalist
   supplier), band-population sensitivity to ±10-point weight shifts, and
   tier-A vs tier-B score drift on the cards where both are computable
   (score at B, then re-score at A, and measure how often the band changes —
   the honest measure of what advert-only scoring is worth).
2. **Briefing-date hygiene.** 37 compulsory-briefing cards carry placeholder
   dates; the registry should flag these for source re-verification since G1
   cannot protect against them.
3. **Functionality-vs-capability mapping.** The F-PACK term compares a
   stated threshold against capability-register coverage, which today is a
   heuristic count. SCORE-EVIDENCE (claims without prescribed evidence score
   zero) suggests the honest refinement: parse the pack's functionality
   criteria table and count criteria for which the register holds a matching
   artifact kind — per-criterion, because of the zero-on-any-criterion
   auto-DQ pattern (DELTA-V2-04).
4. **Keyword factors stay quarantined** until O-03's fire-rate measurement
   lands. This report's model uses none.
