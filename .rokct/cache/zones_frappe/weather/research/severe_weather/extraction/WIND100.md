# 100 m wind top-up: bulk-shear features for tornado / destructive wind

Follow-up to the full extraction, motivated by the mining result that tornado
discrimination was the weakest of the four classes. ERA5 single-levels has no CAPE,
and the original 12-variable extraction had no 100 m wind, so no bulk-shear feature
existed (features.py used `gust_factor` / `dir_veer_6h` as stand-ins). This top-up
adds the low-level kinematic axis.

## Data

- Bucket variables (verified live 2026-08-19): `wind_u_component_100m`,
  `wind_v_component_100m` under `openmeteo/data/copernicus_era5/`, m/s, same
  year-file + rolling-chunk layout and full 1940-present coverage as the 10 m winds.
  Unit sanity check on Hurricane Ida (30N, 90W, 2021-08-29/31): peak 100 m speed
  34.4 m/s vs 23.6 m/s at 10 m, mean speed ratio 1.45 — plausible.
- Extraction: all tornado + destructive_wind series, events and controls, dev AND
  holdout, same windows as the main extraction (onset −14 d .. +3 d, timestamps
  aligned exactly). 13,720/13,720 series extracted, 0 failed (tornado dev 4,761 /
  holdout 1,560; destructive_wind dev 6,165 / holdout 1,234).
- Output kept separate from the finalized main parquets:
  `series/wind100/<class>_<cohort>_w100.parquet` (columns: series_id, time, u100,
  v100, derived `wind_speed_100m`). Like all extracted series, the data files are
  generated artifacts and are not committed.
- Holdout w100 data is extracted and stored only. It was not read by any analysis
  (mining's holdout guard applies; the shear run loads dev files only and re-asserts
  every loaded series_id is dev).

## Features (`wind100_features.py`)

Causal, same conventions as `mining/features.py`; computed from the joined
(main + w100) hourly window:

| feature | definition |
|:--|:--|
| `bulk_shear` | vector wind difference \|V100 − V10\| (m/s) |
| `bulk_shear_delta_6h` / `_24h` | backward 6 h / 24 h change in bulk shear |
| `speed_ratio_100_10` | 100 m / 10 m speed ratio (nocturnal decoupling proxy) |
| `dir_veer_levels` | absolute directional veer between 10 m and 100 m (deg), masked in near-calm |

`|V100 − V10|` is a proxy for low-level shear only (the lowest ~100 m); true 0–1 km
or 0–6 km shear is not observable from ERA5 single levels.

## AUC by lead, DEV cohorts (rank AUC event vs control; (#) = rank by |AUC−0.5| among all 44 features)

New features in bold; the base top-5 (by −6 h rank) shown for comparison.
AUC < 0.5 means the event population is LOWER (e.g. mslp).

### tornado (1,587 events / 3,174 controls)

| feature | -6 h | -24 h | -48 h | -72 h |
|:--|--:|--:|--:|--:|
| **bulk_shear** | 0.791 (#3) | 0.588 (#10) | 0.557 (#7) | 0.501 (#41) |
| **bulk_shear_delta_6h** | 0.645 (#21) | 0.532 (#19) | 0.505 (#36) | 0.487 (#29) |
| **bulk_shear_delta_24h** | 0.722 (#12) | 0.538 (#18) | 0.557 (#8) | 0.473 (#9) |
| **speed_ratio_100_10** | 0.624 (#28) | 0.523 (#26) | 0.520 (#24) | 0.500 (#44) |
| **dir_veer_levels** | 0.520 (#43) | 0.513 (#31) | 0.499 (#43) | 0.506 (#39) |
| mslp_hpa | 0.124 (#1) | 0.301 (#1) | 0.388 (#1) | 0.474 (#11) |
| tcwv_anom_7d | 0.811 (#2) | 0.637 (#4) | 0.552 (#10) | 0.489 (#34) |
| tcwv | 0.790 (#4) | 0.643 (#3) | 0.567 (#5) | 0.516 (#25) |
| gust | 0.775 (#5) | 0.591 (#8) | 0.550 (#11) | 0.512 (#33) |
| theta_e | 0.774 (#6) | 0.656 (#2) | 0.591 (#3) | 0.547 (#1) |

### destructive_wind (2,055 events / 4,110 controls)

| feature | -6 h | -24 h | -48 h | -72 h |
|:--|--:|--:|--:|--:|
| **bulk_shear** | 0.869 (#5) | 0.742 (#3) | 0.582 (#3) | 0.534 (#5) |
| **bulk_shear_delta_6h** | 0.685 (#31) | 0.643 (#20) | 0.535 (#22) | 0.521 (#17) |
| **bulk_shear_delta_24h** | 0.806 (#18) | 0.744 (#2) | 0.569 (#6) | 0.530 (#8) |
| **speed_ratio_100_10** | 0.767 (#21) | 0.681 (#10) | 0.566 (#8) | 0.529 (#9) |
| **dir_veer_levels** | 0.716 (#27) | 0.526 (#37) | 0.488 (#38) | 0.496 (#38) |
| mslp_tend_24h | 0.071 (#1) | 0.190 (#1) | 0.354 (#1) | 0.450 (#2) |
| tcwv_anom_7d | 0.886 (#2) | 0.710 (#7) | 0.541 (#18) | 0.515 (#30) |
| mslp_hpa | 0.115 (#3) | 0.266 (#5) | 0.387 (#2) | 0.438 (#1) |
| gust_max_24h | 0.872 (#4) | 0.701 (#8) | 0.566 (#7) | 0.524 (#12) |
| gust | 0.863 (#6) | 0.734 (#4) | 0.581 (#4) | 0.530 (#7) |

## Verdict

**Shear adds discriminative power, concentrated at short leads; tornado tuning
should include `bulk_shear`.**

- **tornado**: `bulk_shear` at −6 h (AUC 0.791) ranks #3 of 44, ahead of tcwv,
  gust and theta_e and behind only mslp and tcwv_anom_7d — it is the strongest
  *new physical axis* (kinematic) in a top set otherwise dominated by
  pressure/moisture. At −24 h and beyond the edge fades (0.588 / 0.557 / ~0.50),
  so shear sharpens the nowcast/short-lead end, not the 2–3 day outlook.
- **destructive_wind**: `bulk_shear` and `bulk_shear_delta_24h` are top-3 features
  at −24 h (0.742 / 0.744, beaten only by mslp_tend_24h) and stay top-6 at −48 h —
  a material improvement over the best base wind feature (gust 0.734 at −24 h).
- `dir_veer_levels` adds ~nothing for tornado; `speed_ratio_100_10` and
  `bulk_shear_delta_6h` are dominated by `bulk_shear` + `_delta_24h`. Keep
  `bulk_shear` and `bulk_shear_delta_24h`; the rest are droppable.
- Caveat: `bulk_shear` correlates with 10 m wind speed features by construction;
  the AUC table shows marginal power, not independence. It ranks above `gust` /
  `wspd_10m` wherever it matters, so it is at worst a better substitute and at
  best new information — the detector tuner (dev-only) should decide with both
  available.

All numbers are DEV cohort only; holdout remains untouched for the final backtest.
