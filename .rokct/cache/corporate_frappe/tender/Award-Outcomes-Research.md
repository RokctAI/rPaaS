# Award Outcomes — What 32,589 Published Awards Say About Winning SA Tenders

Release date: 2026-08-23. Audience: **the agent building the TenderAssist SDK**
(`tender/frappe`) and the opportunities-registry workstream, as the
award-outcomes companion to `Suitability-Scoring-Research.md`. Source: an
award-centric extraction over the public South African eTenders OCDS release
corpus (snapshot 2026-08-20). The dataset and the scripts that produce it live
in the project workspace dataset directory `etenders-awards/` — bulk
third-party data, deliberately **not** committed to this repository. Every
number in this report is taken from that directory's `coverage.json`,
`analysis.json`, and `analysis_report.txt`, or recomputed from
`awards_extract.jsonl` / `awards_only.csv` with the same deterministic
definitions; nothing is estimated.

**One-paragraph summary.** Of 163,321 releases in the corpus, 32,589 (19.95%)
carry an award block — and that 19.95% is not a random sample: publication
varies from 75.7% of releases at SARS to exactly 0% at the City of Tshwane, so
every statistic below describes the *reported-award* subset, not SA
procurement at large. Within the usable-amount benchmark population
(N=22,311), the median winning value is R13.89m with a mean 23× larger —
means are unusable, medians of tight comparable sets are the only honest
price benchmark. Concentration is far lower than the incumbent-lock-out
folklore suggests: 68.79% of the 17,961 distinct suppliers win exactly once,
suppliers with at most two lifetime wins take 55.54% of *all* awards, and only
41 suppliers exceed 20 wins (4.04% of awards). Entrant win-share is highest in
Mpumalanga (71.0%), at provincial departments (59.2%), and below R10m. What
the feed structurally cannot support: award dates (so no cycle-time analysis),
tenderer counts (so no competition intensity), and cancelled/unsuccessful
outcomes (so no win probability). The dataset's job is market-context
calibration for the fit score — typical deal size, entrant-friendliness, and
buyer transparency, joinable per buyer — not outcome prediction.

---

## 1. Dataset and method

**Provenance.** The corpus is the public eTenders OCDS release feed
(`ocds-api.etenders.gov.za`), snapshotted **2026-08-20** by sequential
tender-ID enumeration over `ocds-9t57fa-1 .. 166500`, yielding **163,321
releases**. 32 IDs returned persistent HTTP 500 at corpus build time
(including `ocds-9t57fa-166057`); they are logged in `failed_ids.txt` and
skipped, not silently discarded. The feed serves *compiled releases*: the same
`ocid` accumulates award blocks over time as procurement progresses, so a
snapshot is a point-in-time picture — recently published tenders have
mechanically fewer awards (quantified in §2).

**Pipeline.** Two scripts, no manual steps: `extract_awards.py` (~13 s) walks
the corpus shards in sorted order and emits the dataset; `coverage_report.py`
(~1 s) produces `coverage.json`. A third, `analyze_awards.py`, produces
`analysis.json` / `analysis_report.txt` with built-in sanity spot-checks
(five independently recomputed cells, all matching). All three are
deterministic — sorted shard order, single pass, no randomness — and reruns
produce byte-identical output.

**Dataset shape** (in the project workspace dataset directory
`etenders-awards/`):

| file | rows | content |
|---|---|---|
| `awards_extract.jsonl` | 163,321 (1 per release) | every release, awarded or not; `ocid`/`release_id` copied byte-exact from source (verified set-identical to the corpus ID list), preserving the join key for the planned calibration join against registry cards |
| `awards_only.csv` | 32,589 (1 per award) | flat per-award table with `amount_flag` quality flags (`zero`, `lt_R100`, `gt_R10bn`) — suspicious rows flagged, never dropped |
| `coverage.json`, `analysis.json` | — | machine-readable coverage and analysis outputs |
| `failed_ids.txt` | 32 IDs | the persistent-500 IDs, kept for audit |

`province` comes from `tender.province`, present on every release in this
feed; the OCDS-standard address alternatives do not exist in this API's
output.

## 2. Coverage — the honesty layer

Read this section before any number in §3–§6. Every downstream statistic
describes the subset of procurement whose awards were actually published to
this feed.

**Headline coverage.** 163,321 releases; **32,589 (19.95%) carry an award
block**. Of awarded releases, 99.98% name at least one supplier, but only
**72.01% carry a non-zero award amount**, and **0.00% carry an award date** —
the `award.date` field is structurally absent from every award in this feed,
as are `numberOfTenderers` (tender- and award-level) and award
`contractPeriod`. Consequently the award-vs-closing lag distribution — how
long adjudication takes — **cannot be computed from this corpus at all**, and
neither can competition intensity.

**Recency artifact.** Because releases gain awards over time, the snapshot
date creates a mechanical coverage drop-off at the recent end: steady-state
award coverage is ~21–24% (shards 2022-H2 through 2025-H2; ID deciles 4–8),
falling to 18.85% in ID decile 9, 12.53% for the 2026-H1 shard, and **3.27%
for 2026-H2** — most of those tenders simply had not been awarded (or their
awards not yet published) by 2026-08-20. Low coverage on recent tenders is a
snapshot artifact, not a publication choice.

**Buyer publication bias — severe and non-random.** Award publication is a
per-buyer behaviour. Among the top-30 buyers by release count, coverage spans
the full range:

- High publishers: **SARS 75.74%**, **Justice & Constitutional Development
  71.96%**, The Mvula Trust 63.05%, CSIR 51.97%, SANRAL 40.20%.
- Low publishers: **ESKOM 9.87%** (12,879 releases, the corpus's largest
  buyer), Independent Development Trust 8.74%, Airports Company 6.56%,
  Johannesburg Water 4.08%, Rand Water 4.06%, Agricultural Research Council
  2.22%, Air Traffic and Navigation Services 0.95%.
- Zero publishers: **City of Tshwane (1,254 releases, 0 awards), Mnquma Local
  Municipality (978, 0), City Council of Johannesburg (909, 0)**.

The zero rate at large municipalities is consistent with municipal practice of
publishing award notices on their own websites rather than into the eTenders
OCDS feed — under MFMA supply-chain-management practice the municipal website
is the customary publication channel for award notices — so absence from this
feed is a channel gap, not evidence that these buyers award nothing.
Category-level coverage also varies: works 26.05%, (blank) 21.27%, goods
18.18%, services 18.13%.

**Data-quality inventory** (counted in `coverage.json`, flagged in the CSV,
never dropped):

| issue | count | share of 32,589 awards |
|---|---|---|
| zero award amount | 9,123 | 28.0% |
| non-zero amount < R100 | 825 | 2.5% |
| amount > R10bn (max R1.80 trillion, `ocds-9t57fa-30487` — clearly erroneous magnitude) | 330 | 1.0% |
| placeholder supplier names ("None", single characters) | 12 | 0.04% |
| currency | 32,589 ZAR | 100% |
| award status | 32,589 "active" | 100% — cancelled/unsuccessful awards are never published to this feed |
| awards per awarded release | exactly 1, single supplier | 100% |
| duplicate (ocid, supplier, amount) rows | 0 | — |

The 100%-"active" fact matters as much as the 19.95% coverage: the feed
records only successes, so win/loss base rates are unobservable.

## 3. Winning-price benchmarks

**Benchmark population.** N = **22,311** award rows with a non-zero, unflagged
amount (32,589 minus 9,123 zeros, 825 sub-R100, 330 over-R10bn) — 68.5% of
award rows.

**Overall distribution.** Median **R13,885,686 (R13.89m)**; IQR **R1.74m –
R150.00m**; mean **R317.20m** — the mean is **23× the median**, dragged by a
long tail of mega-awards (max in benchmark R9.98bn). This is why means are
banned from every downstream use in this workstream: any average-based
benchmark will overstate typical deal size by an order of magnitude. Use
medians of tight comparable sets, always.

Decile table (log-scale spread across nearly five orders of magnitude):

| percentile | p10 | p20 | p30 | p40 | p50 | p60 | p70 | p80 | p90 |
|---|---|---|---|---|---|---|---|---|---|
| ZAR | 234,000 | 1,091,505 | 2,631,248 | 5,962,250 | 13,885,686 | 32,252,753 | 86,248,800 | 250,000,000 | 711,731,542 |

**By category** (medians ordered): **works R45.06m** (N=4,323) > **services
R14.40m** (N=9,266) > **(blank) R10.95m** (N=4,873) > **goods R5.00m**
(N=3,849).

**By province** (medians): North West **R49.94m** (N=530), Free State R32.12m
(483), Mpumalanga R22.87m (810), National R21.26m (2,989), Limpopo R18.42m
(1,254), Eastern Cape R18.40m (2,763), KwaZulu-Natal R14.20m (3,333), Western
Cape R9.74m (4,448), Gauteng R9.73m (5,014), Northern Cape **R6.51m** (687).
Note the inversion: the small-N provinces have the biggest medians — their
published awards skew toward large works/infrastructure, another reason to
benchmark within category × province cells (40 cells with N≥30 are in
`analysis.json`), not against province alone.

**By buyer, the spread is extreme.** Among the top-30 buyers by benchmark
award count, medians span **~196×**: Justice & Constitutional Development
**R1.40m** (N=1,005) versus Eastern Cape Roads and Public Works **R273.07m**
(N=177), with SARS at R2.74m, ESKOM at R121.05m, City of Cape Town at
R200.00m, The Mvula Trust at R208.83m. "Typical award size" is meaningless
without naming the buyer. Full table in §9.

**Semantics caveat.** These amounts are plausibly *total contract or framework
values* (multi-year, multi-line), not unit line prices — the R150m Q3 and the
R711.7m p90 are hard to read any other way. Treat every benchmark here as
contract-total semantics.

## 4. Supplier concentration

**Population.** All 32,589 award rows (zero-value included — win *counts*
measure frequency, not value). Raw supplier strings: 20,620; after
conservative normalisation (trim, casefold, whitespace collapse, trailing
punctuation — **no fuzzy merging**): **17,961 distinct suppliers**. The
supplier-id cross-check shows this under-merges: id `0` is a placeholder
(12,250 rows, treated as missing); among the 20,339 rows with a real id,
**36.85% sit on ids that map to multiple normalised names** — mostly
casing/bracket/typo variants of the same firm. So distinct-supplier counts are
overcounts and every entrant share below is an **upper bound**.

**Win-count distribution** — the central finding:

| lifetime wins | suppliers | % of suppliers | awards | % of all awards |
|---|---|---|---|---|
| 1 | 12,355 | 68.79% | 12,355 | 37.91% |
| 2 | 2,873 | 16.00% | 5,746 | 17.63% |
| 3–5 | 2,006 | 11.17% | 7,204 | 22.11% |
| 6–20 | 686 | 3.82% | 5,966 | 18.31% |
| >20 | 41 | 0.23% | 1,318 | 4.04% |

**68.79% of suppliers win exactly once.** Suppliers with at most two lifetime
wins (15,228 of 17,961) hold 18,101 awards = **55.54% of all published
awards**. Only 41 suppliers exceed 20 wins, and together they hold just 4.04%
of awards. In the published record, South African public procurement is a
long-tail market, not an oligopoly.

**Incumbency varies enormously by buyer.** Share of a buyer's awards going to
suppliers with ≥3 wins *at that buyer*: **SANRAL 61.56%** and **Ingquza Hill
Local Municipality 59.62%** at the locked-in end, versus **Transnet National
Ports Authority 6.04%** and **SASSA 7.14%** at the open end. Even the most
concentrated buyers have no dominant supplier: the highest top-1 share among
top-30 buyers is 10.44% (a stationery vendor at KZN Economic Development);
Justice's top supplier at 3.07% is **Government Printing Works** — a
government entity winning a government tender. Another oddity: Midvaal Local
Municipality's "top supplier" (13 awards) is the literal string
**"non-award"** — award blocks used to record non-awards, a reminder that
supplier strings need cleaning before any join.

## 5. Entrant correlates

"Entrant" = supplier with ≤2 lifetime wins corpus-wide. These are
deterministic cross-tabs, not fitted models, and carry a stated confound: a
supplier winning a huge award is by construction likelier to be a repeat
player at big buyers, so the value-band and buyer-type contrasts partly
restate supplier size rather than an independent entrant effect.

- **By province:** Mpumalanga **71.01%**, Free State 65.98%, Limpopo 65.88%,
  North West 65.87% … Gauteng 55.05%, National 51.49%, Western Cape
  **46.93%**. The provinces with the fewest published awards are the most
  entrant-friendly.
- **By value band** (benchmark rows), monotone: <R10k **67.72%** → R10k–100k
  61.18% → R100k–1M 60.71% → R1M–10M 59.02% → >R10M **54.07%**.
- **By buyer type** (keyword heuristic): provincial departments **59.24%**,
  other national agencies/entities 56.68%, national departments 56.10%, SOEs
  54.50%, municipalities 53.31%, health/education **49.63%**.
- Zero-value awards skew slightly *away* from entrants (51.91% vs 56.95% on
  non-zero rows).

Even at the least entrant-friendly cut, entrants take just under half the
awards — entry is normal everywhere in the published record.

## 6. Worked micro-example — the municipal-website query

To test what a niche comparable set looks like in practice, a
case-insensitive title query for website work (`website` / `web site` /
standalone `web` and variants) was run over all 163,321 titles. It returns 25
raw matches, **24 genuine website tenders** after dropping one product tender
(a "Fortiweb" web-application-firewall purchase). Two warnings and two
lessons:

- **Title matching undercounts.** Most eTenders titles are bare reference
  codes ("SCM72WEBSITEREDESIGN2026", "T10/25 Web"); the true count of website
  tenders is higher than 24. Any comparable-set builder needs description
  text, not just titles.
- **Only 2 of 24 are municipal** — both Xhariep District Municipality (Free
  State), both unawarded, the second an explicit re-advertisement
  ("XDM-Website 23/24" → "XDM-WEBSITE 23/24-2"). Re-advertisement recurs in
  this set (SAQA's web redesign, PPECB's hosting, the Performing Arts Council
  redesign advertised in 2021 and again in 2026): **a re-advert is a visible
  signal of a weak or failed field — an entry opportunity.**
- **6 of the 24 carry award blocks**, all at national bodies, SOEs, or
  provincial agencies — none municipal. One award is zero-value; the five
  priced awards are R320,936 (SACAA website support), R576,000 (Gauteng
  Enterprise Propeller hosting), R1,324,800 (Railway Safety Regulator
  intranet/website), R2,866,380 (Trans-Caledon Tunnel Authority), R3,253,635
  (Competition Tribunal redevelopment) — **median R1.32m, range
  R321k–R3.25m**, a coherent price band two orders of magnitude below the
  corpus median.
- **No repeat supplier**: six awards, six distinct winners. Even in a niche,
  no incumbent owns the space.

Lesson: niche comparable sets are small but real, and they price far more
honestly than corpus-level statistics.

## 7. Practical guidance for a small SA business

Findings-grounded guidance, in the order a bidder would use it:

1. **The incumbent-lock-out fear is overstated in the published record.**
   55.54% of all published awards go to suppliers with at most two lifetime
   wins; 37.91% go to one-time winners. Entry is the norm, and it is most
   normal in Mpumalanga (71.0% entrant share), Free State, North West and
   Limpopo (all ~66%), at provincial departments (59.2%) and municipalities,
   and below R10m (entrant share rises monotonically as value falls). Bid
   where entrants actually win. The exceptions are visible and nameable:
   SANRAL-style ecosystems (61.6% of awards to at-buyer incumbents) reward
   getting onto panels before chasing individual tenders.
2. **Price from medians of your specific comparable set** — category ×
   province, or better a niche title/description query like the website
   example — never from means (23× inflated) and never from corpus-wide
   figures (buyer medians span ~196×). Treat published amounts as
   contract-total semantics, and expect ~28% of your comparables to carry
   zero amounts.
3. **Prefer buyers who publish awards.** At SARS (75.7% publication), Justice
   (72.0%), The Mvula Trust (63.1%), CSIR (52.0%) or SANRAL (40.2%) you can
   see the market you are entering — typical sizes, who wins, how often. At
   zero-publication buyers (Tshwane, Johannesburg, Mnquma) you fly blind, and
   absence of award data means nothing about your chances — their notices
   most likely live on their own municipal websites, outside this feed.
4. **Know what award data cannot tell you.** No award dates → no cycle-time
   estimate. No tenderer counts → no competition intensity. 19.95% coverage
   plus only-successes publication → no win probability. This dataset
   calibrates *market context* — typical deal size, entrant-friendliness,
   buyer transparency — as inputs to the suitability fit score, not outcome
   prediction.
5. **For the calibration join**, the three per-buyer features this dataset
   supports are: **median award size** (benchmark rows), **entrant share**,
   and **publication rate** — keyed by buyer name, and by `ocid` where
   registry cards overlap the corpus. The biggest coverage blind spot —
   municipal awards, with municipalities roughly 32% of the live tender-card
   corpus — is fillable by a future harvest of municipal-website award-notice
   pages, which would slot into this same dataset keyed by buyer name.

## 8. Renewal radar: predicting when contracts return

Fixed-term contracts come back. A client-suggested line of analysis: when a
tender states its contract duration, the expected re-advertisement date is
simply **closing date + stated duration**, turning the historical corpus
into a forward calendar of tenders that have not been advertised yet. This
section builds that radar and then stress-tests it against contracts whose
predicted return date has already passed.

**Mechanic.** For every release with a parseable `tenderPeriod.endDate`, a
deterministic regex pass over the tender title and description extracts a
stated contract duration (digits and number-words, 6–120 months accepted;
noise guards drop "X years' experience", warranty periods and "within N
months" delivery phrases). Expected return = closing date + duration. Two
scripts, no manual steps: `renewal_radar.py` (extraction + pipeline, with
outputs `radar_output.txt`) and `validate_renewals.py` (the honesty check
below, `validation_output.txt`); all four files live in the project
workspace dataset directory `etenders-awards/` alongside the
award-extraction scripts — not committed to this repository.

**Coverage.** 163,295 of 163,321 releases (99.98%) have a parseable closing
date; 52,353 (32.06%) yield an extractable duration; **52,344 (32.0%) have
both** and form the radar population. The duration distribution is heavily
modal: **36 months = 30,373 hits (58.0%)**, then 60 months (8,034), 12
months (4,937) and 24 months (4,688) — the familiar 1/2/3/5-year public
contracting rhythm. For most of the other 68% the duration is stated only
inside the PDF tender pack, not in the OCDS title/description text, so pack
parsing is the identified route to materially higher coverage.

**The 12-month pipeline.** 9,941 predicted returns fall in the next 12
months (2026-09 → 2027-08). Where they sit:

| cut | top entries (count) |
|---|---|
| buyer type | other 2,952 · municipality 2,944 · SOE 1,966 · public entity 1,569 · department 417 · education 93 |
| category | Services: Professional 1,398 · Services: General 1,117 · Other service activities 726 · Supplies: General 702 · Services: Functional (incl. cleaning/security) 553 · Information and communication 346 |
| buyer | ESKOM 937 · Transnet SOC Ltd 291 · Public Works 260 · PRASA 193 · eThekwini Metropolitan Municipality 187 · City of Tshwane 172 |

Note the complement to §2: the buyers heading the renewal pipeline include
ESKOM (9.87% award publication) and City of Tshwane (0.00%) — the radar
reads their demand rhythm from tender adverts even where their award
outcomes are invisible.

**Honesty check — 12 already-due cases, manually adjudicated.** A
deterministic sample of 12 duration-bearing releases (24–60-month terms,
spread across buyer types, descriptive-enough titles) whose predicted
return had already passed was searched for a successor advert from the same
buyer by title/description token similarity, then read by hand. The
automated matcher flagged 5 of 12; manual adjudication keeps only **2
unambiguous same-service renewals** — but both returned essentially on
schedule: Mnquma Local Municipality (24-month term, predicted return
2025-06-09, successor closed 2025-05-14, **−0.9 months**) and Transnet
National Ports Authority (60-month term, predicted 2026-07-06, successor
closed 2026-09-10, **+2.2 months**) — plus 1–2 borderline near-schedule
cases (a Transnet RFP at +1.5 months sat just below the text-match
threshold). The binding constraint is not renewal behaviour, it is
*matching*: most SA tender titles are opaque reference codes ("MWP1569CX",
"5/2/1/2020-21"), so text-based successor matching has low recall and
"as and when required" panel boilerplate creates false-positive traps.
Where a successor was verifiable at all, timing was close to schedule.

The caveats, as a list:

1. **Duration text noise** — regex extraction from free text mis-reads some
   durations despite the noise guards.
2. **Extensions delay returns** — buyers routinely extend expiring
   contracts rather than re-advertise on time.
3. **Early re-advertisement happens** — cancellations, budget cycles and
   scope changes bring tenders back before term.
4. **Panels don't renew on schedule** — "as and when required" panel
   appointments have no single return date at all.
5. **Corpus maturity** — the corpus is only dense from ~2022, so few long
   (48–120-month) contracts have observably matured; the verifiable
   validation base is small by construction.

**Practical framing.** Use the radar as a **lead calendar, not a
certainty**: a predicted window says "prepare now" — get capability,
registrations and compliance documents ready *before* the expected
re-advertisement — and match the successor when it appears by **buyer +
category**, not title text. The planned join against active registry cards
sharpens this further: a radar row whose buyer × category cell also shows
live tender cards is a confirmed demand rhythm, not a guess.

## 9. Machine-readable tables

### 9.1 Benchmark distributions (ZAR, benchmark population N=22,311)

| group | n | median | q1 | q3 |
|---|---|---|---|---|
| overall | 22311 | 13885686 | 1737133 | 150000000 |
| category: works | 4323 | 45057566 | 5036579 | 363806226 |
| category: services | 9266 | 14400000 | 1656002 | 165305197 |
| category: (blank) | 4873 | 10946850 | 1534560 | 88720290 |
| category: goods | 3849 | 4997500 | 840000 | 46508645 |
| province: North West | 530 | 49939320 | 6283432 | 348079062 |
| province: Free State | 483 | 32117382 | 2817682 | 273894483 |
| province: Mpumalanga | 810 | 22865726 | 1566804 | 325726689 |
| province: National | 2989 | 21259920 | 2761529 | 179580000 |
| province: Limpopo | 1254 | 18420781 | 2123590 | 236033172 |
| province: Eastern Cape | 2763 | 18402530 | 2306798 | 231603859 |
| province: KwaZulu-Natal | 3333 | 14200000 | 2000000 | 157768894 |
| province: Western Cape | 4448 | 9743690 | 1189885 | 100000000 |
| province: Gauteng | 5014 | 9730250 | 1381716 | 88710849 |
| province: Northern Cape | 687 | 6506536 | 1068893 | 84182033 |

Deciles (overall): p10 234000 · p20 1091505 · p30 2631248 · p40 5962250 ·
p50 13885686 · p60 32252753 · p70 86248800 · p80 250000000 · p90 711731542.
The 40 category × province cells with N≥30 are in `analysis.json`
(`s1_price_benchmarks_ZAR.by_category_x_province_n_ge_30`).

### 9.2 Win-count buckets (all 32,589 award rows, 17,961 normalised suppliers)

| wins | suppliers | supplier_share_pct | awards | award_share_pct |
|---|---|---|---|---|
| 1 | 12355 | 68.79 | 12355 | 37.91 |
| 2 | 2873 | 16.00 | 5746 | 17.63 |
| 3-5 | 2006 | 11.17 | 7204 | 22.11 |
| 6-20 | 686 | 3.82 | 5966 | 18.31 |
| >20 | 41 | 0.23 | 1318 | 4.04 |

### 9.3 Top-30 buyers by award count — the per-buyer calibration table

Columns: publication % = awarded/releases for that buyer; median = benchmark
median award (non-zero unflagged rows, n in brackets); at-buyer entrant share
= 100 − % of awards to suppliers with ≥3 wins at that buyer (from
`analysis.json`; upper bound, see §4); ≥3-win incumbency = % of awards to
suppliers with ≥3 wins at that buyer. Publication % and medians for buyers
outside `analysis.json`'s top-30-by-releases coverage list were recomputed
from the dataset with identical definitions (all overlapping cells match
`analysis.json` exactly). Medians are rounded to the nearest rand.

| buyer | releases | awards | publication_pct | median_award_ZAR (n) | at_buyer_entrant_share_pct | ge3_win_incumbency_pct |
|---|---|---|---|---|---|---|
| Justice & Constitutional Development | 2040 | 1468 | 71.96 | 1395640 (1005) | 69.35 | 30.65 |
| Passenger Rail Agency of South Africa | 4807 | 1285 | 26.73 | 5000000 (796) | 73.23 | 26.77 |
| ESKOM | 12879 | 1271 | 9.87 | 121047075 (772) | 75.37 | 24.63 |
| Transnet SOC Ltd | 4352 | 1008 | 23.16 | 40477937 (655) | 82.84 | 17.16 |
| South African Revenue Service | 1257 | 952 | 75.74 | 2738570 (683) | 65.44 | 34.56 |
| Public Works | 3348 | 854 | 25.51 | 14605471 (577) | 80.21 | 19.79 |
| THE MVULA TRUST | 1207 | 761 | 63.05 | 208829880 (547) | 80.42 | 19.58 |
| SANRAL | 1495 | 601 | 40.20 | 137956300 (295) | 38.44 | 61.56 |
| City of Cape Town | 1741 | 542 | 31.13 | 200000000 (251) | 74.91 | 25.09 |
| South African Local Government Association | 723 | 542 | 74.97 | 2000000 (397) | 68.08 | 31.92 |
| Stellenbosch Municipality | 679 | 493 | 72.61 | 19833848 (302) | 86.21 | 13.79 |
| George Municipality | 788 | 464 | 58.88 | 3314853 (316) | 76.51 | 23.49 |
| Kwazulu Natal - Transport | 1557 | 452 | 29.03 | 41950209 (351) | 75.88 | 24.12 |
| CSIR | 862 | 448 | 51.97 | 16518888 (412) | 86.83 | 13.17 |
| Cape Winelands District Municipality | 639 | 431 | 67.45 | 2000000 (366) | 70.77 | 29.23 |
| KZN - Economic Development, Tourism & Environ Affairs | 765 | 431 | 56.34 | 4769000 (312) | 57.31 | 42.69 |
| Overstrand Municipality | 484 | 333 | 68.80 | 5754370 (254) | 87.69 | 12.31 |
| Cape Agulhas Municipality | 392 | 318 | 81.12 | 7826158 (195) | 77.67 | 22.33 |
| Mossel Bay Municipality | 571 | 310 | 54.29 | 14363805 (197) | 74.52 | 25.48 |
| Kwazulu Natal - Public Works (Head Office) | 881 | 291 | 33.03 | 4445878 (253) | 84.19 | 15.81 |
| Water and Sanitation | 1238 | 276 | 22.29 | 6710000 (241) | 87.32 | 12.68 |
| Ethekwini Metropolitan Municipality | 1780 | 273 | 15.34 | 104936182 (264) | 90.84 | 9.16 |
| South African Social Security Agency | 779 | 266 | 34.15 | 98137521 (136) | 92.86 | 7.14 |
| Ingquza Hill Local Municipality | 496 | 265 | 53.43 | 6093850 (265) | 40.38 | 59.62 |
| Transnet National Ports Authority | 974 | 265 | 27.21 | 22171464 (156) | 93.96 | 6.04 |
| Swellendam Municipality | 559 | 263 | 47.05 | 3070960 (185) | 81.75 | 18.25 |
| Electoral Commission (IEC) | 494 | 259 | 52.43 | 85750000 (207) | 73.75 | 26.25 |
| National Treasury | 357 | 212 | 59.38 | 7025111 (168) | 86.32 | 13.68 |
| Midvaal Local Municipality | 406 | 210 | 51.72 | 50000000 (93) | 82.86 | 17.14 |
| Development Bank of Southern Africa | 840 | 201 | 23.93 | 59524476 (142) | 86.07 | 13.93 |

### 9.4 Renewal-radar coverage (§8)

`pct` is of the 163,321 total releases, except the last row, which is of
the 52,344-release radar population.

| metric | count | pct |
|---|---|---|
| total releases | 163321 | 100.00 |
| parseable closing date | 163295 | 99.98 |
| extractable duration (6–120 mo, title+description) | 52353 | 32.06 |
| radar population (closing date + duration) | 52344 | 32.05 |
| predicted returns 2026-09 → 2027-08 | 9941 | 18.99 |

## 10. Limitations and reproducibility

Limitations, restated as a list:

1. **Coverage:** only 19.95% of releases carry an award block; the analysed
   population is the reported-award subset, never "SA procurement".
2. **Selection bias:** publication is a non-random per-buyer behaviour
   (75.74% at SARS, 0.00% at Tshwane/Joburg/Mnquma); buyer comparisons partly
   compare *publication habits*, not markets. The municipal zero rates are
   consistent with award notices being published on municipal websites
   outside this feed; a future municipal-website harvest is the identified
   fix, joinable by buyer name.
3. **Recency artifact:** 2026-H1/H2 coverage (12.53% / 3.27%) reflects the
   2026-08-20 snapshot date, not publication collapse.
4. **Missing fields:** award dates, tenderer counts, and contract periods are
   structurally absent — cycle time and competition intensity are not
   computable, full stop.
5. **Only successes:** 100% of awards are status "active"; cancelled and
   unsuccessful outcomes are never published, so win rates are unobservable.
6. **Amount quality:** 28.0% zero amounts, 825 sub-R100, 330 over-R10bn (max
   R1.80tn); benchmark statistics use the flag-cleaned N=22,311 and amounts
   carry contract-total semantics.
7. **Supplier identity:** conservative normalisation under-merges (36.85%
   id-name disagreement on id-bearing rows); supplier counts are overcounts
   and entrant shares are upper bounds. Placeholder artifacts exist
   ("non-award" as a Midvaal "supplier"; id `0` on 12,250 rows).
8. **No models:** everything here is a deterministic cross-tab; the stated
   confound (big awards mechanically favour repeat players) applies to all
   entrant correlates.

**Reproducibility.** The dataset and all numbers regenerate start-to-finish
from the corpus via `extract_awards.py`, `coverage_report.py`, and
`analyze_awards.py` in the project workspace dataset directory
`etenders-awards/` — deterministic single-pass scripts over sorted shards; a
rerun produces byte-identical outputs, and `analyze_awards.py` re-verifies
five spot-check cells on every run (all match). The dataset itself
(`awards_extract.jsonl`, 163,321 rows; `awards_only.csv`, 32,589 rows) stays
in the workspace: it is bulk third-party data and is not committed to this
repository.
