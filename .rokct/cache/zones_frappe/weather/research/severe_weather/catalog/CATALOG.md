# Ground-Truth Disaster Event Catalog

Normalized, QC'd catalog of severe-weather events in four classes —
`flash_flood`, `flood` (riverine/areal/coastal), `destructive_wind`
(incl. tropical cyclones), `tornado` — built for signature mining and
backtesting of the early-warning system.

- **`events.parquet`** — 817,216 events, 21.8 MB (pandas/pyarrow readable)
- **`events_sample.csv`** — 203-row stratified sample (up to 29 rows per
  source x class stratum) for eyeballing
- **`build_catalog.py`** — reproducible build: downloads all raw files from
  the URLs below, validates them by parsing, rebuilds the parquet
  (`python3 build_catalog.py`; `--skip-download` reuses `raw/`)
- **`ANCHORS.md`** — 35 named historically significant events verified
  present in the catalog (all 35 found), for anchoring case studies
- **`raw/`** — the validated raw source files (1.8 GB; **not committed** —
  `build_catalog.py` re-downloads and re-validates them)

## Schema

| column | notes |
|---|---|
| `event_id` | unique; namespaced `se_<EVENT_ID>` / `dfo_<ID>` / `ib_<SID>` |
| `source` | `noaa_storm_events`, `dfo_flood_archive`, `ibtracs` |
| `event_class` | `flash_flood`, `flood`, `destructive_wind`, `tornado` |
| `event_type` | original label (NOAA EVENT_TYPE, DFO MainCause, "Tropical Cyclone") |
| `name` | county/zone name (NOAA), country (DFO), storm name (IBTrACS) |
| `start_utc`, `end_utc` | event window, UTC (see time handling below) |
| `lat`, `lon` | see coordinate handling / `geo_precision` below |
| `country`, `region` | `USA` + state for NOAA; country (+ other countries) for DFO; basin for IBTrACS |
| `deaths`, `injuries` | NOAA: direct+indirect; DFO: `Dead`; IBTrACS: not available (NaN) |
| `damage_usd` | NOAA only: property + crop damage (parsed from `10.00K/2.5M/1.2B` strings) |
| `displaced` | DFO only |
| `magnitude`, `magnitude_type` | tornado: F/EF number; wind: measured/estimated gust kt; TC: max sustained wind kt; DFO: severity class (1/1.5/2) |
| `geo_precision` | `point`, `cz_centroid`, `zone_name_centroid`, `state_centroid`, `event_centroid` (DFO), `peak_intensity_fix` (IBTrACS) |
| `major` | high-impact flag, defined below |

## Sources, acquisition paths, licensing

The build environment's network allowlist blocks the NOAA (`*.noaa.gov`),
DFO (`floodobservatory.colorado.edu`) and EM-DAT origin hosts, so
acquisition used verified public mirrors on reachable hosts
(`raw.githubusercontent.com`, `media.githubusercontent.com`). **Every file was validated by parsing it and
checking row counts/schema/date ranges** — several candidate GitHub mirrors
are broken (files containing NOAA's 301-redirect HTML, or dead git-lfs
pointers) and were rejected by that validation. No Storm Events / IBTrACS
copy exists in the AWS Open Data or GCS public buckets (checked:
`noaa-swdi-pds` holds only SWDI hail/mesocyclone/TVS/NLDN products, and the
AWS open-data registry has no Storm Events or IBTrACS entry).

### 1. NOAA Storm Events (details files), 1996-2025

- Canonical NCEI product: `StormEvents_details-ftp_v1.0_dYYYY_cYYYYMMDD.csv`
  from `ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/` (blocked here).
- Mirror used for 1996-2024 (29 files, complete canonical copies, verified
  against the NCEI schema and plausible per-year row counts of 42k-79k):
  `https://raw.githubusercontent.com/htluu-ucsd/NaturalDisasterProject/main/data/ncei_noaa/<file>`
  (exact per-year file names, incl. `c`-revision tags, are listed in
  `build_catalog.py`).
- 2025 (revision `c20251216`, covers Jan-Sep 2025 — **partial year**):
  `https://raw.githubusercontent.com/mattialodi0/progA3I/main/NCEI_datasets/storm_events/StormEvents_details-ftp_v1.0_d2025_c20251216.csv`
- License: US Government work, public domain.
- Event types kept and mapped: Flash Flood -> `flash_flood`; Flood, Coastal
  Flood -> `flood`; Tornado -> `tornado`; High Wind, Thunderstorm Wind,
  Strong Wind, Marine High Wind, Hurricane (Typhoon)/Hurricane/Typhoon,
  Tropical Storm -> `destructive_wind`.
- Per-year kept-event counts are smooth (19k-35k/yr, no gaps); all 30 year
  files parsed with 0 rows lost to bad timestamps and 0 rows lost to missing
  geometry (after the centroid fallbacks below).

### 2. DFO Global Flood Archive, 1985 - Oct 2021 (frozen)

- Canonical: `floodobservatory.colorado.edu/Archives/FloodArchive.xlsx`
  (blocked here). Mirror used — a **complete** copy of the final frozen
  archive (5,130 events, 1985-01-01 to 2021-10-06, matching the ~5,100-event
  full archive; much fuller than the 913-event subset found during recon):
  `https://raw.githubusercontent.com/kandread/cee597j/master/homework/homework05/FloodArchive.csv`
- License: DFO asks for citation (Brakenridge, G.R., "Global Active Archive
  of Large Flood Events", Dartmouth Flood Observatory, Univ. of Colorado);
  open for research use.
- 241 country labels; day-precision dates; event-centroid coordinates.

### 3. IBTrACS v04 (global tropical cyclones), 1950 - Jun 2024

- Canonical: NCEI IBTrACS v04 `ibtracs.ALL.list` CSV (blocked here).
  Mirror used — full global archive (322 MB, complete column set, updated
  through June 2024), stored under git-lfs and fetched from the LFS media
  endpoint:
  `https://media.githubusercontent.com/media/tomerburg/IBTrACS/main/ibtracs.csv`
- License: US Government work / WMO data, public domain; cite Knapp et al.
  (2010), IBTrACS.
- One catalog event per storm (SID), seasons >= 1950, `spur` tracks dropped
  (both final `main` and 2023+ `PROVISIONAL` tracks kept), storms with max
  sustained wind < 34 kt or no wind data dropped (2,382 of 8,021 storms).
  `lat`/`lon` = first fix at peak intensity; `start_utc`/`end_utc` = first/
  last track fix; `magnitude` = lifetime max sustained wind (USA_WIND,
  falling back to WMO_WIND), in kt.
- Basin coverage: West Pacific 1,871; East Pacific 1,135; North Atlantic
  937; South Indian 837; South Pacific 602; North Indian 254; South
  Atlantic 3.

### 4. EM-DAT / ESWD — not included

Registration-gated (and their hosts are outside the network allowlist);
geolocation is
admin-level only. Revisit only for impact cross-checks.

## Counts

By source and class:

| source | flash_flood | flood | destructive_wind | tornado | total |
|---|---|---|---|---|---|
| noaa_storm_events | 109,809 | 73,920 | 580,483 | 42,463 | 806,675 |
| dfo_flood_archive | 189 | 4,713 | — | — | 4,902 |
| ibtracs | — | — | 5,639 | — | 5,639 |
| **total** | **109,998** | **78,633** | **586,122** | **42,463** | **817,216** |

By decade (start_utc):

| decade | destructive_wind | flash_flood | flood | tornado |
|---|---|---|---|---|
| 1950s | 445 | 0 | 0 | 0 |
| 1960s | 545 | 0 | 0 | 0 |
| 1970s | 728 | 0 | 0 | 0 |
| 1980s | 880 | 0 | 383 | 0 |
| 1990s | 59,727 | 12,496 | 9,632 | 5,496 |
| 2000s | 171,531 | 34,574 | 22,173 | 14,117 |
| 2010s | 205,800 | 38,242 | 31,152 | 13,738 |
| 2020s | 146,466 | 24,686 | 15,293 | 9,112 |

Pre-1990 rows are IBTrACS TCs (global) and DFO floods (1985+) only — Storm
Events coverage starts 1996 by design (that is when NOAA began recording all
48 event types).

Geographic coverage: US at county/point granularity 1996-2025 (all four
classes); global floods 1985-2021 (DFO, 241 country labels, incl. the
European flood record); global tropical cyclones 1950-2024 (IBTrACS, all
basins). Known blind spots: non-US tornadoes and non-TC destructive wind
outside the US (ESWD is gated), global floods after Oct 2021 (DFO frozen),
US events Oct-Dec 2025 (revision lag).

## QC decisions

1. **Time zones.** Storm Events times are local *standard* time with the
   zone in `CZ_TIMEZONE`. A numeric suffix (`CST-6`, `GST10`) is used as the
   UTC offset directly; bare codes (`CST`, `EST`, ... in 1996-2000 files) go
   through an explicit standard-offset map. All 806,675 kept rows converted;
   0 unparseable timezones, 0 invalid timestamps. Spot-checked against
   reality (Joplin 2011 tornado converts to 22:40 UTC; observed 22:34 UTC
   touchdown). DFO days are day-precision: `start_utc` = began 00:00,
   `end_utc` = ended 23:59. IBTrACS ISO_TIME is already UTC.
2. **Coordinates.** Priority: (a) `point` — event BEGIN_LAT/LON (619,641
   rows; (0,0) and out-of-range coords rejected); (b) `cz_centroid` — mean
   of point-event coords in the same (state, CZ_TYPE, CZ_FIPS) county/zone
   (68,462); (c) `zone_name_centroid` — NWS zone numbers do not map to
   county FIPS, so zone names are matched to county names in the same state,
   exact then longest-substring (98,992); (d) `state_centroid` — mean of the
   state's point events (19,580, 2.4%; treat as +-300 km). DFO events carry
   the archive's event centroid (`event_centroid`); IBTrACS events the peak-
   intensity fix (`peak_intensity_fix`). Filter on `geo_precision` when a
   mining task needs tight geolocation.
3. **Dedup across sources.** (a) DFO US-only events beginning >= 1996-01-01
   are dropped (227) — those floods are in Storm Events at much finer
   granularity; DFO US events before 1996 and all multi-country events are
   kept. (b) IBTrACS storms vs Storm Events Hurricane/Tropical Storm rows
   are *deliberately both kept*: they are different granularities (one
   storm-level track event vs county-level impact segments) and carry
   different labels; event_ids are namespaced, and the storm-level record is
   the canonical TC ground truth. (c) Within DFO, duplicate ID 278 had one
   copy with wrong-continent coordinates (dropped); duplicate ID 4842 is two
   real events (Zambia/Mozambique) — kept with uniquified ids.
4. **Damage strings** (`10.00K`, `2.5M`, `1.2B`, bare `K`) parsed with an
   H/K/M/B/T multiplier table; bare suffixes (unknown magnitude) -> NaN.
   Total parsed damage: $438B over 1996-2025.
5. **Validation of downloads**: every file is parsed before use; HTML
   bodies and git-lfs pointer files are rejected (both failure modes were
   actually observed in candidate mirrors).
6. **DFO class split**: DFO has no "flash flood" cause label; its
   short-duration convective label "Brief torrential rain" (189 events) is
   mapped to `flash_flood`, everything else to `flood`.

## `major` flag (5,708 events = 0.7%)

An event is `major` if **any** of:

- `deaths >= 10` — clearly catastrophic regardless of class;
- `damage_usd >= $100M` — top ~0.1% of US damage records;
- tornado with **F/EF >= 3** — the standard "intense tornado" threshold
  (~3% of tornadoes, responsible for the large majority of tornado deaths);
- tropical cyclone with lifetime max wind **>= 96 kt** (Saffir-Simpson
  Category 3+, the NHC "major hurricane" definition);
- DFO severity class **2** ("extreme": >100-yr recurrence interval) or
  **displaced >= 100,000**.

Per class: destructive_wind 1,783; flood 2,351; flash_flood 217; tornado
1,357. Per source: NOAA 1,867; DFO 2,358; IBTrACS 1,483.

## Anchor events

`ANCHORS.md` lists 35 named historically significant events — 14 tropical
cyclones across 5 basins (Katrina, Andrew, Mitch, Sandy, Harvey, Irma,
Maria, Michael, Dorian, Ida, Ian, Haiyan, Nargis, Idai), 5 benchmark
tornado events (Joplin, Moore 2013, Bridge Creek 1999, 2011 Super Outbreak,
Quad-State 2021), 6 US flash floods (Fort Collins 1997, TS Allison 2001,
Boulder 2013, WV 2016, E. Kentucky 2022, Texas Hill Country 2025), 2
derechos (June 2012, August 2020), and 8 DFO floods (Mississippi 1993,
Yangtze 1998, Elbe 2002, Pakistan 2010, Thailand 2011, Central Europe 2013,
Ahr valley 2021, Zhengzhou 2021) — **all 35 verified present**, with
representative `event_id`s for case-study lookup.

## Known limitations / follow-ups

- 2025 Storm Events file is the Dec-2025 revision (events through Sep 2025);
  Oct-Dec 2025 will appear in later NCEI revisions.
- DFO is frozen at Oct 2021; no open global flood catalog that continues it
  was found on the reachable hosts.
- IBTrACS mirror ends June 2024; 2023-2024 tracks are PROVISIONAL (winds
  from operational tcvitals, subject to post-season revision).
- IBTrACS carries no casualty/damage fields; TC `major` is intensity-based.
- Non-US, non-TC wind and tornado events are absent (ESWD requires a
  research licence — worth applying for if European validation is needed).
- On an unrestricted network, `build_catalog.py`'s mirror URLs can be
  swapped for the canonical NCEI/DFO endpoints listed above with no other
  code changes.
