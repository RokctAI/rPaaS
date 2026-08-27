# Detector tuning report - dev cohort only

Generated 2026-08-19 11:30 UTC. The holdout cohort (2018+) was not touched: all loads go through `mining/data.py` (guard raises on any holdout read) and the single-use holdout gate marker does not exist. The frozen acceptance thresholds and the <=2 warnings per control location-year budget were treated as hard constraints and were NEVER relaxed.

## Method

1. **Rule structure** (design decision, before any parameter search): per-class conditions chosen from the mined evidence - `mining/results/SIGNATURES.md` (39 features), the 100 m-wind top-up (`mining/results_wind100/`, bulk-shear features), and the 7x7 neighborhood-precipitation top-up (`mining/results_nbr/`, displaced-rain features; nbr_rain_on_sat_6h is flash_flood's new #1 separator at -6 h, AUC 0.809). Features listed as non-separating were dropped (e.g. `dir_veer_6h` for tornado).
2. **Feasibility reconnaissance** (dev only): per-condition event-vs-control arming-rate calibration, then 51 strictness-ladder configs swept on the full dev cohort to locate the false-alarm-budget boundary. Finding: matched 408 h control windows at the same location/season contain weather episodes statistically close to event pre-windows, so the budget (<=2/loc-yr = one warning per ~5.4 control windows) is the binding constraint everywhere; hard all-of gates (joint co-occurrence of all conditions) are required.
3. **Parameter search** (`tune.py` machinery, seed 42): 60 random candidates + base per run, seeded at the boundary; 5-fold CV grouped by 10x10-degree location cluster (an event and its matched controls share a fold). A candidate is feasible only if FAR <= frozen limit AND budget <= 2/loc-yr in EVERY fold with enough data; feasible candidates ranked by mean fold POD. Each class was searched in two rounds - destructive_wind and tornado with and without the w100 bulk-shear features, flash_flood and flood with point features and with the nbr neighborhood-precip features - and the better feasible pick won per class.
4. **Full-dev backtest** of the merged config via `backtest.py` frozen metric definitions (results_dev_tuned/, uncommitted).

Tuned config: `detector_config_tuned.json`, file sha256 `758ba92bb6ce69c11fc6586c2f64722321e51d19d4c864906cbead9046162ac8`, classes-object sha256 `565b0752491af3f12c803662b385345a2d65e0a0db8b1e5e870618662774381a`.

## Full-dev backtest vs the frozen bars (PLAN.md, frozen 2026-08-19)

| class | events | POD (bar) | FAR (bar) | budget /loc-yr (<=2) | median lead h (bar) | lead IQR h | verdict |
|---|---|---|---|---|---|---|---|
| flash_flood | 1472 | 0.127 (>=0.6) | 0.306 (<=0.6) | 1.62 | 38.0 (>=6) | 15.0..99.5 | **FAIL** (POD) |
| flood | 2429 | 0.054 (>=0.65) | 0.370 (<=0.5) | 1.46 | 94.0 (>=24) | 48.8..140.0 | **FAIL** (POD) |
| destructive_wind | 2055 | 0.228 (>=0.7) | 0.161 (<=0.4) | 1.31 | 20.0 (>=12) | 15.0..29.0 | **FAIL** (POD) |
| tornado | 1587 | 0.086 (>=0.4) | 0.343 (<=0.75) | 1.06 | 23.0 (>=3) | 5.0..59.2 | **FAIL** (POD) |

### Miss breakdown (full itemized lists live in results_dev_tuned/misses.csv, uncommitted)

| class | hits | misses | no_alarm | insufficient_lead | alarm_outside_window |
|---|---|---|---|---|---|
| flash_flood | 187 | 1285 | 1021 | 102 | 162 |
| flood | 130 | 2299 | 1921 | 89 | 289 |
| destructive_wind | 469 | 1586 | 796 | 596 | 194 |
| tornado | 136 | 1451 | 1303 | 76 | 72 |

## flash_flood - search detail

- `flash_flood` (point features only): 30 feasible of 61; best feasible `cand_051` - mean fold POD 0.107, pooled dev POD 0.116, FAR 0.303, budget 1.40/loc-yr, median lead 30 h
- `flash_flood_nbr` (with nbr precip): 16 feasible of 61; best feasible `cand_025` - mean fold POD 0.118, pooled dev POD 0.127, FAR 0.306, budget 1.62/loc-yr, median lead 32 h **<- picked**

Picked params: `warn>=0.682, cool=24h / moist ab 12.9108(p3); nbr_rs6 ab 13.4671(p1); nbr_max12 ab 42.115(p3); nbr_wet ab 1.018(p3)`

(POD, FAR) frontier over all 122 tuned candidates (pooled dev; Pareto-optimal on max-POD/min-FAR; the budget column shows why high-POD points are excluded - constraints were not relaxed):

| candidate | POD | FAR | budget /loc-yr |
|---|---|---|---|
| flash_flood_nbr/cand_032 | 0.024 | 0.127 | 0.15 |
| flash_flood_nbr/cand_017 | 0.026 | 0.148 | 0.19 |
| flash_flood_nbr/cand_056 | 0.032 | 0.151 | 0.23 |
| flash_flood_nbr/cand_008 | 0.034 | 0.157 | 0.24 |
| flash_flood_nbr/cand_044 | 0.041 | 0.185 | 0.36 |
| flash_flood/cand_049 | 0.054 | 0.210 | 0.51 |
| flash_flood/cand_006 | 0.056 | 0.224 | 0.54 |
| flash_flood/cand_010 | 0.057 | 0.239 | 0.58 |
| flash_flood/cand_035 | 0.075 | 0.243 | 0.77 |
| flash_flood/cand_036 | 0.097 | 0.269 | 1.18 |
| flash_flood_nbr/cand_036 | 0.130 | 0.293 | 1.70 |
| flash_flood_nbr/cand_045 | 0.159 | 0.320 | 1.93 |
| flash_flood_nbr/cand_049 | 0.175 | 0.327 | 2.38 |
| flash_flood_nbr/cand_040 | 0.206 | 0.360 | 2.81 |
| flash_flood_nbr/cand_043 | 0.231 | 0.367 | 3.66 |
| flash_flood_nbr/cand_016 | 0.253 | 0.386 | 4.36 |
| flash_flood_nbr/cand_003 | 0.270 | 0.392 | 4.46 |
| flash_flood_nbr/cand_051 | 0.308 | 0.429 | 5.30 |
| flash_flood_nbr/base | 0.356 | 0.469 | 6.90 |
| flash_flood_nbr/cand_007 | 0.385 | 0.481 | 9.40 |
| flash_flood_nbr/cand_018 | 0.398 | 0.491 | 10.33 |
| flash_flood_nbr/cand_054 | 0.418 | 0.498 | 11.11 |
| flash_flood_nbr/cand_055 | 0.452 | 0.528 | 11.68 |
| flash_flood_nbr/cand_042 | 0.502 | 0.546 | 13.42 |
| flash_flood_nbr/cand_019 | 0.639 | 0.561 | 23.46 |

Per-fold scores of the pick:

| fold | events | controls | POD | FAR | budget | median lead h |
|---|---|---|---|---|---|---|
| 0 | 403 | 806 | 0.12 | 0.34 | 1.76 | 90 |
| 1 | 306 | 612 | 0.12 | 0.31 | 1.65 | 30 |
| 2 | 169 | 338 | 0.07 | 0.19 | 0.76 | 8 |
| 3 | 368 | 736 | 0.19 | 0.28 | 1.93 | 32 |
| 4 | 226 | 452 | 0.08 | 0.39 | 1.47 | 74 |

## flood - search detail

- `flood` (point features only): 42 feasible of 61; best feasible `cand_034` - mean fold POD 0.049, pooled dev POD 0.054, FAR 0.370, budget 1.46/loc-yr, median lead 86 h **<- picked**
- `flood_nbr` (with nbr precip): 9 feasible of 61; best feasible `cand_043` - mean fold POD 0.039, pooled dev POD 0.043, FAR 0.361, budget 1.23/loc-yr, median lead 81 h

Picked params: `warn>=0.673, cool=24h / rsat_24 ab 22.1904(p1); rsat_72 ab 39.5838(p3); rain_24 ab 78.481(p1); rain_48 ab 45.4787(p3)`

(POD, FAR) frontier over all 122 tuned candidates (pooled dev; Pareto-optimal on max-POD/min-FAR; the budget column shows why high-POD points are excluded - constraints were not relaxed):

| candidate | POD | FAR | budget /loc-yr |
|---|---|---|---|
| flood/cand_017 | 0.009 | 0.294 | 0.31 |
| flood/cand_057 | 0.012 | 0.303 | 0.38 |
| flood/cand_049 | 0.026 | 0.312 | 0.70 |
| flood/cand_056 | 0.033 | 0.331 | 0.88 |
| flood/cand_030 | 0.037 | 0.344 | 1.09 |
| flood/cand_010 | 0.040 | 0.355 | 1.12 |
| flood_nbr/cand_043 | 0.043 | 0.361 | 1.23 |
| flood/cand_023 | 0.050 | 0.362 | 1.38 |
| flood/cand_008 | 0.053 | 0.367 | 1.46 |
| flood/cand_034 | 0.054 | 0.370 | 1.46 |
| flood_nbr/cand_041 | 0.060 | 0.379 | 2.06 |
| flood/cand_046 | 0.068 | 0.382 | 1.92 |
| flood/base | 0.072 | 0.387 | 1.97 |
| flood/cand_035 | 0.072 | 0.394 | 2.04 |
| flood/cand_026 | 0.087 | 0.403 | 2.43 |
| flood_nbr/cand_011 | 0.091 | 0.417 | 2.97 |
| flood/cand_020 | 0.107 | 0.417 | 3.18 |
| flood_nbr/cand_007 | 0.110 | 0.419 | 3.40 |
| flood_nbr/cand_053 | 0.115 | 0.424 | 3.60 |
| flood_nbr/cand_049 | 0.116 | 0.429 | 3.85 |
| flood_nbr/cand_032 | 0.122 | 0.436 | 4.74 |
| flood_nbr/cand_036 | 0.130 | 0.438 | 4.44 |
| flood_nbr/cand_027 | 0.132 | 0.439 | 4.71 |
| flood_nbr/cand_018 | 0.136 | 0.441 | 5.15 |
| flood_nbr/cand_021 | 0.143 | 0.452 | 5.51 |
| flood_nbr/base | 0.155 | 0.454 | 4.85 |
| flood_nbr/cand_035 | 0.160 | 0.459 | 6.39 |
| flood_nbr/cand_050 | 0.180 | 0.459 | 5.90 |
| flood/cand_001 | 0.183 | 0.463 | 5.85 |
| flood_nbr/cand_029 | 0.203 | 0.475 | 6.96 |
| flood_nbr/cand_024 | 0.212 | 0.477 | 8.47 |
| flood_nbr/cand_034 | 0.227 | 0.490 | 8.66 |
| flood_nbr/cand_003 | 0.257 | 0.496 | 9.65 |
| flood_nbr/cand_023 | 0.317 | 0.522 | 12.82 |

Per-fold scores of the pick:

| fold | events | controls | POD | FAR | budget | median lead h |
|---|---|---|---|---|---|---|
| 0 | 633 | 1266 | 0.07 | 0.41 | 1.95 | 86 |
| 1 | 604 | 1208 | 0.05 | 0.36 | 1.41 | 116 |
| 2 | 503 | 1006 | 0.04 | 0.33 | 1.22 | 86 |
| 3 | 445 | 890 | 0.07 | 0.38 | 1.57 | 82 |
| 4 | 244 | 488 | 0.01 | 0.31 | 0.62 | 29 |

## destructive_wind - search detail

- `destructive_wind_shear` (with w100 bulk-shear): 24 feasible of 61; best feasible `cand_042` - mean fold POD 0.206, pooled dev POD 0.205, FAR 0.172, budget 1.36/loc-yr, median lead 20 h
- `destructive_wind_noshear` (point features only): 47 feasible of 61; best feasible `cand_045` - mean fold POD 0.228, pooled dev POD 0.228, FAR 0.161, budget 1.31/loc-yr, median lead 20 h **<- picked**

Picked params: `warn>=0.779, cool=48h / mslp_fall be -4.8918(p2); gust_high ab 16.9571(p4); wspd_high ab 11.8304(p2); moist ab 10.9388(p5)`

(POD, FAR) frontier over all 122 tuned candidates (pooled dev; Pareto-optimal on max-POD/min-FAR; the budget column shows why high-POD points are excluded - constraints were not relaxed):

| candidate | POD | FAR | budget /loc-yr |
|---|---|---|---|
| destructive_wind_noshear/cand_037 | 0.076 | 0.102 | 0.52 |
| destructive_wind_noshear/cand_032 | 0.094 | 0.107 | 0.65 |
| destructive_wind_noshear/cand_052 | 0.108 | 0.110 | 0.67 |
| destructive_wind_noshear/cand_053 | 0.109 | 0.111 | 0.71 |
| destructive_wind_noshear/cand_014 | 0.140 | 0.121 | 0.84 |
| destructive_wind_noshear/cand_030 | 0.171 | 0.125 | 0.99 |
| destructive_wind_noshear/cand_000 | 0.183 | 0.138 | 1.13 |
| destructive_wind_shear/cand_047 | 0.206 | 0.145 | 1.25 |
| destructive_wind_shear/cand_030 | 0.251 | 0.150 | 1.44 |
| destructive_wind_noshear/cand_036 | 0.258 | 0.166 | 1.67 |
| destructive_wind_noshear/cand_026 | 0.261 | 0.178 | 1.53 |
| destructive_wind_shear/cand_008 | 0.285 | 0.179 | 1.60 |
| destructive_wind_shear/cand_007 | 0.303 | 0.200 | 2.25 |
| destructive_wind_shear/base | 0.310 | 0.201 | 1.93 |
| destructive_wind_shear/cand_040 | 0.331 | 0.204 | 2.11 |
| destructive_wind_shear/cand_034 | 0.366 | 0.205 | 2.15 |
| destructive_wind_shear/cand_026 | 0.401 | 0.229 | 2.52 |

Per-fold scores of the pick:

| fold | events | controls | POD | FAR | budget | median lead h |
|---|---|---|---|---|---|---|
| 0 | 358 | 716 | 0.17 | 0.12 | 0.87 | 18 |
| 1 | 508 | 1016 | 0.23 | 0.16 | 1.35 | 19 |
| 2 | 293 | 586 | 0.30 | 0.21 | 1.87 | 20 |
| 3 | 347 | 694 | 0.19 | 0.21 | 1.83 | 21 |
| 4 | 549 | 1098 | 0.25 | 0.12 | 0.92 | 21 |

## tornado - search detail

- `tornado_shear` (with w100 bulk-shear): 30 feasible of 61; best feasible `cand_009` - mean fold POD 0.081, pooled dev POD 0.086, FAR 0.343, budget 1.06/loc-yr, median lead 30 h **<- picked**
- `tornado_noshear` (point features only): 1 feasible of 61; best feasible `cand_032` - mean fold POD 0.058, pooled dev POD 0.054, FAR 0.368, budget 0.77/loc-yr, median lead 36 h

Picked params: `warn>=0.584, cool=24h / shear_high ab 4.0814(p1); theta_e_high ab 331.6041(p1); theta_e_surge ab 7.3756(p1); moist ab 12.4406(p1); mslp_fall be -6.1838(p1)`

(POD, FAR) frontier over all 122 tuned candidates (pooled dev; Pareto-optimal on max-POD/min-FAR; the budget column shows why high-POD points are excluded - constraints were not relaxed):

| candidate | POD | FAR | budget /loc-yr |
|---|---|---|---|
| tornado_shear/cand_041 | 0.001 | 0.000 | 0.00 |
| tornado_shear/cand_020 | 0.002 | 0.143 | 0.03 |
| tornado_shear/cand_004 | 0.011 | 0.182 | 0.15 |
| tornado_shear/cand_002 | 0.012 | 0.196 | 0.15 |
| tornado_shear/cand_014 | 0.014 | 0.206 | 0.19 |
| tornado_shear/cand_059 | 0.020 | 0.233 | 0.19 |
| tornado_shear/cand_033 | 0.064 | 0.262 | 0.64 |
| tornado_shear/cand_056 | 0.093 | 0.321 | 0.89 |
| tornado_shear/cand_046 | 0.117 | 0.343 | 1.38 |
| tornado_shear/cand_016 | 0.127 | 0.353 | 1.47 |
| tornado_shear/cand_029 | 0.218 | 0.356 | 2.37 |
| tornado_shear/cand_008 | 0.219 | 0.371 | 2.37 |
| tornado_shear/cand_022 | 0.292 | 0.383 | 3.64 |
| tornado_shear/cand_058 | 0.309 | 0.409 | 3.65 |
| tornado_shear/base | 0.387 | 0.450 | 5.46 |
| tornado_noshear/cand_007 | 0.390 | 0.478 | 6.25 |
| tornado_noshear/cand_036 | 0.415 | 0.478 | 6.74 |

Per-fold scores of the pick:

| fold | events | controls | POD | FAR | budget | median lead h |
|---|---|---|---|---|---|---|
| 0 | 666 | 1332 | 0.04 | 0.34 | 0.68 | 10 |
| 1 | 141 | 282 | 0.13 | 0.24 | 1.22 | 148 |
| 2 | 29 | 58 | 0.00 | n/a | 0.00 | n/a |
| 3 | 491 | 982 | 0.13 | 0.33 | 1.18 | 12 |
| 4 | 260 | 520 | 0.10 | 0.44 | 1.86 | 48 |

## Reading of the result

No class reaches its frozen POD bar on dev under the frozen false-alarm budget; FAR, median-lead, and budget bars are met everywhere by construction of the selection rule. Root cause, quantified by the calibration probes (calib_runs/, uncommitted): matched 408 h control windows at the same location and season contain weather episodes whose window-level statistics are close to - for flood, wetter than - event pre-windows, so the budget (one warning per ~5.4 control windows) caps how often the detector may fire far below the POD bars. What limits each class, and what the pre-registered levers did / would do:

- **destructive_wind** (bar 0.70, feasible ~0.23): misses split between `no_alarm` and `insufficient_lead` - a joint gate strict enough for the budget typically completes only inside the final 12 h, too late for the >=12 h minimum lead. **100 m bulk shear (tested)**: strong AUCs (0.845 at -12 h) and feasible in-fold, but its best feasible POD (0.206) did not beat the no-shear rule (0.228) - both recorded above. **Neighborhood features (untested for wind)**: seeing the approaching cyclone at surrounding grid points targets exactly the insufficient-lead bucket and is the one lever plausibly worth several tenths; closing 0.23 -> 0.70 with point data alone is not credible.
- **flash_flood** (bar 0.60, feasible ~0.12): **neighborhood precip (tested)** - the 7x7 displaced-rain features are the new top separators (nbr_rain_on_sat_6h AUC 0.809 at -6 h) and the nbr round won the pick, but the feasible gain was 0.107 -> 0.118 mean-fold POD: better separation at the same hour does not fix the budget cap, because control windows still contain their own convective episodes. **Soil climatology (untested)** may trim false alarms on climatologically wet points; a large gap to 0.60 would remain.
- **flood** (bar 0.65, feasible ~0.05): the hardest case - window-level calibration gaps are NEGATIVE (controls wetter), and **neighborhood precip (tested) did not help** (0.039 vs 0.049 point-only; -24 h AUC ceiling only 0.610 -> 0.625). At a single grid point, long-window rain loading cannot identify which wet episodes flood. **Basin-scale / upstream aggregation (routing rain over the actual catchment) is the identified next lever beyond this wave**; without it the bar is out of reach of this feature set.
- **tornado** (bar 0.40, feasible ~0.08): **100 m bulk shear (tested)** is the strongest single discriminator (AUC 0.791 at -6 h) and the shear round won the pick (0.081 vs 0.058 without), but skill exists only inside ~24 h and the budget forces near-total strictness. **Neighborhood features (untested for tornado)** might roughly double feasible POD; reaching 0.40 under a 2/loc-yr budget with single-point ERA5 (no CAPE, no storm-scale shear) is doubtful.

The 7-day hit window also books alarms that fire 3-7 days early as `alarm_outside_window` misses; a portion of the no-hit mass is early-firing rather than silent (see misses.csv).
