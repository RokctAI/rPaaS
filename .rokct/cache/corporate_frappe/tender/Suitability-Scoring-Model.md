# Suitability Scoring — Merged Model Decision Record

Date: 2026-08-23. Status: **decided** — this is the model the engine in
`tender/frappe/src/control/compliance/suitability.py` implements
(opportunities `FEEDBACK.md` §1.2, corporate PR #51 rework).

Two independent research passes ran over the same live corpus (1,990
published tender cards, 2026-08-23) on the same day:

1. **The corpus research pass** (engine-aware): ran the original strawman
   engine over all 1,990 cards, proved its band degeneracy, found the dead
   functionality extractor, the missing briefing gate, and built a
   two-stage prototype validated over multiple profiles.
2. **The PR-blind outside research** (`tender/Suitability-Scoring-Research.md`,
   PR #52): never saw the engine or the `advanced_enrichment` dataset;
   measured the corpus independently and proposed a two-stage scorer with
   confidence tiers.

The two passes **independently converged** on the architecture (hard gates
then graded fit, never blended), the headline gate (compulsory briefing
already held), the semantics (worth-bidding **triage**, never win
probability — under PPR 2022 price takes 80/90 of 100 points and neither
the bidder's nor competitors' price is knowable from an advert), the
renormalise-over-known-factors rule, and near-identical weights for the
shared factors. That convergence is the evidence base for this model. The
shipped model is the corpus pass's engine spine plus four specific pieces
adopted from the outside report.

## The model

### Stage 1 — hard gates (unweighted; fire only on positive evidence)

Fail ⇒ band `no_bid`, **no numeric score** (a number would imply
comparability that does not exist), **all** firing reasons returned.
Unknown never fails a gate — it lowers confidence or becomes a manual
check.

| Gate | Trigger | Corpus impact (2026-08-23) |
|---|---|---|
| `GATE-CLOSED` | closing date (real, non-placeholder) already passed | 2 cards |
| `GATE-BRIEFING-HELD` | `is_it_compulsory` = Yes AND `briefing_date_and_time` is a REAL past date. Placeholder dates (`0001-01-01`) are UNKNOWN → data-hygiene flag + manual check, never a gate | **445 cards (22.4%)** — the single biggest exclusion; 37 further placeholder-date cards flagged |
| `GATE-CIDB` | category-triggered (statutory) via the GATE-CIDB fixture rule, OR a quoted grading requirement. Ungraded profile + construction category ⇒ gate. Quoted grade: exact-class, grade ≥ required; **one grade below = JV-conditional pass** (manual check, never clean); graded profile vs unquoted grade = provisional pass + manual check | 235 cards for an ungraded profile (union of 214 category-triggered + quoted-requirement cards) |
| `GATE-BBBEE-PREQUAL` | UNION of the buyer-fixture trigger (`institution_matches`: Eskom/TASEZ/…) and quoted pack/enrichment pre-qualification evidence (line must carry BOTH a B-BBEE token and a pre-qualification token). B-BBEE level *mentions* (points tables) NEVER gate — the over-enumeration trap | 178 buyer-triggered cards |
| `PROFILE-INCOMPLETE` | CSD MAAA / TCS PIN / CIPC missing on the profile. Profile-side: reported ONCE as `profile_completeness`, never per card — the remedy is fixing the profile | excludes nothing for a compliant business, everything for a non-registered one |

### Stage 2 — fit score 0–100, renormalised over KNOWN factors

`score = 100 × Σ(wᵢ·fᵢ) / Σ(wᵢ)` over factors with a known value. An
unknown factor redistributes its weight — it is never silently scored.

| Factor | Weight | Source | Evidence |
|---|---|---|---|
| `sector_fit` | 30 | continuous token-overlap: declared operating sectors vs category/title/focus | 100% coverage, widest real variance; the strawman's 4-step ladder gave only 7 distinct total scores over 1,990 cards |
| `readiness` | 20 | the 8 parseable demand types on the enrichment demand lines (tax / CSD / B-BBEE / rates / COIDA / PSIRA / NHBRC / experience) vs profile evidence — the officer's gap list | 372 enriched entries; neutral (unknown) on the 81.3% unenriched |
| `process_feasibility` | 15 | days-to-close, attendable compulsory briefing (+ `briefing_travel_radius`), effort gates (vetting / integrity pact / insurance) | 61.9% of cards close ≤ 14 days, median 11 |
| `geography_fit` | 15 | declared provinces vs card province; national matches all | 100% coverage, 11% national |
| `buyer_burden` | 10 | buyer type (municipal rates/cure culture) + applicable QUIRK fixture rules | municipality 31.7% of corpus; 12 QUIRK fixtures |
| `engagement_economics` | 10 | tender type (RFQ light / open tender heavy) + stated contract duration | tender type 100% present; duration stated on 41.2% |
| `pack_informed` | 10 | FIXED functionality-threshold extractor, preference system, document fees | defined only where pack/enrichment text exists; drives the confidence split |

**Bands:** strong ≥ 80 · review 60–79 · marginal 40–59 · poor < 40 ·
`no_bid` (gated) · `unscored` (nothing known and nothing gated — edge).

**Confidence** is always displayed: `pack_verified` (enrichment/pack text
fed the score) or `advert_only`. On advert-only cards the payload carries
a triage note: the score's first job is **pack-fetch prioritisation** —
fetch packs for promising cards, then re-score at `pack_verified`
(adopted wholesale from #52; the 18.7% enrichment floor is a fetch
backlog, not a law of nature).

**Functionality extractor fix.** The original pattern demanded a literal
`%` and hit **0 of 372** live enrichment entries (the dimension
dead-defaulted to full points). The fixed whitelist adds the quoted
no-percent forms the corpus actually uses — "minimum functionality
threshold of 80", "ACCEPTABLE MINIMUM SCORE 60", "Minimum Required Score
for functionality is: 60" — recovering 20/372 entries (values 60–80);
the `%` form is kept. Still quoted-or-nothing: a bare number on a
non-threshold line is never trusted, and no-percent values below the
observed floor (30) are rejected as raw points on non-100 scales.

**Manual-check noise.** A median of 29 Fatal rules applies per card, ~25
of them universal process-discipline KILLs that are never
profile-checkable. They collapse into ONE grouped `PROCESS-DISCIPLINE`
entry; only card-specific conditional rules (buyer quirks, subject
gates) keep individual entries.

### Market context (additive, 2026-08-23 — the awards-data integration)

Every tender payload carries a `market_context` block resolved from small
derived reference tables (`tender/frappe/src/control/compliance/data/market_context.json`,
regenerated deterministically by `tender/frappe/tools/build_market_context.py`
from the committed awards dataset `tender/awards-dataset/awards_only.csv` —
32,589 published award rows, snapshot 2026-08-20; analysis in
`tender/Award-Outcomes-Research.md`):

- **buyer stats** — normalized-name match (exact → suffix-stripped /
  parenthetical-acronym alias → corpus-wide default) over the top 200
  buyers by award count plus the three documented zero-publisher
  municipalities: award count, publication behaviour (curated §2
  coverage figures; `high`/`medium`/`low`/`zero`/`unknown`), entrant
  share ("small entrants win X% of published awards at this buyer"),
  at-buyer incumbency concentration;
- **typical winning-price band** — median + IQR + N + the table level it
  came from, down a fixed fallback chain: buyer (N ≥ 30) →
  category × province cell (N ≥ 30 only, 30 cells) → category → province
  → **absent** (never a guess). Flag-cleaned amounts only
  (zero / lt_R100 / gt_R10bn dropped), medians/IQR only — the corpus
  mean is 23× the median;
- **honesty caveats**, machine-readable: successes-only feed (no win
  probability — the context prices the market, it never predicts
  winning), 19.95% publication coverage with severe per-buyer bias,
  contract-total amount semantics.

`buyer_burden` additionally consumes the real per-buyer stats where the
buyer resolves (additive refinement on top of the QUIRK/municipal fixture
base, which always stands): low/zero publication −0.1 (outcome
visibility), ≥ 50% at-buyer incumbency −0.1 (SANRAL-style lock-in),
≥ 60% entrant share +0.1 (entry is normal here). Unmatched buyers are
untouched. The market context never moves gates and adds no new payload
semantics beyond the one new key.

### Extensions

- **Grants** — jurisdiction gate FIRST (explicit, whitelisted foreign
  fences only; unstated jurisdiction = manual check, never a gate), then
  fit (sector + deadline feasibility, renormalised).
- **Equity funders** — no deadlines, so no opportunity score: standing-fit
  shortlist semantics (`semantics: standing_fit_shortlist`), scored on
  sector × territory only.
- **EEIP** (n=8) — hand-curated per programme; no scorer.

## What was adopted from which research pass

**From the corpus research pass (the implementation spine):**

1. The degeneracy proof and its cure: eligibility as stage-1 gates, not 40
   weighted points (the strawman scored a compliant services SMME "strong"
   on 89% of the corpus with 7 distinct values).
2. The functionality-extractor fix (0/372 → 20 live hits).
3. The `advanced_enrichment` demand-line dataset and the **readiness**
   factor built on it (#52 never saw this data source).
4. Continuous sector token-overlap; days_to_close in the payload; grouped
   universal manual checks; no numeric score for gated cards;
   multi-profile validation discipline.
5. The **wide statutory CIDB gate** (see deviations below).
6. B-BBEE prequal buyer-fixture trigger (covers advert-only cards where
   #52's pack-table trigger is blind).

**From the outside research (#52) — the four adopted pieces:**

1. **The placeholder-briefing-date rule**: 37 of the 482 originally
   counted "briefing already held" cards carry `0001-01-01` placeholders
   — unknowns under positive-evidence handling, so the gate count is
   **445, not 482**, and placeholders surface as data-hygiene flags.
2. **The advert-only triage → fetch → re-score pipeline**: a tier-B score
   ranks which packs to fetch; re-score at full confidence after
   collection. This dissolved the open "suppress or flag?" decision.
3. **Buyer-burden and engagement-economics factors** (buyer type + QUIRK
   fixtures; RFQ-vs-open process weight; multi-year terms as
   recurring-revenue fit).
4. **The B-BBEE over-enumeration warning** (level mentions are points
   tables, never eligibility bars), plus: profile completeness as a
   present-once profile-side gate, the 5-band scale (≥80/60/40), the
   `briefing_travel_radius` profile field, and the grants/equity/EEIP
   rulings.

## Explicit deviations from #52's recommendations

1. **CIDB gate breadth — category-triggered, not extracted-grade-only.**
   #52 gates only where a grade was extracted (71 cards, 3.6%). This
   model gates every construction-category card for an ungraded profile
   (214+ cards, 10.8%). Evidence: CIDB registration is **statutory** for
   public construction works regardless of whether the advert states the
   grade — both reports cite GATE-CIDB as statutory — and the category
   rollup is positive structured evidence of that requirement, not a
   keyword guess. #52's narrow gate would grade ~144 cards a no-CIDB
   profile can never win. Where a grade IS quoted, #52's exact-class
   comparison and JV-conditional softening are used unchanged; a graded
   profile against an unquoted grade passes provisionally with a manual
   check.
2. **The readiness factor exists.** #52 has no
   demanded-returnables-vs-profile factor because it missed the
   `advanced_enrichment` dataset (372 pre-parsed entries — more coverage
   than the 334 OCR sidecars it did use). Readiness is the R8k/month
   tender officer's actual gap-list job and carries 20 weight, neutral
   when unenriched.
3. Cosmetic: factor weights are the merged sketch
   (30/20/15/15/10/10/10 vs #52's 30/15/20/10/10/15) — sector and
   geography identical, process/pack redistributed to fund readiness.

## Validation (full published corpus, 1,990 cards, today = 2026-08-23)

Run with the real fixture rules and real enrichment
(reproducible: stub frappe, load the engine by path, iterate
`published/api/tenders.json`):

| Profile | Bands (strong/review/marginal/poor/no_bid) | Distinct scores | Gate causes |
|---|---|---|---|
| P1 services SMME (7 sectors, Gauteng, no CIDB) | 231 / 705 / 400 / 71 / 583 | 63 (min 32, med 64, max 97) | briefing 445 · CIDB 235 · closed 2 |
| P2 construction SMME (2GB, Limpopo+Gauteng) | 45 / 505 / 854 / 126 / 460 | 61 (min 32, med 56, max 96) | briefing 445 · CIDB 27 · closed 2 |
| P3 empty profile | no_bid 1,990 | — | PROFILE-INCOMPLETE 1,990 (+ briefing 445, CIDB 235, B-BBEE prequal 178, closed 2 all reported) |

All five bands populated for both real profiles, 60+ distinct score
values (strawman: 7), the briefing gate lands exactly on #52's corrected
445, and 37 placeholder-date cards were flagged (never gated) on every
run. Confidence split: 372 `pack_verified` / 1,618 `advert_only`.

Weights remain argued-not-fitted — the corpus holds no award-outcome
data. The calibration path (record real bid outcomes / scrape award
notices, measure tier-B→tier-A band drift) is future work, per both
reports.
