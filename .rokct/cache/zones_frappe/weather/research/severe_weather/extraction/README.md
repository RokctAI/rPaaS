# ERA5 extraction pipeline

Pipeline order (all paths relative to this directory):

1. `era5_extract.py` - core extractor module (importable; `python3 era5_extract.py`
   runs the Ida sanity check). On-disk read cache in `cache/`.
2. `validate_anchors.py` + `neighborhood_scan.py` + `make_validation_md.py`
   -> `ANCHOR_VALIDATION.md` (Task 2 outputs; stats CSVs alongside).
3. `SAMPLING.md` - pre-registered design. `anchor_tc.py` (TC min-MSLP re-anchor
   pre-pass -> `tc_anchors.parquet`), then `build_manifest.py`
   -> `series/manifest.parquet` + `manifest_counts.md`.
4. `extract_full.py` - full extraction (background; log: `extract_full.log`).
   Resumable: skips series in `series/state_done.txt`; failures in `series/failed.txt`;
   partial output in `series/parts/`.
5. `finalize_series.py` - merges parts into `series/<class>_<cohort>.parquet`
   (8 files: 4 classes x dev/holdout).

## Checking on / resuming the full extraction

- Progress: `tail -5 extract_full.log` (each line = 200-series batch: cumulative
  count, series/s, var-fetches/s, ETA hours, disk free).
- Done when the log ends with `RUN COMPLETE`; then run `python3 finalize_series.py`.
- If the process died early: `cd extraction && nohup python3 -u extract_full.py >> extract_full.log 2>&1 &`
  - it resumes from `state_done.txt` + cache with no duplicated work (duplicate
  series across runs are dropped at finalize).
- Completion check: `wc -l series/state_done.txt` vs 27,812 manifest series.

## Output format

`series/<class>_<cohort>.parquet`: long over time, wide over variables; one row per
(series_id, hour); 408 rows per series; float32 columns = 12 ERA5 variables (stored
units: see era5_extract.py docstring) + derived `wind_speed_10m`.
`series/manifest.parquet`: series_id -> event/control metadata (see SAMPLING.md).
