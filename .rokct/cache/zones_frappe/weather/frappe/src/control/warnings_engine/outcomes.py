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

"""Automatic outcome ledger - evidence of hits, false alarms, and misses (sw3).

"Leave shells of the nut - evidence where it was wrong." A daily verification
pass looks BACK at what the observed weather actually did and records one
"Severe Weather Outcome" row per judgement, building a growing, queryable
evidence base consumed later by a HUMAN-TRIGGERED retraining run (nothing
here retrains, retunes, or feeds back into the frozen detector - the ledger
is write-only evidence):

  verified        an episode was followed by genuinely extreme observed
                  weather - a hit;
  unverified      nothing extreme followed the episode - evidence of a false
                  alarm (the "shell");
  candidate_miss  disaster-grade extremes were observed at an active watch
                  cell with NO warning-tier episode covering them - evidence
                  the detector missed something.

Verification rules (all thresholds in the constants block below):

  * Only episodes that ENDED (status "expired") at least MIN_EPISODE_AGE_HOURS
    ago and whose window + POST_EPISODE_HOURS of aftermath the data source can
    already serve are judged; each episode is judged exactly once (the outcome
    row links back to it). Advisory-tier records and informational classes
    (cold_front) are never judged - they promise nothing checkable.
  * The observed window is [onset, valid_until + POST_EPISODE_HOURS]. Rain
    classes are judged on the window's max 24 h precipitation sum, wind
    classes on the max 10 m gust.
  * Precipitation extremeness is measured against the cell's OWN climatology
    ("Weather Cell Climatology" weekly-sum quantiles) when a row exists: the
    max 24 h fall is placed on the weekly-sum percentile curve, which is
    deliberately conservative (a 24 h fall reaching the weekly p90 is beyond
    the p99.5 of any daily distribution). Cells without a climatology row
    fall back to absolute mm thresholds. Gusts always use absolute m/s
    thresholds (the climatology carries no wind normals).

Candidate-miss scan (same daily pass): for each ACTIVE, recently-requested
watch cell, the last MISS_LOOKBACK_HOURS of observed data are scanned for
disaster-grade extremes (stricter thresholds than verification). An extreme
with no warning-tier episode of the matching class family overlapping the
scan window becomes a candidate_miss row - rate-limited to at most one per
(cell, class) per MISS_RATE_LIMIT_DAYS so the ledger never floods.

Safety properties (mirrors the evaluator's own contract):
  * master flag "severe_weather_outcome_ledger" (site config, default ON);
  * data-horizon short-circuit: the pass runs at most once per source-data
    advance - a tick with no new data costs one meta read;
  * per-episode / per-cell error isolation with rate-limited admin logging
    (TITLE_OUTCOME_PASS); run_outcome_pass never raises;
  * per-run series memo: overlapping windows for the same cell are fetched
    once (windows are ones the hourly evaluator recently read, so the S3
    client serves them largely from cache);
  * one admin Error Log line (TITLE_OUTCOME, rate-limited) ONLY for
    candidate_miss - the interesting case. NOTHING here is user-facing: no
    end-user copy, no API surface, no push.

All datetimes are UTC (naive), matching the rest of the engine.
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np

from . import features
from ...warnings_engine.admin_log import TITLE_OUTCOME, TITLE_OUTCOME_PASS, log_admin_error
from .climatology import precip_percentile, week_of

OUTCOME_DOCTYPE = "Severe Weather Outcome"
WARNING_DOCTYPE = "Severe Weather Warning"
WATCH_DOCTYPE = "Weather Watch Location"
CLIMO_DOCTYPE = "Weather Cell Climatology"

#: master switch (site config), default ON; "0"/"false"/"no"/"off" disables.
CONFIG_FLAG = "severe_weather_outcome_ledger"

#: evidence JSON schema version.
SCHEMA_VERSION = 1

VERDICT_VERIFIED = "verified"
VERDICT_UNVERIFIED = "unverified"
VERDICT_CANDIDATE_MISS = "candidate_miss"

# ------------------------------------------------------------------ #
# verification rules - the constants block (single reference)
# ------------------------------------------------------------------ #

#: an episode is judged only once it ended at least this long ago (wall
#: clock) - late-arriving reanalysis data settles first.
MIN_EPISODE_AGE_HOURS = 48

#: hours of observed aftermath appended to the episode window before
#: judging - "did it materialize afterwards?".
POST_EPISODE_HOURS = 48

#: classes the ledger judges. Informational classes (e.g. cold_front, which
#: is advisory-only by hard cap) are deliberately absent: they promise
#: nothing checkable, so they can never be "wrong".
VERIFIABLE_CLASSES = ("flash_flood", "flood", "destructive_wind", "tornado")

#: severities excluded from verification (informational tier).
EXCLUDED_SEVERITIES = ("advisory",)

#: which observed peak judges which class.
PRECIP_CLASSES = ("flash_flood", "flood")
GUST_CLASSES = ("destructive_wind", "tornado")

#: the only two variables the pass reads - cheap, and the same windows the
#: hourly evaluator recently fetched.
OUTCOME_VARIABLES = ("precipitation", "wind_gusts_10m")

#: min finite hours for a valid 24 h precipitation sum (75% of 24).
PRECIP_24H_MIN_HOURS = 18

#: climatology-relative verification threshold: the episode's max 24 h fall
#: placed on the cell's WEEKLY-sum percentile curve (conservative by
#: construction - see module docstring). >= p90 of the weekly distribution
#: within 24 h counts as "extremes materialized".
VERIFY_PRECIP_WEEKLY_PCTL = 0.90

#: candidate-miss precipitation gate: 24 h fall at/above the weekly p99
#: (the percentile curve's top anchor - beyond the p99.5 of any daily
#: distribution). Disaster-grade only.
MISS_PRECIP_WEEKLY_PCTL = 0.99

#: absolute fallbacks (mm in 24 h) for cells with no climatology row yet.
VERIFY_PRECIP_24H_MM = 50.0
MISS_PRECIP_24H_MM = 100.0

#: gust thresholds (m/s, ERA5 storage units): ~72 km/h verifies a wind
#: episode; ~90 km/h with no episode is a candidate miss.
VERIFY_GUST_MS = 20.0
MISS_GUST_MS = 25.0

#: candidate-miss scan window over freshly observed data (once per day).
MISS_LOOKBACK_HOURS = 72

#: ledger spam control: at most one candidate_miss per (cell, class) per
#: this many days.
MISS_RATE_LIMIT_DAYS = 7

#: class a candidate miss is filed under, per evidence kind (the observed
#: extreme cannot distinguish siblings within a family).
MISS_CLASS_FOR_PRECIP = "flash_flood"
MISS_CLASS_FOR_GUST = "destructive_wind"

#: cost bounds: at most this many episode verifications per daily run (the
#: rest catch up on later runs), and no backfill past this age.
EPISODES_PER_RUN_CAP = 200
BACKFILL_DAYS = 90

#: cache key of the horizon short-circuit (mirrors the evaluator's
#: per-location last_evaluated_horizon pattern, ledger-wide).
HORIZON_CACHE_KEY = "sww_outcome_last_horizon"  # compliance-ignore: py-hardcoded-secret (cache-key name, not a credential)

#: watch cells nobody requested for this long are not scanned for misses
#: (same staleness contract as the evaluator).
STALE_DAYS = 30


# ------------------------------------------------------------------ #
# configuration
# ------------------------------------------------------------------ #

def is_enabled() -> bool:
    """Master flag, default ON. Never raises (default on any trouble)."""
    try:
        import frappe
        raw = frappe.conf.get(CONFIG_FLAG)
    except Exception:
        return True
    if raw is None:
        return True
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


# ------------------------------------------------------------------ #
# pure computation: observed series -> peaks -> verdicts
# ------------------------------------------------------------------ #

def observed_peaks(series: dict, window_start: dt.datetime) -> dict:
    """Peak stats of one observed window.

    series: {"precipitation": mm/h array, "wind_gusts_10m": m/s array},
    hourly, starting at window_start. Missing variables or all-NaN series
    yield None peaks (callers then skip judgement rather than guess).
    """
    out = {"max_precip_24h_mm": None, "precip_peak_at": None,
           "max_gust_ms": None, "gust_peak_at": None}
    p = series.get("precipitation")
    if p is not None:
        sums = features.rolling_sum(np.asarray(p, dtype=np.float64),
                                    24, PRECIP_24H_MIN_HOURS)
        if np.isfinite(sums).any():
            idx = int(np.nanargmax(sums))
            out["max_precip_24h_mm"] = round(float(sums[idx]), 1)
            out["precip_peak_at"] = window_start + dt.timedelta(hours=idx)
    g = series.get("wind_gusts_10m")
    if g is not None:
        garr = np.asarray(g, dtype=np.float64)
        if np.isfinite(garr).any():
            idx = int(np.nanargmax(garr))
            out["max_gust_ms"] = round(float(garr[idx]), 1)
            out["gust_peak_at"] = window_start + dt.timedelta(hours=idx)
    return out


def precip_weekly_pctl(peaks: dict, normals) -> float | None:
    """The max 24 h fall on the cell's weekly-sum percentile curve.

    normals: the parsed Weather Cell Climatology normals dict, or None.
    None when there is no climatology, no peak, or the peak week carries no
    precip normals. The week is the calendar week the peak occurred in.
    """
    if not normals or peaks.get("max_precip_24h_mm") is None:
        return None
    try:
        wk = normals["weeks"][week_of(peaks["precip_peak_at"])]
        if wk.get("precip_mm") is None:
            return None
        return round(precip_percentile(peaks["max_precip_24h_mm"],
                                       wk["precip_mm"]), 3)
    except Exception:
        return None


def episode_verdict(event_class: str, peaks: dict, pctl) -> str | None:
    """verified | unverified for one ended episode, or None = cannot judge.

    Rain classes: climatology percentile when available (>= VERIFY_PRECIP_
    WEEKLY_PCTL verifies), else the absolute fallback. Wind classes: the
    absolute gust threshold. None (skip, retry on a later run) when the
    class's own peak could not be computed - a data gap must never be
    recorded as evidence of a false alarm.
    """
    if event_class in PRECIP_CLASSES:
        max24 = peaks.get("max_precip_24h_mm")
        if max24 is None:
            return None
        if pctl is not None:
            extreme = pctl >= VERIFY_PRECIP_WEEKLY_PCTL
        else:
            extreme = max24 >= VERIFY_PRECIP_24H_MM
    elif event_class in GUST_CLASSES:
        gust = peaks.get("max_gust_ms")
        if gust is None:
            return None
        extreme = gust >= VERIFY_GUST_MS
    else:
        return None
    return VERDICT_VERIFIED if extreme else VERDICT_UNVERIFIED


def miss_findings(peaks: dict, pctl) -> list:
    """Disaster-grade extremes in a quiet-scan window.

    Returns [(event_class, kind)] - at most one precip and one gust finding.
    Stricter thresholds than verification on purpose: only extremes that
    plainly should have been warned about become candidate misses.
    """
    findings = []
    max24 = peaks.get("max_precip_24h_mm")
    if max24 is not None:
        if pctl is not None:
            extreme = pctl >= MISS_PRECIP_WEEKLY_PCTL
        else:
            extreme = max24 >= MISS_PRECIP_24H_MM
        if extreme:
            findings.append((MISS_CLASS_FOR_PRECIP, "precip"))
    gust = peaks.get("max_gust_ms")
    if gust is not None and gust >= MISS_GUST_MS:
        findings.append((MISS_CLASS_FOR_GUST, "gust"))
    return findings


def build_evidence(kind: str, window_start, window_end, peaks: dict, pctl,
                   climatology_available: bool, source_name: str,
                   horizon, extra: dict | None = None) -> dict:
    """The queryable evidence JSON stored on every outcome row."""
    evidence = {
        "version": SCHEMA_VERSION,
        "kind": kind,  # "episode" | "quiet_scan"
        "window": {"start": window_start.isoformat(),
                   "end": window_end.isoformat()},
        "observed": {
            "max_precip_24h_mm": peaks.get("max_precip_24h_mm"),
            "precip_peak_at": (peaks["precip_peak_at"].isoformat()
                               if peaks.get("precip_peak_at") else None),
            # the max 24 h fall on the cell's weekly-sum percentile curve
            # (conservative; see module docstring); None without climatology
            "precip_weekly_pctl": pctl,
            "max_gust_ms": peaks.get("max_gust_ms"),
            "gust_peak_at": (peaks["gust_peak_at"].isoformat()
                             if peaks.get("gust_peak_at") else None),
            # no wind normals exist in the climatology - gusts are always
            # judged against the absolute thresholds below
            "gust_pctl": None,
        },
        "climatology_available": bool(climatology_available),
        "thresholds": {
            "verify_precip_weekly_pctl": VERIFY_PRECIP_WEEKLY_PCTL,
            "miss_precip_weekly_pctl": MISS_PRECIP_WEEKLY_PCTL,
            "verify_precip_24h_mm": VERIFY_PRECIP_24H_MM,
            "miss_precip_24h_mm": MISS_PRECIP_24H_MM,
            "verify_gust_ms": VERIFY_GUST_MS,
            "miss_gust_ms": MISS_GUST_MS,
        },
        "source": source_name,
        "data_horizon": horizon.isoformat(),
    }
    if extra:
        evidence.update(extra)
    return evidence


# ------------------------------------------------------------------ #
# frappe-backed helpers
# ------------------------------------------------------------------ #

def _load_normals(grid_key: str):
    """The cell's stored climatology normals, or None. NEVER builds one -
    the ledger must not add S3 cost; cells without a row use the absolute
    fallbacks until the hourly evaluator builds it."""
    import frappe

    try:
        raw = frappe.db.get_value(
            CLIMO_DOCTYPE, {"grid_key": grid_key}, "normals_json")
        if not raw:
            return None
        normals = json.loads(raw)
        return normals if normals.get("weeks") else None
    except Exception:
        return None


def _insert_outcome(watch_location: str, event_class: str, verdict: str,
                    period_start, period_end, evidence: dict, now,
                    warning=None) -> None:
    import frappe

    frappe.get_doc({
        "doctype": OUTCOME_DOCTYPE,
        "warning": warning,
        "watch_location": watch_location,
        "event_class": event_class,
        "verdict": verdict,
        "period_start": period_start,
        "period_end": period_end,
        "peak_precip_24h_mm": evidence["observed"]["max_precip_24h_mm"],
        "peak_precip_pctl": evidence["observed"]["precip_weekly_pctl"],
        "peak_gust_ms": evidence["observed"]["max_gust_ms"],
        "recorded_at": now,
        "evidence": json.dumps(evidence),
    }).insert(ignore_permissions=True)


class _SeriesMemo:
    """Per-run memo of observed windows: one fetch per (cell, window)."""

    def __init__(self, source):
        self.source = source
        self._cache = {}

    def get(self, latitude, longitude, start, end):
        key = (round(float(latitude), 4), round(float(longitude), 4),
               start, end)
        if key not in self._cache:
            self._cache[key] = self.source.hourly_series(
                latitude, longitude, list(OUTCOME_VARIABLES), start, end)
        return self._cache[key]


# ------------------------------------------------------------------ #
# the daily pass
# ------------------------------------------------------------------ #

def run_outcome_pass():
    """Scheduled (daily): verify ended episodes, then scan for candidate
    misses. Master-flagged, horizon-short-circuited, never raises."""
    try:
        if not is_enabled():
            return
        import frappe
        from frappe.utils import get_datetime

        from .sources.base import get_data_source

        source = get_data_source()
        horizon = source.data_horizon_utc()

        # horizon short-circuit: the source's archive advances ~daily; a run
        # against an already-processed horizon would only re-read windows to
        # reach identical conclusions.
        try:
            cached = frappe.cache().get_value(HORIZON_CACHE_KEY)
            if cached and get_datetime(cached) >= horizon:
                return
        except Exception:
            pass

        now = _utcnow()
        memo = _SeriesMemo(source)
        _verify_ended_episodes(memo, horizon, now)
        _scan_candidate_misses(memo, horizon, now)

        try:
            frappe.cache().set_value(HORIZON_CACHE_KEY, horizon.isoformat())
        except Exception:
            pass
    except Exception:
        log_admin_error(TITLE_OUTCOME_PASS)


def _location_coords(loc_name: str):
    import frappe

    row = frappe.db.get_value(
        WATCH_DOCTYPE, loc_name, ["latitude", "longitude"], as_dict=True)
    if not row:
        return None
    return row


def _verify_ended_episodes(memo, horizon, now):
    """One outcome row per ended, not-yet-judged, verifiable episode."""
    import frappe

    # eligible: ended >= MIN_EPISODE_AGE_HOURS ago AND the aftermath window
    # is fully inside the source's already-available data.
    cutoff = min(now - dt.timedelta(hours=MIN_EPISODE_AGE_HOURS),
                 horizon - dt.timedelta(hours=POST_EPISODE_HOURS))
    floor = now - dt.timedelta(days=BACKFILL_DAYS)
    episodes = frappe.get_all(
        WARNING_DOCTYPE,
        filters={
            "status": "expired",
            "severity": ["not in", list(EXCLUDED_SEVERITIES)],
            "event_class": ["in", list(VERIFIABLE_CLASSES)],
            "valid_until": ["between", [floor, cutoff]],
            # drill fence: training-exercise records (warnings_engine/
            # drill.py) replay past weather and must never be judged -
            # they would poison the retraining evidence base
            "is_drill": ["!=", 1],
        },
        fields=["name", "watch_location", "event_class", "severity",
                "onset", "valid_until", "detector_tier", "confidence"],
        order_by="valid_until desc",
        limit_page_length=EPISODES_PER_RUN_CAP,
    )
    if not episodes:
        return
    judged = {row.warning for row in frappe.get_all(
        OUTCOME_DOCTYPE,
        filters={"warning": ["in", [e.name for e in episodes]]},
        fields=["warning"],
    )}
    for ep in episodes:
        if ep.name in judged:
            continue
        try:
            _judge_episode(memo, ep, horizon, now)
        except Exception:
            log_admin_error(TITLE_OUTCOME_PASS)


def _judge_episode(memo, ep, horizon, now):
    from frappe.utils import get_datetime

    onset = get_datetime(ep.onset)
    valid_until = get_datetime(ep.valid_until)
    if not onset or not valid_until:
        return
    coords = _location_coords(ep.watch_location)
    if not coords:
        return
    start = onset
    end = min(valid_until + dt.timedelta(hours=POST_EPISODE_HOURS), horizon)
    series = memo.get(coords.latitude, coords.longitude, start, end)
    peaks = observed_peaks(series, start)
    normals = _load_normals(ep.watch_location)
    pctl = precip_weekly_pctl(peaks, normals)
    verdict = episode_verdict(ep.event_class, peaks, pctl)
    if verdict is None:
        return  # data gap: never judged blind; retried on a later horizon
    evidence = build_evidence(
        "episode", start, end, peaks, pctl, normals is not None,
        getattr(memo.source, "name", "unknown"), horizon,
        extra={"episode": {
            "warning": ep.name,
            "severity": ep.severity,
            "detector_tier": ep.detector_tier,
            "confidence": ep.confidence,
        }})
    _insert_outcome(ep.watch_location, ep.event_class, verdict,
                    start, end, evidence, now, warning=ep.name)


def _scan_candidate_misses(memo, horizon, now):
    """Unwarned disaster-grade extremes at active watch cells."""
    import frappe
    from frappe.utils import get_datetime

    stale_before = now - dt.timedelta(days=STALE_DAYS)
    locations = frappe.get_all(
        WATCH_DOCTYPE,
        filters={"active": 1},
        fields=["name", "latitude", "longitude", "last_requested_at"],
    )
    start = horizon - dt.timedelta(hours=MISS_LOOKBACK_HOURS)
    for loc in locations:
        last_requested = (get_datetime(loc.last_requested_at)
                          if loc.last_requested_at else None)
        if last_requested and last_requested < stale_before:
            continue
        try:
            _scan_cell(memo, loc, start, horizon, now)
        except Exception:
            log_admin_error(TITLE_OUTCOME_PASS)


def _scan_cell(memo, loc, start, horizon, now):
    import frappe

    series = memo.get(loc.latitude, loc.longitude, start, horizon)
    peaks = observed_peaks(series, start)
    normals = _load_normals(loc.name)
    pctl = precip_weekly_pctl(peaks, normals)
    for event_class, kind in miss_findings(peaks, pctl):
        family = PRECIP_CLASSES if kind == "precip" else GUST_CLASSES
        # was ANY warning-tier episode of the matching family live over the
        # scan window? (any status - an expired record that covered the
        # extreme still means "we warned")
        warned = frappe.get_all(
            WARNING_DOCTYPE,
            filters={
                "watch_location": loc.name,
                "event_class": ["in", list(family)],
                "severity": ["not in", list(EXCLUDED_SEVERITIES)],
                "onset": ["<=", horizon],
                "valid_until": [">=", start],
                # drill fence: a replayed exercise record is not real
                # coverage - it must never mask a candidate miss
                "is_drill": ["!=", 1],
            },
            fields=["name"],
            limit_page_length=1,
        )
        if warned:
            continue
        # rate limit: at most one candidate_miss per (cell, class) per week
        recent = frappe.get_all(
            OUTCOME_DOCTYPE,
            filters={
                "watch_location": loc.name,
                "event_class": event_class,
                "verdict": VERDICT_CANDIDATE_MISS,
                "recorded_at": [">=", now - dt.timedelta(
                    days=MISS_RATE_LIMIT_DAYS)],
            },
            fields=["name"],
            limit_page_length=1,
        )
        if recent:
            continue
        evidence = build_evidence(
            "quiet_scan", start, horizon, peaks, pctl, normals is not None,
            getattr(memo.source, "name", "unknown"), horizon)
        _insert_outcome(loc.name, event_class, VERDICT_CANDIDATE_MISS,
                        start, horizon, evidence, now, warning=None)
        log_admin_error(TITLE_OUTCOME, (
            f"candidate miss at {loc.name} ({event_class}): "
            f"max 24h precip {peaks.get('max_precip_24h_mm')} mm "
            f"(weekly pctl {pctl}), max gust {peaks.get('max_gust_ms')} m/s, "
            f"with no warning-tier episode over the last "
            f"{MISS_LOOKBACK_HOURS} h."))
