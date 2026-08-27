# Pre-registered sampling design for the full ERA5 window extraction

Written and frozen BEFORE the full extraction was run. Rules are implemented
deterministically in `build_manifest.py` (numpy `default_rng(42)`); the realized
counts appear in the tables at the end and in `series/manifest.parquet`.

## (a) Temporal split

- **Development set**: events with onset (catalog `start_utc`) **before 2018-01-01 UTC**.
  Only these series are analyzed during signature mining.
- **Holdout backtest set**: onset **2018-01-01 .. 2025-12-31 UTC**. Extracted
  identically, stored in separate `*_holdout.parquet` files, and **not opened during
  mining** - reserved for the final backtest.
- Controls inherit the cohort of their event regardless of the control year drawn.

## (b) Event sampling per class

Eligibility (all classes): `geo_precision != state_centroid` (+-300 km is useless at
0.25 deg); onset within [1941-01-01, 2025-12-31] so the 14-day precursor window lies
inside the archive; window end before the archive end (~now-5d).

**All `major`-flagged eligible events are included in every class, always.** Where the
majors alone exceed the class target the cohort simply runs over target - majors are
never subsampled. Remaining budget is filled by stratified sampling with strata =
(decade, 10x10-deg geographic cell, season DJF/MAM/JJA/SON, severity tier), allocation
proportional to sqrt(stratum size) (min 1 per non-empty stratum), without replacement,
seed 42. Severity tiers: destructive_wind {major, damage>=$25k or deaths>0, other};
flash_flood/flood {major, deaths>0 or damage>=$1M, other}; tornado {EF>=3, EF2, EF0-1}.

- **destructive_wind, target ~2,000** (realized above target because TC majors alone
  are 1,483): all IBTrACS Cat 3+ and all NOAA wind majors, + stratified IBTrACS
  Cat 1-2 (`magnitude` 64-95 kt) sample of 300, + stratified NOAA High Wind /
  Thunderstorm Wind / Strong Wind / TC-segment events **with damage_usd > 0**
  sample of 400. IBTrACS coordinates are the *peak-intensity fix*; the extraction
  re-anchors each `ib_*` window at the hour of minimum local MSLP inside the storm's
  track period (validated in ANCHOR_VALIDATION.md), and this re-anchored onset also
  defines the control calendar dates.
- **flash_flood, target ~2,000**: all majors + all DFO "Brief torrential rain" events
  (global coverage is scarce and valuable) + stratified NOAA Flash Flood sample to
  ~2,000 total.
- **flood, target ~1,500** (realized ~2,700, see note): **all flood majors are
  included** - the DFO majors alone (severity class 2 or displaced >= 100k, globally)
  plus NOAA damage/deaths majors number 2,351, already above target; + a stratified
  non-major sample of 350 (250 NOAA, 100 DFO) for contrast.
- **tornado, target ~1,500**: the instruction "all EF2+ 1996-2025" (5,209 events)
  contradicts the ~1,500 target, so we pre-register the following resolution keeping
  the target and the severity emphasis: **all EF3+ / major tornadoes** (~1,450) +
  stratified EF2 sample of 450 + stratified EF0-1 sample of 300 (~2,200 total).
  EF2 tornadoes not sampled remain available for a later top-up run via the same
  cache (noted as follow-up).

## (c) Controls

Per sampled event, **2 control windows**: same grid point, same calendar date range
(month-day of the effective onset; Feb 29 maps to Feb 28), in **different randomly
chosen years** drawn uniformly (seed 42) from
[max(1955, event_year - 30), min(2024, event_year + 30)] excluding the event year,
subject to: **no cataloged event of any class within +-10 days of the control window
and within 1.0 deg** (|dlat| <= 1 and |dlon| <= 1 of the event location; the check
uses the full 817k-event catalog, not just the sample). Up to 60 candidate years are
tried per control slot; because the NOAA catalog is dense over the US in summer, a
pre-registered fallback applies when fewer than 2 years pass: the constraint relaxes
to "no same-class event and no major event of any class" in the same box/window, and
the control is flagged `control_quality = "relaxed"` in the manifest (analysis can
filter on it). If even that fails, the slot is left unfilled and logged.

Controls are extracted with the identical variable list, window length (-14 d .. +3 d
around the control pseudo-onset), and storage format as events.

## Extraction window & variables

Window: effective onset - 14 days .. onset + 3 days (408 hourly steps, UTC).
Variables (units as stored): precipitation mm/h; wind_gusts_10m, wind_u/v_component_10m
m/s (+ derived wind_speed_10m); pressure_msl Pa; temperature_2m, dew_point_2m degC;
snowfall_water_equivalent mm/h; soil_moisture_0_to_7cm, _7_to_28cm m3/m3;
total_column_integrated_water_vapour kg/m2; boundary_layer_height m.
Known per-variable coverage gaps (NaN-filled): TCWV & BLH 2024-01-01..2024-06-12;
soil moisture 2023-09-21..2023-12-14.

## Storage format

- `series/<class>_<cohort>.parquet` (cohort in {dev, holdout}; controls live in the
  same file as their events): **long over time, wide over variables** - one row per
  (series_id, hour); columns: `series_id`, `time`, the 12 variables + `wind_speed_10m`
  (float32). Assembled from `series/parts/` written incrementally during the run.
- `series/manifest.parquet`: one row per series - `series_id`, `event_id`, `role`
  (event | control), `event_class`, `cohort`, `lat`, `lon`, grid indices, catalog
  onset, effective (re-anchored) onset, window start/end, `control_year`,
  `control_quality`, and event metadata (source, event_type, magnitude, major,
  geo_precision, country, region, deaths, damage_usd).

## Realized counts

Filled in by `build_manifest.py` (see `manifest_counts.md`); the manifest parquet is
the ground truth.
