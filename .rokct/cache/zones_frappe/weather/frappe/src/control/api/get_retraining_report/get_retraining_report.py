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

"""CONTROL-side ADMIN endpoint: the outcome ledger read back as a retraining
report (sw5).

The daily outcome pass (warnings_engine/outcomes.py) leaves "shells of the
nut" - one Severe Weather Outcome row per after-the-fact verdict. This
endpoint is the first consumer of those shells: it compiles, per event
class, the observed performance (hits, misses, false alarms, observed POD,
observed FAR, observed median lead) side by side with the FROZEN acceptance
thresholds from weather/research/severe_weather/PLAN.md, and states a plain
verdict per class:

  meeting_bar        every computable observed metric is within its frozen bar;
  below_bar          at least one computable observed metric misses its bar;
  insufficient_data  the ledger does not yet hold enough judgements for this
                     class to say anything (the common early state - counts
                     are reported, nothing is divided by zero).

ADMIN TELEMETRY ONLY. The endpoint requires the System Manager role and its
payload NEVER reaches end-user surfaces - it exists so a human can decide
whether to trigger the offline retraining harness
(weather/research/severe_weather/retraining/retrain.py) and, separately,
whether to adopt what that harness produces. Nothing here retunes anything.

Honesty notes baked into the payload (and repeated here for the reader):

  * Observed POD is computed as verified / (verified + candidate_miss).
    Candidate misses are deliberately disaster-grade-only and rate-limited
    (at most one per cell/class per week), so the ledger under-counts misses
    and this POD is GENEROUS relative to the backtest POD in PLAN.md. A
    class scoring below bar on this generous measure is unambiguously below
    bar.
  * Observed FAR is unverified / (verified + unverified) - the frozen
    definition (false alarms / all alarms) applied to judged episodes.
  * Observed lead is a proxy: hours from the start of an episode's live
    window to the observed peak of the class-relevant variable, taken from
    the row's evidence JSON. The episode was live at least that long before
    the extremes peaked.

The pure aggregation half of this module (summarize_ledger and friends) is
deliberately frappe-free: the offline retraining harness loads this file by
path and reuses the same arithmetic on a ledger export, so the desk report
and the harness can never disagree about what the ledger says.
"""
from __future__ import annotations

import datetime as dt
import json

try:  # composed into the control product: frappe + common admin logging
    import frappe
    from ....warnings_engine.admin_log import (
        TITLE_RETRAIN_REPORT,
        log_admin_error,
    )
except ImportError:  # standalone reuse by research/severe_weather/retraining
    frappe = None

    def log_admin_error(title, message=None):  # noqa: D103 - stand-in
        pass

    TITLE_RETRAIN_REPORT = "SevereWeather: retraining report error"


OUTCOME_DOCTYPE = "Severe Weather Outcome"

#: the ledger's verdict vocabulary (mirrors warnings_engine/outcomes.py).
VERDICT_VERIFIED = "verified"
VERDICT_UNVERIFIED = "unverified"
VERDICT_CANDIDATE_MISS = "candidate_miss"

#: classes the ledger judges (outcomes.VERIFIABLE_CLASSES).
EVENT_CLASSES = ("flash_flood", "flood", "destructive_wind", "tornado")
PRECIP_CLASSES = ("flash_flood", "flood")

#: FROZEN acceptance thresholds. Source of truth:
#: weather/research/severe_weather/PLAN.md, "Acceptance thresholds
#: (frozen 2026-08-19)" - the same numbers as detector/backtest.py FROZEN.
#: DO NOT EDIT: results are compared against these bars, never the reverse.
FROZEN_THRESHOLDS = {
    "flash_flood":      {"pod": 0.60, "far": 0.60, "min_lead_h": 6},
    "flood":            {"pod": 0.65, "far": 0.50, "min_lead_h": 24},
    "destructive_wind": {"pod": 0.70, "far": 0.40, "min_lead_h": 12},
    "tornado":          {"pod": 0.40, "far": 0.75, "min_lead_h": 3},
}
THRESHOLDS_SOURCE = ("weather/research/severe_weather/PLAN.md "
                     "(Acceptance thresholds, frozen 2026-08-19)")

#: a class earns a real verdict only once the ledger holds at least this many
#: judgements for it; below that the verdict is insufficient_data. Also the
#: recommended per-class volume before running the retraining harness.
MIN_OUTCOMES_FOR_VERDICT = 20

#: median lead is reported only over at least this many observed leads.
MIN_LEADS_FOR_MEDIAN = 5

CLASS_VERDICT_MEETING = "meeting_bar"
CLASS_VERDICT_BELOW = "below_bar"
CLASS_VERDICT_INSUFFICIENT = "insufficient_data"

CHECK_PASS = "pass"
CHECK_FAIL = "fail"
CHECK_NA = "not_computable"


# --------------------------------------------------------------------------- #
# pure aggregation (no frappe) - reused by the offline retraining harness
# --------------------------------------------------------------------------- #

def _parse_evidence(raw):
    """Evidence JSON as a dict, or None. Accepts dict, JSON string, None."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except (TypeError, ValueError):
        return None


def _parse_iso(value):
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value
    try:
        return dt.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def observed_lead_hours(event_class: str, evidence) -> float | None:
    """Observed-lead proxy for one VERIFIED ledger row, in hours.

    Hours from the start of the episode's live window (evidence
    window.start) to the observed peak of the class-relevant variable
    (precip_peak_at for rain classes, gust_peak_at for wind classes).
    None whenever any piece is missing or malformed - a missing lead is
    reported as missing, never guessed.
    """
    ev = _parse_evidence(evidence)
    if not ev:
        return None
    start = _parse_iso((ev.get("window") or {}).get("start"))
    observed = ev.get("observed") or {}
    peak_key = ("precip_peak_at" if event_class in PRECIP_CLASSES
                else "gust_peak_at")
    peak = _parse_iso(observed.get(peak_key))
    if start is None or peak is None:
        return None
    hours = (peak - start).total_seconds() / 3600.0
    return round(hours, 1) if hours >= 0 else None


def _median(values: list) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _check(value, bar, at_least: bool) -> str:
    if value is None:
        return CHECK_NA
    ok = value >= bar if at_least else value <= bar
    return CHECK_PASS if ok else CHECK_FAIL


def summarize_class(event_class: str, rows: list) -> dict:
    """Observed performance vs the frozen bar for one class.

    rows: ledger rows (dicts with at least "verdict"; "evidence" optional)
    already filtered to this event_class. Pure - never divides by zero,
    never raises on malformed evidence.
    """
    thresholds = FROZEN_THRESHOLDS[event_class]
    hits = sum(1 for r in rows if r.get("verdict") == VERDICT_VERIFIED)
    false_alarms = sum(1 for r in rows
                       if r.get("verdict") == VERDICT_UNVERIFIED)
    misses = sum(1 for r in rows
                 if r.get("verdict") == VERDICT_CANDIDATE_MISS)
    total = len(rows)

    events = hits + misses            # observed event universe (see caveat)
    alarms = hits + false_alarms      # all judged alarms
    pod = round(hits / events, 3) if events else None
    far = round(false_alarms / alarms, 3) if alarms else None

    leads = []
    for r in rows:
        if r.get("verdict") != VERDICT_VERIFIED:
            continue
        lead = observed_lead_hours(event_class, r.get("evidence"))
        if lead is not None:
            leads.append(lead)
    median_lead = (round(_median(leads), 1)
                   if len(leads) >= MIN_LEADS_FOR_MEDIAN else None)

    if total < MIN_OUTCOMES_FOR_VERDICT:
        verdict = CLASS_VERDICT_INSUFFICIENT
        checks = {"pod": CHECK_NA, "far": CHECK_NA, "median_lead": CHECK_NA}
        detail = (f"insufficient data: {total} judged outcome(s) on record, "
                  f"{MIN_OUTCOMES_FOR_VERDICT} needed for a verdict "
                  f"({hits} hit(s), {false_alarms} false alarm(s), "
                  f"{misses} candidate miss(es))")
    else:
        checks = {
            "pod": _check(pod, thresholds["pod"], at_least=True),
            "far": _check(far, thresholds["far"], at_least=False),
            "median_lead": _check(median_lead, thresholds["min_lead_h"],
                                  at_least=True),
        }
        failing = sorted(k for k, v in checks.items() if v == CHECK_FAIL)
        computable = [k for k, v in checks.items() if v != CHECK_NA]
        if failing:
            verdict = CLASS_VERDICT_BELOW
            detail = ("below bar on " + ", ".join(failing)
                      + f" ({total} judged outcomes)")
        elif "pod" in computable and "far" in computable:
            verdict = CLASS_VERDICT_MEETING
            detail = (f"meeting bar on every computable metric "
                      f"({', '.join(computable)}; {total} judged outcomes)")
            if checks["median_lead"] == CHECK_NA:
                detail += ("; observed lead not yet computable "
                           f"(fewer than {MIN_LEADS_FOR_MEDIAN} usable leads)")
        else:
            verdict = CLASS_VERDICT_INSUFFICIENT
            detail = (f"insufficient data: {total} rows on record but "
                      "neither observed POD nor observed FAR is computable "
                      f"({hits} hit(s), {false_alarms} false alarm(s), "
                      f"{misses} candidate miss(es))")

    return {
        "event_class": event_class,
        "counts": {
            "total": total,
            "hits": hits,
            "false_alarms": false_alarms,
            "candidate_misses": misses,
        },
        "observed": {
            "pod": pod,
            "far": far,
            "median_lead_h": median_lead,
            "n_leads": len(leads),
        },
        "thresholds": {
            "pod_min": thresholds["pod"],
            "far_max": thresholds["far"],
            "median_lead_min_h": thresholds["min_lead_h"],
        },
        "checks": checks,
        "verdict": verdict,
        "detail": detail,
    }


def summarize_ledger(rows: list) -> dict:
    """{event_class: summarize_class(...)} over raw ledger rows (all classes).

    Rows with an unknown/missing event_class are counted under
    "_unclassified" (total only) rather than silently dropped.
    """
    by_class = {klass: [] for klass in EVENT_CLASSES}
    unclassified = 0
    for r in rows:
        klass = (r or {}).get("event_class")
        if klass in by_class:
            by_class[klass].append(r)
        else:
            unclassified += 1
    report = {klass: summarize_class(klass, class_rows)
              for klass, class_rows in by_class.items()}
    if unclassified:
        report["_unclassified"] = {"counts": {"total": unclassified}}
    return report


def build_summary_text(classes: dict, total: int) -> str:
    """One plain-language line per class, admin-readable at a glance."""
    lines = [f"Outcome ledger: {total} judged outcome(s) on record. "
             f"Bars: {THRESHOLDS_SOURCE}."]
    for klass in EVENT_CLASSES:
        c = classes.get(klass)
        if not c:
            continue
        counts, obs, thr = c["counts"], c["observed"], c["thresholds"]
        label = {CLASS_VERDICT_MEETING: "MEETING BAR",
                 CLASS_VERDICT_BELOW: "BELOW BAR",
                 CLASS_VERDICT_INSUFFICIENT: "INSUFFICIENT DATA",
                 }[c["verdict"]]

        def fmt(value, target, nd=2):
            shown = "n/a" if value is None else f"{value:.{nd}f}"
            return f"{shown} (bar {target})"

        lines.append(
            f"{klass}: {label} - {counts['hits']} hit(s), "
            f"{counts['false_alarms']} false alarm(s), "
            f"{counts['candidate_misses']} candidate miss(es); "
            f"observed POD {fmt(obs['pod'], '>=' + str(thr['pod_min']))}, "
            f"observed FAR {fmt(obs['far'], '<=' + str(thr['far_max']))}, "
            f"observed median lead "
            f"{fmt(obs['median_lead_h'], '>=' + str(thr['median_lead_min_h']) + ' h', 1)}.")
    unclassified = classes.get("_unclassified")
    if unclassified:
        lines.append(f"{unclassified['counts']['total']} row(s) carried an "
                     "unknown event class and were left out of the per-class "
                     "figures.")
    lines.append("Observed POD is generous (candidate misses are "
                 "disaster-grade-only and rate-limited); below-bar on this "
                 "measure is unambiguously below bar. Retuning is a "
                 "human-triggered offline run - see "
                 "research/severe_weather/retraining/RETRAINING.md.")
    return "\n".join(lines)


def build_report(rows: list) -> dict:
    """The full report payload from raw ledger rows. Pure."""
    classes = summarize_ledger(rows)
    total = len(rows)
    return {
        "admin_only": True,
        "generated_at": dt.datetime.utcnow().replace(
            microsecond=0).isoformat() + "Z",
        "total_outcomes": total,
        "thresholds_source": THRESHOLDS_SOURCE,
        "min_outcomes_for_verdict": MIN_OUTCOMES_FOR_VERDICT,
        "classes": classes,
        "summary": build_summary_text(classes, total),
    }


# --------------------------------------------------------------------------- #
# the whitelisted endpoint (frappe-side)
# --------------------------------------------------------------------------- #

def _require_system_manager():
    """Admin telemetry only: any caller without System Manager is refused."""
    roles = set(frappe.get_roles())
    if "System Manager" not in roles:
        raise frappe.PermissionError(
            "get_retraining_report is admin telemetry (System Manager only)")


def _fetch_ledger_rows() -> list:
    return frappe.get_all(
        OUTCOME_DOCTYPE,
        fields=["name", "event_class", "verdict", "evidence",
                "period_start", "period_end", "recorded_at"],
        limit_page_length=0,
    )


def _whitelist(fn):
    return frappe.whitelist()(fn) if frappe is not None else fn


@_whitelist
def get_retraining_report():
    """Observed ledger performance per event class vs the frozen bars.

    System Manager only; read-only over the Severe Weather Outcome ledger.
    Internal errors are admin-logged (rate-limited) and reported in-band as
    {"error": true, ...} - the endpoint itself never leaks a traceback.
    """
    _require_system_manager()
    try:
        return build_report(_fetch_ledger_rows())
    except Exception:
        log_admin_error(TITLE_RETRAIN_REPORT)
        return {
            "admin_only": True,
            "error": True,
            "total_outcomes": 0,
            "classes": {},
            "summary": ("report generation failed - see the Error Log "
                        f"entry titled {TITLE_RETRAIN_REPORT!r}"),
        }
