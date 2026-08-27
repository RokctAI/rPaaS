# Detection algorithm + backtest harness

Turns mined precursor signatures into per-location, per-class warnings and
grades them against the FROZEN acceptance thresholds in
`research/severe_weather/PLAN.md`. Built so that when signature mining
completes, tuning and the final backtest are fast: everything already runs end
to end on partial data with a placeholder config.

## Modules

| file | role |
|---|---|
| `detector.py` | Core algorithm. Pure-Python forward state machine (no third-party imports in the core loop - intended for later adaptation into the SDK backend). Input: a causal feature series from `mining/features.py` for one location. Per class: threshold conditions with hysteresis (on/off), persistence (must hold N h), weighted score -> confidence 0-1, all-of (`required`) / any-of (`groups`) gating, severity tiers watch < warning < severe with a retention margin, and a post-episode cooldown against alarm flapping. Output: time-indexed (event_class, severity, confidence, first_fired_at) plus discrete alarm episodes that record **which precursors fired** (interpretability). Causal throughout: state at t uses only data <= t. |
| `detector_config.json` | Per-class rule sets. Currently **0.1-placeholder**, drawn from the physics seen so far (partial mining + anchors): pressure-fall + gust trend + TCWV plume for destructive wind; rain-on-saturated-soil + accumulations for floods; a provisional tornado favorable-conditions proxy (gust trend + theta-e surge + veer + moisture - mining will refine it; ERA5 has no CAPE). |
| `backtest.py` | Frozen metric definitions implemented verbatim (see below). Dev cohort runs freely; holdout is single-use and gated. Outputs per-class results (CSV + markdown), an itemized miss list, an itemized false-alarm list, and lead-time distributions. |
| `tune.py` | **Dev-only** parameter search (holdout physically unreachable: all data access goes through `mining/data.py`, whose guard raises on any holdout read). Per class: seeded random search over thresholds / persistence / tier scores / cooldown, maximizing POD subject to FAR <= frozen limit and false-alarm budget <= 2/loc-yr, k-fold by 10-degree location cluster so parameters must generalize across regions. Writes the tuned `detector_config.json` + `tuning_report.md` (every candidate tried, per-fold dev scores). |
| `test_detector.py` | Synthetic-series unit checks: persistence, hysteresis, cooldown, NaN tolerance, gating, causality, config sanity. |
| `test_holdout_gate.py` | Proves every route to the holdout cohort is refused without the explicit flags, and that the single-use marker blocks a second run. |

## Frozen metrics (PLAN.md, frozen 2026-08-19 - implemented in `backtest.py`)

- **Hit**: correct-class warning episode active in `[onset - 7 d, onset]` with at
  least the class minimum lead (flash flood 6 h, flood 24 h, destructive wind
  12 h, tornado 3 h). Lead = hours from the episode's **first firing** to onset.
- **POD** = hits / all sampled events of the class; every miss listed with a
  reason (`no_alarm`, `alarm_outside_window`, `insufficient_lead`).
- **FAR** = false alarms / all alarms; false alarms are warning episodes on the
  matched control series; "all alarms" = those + warning episodes on the event
  series of the same class.
- **False-alarm budget** <= 2 per control location-year. Implemented
  conservatively as ALL warning-or-worse episodes (not only the `severe` tier),
  so the budget cannot be passed on a tier technicality. A cross-class combined
  budget is reported as an informational extra.
- **Lead time**: median per class over hits, with p25/p75/min/max and the full
  per-hit list in `lead_times.csv`.

Frozen targets live in `backtest.FROZEN` and are not to be edited.

## Workflow: tune on dev -> freeze config -> single holdout run

1. **Mining completes** -> update `detector_config.json` conditions to the
   features that actually separate (SIGNATURES.md), keeping placeholders only
   where mining found nothing better.
2. **Tune on dev** (extraction finalized):
   `python3 tune.py` - overwrites `detector_config.json` with the tuned rules
   and writes `tuning_report.md`. Dev-only by construction.
3. **Sanity-check on dev**: `python3 backtest.py --cohort dev` - full dev
   metrics with the tuned config.
4. **Freeze**: record the config SHA-256 (printed in results.md), commit the
   config. No further edits.
5. **Single holdout run** (exactly once, with the frozen config):
   `python3 backtest.py --cohort holdout --holdout --i-understand-single-use`
   This writes `HOLDOUT_RUN_MARKER.json` (tamper-evident: config hash, start /
   finish times, results digest, self-signature) **before** loading any holdout
   data - a crashed run still burns the single use. Any later holdout attempt
   is refused while the marker exists. Results are reported against the frozen
   numbers whether or not they pass.

## Current status (2026-08-19)

- Extraction still in flight; validated end-to-end on partial dev data with the
  placeholder config (see `results_dev/` - labeled PARTIAL/PLACEHOLDER in the
  report). The placeholder rules are far too loose on the false-alarm budget,
  exactly what step 2 exists to fix.
- Remaining dependencies on mining output: final feature choice per class
  (especially tornado), tuned thresholds, and the finalized dev parquet files
  (until then, loading falls back to the extraction cache, which is slower).
