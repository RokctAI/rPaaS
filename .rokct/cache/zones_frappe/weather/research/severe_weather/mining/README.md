# Precursor-signature mining framework

Mines event-vs-control precursor signatures from the ERA5 windows extracted under
`../extraction/` (see `SAMPLING.md` there for the pre-registered design). Operates on
the **dev cohort only** - the holdout cohort (onset 2018+) is refused at the data
layer (`data.py`, `HoldoutAccessError`) and is reserved for the final backtest
against the frozen thresholds in the repo plan.

## Modules

| file | role |
|---|---|
| `data.py` | dev-only loader + **holdout guard**. Sources: finalized `<class>_dev.parquet` > readable part files > reconstruction from the extraction read-cache (`state_done.txt`), so mining runs on partial data while the extraction is in flight. |
| `features.py` | 39 causal candidate features per hourly window: rainfall accumulations (3-72 h), antecedent precipitation index, wet-spell stats, soil-moisture level/7-day delta/causal percentile/saturation ratio, MSLP + 3/6/24 h tendencies (Pa converted to hPa), gust and wind levels/trends, gust-factor + directional-veer shear proxies, dew-point depression, theta-e proxy, TCWV + 7-day anomaly, BLH, snowmelt proxy, rain-on-saturated-soil interactions. Everything is right-aligned/backward-looking (causal at every t); NaN gaps degrade to NaN via min_periods. |
| `composites.py` | onset-aligned median+IQR composite curves (3-hourly grid, -336..+69 h) and per-lead discriminative power: rank AUC, Cliff's delta, robust d. |
| `mine.py` | harness: load -> features -> composites + AUC tables -> `results/` (parquet/CSV + `run_meta.json` with a `partial` flag). |
| `report.py` | renders `SIGNATURES.md` (+ composite PNGs under `results/plots/`) from `results/`. |
| `check_anchors.py` | feature spot-check on 3 named anchors (Katrina 2005, Elbe 2002, Ahr 2021) via direct extraction - machinery validation, not mining. |
| `test_holdout_guard.py` | proves every route to holdout data is refused. |

## Data prerequisites (not committed)

All paths in this package are relative to this directory. The inputs it reads —
`../extraction/series/` (manifest, finalized/part parquets, `state_done.txt`) and
`../extraction/cache/` (the extractor's read-cache) — are **generated data produced by
running the extraction pipeline** (`../extraction/era5_extract.py` per `SAMPLING.md`) and
are not committed to the repo. Likewise everything this package writes (`results/`,
`SIGNATURES.md`, plots) is generated output and stays uncommitted until results are
reviewed. Fresh checkouts must run the extraction first; until then `mine.py` fails
fast on the missing manifest.

## Run

```bash
python3 test_holdout_guard.py        # guard must pass before anything else
python3 mine.py                      # all classes; add --max-events N for a quick pass
python3 report.py                    # writes SIGNATURES.md
python3 check_anchors.py             # feature physics spot-check
```

## When the extraction completes (~8 h run)

1. `python3 ../extraction/finalize_series.py` - merges parts into
   `series/<class>_dev.parquet` (+ holdout files, which mining never opens).
   Note: part files from a run that was restarted mid-flight never get a parquet
   footer; `data.py` skips them and reconstructs those series from the cache, so
   nothing is lost either way.
2. `python3 mine.py && python3 report.py` - full-dev-cohort results;
   `run_meta.json.partial` flips to false and the PARTIAL banner disappears.

## Known limitations / follow-ups

- No 100 m wind in the extracted variable set, so the |V100-V10| shear proxy is
  substituted by gust-factor and 10 m directional veer; a 100 m top-up extraction
  would enable the real thing (matters most for tornado/derecho environments).
- Single-point features only; ANCHOR_VALIDATION.md shows convective classes are
  displaced by ~0.25-1 deg, so neighborhood-max features (+-2 cells) are the next
  step if point AUCs underwhelm for flash_flood/tornado.
- `sm_pct` / `sm_sat_ratio` are percentiles of the series' own 14-day history, not a
  long-term climatology; a per-gridpoint climatological percentile would sharpen the
  saturation signal.
