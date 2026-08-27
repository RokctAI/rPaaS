# Working plan — severe-weather early warnings

Status: research phase. This plan is the working document; everything except the
**Acceptance thresholds** section may evolve. The thresholds are frozen (see below) and were
committed before any signature mining or tuning began, so results cannot be graded on a curve.

## 1. Data source

**Primary: the Open-Meteo AWS Open Data bucket, `s3://openmeteo`** (CC-BY-4.0; attribution:
"Weather data by Open-Meteo.com"). Anonymous access, no egress cost to us, no API rate limits.

- `data/copernicus_era5/` — 0.25 deg global, hourly, 1940 → now-5days. Variables of interest:
  `precipitation`, `pressure_msl`, `wind_gusts_10m`, `wind_u/v_component_10m`,
  `temperature_2m`, `dew_point_2m`, `soil_moisture_0_to_7cm` (+ deeper layers),
  `snowfall_water_equivalent`, `total_column_integrated_water_vapour`,
  `boundary_layer_height`. **ERA5 has no CAPE** — convective potential must be proxied from
  these fields (e.g. dew-point depression, low-level moisture, pressure tendencies).
- `data/copernicus_era5_land/` (0.1 deg) for finer soil moisture/temperature where useful.
- CAPE / lifted index exist only in the historical-forecast archives (`ncep_gfs025` etc.,
  roughly the last 2–4 years) — usable for validation of the tornado proxy, not for the
  50-year record.

**Access pattern: per-point time-series mining via `omfiles` + `s3fs` (anonymous), with
ranged reads.** Verified end-to-end (see `RECON_DATA.md`): one point-year-variable read is
~11 HTTP GETs / ~15 kB; a 50-year, 7-variable single-point series is ~5–6 MB transferred.
This is latency-bound and embarrassingly parallel — open each (variable, year) file once and
read many event locations from it; nearby locations share internal chunks. **No bulk mirror
of the archive is needed.** Regional field cutouts (~37 MB per CONUS variable-year) are the
fallback only if spatial-context features prove necessary.

Grid/join discipline: `lat_idx = (lat + 90) / 0.25` (index 0 = 90S),
`lon_idx = (lon + 180) / 0.25` (index 0 = 180W); snap event coordinates with
`round(x / 0.25) * 0.25`; all timestamps in UTC.

## 2. Ground-truth event catalogs

1. **NOAA Storm Events, 1996+** (US core; minute-precision local times, point lat/lon for
   convective events, county/zone for many floods): classes `Flash Flood`, `Flood`,
   `Tornado`, `High Wind` / `Thunderstorm Wind` (magnitude >= 50 kt for the destructive-wind
   class). 1996+ is when all 48 event types are reported; 1955–1995 tornado/wind/hail is a
   secondary extended-history set. Convert local times to UTC via `CZ_TIMEZONE`; map
   zone-only events to county centroids (treat as ±25 km).
2. **DFO Global Flood Archive, 1985–2021** (global floods; event centroid lat/lon, day-precision
   begin/end, severity/dead/displaced): complements NOAA with 100+ countries.
3. **IBTrACS** (global tropical-cyclone best tracks, 3–6-hourly position + intensity): derive
   gale-radius-passage labels for the destructive-wind class at coastal locations.
4. Skipped for now: EM-DAT and ESWD (registration-gated; EM-DAT also lacks precise
   coordinates/times). Revisit ESWD if European tornado/flash-flood validation is wanted.

**Event catalog — done.** Built and committed under `catalog/`: `events.parquet` holds
817,216 normalized, QC'd events — 806,675 from NOAA Storm Events (1996–Sep 2025), 4,902 from
the DFO Flood Archive (1985–Oct 2021), 5,639 tropical cyclones from IBTrACS (1950–Jun 2024) —
split into 109,998 flash floods, 78,633 floods, 586,122 destructive-wind events, and 42,463
tornadoes, with 5,708 flagged `major` and all 35 named anchor events verified present
(`catalog/ANCHORS.md`). Schema, source mirrors, licensing, and QC decisions (UTC conversion,
coordinate fallbacks with a `geo_precision` flag, cross-source dedup, damage-string parsing)
are documented in `catalog/CATALOG.md`; `catalog/build_catalog.py` reproduces the parquet
from public URLs end to end.

## 3. Mining approach

Per event class (flash flood, riverine/areal flood, destructive wind, tornado):

1. **Event set**: sample cataloged events; snap each to its nearest ERA5 grid point; extract
   the precursor window T-14d → T+2d, hourly, for all candidate variables.
2. **Matched non-event controls**: for each event, draw control windows from the *same
   location* and *same season* in years with no cataloged event of that class within a
   guard interval — so the contrast isolates event precursors, not climatology or geography.
3. **Event-relative composites**: superpose event windows aligned on onset; contrast
   composite trajectories and distributions (levels, tendencies, accumulations, e.g.
   antecedent soil moisture + rainfall accumulation for floods; pressure-fall rate + gust
   trajectory for wind; low-level moisture/shear proxies for tornado conditions) against the
   control distribution. Keep only features with real separability.
4. Explicitly record negative results — features that do NOT separate — to prevent
   re-derivation churn later.

## 4. Detection algorithm

Turn the separable features into a per-location, per-class detector that runs on a short
rolling window of recent hourly data (the same features, computable from ERA5-equivalent
live inputs). Constraints, in order: interpretability (a warning must state which precursors
fired), calibration (score maps to a probability-like level), and cheapness (must run inside
a Frappe scheduled job per location without meaningful cost). Model class is an open choice
(thresholded composite indices → logistic/GBM on window features), decided by backtest
performance against the frozen thresholds — not the other way around.

## 5. Backtest

- Strict temporal holdout: tune on one era, accept on a held-out era (and held-out regions
  for the global classes). No threshold or feature changes after seeing held-out results.
- Evaluation follows the metric definitions in the frozen section below: (event, location)
  pairs, nearest-grid-point detection, 7-day pre-onset hit window, FAR on matched controls,
  false-alarm budget per location-year, per-class median lead time.
- Report per-class results against the frozen numbers whether or not they pass, with
  itemized misses and false alarms.

## 6. SDK integration arc (after acceptance only)

Additive changes only, per the repo invariants documented in `RECON_REPO.md`:

1. **Backend**: new `weather/frappe/src/weather/<endpoint>/` function decorated
   `@frappe.whitelist()` (note: the two existing weather endpoints lack the decorator — do
   not copy that omission), plus a scheduler function; register both in
   `weather/frappe/manifest.json` under `hooks.whitelisted_methods` and
   `hooks.scheduler_events`. Merge to main activates it at next compose — the module is
   already in the `rcore` and `deliveryplatform` composer templates, so jobs must be
   idempotent and cheap (they run on both shell products).
2. **Client**: additive weather_sdk surface (new cmd via the platform gateway envelope),
   `weather/dart/manifest.json` version bump in the same commit, and create the missing
   `weather/dart/CHANGELOG.md`.
3. Only `base_sdk` imports (ADR-005); no breaking changes — shells compose at `ref: main`.

---

## Progress

- 2026-08-19: Extraction pipeline validated on 35 anchors; sampling pre-registered: dev < 2018-01-01, holdout 2018+; 9,272 events + 18,540 controls. See `extraction/`.
- 2026-08-19: Mining framework built (`mining/`); holdout guard tested; partial-data validation shows expected physics (rain/soil features lead floods, pressure falls lead wind events).
- 2026-08-19: Detector state machine, frozen-metric backtest harness, and dev-only tuner built; single-use holdout gate tested. See `detector/`.
- 2026-08-19: Full extraction complete (27,812 series, 0 failed); dev-cohort mining done — signatures in `mining/results/SIGNATURES.md`.
- 2026-08-19: Detector tuned on dev (structure from mined signatures incl. w100 bulk-shear + neighborhood-precip top-ups; seeded search, 5-fold by location cluster, constraints never relaxed) — FAR/budget/lead bars met for all classes, POD bars missed everywhere (wind 0.23 vs 0.70, flash flood 0.13 vs 0.60, tornado 0.09 vs 0.40, flood 0.05 vs 0.65); the ≤2 warnings/loc-yr budget on matched controls is the binding constraint. Config + full analysis in `detector/detector_config_tuned.json` + `detector/tuning_report.md`; holdout untouched.

---

## Acceptance thresholds (frozen 2026-08-19, before any signature mining or tuning)

Metric definitions:
- Evaluation unit: (event, location) pairs from the ground-truth catalog, detection run on the ERA5 grid point nearest the event coordinates.
- Hit: a warning of the correct event class active in the window from 7 days before event onset up to onset, with at least the minimum lead time.
- Hit rate (POD) = hits / all sampled cataloged events of that class, misses reported individually.
- False-alarm rate (FAR) = false alarms / all alarms, measured on matched non-event control periods drawn from the same locations and seasons.
- False-alarm budget: at most 2 severe warnings per location-year on control (non-event) data.
- Lead time: hours from first firing of the warning to event onset; median reported per class.

Per-class thresholds (algorithm accepted only if ALL are met on the held-out backtest, without moving these numbers):
- Flash flood: POD >= 0.60, FAR <= 0.60, median lead >= 6 h.
- Riverine/areal flood: POD >= 0.65, FAR <= 0.50, median lead >= 24 h.
- Destructive wind (incl. tropical-cyclone landfall): POD >= 0.70, FAR <= 0.40, median lead >= 12 h.
- Tornado (favorable-conditions proxy; ERA5 has no CAPE): POD >= 0.40, FAR <= 0.75, median lead >= 3 h.

Results are reported against these numbers whether or not they are met. Misses and false alarms are listed, not summarized away.
