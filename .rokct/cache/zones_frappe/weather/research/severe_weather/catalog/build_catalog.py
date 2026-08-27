#!/usr/bin/env python3
"""Build the ground-truth disaster event catalog for the severe-weather
early-warning project.

Sources (the NOAA/DFO origin hosts were blocked by the build environment's
network allowlist, so verified public mirrors on raw.githubusercontent.com
/ media.githubusercontent.com are used; every downloaded file is validated by
parsing, never by filename):

  1. NOAA Storm Events details files, 1996-2025 (mirror of the canonical NCEI
     csvfiles directory; 2025 file is the c20251216 revision, Jan-Sep 2025).
  2. Dartmouth Flood Observatory (DFO) Global Active Archive of Large Flood
     Events, full frozen archive (5,130 events, 1985 - 2021-10).
  3. IBTrACS v04 global tropical cyclone best tracks (full archive mirror,
     through June 2024).

Output: events.parquet + events_sample.csv (normalized catalog) and
anchor-event verification (ANCHORS.md).

Usage:  python3 build_catalog.py [--raw-dir raw] [--out-dir .] [--skip-download]
"""

import argparse
import io
import os
import re
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Source URLs
# --------------------------------------------------------------------------

SE_MIRROR = ("https://raw.githubusercontent.com/htluu-ucsd/"
             "NaturalDisasterProject/main/data/ncei_noaa/")

# Canonical NCEI file names (dYYYY_cYYYYMMDD revision tags) present on the
# mirror, one per year 1996-2024.
SE_FILES = [
    "StormEvents_details-ftp_v1.0_d1996_c20220425.csv",
    "StormEvents_details-ftp_v1.0_d1997_c20220425.csv",
    "StormEvents_details-ftp_v1.0_d1998_c20220425.csv",
    "StormEvents_details-ftp_v1.0_d1999_c20220425.csv",
    "StormEvents_details-ftp_v1.0_d2000_c20220425.csv",
    "StormEvents_details-ftp_v1.0_d2001_c20220425.csv",
    "StormEvents_details-ftp_v1.0_d2002_c20220425.csv",
    "StormEvents_details-ftp_v1.0_d2003_c20220425.csv",
    "StormEvents_details-ftp_v1.0_d2004_c20220425.csv",
    "StormEvents_details-ftp_v1.0_d2005_c20220425.csv",
    "StormEvents_details-ftp_v1.0_d2006_c20250122.csv",
    "StormEvents_details-ftp_v1.0_d2007_c20240216.csv",
    "StormEvents_details-ftp_v1.0_d2008_c20240620.csv",
    "StormEvents_details-ftp_v1.0_d2009_c20231116.csv",
    "StormEvents_details-ftp_v1.0_d2010_c20220425.csv",
    "StormEvents_details-ftp_v1.0_d2011_c20230417.csv",
    "StormEvents_details-ftp_v1.0_d2012_c20221216.csv",
    "StormEvents_details-ftp_v1.0_d2013_c20230118.csv",
    "StormEvents_details-ftp_v1.0_d2014_c20231116.csv",
    "StormEvents_details-ftp_v1.0_d2015_c20240716.csv",
    "StormEvents_details-ftp_v1.0_d2016_c20220719.csv",
    "StormEvents_details-ftp_v1.0_d2017_c20250122.csv",
    "StormEvents_details-ftp_v1.0_d2018_c20240716.csv",
    "StormEvents_details-ftp_v1.0_d2019_c20240117.csv",
    "StormEvents_details-ftp_v1.0_d2020_c20240620.csv",
    "StormEvents_details-ftp_v1.0_d2021_c20240716.csv",
    "StormEvents_details-ftp_v1.0_d2022_c20241121.csv",
    "StormEvents_details-ftp_v1.0_d2023_c20241216.csv",
    "StormEvents_details-ftp_v1.0_d2024_c20250122.csv",
]

# 2025 partial year (Jan-Sep) from a second mirror.
SE_2025_FILE = "StormEvents_details-ftp_v1.0_d2025_c20251216.csv"
SE_2025_URL = ("https://raw.githubusercontent.com/mattialodi0/progA3I/main/"
               "NCEI_datasets/storm_events/" + SE_2025_FILE)

# Full frozen DFO archive (5,130 events, 1985 - 2021-10-06).
DFO_URL = ("https://raw.githubusercontent.com/kandread/cee597j/master/"
           "homework/homework05/FloodArchive.csv")

# Full global IBTrACS v04 CSV (through June 2024), stored under git-lfs, so it
# is fetched from the media endpoint.
IBTRACS_URL = ("https://media.githubusercontent.com/media/tomerburg/IBTrACS/"
               "main/ibtracs.csv")

# --------------------------------------------------------------------------
# Event-type mapping (NOAA Storm Events EVENT_TYPE -> catalog class)
# --------------------------------------------------------------------------

SE_CLASS = {
    "Flash Flood": "flash_flood",
    "Flood": "flood",
    "Coastal Flood": "flood",
    "Tornado": "tornado",
    "High Wind": "destructive_wind",
    "Thunderstorm Wind": "destructive_wind",
    "Strong Wind": "destructive_wind",
    "Marine High Wind": "destructive_wind",
    "Hurricane (Typhoon)": "destructive_wind",
    "Hurricane": "destructive_wind",
    "Typhoon": "destructive_wind",
    "Tropical Storm": "destructive_wind",
}

# Local STANDARD time zone -> UTC offset hours (Storm Events records local
# standard time; a numeric suffix in CZ_TIMEZONE, when present, is the offset).
TZ_ALPHA = {
    "EST": -5, "CST": -6, "MST": -7, "PST": -8, "AST": -4, "HST": -10,
    "AKST": -9, "SST": -11, "GST": 10, "CHST": 10, "GMT": 0, "UTC": 0,
    "EDT": -4, "CDT": -5, "MDT": -6, "PDT": -7, "ADT": -3, "AKDT": -8,
    "HDT": -9,
}

BASIN_NAME = {
    "NA": "North Atlantic", "EP": "East Pacific", "WP": "West Pacific",
    "NI": "North Indian", "SI": "South Indian", "SP": "South Pacific",
    "SA": "South Atlantic", "MM": "Mixed/Multiple",
}

# US country labels used by DFO (for the dedup rule against Storm Events).
DFO_USA = {"usa", "united states", "united states of america"}

MAJOR_DEATHS = 10          # deaths >= 10
MAJOR_DAMAGE = 1.0e8       # property+crop damage >= $100M
MAJOR_FSCALE = 3           # tornado F/EF >= 3
MAJOR_TC_WIND = 96         # TC max sustained wind >= 96 kt (Saffir-Simpson 3+)
MAJOR_DFO_SEV = 2          # DFO severity class 2 ("extreme", >100-yr recurrence)
MAJOR_DFO_DISP = 100000    # DFO displaced >= 100k


# --------------------------------------------------------------------------
# Download helpers
# --------------------------------------------------------------------------

def fetch(url, dest, min_bytes=1000, tries=3):
    """Download url -> dest unless a plausible file already exists."""
    if os.path.exists(dest) and os.path.getsize(dest) >= min_bytes:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for attempt in range(1, tries + 1):
        try:
            print(f"  downloading {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "catalog-build/1.0"})
            with urllib.request.urlopen(req, timeout=600) as r, open(dest + ".part", "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            size = os.path.getsize(dest + ".part")
            if size < min_bytes:
                raise IOError(f"file too small ({size} B)")
            head = open(dest + ".part", "rb").read(200)
            if head.lstrip().startswith(b"<"):
                raise IOError("got HTML, not data (broken mirror)")
            if head.startswith(b"version https://git-lfs"):
                raise IOError("got a git-lfs pointer, not data")
            os.replace(dest + ".part", dest)
            return dest
        except Exception as e:
            print(f"    attempt {attempt} failed: {e}")
            if attempt == tries:
                raise
            time.sleep(3 * attempt)


def download_all(raw):
    files = {}
    se_dir = os.path.join(raw, "stormevents")
    for name in SE_FILES:
        files[name] = fetch(SE_MIRROR + name, os.path.join(se_dir, name), 5_000_000)
    files[SE_2025_FILE] = fetch(SE_2025_URL, os.path.join(se_dir, SE_2025_FILE), 5_000_000)
    files["dfo"] = fetch(DFO_URL, os.path.join(raw, "dfo", "FloodArchive.csv"), 100_000)
    files["ibtracs"] = fetch(IBTRACS_URL, os.path.join(raw, "ibtracs", "ibtracs_all.csv"), 100_000_000)
    return files


# --------------------------------------------------------------------------
# NOAA Storm Events
# --------------------------------------------------------------------------

def parse_damage(s):
    """'10.00K' -> 10000.0 ; '' / 'K' / NaN -> NaN ; '2.5B' -> 2.5e9."""
    if not isinstance(s, str):
        return np.nan
    s = s.strip()
    if not s:
        return np.nan
    mult = {"H": 1e2, "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
    m = 1.0
    if s[-1].upper() in mult:
        m = mult[s[-1].upper()]
        s = s[:-1]
    if not s:
        return np.nan  # bare suffix like 'K' = unknown magnitude
    try:
        return float(s) * m
    except ValueError:
        return np.nan


def tz_offset_hours(tz):
    """CZ_TIMEZONE ('CST-6', 'CST', 'GST10', ...) -> UTC offset in hours."""
    if not isinstance(tz, str):
        return np.nan
    tz = tz.strip().upper()
    m = re.match(r"^([A-Z]+)(-?\d+)?$", tz)
    if not m:
        return np.nan
    alpha, num = m.groups()
    if num is not None:
        return float(num)
    return float(TZ_ALPHA.get(alpha, np.nan))


def f_scale_num(v):
    if not isinstance(v, str):
        return np.nan
    m = re.search(r"(\d)", v)
    return float(m.group(1)) if m else np.nan


SE_USECOLS = [
    "BEGIN_YEARMONTH", "BEGIN_DAY", "BEGIN_TIME",
    "END_YEARMONTH", "END_DAY", "END_TIME",
    "EVENT_ID", "STATE", "STATE_FIPS", "EVENT_TYPE",
    "CZ_TYPE", "CZ_FIPS", "CZ_NAME", "CZ_TIMEZONE",
    "INJURIES_DIRECT", "INJURIES_INDIRECT", "DEATHS_DIRECT", "DEATHS_INDIRECT",
    "DAMAGE_PROPERTY", "DAMAGE_CROPS",
    "MAGNITUDE", "MAGNITUDE_TYPE", "CATEGORY", "TOR_F_SCALE",
    "BEGIN_LAT", "BEGIN_LON", "END_LAT", "END_LON",
]


def to_utc(ym, day, hhmm, off_hours):
    """Vectorized local-standard-time -> UTC conversion."""
    ts = pd.to_datetime(
        {
            "year": ym // 100,
            "month": ym % 100,
            "day": day,
            "hour": hhmm // 100,
            "minute": hhmm % 100,
        },
        errors="coerce",
    )
    return ts - pd.to_timedelta(off_hours, unit="h")


def load_storm_events(se_dir):
    frames = []
    print("Parsing Storm Events year files ...")
    for name in sorted(os.listdir(se_dir)):
        if not name.endswith(".csv"):
            continue
        df = pd.read_csv(os.path.join(se_dir, name), usecols=SE_USECOLS,
                         low_memory=False)
        year = int(re.search(r"_d(\d{4})_", name).group(1))
        n_all = len(df)
        df = df[df["EVENT_TYPE"].isin(SE_CLASS)].copy()
        df["file_year"] = year
        frames.append(df)
        print(f"  {name}: {n_all} rows total, {len(df)} kept")
    df = pd.concat(frames, ignore_index=True)

    off = df["CZ_TIMEZONE"].map(tz_offset_hours)
    n_no_tz = int(off.isna().sum())
    off = off.fillna(0.0)  # assume UTC if timezone unparseable (rare)

    df["start_utc"] = to_utc(df["BEGIN_YEARMONTH"].astype(int),
                             df["BEGIN_DAY"].astype(int),
                             df["BEGIN_TIME"].astype(int), off)
    df["end_utc"] = to_utc(df["END_YEARMONTH"].astype(int),
                           df["END_DAY"].astype(int),
                           df["END_TIME"].astype(int), off)
    n_bad_time = int(df["start_utc"].isna().sum())
    df = df[df["start_utc"].notna()].copy()
    swap = df["end_utc"].isna() | (df["end_utc"] < df["start_utc"])
    df.loc[swap, "end_utc"] = df.loc[swap, "start_utc"]

    # ---- coordinates: point, else county/zone centroid, else state centroid
    df["lat"] = pd.to_numeric(df["BEGIN_LAT"], errors="coerce")
    df["lon"] = pd.to_numeric(df["BEGIN_LON"], errors="coerce")
    ok = df["lat"].notna() & df["lon"].notna() & (df["lat"].abs() <= 90) & \
        (df["lon"].abs() <= 180) & ~((df["lat"] == 0) & (df["lon"] == 0))
    df.loc[~ok, ["lat", "lon"]] = np.nan

    key = ["STATE_FIPS", "CZ_TYPE", "CZ_FIPS"]
    cz_cent = (df[ok].groupby(key)[["lat", "lon"]].mean()
               .rename(columns={"lat": "clat", "lon": "clon"}))
    st_cent = (df[ok].groupby("STATE_FIPS")[["lat", "lon"]].mean()
               .rename(columns={"lat": "slat", "lon": "slon"}))
    df = df.merge(cz_cent, left_on=key, right_index=True, how="left")
    df = df.merge(st_cent, left_on="STATE_FIPS", right_index=True, how="left")

    df["geo_precision"] = "point"
    use_cz = df["lat"].isna() & df["clat"].notna()
    df.loc[use_cz, "lat"] = df.loc[use_cz, "clat"]
    df.loc[use_cz, "lon"] = df.loc[use_cz, "clon"]
    df.loc[use_cz, "geo_precision"] = "cz_centroid"

    # Zone (CZ_TYPE='Z') events often have no coordinates and zone numbers do
    # not map to county FIPS.  Match the zone NAME against county names in the
    # same state (exact, then substring) and use that county's centroid of
    # point events.
    cn = df[ok & (df["CZ_TYPE"] == "C")].copy()
    cn["cname"] = cn["CZ_NAME"].astype(str).str.upper().str.strip()
    name_cent = cn.groupby(["STATE_FIPS", "cname"])[["lat", "lon"]].mean()
    state_counties = {s: g.index.get_level_values(1).tolist()
                      for s, g in name_cent.groupby(level=0)}
    need = df["lat"].isna()
    zone_keys = (df.loc[need, ["STATE_FIPS", "CZ_NAME"]]
                 .assign(zname=lambda x: x["CZ_NAME"].astype(str).str.upper().str.strip())
                 [["STATE_FIPS", "zname"]].drop_duplicates())
    zmap = {}
    for sf, zn in zone_keys.itertuples(index=False):
        if (sf, zn) in name_cent.index:
            zmap[(sf, zn)] = name_cent.loc[(sf, zn)]
            continue
        hits = [c for c in state_counties.get(sf, []) if c and c in zn]
        if hits:
            best = max(hits, key=len)  # longest county name contained in zone name
            zmap[(sf, zn)] = name_cent.loc[(sf, best)]
    if zmap:
        zdf = pd.DataFrame(
            {"STATE_FIPS": [k[0] for k in zmap], "zname": [k[1] for k in zmap],
             "zlat": [v["lat"] for v in zmap.values()],
             "zlon": [v["lon"] for v in zmap.values()]})
        df["zname"] = df["CZ_NAME"].astype(str).str.upper().str.strip()
        df = df.merge(zdf, on=["STATE_FIPS", "zname"], how="left")
        use_zn = df["lat"].isna() & df["zlat"].notna()
        df.loc[use_zn, "lat"] = df.loc[use_zn, "zlat"]
        df.loc[use_zn, "lon"] = df.loc[use_zn, "zlon"]
        df.loc[use_zn, "geo_precision"] = "zone_name_centroid"

    use_st = df["lat"].isna() & df["slat"].notna()
    df.loc[use_st, "lat"] = df.loc[use_st, "slat"]
    df.loc[use_st, "lon"] = df.loc[use_st, "slon"]
    df.loc[use_st, "geo_precision"] = "state_centroid"
    n_no_geo = int(df["lat"].isna().sum())
    df = df[df["lat"].notna()].copy()

    # ---- severity fields
    df["deaths"] = (pd.to_numeric(df["DEATHS_DIRECT"], errors="coerce").fillna(0)
                    + pd.to_numeric(df["DEATHS_INDIRECT"], errors="coerce").fillna(0))
    df["injuries"] = (pd.to_numeric(df["INJURIES_DIRECT"], errors="coerce").fillna(0)
                      + pd.to_numeric(df["INJURIES_INDIRECT"], errors="coerce").fillna(0))
    df["damage_usd"] = (df["DAMAGE_PROPERTY"].map(parse_damage).fillna(0)
                        + df["DAMAGE_CROPS"].map(parse_damage).fillna(0))

    df["event_class"] = df["EVENT_TYPE"].map(SE_CLASS)
    fnum = df["TOR_F_SCALE"].map(f_scale_num)
    wind = pd.to_numeric(df["MAGNITUDE"], errors="coerce")
    df["magnitude"] = np.where(df["event_class"] == "tornado", fnum, wind)
    df["magnitude_type"] = np.where(
        df["event_class"] == "tornado", "f_ef_scale",
        np.where(df["event_class"] == "destructive_wind", "wind_kt", ""))
    df.loc[df["event_class"].isin(["flood", "flash_flood"]), "magnitude"] = np.nan

    df["major"] = ((df["deaths"] >= MAJOR_DEATHS)
                   | (df["damage_usd"] >= MAJOR_DAMAGE)
                   | ((df["event_class"] == "tornado") & (fnum >= MAJOR_FSCALE)))

    out = pd.DataFrame({
        "event_id": "se_" + df["EVENT_ID"].astype(int).astype(str),
        "source": "noaa_storm_events",
        "event_class": df["event_class"],
        "event_type": df["EVENT_TYPE"],
        "name": df["CZ_NAME"].astype(str).str.title(),
        "start_utc": df["start_utc"],
        "end_utc": df["end_utc"],
        "lat": df["lat"].round(4),
        "lon": df["lon"].round(4),
        "country": "USA",
        "region": df["STATE"].astype(str).str.title(),
        "deaths": df["deaths"].astype(float),
        "injuries": df["injuries"].astype(float),
        "damage_usd": df["damage_usd"].astype(float),
        "displaced": np.nan,
        "magnitude": df["magnitude"].astype(float),
        "magnitude_type": df["magnitude_type"],
        "geo_precision": df["geo_precision"],
        "major": df["major"],
    })
    stats = {"rows": len(out), "no_tz": n_no_tz, "bad_time": n_bad_time,
             "no_geo_dropped": n_no_geo}
    print(f"Storm Events normalized: {stats}")
    return out, stats


# --------------------------------------------------------------------------
# DFO Global Flood Archive
# --------------------------------------------------------------------------

def load_dfo(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    n_all = len(df)
    df["Began"] = pd.to_datetime(df["Began"], errors="coerce")
    df["Ended"] = pd.to_datetime(df["Ended"], errors="coerce")
    df = df[df["Began"].notna()].copy()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["long"], errors="coerce")
    df = df[df["lat"].notna() & df["lon"].notna()].copy()

    # Source-data QC: DFO ID 278 (Indonesia, Jan 1989) appears twice, once
    # with coordinates in the UK — drop the bad-coordinate copy.  ID 4842
    # appears twice for two genuinely distinct events (Zambia / Mozambique);
    # those are kept and their event_ids uniquified below.
    df = df[~((df["ID"] == 278) & (df["lat"] > 40))].copy()
    dup_rank = df.groupby("ID").cumcount()
    df["uid"] = df["ID"].astype(int).astype(str)
    df.loc[dup_rank > 0, "uid"] = df["uid"] + "b"

    # Dedup vs Storm Events: drop US-only events from 1996 onwards (those
    # floods are covered, with much finer granularity, by Storm Events).
    country = df["Country"].astype(str).str.strip().str.lower()
    other = df["OtherCountry"].astype(str).str.strip().replace("0", "")
    us_only = country.isin(DFO_USA) & (other.str.len() < 2)
    dedup = us_only & (df["Began"] >= "1996-01-01")
    n_dedup = int(dedup.sum())
    df = df[~dedup].copy()

    other = df["OtherCountry"].astype(str).str.strip().replace("0", "")
    cause = df["MainCause"].astype(str)
    # DFO has no literal "flash flood" cause; its short-duration convective
    # cause label is "Brief torrential rain" (with case variants).
    is_flash = cause.str.lower().str.contains("flash|brief torrential")
    sev = pd.to_numeric(df["Severity"], errors="coerce")
    dead = pd.to_numeric(df["Dead"], errors="coerce").fillna(0)
    disp = pd.to_numeric(df["Displaced"], errors="coerce").fillna(0)

    out = pd.DataFrame({
        "event_id": "dfo_" + df["uid"],
        "source": "dfo_flood_archive",
        "event_class": np.where(is_flash, "flash_flood", "flood"),
        "event_type": cause.str.strip(),
        "name": df["Country"].astype(str).str.strip(),
        "start_utc": df["Began"],
        "end_utc": df["Ended"].fillna(df["Began"]) + pd.Timedelta(hours=23, minutes=59),
        "lat": df["lat"].round(4),
        "lon": df["lon"].round(4),
        "country": df["Country"].astype(str).str.strip(),
        "region": (df["Country"].astype(str).str.strip()
                   + np.where(other.str.len() > 1, " + " + other, "")),
        "deaths": dead.astype(float),
        "injuries": np.nan,
        "damage_usd": np.nan,
        "displaced": disp.astype(float),
        "magnitude": sev.astype(float),
        "magnitude_type": "dfo_severity_class",
        "geo_precision": "event_centroid",
        "major": ((dead >= MAJOR_DEATHS) | (sev >= MAJOR_DFO_SEV)
                  | (disp >= MAJOR_DFO_DISP)),
    })
    stats = {"rows": len(out), "input_rows": n_all, "us_dedup_dropped": n_dedup}
    print(f"DFO normalized: {stats}")
    return out, stats


# --------------------------------------------------------------------------
# IBTrACS
# --------------------------------------------------------------------------

IB_USECOLS = ["SID", "SEASON", "BASIN", "NAME", "ISO_TIME", "NATURE",
              "LAT", "LON", "WMO_WIND", "WMO_PRES", "TRACK_TYPE",
              "USA_WIND", "USA_PRES", "LANDFALL"]


def load_ibtracs(path, min_season=1950, min_wind_kt=34):
    print("Parsing IBTrACS (this is a 320 MB csv) ...")
    # keep_default_na=False so the North Atlantic basin code "NA" is not read
    # as missing; blanks are handled explicitly.
    df = pd.read_csv(path, usecols=IB_USECOLS, skiprows=[1], low_memory=False,
                     keep_default_na=False, na_values=[" ", ""])
    # 'main' = final best track; 'PROVISIONAL' = recent seasons (2023+) not
    # yet finalized.  'spur' tracks (alternate centers) are excluded.
    tt = df["TRACK_TYPE"].astype(str)
    df = df[~tt.str.lower().str.contains("spur")].copy()
    df["SEASON"] = pd.to_numeric(df["SEASON"], errors="coerce")
    df = df[df["SEASON"] >= min_season].copy()
    df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"], errors="coerce")
    df["lat"] = pd.to_numeric(df["LAT"], errors="coerce")
    df["lon"] = pd.to_numeric(df["LON"], errors="coerce")
    df["wind"] = pd.to_numeric(df["USA_WIND"], errors="coerce").fillna(
        pd.to_numeric(df["WMO_WIND"], errors="coerce"))
    df["pres"] = pd.to_numeric(df["USA_PRES"], errors="coerce").fillna(
        pd.to_numeric(df["WMO_PRES"], errors="coerce"))
    df = df[df["ISO_TIME"].notna() & df["lat"].notna()].copy()

    n_storms_all = df["SID"].nunique()
    g = df.groupby("SID", sort=True)
    agg = g.agg(start_utc=("ISO_TIME", "min"), end_utc=("ISO_TIME", "max"),
                max_wind=("wind", "max"), min_pres=("pres", "min"),
                season=("SEASON", "first"), basin=("BASIN", "first"),
                name=("NAME", "first"))
    # position at peak intensity (first fix at max wind; track midpoint if no
    # wind data at all)
    idx = df.assign(w=df["wind"].fillna(-1)).groupby("SID")["w"].idxmax()
    peak = df.loc[idx.values, ["SID", "lat", "lon"]].set_index("SID")
    agg = agg.join(peak)

    kept = agg[agg["max_wind"] >= min_wind_kt].copy()
    n_no_wind = int(agg["max_wind"].isna().sum())

    out = pd.DataFrame({
        "event_id": "ib_" + kept.index.astype(str),
        "source": "ibtracs",
        "event_class": "destructive_wind",
        "event_type": "Tropical Cyclone",
        "name": kept["name"].astype(str).str.title(),
        "start_utc": kept["start_utc"],
        "end_utc": kept["end_utc"],
        "lat": kept["lat"].round(4),
        "lon": kept["lon"].round(4),
        "country": "",
        "region": kept["basin"].map(BASIN_NAME).fillna("Unknown basin"),
        "deaths": np.nan,
        "injuries": np.nan,
        "damage_usd": np.nan,
        "displaced": np.nan,
        "magnitude": kept["max_wind"].astype(float),
        "magnitude_type": "max_sustained_wind_kt",
        "geo_precision": "peak_intensity_fix",
        "major": kept["max_wind"] >= MAJOR_TC_WIND,
    }).reset_index(drop=True)
    stats = {"rows": len(out), "storms_since_1950": n_storms_all,
             "dropped_no_wind_or_weak": n_storms_all - len(out),
             "storms_without_wind_data": n_no_wind}
    print(f"IBTrACS normalized: {stats}")
    return out, stats


# --------------------------------------------------------------------------
# Anchor events (historically significant, used for case studies)
# --------------------------------------------------------------------------

ANCHORS = [
    # (label, source, class, query dict)
    ("Hurricane Katrina 2005 (Cat 5, Gulf Coast)", "ibtracs", dict(name="Katrina", season=2005)),
    ("Hurricane Andrew 1992 (Cat 5, FL)", "ibtracs", dict(name="Andrew", season=1992)),
    ("Hurricane Mitch 1998 (Central America)", "ibtracs", dict(name="Mitch", season=1998)),
    ("Hurricane Sandy 2012 (NE US)", "ibtracs", dict(name="Sandy", season=2012)),
    ("Hurricane Harvey 2017 (TX floods)", "ibtracs", dict(name="Harvey", season=2017)),
    ("Hurricane Irma 2017 (FL/Caribbean)", "ibtracs", dict(name="Irma", season=2017)),
    ("Hurricane Maria 2017 (Puerto Rico)", "ibtracs", dict(name="Maria", season=2017)),
    ("Hurricane Michael 2018 (Cat 5, FL)", "ibtracs", dict(name="Michael", season=2018)),
    ("Hurricane Dorian 2019 (Bahamas)", "ibtracs", dict(name="Dorian", season=2019)),
    ("Hurricane Ida 2021 (LA + NE flash floods)", "ibtracs", dict(name="Ida", season=2021)),
    ("Hurricane Ian 2022 (Cat 5, FL)", "ibtracs", dict(name="Ian", season=2022)),
    ("Typhoon Haiyan 2013 (Philippines)", "ibtracs", dict(name="Haiyan", season=2013)),
    ("Cyclone Nargis 2008 (Myanmar)", "ibtracs", dict(name="Nargis", season=2008)),
    ("Cyclone Idai 2019 (Mozambique)", "ibtracs", dict(name="Idai", season=2019)),
    ("Joplin MO EF5 tornado 2011-05-22", "se_tor", dict(state="Missouri", date=("2011-05-22", "2011-05-23"), fmin=5)),
    ("Moore OK EF5 tornado 2013-05-20", "se_tor", dict(state="Oklahoma", date=("2013-05-20", "2013-05-21"), fmin=5)),
    ("Bridge Creek-Moore OK F5 1999-05-03", "se_tor", dict(state="Oklahoma", date=("1999-05-03", "1999-05-04"), fmin=5)),
    ("2011-04-27 Super Outbreak (AL EF4+)", "se_tor", dict(state="Alabama", date=("2011-04-27", "2011-04-28"), fmin=4)),
    ("Quad-State (Mayfield KY) EF4 2021-12-10", "se_tor", dict(state="Kentucky", date=("2021-12-10", "2021-12-12"), fmin=4)),
    ("Fort Collins CO flash flood 1997-07-28", "se_ff", dict(state="Colorado", date=("1997-07-28", "1997-07-30"))),
    ("Boulder CO flash flood 2013-09-11", "se_ff", dict(state="Colorado", date=("2013-09-11", "2013-09-14"))),
    ("West Virginia flash flood 2016-06-23", "se_ff", dict(state="West Virginia", date=("2016-06-23", "2016-06-25"))),
    ("Eastern Kentucky flash flood 2022-07-27", "se_ff", dict(state="Kentucky", date=("2022-07-27", "2022-07-30"))),
    ("TS Allison Houston flooding 2001-06", "se_ff", dict(state="Texas", date=("2001-06-05", "2001-06-11"))),
    ("Texas Hill Country flash flood 2025-07-04", "se_ff", dict(state="Texas", date=("2025-07-04", "2025-07-06"))),
    ("June 2012 mid-Atlantic derecho", "se_wind", dict(state="West Virginia", date=("2012-06-29", "2012-07-01"))),
    ("August 2020 Midwest derecho (Iowa)", "se_wind", dict(state="Iowa", date=("2020-08-10", "2020-08-12"))),
    ("Mississippi River Great Flood 1993 (DFO)", "dfo", dict(country="USA", date=("1993-05-01", "1993-08-31"))),
    ("Yangtze flood 1998 (DFO)", "dfo", dict(country="China", date=("1998-06-01", "1998-09-30"))),
    ("Elbe flood 2002 (DFO, Germany/Czechia)", "dfo", dict(country="Germany", date=("2002-08-01", "2002-08-31"))),
    ("Central Europe flood 2013 (DFO)", "dfo", dict(country="Germany", date=("2013-05-25", "2013-06-30"))),
    ("Pakistan floods 2010 (DFO)", "dfo", dict(country="Pakistan", date=("2010-07-01", "2010-09-30"))),
    ("Thailand floods 2011 (DFO)", "dfo", dict(country="Thailand", date=("2011-06-01", "2011-12-31"))),
    ("Ahr valley flood 2021 (DFO, Germany)", "dfo", dict(country="Germany", date=("2021-07-01", "2021-07-31"))),
    ("Zhengzhou (Henan) flood 2021 (DFO)", "dfo", dict(country="China", date=("2021-07-01", "2021-08-15"))),
]


def find_anchor(cat, source, q):
    if source == "ibtracs":
        m = cat[(cat["source"] == "ibtracs")
                & (cat["name"].str.upper() == q["name"].upper())
                & (cat["start_utc"].dt.year.isin([q["season"] - 1, q["season"]]))]
    else:
        t0, t1 = pd.Timestamp(q["date"][0]), pd.Timestamp(q["date"][1]) + pd.Timedelta(days=1)
        if source == "dfo":
            m = cat[(cat["source"] == "dfo_flood_archive")
                    & cat["country"].str.contains(q["country"], case=False, na=False)
                    & (cat["start_utc"] < t1) & (cat["end_utc"] >= t0)]
        else:
            cls = {"se_tor": "tornado", "se_ff": "flash_flood",
                   "se_wind": "destructive_wind"}[source]
            m = cat[(cat["source"] == "noaa_storm_events")
                    & (cat["event_class"] == cls)
                    & (cat["region"] == q["state"])
                    & (cat["start_utc"] >= t0) & (cat["start_utc"] < t1)]
            if "fmin" in q:
                m = m[m["magnitude"] >= q["fmin"]]
    if len(m) == 0:
        return None
    best = m.sort_values(["major", "deaths", "damage_usd", "magnitude"],
                         ascending=False).iloc[0]
    return best, len(m)


def write_anchor_report(cat, out_dir):
    lines = ["# Anchor events (verified present in events.parquet)", "",
             "| # | Event | Found | Matching rows | Representative event_id | Class | Start (UTC) | Deaths | Magnitude |",
             "|---|-------|-------|---------------|--------------------------|-------|-------------|--------|-----------|"]
    n_ok = 0
    for i, (label, source, q) in enumerate(ANCHORS, 1):
        r = find_anchor(cat, source, q)
        if r is None:
            lines.append(f"| {i} | {label} | MISSING | 0 | - | - | - | - | - |")
            continue
        best, n = r
        n_ok += 1
        lines.append(
            f"| {i} | {label} | yes | {n} | `{best['event_id']}` | "
            f"{best['event_class']} | {best['start_utc']:%Y-%m-%d %H:%M} | "
            f"{'' if pd.isna(best['deaths']) else int(best['deaths'])} | "
            f"{'' if pd.isna(best['magnitude']) else best['magnitude']} |")
    lines += ["", f"{n_ok}/{len(ANCHORS)} anchors found."]
    path = os.path.join(out_dir, "ANCHORS.md")
    with open(path, "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Anchor verification: {n_ok}/{len(ANCHORS)} found -> {path}")
    return n_ok


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--raw-dir", default=os.path.join(here, "raw"))
    ap.add_argument("--out-dir", default=here)
    ap.add_argument("--skip-download", action="store_true",
                    help="assume raw files are already present")
    args = ap.parse_args()

    if not args.skip_download:
        download_all(args.raw_dir)

    se, se_stats = load_storm_events(os.path.join(args.raw_dir, "stormevents"))
    dfo, dfo_stats = load_dfo(os.path.join(args.raw_dir, "dfo", "FloodArchive.csv"))
    ib, ib_stats = load_ibtracs(os.path.join(args.raw_dir, "ibtracs", "ibtracs_all.csv"))

    cat = pd.concat([se, dfo, ib], ignore_index=True)
    cat = cat.sort_values("start_utc").reset_index(drop=True)
    for c in ["event_id", "source", "event_class", "event_type", "name",
              "country", "region", "magnitude_type", "geo_precision"]:
        cat[c] = cat[c].astype("string")
    cat["major"] = cat["major"].fillna(False).astype(bool)

    assert cat["event_id"].is_unique, "event_id collision"
    assert cat["event_class"].isin(
        ["flash_flood", "flood", "destructive_wind", "tornado"]).all()

    out_parquet = os.path.join(args.out_dir, "events.parquet")
    cat.to_parquet(out_parquet, index=False)

    # ~200-row stratified sample for eyeballing
    rng = 42
    parts = []
    for (_, _), grp in cat.groupby(["source", "event_class"]):
        parts.append(grp.sample(min(len(grp), 29), random_state=rng))
    sample = pd.concat(parts).sort_values("start_utc")
    sample.to_csv(os.path.join(args.out_dir, "events_sample.csv"), index=False,
                  lineterminator="\n")

    # summary
    print("\n=== catalog summary ===")
    print(cat.groupby(["source", "event_class"]).size())
    print("\nby decade:")
    print(cat.groupby([cat["start_utc"].dt.year // 10 * 10, "event_class"])
          .size().unstack(fill_value=0))
    print(f"\nmajor events: {int(cat['major'].sum())} / {len(cat)}")
    print(f"wrote {out_parquet} ({len(cat)} events)")

    write_anchor_report(cat, args.out_dir)


if __name__ == "__main__":
    main()
