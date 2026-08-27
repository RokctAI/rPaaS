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

"""Neighbor propagation + basin-consensus pass over the active watch cells.

Runs AFTER the hourly per-cell evaluation pass (wired at the end of
evaluator.evaluate_watch_locations). Motivated by two findings on the research branch
(weather/research/severe_weather):

  * BACKTEST.md "river-routing blind spot": the per-cell detector reads local
    rain-on-saturated-soil, so downstream cells inheriting upstream water are
    warned late or not at all (Limpopo 1977: Chokwe silent until in-event
    while the upstream cell had warned 128 h earlier).
  * LIMPOPO_CASE_STUDY.md basin-consensus finding: >=5 of 6 basin cells
    firing near-simultaneously occurred ONLY in 2013, 2023 (Freddy) and 2026
    - exactly the catastrophic basin-wide floods of the modern record. A
    k-of-n consensus turns the per-cell detector into a rare-event
    wide-extent flag essentially for free.

Two bounded, cheap passes over state that is already in the database (pure
doctype reads - NO new source/S3 fetches):

1. NEIGHBOR ADVISORY - a cell X holding an active real episode (severity
   heads_up or warning) projects a soft advisory to nearby active watch
   cells that plausibly lie in the episode's path:
     - storm-driven classes (flash_flood, destructive_wind, tornado) are
       direction-aware: a target qualifies when it sits inside the downwind
       cone around the steering direction at X (the mean recent 10 m/100 m
       wind direction, stashed by the evaluator in the warning's precursors
       JSON as "steering_deg" - degrees clockwise from north, the direction
       the wind blows TOWARD). Without a stored steering direction the pass
       falls back to the conservative isotropic reduced radius.
     - flood is isotropic at a REDUCED radius: "downstream" cannot be
       resolved without elevation/basin data (the current source exposes
       none), so flood propagation is deliberately conservative. Basin
       topology / elevation-aware routing is the documented future
       refinement (BACKTEST.md next-lever 1).
   Advisories use the new severity enum value "advisory", strictly BELOW
   heads_up in prominence (see SEVERITY_ORDER). They never overwrite a real
   record, never outlive their source episode's validity, and are expired
   the moment the target cell earns a real same-class episode of its own.

   COLD FRONTS (sw2.1, cold_front.py): a first-hand cold-front DETECTION
   record (event_class "cold_front", precursors mode "cold_front_detection")
   also seeds this pass, even though its severity is only "advisory" -
   projecting the calm "cooler, windier weather ... may reach you {timing}"
   line to cells in the downwind steering cone, with the timing word derived
   from the stored steering speed x distance (front_timing_phrase; "soon"
   when no speed is stored). Projected advisories never re-seed (the mode
   discriminator stops chain propagation), and the class is EXCLUDED from
   basin consensus - routine weather is never escalated.

2. BASIN CONSENSUS - when >= K distinct cells within the basin radius hold
   active same-class real episodes simultaneously, each member episode is
   escalated: its stored confidence is boosted, the wide extent is recorded
   in admin telemetry, and - bounded - a heads_up member may be raised to
   the warning severity tier. Consensus NEVER invents an episode, never
   raises past the per-class severity cap (tornado stays heads_up), never
   touches advisory records, and never downgrades anything.

Safety properties (mirroring evaluator.py):
  - config-flagged: disabled unless weather_propagation_enabled is set;
  - idempotent: re-running the pass on unchanged state plans zero actions
    (plan_propagation on an applied state returns an empty plan);
  - cheap: two frappe.get_all reads + O(active_cells^2) pure arithmetic;
  - per-cell error isolation: each planned action is applied in its own
    try/except; one bad record cannot starve the rest.

The planning core (plan_propagation / apply_plan) is pure - no frappe, no
I/O - so it is unit-testable offline and replayable over historical episode
lists (the Jan-2013 Limpopo replay in the PR notes uses exactly this).

Copy rules: everything user-visible here is calm heads-up phrasing; no
user-facing string ever contains the word "warning" (the ZA legal
constraint carried over from messages.py).
"""
from __future__ import annotations

import datetime as dt
import json
import math
from dataclasses import dataclass, field

import frappe
from frappe.utils import cint, flt

from ...warnings_engine import messages
from ...warnings_engine.admin_log import log_admin_error

WATCH_DOCTYPE = "Weather Watch Location"
WARNING_DOCTYPE = "Severe Weather Warning"

#: stable admin Error Log titles (grep keys, rate-limited by admin_log)
TITLE_PROPAGATION = "SevereWeather: propagation failed"
TITLE_CONSENSUS = "SevereWeather: basin consensus"

#: the new severity enum value - strictly below heads_up in prominence.
#: Clients that do not know it must fail closed (render nothing); the dart
#: banner currently knows only heads_up|warning, so advisories surface there
#: only once the dart side learns the value (documented follow-up).
SEVERITY_ADVISORY = "advisory"

#: prominence order, least to most prominent. Clients may use this to sort;
#: the propagation passes use it to guarantee they never downgrade.
SEVERITY_ORDER = (SEVERITY_ADVISORY, "heads_up", "warning")

#: real (evaluator-issued) severities - the only ones that seed advisories
#: for the SEVERE classes or count toward consensus.
REAL_SEVERITIES = frozenset(("heads_up", "warning"))

#: the informational cold-front class (cold_front.py). Its DETECTION records
#: (precursors mode FRONT_DETECTION_MODE) also seed neighbor advisories -
#: the "cell X felt the front, warn the downwind cells" feature - even
#: though their severity is only "advisory". They are excluded from basin
#: consensus (routine weather is never escalated) and, like every advisory,
#: never seed from a record that is itself a projected advisory (mode
#: "neighbor_advisory"), so fronts cannot chain-propagate.
FRONT_CLASS = "cold_front"
FRONT_DETECTION_MODE = "cold_front_detection"

#: classes whose hazard travels with the steering flow: direction-aware
#: propagation along the steering wind at the source cell. Cold fronts
#: advect with the flow like storms do.
DIRECTIONAL_CLASSES = frozenset(
    ("flash_flood", "destructive_wind", "tornado", FRONT_CLASS))

#: configuration defaults; every key is overridable via site config
#: (frappe.conf) under "weather_propagation_<key>".
DEFAULTS = {
    "enabled": 0,                     # master flag - the pass is off until set
    "neighbor_radius_km": 150.0,      # advisory reach for directional classes
    "flood_radius_factor": 0.6,       # flood / no-steering fallback: reduced
                                      # isotropic reach (0.6 * 150 = 90 km)
    "direction_half_angle_deg": 60.0, # downwind cone half-angle
    "basin_radius_km": 300.0,         # consensus neighborhood
    "consensus_k": 4,                 # >= K distinct cells => consensus
}

#: confidence boost per consensus member beyond the threshold K (bounded at
#: 1.0); recorded in precursors as "consensus_confidence" - admin telemetry,
#: never shown to users.
CONSENSUS_CONFIDENCE_STEP = 0.05

# --------------------------------------------------------------------------- #
# advisory copy - calm, below heads_up in tone; NEVER the word "warning"
# --------------------------------------------------------------------------- #

ADVISORY_LABEL = "Worth knowing"

ADVISORY_HEADLINES = {
    "flash_flood": "Heavy downpours in the wider area around {place}",
    "flood": "Very wet conditions in the wider area around {place}",
    "destructive_wind": "Strong winds in the wider area around {place}",
    "tornado": "Storms in the wider area around {place}",
    "cold_front": "A cool change on its way to {place}",
}

ADVISORY_MESSAGES = {
    "flash_flood": (
        "Sudden heavy rain is affecting areas near {place} and may reach "
        "your area later today. Worth keeping an eye on the sky and on "
        "low-lying roads."
    ),
    "flood": (
        "Rivers and low ground in areas near {place} are getting very wet. "
        "Water levels around you could rise over the coming days, even "
        "without heavy rain where you are."
    ),
    "destructive_wind": (
        "Very strong winds are affecting areas near {place} and may reach "
        "your area later today. Worth tying down anything loose outside."
    ),
    "tornado": (
        "Storms affecting areas nearby may reach your area later today. "
        "Keep an ear on local alerts."
    ),
    "cold_front": (
        "Cooler, windier weather is moving through nearby areas and may "
        "reach you {when}. Expect a temperature drop and gusty conditions "
        "when it arrives."
    ),
}

#: cold-front projected-advisory variant mirroring the source cell's
#: unusual-for-here detection (see cold_front.is_unusual); the rain sentence
#: (messages.COLD_FRONT_RAIN_SENTENCE) is appended only when the source
#: cell's observed post-frontal rain signal supports it.
ADVISORY_MESSAGE_FRONT_UNUSUAL = (
    "Noticeably colder weather is moving through nearby areas - unusual "
    "for this time of year - and may reach you {when}."
)

#: timing words for the cold-front advisory, chosen from the front's cheap
#: ETA estimate (steering speed x distance); the fallback when no speed is
#: stored is deliberately vague.
FRONT_TIMING_FALLBACK = "soon"
FRONT_TIMING_BUCKETS = (
    (6.0, "in the next few hours"),
    (18.0, "later today"),
    (36.0, "tomorrow"),
)
FRONT_TIMING_BEYOND = "in the coming days"

#: an ETA estimate needs at least this much steering flow to be credible.
FRONT_MIN_SPEED_MS = 1.0


def front_timing_phrase(distance_km, speed_ms) -> str:
    """Timing word for a projected cold-front advisory.

    speed_ms is the source cell's stored mean steering speed
    ("steering_speed_ms" in the detection record's precursors). Falls back
    to FRONT_TIMING_FALLBACK when the speed is missing/implausible.
    """
    try:
        speed = float(speed_ms)
        distance = float(distance_km)
    except (TypeError, ValueError):
        return FRONT_TIMING_FALLBACK
    if not (speed >= FRONT_MIN_SPEED_MS and distance >= 0):
        return FRONT_TIMING_FALLBACK
    eta_h = distance / (speed * 3.6)
    for bound, phrase in FRONT_TIMING_BUCKETS:
        if eta_h <= bound:
            return phrase
    return FRONT_TIMING_BEYOND

#: appended (once) to an escalated episode's message - the wide-extent line.
WIDE_AREA_NOTES = {
    "flash_flood": "Heavy rain is affecting a wide area around you.",
    "flood": "Heavy rain is affecting a wide area around you.",
    "destructive_wind": "Strong winds are affecting a wide area around you.",
    "tornado": "Stormy weather is affecting a wide area around you.",
}


# --------------------------------------------------------------------------- #
# geometry (pure)
# --------------------------------------------------------------------------- #

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance between two points, km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = p2 - p1
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2.0) ** 2)
    return 2.0 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1.0, a)))


def bearing_deg(lat1, lon1, lat2, lon2) -> float:
    """Initial great-circle bearing from point 1 to point 2.

    Degrees clockwise from true north, in [0, 360).
    """
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def steering_deg_from_uv(u, v) -> float:
    """Direction the wind blows TOWARD from u (east) / v (north) components.

    Degrees clockwise from true north, in [0, 360) - directly comparable to
    bearing_deg(). This is the convention the evaluator wiring stashes into
    the warning's precursors JSON as "steering_deg".
    """
    return (math.degrees(math.atan2(u, v)) + 360.0) % 360.0


def angular_diff_deg(a, b) -> float:
    """Smallest absolute angle between two bearings, degrees in [0, 180]."""
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #

def load_config() -> dict:
    """Merge site-config overrides (weather_propagation_*) over DEFAULTS."""
    cfg = dict(DEFAULTS)
    conf = getattr(frappe, "conf", None) or {}
    for key, default in DEFAULTS.items():
        raw = conf.get("weather_propagation_" + key)
        if raw is None:
            continue
        if key in ("enabled", "consensus_k"):
            cfg[key] = cint(raw)
        else:
            cfg[key] = flt(raw)
    return cfg


# --------------------------------------------------------------------------- #
# planning core (pure - no frappe, no I/O)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class PlannedAdvisory:
    """Issue (or refresh) one advisory record at a target cell."""
    target: str                 # target watch-location name
    event_class: str
    source: str                 # source watch-location name
    source_warning: str         # source warning record name
    distance_km: float
    bearing_deg: float          # source -> target
    steering_deg: object        # float, or None when isotropic fallback
    gating: str                 # "directional" | "isotropic"
    onset: object               # source episode onset (informative)
    valid_until: object         # never outlives the source record
    headline: str
    message: str
    precursors: str             # JSON, admin detail
    existing_name: object = None  # set => refresh this advisory in place


@dataclass(frozen=True)
class PlannedEscalation:
    """Escalate one existing real episode on basin consensus."""
    name: str                   # warning record name (existing - never new)
    watch_location: str
    event_class: str
    count: int                  # distinct cells in consensus (incl. itself)
    members: tuple              # sorted watch-location names
    new_severity: object        # "warning" to raise heads_up, else None
    headline: object            # new headline, or None to keep
    message: object             # new message, or None to keep
    precursors: str             # JSON with basin_consensus telemetry


@dataclass(frozen=True)
class PlannedExpiry:
    """Expire one advisory that a real same-class episode has outranked."""
    name: str
    reason: str


@dataclass
class PropagationPlan:
    advisories: list = field(default_factory=list)
    escalations: list = field(default_factory=list)
    expiries: list = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.advisories or self.escalations or self.expiries)


def _parse_precursors(warning) -> dict:
    raw = warning.get("precursors")
    if isinstance(raw, dict):
        return dict(raw)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {}


def _is_front_detection(warning) -> bool:
    """True for a first-hand cold-front DETECTION record (cold_front.py).

    Detection records carry precursors mode FRONT_DETECTION_MODE; projected
    cold-front advisories carry mode "neighbor_advisory" and must never
    re-seed (no chain propagation)."""
    w = dict(warning)
    return (w.get("event_class") == FRONT_CLASS
            and _parse_precursors(w).get("mode") == FRONT_DETECTION_MODE)


def _steering_deg(warning) -> object:
    """The stored steering direction at the source cell, or None.

    The evaluator (_steering_deg in evaluator.py) computes it from the wind
    series it already fetched - the propagation pass itself never fetches.
    """
    val = _parse_precursors(warning).get("steering_deg")
    try:
        return float(val) % 360.0 if val is not None else None
    except (TypeError, ValueError):
        return None


def _iso(value) -> object:
    return value.isoformat() if isinstance(value, dt.datetime) else value


def _sort_key(warning):
    onset = warning.get("onset")
    key = onset.isoformat() if isinstance(onset, dt.datetime) else str(onset or "")
    return (key, str(warning.get("name") or ""))


def render_advisory(event_class: str, place, when: str | None = None) -> dict:
    """Calm advisory copy for one class; same contract as messages.render.

    when: timing word for the cold_front message ({when} placeholder);
    ignored by classes whose copy has no timing slot.
    """
    place = (place or "").strip() or messages.DEFAULT_PLACE
    when = when or FRONT_TIMING_FALLBACK
    return {
        "severity": SEVERITY_ADVISORY,
        "severity_label": ADVISORY_LABEL,
        "headline": ADVISORY_HEADLINES[event_class].format(place=place, when=when),
        "message": ADVISORY_MESSAGES[event_class].format(place=place, when=when),
    }


def plan_propagation(locations, warnings, cfg=None) -> PropagationPlan:
    """Pure planning pass: (active cells, active warnings, config) -> plan.

    locations: iterable of dicts with name, latitude, longitude, label.
    warnings:  iterable of dicts with name, watch_location, event_class,
               severity, status, onset, valid_until, message, precursors.
    Only status == "active" rows participate. Deterministic and idempotent:
    planning again on the applied state returns an empty plan.
    """
    cfg = {**DEFAULTS, **(cfg or {})}
    radius = float(cfg["neighbor_radius_km"])
    reduced_radius = radius * float(cfg["flood_radius_factor"])
    half_angle = float(cfg["direction_half_angle_deg"])
    basin_radius = float(cfg["basin_radius_km"])
    consensus_k = int(cfg["consensus_k"])

    locs = {}
    for loc in locations:
        d = dict(loc)
        if d.get("name") and d.get("latitude") is not None \
                and d.get("longitude") is not None:
            locs[d["name"]] = d

    active = [dict(w) for w in warnings if dict(w).get("status") == "active"]
    # Fail-closed class gate: only classes this pass has advisory copy for
    # may seed advisories or count toward consensus. Classes outside the
    # table (e.g. the basin-routed upstream_flood, which is itself a derived
    # signal - see basin.py) are silently ignored rather than crashing the
    # pass or chain-propagating.
    real = sorted(
        (w for w in active
         if w.get("severity") in REAL_SEVERITIES
         and w.get("event_class") in ADVISORY_HEADLINES
         and w.get("watch_location") in locs),
        key=_sort_key)
    # cold-front DETECTION records seed advisories too (severity is advisory
    # by design, but the mode discriminator marks them as first-hand
    # observations, not projections - projections never re-seed).
    fronts = sorted(
        (w for w in active
         if _is_front_detection(w) and w.get("watch_location") in locs),
        key=_sort_key)
    seeds = sorted(real + fronts, key=_sort_key)
    advisories_db = [w for w in active
                     if w.get("severity") == SEVERITY_ADVISORY
                     and not _is_front_detection(w)]

    plan = PropagationPlan()

    # -- outranking: a first-hand same-class episode (real severity, or a
    # cell's own cold-front detection) expires the cell's projected advisory --
    real_pairs = {(w["watch_location"], w["event_class"]) for w in seeds}
    outranked = set()
    for adv in advisories_db:
        pair = (adv.get("watch_location"), adv.get("event_class"))
        if pair in real_pairs:
            plan.expiries.append(PlannedExpiry(
                name=adv["name"], reason="outranked by real episode"))
            outranked.add(adv.get("name"))

    # -- pass 1: neighbor advisories ---------------------------------------- #
    adv_by_pair = {
        (a.get("watch_location"), a.get("event_class")): a
        for a in advisories_db if a.get("name") not in outranked}
    covered = set(real_pairs) | set(adv_by_pair)
    planned_pairs = set()

    for w in seeds:
        src = locs[w["watch_location"]]
        event_class = w["event_class"]
        steering = _steering_deg(w)
        directional = event_class in DIRECTIONAL_CLASSES and steering is not None
        reach = radius if directional else reduced_radius
        for target in locs.values():
            if target["name"] == src["name"]:
                continue
            pair = (target["name"], event_class)
            if pair in planned_pairs:
                continue  # first (earliest-onset) source wins
            existing = adv_by_pair.get(pair)
            if pair in covered and existing is None:
                continue  # a real record holds this pair
            dist = haversine_km(src["latitude"], src["longitude"],
                                target["latitude"], target["longitude"])
            if dist > reach:
                continue
            brg = bearing_deg(src["latitude"], src["longitude"],
                              target["latitude"], target["longitude"])
            if directional and angular_diff_deg(brg, steering) > half_angle:
                continue
            if existing is not None:
                # refresh only when the source's validity has advanced
                cur = existing.get("valid_until")
                new = w.get("valid_until")
                if not (cur is not None and new is not None and new > cur):
                    continue
            when = None
            src_pre = _parse_precursors(w)
            if event_class == FRONT_CLASS:
                when = front_timing_phrase(
                    dist, src_pre.get("steering_speed_ms"))
            rendered = render_advisory(event_class, target.get("label"), when)
            if event_class == FRONT_CLASS:
                # mirror the source cell's copy scaling: unusual-for-here
                # variant, and the rain mention only when its observed
                # post-frontal rain signal supports it
                if src_pre.get("unusual"):
                    rendered["message"] = \
                        ADVISORY_MESSAGE_FRONT_UNUSUAL.format(when=when)
                if src_pre.get("rain_signal"):
                    rendered["message"] += \
                        " " + messages.COLD_FRONT_RAIN_SENTENCE
            precursor_data = {
                "mode": "neighbor_advisory",
                "propagated_from": src["name"],
                "source_warning": w.get("name"),
                "distance_km": round(dist, 1),
                "bearing_deg": round(brg, 1),
                "steering_deg": round(steering, 1) if directional else None,
                "gating": "directional" if directional else "isotropic",
                "source_onset": _iso(w.get("onset")),
            }
            if when is not None:
                precursor_data["timing_phrase"] = when
                precursor_data["unusual"] = bool(src_pre.get("unusual"))
                precursor_data["rain_signal"] = bool(src_pre.get("rain_signal"))
            precursors = json.dumps(precursor_data)
            plan.advisories.append(PlannedAdvisory(
                target=target["name"], event_class=event_class,
                source=src["name"], source_warning=str(w.get("name")),
                distance_km=round(dist, 1), bearing_deg=round(brg, 1),
                steering_deg=round(steering, 1) if directional else None,
                gating="directional" if directional else "isotropic",
                onset=w.get("onset"), valid_until=w.get("valid_until"),
                headline=rendered["headline"], message=rendered["message"],
                precursors=precursors,
                existing_name=existing.get("name") if existing else None,
            ))
            planned_pairs.add(pair)

    # -- pass 2: basin consensus -------------------------------------------- #
    for w in real:
        src = locs[w["watch_location"]]
        members = set()
        for o in real:
            if o["event_class"] != w["event_class"]:
                continue
            other = locs[o["watch_location"]]
            if haversine_km(src["latitude"], src["longitude"],
                            other["latitude"], other["longitude"]) <= basin_radius:
                members.add(o["watch_location"])
        count = len(members)
        if count < consensus_k:
            continue
        prior = _parse_precursors(w).get("basin_consensus") or {}
        if prior.get("count") == count:
            continue  # already recorded at this extent - idempotent
        # bounded escalation: heads_up -> warning only, respecting the
        # per-class cap (tornado stays heads_up); never downgrade, never
        # invent - only existing real records are touched.
        new_severity = None
        if w.get("severity") == "heads_up" \
                and messages.cap_severity(w["event_class"], "warning") == "warning":
            new_severity = "warning"
        note = WIDE_AREA_NOTES[w["event_class"]]
        headline = None
        message = None
        loc_label = src.get("label")
        if new_severity:
            rendered = messages.render(w["event_class"], new_severity, loc_label)
            headline = rendered["headline"]
            message = rendered["message"] + " " + note
        elif note not in str(w.get("message") or ""):
            message = (str(w.get("message") or "").rstrip() + " " + note).strip()
        precursors = _parse_precursors(w)
        base_conf = precursors.get("confidence")
        boosted = None
        try:
            boosted = min(1.0, float(base_conf)
                          + CONSENSUS_CONFIDENCE_STEP * (count - consensus_k + 1))
        except (TypeError, ValueError):
            pass
        precursors["basin_consensus"] = {
            "count": count,
            "k": consensus_k,
            "radius_km": basin_radius,
            "members": sorted(members),
            "severity_raised": bool(new_severity),
        }
        if boosted is not None:
            precursors["consensus_confidence"] = round(boosted, 3)
        plan.escalations.append(PlannedEscalation(
            name=str(w["name"]), watch_location=w["watch_location"],
            event_class=w["event_class"], count=count,
            members=tuple(sorted(members)), new_severity=new_severity,
            headline=headline, message=message,
            precursors=json.dumps(precursors)))

    return plan


def apply_plan(warnings, plan: PropagationPlan, now=None) -> list:
    """Pure state-transition mirror of the DB apply - for tests and offline
    replays. Returns a NEW list of warning dicts with the plan applied."""
    out = [dict(w) for w in warnings]
    by_name = {w.get("name"): w for w in out}
    for exp in plan.expiries:
        if exp.name in by_name:
            by_name[exp.name]["status"] = "expired"
    for esc in plan.escalations:
        w = by_name.get(esc.name)
        if w is None:
            continue
        if esc.new_severity:
            w["severity"] = esc.new_severity
        if esc.headline is not None:
            w["headline"] = esc.headline
        if esc.message is not None:
            w["message"] = esc.message
        w["precursors"] = esc.precursors
    for adv in plan.advisories:
        if adv.existing_name and adv.existing_name in by_name:
            row = by_name[adv.existing_name]
            row["valid_until"] = adv.valid_until
            row["precursors"] = adv.precursors
            continue
        row = {
            "name": "ADV-{0}-{1}".format(adv.target, adv.event_class),
            "watch_location": adv.target,
            "event_class": adv.event_class,
            "severity": SEVERITY_ADVISORY,
            "status": "active",
            "headline": adv.headline,
            "message": adv.message,
            "onset": adv.onset,
            "valid_until": adv.valid_until,
            "issued_at": now,
            "precursors": adv.precursors,
        }
        out.append(row)
        by_name[row["name"]] = row
    return out


# --------------------------------------------------------------------------- #
# scheduled entry point (frappe apply, per-record error isolation)
# --------------------------------------------------------------------------- #

def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


def run_propagation_pass(now=None):
    """Run both passes over the active cells. Called by the evaluator after
    the per-cell loop (evaluator.evaluate_watch_locations); safe to call any
    time - idempotent, and a no-op unless weather_propagation_enabled is set."""
    cfg = load_config()
    if not cfg.get("enabled"):
        return
    now = now or _utcnow()
    try:
        locations = frappe.get_all(
            WATCH_DOCTYPE,
            filters={"active": 1},
            fields=["name", "latitude", "longitude", "label"],
        )
        warnings = frappe.get_all(
            WARNING_DOCTYPE,
            # drill fence: replay records (warnings_engine/drill.py) must
            # never seed real neighbor advisories or consensus escalations
            filters={"status": "active", "is_drill": ["!=", 1]},
            fields=["name", "watch_location", "event_class", "severity",
                    "status", "onset", "valid_until", "headline", "message",
                    "precursors"],
        )
        plan = plan_propagation(locations, warnings, cfg)
    except Exception:
        log_admin_error(TITLE_PROPAGATION)
        return

    for exp in plan.expiries:
        try:
            frappe.db.set_value(WARNING_DOCTYPE, exp.name, {"status": "expired"})
        except Exception:
            log_admin_error(TITLE_PROPAGATION)
    for adv in plan.advisories:
        try:
            _apply_advisory(adv, now)
        except Exception:
            log_admin_error(TITLE_PROPAGATION)
    for esc in plan.escalations:
        try:
            _apply_escalation(esc)
        except Exception:
            log_admin_error(TITLE_PROPAGATION)
    if plan.escalations:
        # admin telemetry: the wide-extent flag is the rare-event signal the
        # Limpopo study identified - make it visible under a stable title.
        summary = "; ".join(
            "{0}/{1}: {2} cells in consensus ({3})".format(
                esc.watch_location, esc.event_class, esc.count,
                ", ".join(esc.members))
            for esc in plan.escalations)
        log_admin_error(TITLE_CONSENSUS, summary)


def _apply_advisory(adv: PlannedAdvisory, now):
    if adv.existing_name:
        frappe.db.set_value(WARNING_DOCTYPE, adv.existing_name, {
            "valid_until": adv.valid_until,
            "precursors": adv.precursors,
        })
        return
    # race guard: another action this pass may have created the pair
    existing = frappe.db.get_value(
        WARNING_DOCTYPE,
        {"watch_location": adv.target, "event_class": adv.event_class,
         "status": "active", "is_drill": ["!=", 1]},
        "name",
    )
    if existing:
        return
    frappe.get_doc({
        "doctype": WARNING_DOCTYPE,
        "watch_location": adv.target,
        "event_class": adv.event_class,
        "severity": SEVERITY_ADVISORY,
        "headline": adv.headline,
        "message": adv.message,
        "onset": adv.onset,
        "valid_until": adv.valid_until,
        "issued_at": now,
        "status": "active",
        "precursors": adv.precursors,
    }).insert(ignore_permissions=True)


def _apply_escalation(esc: PlannedEscalation):
    fields = {"precursors": esc.precursors}
    if esc.new_severity:
        fields["severity"] = esc.new_severity
    if esc.headline is not None:
        fields["headline"] = esc.headline
    if esc.message is not None:
        fields["message"] = esc.message
    frappe.db.set_value(WARNING_DOCTYPE, esc.name, fields)
