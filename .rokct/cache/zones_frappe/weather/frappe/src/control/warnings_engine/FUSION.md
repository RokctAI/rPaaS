# FORECAST FUSION — running the frozen detector over the forecast feed

Status: **wired, default OFF, unvalidated.** No threshold was changed and no
accuracy is claimed until the fire-and-verify ledger below accumulates.

## Why

The observed-basis evaluator is only as current as its archive. The default
ERA5 source (`sources/openmeteo_s3.py`) trails real time by ~2–7 days, which
a live Hawaii test made concrete: the detector fired correctly on Hurricane
Lala from observed data — but the data ended five days back, so the "signal"
was history by the time it existed; Tropical Storm Moke never entered the
archive at all inside the test window. A warning system that is only ever
right in retrospect is not a warning system.

Forecast fusion closes the gap from the other side: the **same frozen
conditions** (`detector_config.json`, sha-verified against
`detector.CONFIG_SHA256` — byte-identical to the research branch's
`detector_config_tuned.json`) are walked causally over a timeline that
extends into the future, so precursor build-up in the forecast can fire a
signal **ahead** of the event.

Naming note: `fusion.py` (wave 2) is a different, older module — it fuses an
*already-fired observed episode* with the platform's cached consumer
forecast to sharpen end-user copy. This document describes the wave-7
forecast-feed **detection** path (`forecast.py` +
`sources/openmeteo_forecast.py`). The two share nothing but the word.

## The wiring

```
sources/openmeteo_forecast.py   OpenMeteoForecastSource — Open-Meteo forecast
                                API (open-meteo.com), one request per point:
                                past_days of model analysis + forecast_days
                                of forecast, hourly, UTC, ERA5 storage units.
                                Used ONLY by the forecast pass; never
                                returned by sources.base.get_data_source().
forecast.py                     run_forecast_pass (hourly, MASTER SWITCH
                                default OFF): per active watch location,
                                fetch 408 h history + next `horizon_hours`
                                (default 72) forecast, compute the identical
                                features (features.py), run the frozen
                                detector (detector.py), record any
                                warning-tier hour AT/AFTER "now" as a
                                Severe Weather Forecast Signal row.
                                verify_forecast_signals (daily): settle open
                                rows against OBSERVED data; file
                                missed_event rows.
Severe Weather Forecast Signal  the ledger doctype (admin-only).
```

Window sizing: the trailing window is the evaluator's own `WINDOW_HOURS`
(408 h) — long enough for the 168 h TCWV baseline (120 h min periods), the
72 h accumulations, the 24 h MSLP tendency, and the expanding causal
soil-moisture percentile (min 48 valid past hours). The source's
`past_days` is computed from that window (17 days for 408 h), `forecast_days`
from the horizon — one API call covers both.

`neighborhood_precipitation()` is implemented here (the point-API stub in
`sources/openmeteo_api.py` deliberately returns None): one multi-location
request with comma-separated latitude/longitude lists covers the 7×7 grid at
0.25° spacing (±0.75°), same cell ordering as the S3 source, so the
flash-flood neighborhood conditions arm on the forecast path.

## Basis tagging — forecast and observed never mix

Every row this path writes carries `basis: "forecast"`, plus
`first_forecast_at`, `lead_hours`, `horizon_hours`, `model`, `source`, and
the frozen config's sha256. Forecast firings:

* live in their **own doctype** — never a Severe Weather Warning record;
* never push, never propagate, never seed advisories, never reach any
  end-user or tenant surface (this PR adds **no** end-user copy at all);
* are invisible to the outcome ledger and the retraining report, which read
  only observed-basis records — so no observed statistic can be inflated or
  polluted by forecast-basis rows, and vice versa.

## The three transfer caveats (why the switch defaults OFF)

The frozen detector was tuned and backtested on ERA5 reanalysis. The
forecast API cannot reproduce ERA5's inputs exactly:

1. **Soil-moisture layers.** ERA5 stores one 0–7 cm layer; the forecast API
   exposes 0–1 / 1–3 / 3–9 cm. We approximate 0–7 cm with a depth-weighted
   mean (weights 1/7, 2/7, 4/7; the 3–9 cm layer stands in for its 3–7 cm
   portion). The engine consumes this only through the causal percentile,
   which absorbs constant bias but not a different dynamic range.
2. **100 m wind.** The forecast API (best_match) provides 80 m and 120 m
   speed/direction, not 100 m u/v. We convert to u/v per level and take the
   80/120 mean (linear interpolation lands on 100 m); an hour missing either
   level yields NaN, which de-arms rather than guesses. The tornado
   bulk-shear feature built on this is the **least validated** transfer.
   10 m u/v are likewise derived from speed/direction.
3. **Forecast error vs reanalysis-tuned thresholds.** Beyond variable
   plumbing, forecast fields carry model error that grows with lead time,
   and the "past_days" portion of the timeline is the forecast model's own
   analysis, not ERA5. Thresholds tuned on reanalysis may sit differently on
   this distribution — in either direction. Nobody has measured it for this
   detector yet; that is exactly what the ledger exists to measure.
   (Related: the neighborhood cells are point samples interpolated from the
   forecast model's grid, not true 0.25° cell means.)

Because of these, `severe_weather_forecast_detection` defaults **OFF** and
only an explicit truthy value enables it — consistent with how this SDK
gates every unvalidated behavior. Nothing else in the engine changes when
it is off: the pass returns before any fetch.

## Fire-and-verify ledger — honesty before claims

Every firing is recorded and later confronted with what actually happened:

* **hit** — the daily pass, once the *observed* configured source (ERA5 by
  default) has data past the predicted window
  (`first_forecast_at` + per-class validity + 48 h aftermath), finds that
  extremes materialized. Judged with the outcome ledger's own machinery
  (`outcomes.observed_peaks` / `episode_verdict`, climatology percentile
  included) — the forecast path is held to exactly the observed bar, no new
  thresholds.
* **false_alarm** — the window elapsed and nothing extreme followed.
* **missed_event** — an observed-basis warning-tier episode fired with no
  forecast signal issued before its onset predicting within ±48 h of it.
* Data gaps are never judged; the row stays open and is retried. A later
  forecast run that stops showing the event refreshes the row (peaks are
  high-water marks) but never deletes it — a weakening forecast cannot
  erase the original claim.
* Settling always runs while open rows exist, even if the operator turns
  the switch off afterwards; firing and miss accounting require the switch
  (with the pass off, "we never predicted it" reflects configuration, not
  skill).

Per-class hit / false-alarm / miss counts over these rows mirror the
retraining report's shape and are the *only* basis on which forecast-path
accuracy may ever be claimed. Until they exist in meaningful numbers, the
honest statement is: **the wiring works; the skill is unmeasured.**

## What was deliberately not done

* No detector threshold, weight, gate, persistence, or cooldown changed —
  `detector_config.json` remains byte-identical (sha-verified at load).
* No end-user surface: no copy, no severity, no push, no tenant API change
  (the SAWS wording constraints in `messages.py` are untouched).
* No fallback of the observed evaluator onto forecast data — the source
  factory (`sources/base.py`) cannot return the forecast source.
* No automatic enabling, tuning, or feedback: the ledger is write-only
  evidence for humans, exactly like the outcome ledger.
