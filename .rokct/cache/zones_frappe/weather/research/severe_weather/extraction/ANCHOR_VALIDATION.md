# Anchor validation: ERA5 point extraction vs 35 known events

Window: onset-14d .. onset+3d, hourly, at the nearest 0.25 deg grid point to the
catalog coordinate; 12 ERA5 variables (see `era5_extract.py`). Signature stats below
are from the near-onset phase (NOAA events: onset +-24 h; DFO floods / TCs: onset-24h
onward); `24h accum` = max rolling 24-h precipitation, `window accum` = full 17-day total.

**IBTrACS anchoring caveat (drives design):** the catalog point for a TC is its
*peak-intensity fix* and `start_utc` is track genesis - often 3-10 days before the
storm reaches that point. Anchor windows for `ib_*` events were therefore re-anchored
at the hour of minimum local MSLP within the storm's track period (`shift` column,
in hours after genesis). The full extraction (SAMPLING.md) pre-registers the same rule.

## Ida reproduction check (module self-test, `era5_extract.sanity_check()`)

At the recon grid point 30.0N, -90.0W, 2021-08-29 +48 h, the module reproduces the
recon numbers exactly: **peak precip 27.9 mm/h, peak gust 42.5 m/s, min MSLP 992.0 hPa**
(recon: ~27.9 / 42.5 / ~992.0). At Ida's IBTrACS peak-intensity fix (28.5N, -89.6W,
re-anchored 2021-08-29 12Z) the anchor table below shows 23.6 mm/h / 43.0 m/s / 985.3 hPa -
same storm, slightly deeper because the fix sits closer to the eyewall track.

## Per-anchor signature table

| # | Anchor | Class | Onset (eff.) | shift h | Peak precip mm/h (t) | 24h accum mm | Peak gust m/s (t) | Min MSLP hPa (t) | Signal |
|---|--------|-------|--------------|---------|----------------------|--------------|-------------------|------------------|--------|
| 1 | Hurricane Katrina 2005 | destructive_wind | 2005-08-28 17Z | 119 | 14.0 (08-28 23Z) | 153 | 48.1 (08-28 23Z) | 952.6 (08-28 17Z) | strong |
| 2 | Hurricane Andrew 1992 | destructive_wind | 1992-08-23 19Z | 169 | 8.6 (08-23 22Z) | 58 | 20.0 (08-23 23Z) | 1009.5 (08-23 19Z) | moderate |
| 3 | Hurricane Mitch 1998 | destructive_wind | 1998-10-26 17Z | 113 | 20.4 (10-27 00Z) | 202 | 41.2 (10-26 23Z) | 980.6 (10-26 17Z) | strong |
| 4 | Hurricane Sandy 2012 | destructive_wind | 2012-10-25 05Z | 83 | 17.9 (10-25 04Z) | 148 | 29.9 (10-25 03Z) | 987.5 (10-25 05Z) | strong |
| 5 | Hurricane Harvey 2017 | destructive_wind | 2017-08-26 00Z | 234 | 11.8 (08-25 21Z) | 114 | 28.5 (08-26 10Z) | 985.0 (08-26 00Z) | strong |
| 6 | Hurricane Irma 2017 | destructive_wind | 2017-09-05 18Z | 162 | 15.3 (09-06 00Z) | 114 | 35.5 (09-05 22Z) | 977.7 (09-05 18Z) | strong |
| 7 | Hurricane Maria 2017 | destructive_wind | 2017-09-20 01Z | 85 | 10.7 (09-19 21Z) | 84 | 36.3 (09-19 19Z) | 979.2 (09-20 01Z) | strong |
| 8 | Hurricane Michael 2018 | destructive_wind | 2018-10-10 18Z | 96 | 14.7 (10-10 17Z) | 98 | 30.6 (10-10 17Z) | 984.3 (10-10 18Z) | strong |
| 9 | Hurricane Dorian 2019 | destructive_wind | 2019-09-01 20Z | 206 | 16.7 (09-02 01Z) | 204 | 32.1 (09-02 05Z) | 989.2 (09-01 20Z) | strong |
| 10 | Hurricane Ida 2021 | destructive_wind | 2021-08-29 12Z | 72 | 23.6 (08-29 16Z) | 158 | 43.0 (08-29 16Z) | 985.3 (08-29 12Z) | strong |
| 11 | Hurricane Ian 2022 | destructive_wind | 2022-09-28 10Z | 136 | 24.0 (09-28 08Z) | 265 | 39.8 (09-28 06Z) | 973.1 (09-28 10Z) | strong |
| 12 | Typhoon Haiyan 2013 | destructive_wind | 2013-11-07 12Z | 126 | 8.1 (11-07 17Z) | 85 | 35.8 (11-07 16Z) | 983.1 (11-07 12Z) | strong |
| 13 | Cyclone Nargis 2008 | destructive_wind | 2008-05-02 02Z | 158 | 22.3 (05-02 06Z) | 174 | 30.6 (05-02 08Z) | 985.3 (05-02 02Z) | strong |
| 14 | Cyclone Idai 2019 | destructive_wind | 2019-03-11 09Z | 177 | 6.4 (03-11 19Z) | 67 | 33.8 (03-11 19Z) | 987.0 (03-11 09Z) | strong |
| 15 | Joplin MO EF5 2011 | tornado | 2011-05-22 22Z | 0 | 5.3 (05-23 17Z) | 17 | 18.6 (05-22 19Z) | 1002.5 (05-22 22Z) | moderate |
| 16 | Moore OK EF5 2013 | tornado | 2013-05-20 20Z | 0 | 7.1 (05-21 06Z) | 24 | 18.2 (05-19 21Z) | 999.9 (05-19 23Z) | moderate |
| 17 | Bridge Creek F5 1999 | tornado | 1999-05-03 23Z | 0 | 3.8 (05-04 11Z) | 18 | 20.4 (05-04 13Z) | 991.2 (05-04 21Z) | moderate |
| 18 | Super Outbreak AL EF4 2011 | tornado | 2011-04-27 21Z | 0 | 5.2 (04-27 23Z) | 24 | 21.1 (04-27 20Z) | 1001.3 (04-27 22Z) | moderate |
| 19 | Quad-State EF4 2021 | tornado | 2021-12-11 03Z | 0 | 8.3 (12-11 01Z) | 39 | 21.1 (12-11 07Z) | 1001.5 (12-11 09Z) | moderate |
| 20 | Fort Collins FF 1997 | flash_flood | 1997-07-29 04Z | 0 | 6.4 (07-29 07Z) | 40 | 10.7 (07-29 07Z) | 1017.7 (07-29 21Z) | moderate |
| 21 | Boulder CO FF 2013 | flash_flood | 2013-09-12 04Z | 0 | 3.5 (09-12 18Z) | 26 | 10.7 (09-12 19Z) | 1021.7 (09-11 09Z) | weak |
| 22 | West Virginia FF 2016 | flash_flood | 2016-06-23 17Z | 0 | 7.1 (06-23 15Z) | 49 | 15.4 (06-23 15Z) | 1013.3 (06-23 10Z) | moderate |
| 23 | E Kentucky FF 2022 | flash_flood | 2022-07-28 04Z | 0 | 1.6 (07-28 14Z) | 9 | 13.2 (07-27 16Z) | 1013.4 (07-27 23Z) | weak |
| 24 | TS Allison Houston 2001 | flash_flood | 2001-06-07 09Z | 0 | 5.7 (06-07 10Z) | 38 | 13.7 (06-06 09Z) | 1007.7 (06-06 10Z) | moderate |
| 25 | TX Hill Country FF 2025 | flash_flood | 2025-07-04 09Z | 0 | 11.3 (07-04 17Z) | 87 | 13.4 (07-04 11Z) | 1012.7 (07-04 10Z) | strong |
| 26 | June 2012 derecho | destructive_wind | 2012-06-29 23Z | 0 | 0.7 (06-30 21Z) | 1 | 15.6 (06-30 20Z) | 1008.5 (06-29 22Z) | weak |
| 27 | Aug 2020 Midwest derecho | destructive_wind | 2020-08-10 17Z | 0 | 8.6 (08-10 14Z) | 16 | 12.7 (08-10 17Z) | 1010.8 (08-10 11Z) | weak |
| 28 | Mississippi flood 1993 | flood | 1993-06-24 00Z | 0 | 4.1 (06-24 22Z) | 19 | 14.3 (06-24 20Z) | 1008.6 (06-23 23Z) | weak |
| 29 | Yangtze flood 1998 | flood | 1998-08-05 00Z | 0 | 0.2 (08-04 09Z) | 0 | 11.5 (08-07 04Z) | 998.9 (08-06 09Z) | strong |
| 30 | Elbe flood 2002 | flood | 2002-08-07 00Z | 0 | 4.5 (08-06 21Z) | 59 | 10.6 (08-07 06Z) | 1002.6 (08-09 23Z) | strong |
| 31 | C Europe flood 2013 | flood | 2013-05-28 00Z | 0 | 2.7 (05-29 08Z) | 11 | 12.6 (05-27 00Z) | 999.6 (05-29 02Z) | moderate |
| 32 | Pakistan floods 2010 | flood | 2010-07-27 00Z | 0 | 8.8 (07-29 23Z) | 53 | 13.1 (07-27 11Z) | 995.7 (07-26 11Z) | strong |
| 33 | Thailand floods 2011 | flood | 2011-08-05 00Z | 0 | 1.6 (08-04 05Z) | 8 | 14.2 (08-05 05Z) | 1000.4 (08-06 11Z) | strong |
| 34 | Ahr valley flood 2021 | flood | 2021-07-14 00Z | 0 | 5.3 (07-14 04Z) | 69 | 15.3 (07-14 18Z) | 1007.3 (07-14 19Z) | strong |
| 35 | Zhengzhou flood 2021 | flood | 2021-07-20 00Z | 0 | 12.1 (07-20 00Z) | 140 | 12.3 (07-20 04Z) | 1004.5 (07-21 08Z) | strong |

Signal grades (class-specific, near-onset): destructive_wind/tornado by peak gust
(strong >=28, moderate >=18 m/s); flash_flood by peak hourly precip (strong >=8,
moderate >=4 mm/h); flood by accumulation (strong: 24h >=50 mm or window >=120 mm).

## Neighborhood displacement scan (US point events, +-0.75 deg, 7x7 points)

| Anchor | Class | Point peak precip | Nbhd max precip | displ. deg | Point peak gust | Nbhd max gust | displ. deg |
|--------|-------|-------------------|-----------------|------------|-----------------|---------------|------------|
| Joplin MO EF5 2011 | tornado | 5.3 | 14.8 | 0.90 | 18.6 | 19.6 | 0.50 |
| Moore OK EF5 2013 | tornado | 7.1 | 15.2 | 0.25 | 18.2 | 18.7 | 0.71 |
| Bridge Creek F5 1999 | tornado | 3.8 | 14.3 | 0.79 | 20.4 | 22.0 | 0.35 |
| Super Outbreak AL EF4 2011 | tornado | 5.2 | 13.0 | 1.06 | 21.1 | 24.2 | 0.71 |
| Quad-State EF4 2021 | tornado | 8.3 | 10.7 | 0.35 | 21.1 | 23.5 | 1.06 |
| Fort Collins FF 1997 | flash_flood | 6.4 | 9.4 | 0.25 | 10.7 | 15.3 | 0.56 |
| Boulder CO FF 2013 | flash_flood | 3.5 | 8.2 | 0.56 | 10.7 | 11.7 | 0.75 |
| West Virginia FF 2016 | flash_flood | 7.1 | 15.4 | 0.56 | 15.4 | 20.2 | 0.79 |
| E Kentucky FF 2022 | flash_flood | 1.6 | 8.6 | 0.79 | 13.2 | 14.3 | 0.90 |
| TS Allison Houston 2001 | flash_flood | 5.7 | 17.4 | 1.06 | 13.7 | 17.5 | 0.56 |
| TX Hill Country FF 2025 | flash_flood | 11.3 | 24.3 | 0.35 | 13.4 | 14.2 | 0.25 |
| June 2012 derecho | destructive_wind | 0.7 | 2.7 | 0.79 | 15.6 | 16.3 | 0.79 |
| Aug 2020 Midwest derecho | destructive_wind | 8.6 | 14.6 | 0.90 | 12.7 | 15.7 | 0.35 |

## Findings

### Tropical cyclones: 13/14 strong, 1 moderate

After MSLP re-anchoring, every TC anchor shows a textbook signature at its
peak-intensity fix: gusts 29-48 m/s, MSLP minima 952-990 hPa, 24-h rain
accumulations 58-265 mm, and gust/precip/pressure extremes co-located in time
within +-10 h. Katrina is the deepest (48.1 m/s, 952.6 hPa on 2005-08-28 17Z -
exactly its observed Cat-5 peak time; ERA5's 952 vs the observed 902 hPa is the
expected 0.25-deg intensity damping). The one *moderate* is **Andrew 1992**
(20.0 m/s, 1009.5 hPa): Andrew was an unusually compact storm and 1992 is in the
sparse pre-satellite-scatterometer assimilation era, so ERA5 badly underresolves
its core - a known reanalysis limitation worth remembering for pre-~1998 TCs.
ERA5 intensity is systematically damped: observed peak gusts for these storms
are 70-90+ m/s; ERA5 delivers 30-48. Ranking/beyond-threshold detection works;
absolute magnitudes must be treated as a proxy scale, not physical peak winds.

### Tornadoes: all 5 "moderate" - systematically damped, as expected

The five benchmark tornado events (incl. 3 EF5s) produce point gusts of only
18.2-21.1 m/s and neighborhood maxima of 18.7-24.2 m/s: **a 0.25-deg reanalysis
never sees the tornado itself, only the parent mesoscale environment.** The
signal is real but ~3x weaker than the true event (EF5 winds >89 m/s), and the
gust peak is mistimed by up to +-24 h (Moore 2013: environment gust peak 23 h
before touchdown). Displacement is moderate: precip maxima sit 0.25-1.06 deg
from the touchdown point. Consequence for proxy design: tornado labels cannot be
mined from gust magnitude; they need environment-style precursors (instability /
moisture / shear proxies from TCWV, dewpoint, MSLP gradients and the diurnal
gust structure), and event matching should use a ~1-deg / +-24 h tolerance.

### Flash floods: 1 strong, 4 moderate, 2 weak - displaced more than damped

Point peak hourly precip spans 1.6-11.3 mm/h. The neighborhood scan shows the
main failure mode is *displacement*, not absence: E. Kentucky 2022 jumps from
1.6 to 8.6 mm/h (0.79 deg away), TS Allison from 5.7 to 17.4 (1.06 deg),
Boulder 2013 from 3.5 to 8.2 (0.56 deg). Median displacement of the precip
maximum for the 8 US convective/flash-flood anchors is ~0.6 deg (~60 km),
i.e. one to three grid cells. Orographic, training-cell events (Boulder, E.
Kentucky) are the weakest - ERA5 spreads their rain in space and time. Proxy
design should use neighborhood-max or area-mean precip features (+-2 cells)
rather than single-point values, and 6-24 h accumulations rather than 1-h peaks.

### Derechos: both weak at the point - the worst case for 0.25 deg

June 2012 (15.6 m/s point, 16.3 nbhd) and August 2020 Iowa (12.7 / 15.7 m/s vs
observed 50-60 m/s gusts) barely register: a derecho's damaging-wind corridor is
tens of km wide and moves at ~25 m/s, faster than hourly 0.25-deg sampling can
integrate. NOAA Thunderstorm-Wind point events will generally show gust
signatures far below their measured magnitudes; mining should treat them as
environment labels (like tornadoes), not wind-magnitude labels.

### Floods (DFO): 6 strong / 1 moderate / 1 weak - accumulation is the signal

Riverine floods show up in 24-h/multi-day accumulation, not hourly peaks:
Zhengzhou 2021 has 140 mm/24h (observed 624 mm/24h city max - damped ~4x but
unambiguous), Ahr valley 69 mm/24h, Pakistan 2010 258 mm over the window.
Yangtze 1998 is instructive: near-zero rain at the centroid *at onset* but 306 mm
across the 17-day window - basin-scale floods integrate rain over weeks and a
large upstream area, so the event-centroid point still carries signal, but with
long lags. Mississippi 1993 is the one *weak* flood: a 3-month basin flood whose
DFO centroid + onset date capture neither the months of antecedent rain nor the
upstream sources; expect this failure mode for very large, slow riverine events.

### Bottom line for mining

- TC / large-synoptic events: excellent, direct signatures; magnitudes damped but
  monotone. Anchor IBTrACS windows via local MSLP minimum, never genesis time.
- Tornado / derecho / small flash floods at 0.25 deg: signatures are weak
  (gusts ~40-60% of true magnitudes at best, hourly rain damped 2-4x) and
  displaced by ~0.25-1 deg. Use neighborhood aggregation and environment
  precursors; treat these classes as environment-labeled, not magnitude-labeled.
- Floods: use 24-h to multi-day accumulations; expect long/variable lags for
  basin-scale events.

