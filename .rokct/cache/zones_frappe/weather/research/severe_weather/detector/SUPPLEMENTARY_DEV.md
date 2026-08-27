# Supplementary dev-set analysis (post-hoc)

Generated 2026-08-19 12:26 UTC by `supplementary_dev.py` (every number here is reproduced by that script; it re-runs the tuned config over the dev cohort in-process and asserts exact agreement with `results_dev_tuned/summary.json` before slicing).

**Scope and rules.** All analyses are honest post-hoc breakdowns of the SAME dev backtest that produced the headline numbers: no retuning, no config changes, no holdout access (holdout series stay behind the guard in `mining/data.py`; the single-use gate in `backtest.py` is untouched). The frozen metrics remain the metrics of record; everything labeled *post-hoc* below is interpretation, not a replacement.

Config: `detector_config_tuned.json`. Dev backtest of record: `results_dev_tuned/` (FAR, budget and median-lead bars pass in all four classes; all four frozen POD bars fail).

Reproduction check: flash_flood: OK (187/1472 hits, 222 false alarms); flood: OK (130/2429 hits, 330 false alarms); destructive_wind: OK (469/2055 hits, 250 false alarms); tornado: OK (136/1587 hits, 157 false alarms)

## 1. POD by severity

Hit = warning of the correct class active in [onset-7d, onset] with at least the frozen class minimum lead (frozen definition, unchanged). Median lead is over hits in the bucket.

### flash_flood

| major flag | events | hits | POD | median lead h |
|---|---|---|---|---|
| major | 183 | 32 | 0.175 | 22 |
| non-major | 1289 | 155 | 0.120 | 50 |

| deaths | events | hits | POD | median lead h |
|---|---|---|---|---|
| 0 | 1195 | 152 | 0.127 | 40 |
| 1-9 | 192 | 28 | 0.146 | 30 |
| 10+ | 85 | 7 | 0.082 | 23 |

| magnitude bucket | events | hits | POD | median lead h |
|---|---|---|---|---|
| DFO severity 1 | 158 | 9 | 0.057 | 110 |
| DFO severity 1.5 | 1 | 0 | 0.000 | - |
| DFO severity 2 | 30 | 1 | 0.033 | 16 |
| US (no magnitude) | 1283 | 177 | 0.138 | 37 |

| damage | events | hits | POD | median lead h |
|---|---|---|---|---|
| $0 | 656 | 70 | 0.107 | 53 |
| <$1M | 385 | 56 | 0.145 | 64 |
| $1M-$100M | 159 | 24 | 0.151 | 27 |
| >$100M | 83 | 27 | 0.325 | 23 |
| unknown | 189 | 10 | 0.053 | 96 |

### flood

| major flag | events | hits | POD | median lead h |
|---|---|---|---|---|
| major | 2177 | 127 | 0.058 | 93 |
| non-major | 252 | 3 | 0.012 | 124 |

| deaths | events | hits | POD | median lead h |
|---|---|---|---|---|
| 0 | 426 | 13 | 0.031 | 76 |
| 1-9 | 273 | 13 | 0.048 | 39 |
| 10+ | 1730 | 104 | 0.060 | 97 |

| magnitude bucket | events | hits | POD | median lead h |
|---|---|---|---|---|
| DFO severity 1 | 1287 | 70 | 0.054 | 105 |
| DFO severity 1.5 | 235 | 17 | 0.072 | 85 |
| DFO severity 2 | 659 | 33 | 0.050 | 86 |
| US (no magnitude) | 248 | 10 | 0.040 | 37 |

| damage | events | hits | POD | median lead h |
|---|---|---|---|---|
| $0 | 98 | 2 | 0.020 | 129 |
| <$1M | 33 | 0 | 0.000 | - |
| $1M-$100M | 45 | 0 | 0.000 | - |
| >$100M | 72 | 8 | 0.111 | 37 |
| unknown | 2181 | 120 | 0.055 | 97 |

### destructive_wind

| major flag | events | hits | POD | median lead h |
|---|---|---|---|---|
| major | 1495 | 403 | 0.270 | 19 |
| non-major | 560 | 66 | 0.118 | 21 |

| deaths | events | hits | POD | median lead h |
|---|---|---|---|---|
| 0 | 400 | 4 | 0.010 | 68 |
| 1-9 | 56 | 2 | 0.036 | 29 |
| 10+ | 8 | 0 | 0.000 | - |
| unknown | 1591 | 463 | 0.291 | 20 |

| magnitude bucket | events | hits | POD | median lead h |
|---|---|---|---|---|
| TC Cat1-2 (64-95 kt) | 268 | 62 | 0.231 | 21 |
| TC Cat3+ (>=96 kt) | 1323 | 401 | 0.303 | 19 |
| US wind <65 kt | 190 | 2 | 0.011 | 44 |
| US wind >=65 kt | 61 | 0 | 0.000 | - |
| US wind, gust unknown | 213 | 4 | 0.019 | 54 |

| damage | events | hits | POD | median lead h |
|---|---|---|---|---|
| <$1M | 280 | 4 | 0.014 | 68 |
| $1M-$100M | 12 | 0 | 0.000 | - |
| >$100M | 172 | 2 | 0.012 | 29 |
| unknown | 1591 | 463 | 0.291 | 20 |

### tornado

| major flag | events | hits | POD | median lead h |
|---|---|---|---|---|
| major | 1052 | 104 | 0.099 | 20 |
| non-major | 535 | 32 | 0.060 | 30 |

| deaths | events | hits | POD | median lead h |
|---|---|---|---|---|
| 0 | 1249 | 104 | 0.083 | 22 |
| 1-9 | 306 | 26 | 0.085 | 26 |
| 10+ | 32 | 6 | 0.188 | 16 |

| magnitude bucket | events | hits | POD | median lead h |
|---|---|---|---|---|
| EF unknown | 1 | 0 | 0.000 | - |
| EF0-1 | 212 | 10 | 0.047 | 72 |
| EF2 | 331 | 22 | 0.066 | 14 |
| EF3+ | 1043 | 104 | 0.100 | 20 |

| damage | events | hits | POD | median lead h |
|---|---|---|---|---|
| $0 | 379 | 35 | 0.092 | 12 |
| <$1M | 519 | 37 | 0.071 | 31 |
| $1M-$100M | 633 | 58 | 0.092 | 28 |
| >$100M | 56 | 6 | 0.107 | 10 |

### Named anchor events in dev

Representative anchor rows from `catalog/ANCHORS.md` plus catalog siblings sampled into dev (same class, onset within 2 days, within 3 deg of the representative point).

| anchor | class | sampled rows in dev | outcome |
|---|---|---|---|
| Hurricane Katrina 2005 | destructive_wind | 1 | MISSED 0/1 (insufficient_lead x1) |
| Hurricane Andrew 1992 | destructive_wind | 1 | MISSED 0/1 (no_alarm x1) |
| Hurricane Mitch 1998 | destructive_wind | 1 | MISSED 0/1 (insufficient_lead x1) |
| Hurricane Sandy 2012 | destructive_wind | 1 | MISSED 0/1 (no_alarm x1) |
| Hurricane Harvey 2017 | destructive_wind | 1 | MISSED 0/1 (insufficient_lead x1) |
| Hurricane Irma 2017 | destructive_wind | 1 | MISSED 0/1 (insufficient_lead x1) |
| Hurricane Maria 2017 | destructive_wind | 1 | MISSED 0/1 (insufficient_lead x1) |
| Hurricane Michael 2018 | destructive_wind | 0 | holdout cohort (2018+), not evaluated |
| Hurricane Dorian 2019 | destructive_wind | 0 | holdout cohort (2018+), not evaluated |
| Hurricane Ida 2021 | destructive_wind | 0 | holdout cohort (2018+), not evaluated |
| Hurricane Ian 2022 | destructive_wind | 0 | holdout cohort (2018+), not evaluated |
| Typhoon Haiyan 2013 | destructive_wind | 1 | MISSED 0/1 (no_alarm x1) |
| Cyclone Nargis 2008 | destructive_wind | 1 | MISSED 0/1 (alarm_outside_window x1) |
| Cyclone Idai 2019 | destructive_wind | 0 | holdout cohort (2018+), not evaluated |
| Joplin MO EF5 2011 | tornado | 4 | MISSED 0/4 (no_alarm x3, alarm_outside_window x1) |
| Moore OK EF5 2013 | tornado | 7 | MISSED 0/7 (no_alarm x7) |
| Bridge Creek-Moore OK F5 1999 | tornado | 18 | HIT 3/18 (leads: 11h, 12h, 12h) |
| 2011-04-27 Super Outbreak | tornado | 68 | MISSED 0/68 (no_alarm x67, insufficient_lead x1) |
| Quad-State (Mayfield KY) EF4 2021 | tornado | 0 | holdout cohort (2018+), not evaluated |
| Fort Collins CO flash flood 1997 | flash_flood | 1 | MISSED 0/1 (no_alarm x1) |
| Boulder CO flash flood 2013 | flash_flood | 3 | MISSED 0/3 (no_alarm x3) |
| West Virginia flash flood 2016 | flash_flood | 1 | HIT 1/1 (leads: 44h) |
| Eastern Kentucky flash flood 2022 | flash_flood | 0 | holdout cohort (2018+), not evaluated |
| TS Allison Houston flooding 2001 | flash_flood | 0 | not sampled into dev |
| Texas Hill Country flash flood 2025 | flash_flood | 0 | holdout cohort (2018+), not evaluated |
| June 2012 mid-Atlantic derecho | destructive_wind | 0 | not sampled into dev |
| August 2020 Midwest derecho | destructive_wind | 0 | holdout cohort (2018+), not evaluated |
| Mississippi River Great Flood 1993 | flood | 1 | MISSED 0/1 (no_alarm x1) |
| Yangtze flood 1998 | flood | 1 | MISSED 0/1 (no_alarm x1) |
| Elbe flood 2002 | flood | 1 | MISSED 0/1 (no_alarm x1) |
| Central Europe flood 2013 | flood | 1 | MISSED 0/1 (no_alarm x1) |
| Pakistan floods 2010 | flood | 1 | HIT 1/1 (leads: 135h) |
| Thailand floods 2011 | flood | 1 | MISSED 0/1 (no_alarm x1) |
| Ahr valley flood 2021 | flood | 0 | holdout cohort (2018+), not evaluated |
| Zhengzhou (Henan) flood 2021 | flood | 0 | holdout cohort (2018+), not evaluated |

## 2. POD by region and decade

US events come from NOAA Storm Events (dense, well-timed catalog); non-US flood rows come from DFO (day-precision onsets, country-scale coordinates); IBTrACS cyclones are basin-located (often offshore at the peak-intensity fix). Catalog completeness and onset/location precision therefore differ sharply by region - these splits partly measure the catalog, not only the detector.

### flash_flood

| region | events | hits | POD | median lead h |
|---|---|---|---|---|
| USA (Storm Events) | 1283 | 177 | 0.138 | 37 |
| non-US (DFO) | 189 | 10 | 0.053 | 96 |

| decade | events | hits | POD | median lead h |
|---|---|---|---|---|
| 1990s | 384 | 44 | 0.115 | 32 |
| 2000s | 623 | 78 | 0.125 | 40 |
| 2010s | 465 | 65 | 0.140 | 39 |

### flood

| region | events | hits | POD | median lead h |
|---|---|---|---|---|
| USA (Storm Events) | 334 | 12 | 0.036 | 38 |
| non-US (DFO) | 2095 | 118 | 0.056 | 97 |

| decade | events | hits | POD | median lead h |
|---|---|---|---|---|
| 1980s | 244 | 12 | 0.049 | 67 |
| 1990s | 723 | 41 | 0.057 | 108 |
| 2000s | 933 | 39 | 0.042 | 95 |
| 2010s | 529 | 38 | 0.072 | 86 |

### destructive_wind

| region | events | hits | POD | median lead h |
|---|---|---|---|---|
| TC basins (IBTrACS) | 1591 | 463 | 0.291 | 20 |
| USA (Storm Events) | 464 | 6 | 0.013 | 52 |

| decade | events | hits | POD | median lead h |
|---|---|---|---|---|
| 1950s | 169 | 46 | 0.272 | 20 |
| 1960s | 163 | 53 | 0.325 | 21 |
| 1970s | 179 | 38 | 0.212 | 21 |
| 1980s | 246 | 69 | 0.280 | 21 |
| 1990s | 411 | 91 | 0.221 | 19 |
| 2000s | 511 | 94 | 0.184 | 18 |
| 2010s | 376 | 78 | 0.207 | 20 |

### tornado

| region | events | hits | POD | median lead h |
|---|---|---|---|---|
| USA (Storm Events) | 1587 | 136 | 0.086 | 23 |

| decade | events | hits | POD | median lead h |
|---|---|---|---|---|
| 1990s | 359 | 31 | 0.086 | 19 |
| 2000s | 644 | 60 | 0.093 | 29 |
| 2010s | 584 | 45 | 0.077 | 17 |

## 3. Control-contamination check (post-hoc)

Question: how many "false" alarms fired on control windows whose weather plausibly WAS a real, uncatalogued event? Hazard variable: 24 h precipitation sum (flood classes) / 10 m wind gust (wind classes). For each location we pool the hourly hazard values of all its extracted windows (event + 2 season-matched controls, ~1224 h) and take p99 / p99.9 as that location's own extreme thresholds; `>= event peak` additionally asks whether the weather near the alarm was at least as strong as anything in the cataloged event's own 408 h window at the same location. An alarm counts as contaminated when the hazard reaches the threshold within [fired-24h, last_active+48h].

Note the p99.9 of ~1224 pooled hours is essentially the single most extreme hour among the location's three windows, so `>= p99.9` means the control window contains the most extreme weather ever sampled at that location - strong evidence of an uncatalogued event, given DFO/Storm-Events coverage gaps (esp. outside the US before ~2000).

| class | hazard | false alarms | >=p99 | >=p99.9 | >=event peak | US alarms: >=p99.9 | non-US alarms: >=p99.9 |
|---|---|---|---|---|---|---|---|
| flash_flood | 24h precip | 222 | 42% | 40% | 49% | 40% (n=199) | 39% (n=23) |
| flood | 24h precip | 330 | 67% | 59% | 72% | 100% (n=8) | 58% (n=322) |
| destructive_wind | gust | 250 | 60% | 34% | 37% | 25% (n=8) | 35% (n=242) |
| tornado | gust | 157 | 61% | 31% | 42% | 31% (n=157) | - (n=0) |

**Post-hoc adjusted FAR / budget if contaminated control windows were excluded** (window removed entirely: its alarms from the numerator, its 408 h from the location-years). CLEARLY LABELED POST-HOC - the frozen FAR/budget above remain the metrics of record.

| class | frozen FAR | FAR excl. >=p99.9 | FAR excl. >=event-peak | frozen budget | budget excl. >=p99.9 | budget excl. >=event-peak |
|---|---|---|---|---|---|---|
| flash_flood | 0.306 | 0.203 | 0.179 | 1.62 | 0.96 | 0.83 |
| flood | 0.370 | 0.159 | 0.125 | 1.46 | 0.49 | 0.37 |
| destructive_wind | 0.161 | 0.108 | 0.106 | 1.31 | 0.84 | 0.83 |
| tornado | 0.343 | 0.257 | 0.232 | 1.06 | 0.71 | 0.63 |

## 4. Alarm-budget interpretation note (post-hoc alternative - NOT the frozen metric)

The frozen budget divides false alarms by control location-years, where every control window is a 408 h SEASON-MATCHED window (same calendar dates as a real event, different year). Annualizing those hours (x21.5) therefore implicitly assumes the whole year behaves like the local storm season. That is the conservative upper reading; the frozen number stands as the metric of record. The alternative de-seasonalized reading below assumes a nominal 13-week storm season (5.4 windows/yr) and a climatologically quiet remainder of the year. We cannot measure the quiet-season alarm rate directly (all control windows are in-season by design), but the tuned rules gate on season-typical conditions (moisture anomaly, saturation, instability, deep pressure falls), so the quiet-season rate is bounded between 0 and the in-season rate; the table gives the quiet-season=0 floor - the truth lies between the two columns, and the armed-fraction column shows how rarely controls even reach watch level in season.

| class | false alarms / 408h control window | frozen: /loc-yr (x21.5) | season-only: /yr (x5.4, quiet=0) | control hours at watch+ | at warning+ |
|---|---|---|---|---|---|
| flash_flood | 0.075 | 1.62 | 0.40 | 0.14% | 0.13% |
| flood | 0.068 | 1.46 | 0.36 | 0.40% | 0.39% |
| destructive_wind | 0.061 | 1.31 | 0.33 | 0.20% | 0.19% |
| tornado | 0.049 | 1.06 | 0.26 | 0.06% | 0.05% |

## 5. Synthesis per class (what the frozen operating point actually delivers)

**flash_flood** - At the frozen operating point the detector catches 13% of all sampled flash floods but 17% of major ones (n=183) with median lead 22 h among major hits, at ~0.08 false alarms per 17-day storm-season window (~1 per 13 windows); 40% of those "false" alarms coincide with the most extreme 24 h rainfall sampled at that location, i.e. plausibly real uncatalogued flooding. The severity gradient is real and monotone in damage: POD reaches 0.33 on >$100M events (vs 0.11 on $0 events), with shorter leads on the big ones. The budget-feasible rules are moisture+neighborhood-rain gates that fire on synoptically forced rain; small, convectively driven US flash floods (the catalog majority) mostly present no separable precursor at this point scale, which is why overall POD sits far below the frozen 0.60 bar while major-event POD is materially higher.

**flood** - POD is 5% overall and 6% on major floods (n=2177); when it does hit, lead is long (median 94 h, consistent with multi-day hydrological loading), at ~0.07 false alarms per season window. The class is dominated by non-US DFO rows with day-precision onsets and country-scale centroids, so the extracted point often is not where or exactly when the flood was; the detector's rain-on-saturated-soil gates verify at the grid point, and 59% of its "false" alarms sit on the location's most extreme sampled rainfall. Point-scale detection against this catalog under the frozen 0.65 bar is not close; basin-scale aggregation is the identified next lever.

**destructive_wind** - The strongest class: 23% overall, 27% on major events (n=1495), and the class is really two populations: tropical cyclones (IBTrACS, POD 0.29, rising with Saffir-Simpson category to 0.30 at Cat3+) versus US convective wind reports (POD 0.01 - no synoptic pressure-fall signature at the point scale). Median lead is 20 h at ~0.06 false alarms per season window and the lowest FAR (0.16). 596 of 1586 misses are insufficient-lead cases - an alarm was active but first fired <12 h before onset; the named anchor hurricanes in dev (Katrina, Mitch, Harvey, Irma, Maria) all miss exactly this way, because onset is timed at the peak-intensity fix that the alarm chases. A severity-gated surface (TC Cat1+ focus, watch-tier lead relaxed) is defensible here even though the frozen all-events 0.70 bar fails.

**tornado** - 9% overall against the frozen 0.40 bar, 10% on major (EF2+/killer) rows (n=1052), median lead 23 h, ~0.05 false alarms per season window. The all-required shear+instability+moisture+pressure-fall gate needed to stay inside the budget is much stricter than a real tornado-environment screen; ERA5 point thermodynamics+bulk shear at one grid point identifies favorable ENVIRONMENTS, not touchdowns, so POD on individual catalog rows stays low even for violent tornadoes (EF3+ 0.10 vs EF0-1 0.05, deaths 10+ 0.19 - a real but shallow gradient), and the marquee outbreaks are missed: 0/4 sampled Joplin-day rows, 0/7 Moore 2013, 0/68 rows of the 2011-04-27 Super Outbreak. This class does not support an event-level warning product at the frozen bars; at most a conditions-favorable watch surface.
