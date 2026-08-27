"""Limpopo basin case-study extraction: multi-decade hourly ERA5 series at 6 basin
points, plus the 7x7 neighborhood precipitation the frozen flash-flood rule needs.

Blind-case-study support module: extraction only, no tuning. Reuses
extraction/era5_extract.py (point pieces + cache) and adds a multi-chunk
neighborhood fetch patterned on extraction/extract_nbr_precip.py.

Eras extracted per point:
  e1977   1975-01-01 .. 1979-01-01   (tests the Feb-1977 Emilie flood)
  modern  1995-01-01 .. 2026-08-14   (tests 2000, 2013 and the blind 2025/26 event)

Point variables (precipitation comes from the neighborhood's own center cell p33):
  soil_moisture_0_to_7cm, pressure_msl, wind_gusts_10m, wind_u/v_component_10m,
  temperature_2m, dew_point_2m, total_column_integrated_water_vapour,
  wind_u/v_component_100m

Usage:
  python3 extract_limpopo.py warm <shard> <n_shards>   # fetch pieces into cache
  python3 extract_limpopo.py assemble                  # cache -> per-point parquet
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACTION_DIR = os.path.normpath(os.path.join(HERE, "..", "extraction"))
sys.path.insert(0, EXTRACTION_DIR)
import era5_extract as ex  # noqa: E402

OUT_DIR = os.path.join(HERE, "series")
NBR_CACHE = os.path.join(HERE, "cache_nbr")
SRC = ex.BUCKET_ERA5
HALO = 3
NLAT, NLON = 721, 1440
LONC = 6
CELL_COLS = [f"p{r}{c}" for r in range(7) for c in range(7)]

#: (name, lat, lon) - Limpopo basin spanning Vhembe -> Mozambique coast
POINTS = [
    ("thohoyandou", -22.95, 30.48),   # Vhembe district, Luvuvhu headwaters
    ("musina", -22.35, 30.03),        # Vhembe / Beitbridge area (same ERA5 cell)
    ("pafuri", -22.45, 31.32),        # Limpopo-Luvuvhu confluence, N Kruger
    ("mapai", -22.85, 31.98),         # middle Limpopo, Gaza province MZ
    ("chokwe", -24.53, 32.98),        # lower Limpopo irrigation belt MZ
    ("xai_xai", -25.05, 33.64),       # Limpopo mouth, Gaza province MZ
]

ERAS = {
    "e1977": (dt.datetime(1975, 1, 1), dt.datetime(1979, 1, 1)),
    "modern": (dt.datetime(1995, 1, 1), dt.datetime(2026, 8, 14)),
}

POINT_VARS = [
    "soil_moisture_0_to_7cm", "pressure_msl", "wind_gusts_10m",
    "wind_u_component_10m", "wind_v_component_10m", "temperature_2m",
    "dew_point_2m", "total_column_integrated_water_vapour",
    "wind_u_component_100m", "wind_v_component_100m",
]
NAN_VARS = ["snowfall_water_equivalent", "soil_moisture_7_to_28cm",
            "boundary_layer_height"]  # unused by the frozen rules; kept as NaN


def log(msg):
    print(f"[{dt.datetime.utcnow():%H:%M:%S}] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# work planning
# --------------------------------------------------------------------------- #

def point_piece_tasks():
    """All (var, kind, key, block, la, lo) cache units for the point variables."""
    tasks = set()
    for var in POINT_VARS:
        years, chunks = ex.get_availability(SRC, var)
        for _, lat, lon in POINTS:
            la, lo = ex.grid_index(lat, lon)
            for t0, t1 in ERAS.values():
                for kind, key, h0, n, _ in ex.iter_segments(t0, t1, years, chunks):
                    if kind == "missing":
                        continue
                    if kind == "year":
                        for b in range(h0 // ex.BLOCK_HOURS,
                                       (h0 + n - 1) // ex.BLOCK_HOURS + 1):
                            tasks.add((var, kind, key, b, la, lo))
                    else:
                        tasks.add((var, kind, key, None, la, lo))
    return sorted(tasks, key=str)


def nbr_unit_tasks():
    """All (kind, key, block, la_lo, la_hi, lc) neighborhood-precip units."""
    years, chunks = ex.get_availability(SRC, "precipitation")
    tasks = set()
    for _, lat, lon in POINTS:
        la, lo = ex.grid_index(lat, lon)
        la_lo, la_hi = max(0, la - HALO), min(NLAT - 1, la + HALO)
        lcs = sorted({((lo + dx) % NLON) // LONC for dx in range(-HALO, HALO + 1)})
        for t0, t1 in ERAS.values():
            for kind, key, h0, n, _ in ex.iter_segments(t0, t1, years, chunks):
                if kind == "missing":
                    continue
                if kind == "year":
                    blocks = range(h0 // ex.BLOCK_HOURS,
                                   (h0 + n - 1) // ex.BLOCK_HOURS + 1)
                else:
                    blocks = (None,)
                for b in blocks:
                    for lc in lcs:
                        tasks.add((kind, key, b, la_lo, la_hi, lc))
    return sorted(tasks, key=str)


def _nbr_cache_path(kind, key, block, la_lo, la_hi, lc):
    b = "c" if block is None else f"b{block}"
    return os.path.join(NBR_CACHE, f"{kind}_{key}_{b}_{la_lo}_{la_hi}_{lc}.npy")


def _unit_hours(kind, key, block):
    if kind == "year":
        h0 = block * ex.BLOCK_HOURS
        return h0, min(h0 + ex.BLOCK_HOURS, ex.hours_in_year(key))
    return 0, ex.CHUNK_HOURS


def fetch_nbr_unit(kind, key, block, la_lo, la_hi, lc):
    path = _nbr_cache_path(kind, key, block, la_lo, la_hi, lc)
    if os.path.exists(path):
        try:
            return np.load(path)
        except Exception:
            os.remove(path)
    h0, h1 = _unit_hours(kind, key, block)

    def do():
        try:
            r = ex._get_reader(SRC, "precipitation", kind, key)
            return r.read_array((slice(la_lo, la_hi + 1),
                                 slice(lc * LONC, (lc + 1) * LONC),
                                 slice(h0, h1)))
        except Exception:
            ex._drop_reader(SRC, "precipitation", kind, key)
            raise

    arr = np.asarray(ex._retrying(
        do, f"nbr {kind}_{key} b{block} la{la_lo}-{la_hi} lc{lc}"), dtype=np.float32)
    os.makedirs(NBR_CACHE, exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp.npy"
    np.save(tmp, arr)
    os.replace(tmp, path)
    return arr


def fetch_point_piece(var, kind, key, block, la, lo):
    return ex._read_piece(SRC, var, kind, key, la, lo, block)


# --------------------------------------------------------------------------- #
# warm / assemble
# --------------------------------------------------------------------------- #

def warm(shard: int, n_shards: int, workers: int = 24):
    pts = point_piece_tasks()
    nbr = nbr_unit_tasks()
    mine_p = [t for i, t in enumerate(pts) if i % n_shards == shard]
    mine_n = [t for i, t in enumerate(nbr) if i % n_shards == shard]
    log(f"shard {shard}/{n_shards}: {len(mine_p)} point pieces + "
        f"{len(mine_n)} nbr units")
    t0 = time.time()
    done = fails = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(fetch_point_piece, *t) for t in mine_p]
        futs += [pool.submit(fetch_nbr_unit, *t) for t in mine_n]
        for f in cf.as_completed(futs):
            try:
                f.result()
                done += 1
            except Exception as e:  # noqa: BLE001
                fails += 1
                log(f"FAIL: {e}")
            if done % 500 == 0:
                rate = done / (time.time() - t0)
                log(f"{done}/{len(futs)} pieces ({rate:.1f}/s, "
                    f"eta {(len(futs) - done) / max(rate, 0.1) / 60:.0f} min)")
    log(f"shard {shard} complete: {done} ok, {fails} failed, "
        f"{(time.time() - t0) / 60:.1f} min")
    return fails


def assemble_nbr(lat, lon, t0, t1):
    """(index, DataFrame of 49 cells) for one point/era, from the unit cache."""
    years, chunks = ex.get_availability(SRC, "precipitation")
    la, lo = ex.grid_index(lat, lon)
    la_lo, la_hi = max(0, la - HALO), min(NLAT - 1, la + HALO)
    idx = pd.date_range(t0, t1, freq="1h", inclusive="left")
    out = np.full((len(idx), 7, 7), np.nan, dtype=np.float32)
    for kind, key, h0, n, off in ex.iter_segments(t0, t1, years, chunks):
        if kind == "missing":
            continue
        blocks = (range(h0 // ex.BLOCK_HOURS, (h0 + n - 1) // ex.BLOCK_HOURS + 1)
                  if kind == "year" else (None,))
        for b in blocks:
            ph0, ph1 = _unit_hours(kind, key, b)
            s0, e0 = max(h0, ph0), min(h0 + n, ph1)
            if e0 <= s0:
                continue
            t_out = slice(off + s0 - h0, off + e0 - h0)
            t_unit = slice(s0 - ph0, e0 - ph0)
            unit_by_lc = {}
            for dx in range(-HALO, HALO + 1):
                lo2 = (lo + dx) % NLON
                lc, col = lo2 // LONC, lo2 % LONC
                if lc not in unit_by_lc:
                    unit_by_lc[lc] = np.load(
                        _nbr_cache_path(kind, key, b, la_lo, la_hi, lc))
                arr = unit_by_lc[lc]
                for dy in range(-HALO, HALO + 1):
                    la2 = la + dy
                    if not (la_lo <= la2 <= la_hi):
                        continue
                    out[t_out, dy + HALO, dx + HALO] = arr[la2 - la_lo, col, t_unit]
    return idx, pd.DataFrame(out.reshape(len(idx), -1), index=idx,
                             columns=CELL_COLS)


def assemble():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, lat, lon in POINTS:
        for era, (t0, t1) in ERAS.items():
            base = os.path.join(OUT_DIR, f"{name}_{era}")
            if os.path.exists(base + ".parquet") and os.path.exists(base + "_nbr.parquet"):
                log(f"{name}/{era}: already assembled")
                continue
            idx, nbr = assemble_nbr(lat, lon, t0, t1)
            data = {v: ex.fetch_variable(lat, lon, t0, t1, v) for v in POINT_VARS}
            df = pd.DataFrame(data, index=idx)
            df["precipitation"] = nbr["p33"].to_numpy()  # point = center cell
            for v in NAN_VARS:
                df[v] = np.nan
            df["wind_speed_10m"] = np.hypot(df["wind_u_component_10m"],
                                            df["wind_v_component_10m"])
            df.astype(np.float32).to_parquet(base + ".parquet", compression="zstd")
            nbr.to_parquet(base + "_nbr.parquet", compression="zstd")
            pv = float(np.isfinite(df["precipitation"].to_numpy()).mean())
            log(f"{name}/{era}: {len(idx)} h, precip valid {pv:.3f} -> {base}*.parquet")
    log("ASSEMBLE COMPLETE")


if __name__ == "__main__":
    if sys.argv[1] == "warm":
        sys.exit(1 if warm(int(sys.argv[2]), int(sys.argv[3])) else 0)
    elif sys.argv[1] == "assemble":
        assemble()
