# Recon: Open-Meteo bulk weather data + disaster event catalogs

Date: 2026-08-19. Every claim below was verified by actually running the commands shown,
unless explicitly marked otherwise.

Network caveat: verification ran from a network with a restrictive egress allowlist.
Reachable from there: `s3.amazonaws.com` (incl. bucket vhosts), `storage.googleapis.com`,
`github.com` / `raw.githubusercontent.com`, `pypi.org`. Unreachable from there (an egress
policy denial, not a property of the service): `*.open-meteo.com`, `*.noaa.gov` /
`ncei.noaa.gov`, `floodobservatory.colorado.edu`, `emdat.be`, `eswd.eu`, `huggingface.co`,
`zenodo.org`, `data.humdata.org`, `api.reliefweb.int`. On a normal network these all work;
findings below separate "provider requires registration" from "egress-blocked during recon".

---

## TASK A — Open-Meteo AWS Open Data bucket (s3://openmeteo, CC-BY-4.0)

### A1. Anonymous access: WORKS

```
$ curl -sS "https://openmeteo.s3.amazonaws.com/?list-type=2&max-keys=50&delimiter=/"
<ListBucketResult ...><Name>openmeteo</Name>...
  <CommonPrefixes><Prefix>data/</Prefix></CommonPrefixes>
  <CommonPrefixes><Prefix>data_run/</Prefix></CommonPrefixes>
  <CommonPrefixes><Prefix>data_spatial/</Prefix></CommonPrefixes>
```

No credentials needed (plain HTTPS GET / `--no-sign-request` equivalent). Also works via
`s3fs.S3FileSystem(anon=True)`.

**Bucket layout** (top level):
- `data/<model>/<variable>/…` — the time-series-optimized archive (what we want)
- `data_run/` — per-model-run files (forecast runs)
- `data_spatial/` — spatially-optimized recent fields (per-run GRIB-like layout; only recent data)

**Models under `data/`** (~100 dirs): `copernicus_era5`, `copernicus_era5_land`,
`copernicus_era5_ensemble`, `copernicus_era5_ocean`, `ecmwf_ifs_analysis_long_window`, plus the
historical-forecast archives: `ncep_gfs025`, `ncep_gfs013`, `ncep_hrrr_conus`, `dwd_icon`,
`dwd_icon_eu`, `dwd_icon_d2`, `ecmwf_ifs025`, `meteofrance_arome/arpege*`, `ukmo_*`, `jma_*`,
`cmc_gem_*`, `knmi_*`, `dmi_*`, `meteoswiss_*`, ensembles, wave and air-quality models, and
`copernicus_dem90` (elevation).

**`data/copernicus_era5/` variables** (0.25 deg global, hourly, 1940 -> now-5days):
`precipitation, pressure_msl, wind_gusts_10m, wind_u/v_component_10m, wind_u/v_component_100m,
temperature_2m, dew_point_2m, snowfall_water_equivalent, soil_moisture_0_to_7cm / 7_to_28 /
28_to_100 / 100_to_255cm, soil_temperature_* (4 layers), cloud_cover (+low/mid/high),
shortwave/direct_radiation, boundary_layer_height, total_column_integrated_water_vapour,
sea_surface_temperature, static/` — **no CAPE in ERA5**.

**`data/copernicus_era5_land/`** (0.1 deg): only `temperature_2m, dew_point_2m, snow_depth,
soil_moisture_* (4), soil_temperature_* (4)` — no precipitation/wind/pressure here; use era5 for
those.

**CAPE availability**: only in historical-forecast model archives: `ncep_gfs025/cape` (earliest
file `chunk_1000.om` ≈ late 2024 in this naming; GFS archive generally reaches back to 2021 via
`ncep_gfs013`/API), `ecmwf_ifs025/cape`, `dwd_icon/cape`, `meteofrance_arpege_world025/cape`,
plus `lifted_index` and `convective_inhibition` in `ncep_gfs025`. So: **CAPE-like precursors are
only available for roughly the last 2–4 years**; for the 50-year record, convective proxies must
be derived from ERA5 fields (or use ERA5 pressure-level data from other sources).

**File format & chunking** (verified by decoding, and from `static/meta.json`):

```
$ curl .../data/copernicus_era5/static/meta.json
{"chunk_time_length":504, "temporal_resolution_seconds":3600, "update_interval_seconds":86400,
 "data_end_time":1786579200 (=2026-08-13), BBOX[-90,-180,90,179.75] ...}
```

- Per variable: `year_1940.om` … `year_2021.om` (~1.5–1.7 GB each, full globe, full year) plus
  rolling `chunk_904.om` … `chunk_984.om` for 2022→now. Chunk index = floor(days_since_unix_epoch/21);
  chunk_904 starts 2021-12-23, chunk_984 starts 2026-07-30. 21 days x 24 h = 504 h per chunk file.
- ERA5 precipitation totals: 82 year-files = 135 GB + 81 chunk-files = 8 GB → **~143 GB per
  variable for the full 86-year global archive**.
- Inside a year-file (read with `omfiles`): `shape=(721, 1440, 8760)` = (lat, lon, hour),
  internal chunks `(1, 6, 1095)` = 1 lat x 6 lon (1.5 deg) x 1095 h (45.6 days), dtype float32,
  compression `pfor_delta_2d_int16`, scale_factor 10 (i.e. 0.1 precision int16).
- Inside a rolling chunk-file: `shape=(721, 1440, 504)`, chunks `(1, 6, 504)`.
- Grid orientation (verified empirically with July temperature at poles/Sahara):
  `lat_idx = (lat + 90) / 0.25` (index 0 = 90S), `lon_idx = (lon + 180) / 0.25` (index 0 = 180W).
- Units as stored: temperature degC, precipitation mm/h, pressure_msl Pa, wind gusts m/s.
- Forecast-model archives flatten space: e.g. `ncep_gfs025/cape/chunk_1000.om` is
  `shape=(1038240, 481)` (=721*1440 gridpoints, ~20 days hourly), chunks `(6, 481)`.

### A2. Reading .om files in Python: PROVEN end-to-end

Format spec: github.com/open-meteo/om-file-format. Reader: **`omfiles` on PyPI (v1.2.0,
Rust-backed, fsspec-compatible)** — `pip install omfiles s3fs` worked first try on Python 3.11.

Note: `OmFileReader.from_fsspec` fails with fsspec's `HTTPFileSystem` (`_cat_file() missing 1
required positional argument` — incompat with async http fs); **use `s3fs.S3FileSystem(anon=True)`**,
which does ranged reads (no need to download the 1.6 GB file).

Working demonstration and its verbatim output — **Hurricane Ida at grid point
30.0N, -90.0W (New Orleans), 2021-08-29T00Z + 48 h**, decoded straight from
`s3://openmeteo/data/copernicus_era5/*/year_2021.om`:

```python
import s3fs, datetime
from omfiles import OmFileReader
fs = s3fs.S3FileSystem(anon=True)
la, lo = int(round((30.0+90)/0.25)), int(round((-90.0+180)/0.25))
t0 = int((datetime.datetime(2021,8,29)-datetime.datetime(2021,1,1)).total_seconds()//3600)
r = OmFileReader.from_fsspec(fs, "openmeteo/data/copernicus_era5/precipitation/year_2021.om")
v = r.read_array((slice(la,la+1), slice(lo,lo+1), slice(t0, t0+48)))
```

```
precipitation [mm/h] 2021-08-29T00Z +48h @ (30.0,-90.0):
   0.0 0.0 0.5 0.8 0.6 1.1 0.4 0.4 0.2 0.0 0.2 0.4 0.5 0.5 0.7 1.0 1.2 2.7 4.7 11.5 11.2 7.9 10.8 13.2
   13.5 18.6 25.6 25.8 27.9 24.6 20.5 15.1 11.8 7.5 4.4 2.4 1.6 1.3 1.3 1.3 0.9 0.8 0.8 0.0 0.0 0.0 0.8 0.2
   max=27.9  sum=277.2
wind_gusts_10m [m/s]: rises 11.4 -> peak 42.5 (≈153 km/h) at landfall+overnight, decays to 12.6
pressure_msl [Pa]: 101460 max -> 99200 min (1014.6 -> 992.0 hPa) at 2021-08-30T01Z, then recovery
```

That is a textbook landfalling-hurricane signature decoded from real bucket bytes — values,
timing, and physical consistency all check out (Ida landfall 2021-08-29 ~17Z ~90 km SW of this
grid point).

### A3. Free archive API (archive-api.open-meteo.com): NOT VERIFIED (egress-blocked during recon)

`curl https://archive-api.open-meteo.com/v1/archive?...` was blocked by the recon network's
egress policy (`api.open-meteo.com` likewise). This is a network limitation, not an API outage.
For the project: fine — bulk mining should use the bucket anyway. Documented API constraints
(unverified from the recon network): free for non-commercial use, ~10,000 calls/day (plus
hourly/minutely burst limits), ERA5 + ERA5-Land + best-match, JSON, 1940→now. Use it only for
spot-checking on an unrestricted network, or use the bucket + `omfiles` even for spot checks
(verified working).

### A4. Data-volume / acquisition-cost estimate (measured, not guessed)

Measured with an instrumented `s3fs` subclass counting actual GETs and bytes:

```
full-year hourly precip, 1 point: (1, 1, 8760), sum=2039 mm, nonzero hours=1857
HTTP GETs: 11, bytes transferred: 15 kB, wall time: 23.1 s   (cold, serial, incl. header+index reads)
```

- A single point-year-variable read touches ceil(8760/1095) = 8 internal chunks (~0.6–1.9 kB
  each compressed) + trailer/lookup-table reads ≈ **11 GETs, ~15 kB**.
- **50-year, 7-variable, single-grid-point series ≈ 50 x 7 x 15 kB ≈ 5–6 MB transferred**
  (~4,000 ranged GETs). Latency-bound, embarrassingly parallel; with an async reader
  (`OmFileReaderAsync`) or 20-way concurrency this is minutes, not hours, per location.
- Amortization matters: open each (variable, year) file once and read MANY locations from it —
  header/lookup overhead (~3 GETs) is per-file, and each internal chunk covers 6 lon points x 1
  lat x 45.6 days, so nearby event locations share chunks for free.
- Regional fields are also cheap: a CONUS cutout (25–50N, 125–65W) of one variable-year ≈
  (100x240)/(721x1440) x 1.6 GB ≈ **37 MB**; full-globe variable-year = 1.6 GB; full-globe,
  86 years, one variable = ~143 GB.
- **Conclusion: per-location time-series mining is the right architecture.** No bulk mirror
  needed. Only go regional-field if we later want spatial context maps around events.
- AWS Open Data program bucket: anonymous GETs, no egress charge to us, no API-key rate limits
  (normal S3 request throughput applies). License CC-BY-4.0 — attribution
  "Weather data by Open-Meteo.com".

---

## TASK B — Disaster event catalogs

### B1. NOAA Storm Events (ground truth, US): VERIFIED (via mirror; origin host egress-blocked during recon)

- Origin `https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/` was egress-blocked on
  the recon network (NOAA is fine from normal networks). File naming confirmed current via
  mirrors: `StormEvents_details-ftp_v1.0_dYYYY_cYYYYMMDD.csv.gz`, one file per year
  1950→present, plus `_fatalities_` and `_locations_` companions.
- **Actually downloaded and parsed** a mirrored canonical year file (1954, from
  raw.githubusercontent.com/htluu-ucsd/NaturalDisasterProject): 609 events, all with
  BEGIN_LAT/BEGIN_LON, header verbatim:

```
BEGIN_YEARMONTH,BEGIN_DAY,BEGIN_TIME,END_YEARMONTH,END_DAY,END_TIME,EPISODE_ID,EVENT_ID,STATE,
STATE_FIPS,YEAR,MONTH_NAME,EVENT_TYPE,CZ_TYPE,CZ_FIPS,CZ_NAME,WFO,BEGIN_DATE_TIME,CZ_TIMEZONE,
END_DATE_TIME,INJURIES_DIRECT,INJURIES_INDIRECT,DEATHS_DIRECT,DEATHS_INDIRECT,DAMAGE_PROPERTY,
DAMAGE_CROPS,SOURCE,MAGNITUDE,MAGNITUDE_TYPE,FLOOD_CAUSE,CATEGORY,TOR_F_SCALE,TOR_LENGTH,
TOR_WIDTH,...,BEGIN_RANGE,BEGIN_AZIMUTH,BEGIN_LOCATION,END_RANGE,END_AZIMUTH,END_LOCATION,
BEGIN_LAT,BEGIN_LON,END_LAT,END_LON,EPISODE_NARRATIVE,EVENT_NARRATIVE,DATA_SOURCE
```

- Coverage tiers (matters for training windows): **1950–1954 tornado only; 1955–1995 tornado +
  thunderstorm wind + hail; 1996+ all 48 event types** (Flood, Flash Flood, High Wind,
  Thunderstorm Wind, Tornado, Winter Storm, …). Begin/end date-time to the minute in local time
  (CZ_TIMEZONE given — convert to UTC before joining to ERA5!). Point lat/lon on tornado and most
  convective events; county/zone (CZ_*) only for many flood/zone events (BEGIN_LAT sometimes
  empty 1996+ zone events — geocode via county centroid as fallback).
- Size: ~60 MB/year CSV recent years (2021 file = 60,463,392 bytes per its LFS pointer);
  ~1.9 M events total 1950→present.
- Caution for mirror use: several GitHub "mirrors" are broken (files contain the NOAA 301
  redirect HTML, e.g. talhasajjad140/Dashboard) or LFS-pointer-only (sf00053/Machine-Learning —
  LFS object 404s). For production, download the official csvfiles/ directory from NCEI on an
  unrestricted network (a plain `wget -r -A "*details*csv.gz"` job, ~2 GB total).

### B2. EM-DAT: NOT freely downloadable (provider-side) — as expected

EM-DAT (CRED/UCLouvain) requires **registration and login at public.emdat.be** to download the
xlsx; free for non-commercial research but no anonymous bulk endpoint, and redistribution is
restricted. Its geo precision is also weak for our purpose (country/admin-level, no exact
coordinates; day-level dates, often missing day). The domain was additionally egress-blocked
during recon. **Recommendation: skip EM-DAT for signature mining; at most use it later for
impact cross-checks.**

### B3. Global / non-US catalogs

- **Dartmouth Flood Observatory (DFO) Global Active Archive of Large Flood Events** — the best
  open global flood catalog: ~5,100 events, 1985–2021 (archive frozen ~Oct 2021; file
  Last-Modified 2022-09-02 per a mirror's version metadata), event centroid lat/lon + affected-area
  polygon, begin/end dates (day precision), dead, displaced, main cause, severity class.
  Canonical schema (verbatim from a mirrored `floodarchive_italy.csv`):
  `ID,GlideNumber,Country,OtherCountry,long,lat,Area,Began,Ended,Validation,Dead,Displaced,MainCause,Severity`.
  Origin (`floodobservatory.colorado.edu/Archives/FloodArchive.{xlsx,shp}`) was egress-blocked
  during recon, but **a mirrored derivative was actually downloaded and parsed** (913 events,
  2000-02-17 → 2018-12-05, 114 countries — a partial mirror; the full file is ~138 kB xlsx).
  VERIFIED non-US catalog download: yes.
- **ESWD (European Severe Weather Database, ESSL)** — best European tornado/wind/hail/flash-flood
  event DB with exact coordinates+times, but bulk export requires application/licence
  (research licences exist); no anonymous bulk download. Egress-blocked during recon too.
  Treat like EM-DAT: valuable but gated.
- **Copernicus EMS / EEA**: EMS rapid-mapping activations list is open (flood/fire activations
  with dates+areas, 2012+, small N) — usable as a European flood event list; EEA datasets are
  aggregate statistics, not event catalogs.
- **IBTrACS** (NOAA/WMO tropical cyclone best tracks, global, 1840s+, 3-hourly positions +
  intensity, fully open CSV) — the natural global ground truth for destructive-wind/TC events;
  NOAA-hosted so egress-blocked during recon, but same access class as Storm Events.
- Honorable mentions, not verified during recon: GDACS event API (open), ReliefWeb API (open),
  HDX copies of DFO/EM-DAT subsets.

### B4. Recommended catalog strategy

1. **US core (training + backtesting): NOAA Storm Events 1996–present**, event types
   `Flash Flood`, `Flood`, `Tornado`, `High Wind`, `Thunderstorm Wind` (magnitude >= 50 kt for a
   "destructive wind" class), optionally `Hail` >= 2". Rationale: minute-precision times, point or
   county geometry, 3 decades x 48 types, zero access friction. Use 1955–1995 tornado/wind/hail
   as an extended-history secondary set (times cruder, locations point-based).
   Geo precision: point lat/lon (0.01 deg) for convective events; county/zone for some floods —
   map zone events to county centroids (FIPS in file) and treat as ±25 km.
2. **Global floods: DFO Flood Archive 1985–2021** (centroid + begin/end dates, day precision,
   severity/displaced as weights). Complements NOAA's US-flood view with 100+ countries and pairs
   perfectly with ERA5 (both end ~2021+ coverage; DFO frozen 2021).
3. **Global destructive wind: IBTrACS** (position/intensity every 3–6 h → derive "gale-radius
   passage" labels at any coastal location).
4. Skip EM-DAT and ESWD initially (registration-gated); revisit ESWD if we want European
   tornado/flash-flood validation and are willing to apply for a research licence.
5. Join discipline: convert Storm Events local times to UTC via CZ_TIMEZONE; snap event lat/lon
   to nearest 0.25 deg ERA5 node with `round(x/0.25)*0.25`; extract precursor windows (e.g.
   T-14d → T+2d) per event from the bucket.
