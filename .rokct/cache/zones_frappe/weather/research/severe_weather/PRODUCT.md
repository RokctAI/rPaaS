# Severe-weather early warnings — product overview

Audience: investors and partners evaluating this capability as a standalone product.
Rule of this document: every number is taken from the published research record in this
directory and is reported with its honest context, including where the system falls
short. Nothing here is projected, extrapolated, or rounded up.

## What it is

An early-warning layer inside a consumer weather experience. The platform's weather
module already shows people their local conditions; this capability adds a quiet
background service that watches each user's area for the precursors of floods,
destructive winds, and tornado-favorable conditions — patterns it learned by mining 85
years of global hourly weather history (the ERA5 reanalysis, 1940–present) against a
catalog of 817,216 real recorded disasters. When those precursors build, the app shows
a calm, plain-language heads-up ("Flooding possible near your area in the coming
days"); when nothing is brewing, it shows nothing. The whole pipeline — event catalog,
signature mining, detector, backtest — is reproducible from public data and is
published in this repository, misses included.

## The proof points, with their honest context

**A ground-truth catalog of 817,216 disasters.** Built from three public sources —
806,675 NOAA Storm Events (1996–Sep 2025), 4,902 DFO Global Flood Archive floods
(1985–Oct 2021), 5,639 IBTrACS tropical cyclones (1950–Jun 2024) — normalized, QC'd,
deduplicated, with 5,708 events flagged major and all 35 named anchor events (Katrina,
Joplin, the Ahr valley…) verified present. The build script re-creates the catalog
end-to-end from public URLs (`catalog/`).

**27,812 extracted precursor series.** For 9,272 sampled events plus 18,540 matched
same-location, same-season control windows, hourly ERA5 series were extracted around
onset (0 failures) and mined for features that separate disaster run-ups from ordinary
weather. The resulting signature library (`mining/results/SIGNATURES.md`) records both
the winners — rain-on-saturated-soil for floods, 24 h pressure falls for destructive
wind, moisture/instability plus bulk shear for tornadoes — and the features that do
not separate, so the negative results are never re-derived.

**The physics reproduces named storms.** The extraction pipeline was validated on all
35 anchor events. Hurricane Ida's signature at the recon grid point reproduces the
independent recon numbers exactly (peak precipitation 27.9 mm/h, peak gust 42.5 m/s,
minimum pressure 992.0 hPa), and Katrina's ERA5 series bottoms out at 952.6 hPa with
48.1 m/s gusts at the exact hour of its observed Category-5 peak. 13 of 14 tropical
cyclone anchors show the textbook signature; the caveat is stated in the same
document: ERA5 damps absolute intensities, so magnitudes are a proxy scale
(`extraction/ANCHOR_VALIDATION.md`).

**A blind result on a real catastrophe.** The detector configuration was frozen using
only pre-2018 data, then run causally over six ERA5 grid points spanning the Limpopo
basin. For the December 2025 – February 2026 floods — a period no tuning ever saw — it
issued severe flood alarms at all six points between 9 and 14 January 2026: roughly 2
days before the escalation in Vhembe, about 5 days before the national weather
service's level-10 red warning, and about 10 days before the evacuation order on the
lower Limpopo. The same frozen config warned ahead at 5 of 6 points for the 2013 flood
and 4 of 6 for 2000; its known blind spot is river-routed flooding at downstream
points whose own rain stays modest (1977: 1 of 6, upstream only)
(`casestudy_limpopo/LIMPOPO_CASE_STUDY.md`).

**What it catches on held-out data.** On the untouched 2018+ holdout cohort, at an
operating point capped at ≤2 alarms per location-year on non-event controls (achieved
0.87–1.45), the detector caught 44% of major flash floods (54% of those with >$100M
damage, median lead ~15 h) and about a third of tropical-cyclone landfalls (34%,
~19 h median lead), with false-alarm rates of 0.15–0.34 and all lead-time bars met
(`BACKTEST.md`).

**The frozen backtest verdict, stated plainly: NOT ACCEPTED.** Before any mining
began, acceptance thresholds were committed and frozen. On the single permitted
holdout run, every false-alarm and lead-time bar passed and every overall
detection-rate bar failed — flash flood 0.13 vs the 0.60 bar, flood 0.03 vs 0.65,
destructive wind 0.16 vs 0.70, tornado 0.12 vs 0.40. The shortfall is structural, not
cosmetic: the system is deliberately conservative, and any rule loose enough to
approach those bars would blow the false-alarm budget. It does not detect small
convective events at point scale, and it does not localize river-routed floods from
local rain. The full report, with every miss itemized, is public in this repository
(`BACKTEST.md`, `PLAN.md`). What ships is the defensible subset of what the detector
demonstrably does — not what the original bars hoped for.

**Many "false" alarms are real weather the catalogs missed.** Post-hoc analysis found
that 33–64% of holdout false alarms (by class) fired on the most extreme weather ever
sampled at that location (≥ its own 99.9th percentile) — strong evidence of real,
uncatalogued events, especially for floods outside the US. The frozen metrics stand as
computed; this finding says the true false-alarm behavior is likely better than the
recorded accounting (`BACKTEST.md` §5.3, `detector/SUPPLEMENTARY_DEV.md`).

## Why it is cheap to run

- **Open data, no licensing on the default path.** The ERA5 archive is read
  anonymously from a public AWS Open Data bucket under CC-BY-4.0. The one obligation
  is attribution — "Weather data by Open-Meteo.com" is rendered on every surface that
  shows warning data. No API keys, no rate limits, no per-call fees. A commercial
  lag-free API is a config switch, not a rewrite.
- **One evaluation serves every user in a cell.** Warnings are computed per 0.25°
  grid cell on a schedule, so a thousand users in the same area cost the same as one.
  Client requests hit a cached, already-computed answer.
- **Tiny data volumes.** A point-year of one variable transfers ~15 kB via ranged
  reads; a full evaluation window for one cell (11 variables plus the neighborhood
  rain box) fetches in seconds. No bulk mirror of the archive is needed.
- **Runs inside existing infrastructure.** The evaluator is an ordinary scheduled job
  in the existing backend; the detector is a small, interpretable rule engine — every
  alarm can state exactly which precursors fired.

## Who pays for it

- **Consumer differentiation for the existing platform.** The heads-up banner ships
  inside the current apps: a weather feature competitors' delivery and commerce
  platforms do not have, at near-zero marginal cost.
- **B2B decision support.** The same per-cell warning feed applies to logistics and
  delivery planning (reroute or pre-position before flooding), insurers (portfolio
  exposure heads-ups), and agriculture (multi-day flood leads; the flood class's
  median lead on hits is measured in days).
- **Disaster-management organizations, via the admin surface.** The Limpopo result is
  the demonstration: days of basin-level lead on a real catastrophe, from a config
  that had never seen the event. Positioning is decision support for professionals —
  never official public alerting.
- **Legal posture (South Africa).** Only the national weather service (SAWS) may
  issue official severe-weather warnings. End-user copy is therefore heads-up
  possibility phrasing — the word "warning" and official taxonomy never reach a user,
  enforced by a unit test. Legal review is required before any marketing of this
  capability as "warnings" in South Africa.

## Why it is defensible

- **The signature library.** Mined precursor signatures across four event classes and
  five lead times, including recorded negative results — reproducing it requires
  redoing the extraction and mining, not copying a paper.
- **The event catalog and pipeline.** An 817,216-event, QC'd, cross-source catalog
  with a one-command rebuild, plus the extraction machinery validated on 35 named
  disasters.
- **The published methodology itself.** Frozen pre-registered thresholds, a
  tamper-evident single-use holdout gate, itemized misses, and a verdict recorded
  against the system's own interest. In a market of unverifiable weather-AI claims,
  an audit trail a due-diligence team can re-run is the differentiator.

## Roadmap

In progress (wave 2, matching the integration design and the open work branches):

- **Forecast fusion** — evaluate on forecast data, not only the reanalysis tail, to
  recover the short-lead classes' usefulness in live operation.
- **Seasonal baselines** — de-seasonalized thresholds and alarm budgets.
- **SAWS relay** — surface official national warnings alongside the platform's own
  heads-ups in South Africa, via the admin surface.
- **Basin/neighbor propagation** — k-of-n basin consensus and upstream-to-downstream
  propagation; the Limpopo study shows basin-wide simultaneous firing is the rare
  signature that marks the catastrophic floods, and identifies river routing as the
  largest single gap.
- **Push notifications** — deliver heads-ups without the app open.

Further out: expansion beyond the initial geography on the same global data, and
storm-scale predictors (the identified missing ingredient for tornado and convective
wind skill).

## Where the evidence lives

All in `weather/research/severe_weather/` in this repository: `PLAN.md` (frozen
acceptance thresholds), `catalog/` (event catalog + rebuild script),
`mining/results/SIGNATURES.md` (signature library), `BACKTEST.md` (the holdout report
of record), `detector/SUPPLEMENTARY_DEV.md` (post-hoc breakdowns),
`casestudy_limpopo/LIMPOPO_CASE_STUDY.md` (the blind case study), and
`INTEGRATION_DESIGN.md` (how it ships inside the platform).
