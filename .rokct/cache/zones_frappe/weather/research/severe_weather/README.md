# Severe-weather early-warning research

This directory holds the research track for adding **severe-weather early warnings** to the
weather module: warnings for **floods, destructive wind (including tropical-cyclone landfall),
and tornado-favorable conditions**, learned from the full ERA5 historical record rather than
hand-picked meteorological rules.

## Goal

Given only a location (the same lat/lng the weather SDK already has for a shop), detect —
hours to days ahead — that conditions match the historical precursor signatures of damaging
events at comparable locations, and surface a warning through the existing weather pipeline.

The approach: mine ~50 years of hourly ERA5 reanalysis (via the Open-Meteo AWS Open Data
bucket) around thousands of cataloged real events (NOAA Storm Events, DFO Flood Archive,
IBTrACS), build event-relative composite signatures per event class, contrast them against
matched non-event controls, then turn the separable signal into a detection algorithm that is
backtested against **acceptance thresholds frozen before any tuning** (see `PLAN.md`).

This directory is **documentation and research only** — nothing here is composed into any
app shell. The composer references this module by the explicit paths `weather/frappe` and
`weather/dart`, and the SDK validator only discovers `dart/manifest.json` files, so
`weather/research/` is inert with respect to all tooling. SDK integration happens later as a
separate, additive change to `weather/frappe` + `weather/dart` per the plan.

## Data licensing

Weather data by [Open-Meteo.com](https://open-meteo.com/), CC-BY-4.0
(`s3://openmeteo`, AWS Open Data). NOAA Storm Events and IBTrACS are US-government open data;
the DFO Global Flood Archive is openly published by the Dartmouth Flood Observatory.

## Index

| File | Contents |
|---|---|
| `README.md` | This orientation page. |
| `PLAN.md` | Working plan: data sources, ground-truth catalogs, mining approach, detection algorithm, backtest design, SDK integration arc — and the **frozen acceptance thresholds**. |
| `RECON_REPO.md` | Repository recon: how the weather module composes into shells (gateway cmd flow, frappe manifest schema, scheduler events, validator/compliance rules, versioning), with file:line citations. |
| `RECON_DATA.md` | Data recon: the `s3://openmeteo` bucket layout, `.om` file format, a verified end-to-end Hurricane Ida decode, measured per-point transfer costs, and the event-catalog survey. |
| `INTEGRATION_DESIGN.md` | SDK integration design (design doc only, no feature code): scheduled evaluator + `tenant.api.get_weather_warnings` cmd, data-source abstraction (S3 bucket vs commercial API), doctypes, end-user copy, admin telemetry, backward-compat rules, and the activating-PR rollout sequence. |
| `catalog/` | The ground-truth event catalog: `events.parquet` (817,216 normalized events from NOAA Storm Events, the DFO Flood Archive, and IBTrACS), `events_sample.csv`, the reproducible `build_catalog.py`, `CATALOG.md` (schema, sources, QC decisions), and `ANCHORS.md` (35 verified anchor events). |
| `extraction/` | ERA5 extraction pipeline: `era5_extract.py` (core extractor), `ANCHOR_VALIDATION.md` + stats CSVs (35-anchor validation), `SAMPLING.md` (pre-registered sampling design: dev/holdout split at 2018-01-01, 9,272 events + 18,540 matched controls), `manifest_counts.md`, and `finalize_series.py`. |
| `mining/` | Precursor signature-mining framework (dev cohort only): `data.py` (loader with hard holdout guard), `features.py` (39 causal candidate features), `composites.py` (onset-aligned composites + AUC/Cliff's-delta by lead), `mine.py` / `report.py` (harness + SIGNATURES.md renderer), `check_anchors.py` (anchor spot-check), `test_holdout_guard.py`. Operates on the uncommitted extraction workspace; see its README. |
| `detector/` | Detection algorithm + backtest harness: `detector.py` (per-class hysteresis state machine), `detector_config.json` (placeholder rules, pre-tuning), `backtest.py` (frozen PLAN.md metrics: POD/FAR/lead, single-use holdout gate), `tune.py` (dev-cohort-only random search with k-fold CV), `test_detector.py`, `test_holdout_gate.py`. Operates on the uncommitted extraction workspace; see its README. |
