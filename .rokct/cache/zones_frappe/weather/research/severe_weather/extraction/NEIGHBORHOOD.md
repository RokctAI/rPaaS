# Neighborhood-precipitation top-up: displaced-rain features for the flood classes

Follow-up to the anchor validation finding (ANCHOR_VALIDATION.md): for the US
convective / flash-flood anchors the ERA5 precipitation maximum sits a median
~0.6 deg (~60 km, one to three grid cells) from the catalog point — displaced, not
absent (E. Kentucky 2022: 1.6 mm/h at the point vs 8.6 mm/h 0.79 deg away). Point
features therefore systematically miss the causal rain, and detector tuning showed
the point-feature set cannot reach the frozen flood bars. This top-up extracts the
7x7 grid-point neighborhood (+-3 points = +-0.75 deg) of hourly `precipitation`
for every flash_flood and flood series and adds features that let each hour take
the strongest signal anywhere in that neighborhood.

## Extraction

- Coverage: ALL flash_flood + flood series, events and controls, dev AND holdout,
  same aligned 408 h windows as the main extraction (onset -14 d .. +3 d,
  timestamps aligned exactly, including the sub-hour window-label convention).
  14,092/14,092 series extracted, 0 failed: flash_flood dev 4,416 / holdout 1,582;
  flood dev 7,287 / holdout 807. 5,749,536 rows total.
- Chunk-locality batching: the `.om` year files store internal chunks of
  (1 lat, 6 lon, 1095 h) — reading one point already downloads a whole 6-longitude
  chunk row. The unit of work is one `read_array` call covering (up to 7 lats, one
  6-longitude chunk column, one time block), i.e. up to 7 internal chunks per call,
  and units are deduplicated within each batch. Measured cost: 39,275 read calls
  for 14,092 series (2.79 calls/series) — call-count parity with a plain
  single-point extraction of the same windows, ~7x its downloaded chunk volume,
  and far below the ~49x of a naive per-cell extraction.
- Throughput: one Python process caps at ~4.3 multi-chunk reads/s regardless of
  thread count (the sync fsspec bridge serializes), so the run is sharded across
  6 processes x 48 threads: 24 min wall clock end to end. Part files rotate per
  batch (footer written every 400 series), so an interrupted run resumes losing at
  most one batch.
- Output kept separate from the finalized main parquets, one file per
  class/cohort: `series/nbr_precip/<class>_<cohort>_nbr.parquet` (88 MB zstd for
  all four). Wide schema: `series_id`, `time`, and 49 float32 columns `p{r}{c}`
  (r, c in 0..6) = precipitation in mm/h at grid offset (dlat = r-3, dlon = c-3)
  from the series' grid point; r increases northward, c eastward, 0.25 deg per
  step; longitude wraps; off-grid latitudes are NaN. `p33` is the point itself
  (verified byte-identical to the finalized point extraction). Like all extracted
  series, the data files are generated artifacts and are not committed.
- Holdout neighborhood data is extracted and stored only. It was not read by any
  analysis (mining's holdout guard applies; the AUC run loads dev files only and
  re-asserts every loaded series_id is dev).

## Features (`nbr_features.py`)

Causal, same conventions as `mining/features.py`. Rolling accumulations are
computed per cell FIRST, then reduced across cells — `nbr_max_sum_Wh` is the max
over the 49 cells of each cell's OWN W-hour accumulation (the displaced-maximum
reading), not the sum of a per-hour spatial max.

| feature | definition |
|:--|:--|
| `nbr_max_sum_{6,12,24,48,72}h` | max over 7x7 cells of the cell's own W h rain accumulation (mm) |
| `nbr_p90_sum_{6,12,24,48,72}h` | 90th percentile over cells of the same accumulations (robust variant) |
| `nbr_wet_frac` | fraction of cells with precip > 0.1 mm/h now (spatial extent of rain) |
| `nbr_wet_frac_24h` | fraction of cells with > 1 mm rain in the last 24 h |
| `nbr_rain_on_sat_{6,24,72}h` | `nbr_max_sum_Wh` x the POINT's causal soil-moisture percentile (`sm_pct`) |

## AUC by lead, DEV cohorts (rank AUC event vs control; (#) = rank by |AUC-0.5| among all 54 features)

New features in bold; the base top-5 rain-relevant features (by -6 h rank) below
for comparison.

### flash_flood (1,472 events / 2,944 controls)

| feature | -6 h | -24 h | -48 h | -72 h |
|:--|--:|--:|--:|--:|
| **nbr_rain_on_sat_6h** | 0.809 (#1) | 0.666 (#3) | 0.566 (#10) | 0.546 (#12) |
| **nbr_max_sum_6h** | 0.808 (#2) | 0.665 (#4) | 0.565 (#11) | 0.547 (#10) |
| **nbr_p90_sum_6h** | 0.801 (#3) | 0.665 (#5) | 0.563 (#15) | 0.540 (#22) |
| **nbr_max_sum_12h** | 0.800 (#4) | 0.657 (#6) | 0.572 (#6) | 0.551 (#4) |
| **nbr_wet_frac** | 0.797 (#5) | 0.666 (#2) | 0.564 (#14) | 0.535 (#25) |
| **nbr_p90_sum_12h** | 0.796 (#7) | 0.655 (#7) | 0.570 (#8) | 0.547 (#9) |
| **nbr_max_sum_24h** | 0.791 (#8) | 0.648 (#9) | 0.572 (#4) | 0.547 (#11) |
| **nbr_rain_on_sat_24h** | 0.791 (#9) | 0.651 (#8) | 0.573 (#3) | 0.543 (#17) |
| **nbr_p90_sum_24h** | 0.790 (#10) | 0.647 (#10) | 0.571 (#7) | 0.545 (#14) |
| **nbr_wet_frac_24h** | 0.760 (#14) | 0.627 (#19) | 0.559 (#19) | 0.545 (#13) |
| **nbr_max_sum_48h** | 0.754 (#15) | 0.629 (#17) | 0.564 (#13) | 0.543 (#19) |
| **nbr_rain_on_sat_72h** | 0.746 (#19) | 0.625 (#20) | 0.560 (#16) | 0.544 (#15) |
| **nbr_max_sum_72h** | 0.727 (#24) | 0.614 (#25) | 0.558 (#20) | 0.550 (#5) |
| tcwv_anom_7d | 0.796 (#6) | 0.684 (#1) | 0.584 (#1) | 0.549 (#7) |
| rain_on_sat_24h | 0.767 (#11) | 0.630 (#15) | 0.555 (#23) | 0.533 (#29) |
| precip_sum_24h | 0.764 (#12) | 0.629 (#16) | 0.555 (#24) | 0.534 (#26) |
| precip_sum_12h | 0.760 (#13) | 0.634 (#12) | 0.547 (#29) | 0.534 (#28) |
| rain_on_sat_6h | 0.751 (#17) | 0.632 (#14) | 0.541 (#33) | 0.530 (#31) |

(`nbr_p90_sum_48h` 0.754/0.629/0.564/0.543 and `nbr_p90_sum_72h`
0.726/0.614/0.560/0.552 (#3 at -72 h) omitted from the table for brevity.)

### flood (2,429 events / 4,858 controls)

| feature | -6 h | -24 h | -48 h | -72 h |
|:--|--:|--:|--:|--:|
| **nbr_rain_on_sat_6h** | 0.679 (#1) | 0.617 (#4) | 0.572 (#14) | 0.556 (#10) |
| **nbr_p90_sum_6h** | 0.678 (#2) | 0.613 (#7) | 0.566 (#21) | 0.550 (#20) |
| **nbr_max_sum_6h** | 0.674 (#3) | 0.613 (#8) | 0.567 (#20) | 0.553 (#16) |
| **nbr_p90_sum_12h** | 0.674 (#4) | 0.621 (#2) | 0.574 (#8) | 0.554 (#15) |
| **nbr_rain_on_sat_24h** | 0.672 (#5) | 0.617 (#5) | 0.578 (#1) | 0.557 (#8) |
| **nbr_max_sum_12h** | 0.670 (#6) | 0.618 (#3) | 0.573 (#10) | 0.553 (#17) |
| **nbr_p90_sum_24h** | 0.668 (#7) | 0.615 (#6) | 0.577 (#2) | 0.555 (#12) |
| **nbr_wet_frac** | 0.667 (#8) | 0.625 (#1) | 0.568 (#18) | 0.554 (#14) |
| **nbr_max_sum_24h** | 0.663 (#10) | 0.613 (#9) | 0.575 (#5) | 0.554 (#13) |
| **nbr_rain_on_sat_72h** | 0.660 (#11) | 0.608 (#11) | 0.575 (#4) | 0.561 (#3) |
| **nbr_p90_sum_48h** | 0.657 (#16) | 0.608 (#12) | 0.574 (#6) | 0.560 (#5) |
| **nbr_p90_sum_72h** | 0.646 (#20) | 0.601 (#18) | 0.575 (#3) | 0.562 (#1) |
| **nbr_max_sum_72h** | 0.640 (#23) | 0.597 (#21) | 0.571 (#16) | 0.558 (#7) |
| rain_on_sat_24h | 0.664 (#9) | 0.610 (#10) | 0.574 (#9) | 0.551 (#19) |
| precip_sum_12h | 0.659 (#12) | 0.606 (#15) | 0.568 (#19) | 0.545 (#25) |
| rain_on_sat_6h | 0.658 (#13) | 0.595 (#22) | 0.555 (#27) | 0.539 (#29) |
| precip_sum_24h | 0.658 (#14) | 0.607 (#13) | 0.572 (#13) | 0.549 (#21) |
| rain_on_sat_72h | 0.657 (#15) | 0.606 (#14) | 0.574 (#7) | 0.561 (#2) |

(`nbr_wet_frac_24h` 0.636/0.598/0.564/0.551 and `nbr_max_sum_48h`
0.652/0.604/0.571/0.557 omitted for brevity.)

## Verdict

**The displaced-rain lever is material for flash_flood at short leads; for flood
it lifts the -24 h ceiling only modestly (0.610 -> 0.625) — worth taking, but it
does not close the gap on its own.**

- **flash_flood**: the neighborhood features take the top 5 outright at -6 h —
  `nbr_rain_on_sat_6h` 0.809 is the new best feature of the whole library
  (base best: tcwv_anom_7d 0.796; best base rain feature: rain_on_sat_24h 0.767,
  so +0.04 on the rain axis). At -24 h they hold #2-#10 (0.666 vs 0.634 for the
  best point rain feature), with only tcwv_anom_7d (0.684) ahead. This is exactly
  the short-lead end the flash-flood bar (median lead >= 6 h) is graded on —
  **flash-flood tuning should re-run with these features.**
- **flood**: the -24 h ceiling moves 0.610 -> 0.625 (+0.015), and the best new
  feature there is `nbr_wet_frac` — spatial EXTENT, not the displaced max —
  consistent with riverine floods responding to areal rain rather than convective
  cores. At -48/-72 h the lift is within noise (<= +0.004). Displacement is a
  second-order problem for this class; the remaining gap to the frozen flood bar
  (POD >= 0.65 at median lead >= 24 h) is upstream-basin rain and routing lag
  that a +-0.75 deg local window cannot see. **Flood tuning should still re-run
  with the new features (nbr_wet_frac + nbr_p90_sum_12h are cheap real gains),
  but the next flood lever is basin-scale aggregation (upstream accumulation /
  larger asymmetric windows), not a bigger local neighborhood.**
- Redundancy notes for the tuner: `nbr_p90_sum_*` tracks `nbr_max_sum_*` within
  ~0.005 AUC everywhere (a 49-cell field is smooth) — keep one of the two;
  `nbr_wet_frac` carries independent extent information (flood #1 at -24 h);
  the `nbr_rain_on_sat_*` interactions edge out their plain counterparts at most
  leads, mirroring the point-feature result.

All numbers are DEV cohort only; holdout remains untouched for the final backtest.
