"""ERA5 hourly point time-series extractor for s3://openmeteo (anonymous, CC-BY-4.0).

Data layout (verified against the live bucket 2026-08-19):
  openmeteo/data/copernicus_era5/<variable>/year_YYYY.om   1940..2021, shape (721, 1440, 8760|8784)
  openmeteo/data/copernicus_era5/<variable>/chunk_NNN.om   NNN = days_since_unix_epoch // 21,
                                                           504 h each; 904 (2021-12-23) .. now-5d
  grid: lat_idx = round((lat+90)/0.25)  (0 = 90S .. 720 = 90N)
        lon_idx = round((lon+180)/0.25) (0 = 180W .. 1439 = 179.75E), wraps at 1440
  year-file internal chunks (1 lat, 6 lon, 1095 h); chunk-file internal chunks (1, 6, 504 h)

Units AS STORED (verified by decode + plausibility checks, see sanity_check()):
  precipitation                        mm/h        (total precip, water equivalent)
  wind_gusts_10m                       m/s
  wind_u_component_10m / _v_           m/s
  pressure_msl                         Pa          (divide by 100 for hPa)
  temperature_2m, dew_point_2m         degC
  snowfall_water_equivalent            mm/h        (water equivalent)
  soil_moisture_0_to_7cm, _7_to_28cm   m3/m3
  total_column_integrated_water_vapour kg/m2
  boundary_layer_height                m

Caching: decoded point series are cached under extraction/cache/ as float32 .npy,
one file per (variable, container-block, grid index):
  cache/<var>/y{YYYY}_b{B}_{la}_{lo}.npy   B-th 1095-hour block of a year file
  cache/<var>/c{NNN}_{la}_{lo}.npy         full 504-h series of a rolling chunk file
Block granularity matches the year files' internal time chunking, so a 17-day window
costs 1-2 ranged reads per variable instead of 8 for a full year, while clustered
events at the same grid point still share cache entries. Cache is the resume state
for bulk extraction: re-running skips everything already on disk.
"""
from __future__ import annotations

import datetime as dt
import os
import random
import threading
import time

import numpy as np
import pandas as pd

BUCKET_ERA5 = "openmeteo/data/copernicus_era5"
BUCKET_ERA5_LAND = "openmeteo/data/copernicus_era5_land"
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
EPOCH = dt.datetime(1970, 1, 1)
YEAR_FILE_MAX = 2021          # last calendar year served by year_YYYY.om
YEAR_FILE_MIN = 1940
CHUNK_DAYS = 21
CHUNK_HOURS = CHUNK_DAYS * 24  # 504
BLOCK_HOURS = 1095             # internal time-chunk length of year files
DEFAULT_WORKERS = 24
RETRIES = 4

#: variable -> unit as stored in the bucket
VARIABLES = {
    "precipitation": "mm/h",
    "wind_gusts_10m": "m/s",
    "wind_u_component_10m": "m/s",
    "wind_v_component_10m": "m/s",
    "pressure_msl": "Pa",
    "temperature_2m": "degC",
    "dew_point_2m": "degC",
    "snowfall_water_equivalent": "mm/h",
    "soil_moisture_0_to_7cm": "m3/m3",
    "soil_moisture_7_to_28cm": "m3/m3",
    "total_column_integrated_water_vapour": "kg/m2",
    "boundary_layer_height": "m",
}
DEFAULT_VARIABLES = list(VARIABLES)

_thread_local = threading.local()
_fs_lock = threading.Lock()
_fs = None


def _get_fs():
    """One shared anonymous S3 filesystem (s3fs is thread-safe for reads)."""
    global _fs
    with _fs_lock:
        if _fs is None:
            import s3fs
            _fs = s3fs.S3FileSystem(anon=True, default_block_size=64 * 1024)
        return _fs


#: grid step per model (ERA5 0.25 deg -> (721, 1440); ERA5-Land 0.1 deg -> (1801, 3600))
GRID_STEP = {BUCKET_ERA5: 0.25, BUCKET_ERA5_LAND: 0.1}


def grid_index(lat: float, lon: float, model: str = BUCKET_ERA5) -> tuple[int, int]:
    step = GRID_STEP[model]
    n_lat = int(round(180 / step)) + 1
    n_lon = int(round(360 / step))
    la = int(round((lat + 90.0) / step))
    lo = int(round((lon + 180.0) / step)) % n_lon
    la = min(max(la, 0), n_lat - 1)
    return la, lo


def grid_latlon(la: int, lo: int) -> tuple[float, float]:
    return la * 0.25 - 90.0, lo * 0.25 - 180.0


def hours_in_year(year: int) -> int:
    return 8784 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 8760


def _floor_hour(t: dt.datetime) -> dt.datetime:
    return t.replace(minute=0, second=0, microsecond=0)


_avail: dict = {}
_avail_lock = threading.Lock()


def get_availability(model: str, var: str) -> tuple[frozenset, frozenset]:
    """(years, chunk indices) actually present for a variable, listed once per process.

    Not every variable has the same coverage (verified 2026-08-19): most ERA5 vars have
    year_1940..2021 + chunk_904.., but total_column_integrated_water_vapour and
    boundary_layer_height have year files through 2023 and chunks only from 947
    (mid-2024) -> a gap 2024-01-01 .. 2024-06-12 that is NaN-filled; soil moisture
    is missing chunks 934-937 (2023-09-21 .. 2023-12-14), likewise NaN-filled.
    """
    k = (model, var)
    with _avail_lock:
        got = _avail.get(k)
    if got is not None:
        return got
    fs = _get_fs()
    files = _retrying(lambda: fs.ls(f"{model}/{var}/"), f"ls {model}/{var}")
    years, chunks = set(), set()
    for f in files:
        name = f.rsplit("/", 1)[-1]
        if name.startswith("year_"):
            years.add(int(name[5:-3]))
        elif name.startswith("chunk_"):
            chunks.add(int(name[6:-3]))
    got = (frozenset(years), frozenset(chunks))
    with _avail_lock:
        _avail[k] = got
    return got


def iter_segments(t0: dt.datetime, t1: dt.datetime,
                  years: frozenset | None = None, chunks: frozenset | None = None):
    """Split hourly-aligned window [t0, t1) into container segments.

    Yields (kind, key, h0, n, out_off): kind 'year'|'chunk'|'missing', key = year or
    chunk index, h0 = first hour index inside that container, n = number of hours,
    out_off = offset into the output array. Year files are preferred where present
    (chunk 904 overlaps the last 9 days of 2021 but year_2021 wins there); times not
    covered by any available file yield 'missing' segments (NaN-filled by the caller).
    When years/chunks are None the default layout (year<=2021, chunk>=904) is assumed.
    """
    t = t0
    while t < t1:
        year_ok = (t.year <= YEAR_FILE_MAX) if years is None else (t.year in years)
        year_end = dt.datetime(t.year + 1, 1, 1)
        ci = (t - EPOCH).days // CHUNK_DAYS
        cstart = EPOCH + dt.timedelta(days=ci * CHUNK_DAYS)
        cend = cstart + dt.timedelta(days=CHUNK_DAYS)
        chunk_ok = (ci >= 904) if chunks is None else (ci in chunks)
        if year_ok:
            seg_end = min(year_end, t1)
            h0 = int((t - dt.datetime(t.year, 1, 1)).total_seconds() // 3600)
            kind, key = "year", t.year
        elif chunk_ok:
            seg_end = min(cend, t1)
            h0 = int((t - cstart).total_seconds() // 3600)
            kind, key = "chunk", ci
        else:
            seg_end = min(year_end, cend, t1)
            h0, kind, key = 0, "missing", 0
        n = int((seg_end - t).total_seconds() // 3600)
        yield (kind, key, h0, n, int((t - t0).total_seconds() // 3600))
        t = seg_end


def _container_path(model: str, var: str, kind: str, key: int) -> str:
    name = f"year_{key}.om" if kind == "year" else f"chunk_{key}.om"
    return f"{model}/{var}/{name}"


def _get_reader(model: str, var: str, kind: str, key: int):
    """Thread-local reader cache: each thread keeps its own open OmFileReader per file."""
    cache = getattr(_thread_local, "readers", None)
    if cache is None:
        cache = _thread_local.readers = {}
    k = (model, var, kind, key)
    r = cache.get(k)
    if r is None:
        from omfiles import OmFileReader
        r = OmFileReader.from_fsspec(_get_fs(), _container_path(model, var, kind, key))
        # keep the reader cache bounded (files pin an fsspec handle each)
        if len(cache) > 64:
            cache.clear()
        cache[k] = r
    return r


def _drop_reader(model: str, var: str, kind: str, key: int):
    cache = getattr(_thread_local, "readers", None)
    if cache:
        cache.pop((model, var, kind, key), None)


def _retrying(fn, what: str):
    for attempt in range(RETRIES):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - S3/network hiccups come in many flavors
            if attempt == RETRIES - 1:
                raise RuntimeError(f"failed after {RETRIES} attempts: {what}: {e}") from e
            time.sleep((2 ** attempt) + random.random())


def _cache_path(var: str, kind: str, key: int, la: int, lo: int,
                block: int | None, model: str = BUCKET_ERA5) -> str:
    prefix = "" if model == BUCKET_ERA5 else "land_"
    d = os.path.join(CACHE_DIR, prefix + var)
    if kind == "year":
        return os.path.join(d, f"y{key}_b{block}_{la}_{lo}.npy")
    return os.path.join(d, f"c{key}_{la}_{lo}.npy")


def _read_piece(model: str, var: str, kind: str, key: int, la: int, lo: int,
                block: int | None) -> np.ndarray:
    """Read (with cache) one cache unit: a 1095-h year-file block or a full 504-h chunk."""
    path = _cache_path(var, kind, key, la, lo, block, model)
    if os.path.exists(path):
        try:
            return np.load(path)
        except Exception:
            os.remove(path)  # truncated cache file from an interrupted run
    if kind == "year":
        h0 = block * BLOCK_HOURS
        h1 = min(h0 + BLOCK_HOURS, hours_in_year(key))
    else:
        h0, h1 = 0, CHUNK_HOURS

    def do():
        try:
            r = _get_reader(model, var, kind, key)
            return r.read_array((slice(la, la + 1), slice(lo, lo + 1), slice(h0, h1))).ravel()
        except Exception:
            _drop_reader(model, var, kind, key)  # stale handle: reopen on retry
            raise

    arr = _retrying(do, f"{var} {kind}_{key} ({la},{lo}) h{h0}:{h1}").astype(np.float32)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp.npy"
    np.save(tmp, arr)
    os.replace(tmp, path)
    return arr


def fetch_variable(lat: float, lon: float, start: dt.datetime, end: dt.datetime,
                   var: str, model: str = BUCKET_ERA5) -> np.ndarray:
    """Hourly series for one variable over [start, end) at the nearest grid point."""
    t0, t1 = _floor_hour(start), _floor_hour(end)
    la, lo = grid_index(lat, lon, model)
    n_out = int((t1 - t0).total_seconds() // 3600)
    out = np.full(n_out, np.nan, dtype=np.float32)
    years, chunks = get_availability(model, var)
    for kind, key, h0, n, off in iter_segments(t0, t1, years, chunks):
        if kind == "missing":
            continue  # no file covers this span for this variable -> stays NaN
        if kind == "year":
            b0, b1 = h0 // BLOCK_HOURS, (h0 + n - 1) // BLOCK_HOURS
            for b in range(b0, b1 + 1):
                piece = _read_piece(model, var, kind, key, la, lo, b)
                ps, pe = b * BLOCK_HOURS, b * BLOCK_HOURS + len(piece)
                s, e = max(h0, ps), min(h0 + n, pe)
                out[off + (s - h0): off + (e - h0)] = piece[s - ps: e - ps]
        else:
            piece = _read_piece(model, var, kind, key, la, lo, None)
            out[off: off + n] = piece[h0: h0 + n]
    return out


def fetch_series(lat: float, lon: float, start: dt.datetime, end: dt.datetime,
                 variables: list[str] | None = None,
                 compute_wind_speed: bool = True) -> pd.DataFrame:
    """Hourly DataFrame (UTC index) over [start, end) for a variable list.

    Handles year-file vs rolling-chunk boundary and windows spanning year edges.
    Adds wind_speed_10m = hypot(u, v) when both components are requested.
    """
    variables = list(variables or DEFAULT_VARIABLES)
    t0, t1 = _floor_hour(start), _floor_hour(end)
    idx = pd.date_range(t0, t1, freq="1h", inclusive="left")
    data = {v: fetch_variable(lat, lon, t0, t1, v) for v in variables}
    df = pd.DataFrame(data, index=idx)
    if compute_wind_speed and {"wind_u_component_10m", "wind_v_component_10m"} <= set(variables):
        df["wind_speed_10m"] = np.hypot(df["wind_u_component_10m"], df["wind_v_component_10m"])
    return df


def extract_window(lat: float, lon: float, onset: dt.datetime,
                   days_before: int = 14, days_after: int = 3,
                   variables: list[str] | None = None) -> pd.DataFrame:
    """Precursor window: [onset - days_before, onset + days_after), hourly."""
    onset = _floor_hour(onset)
    return fetch_series(lat, lon, onset - dt.timedelta(days=days_before),
                        onset + dt.timedelta(days=days_after), variables)


def data_end_time() -> dt.datetime:
    """Approximate end of the archive (ERA5 lags realtime by ~5 days)."""
    return dt.datetime.utcnow() - dt.timedelta(days=5, hours=12)


def sanity_check(verbose: bool = True) -> dict:
    """Unit / plausibility check incl. reproduction of the recon Hurricane Ida decode."""
    res = {}
    df = fetch_series(30.0, -90.0, dt.datetime(2021, 8, 29), dt.datetime(2021, 8, 31))
    res["ida_peak_precip_mm_h"] = float(df["precipitation"].max())
    res["ida_peak_gust_m_s"] = float(df["wind_gusts_10m"].max())
    res["ida_min_mslp_hPa"] = float(df["pressure_msl"].min() / 100.0)
    ok = (abs(res["ida_peak_precip_mm_h"] - 27.9) < 0.2
          and abs(res["ida_peak_gust_m_s"] - 42.5) < 0.5
          and abs(res["ida_min_mslp_hPa"] - 992.0) < 1.0)
    res["ida_matches_recon"] = ok
    res["ranges"] = {v: (float(np.nanmin(df[v])), float(np.nanmax(df[v])))
                     for v in DEFAULT_VARIABLES}
    if verbose:
        print(f"Ida @30N,-90W: peak precip {res['ida_peak_precip_mm_h']:.1f} mm/h, "
              f"peak gust {res['ida_peak_gust_m_s']:.1f} m/s, "
              f"min MSLP {res['ida_min_mslp_hPa']:.1f} hPa -> recon match: {ok}")
        for v, (lo_, hi_) in res["ranges"].items():
            print(f"  {v:38s} [{VARIABLES[v]:6s}] min {lo_:10.2f} max {hi_:10.2f}")
    return res


if __name__ == "__main__":
    sanity_check()
