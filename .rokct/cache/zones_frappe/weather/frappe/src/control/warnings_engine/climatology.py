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

"""Per-grid-cell calendar-week climatology + out-of-season anomaly features.

Rain that is unusual FOR THE SEASON at a location should score as more
anomalous. This module builds, once ever per watch cell, weekly normals from
the ERA5 year files (1940-2021) in the public s3://openmeteo archive, caches
them durably in the "Weather Cell Climatology" doctype, and exposes three
scalar features per evaluation:

  precip_pctl            trailing 7-day precipitation as a percentile of this
                         calendar week's climatological weekly-sum distribution
  tcwv_z                 trailing 24 h TCWV mean as a z-score against this
                         week's climatological mean/std
  out_of_season_factor   precip_pctl weighted by how climatologically DRY this
                         week is at this cell - a wet spell during dry-season
                         weeks scores higher than the same spell in the wet
                         season

STRICT NON-INTERFERENCE CONTRACT: the frozen per-class detector rules are
untouched and these features are never inputs to detector.run_class. They feed
only (a) admin/fusion context recorded in the warning's precursors JSON plus
an optional calm copy sentence ("unusual for this time of year"), and (b) a
BOUNDED confidence annotation (bounded_confidence_boost, at most
+MAX_CONFIDENCE_BOOST, recorded alongside - never replacing - the detector's
own confidence). Nothing here can change which tier fires or whether a
warning surfaces; any failure in this module degrades to "no seasonal
context", never to a missed or altered warning.

Config flag (tenant site config, mirroring severe_weather_source):
  "severe_weather_seasonal_climatology": default ON; set to "0"/"false"/"off"
  to disable all seasonal computation.

Year subsampling (cost decision, documented): every 3rd year 1940..2021
(28 sample years). One year of hourly point data for one variable is ~8
ranged reads (the year files chunk time in 1095 h blocks), so a full cell
build is 2 variables x 28 years x ~8 reads = ~450 ranged reads plus 2
availability listings - a few hundred small GETs, once ever per cell. 28
samples per calendar week give solid median/p75/p90; the p99 of the weekly
distribution is necessarily close to the sample maximum at this sample size
(fine for a bounded factor; documented limitation).

Calendar weeks: week w covers day-of-year [7w, 7w+7), 0-based, w = 0..51;
days 364/365 fold into week 51. The Feb-29 leap day shifts post-February
dates by one day within their week - negligible at weekly resolution.

All quantities in ERA5 storage units (precipitation mm/h -> weekly sums in
mm; TCWV kg/m2). Weekly sums are computed as (mean of finite hourly values)
x 168 so data gaps and week 51's extra days never bias the distribution; a
(year, week) sample needs >= 75% finite hours or it is dropped.
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np

from ...warnings_engine.admin_log import log_admin_error

CLIMO_DOCTYPE = "Weather Cell Climatology"
TITLE_CLIMATOLOGY = "SevereWeather: climatology unavailable"

CONFIG_FLAG = "severe_weather_seasonal_climatology"

SCHEMA_VERSION = 1
WEEKS_PER_YEAR = 52

#: sampled climatology years: every 3rd year across the full year-file era.
SAMPLE_YEARS = tuple(range(1940, 2022, 3))

#: the two variables the weekly normals are built from (ERA5 storage units).
CLIMO_VARIABLES = ("precipitation", "total_column_integrated_water_vapour")

#: a calendar week's normals need at least this many year samples.
MIN_YEAR_SAMPLES = 15

#: fraction of a week's nominal hours that must be finite to keep a sample.
MIN_WEEK_COVERAGE = 0.75

#: trailing windows evaluated against the normals, and their coverage floors.
PRECIP_WINDOW_H = 168
PRECIP_MIN_FINITE = 126     # 75% of 168
TCWV_WINDOW_H = 24
TCWV_MIN_FINITE = 18        # 75% of 24

#: below this much trailing 7-day rain the out-of-season factor is 0 - dry
#: season drizzle must never look anomalous just because the week is dry.
MIN_RAIN_MM_7D = 10.0

#: floor for the weekly TCWV std (kg/m2) so z-scores cannot explode.
TCWV_STD_FLOOR = 0.5

#: hard cap of the confidence annotation: at most +0.15, absolute.
MAX_CONFIDENCE_BOOST = 0.15

#: event classes whose confidence annotation may use the rain features.
RAIN_CLASSES = ("flash_flood", "flood")

#: thresholds for the optional calm copy sentence.
NOTE_OOS_FACTOR = 0.5
NOTE_PCTL = 0.95

#: retry backoff after a failed cell build (seconds) - the evaluator runs
#: hourly; a broken build must not add a few hundred reads every tick.
BUILD_BACKOFF_SECONDS = 6 * 3600

#: calm, legal-safe copy fragments (no "warning", no official taxonomy) -
#: appended to an already-approved message, never shown on their own.
_NOTE_OUT_OF_SEASON = "This much rain is unusual for this time of year."
_NOTE_EXTREME_IN_SEASON = ("Recent rain is at the high end of what's usual "
                           "here, even for this time of year.")

#: every sentence seasonal_note() can ever append - public so the combined-
#: copy cap (official_alerts._appended_extra_count) can recognise them.
NOTE_SENTENCES = (_NOTE_OUT_OF_SEASON, _NOTE_EXTREME_IN_SEASON)


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #

def is_enabled() -> bool:
    """Site-config flag, default ON. Never raises (default on any trouble)."""
    try:
        import frappe
        raw = frappe.conf.get(CONFIG_FLAG)
    except Exception:
        return True
    if raw is None:
        return True
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


# --------------------------------------------------------------------------- #
# pure computation: hourly year series -> weekly normals
# --------------------------------------------------------------------------- #

def week_of(ts: dt.datetime) -> int:
    """Calendar week 0..51 of a datetime (day-of-year // 7, capped at 51)."""
    doy = (ts.date() - dt.date(ts.year, 1, 1)).days
    return min(doy // 7, WEEKS_PER_YEAR - 1)


def weekly_mean(hourly) -> np.ndarray:
    """(52,) mean of finite hourly values per calendar week for ONE year.

    NaN where fewer than MIN_WEEK_COVERAGE of the week's nominal hours are
    finite. Input length 8760 or 8784 (leap); week 51 absorbs the tail days.
    """
    x = np.asarray(hourly, dtype=np.float64)
    week = np.minimum((np.arange(x.size) // 24) // 7, WEEKS_PER_YEAR - 1)
    finite = np.isfinite(x)
    sums = np.zeros(WEEKS_PER_YEAR)
    cnts = np.zeros(WEEKS_PER_YEAR)
    np.add.at(sums, week[finite], x[finite])
    np.add.at(cnts, week[finite], 1.0)
    nominal = np.bincount(week, minlength=WEEKS_PER_YEAR).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        means = sums / cnts
    means[cnts < MIN_WEEK_COVERAGE * nominal] = np.nan
    return means


def normals_from_samples(precip_weekly_sums, tcwv_weekly_means) -> list:
    """Across-year weekly samples -> the 52-entry "weeks" normals list.

    precip_weekly_sums: (n_years, 52) weekly precipitation sums (mm).
    tcwv_weekly_means:  (n_years, 52) weekly TCWV means (kg/m2).
    A week with fewer than MIN_YEAR_SAMPLES finite samples for a variable
    gets None for that variable's block (features then degrade to None).
    """
    ps = np.asarray(precip_weekly_sums, dtype=np.float64)
    ts = np.asarray(tcwv_weekly_means, dtype=np.float64)
    weeks = []
    for w in range(WEEKS_PER_YEAR):
        p = ps[:, w][np.isfinite(ps[:, w])]
        t = ts[:, w][np.isfinite(ts[:, w])]
        precip = None
        if p.size >= MIN_YEAR_SAMPLES:
            precip = {
                "n": int(p.size),
                "median": round(float(np.percentile(p, 50)), 2),
                "p75": round(float(np.percentile(p, 75)), 2),
                "p90": round(float(np.percentile(p, 90)), 2),
                "p99": round(float(np.percentile(p, 99)), 2),
            }
        tcwv = None
        if t.size >= MIN_YEAR_SAMPLES:
            tcwv = {
                "n": int(t.size),
                "mean": round(float(np.mean(t)), 2),
                "std": round(float(np.std(t, ddof=1)), 2),
            }
        weeks.append({"week": w, "precip_mm": precip, "tcwv": tcwv})
    return weeks


def compute_cell_normals(source, latitude, longitude,
                         years=SAMPLE_YEARS) -> dict:
    """Build the full normals document for one grid cell (network via source).

    source: any WarningsDataSource (hourly_series is the only method used).
    Cost: len(CLIMO_VARIABLES) x len(years) x ~8 ranged reads, once ever.
    """
    n_years = len(years)
    p_sums = np.full((n_years, WEEKS_PER_YEAR), np.nan)
    t_means = np.full((n_years, WEEKS_PER_YEAR), np.nan)
    for i, year in enumerate(years):
        series = source.hourly_series(
            latitude, longitude, list(CLIMO_VARIABLES),
            dt.datetime(year, 1, 1), dt.datetime(year + 1, 1, 1))
        p_sums[i] = weekly_mean(series["precipitation"]) * PRECIP_WINDOW_H
        t_means[i] = weekly_mean(
            series["total_column_integrated_water_vapour"])
    return {
        "version": SCHEMA_VERSION,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "years_sampled": list(years),
        "source": getattr(source, "name", "unknown"),
        "computed_at": dt.datetime.utcnow().replace(microsecond=0).isoformat(),
        "weeks": normals_from_samples(p_sums, t_means),
    }


# --------------------------------------------------------------------------- #
# pure computation: normals + current window -> seasonal features
# --------------------------------------------------------------------------- #

def precip_percentile(value_mm: float, precip_normal: dict) -> float:
    """Percentile (0..0.99) of a 7-day sum against a week's distribution.

    Piecewise-linear through the stored quantile anchors (0 -> 0, median ->
    0.50, p75 -> 0.75, p90 -> 0.90, p99 -> 0.99), flat at 0.99 beyond p99.
    A bone-dry week (all anchors 0) maps any positive rain to 0.99.
    """
    v = float(value_mm)
    if not np.isfinite(v) or v <= 0.0:
        return 0.0
    xs, fs = [0.0], [0.0]
    for key, pc in (("median", 0.50), ("p75", 0.75),
                    ("p90", 0.90), ("p99", 0.99)):
        q = float(precip_normal[key])
        if q > xs[-1]:
            xs.append(q)
            fs.append(pc)
    if len(xs) == 1:            # every quantile is 0: any rain is extreme
        return 0.99
    return float(np.interp(v, xs, fs))


def week_wetness_ranks(weeks: list) -> list:
    """Rank of each week's median weekly rain among the 52 weeks, in [0, 1].

    0 = driest week of the year at this cell, 1 = wettest; ties share the
    midrank (a fully arid cell ranks every week 0.5). None where a week has
    no precip normals.
    """
    medians = [None if w["precip_mm"] is None else w["precip_mm"]["median"]
               for w in weeks]
    known = [m for m in medians if m is not None]
    out = []
    for m in medians:
        if m is None or len(known) < 2:
            out.append(None)
            continue
        below = sum(1 for k in known if k < m)
        ties = sum(1 for k in known if k == m) - 1
        out.append(round((below + 0.5 * ties) / (len(known) - 1), 3))
    return out


def out_of_season_factor(pctl: float, wetness_rank, precip_7d_mm: float) -> float:
    """Wet spell during climatologically dry weeks scores higher, in [0, 1].

    precip_pctl weighted by (1 - week wetness rank): the same 95th-percentile
    spell is worth ~0.95 in the year's driest week and ~0 in its wettest.
    Zero below MIN_RAIN_MM_7D of absolute rain, and zero (conservative) when
    the week's wetness rank is unknown.
    """
    if wetness_rank is None or not np.isfinite(precip_7d_mm):
        return 0.0
    if precip_7d_mm < MIN_RAIN_MM_7D:
        return 0.0
    return round(float(pctl) * (1.0 - float(wetness_rank)), 3)


def seasonal_snapshot(normals: dict, series: dict, horizon: dt.datetime):
    """Normals + the evaluator's already-fetched window -> feature snapshot.

    series is the evaluator's hourly window ENDING at the data horizon (the
    same arrays features.compute_features consumes - no extra reads). Returns
    a JSON-ready dict, or None when this week has no usable normals. Fields
    with insufficient current data are None.
    """
    weeks = normals["weeks"]
    w = week_of(horizon)
    wk = weeks[w]

    precip_pctl = precip_7d = oos = None
    if wk["precip_mm"] is not None:
        p = np.asarray(series["precipitation"], dtype=np.float64)[-PRECIP_WINDOW_H:]
        finite = p[np.isfinite(p)]
        if finite.size >= PRECIP_MIN_FINITE:
            precip_7d = round(float(finite.mean() * PRECIP_WINDOW_H), 1)
            precip_pctl = round(precip_percentile(precip_7d, wk["precip_mm"]), 3)
            rank = week_wetness_ranks(weeks)[w]
            oos = out_of_season_factor(precip_pctl, rank, precip_7d)

    tcwv_z = None
    if wk["tcwv"] is not None:
        t = np.asarray(
            series["total_column_integrated_water_vapour"],
            dtype=np.float64)[-TCWV_WINDOW_H:]
        finite = t[np.isfinite(t)]
        if finite.size >= TCWV_MIN_FINITE:
            std = max(float(wk["tcwv"]["std"]), TCWV_STD_FLOOR)
            tcwv_z = round((float(finite.mean()) - float(wk["tcwv"]["mean"])) / std, 2)

    if precip_pctl is None and tcwv_z is None:
        return None
    return {
        "week": w,
        "precip_7d_mm": precip_7d,
        "precip_pctl": precip_pctl,
        "tcwv_z": tcwv_z,
        "out_of_season_factor": oos,
        "week_normals": {"precip_mm": wk["precip_mm"], "tcwv": wk["tcwv"]},
    }


# --------------------------------------------------------------------------- #
# bounded fusion outputs (annotation + copy) - never change what fires
# --------------------------------------------------------------------------- #

def bounded_confidence_boost(confidence: float, snapshot) -> float:
    """Detector confidence + a bounded seasonal-anomaly increment.

    Driver b in [0, 1] is the larger of the out-of-season factor and the
    beyond-p90 exceedance ((pctl - 0.90) / 0.09); the increment is at most
    MAX_CONFIDENCE_BOOST absolute, and the result is clamped to [0, 1].
    Recorded in precursors as an annotation only - the detector's tier and
    raw confidence are never modified.
    """
    conf = float(confidence)
    if not snapshot:
        return round(min(max(conf, 0.0), 1.0), 3)
    oos = snapshot.get("out_of_season_factor") or 0.0
    pctl = snapshot.get("precip_pctl") or 0.0
    exceed = min(max((pctl - 0.90) / 0.09, 0.0), 1.0)
    b = max(float(oos), exceed)
    return round(min(max(conf, 0.0) + MAX_CONFIDENCE_BOOST * b, 1.0), 3)


def seasonal_note(snapshot):
    """Optional calm sentence appended to an ALREADY-surfacing message.

    Never contains the word "warning" or official warning taxonomy; never
    causes a message to exist - it only enriches approved copy. None when
    nothing seasonal is noteworthy.
    """
    if not snapshot:
        return None
    oos = snapshot.get("out_of_season_factor") or 0.0
    pctl = snapshot.get("precip_pctl") or 0.0
    if oos >= NOTE_OOS_FACTOR:
        return _NOTE_OUT_OF_SEASON
    if pctl >= NOTE_PCTL:
        return _NOTE_EXTREME_IN_SEASON
    return None


# --------------------------------------------------------------------------- #
# durable per-cell cache (frappe-backed) + evaluator entry point
# --------------------------------------------------------------------------- #

def _load_or_compute_normals(source, loc):
    """Durable load of the cell's normals; build + store on first evaluation.

    Storage: one "Weather Cell Climatology" row per grid cell (name ==
    grid_key == the Weather Watch Location name), normals JSON in
    normals_json. A failed build sets a BUILD_BACKOFF_SECONDS cache backoff
    so the hourly job does not re-pay a few hundred reads every tick.
    """
    import frappe

    row = frappe.db.get_value(
        CLIMO_DOCTYPE, {"grid_key": loc.name}, ["name", "normals_json"],
        as_dict=True)
    if row and row.normals_json:
        try:
            normals = json.loads(row.normals_json)
            if normals.get("version") == SCHEMA_VERSION:
                return normals
        except Exception:
            pass  # unreadable/outdated: rebuild below

    backoff_key = f"sww_climo_backoff_{loc.name}"
    try:
        if frappe.cache().get_value(backoff_key):
            return None
    except Exception:
        pass

    try:
        normals = compute_cell_normals(source, loc.latitude, loc.longitude)
    except Exception:
        try:
            frappe.cache().set_value(backoff_key, 1,
                                     expires_in_sec=BUILD_BACKOFF_SECONDS)
        except Exception:
            pass
        raise

    payload = json.dumps(normals)
    if row:
        frappe.db.set_value(CLIMO_DOCTYPE, row.name, {
            "normals_json": payload,
            "computed_at": normals["computed_at"],
            "years_sampled": len(normals["years_sampled"]),
            "source": normals["source"],
        })
    else:
        frappe.get_doc({
            "doctype": CLIMO_DOCTYPE,
            "grid_key": loc.name,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "computed_at": normals["computed_at"],
            "years_sampled": len(normals["years_sampled"]),
            "source": normals["source"],
            "normals_json": payload,
        }).insert(ignore_permissions=True)
    return normals


def seasonal_context(source, loc, series, horizon):
    """Evaluator hook: the cell's seasonal snapshot, or None.

    NEVER raises - any failure logs (rate-limited) and degrades to "no
    seasonal context"; the frozen detector pipeline is unaffected either way.
    """
    try:
        if not is_enabled():
            return None
        normals = _load_or_compute_normals(source, loc)
        if not normals:
            return None
        return seasonal_snapshot(normals, series, horizon)
    except Exception:
        log_admin_error(TITLE_CLIMATOLOGY)
        return None
