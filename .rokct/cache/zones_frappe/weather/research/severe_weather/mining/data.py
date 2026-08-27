"""Data access layer for precursor-signature mining - DEV COHORT ONLY.

HOLDOUT GUARD (hard rule, pre-registered in extraction/SAMPLING.md): series with
cohort == "holdout" (event onset 2018-01-01 or later) are reserved for the final
backtest and MUST NOT be read during mining. This module is the only sanctioned way
for mining/analysis code to reach the extracted series, and it enforces the rule:

  * `load_manifest()` returns dev rows only; holdout rows are dropped before return.
  * `load_series()` refuses any cohort other than "dev" (HoldoutAccessError), refuses
    explicit series_ids that map to holdout, never opens `*_holdout*` parquet files,
    and post-asserts that every series it returns is a dev series.

Sources, in priority order (deduplicated by series_id):
  1. finalized `extraction/series/<class>_dev.parquet` (exists after finalize_series.py)
  2. readable part files `extraction/series/parts/<class>_dev.*.parquet`
     (parts being written by a live extraction run have no footer yet and are skipped)
  3. reconstruction from the extraction read-cache (`extraction/cache/*.npy`) for series
     listed in `series/state_done.txt` - this is how mining runs on partial data while
     the extraction is still in flight. Completed series are fully cached, so this path
     is local-disk only (era5_extract would fall through to S3 only for a series whose
     cache was manually deleted).
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACTION_DIR = os.path.normpath(os.path.join(HERE, "..", "extraction"))
SERIES_DIR = os.path.join(EXTRACTION_DIR, "series")
PARTS_DIR = os.path.join(SERIES_DIR, "parts")
STATE_DONE = os.path.join(SERIES_DIR, "state_done.txt")
MANIFEST = os.path.join(SERIES_DIR, "manifest.parquet")

CLASSES = ["flash_flood", "flood", "destructive_wind", "tornado"]
WINDOW_HOURS = 408          # onset-14d .. onset+3d, hourly
ONSET_INDEX = 336           # row index of onset_eff within a complete window
VALUE_COLUMNS = [
    "precipitation", "wind_gusts_10m", "wind_u_component_10m", "wind_v_component_10m",
    "pressure_msl", "temperature_2m", "dew_point_2m", "snowfall_water_equivalent",
    "soil_moisture_0_to_7cm", "soil_moisture_7_to_28cm",
    "total_column_integrated_water_vapour", "boundary_layer_height", "wind_speed_10m",
]


class HoldoutAccessError(RuntimeError):
    """Raised on any attempt to read holdout-cohort series during mining."""


_manifest_raw_cache: pd.DataFrame | None = None


def _read_manifest_raw() -> pd.DataFrame:
    """Full manifest incl. holdout METADATA (never series values).

    Private on purpose: mining code must use load_manifest(). The raw frame exists
    so the guard can recognize holdout series_ids in order to refuse them, and so
    the guard test can pick a holdout id to prove refusal.
    """
    global _manifest_raw_cache
    if _manifest_raw_cache is None:
        _manifest_raw_cache = pd.read_parquet(MANIFEST)
    return _manifest_raw_cache


def load_manifest() -> pd.DataFrame:
    """Series manifest restricted to the dev cohort (the only cohort mining may see)."""
    raw = _read_manifest_raw()
    dev = raw[raw["cohort"] == "dev"].copy()
    # Belt and braces: the cohort column is the split of record, but re-check onsets.
    if (dev["onset_catalog"] >= pd.Timestamp("2018-01-01")).any():
        raise HoldoutAccessError("manifest dev rows contain post-2018 onsets - split is corrupt")
    if len(dev) == 0:
        raise RuntimeError(f"no dev rows in manifest {MANIFEST}")
    return dev


def _holdout_ids() -> set:
    raw = _read_manifest_raw()
    return set(raw.loc[raw["cohort"] != "dev", "series_id"])


def done_series_ids() -> set:
    """series_ids already fully extracted (all cohorts - filter before use)."""
    if not os.path.exists(STATE_DONE):
        return set()
    with open(STATE_DONE) as f:
        return {line.strip() for line in f if line.strip()}


def _assert_dev_only(series_ids, context: str) -> None:
    bad = set(series_ids) & _holdout_ids()
    if bad:
        raise HoldoutAccessError(
            f"HOLDOUT GUARD: refusing to touch {len(bad)} holdout series in {context} "
            f"(e.g. {sorted(bad)[:3]}). Holdout (2018+) is reserved for the final backtest.")


def _readable_parquets(event_class: str) -> list[str]:
    """Finalized + readable part files for <class>_dev, never any holdout file."""
    paths = []
    fin = os.path.join(SERIES_DIR, f"{event_class}_dev.parquet")
    if os.path.exists(fin):
        paths.append(fin)
    paths.extend(sorted(glob.glob(os.path.join(PARTS_DIR, f"{event_class}_dev.*.parquet"))))
    ok = []
    for p in paths:
        if "holdout" in os.path.basename(p):  # paranoia; the glob already excludes it
            continue
        try:
            pq.ParquetFile(p)  # a part file still being written has no footer -> raises
            ok.append(p)
        except Exception:
            continue
    return ok


def _reconstruct_from_cache(row) -> pd.DataFrame | None:
    """Rebuild one completed series from the extraction read-cache via era5_extract."""
    if EXTRACTION_DIR not in sys.path:
        sys.path.insert(0, EXTRACTION_DIR)
    import era5_extract as ex
    try:
        df = ex.fetch_series(row.lat, row.lon, row.window_start.to_pydatetime(),
                             row.window_end.to_pydatetime())
    except Exception:
        return None
    return df.astype(np.float32)[VALUE_COLUMNS]


def load_series(event_class: str, cohort: str = "dev", series_ids: list[str] | None = None,
                max_events: int | None = None, verbose: bool = False,
                ) -> dict[str, pd.DataFrame]:
    """Load extracted windows for one event class as {series_id: hourly DataFrame}.

    Each frame has a UTC DatetimeIndex covering exactly window_start .. window_end
    (408 rows, reindexed if necessary) and the 13 value columns (float32).

    cohort must be "dev" - anything else raises HoldoutAccessError.
    series_ids optionally restricts the load; a holdout id raises HoldoutAccessError.
    max_events keeps only the first N event series (manifest order) plus their controls.
    """
    if cohort != "dev":
        raise HoldoutAccessError(
            f"HOLDOUT GUARD: load_series(cohort={cohort!r}) refused - mining reads dev only.")
    if event_class not in CLASSES:
        raise ValueError(f"unknown event_class {event_class!r}; expected one of {CLASSES}")

    dev = load_manifest()
    sel = dev[dev["event_class"] == event_class]
    if series_ids is not None:
        _assert_dev_only(series_ids, "load_series(series_ids=...)")
        unknown = set(series_ids) - set(dev["series_id"])
        if unknown:
            raise KeyError(f"series_ids not in dev manifest: {sorted(unknown)[:5]}")
        sel = sel[sel["series_id"].isin(set(series_ids))]
    if max_events is not None:
        keep_events = sel.loc[sel["role"] == "event", "series_id"].head(max_events)
        keep = set(keep_events) | set(
            sel.loc[sel["role"] == "control"]
               .loc[lambda d: d["event_id"].isin(set(keep_events)), "series_id"])
        sel = sel[sel["series_id"].isin(keep)]

    allowed = set(sel["series_id"])
    by_id = sel.set_index("series_id")
    out: dict[str, pd.DataFrame] = {}

    # 1+2: finalized file and readable parts
    for path in _readable_parquets(event_class):
        df = pd.read_parquet(path)
        df = df[df["series_id"].isin(allowed - set(out))]
        for sid, g in df.groupby("series_id", sort=False):
            out[sid] = g.set_index("time")[VALUE_COLUMNS].astype(np.float32)
        if verbose:
            print(f"  {os.path.basename(path)}: cumulative {len(out)} series")

    # 3: cache reconstruction for completed-but-unfinalized series
    remaining = (allowed & done_series_ids()) - set(out)
    for sid in sorted(remaining):
        df = _reconstruct_from_cache(by_id.loc[sid])
        if df is not None:
            out[sid] = df
    if verbose and remaining:
        print(f"  cache reconstruction: +{len(remaining)} series -> {len(out)}")

    # normalize every window to the exact 408-hour index
    for sid, df in out.items():
        row = by_id.loc[sid]
        idx = pd.date_range(row.window_start, row.window_end, freq="1h", inclusive="left")
        if len(df) != len(idx) or not df.index.equals(idx):
            out[sid] = df[~df.index.duplicated()].reindex(idx)

    # hard post-condition: nothing loaded may be holdout
    _assert_dev_only(out.keys(), f"load_series({event_class!r}) result")
    return out


def loaded_counts() -> pd.DataFrame:
    """How many series are available right now, per class/cohort/role (metadata only)."""
    raw = _read_manifest_raw()
    done = done_series_ids()
    avail = raw[raw["series_id"].isin(done)]
    return (avail.groupby(["event_class", "cohort", "role"]).size()
                 .rename("n_done").reset_index())
