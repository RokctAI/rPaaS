# Final backtest report - single-use holdout run (2026-08-19)

This is the report of record for the severe-weather precursor detector. It grades the
frozen, dev-tuned configuration against the pre-registered acceptance thresholds on the
held-out cohort, in exactly one gated run. **Verdict: NOT ACCEPTED at the frozen bars -
all four classes fail their POD bar; every FAR, false-alarm-budget, and median-lead bar
passes.** No threshold is re-litigated here; the frozen verdict stands as computed.

## 1. Protocol

- **Thresholds frozen before any mining.** The acceptance thresholds (PLAN.md,
  "Acceptance thresholds (frozen 2026-08-19, before any signature mining or tuning)")
  were committed before signature mining or tuning began. Metric definitions are
  implemented verbatim in `detector/backtest.py` (`FROZEN`); the definitions used below
  are exactly those.
- **Dev/holdout split pre-registered.** `extraction/SAMPLING.md`: dev = onsets before
  2018-01-01, holdout = 2018+ (through 2025), fixed before extraction. Holdout series
  were physically unreachable during mining and tuning (`mining/data.py` guard; refusal
  proven by `mining/test_holdout_guard.py` and `detector/test_holdout_gate.py`).
- **Config frozen from dev-only tuning.** `detector/detector_config_tuned.json`,
  file sha256 `758ba92bb6ce69c11fc6586c2f64722321e51d19d4c864906cbead9046162ac8`
  (classes-object sha256 `565b0752491af3f12c803662b385345a2d65e0a0db8b1e5e870618662774381a`),
  produced by the dev-only search documented in `detector/tuning_report.md`. No edits
  after freezing; the holdout gate verified the hash before unlocking.
- **Single-use gate.** The run was executed once by `detector/run_backtest_holdout.py`
  (`--execute --holdout --i-understand-single-use`) after a dev-cohort dry run of the
  identical loader path. The tamper-evident `HOLDOUT_RUN_MARKER.json` was written
  before any holdout data was loaded and finalized with the results digest:
  - `config_sha256`: `758ba92bb6ce69c11fc6586c2f64722321e51d19d4c864906cbead9046162ac8`
  - `started_utc`: `2026-08-19T12:34:25Z`, `finished_utc`: `2026-08-19T12:43:02Z`
  - `results_sha256`: `a142605795ed3c3fc80052774849d77387857f12f51781aece6dc033474dda28`
  - `signature_sha256`: `eedf20750e587d00a6dbb379886a55c0cd973f29a290a74f23d696425fabb6c8`
  Any further holdout attempt is refused while the marker exists. Post-hoc breakdowns
  in section 5 slice the recorded outputs of this same run
  (`detector/supplementary_holdout.py`); no second pass over holdout data was made.
- **Cohort actually scored:** 1,729 holdout events + 3,454 matched controls
  (flash_flood 528/1054, flood 269/538, destructive_wind 412/822, tornado 520/1040);
  every manifest holdout series was present and complete (no partial-data caveat).

## 2. Headline: holdout results vs the frozen bars

Metrics of record (frozen definitions: hit = correct-class warning active in
[onset - 7 d, onset] with at least the class minimum lead; FAR on matched controls;
budget = warning-or-worse episodes per control location-year, counted conservatively
across all tiers).

| class | events | POD (bar) | verdict | FAR (bar) | verdict | budget /loc-yr (<=2) | verdict | median lead h (bar) | verdict | lead IQR h | overall |
|---|---|---|---|---|---|---|---|---|---|---|---|
| flash_flood | 528 | 0.133 (>=0.60) | **FAIL** | 0.286 (<=0.60) | PASS | 1.45 | PASS | 33.5 (>=6) | PASS | 15.2..88.0 | **FAIL (POD)** |
| flood | 269 | 0.026 (>=0.65) | **FAIL** | 0.338 (<=0.50) | PASS | 1.00 | PASS | 83.0 (>=24) | PASS | 55.0..129.5 | **FAIL (POD)** |
| destructive_wind | 412 | 0.163 (>=0.70) | **FAIL** | 0.146 (<=0.40) | PASS | 1.23 | PASS | 19.0 (>=12) | PASS | 14.0..28.5 | **FAIL (POD)** |
| tornado | 520 | 0.117 (>=0.40) | **FAIL** | 0.304 (<=0.75) | PASS | 0.87 | PASS | 7.0 (>=3) | PASS | 5.0..11.0 | **FAIL (POD)** |

Cross-class alarm budget on all controls combined: 2.09 warnings/loc-yr over 160.8
control location-years (informational; the frozen budget is per-class above).

Full outputs: `detector/results_holdout/` (`results.csv`, `results.md`, `misses.csv`,
`false_alarms.csv`, `lead_times.csv`, `summary.json`).

## 3. Dev results for reference (same config, results of record from tuning)

| class | events | POD | FAR | budget /loc-yr | median lead h | lead IQR h | holdout vs dev |
|---|---|---|---|---|---|---|---|
| flash_flood | 1472 | 0.127 | 0.306 | 1.62 | 38.0 | 15.0..99.5 | POD +0.006 (stable), FAR/budget slightly better |
| flood | 2429 | 0.054 | 0.370 | 1.46 | 94.0 | 48.8..140.0 | POD -0.028 (worse; 7 hits, small numbers) |
| destructive_wind | 2055 | 0.228 | 0.161 | 1.31 | 20.0 | 15.0..29.0 | POD -0.065 (worse), FAR/budget slightly better |
| tornado | 1587 | 0.086 | 0.343 | 1.06 | 23.0 | 5.0..59.2 | POD +0.031 (better), median lead 23 -> 7 h (still >= 3 h bar) |

Generalization reading: the false-alarm side transfers cleanly - FAR and budget are
*better* on holdout than dev in all four classes, so the tuned gates did not overfit
the dev controls. POD moves within sampling noise for flash_flood and tornado, and
drops for destructive_wind (0.228 -> 0.163) and flood (0.054 -> 0.026). For wind the
drop concentrates in 2024-2025 (0 hits on 68 events in those two years vs 0.10-0.32
POD per year 2018-2023 - see section 5); for flood the holdout count is 7 hits, so the
dev-holdout difference is at the edge of statistical resolution. Nothing in the
holdout result changes the dev-era conclusion: the frozen POD bars are missed by a
wide margin at the budget-feasible operating point, and pass/fail was never close.

## 4. Misses

Miss reasons per class (frozen taxonomy: `no_alarm` = no episode at all in the window,
`insufficient_lead` = alarm active but first fired later than the class minimum lead,
`alarm_outside_window` = episodes exist but none inside [onset - 7 d, onset]):

| class | hits | misses | no_alarm | insufficient_lead | alarm_outside_window |
|---|---|---|---|---|---|
| flash_flood | 70 | 458 | 366 | 36 | 56 |
| flood | 7 | 262 | 228 | 5 | 29 |
| destructive_wind | 67 | 345 | 144 | 102 | 99 |
| tornado | 61 | 459 | 429 | 17 | 13 |

The full itemized miss list - every missed event with `event_id`, onset, reason, best
confidence reached, location, and severity metadata - is committed at
`detector/results_holdout/misses.csv` (1,524 rows). The itemized false-alarm list
(185 rows: series, firing time, tier, confidence, fired conditions) is
`detector/results_holdout/false_alarms.csv`; the per-hit lead distribution is
`detector/results_holdout/lead_times.csv`.

Notable pattern (same as dev): destructive_wind is the only class where
`insufficient_lead` + `alarm_outside_window` (201) outweighs `no_alarm` (144) - the
detector usually sees the cyclone but fires late relative to the >= 12 h bar, or early
relative to the 7-day window, both artifacts of onset being timed at the IBTrACS
peak-intensity fix (see section 7).

## 5. Post-hoc breakdowns (reporting, not tuning - clearly separated from the frozen verdict)

Everything in this section slices the recorded results of the single run. It changes
no metric of record. Computed by `detector/supplementary_holdout.py` with the same
bucket definitions as the dev supplement (`detector/SUPPLEMENTARY_DEV.md`).

### 5.1 Severity (major vs non-major, finer buckets)

POD rises with event severity in every class where severity is measured - the same
gradient as dev, mostly steeper on holdout:

| class | major POD (n) | non-major POD (n) | finer buckets |
|---|---|---|---|
| flash_flood | **0.441** (34) | 0.111 (494) | damage >$100M: **0.536** (28) vs $0: 0.092 (316); deaths 1-9: 0.220 |
| flood | 0.029 (171) | 0.020 (98) | deaths 10+: 0.039 (129); DFO sev 1.5: 0.040; every bucket far below the bar |
| destructive_wind | 0.206 (272) | 0.079 (140) | TC Cat1-2: 0.344 (32), TC Cat3+: 0.344 (160); US convective wind: 0.000-0.009 |
| tornado | 0.148 (305) | 0.074 (215) | EF3+: **0.149** (302) vs EF0-1: 0.012 (81); EF2: 0.118 |

Median lead among major-event hits: flash_flood 15 h, destructive_wind 18 h, tornado
7 h, flood 99 h.

### 5.2 Region and year

- flash_flood: all 528 holdout rows are US Storm Events; POD by year 0.06-0.22 with no
  trend (2025: 0.061, dominated by the very large Texas Hill Country sample).
- flood: US 0.019 (107) vs non-US DFO 0.031 (162).
- destructive_wind: **TC basins 0.344 (192) vs US convective wind reports 0.005
  (220)** - the class remains two populations, and the frozen all-events bar averages
  over both. Per-year TC-era POD is 0.10-0.32 through 2023, then 0.000 on 45 events in
  2024 and 23 in 2025. That 2024-2025 collapse is worth flagging honestly: it may
  reflect provisional IBTrACS best-track data and the near-real-time ERA5 tail rather
  than a detector change, but on the recorded metrics it is a real 0/68.
- tornado: POD by year swings 0.012-0.333 (n = 29-81/yr) - consistent with a
  small-sample environment screen, not a stable event-level detector.

### 5.3 Control contamination (p99.9 criterion)

A "false" alarm is flagged contaminated when the hazard variable (24 h precip for
flood classes, 10 m gust for wind classes) within [fired - 24 h, last_active + 48 h]
reaches the location's own pooled-window p99.9 - essentially the most extreme hour
ever sampled at that location, strong evidence of an uncatalogued event.

| class | false alarms | >=p99.9 | >=event peak | frozen FAR -> excl. p99.9 | frozen budget -> excl. p99.9 |
|---|---|---|---|---|---|
| flash_flood | 71 | 35% | 42% | 0.286 -> 0.206 | 1.45 -> 0.96 |
| flood | 25 | **64%** | 80% | 0.338 -> 0.093 | 1.00 -> 0.21 |
| destructive_wind | 47 | 36% | 40% | 0.146 -> 0.095 | 1.23 -> 0.77 |
| tornado | 42 | 33% | 29% | 0.304 -> 0.220 | 0.87 -> 0.57 |

The frozen FAR/budget above remain the metrics of record; these adjusted columns say
the true false-alarm behavior is likely better than the frozen accounting, especially
for flood, where most "false" alarms sit on the most extreme rainfall ever sampled at
that location (DFO catalog coverage gaps).

### 5.4 De-seasonalized budget note

The frozen budget annualizes 408 h season-matched control windows (x21.5), implicitly
treating the whole year like storm season - the conservative upper reading. Holdout
alarm rates per control window: flash_flood 0.067, flood 0.046, destructive_wind
0.057, tornado 0.040 (about one warning per 15-25 windows). Under a nominal 13-week
season (x5.4, quiet season = 0) the budget readings would be 0.22-0.36/loc-yr;
the truth lies between the columns. Controls spend 0.05-0.29% of hours at watch tier
or above - the detector is quiet almost always.

### 5.5 Named holdout-era anchors

Representative anchor rows plus catalog siblings sampled into holdout (same class,
onset within 2 days, within 3 degrees). Frozen scoring.

| anchor | class | rows | outcome |
|---|---|---|---|
| Hurricane Michael 2018 | destructive_wind | 1 | MISS (insufficient_lead) |
| Hurricane Dorian 2019 | destructive_wind | 1 | MISS (insufficient_lead) |
| Hurricane Ida 2021 | destructive_wind | 1 | MISS (insufficient_lead) |
| Hurricane Ian 2022 | destructive_wind | 1 | MISS (insufficient_lead) |
| Cyclone Idai 2019 | destructive_wind | 1 | MISS (no_alarm) |
| Quad-State (Mayfield KY) EF4 2021 | tornado | 23 | MISS 0/23 (no_alarm x19, insufficient_lead x4) |
| Eastern Kentucky flash flood 2022 | flash_flood | 2 | MISS 0/2 (no_alarm) |
| Texas Hill Country flash flood 2025 | flash_flood | 5 | **HIT 1/5** (lead 19 h) |
| Ahr valley flood 2021 | flood | 1 | MISS (no_alarm) |
| Zhengzhou (Henan) flood 2021 | flood | 1 | MISS (insufficient_lead) |
| August 2020 Midwest derecho | destructive_wind | 0 | not sampled into holdout |

Every holdout-era anchor hurricane (Michael, Dorian, Ida, Ian) misses the same way the
dev anchors (Katrina, Mitch, Harvey, Irma, Maria) did: an alarm was active but first
fired inside the final 12 h before the peak-intensity onset fix - the
onset-definition artifact, not silence. Quad-State 2021 (December, strongly sheared
but marginal point thermodynamics) and the marquee dev outbreaks confirm the tornado
rule screens environments, not events.

## 6. Limpopo blind case study (cross-reference)

The catalog metrics above are complemented by one deep blind case study,
`casestudy_limpopo/LIMPOPO_CASE_STUDY.md`: the identical frozen config
(sha256 `758ba92b...`), run causally over six ERA5 grid points spanning the Limpopo
basin, warned at all six points during the Dec 2025 - Feb 2026 floods - a period no
tuning ever saw - including flood-severe episodes at the lower-basin points 10.2 days
before the 20 Jan Xai-Xai evacuation order, with an alarm climatology of ~0.5
flood-severe episodes per point-year whose historical clusters line up with documented
floods (1996, 1999, 2000, 2013, Dando 2012, Dineo 2017, Eloise 2021, Freddy 2023). It
also illustrates why the catalog POD understates operational value: several of the
most useful 2026 warnings fired so early, or verified downstream of the rain via the
river, that the frozen 7-day/point-scale scoring books them as misses.

## 7. Honest conclusions

**What the detector demonstrably does at this operating point.** Under a hard budget
of <= 2 warnings per control location-year (achieved: 0.87-1.45), with FAR 0.15-0.34
and compliant lead times, it catches: about one in three tropical cyclones near
landfall (~19 h median lead), about half of the very-high-impact US flash floods
(>$100M damage POD 0.54, major-flag 0.44, ~15 h lead) and one in eight overall, one in
seven EF3+ tornado rows (7 h median lead, environment-screen semantics), and a small
fraction of riverine floods with multi-day leads (83 h median). Its false-alarm
behavior generalizes from dev to holdout with margin, and one third to two thirds of
its residual "false" alarms coincide with the most extreme weather ever sampled at
that location. Where the physics is synoptic-scale and local - moisture plumes feeding
saturated ground, deep pressure falls with high gusts - the precursors are real,
transferable, and cheap to compute from a single ERA5 grid point.

**What it does not do.** It does not meet any frozen POD bar, on dev or holdout, and
the shortfall is structural, not a tuning artifact: matched same-location, same-season
control windows contain weather statistically close to event pre-windows, so any rule
loose enough to approach the POD bars explodes the false-alarm budget
(`detector/tuning_report.md`, candidate frontiers). It does not detect convectively
driven events at point scale (US convective wind POD 0.005-0.01, EF0-1 tornadoes 0.01,
majority-population US flash floods ~0.1); it does not localize riverine floods from
point rain (flood POD 0.026 against country-scale DFO rows); and it does not clear the
12 h lead bar for cyclones whose onset is timed at peak intensity, because its alarm
tracks the arriving circulation itself.

**Identified next levers (pre-registered in the tuning report, not attempted here):**
1. **Basin/upstream aggregation for flood** - route rain over the actual catchment
   instead of verifying at a centroid grid point; the Limpopo study shows the upstream
   signal exists days ahead. The largest single gap (0.026 vs 0.65) cannot close
   without it.
2. **Neighborhood/storm-scale predictors for wind and tornado** - seeing the
   approaching system at surrounding grid points targets the dominant
   insufficient-lead miss bucket for TCs; storm-scale shear/CAPE (absent from ERA5
   point series) is the missing ingredient for tornado event-level skill.
3. **Onset-definition artifacts for TC lead** - IBTrACS onsets at the peak-intensity
   fix systematically shrink measured leads (all nine anchor hurricanes across both
   cohorts miss as insufficient_lead/outside-window, not no_alarm); scoring against
   landfall or wind-arrival time would measure the same alarms very differently. A
   severity-gated warning surface (TC Cat1+, watch-tier lead) is the defensible
   product shape inside the current feature set.

The frozen thresholds were set as product acceptance bars before any evidence
existed on feasibility; the evidence now exists, the algorithm as tuned does not meet
them, and this report records that plainly. The verdict stands as computed.
