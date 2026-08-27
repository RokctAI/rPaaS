# Limpopo / Vhembe long-duration-rain floods: a blind case study of the frozen detector

Requested by Ray. Two questions:

1. **Recurrence** — Ray's hypothesis: the catastrophic long-rain Limpopo-basin floods
   recur roughly every 25-30 years (his count: the most recent arrived ~25 years after
   the previous one; earlier gaps ~30 years).
2. **Blind test** — the detector, tuned WITHOUT any data from the most recent event's
   period, should have flagged that event ahead of time.

## Blind protocol

`detector/detector_config_tuned.json` (sha256 `758ba92bb6ce...`, "tuned-2026-08-19")
was frozen on the **pre-2018 global dev cohort only** (dev/holdout split at 2018-01-01,
frozen in `extraction/SAMPLING.md` before extraction; the tuning search never saw any
2018+ series, any Limpopo-specific series, or any location-targeted objective). Nothing
in this study touches the config: it is loaded read-only and run **causally** (forward
state machine, features computed from past values only) over multi-decade hourly series
the config has never seen. The most recent event (Dec 2025 - Feb 2026) is therefore a
genuine blind test; 1977, 2000 and 2013 are out-of-sample in space (no Limpopo tuning)
but inside (2000, 2013) or before (1977) the climatological period the dev cohort spans.

One documented implementation deviation, forced by scale: `mining/features.py` computes
the causal soil-moisture percentile (`sm_pct`) with an O(n^2) broadcast that is only
viable on the 408-hour event windows used in mining/tuning. On 277,000-hour continuous
series this study substitutes a **trailing 408-hour rolling percentile** — the same
"fraction of history <= current value" definition over exactly the dev-window amount of
history, still fully causal. No thresholds or rule structures were changed
(see `run_detector.py`).

## 1. Ground truth

Four major long-rain / basin-wide flood events, plus the smaller documented floods used
to cross-check alarms (section 4).

| Event | Onset chronology (UTC dates) | Impact | Sources |
|---|---|---|---|
| **Feb 1977** (Severe Tropical Storm Emilie) | Emilie crossed Madagascar ~2 Feb, then hit Inhambane/Gaza and continued into north-eastern South Africa; heavy rain over the basin in the first days of February; **Chokwe and lower Xai-Xai completely inundated on 12 Feb 1977** ("a wall of water ... in the middle of the night") | ~300 deaths; benchmark flood — Massingir's 14 floodgates were not all opened again until 2013; resettlement villages (Chiaquelane) date from it | [MedCrave flood history, lower Limpopo](https://medcraveonline.com/MOJES/flood-history-in-lower-limpopo-mozambique.html); [worlddata.info Mozambique cyclones](https://www.worlddata.info/africa/mozambique/cyclones.php); [Open University Mozambique news 454](https://university.open.ac.uk/technology/mozambique/sites/www.open.ac.uk.technology.mozambique/files/files/Mozambique_454-26Apr19_2nd-severe-cyclone.pdf); [Chiaquelane (Wikipedia)](https://en.wikipedia.org/wiki/Chiaquelane) |
| **Feb 2000** (antecedent rains + Cyclone Connie, then Cyclone Eline) | Heavy rain Oct-Nov 1999 and through Jan 2000; Connie's deluge 4-7 Feb (Maputo 455 mm); TRMM shows the heavy rain moving inland over northern South Africa by 6 Feb; main rainfall from 8 Feb; **Limpopo inundated Chokwe and Xai-Xai on 12 Feb**; Eline landfall near Beira 22 Feb renewed rain over SA/Zimbabwe 20-22 Feb; **Limpopo crest 25-27 Feb** (11 m above normal, 15 km wide); flooding persisted into March | ~700 deaths, ~544,000 displaced; worst in ~50 years; 6 killed in SA's Northern Province by Eline's rains | [2000 Mozambique flood (Wikipedia)](https://en.wikipedia.org/wiki/2000_Mozambique_flood); [FloodList: Mozambique Floods 2000](https://floodlist.com/africa/mozambique-floods-2000); [World Bank/GFDRR damage assessment](https://www.gfdrr.org/sites/default/files/publication/pda-2000-mozambique.pdf); [Dartmouth Flood Observatory analysis](https://floodobservatory.colorado.edu/00003.html); [OCHA sitrep](https://reliefweb.int/report/mozambique/mozambique-floods-situation-report-3-apr-2000) |
| **Jan 2013** | Rain band 11-20 Jan (>200 mm over southern Mozambique / southern Zimbabwe / adjacent SA); Limpopo orange alert 12 Jan; SA-side flooding mid-Jan (Kruger rivers, Limpopo province); **Chokwe: river rising rapidly, evacuation from 22 Jan**, town inundated 23-25 Jan; Xai-Xai lower town flooded; Pafuri cut off | 113 deaths by the time the red alert lifted (12 Mar); 150,000-250,000 displaced/affected; "the town all but destroyed for the second time in 13 years" | [ReliefWeb Southern Africa Floods sitrep 1](https://reliefweb.int/report/mozambique/southern-africa-floods-situation-report-no-1-29-january-2013); [NASA Earth Observatory](https://earthobservatory.nasa.gov/images/80297/close-up-of-flooding-in-mozambique); [Manhique et al. 2015, Nat. Hazards](https://link.springer.com/article/10.1007/s11069-015-1616-y); [FloodList 2013](https://floodlist.com/africa/floods-mozambique-2013) |
| **Dec 2025 - Feb 2026** (the BLIND event) | Flooding from ~25 Dec 2025 (Waterberg/Capricorn); main phase mid-Jan: SAWS level-9 warnings 12 Jan (eastern Lowveld, Collins Chabane, Giyani), **level-10 red warning 15-16 Jan**; Vhembe + Mopani hardest hit (>100 mm/48 h; Thohoyandou bridge collapse; R524 destroyed); Kruger rivers (incl. Luvuvhu, Limpopo) overflowed wk of 12-19 Jan; **national disaster declared 18 Jan**; Gaza province: up to 700 mm rain in <7 days, **Xai-Xai ordered ~115,000 evacuated 20 Jan**, Limpopo burst its banks, >40% of Gaza submerged, flood waves continued into Feb-Mar | >=30 deaths (Limpopo + Mpumalanga); ~2,000 homes destroyed in Limpopo; >300,000 displaced in Gaza; reported as possibly worse than 1977 and 2000 | [ASIS/AP national disaster](https://www.asisonline.org/security-management-magazine/latest-news/today-in-security/2026/january/south-africa-mozambique-zimbabwe-flooding-natural-disaster/); [africanfarming: SAWS L9, 12 Jan](https://www.africanfarming.com/2026/01/12/weather-service-issues-level-9-and-6-warning-for-heavy-rainfall/); [IOL: L10 red warning 15-16 Jan](https://iol.co.za/news/south-africa/2026-01-15-flood-crisis-deepens-as-saws-issues-level-10-warning-and-ramaphosa-visits-besieged-limpopo/); [IOL: Limpopo toll](https://iol.co.za/news/south-africa/2026-01-16-death-toll-rises-to-nine-almost-2000-homes-destroyed-as-limpopo-floods-wreak-havoc/); [ACAPS Gaza impact](https://www.acaps.org/fileadmin/Data_Product/Main_media/20262501_Mozambique_Impact_of_flooding_in_Gaza_Maputo_Niassa_Sofala_and_Zambezia_provinces.pdf); [Daily Sabah: 300k displaced](https://www.dailysabah.com/world/africa/floods-displace-more-than-300000-in-mozambiques-gaza-province); [Club of Mozambique: Xai-Xai evacuation](https://clubofmozambique.com/news/mozambique-xai-xai-steps-up-evacuation-from-flood-prone-areas/); [The Conversation](https://theconversation.com/south-africas-floods-turned-deadly-because-limpopo-wasnt-prepared-how-to-prevent-a-repeat-274287); [Mongabay: Kruger](https://news.mongabay.com/short-article/2026/02/after-intense-flooding-kruger-national-park-rushes-to-repair-damage/) |

Historical context for the recurrence question: the lower-Limpopo record also lists
severe floods in **1955, 1967, 1972, 1975, 1981**
([MedCrave flood history](https://medcraveonline.com/MOJES/flood-history-in-lower-limpopo-mozambique.html);
[LIMCOM hydrology](https://limpopocommission.org/the-basin/the-river-basin/hydrology/hydrology-of-the-limpopo-river-basin/flooding/)).

Onset dates carry real uncertainty (+-days for 1977; multi-phase for 2000 and 2025/26).
Leads below are quoted against the specific documented milestone named in each case.

## 2. Method

Six ERA5 grid points spanning the basin (0.25-degree cells; Musina's cell also covers
the Beitbridge area):

| Point | Lat | Lon | Role |
|---|---|---|---|
| thohoyandou | -22.95 | 30.48 | Vhembe district, Luvuvhu headwaters |
| musina | -22.35 | 30.03 | Vhembe / Beitbridge, main-stem Limpopo |
| pafuri | -22.45 | 31.32 | Limpopo-Luvuvhu confluence, N Kruger |
| mapai | -22.85 | 31.98 | middle Limpopo, Gaza (MZ) |
| chokwe | -24.53 | 32.98 | lower Limpopo irrigation belt (MZ) |
| xai_xai | -25.05 | 33.64 | Limpopo mouth, Gaza (MZ) |

Data: hourly ERA5 from the public `s3://openmeteo` archive via
`extraction/era5_extract.py`, two eras per point — **1975-01-01 .. 1979-01-01** (for the
1977 event) and **1995-01-01 .. 2026-08-14** (through the latest available rolling
chunk), all 11 variables the frozen rules reference, plus the 7x7-neighborhood hourly
precipitation the flash-flood rule needs (`extract_limpopo.py`; ~24k cached reads, 0
failures). Features: `mining/features.py` + `extraction/nbr_features.py` +
`extraction/wind100_features.py`, unmodified except the `sm_pct` substitution documented
above. Detector: `detector/detector.py` with the frozen config, all four classes, run
independently per point per era (`run_detector.py`). Every warning-or-worse episode is
in `alarms.csv`; scoring criteria mirror `detector/backtest.py` (hit = correct-class
warning active in [onset - 7 d, onset], first fired >= 24 h (flood) / 6 h (flash_flood)
before onset).

Known data gaps (NaN-tolerated by the detector, then de-armed): TCWV 2024-01-01 ..
2024-06-12; soil moisture 2023-09-21 .. 2023-12-14.

## 3. Per-event results

Severity tiers: watch < warning < severe; confidence = weighted fraction of rule
conditions active. Times UTC.

### Feb 1977 — partial: one upstream point warned 5.3 days before the Chokwe disaster

| Point | First warning before/at event | Lead vs milestone |
|---|---|---|
| thohoyandou | **flood, severe, 6 Feb 17:00 - 10 Feb 11:00** (conf 1.0) | fired during Emilie's rains over the escarpment; **128 h before Chokwe/Xai-Xai inundation (12 Feb)** |
| xai_xai | flash_flood warning 15 Feb 04:00; flood severe 15 Feb 07:00 | ~3 days **after** the 12 Feb inundation (in-event, not predictive) |
| musina, pafuri, mapai, chokwe | no warning in the event window | — |

The lower-basin catastrophe was river-routed: ERA5 point rain at Chokwe/Xai-Xai stayed
below the frozen thresholds until mid-event (fig. `event_1977_chokwe.png`); the only
predictive signal was upstream. Consistent with the documented 1975 flood year, the
1975 era also produced flood-severe episodes at thohoyandou/pafuri on 13 Feb 1975.

### Feb 2000 — flash-flood rule warned 2.5-5 days ahead; flood rule caught the antecedent and Eline phases but missed the 8-12 Feb river rise

| Point | First qualifying warning | Lead |
|---|---|---|
| musina | flash_flood warning 5 Feb 14:00 | 58 h before the 8 Feb rain onset |
| mapai | flash_flood warning 4 Feb 16:00 | 80 h before 8 Feb |
| chokwe | flash_flood warning 6 Feb 20:00 | **124 h before the 12 Feb inundation** |
| xai_xai | flash_flood warning 6 Feb 21:00 | 123 h before 12 Feb |
| thohoyandou | flood severe 23 Feb 23:00 - 25 Feb 21:00 | 1-3 days before the 25-27 Feb Limpopo crest (post-Eline) |
| (antecedent phase) | flood severe at thohoyandou/pafuri/musina 17 Jan; pafuri 3 Jan | during the documented January antecedent rains |
| xai_xai | flood severe 9 Mar | during the documented March continuation |

The flood class itself produced no pre-12-Feb warning at the lower-basin points — the
first-phase water came from Connie's coastal deluge south of the basin plus upstream
runoff, not local point rain (fig. `event_2000_chokwe.png`).

### Jan 2013 — warned at all six points; upstream ~2 days ahead, downstream ~1 day

| Point | First qualifying warning | Lead |
|---|---|---|
| mapai | **flood severe 12 Jan 01:00** (also flash_flood 11 Jan 20:00) | 47-52 h before the 14 Jan SA rain peak; **10 days before Chokwe's evacuation** |
| pafuri | flash_flood warning 11 Jan 23:00 | 49 h |
| thohoyandou | flash_flood warning 12 Jan 06:00 (flood severe 20 Jan 08:00) | 42 h |
| musina | flood severe 20 Jan 14:00 | in-event for the rain phase |
| chokwe | flood severe 21 Jan 10:00 | 14 h before the 22 Jan river rise/evacuation — real warning, but **below the flood class's 24 h minimum lead**, so scored a miss under the frozen criteria |
| xai_xai | flash_flood warning 21 Jan 07:00 (hit, 17 h); flood severe 21 Jan 13:00 (11 h, below minimum) | |

### Dec 2025 - Feb 2026 (BLIND) — severe flood warnings at every point, 9-14 Jan

| Point | First warning (any) | Flood-severe episode | Lead vs documented milestones |
|---|---|---|---|
| chokwe | flash_flood 9 Jan 21:00 | **10 Jan 04:00 - 11 Jan 14:00** | **10.2 days before the 20 Jan Xai-Xai-area evacuation order** |
| xai_xai | flash_flood 9 Jan 21:00 | 10 Jan 17:00 | 9.3 days before 20 Jan |
| mapai | flash_flood 10 Jan 03:00 | 10 Jan 23:00 - 13 Jan | 25-45 h before the 12 Jan escalation |
| thohoyandou | flash_flood 11 Jan 05:00 | 11 Jan 07:00 - 15 Jan | 17-19 h before the 12 Jan SAWS level-9 day; ~4.5 days before the 15-16 Jan level-10 red warning |
| pafuri | flash_flood 10 Jan 23:00 | 12 Jan 00:00 - 13 Jan (again 14, 16 Jan) | 25 h |
| musina | flash_flood 11 Jan 09:00 | 14 Jan 00:00 | 15 h before 12 Jan (flash); flood during peak |
| (first phase) | | thohoyandou + pafuri flood severe **22 Dec 11:00/15:00** | ~2.5-3 days before the documented ~25 Dec onset of the first flooding phase |
| (continuation) | | chokwe + xai_xai flood severe 3 Mar and 8 Mar | during the documented Feb-Mar flood waves |

Under the frozen scoring criteria: flash-flood hits at thohoyandou, musina, pafuri,
mapai; flood hit at mapai (25 h lead, severe, conf 1.0); the chokwe/xai_xai flood-severe
episodes of 10 Jan fired so early relative to the 20 Jan lower-basin milestone that they
fall outside the 7-day hit window — operationally they were the earliest and most
valuable warnings of all. Figures `event_2026_thohoyandou.png` (rain accumulations
~4x the severe thresholds) show how far past the frozen gates this event ran.

### Summary table (frozen scoring, flood or flash_flood)

| Event | Points warned ahead | Best lead (qualifying) | Earliest useful signal |
|---|---|---|---|
| 1977 | 1 of 6 | — (fired at rain onset) | 128 h before the downstream disaster |
| 2000 | 4 of 6 | 124 h (chokwe, flash) | 5.2 days (chokwe flash vs the 12 Feb inundation) |
| 2013 | 5 of 6 | 52 h (mapai, flash) | 10 days (mapai flood severe vs Chokwe evac) |
| **2026 (blind)** | **6 of 6** | 45 h (mapai, flash) | **10.2 days (chokwe flood severe vs evacuation order)** |

## 4. Alarm climatology — how rare are these alarms?

Full list: `alarms.csv` (507 episodes, all points/eras/classes). Modern era
(1995 - Aug 2026, 189.7 point-years):

| Class | Episodes | Per point-year | Notes |
|---|---|---|---|
| flood | 99 | 0.52 | all reached severe |
| flash_flood | 352 | 1.86 | none exceeded warning tier; within ~budget at inland points (1.4-1.8/pt-yr) but above the dev <=2 bar at the coastal points (chokwe 2.1, xai_xai 2.7) |
| destructive_wind | 3 | 0.02 | 16 Jan 2012 (x2), 15 Feb 2017 |
| tornado | 9 | 0.05 | incl. a 4-point cluster 23 Jan 2021 |

Flood-severe episodes per calendar year, all six points combined (modern era):

| yr | n | yr | n | yr | n | yr | n |
|---|---|---|---|---|---|---|---|
| 1995 | 0 | 2003 | 0 | 2011 | 1 | 2019 | 7 |
| 1996 | 3 | 2004 | 1 | 2012 | 1 | 2020 | 3 |
| 1997 | 0 | 2005 | 0 | **2013** | **11** | 2021 | 5 |
| 1998 | 2 | 2006 | 4 | 2014 | 6 | 2022 | 1 |
| 1999 | 7 | 2007 | 2 | 2015 | 0 | 2023 | 7 |
| 2000 | 7 | 2008 | 1 | 2016 | 1 | 2024 | 1 |
| 2001 | 5 | 2009 | 0 | 2017 | 3 | 2025 | 3 |
| 2002 | 0 | 2010 | 3 | 2018 | 0 | **2026** | **14** |

Cross-checking alarm clusters against the documented record (verified via news/reports):

* **Jan-Feb 1996** (3 episodes, thohoyandou): the Jan 1996 rains put the Limpopo — dry
  since Oct 1995 — into overflow ([MDPI Water 13:3490](https://www.mdpi.com/2073-4441/13/24/3490)).
* **Feb 1999** (5 episodes, 5-8 Feb): documented Feb 1999 flood relief operations in
  neighboring Inhambane province ([ReliefWeb](https://reliefweb.int/report/mozambique/flooding-mozambique-emergency-appeal)).
* **16-17 Jan 2012** (destructive_wind x2 + flood): Tropical Storm **Dando** — fiercest
  storm in the area since 1984; flooding in Gaza incl. Chokwe
  ([The New Humanitarian](https://www.thenewhumanitarian.org/node/251528)).
* **15-17 Feb 2017** (destructive_wind + 2 flood): Cyclone **Dineo** landfall in
  Inhambane, moving inland across the basin (dates per public storm records).
* **23-24 Jan 2021** (tornado-class cluster + flood): Cyclone **Eloise**; the lower
  Limpopo reached its Flood Early Action trigger 1 Feb, Chokwe flood peak ~4 Feb
  ([ReliefWeb flash update](https://reliefweb.int/report/mozambique/southern-africa-tropical-cyclone-eloise-flash-update-no5-22-january-2021);
  [Anticipation Hub](https://www.anticipation-hub.org/news/anticipating-the-flood-taking-early-actions-at-the-lower-limpopo-in-mozambique)).
* **26 Feb - 1 Mar 2023** (5-point flood cluster): Cyclone **Freddy**'s first landfall
  (24 Feb 2023, southern Mozambique; dates per public storm records).
* **3-8 Mar 2026**: the documented Feb-Mar continuation of the 2026 disaster.

Not individually verified against news (smaller clusters): 1998, Nov 1999, 2001, 2004,
2006, 2007, 2008, 2010, 2011, Dec 2013/Jan 2014 wet spell, 2016, 2019, 2020, 2022,
Apr 2024, Feb 2025, Aug 2026 (xai_xai, 11 Aug — days before this study's data end).
The tornado/destructive-wind "alarms" above are class confusions in name (they fired on
landfalling cyclones, not tornadoes) but not spurious weather.

## 5. Verdict

**On Ray's 25-30-year recurrence hypothesis: the spacing is real only for the
record-breakers, not as a general rhythm.** The three floods described as
worst-in-memory — 1977, 2000, 2025/26 — are spaced 23 and 26 years, matching Ray's
count. But 2013 (13 years after 2000, 113 dead, Chokwe destroyed "for the second time
in 13 years") was of the same catastrophic class, and the pre-satellite record adds
1955/1967/1972/1975/1981. Major Limpopo floods recur on a ~5-15-year scale; the
detector agrees — flood-severe episodes occur in 20 of 32 modern years (0.52 per
point-year), so a single point's severe flood alarm is roughly a twice-a-decade event,
not a generational one. What IS rare in the 31.6-year modern record is **basin-wide
near-simultaneous firing** (>=5 of 6 points within ~4 days): it happened in
2013, 2023 (Freddy) and 2026 only — and the two biggest yearly alarm totals in the
whole record are 2013 (11) and 2026 (14), exactly the two catastrophic basin floods in
the modern span. A "basin-wide consensus" aggregation (k-of-n points) would convert the
per-point detector into a rare-event catastrophic-flood flag essentially for free;
that is the natural follow-up.

**On the blind test: yes, the system would have warned.** Run causally over data whose
period the config was never tuned on, the frozen detector issued severe flood warnings
at all six basin points between 9 and 14 January 2026 — first alarms late on 9 Jan,
~2 days before the 12 Jan escalation in Vhembe, ~5 days before SAWS's level-10 red
warning of 15-16 Jan, and ~10 days before the 20 Jan evacuation order on the lower
Limpopo — plus an earlier severe alarm on 22 Dec 2025, 2.5 days ahead of the
documented first flooding phase. Its weakest showings were the river-routed lower-basin
onsets of 1977 (silent at Chokwe until in-event) and the first 2000 river rise
(flash-flood warnings only, 2.5-5 days ahead; the flood rule proper missed it): the
detector reads local rain-on-saturated-soil, so downstream points inheriting upstream
water are warned late or not at all unless their own rain also turns extreme — as it
did in 2013 and 2026.

## Files

* `extract_limpopo.py` — extraction (points, eras, neighborhood units, cache).
* `run_detector.py` — features + frozen-config causal run; writes `alarms.csv`.
* `evaluate.py` — event scoring + yearly counts; writes `evaluation.json`.
* `make_figures.py`, `figures/` — precursor timelines per event (feature series vs the
  frozen ON thresholds; shading = warning episodes).
* `alarms.csv` — every warning episode (507 rows).

Extracted series, feature frames and the read cache stay uncommitted (multi-GB), same
policy as the mining/extraction work.
