# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""Default warnings data source: anonymous ranged reads from s3://openmeteo.

Minimal production port of the research extractor (era5_extract.py on the
research branch) - the ERA5 hourly archive, read anonymously via
omfiles + s3fs. CC-BY-4.0; the attribution string is carried in every
client response. No credentials, no API keys, no rate limits; a full
17-day point window costs a few hundred small ranged GETs.

Bucket layout (verified against the live bucket):
  openmeteo/data/copernicus_era5/<variable>/year_YYYY.om   1940..2021
  openmeteo/data/copernicus_era5/<variable>/chunk_NNN.om   NNN = days_since_epoch // 21,
                                                           504 h each, 2021-12-23 .. now
  grid: lat_idx = round((lat+90)/0.25), lon_idx = round((lon+180)/0.25) % 1440

Units AS STORED (the feature module expects exactly these):
  precipitation mm/h; wind_* m/s; pressure_msl Pa; temperature_2m /
  dew_point_2m degC; soil_moisture_* m3/m3;
  total_column_integrated_water_vapour kg/m2.

KNOWN, DELIBERATE LIMITATION - ERA5 real-time lag: the archive trails real
time by ~2-7 days (static/meta.json data_end_time). The integration design
hoped to top up recent hours from the bucket's near-real-time model-analysis
archives, but those were verified NOT to be drop-in compatible
(ecmwf_ifs_analysis_long_window is 6-hourly on a reduced Gaussian O1280 grid
and lacks wind_gusts_10m; ncep_gfs025 lacks the needed surface fields), and
the frozen detector was never validated on non-ERA5 inputs. So this source
serves ERA5 only, up to its own data horizon; the evaluator's validity
window decides honestly whether an episode is still current enough to show
anyone. A lag-free path exists via the config-switchable API source.
"""
from __future__ import annotations

import datetime as dt
import json
import random
import time

import numpy as np

BUCKET_ERA5 = "openmeteo/data/copernicus_era5"
EPOCH = dt.datetime(1970, 1, 1)
GRID_STEP = 0.25
N_LAT = 721
N_LON = 1440
YEAR_FILE_MAX = 2021          # last calendar year served by year_YYYY.om
CHUNK_DAYS = 21
CHUNK_HOURS = CHUNK_DAYS * 24  # 504
BLOCK_HOURS = 1095             # internal time-chunk length of year files
FIRST_ROLLING_CHUNK = 904      # 2021-12-23
RETRIES = 4
NBR_HALF = 3                   # 7x7 neighborhood box (+-0.75 deg)


def grid_index(lat: float, lon: float):
    la = int(round((float(lat) + 90.0) / GRID_STEP))
    lo = int(round((float(lon) + 180.0) / GRID_STEP)) % N_LON
    return min(max(la, 0), N_LAT - 1), lo


def grid_round(value: float) -> float:
    """Round a coordinate to the 0.25 deg ERA5 grid (join discipline)."""
    return round(float(value) / GRID_STEP) * GRID_STEP


def hours_in_year(year: int) -> int:
    return 8784 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 8760


def _floor_hour(t: dt.datetime) -> dt.datetime:
    return t.replace(minute=0, second=0, microsecond=0, tzinfo=None)


def _retrying(fn, what: str):
    for attempt in range(RETRIES):
        try:
            return fn()
        except Exception as exc:  # S3/network hiccups come in many flavors
            if attempt == RETRIES - 1:
                raise RuntimeError(
                    f"failed after {RETRIES} attempts: {what}: {exc}") from exc
            time.sleep((2 ** attempt) + random.random())


def iter_segments(t0: dt.datetime, t1: dt.datetime, years, chunks):
    """Split hourly-aligned window [t0, t1) into container segments.

    Yields (kind, key, h0, n, out_off): kind 'year'|'chunk'|'missing'.
    Year files are preferred where present; hours not covered by any
    available file yield 'missing' segments (NaN-filled by the caller).
    """
    t = t0
    while t < t1:
        year_ok = t.year in years
        year_end = dt.datetime(t.year + 1, 1, 1)
        ci = (t - EPOCH).days // CHUNK_DAYS
        cstart = EPOCH + dt.timedelta(days=ci * CHUNK_DAYS)
        cend = cstart + dt.timedelta(days=CHUNK_DAYS)
        chunk_ok = ci in chunks
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


class OpenMeteoS3Source:
    """Anonymous ERA5 reads from s3://openmeteo (default source)."""

    name = "openmeteo_s3"

    def __init__(self):
        self._fs = None
        self._readers = {}
        self._availability = {}

    # -- plumbing --------------------------------------------------------- #

    def _get_fs(self):
        if self._fs is None:
            import s3fs
            self._fs = s3fs.S3FileSystem(anon=True, default_block_size=64 * 1024)
        return self._fs

    def _get_reader(self, var: str, kind: str, key: int):
        from omfiles import OmFileReader
        k = (var, kind, key)
        r = self._readers.get(k)
        if r is None:
            name = f"year_{key}.om" if kind == "year" else f"chunk_{key}.om"
            r = OmFileReader.from_fsspec(self._get_fs(), f"{BUCKET_ERA5}/{var}/{name}")
            if len(self._readers) > 64:  # readers pin an fsspec handle each
                self._readers.clear()
            self._readers[k] = r
        return r

    def _drop_reader(self, var: str, kind: str, key: int):
        self._readers.pop((var, kind, key), None)

    def _get_availability(self, var: str):
        """(years, chunk indices) actually present for a variable (some
        variables have documented gaps in the rolling chunks)."""
        got = self._availability.get(var)
        if got is not None:
            return got
        fs = self._get_fs()
        files = _retrying(lambda: fs.ls(f"{BUCKET_ERA5}/{var}/"), f"ls {var}")
        years, chunks = set(), set()
        for f in files:
            fname = f.rsplit("/", 1)[-1]
            if fname.startswith("year_"):
                years.add(int(fname[5:-3]))
            elif fname.startswith("chunk_"):
                chunks.add(int(fname[6:-3]))
        got = (frozenset(years), frozenset(chunks))
        self._availability[var] = got
        return got

    def _read_point(self, var: str, kind: str, key: int, la: int, lo: int,
                    h0: int, n: int) -> np.ndarray:
        def do():
            try:
                r = self._get_reader(var, kind, key)
                return r.read_array(
                    (slice(la, la + 1), slice(lo, lo + 1), slice(h0, h0 + n))
                ).ravel()
            except Exception:
                self._drop_reader(var, kind, key)  # stale handle: reopen on retry
                raise
        return _retrying(do, f"{var} {kind}_{key} ({la},{lo}) h{h0}:{h0 + n}")

    # -- WarningsDataSource interface ------------------------------------- #

    def data_horizon_utc(self) -> dt.datetime:
        """End of the ERA5 archive, from the bucket's static/meta.json."""
        fs = self._get_fs()
        raw = _retrying(lambda: fs.cat(f"{BUCKET_ERA5}/static/meta.json"),
                        "read static/meta.json")
        meta = json.loads(raw)
        return _floor_hour(EPOCH + dt.timedelta(seconds=int(meta["data_end_time"])))

    def hourly_series(self, latitude, longitude, variables, start_utc, end_utc):
        t0, t1 = _floor_hour(start_utc), _floor_hour(end_utc)
        la, lo = grid_index(latitude, longitude)
        n_out = int((t1 - t0).total_seconds() // 3600)
        out = {}
        for var in variables:
            arr = np.full(n_out, np.nan, dtype=np.float64)
            years, chunks = self._get_availability(var)
            for kind, key, h0, n, off in iter_segments(t0, t1, years, chunks):
                if kind == "missing":
                    continue  # no file covers this span -> stays NaN
                piece = self._read_point(var, kind, key, la, lo, h0, n)
                arr[off: off + len(piece)] = piece
            out[var] = arr
        return out

    def neighborhood_precipitation(self, latitude, longitude, start_utc, end_utc):
        """(n_hours, 49) precipitation for the 7x7 box around the point.

        Cells are read row-wise (one lat row x 7 lon slice per container),
        so the whole box costs ~7 ranged reads per container. Off-grid
        latitude rows are NaN; longitude wraps at the date line (the rare
        wrap case falls back to per-cell reads).
        """
        t0, t1 = _floor_hour(start_utc), _floor_hour(end_utc)
        la, lo = grid_index(latitude, longitude)
        n_out = int((t1 - t0).total_seconds() // 3600)
        width = 2 * NBR_HALF + 1
        cells = np.full((n_out, width * width), np.nan, dtype=np.float64)
        years, chunks = self._get_availability("precipitation")
        wraps = lo - NBR_HALF < 0 or lo + NBR_HALF >= N_LON
        for r in range(width):
            row_la = la + (r - NBR_HALF)
            if row_la < 0 or row_la >= N_LAT:
                continue  # off-grid latitudes stay NaN
            for kind, key, h0, n, off in iter_segments(t0, t1, years, chunks):
                if kind == "missing":
                    continue
                if not wraps:
                    def do(row_la=row_la, kind=kind, key=key, h0=h0, n=n):
                        try:
                            rd = self._get_reader("precipitation", kind, key)
                            return rd.read_array((
                                slice(row_la, row_la + 1),
                                slice(lo - NBR_HALF, lo + NBR_HALF + 1),
                                slice(h0, h0 + n),
                            ))
                        except Exception:
                            self._drop_reader("precipitation", kind, key)
                            raise
                    block = _retrying(do, f"nbr precipitation {kind}_{key} row {row_la}")
                    # block shape (1, 7, n) -> per-cell columns
                    for c in range(width):
                        cells[off: off + block.shape[2], r * width + c] = block[0, c, :]
                else:
                    for c in range(width):
                        col_lo = (lo + (c - NBR_HALF)) % N_LON
                        piece = self._read_point("precipitation", kind, key,
                                                 row_la, col_lo, h0, n)
                        cells[off: off + len(piece), r * width + c] = piece
        return cells
