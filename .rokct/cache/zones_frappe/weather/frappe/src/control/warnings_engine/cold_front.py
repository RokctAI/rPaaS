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

"""Cold-front passage detection - the informational "cool change" advisory.

A cold front is ROUTINE weather, not a hazard: this module exists so the
area-X -> area-Y neighbor mechanics (propagation.py) can tell a downstream
cell "cooler, windier weather is on its way" a few hours ahead. Everything
here is therefore hard-capped at the ADVISORY tier (strictly below heads_up
in prominence, muted by default in clients that do not render the enum
value) and is fully additive:

  - it never touches the frozen detector, its config, or its four severe
    event classes (the sha256 provenance guard in detector.py is unchanged);
  - it never produces a heads_up or warning severity: records are written
    with severity "advisory" and messages.CLASS_MAX_SEVERITY caps the
    cold_front class at "advisory" so no shared severity path can ever
    raise one;
  - it is never push-notified: push.py ranks severities via
    messages.SEVERITY_WORDS (heads_up|warning), so "advisory" ranks 0 and
    is refused before any other gate - and this module never calls push;
  - fusion (fusion.py) and seasonal climatology (climatology.py) ignore the
    class: it is absent from their RAIN_CLASSES/WIND_CLASSES and this
    module never calls their hooks.

DETECTION (pure, causal - detect_passages below): a frontal passage at hour
t is declared only from values at hours <= t, when ALL four classic surface
signatures coincide (thresholds/windows are the DEFAULTS constants block,
calibrated on a documented real front - see the note there):

  1. temperature drop:  2 m temperature at t sits >= temp_drop_c below the
     maximum of the preceding temp_drop_window_h hours;
  2. wind shift:        the vector-mean 10 m wind direction over the last
     shift_mean_h hours differs by >= shift_min_deg from the direction
     shift_window_h hours earlier (both windows must carry >= shift_min_speed_ms
     mean speed - direction is meaningless in near-calm);
  3. trough passage:    MSLP reached a local minimum inside the last
     trough_window_h hours, having FALLEN >= trough_fall_hpa into it and
     RISEN >= trough_rise_hpa since it (the classic fall-then-rise);
  4. gust bump:         the max 10 m gust of the last gust_recent_h hours
     exceeds the pre-frontal mean gust by >= gust_bump_ms.

Consecutive qualifying hours (and re-qualifications within merge_gap_h) are
coalesced into ONE passage event whose time is the first qualifying hour.

COPY SCALING (render_detection below): a front's notability is about REACH,
not severity - a passage that is out of the ordinary FOR THIS CELL (e.g. a
front penetrating deep into hot northern areas) gets the "unusual" copy
variant. The gate (is_unusual) is data-driven and config-tunable: the
absolute unusual_temp_drop_c threshold, OR the drop exceeding
unusual_drop_sigma x the cell's own causal pre-frontal temperature spread.
(The durable Weather Cell Climatology store holds precip/TCWV weekly
normals only - no temperature normals - so the adaptive gate uses the
fetched window's spread; stored temperature normals are the documented
follow-up.) The "Some rain may follow." sentence is appended ONLY when the
observed post-frontal precipitation at the cell reaches rain_signal_mm -
never speculatively. Both facets stay at the advisory tier and are mirrored
onto projected neighbor advisories by propagation.py.

EVALUATOR WIRING (evaluate_cell below, called per cell from
evaluator._evaluate_location on the SAME already-fetched hourly series - no
extra source reads): a passage within recent_h of the data horizon upserts
one Severe Weather Warning record (event_class "cold_front", severity
"advisory"). Noise control: a per-cell cooldown (cooldown_h, default 72)
suppresses re-issue - one advisory per front, not one per evaluation - and
the master site-config flag gates the whole pass.

PROPAGATION: the record's precursors carry mode "cold_front_detection" plus
the steering direction/speed; propagation.py picks it up as a seed and
projects a calm "may reach you {timing}" advisory to cells inside the
downwind steering cone (see propagation.FRONT_CLASS handling).

Site-config keys (frappe.conf, per tenant site):
  severe_weather_cold_front       MASTER FLAG; default ON
                                  ("0"/"false"/"no"/"off" disables)
  severe_weather_cold_front_<key> per-threshold override for every key in
                                  DEFAULTS below (e.g.
                                  severe_weather_cold_front_cooldown_h)

Admin telemetry: each fresh detection logs one rate-limited line under the
stable Error Log title TITLE_DETECTED. All datetimes are UTC (naive).
"""
from __future__ import annotations

import datetime as dt
import json
import math
from dataclasses import dataclass

import frappe
from frappe.utils import flt

from ...warnings_engine import messages
from ...warnings_engine.admin_log import log_admin_error
# single source of truth for the class name and the precursors-mode
# discriminator lives with the pass that consumes them (propagation.py)
from .propagation import FRONT_CLASS, FRONT_DETECTION_MODE

WARNING_DOCTYPE = "Severe Weather Warning"

#: precursors "mode" discriminator: a detection record (a propagation seed),
#: as opposed to the "neighbor_advisory" mode of a projected advisory.
MODE_DETECTION = FRONT_DETECTION_MODE

#: the ONLY severity this module ever writes - the hard cap.
SEVERITY_ADVISORY = "advisory"

#: stable admin Error Log titles (rate-limited by admin_log)
TITLE_DETECTED = "SevereWeather: cold front detected"
TITLE_COLD_FRONT = "SevereWeather: cold front pass failed"

#: master site-config flag; missing/None = ON, "0"/"false"/"no"/"off" = OFF.
SITE_CONFIG_FLAG = "severe_weather_cold_front"

#: detection thresholds + lifecycle knobs - the complete tunable surface.
#: Every key is overridable via site config as
#: "severe_weather_cold_front_<key>" (numbers; windows/hours are ints).
#:
#: CALIBRATION: the textbook station signature (~6 degC drop and ~45 deg
#: veer inside ~6 h) is too sharp for 0.25-degree ERA5 cell means, where
#: frontal gradients smear over 12-24 h - especially at maritime cells. The
#: defaults below were calibrated by replaying the documented 6-7 Jun 2017
#: "Cape storm" front (SAWS orange level 8) over ERA5: they detect the
#: passage at the Cape Town coastal cell (07 Jun 03Z), Swellendam (04Z) and
#: Beaufort West far inland (08Z) - the real west-to-east passage order -
#: and also the documented weaker front of 3 Jun 2017, while the
#: trough-rise + gust-bump conjunction keeps ordinary diurnal cooling out.
DEFAULTS = {
    "temp_drop_c": 5.0,        # 2 m temperature fall vs the pre-front max ...
    "temp_drop_window_h": 12,  # ... within this many hours
    "shift_min_deg": 30.0,     # wind-direction shift (veer/back) ...
    "shift_window_h": 12,      # ... vs the direction this many hours earlier
    "shift_mean_h": 3,         # vector-mean window on each side of the shift
    "shift_min_speed_ms": 1.0, # both windows need this mean speed
    "trough_window_h": 24,     # MSLP fall-then-rise lookback
    "trough_fall_hpa": 3.0,    # min fall into the trough
    "trough_rise_hpa": 1.0,    # min rise since the trough
    "gust_bump_ms": 5.0,       # recent max gust vs pre-frontal mean gust
    "gust_recent_h": 3,        # "recent" window for the gust max
    "merge_gap_h": 6,          # re-qualification within this gap = same front
    "recent_h": 24,            # passage older than this vs horizon = stale
                               # (covers the ERA5 archive's daily advance)
    "cooldown_h": 72,          # per-cell re-issue suppression (noise control)
    "validity_h": 24,          # advisory lifetime past the data horizon
    # -- copy scaling: how unusual is this passage FOR THIS CELL? ---------- #
    "unusual_temp_drop_c": 9.0,   # absolute gate: a drop this big is always
                                  # copy-worthy ("unusual" variant)
    "unusual_drop_sigma": 3.0,    # adaptive gate: drop >= sigma x the cell's
                                  # own pre-frontal hourly-temperature spread
                                  # (0 disables the adaptive gate)
    # -- rain mention: only when the data supports it ---------------------- #
    "rain_signal_mm": 1.0,        # min post-frontal precip (mm since the
                                  # passage hour) before copy may say
                                  # "Some rain may follow."
}

#: series variables the detector reads (all already fetched by the evaluator
#: as part of features.POINT_VARIABLES - this module adds NO source reads).
SERIES_VARIABLES = ("temperature_2m", "pressure_msl", "wind_gusts_10m",
                    "wind_u_component_10m", "wind_v_component_10m")


def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow().replace(microsecond=0)


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #

def cold_front_enabled() -> bool:
    """Master site-config flag, default ON."""
    try:
        value = frappe.conf.get(SITE_CONFIG_FLAG)
    except Exception:
        return True
    if value is None:
        return True
    return str(value).strip().lower() not in ("0", "false", "no", "off", "")


def load_config() -> dict:
    """Merge site-config overrides (severe_weather_cold_front_*) over DEFAULTS."""
    cfg = dict(DEFAULTS)
    conf = getattr(frappe, "conf", None) or {}
    for key, default in DEFAULTS.items():
        raw = conf.get("severe_weather_cold_front_" + key)
        if raw is None:
            continue
        value = flt(raw)
        cfg[key] = int(value) if isinstance(default, int) else value
    return cfg


# --------------------------------------------------------------------------- #
# detection core (pure - no frappe, no I/O; unit-testable offline and
# replayable over historical ERA5 series)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class FrontPassage:
    """One detected frontal passage (coalesced run of qualifying hours)."""
    index: int                  # index of the first qualifying hour
    time: object                # times[index]
    temp_drop_c: float
    shift_deg: float
    trough_fall_hpa: float
    trough_rise_hpa: float
    gust_bump_ms: float


def _finite(values) -> list:
    return [v for v in values
            if v is not None and not (isinstance(v, float) and math.isnan(v))]


def _val(seq, i):
    v = seq[i]
    if v is None:
        return None
    v = float(v)
    return None if math.isnan(v) else v


def _mean_wind_dir(u, v, lo, hi, min_speed) -> object:
    """Vector-mean 10 m wind direction (deg, blowing toward) over [lo, hi),
    or None when data is missing or the mean flow is weaker than min_speed."""
    pairs = [(_val(u, i), _val(v, i)) for i in range(lo, hi)]
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    if not pairs:
        return None
    mu = sum(a for a, _ in pairs) / len(pairs)
    mv = sum(b for _, b in pairs) / len(pairs)
    if math.hypot(mu, mv) < min_speed:
        return None
    return (math.degrees(math.atan2(mu, mv)) + 360.0) % 360.0


def _angular_diff(a, b) -> float:
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


def _signature_at(i, temp, mslp_hpa, gust, u, v, cfg) -> object:
    """Diagnostics dict when ALL four frontal signatures hold at hour i
    (causal: values at hours <= i only), else None."""
    # 1. temperature drop
    t_now = _val(temp, i)
    if t_now is None:
        return None
    window = _finite(_val(temp, j)
                     for j in range(i - int(cfg["temp_drop_window_h"]), i))
    if not window:
        return None
    drop = max(window) - t_now
    if drop < float(cfg["temp_drop_c"]):
        return None

    # 2. wind-direction shift
    mean_h = int(cfg["shift_mean_h"])
    back = i - int(cfg["shift_window_h"])
    dir_now = _mean_wind_dir(u, v, i - mean_h + 1, i + 1,
                             float(cfg["shift_min_speed_ms"]))
    dir_before = _mean_wind_dir(u, v, back - mean_h + 1, back + 1,
                                float(cfg["shift_min_speed_ms"]))
    if dir_now is None or dir_before is None:
        return None
    shift = _angular_diff(dir_now, dir_before)
    if shift < float(cfg["shift_min_deg"]):
        return None

    # 3. MSLP trough passage (fall then rise inside the lookback)
    lo = i - int(cfg["trough_window_h"])
    p = [(j, _val(mslp_hpa, j)) for j in range(lo, i + 1)]
    p = [(j, val) for j, val in p if val is not None]
    if len(p) < 3:
        return None
    j_min, p_min = min(p, key=lambda jp: jp[1])
    if j_min == p[0][0] or j_min == p[-1][0]:
        return None  # minimum at the window edge: no passage inside it
    fall = max(val for j, val in p if j <= j_min) - p_min
    rise = p[-1][1] - p_min
    if fall < float(cfg["trough_fall_hpa"]) or rise < float(cfg["trough_rise_hpa"]):
        return None

    # 4. gust bump vs the pre-frontal baseline
    recent_h = int(cfg["gust_recent_h"])
    recent = _finite(_val(gust, j) for j in range(i - recent_h + 1, i + 1))
    baseline = _finite(_val(gust, j) for j in range(lo, back + 1))
    if not recent or not baseline:
        return None
    bump = max(recent) - sum(baseline) / len(baseline)
    if bump < float(cfg["gust_bump_ms"]):
        return None

    return {"temp_drop_c": round(drop, 2), "shift_deg": round(shift, 1),
            "trough_fall_hpa": round(fall, 2), "trough_rise_hpa": round(rise, 2),
            "gust_bump_ms": round(bump, 2)}


def detect_passages(times, series, cfg=None) -> list:
    """Scan one cell's hourly series for cold-frontal passages.

    times:  sequence of timestamps (hourly, ascending).
    series: mapping variable name -> aligned sequence of floats (numpy arrays
            or plain lists; NaN/None where missing) covering at least
            SERIES_VARIABLES.
    Returns a list of FrontPassage, coalesced (a contiguous or nearly-
    contiguous run of qualifying hours is ONE passage at its first hour).
    Causal: the event at times[i] is decided from hours <= i only.
    """
    cfg = {**DEFAULTS, **(cfg or {})}
    missing = [v for v in SERIES_VARIABLES if v not in series]
    if missing:
        raise KeyError(f"cold_front: variables not provided: {missing}")
    temp = series["temperature_2m"]

    def _hpa(x):
        if x is None:
            return None
        x = float(x)
        return None if math.isnan(x) else x / 100.0

    mslp_hpa = [_hpa(x) for x in series["pressure_msl"]]
    gust = series["wind_gusts_10m"]
    u = series["wind_u_component_10m"]
    v = series["wind_v_component_10m"]

    lookback = max(int(cfg["trough_window_h"]),
                   int(cfg["temp_drop_window_h"]),
                   int(cfg["shift_window_h"]) + int(cfg["shift_mean_h"]))
    n = len(times)
    passages: list = []
    last_hit = None
    for i in range(lookback, n):
        diag = _signature_at(i, temp, mslp_hpa, gust, u, v, cfg)
        if diag is None:
            continue
        if last_hit is not None and i - last_hit <= int(cfg["merge_gap_h"]):
            last_hit = i  # same front, still qualifying: extend the run
            continue
        last_hit = i
        passages.append(FrontPassage(
            index=i, time=times[i], temp_drop_c=diag["temp_drop_c"],
            shift_deg=diag["shift_deg"],
            trough_fall_hpa=diag["trough_fall_hpa"],
            trough_rise_hpa=diag["trough_rise_hpa"],
            gust_bump_ms=diag["gust_bump_ms"]))
    return passages


def temp_spread_c(series, upto_index) -> object:
    """Std-dev of the cell's own hourly 2 m temperature BEFORE the passage
    (causal): the cheap per-cell 'what is normal here right now' spread the
    adaptive unusualness gate compares the frontal drop against. None when
    too little history. (The durable Weather Cell Climatology store carries
    precip/TCWV weekly normals only - wiring stored temperature normals in
    here is the documented follow-up; until then the recent spread plus the
    absolute config threshold provide the unusual-for-here signal.)"""
    vals = _finite(_val(series["temperature_2m"], j)
                   for j in range(0, max(0, int(upto_index))))
    if len(vals) < 48:
        return None
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / len(vals)
    return round(math.sqrt(var), 2)


def is_unusual(passage, series, cfg) -> tuple:
    """(unusual: bool, spread_c: float|None) - is this frontal passage out
    of the ordinary FOR THIS CELL? True when the temperature drop clears the
    absolute config gate, or the adaptive gate (sigma x the cell's own
    pre-frontal spread). Fronts reaching cells where such drops are rare
    (e.g. deep penetration into hot northern areas) flag adaptively even
    when the absolute gate does not fire."""
    spread = temp_spread_c(series, passage.index)
    if passage.temp_drop_c >= float(cfg["unusual_temp_drop_c"]):
        return True, spread
    sigma = float(cfg["unusual_drop_sigma"])
    if sigma > 0 and spread and passage.temp_drop_c >= sigma * spread:
        return True, spread
    return False, spread


def rain_signal_mm(series, passage_index) -> float:
    """Observed precipitation (mm) at the cell since the passage hour - the
    post-frontal moisture signal that gates the rain mention. 0.0 when the
    series has no precipitation variable (unit-test series)."""
    precip = series.get("precipitation")
    if precip is None:
        return 0.0
    vals = _finite(_val(precip, j)
                   for j in range(max(0, int(passage_index)), len(precip)))
    return round(sum(vals), 2) if vals else 0.0


def render_detection(place, unusual=False, rain=False) -> dict:
    """Compose the detection cell's copy from the messages.py building
    blocks: ordinary or unusual variant, with the rain sentence appended
    only when the data-driven gate passed. Always severity advisory."""
    out = messages.render(FRONT_CLASS, SEVERITY_ADVISORY, place)
    place_s = (place or "").strip() or messages.DEFAULT_PLACE
    if unusual:
        out["headline"] = messages.COLD_FRONT_UNUSUAL_HEADLINE.format(
            place=place_s)
        out["message"] = messages.COLD_FRONT_UNUSUAL_MESSAGE.format(
            place=place_s)
    if rain:
        out["message"] += " " + messages.COLD_FRONT_RAIN_SENTENCE
    return out


def steering_speed_ms(series, hours: int = 6) -> object:
    """Mean recent 10 m/100 m wind speed (m/s) from the already-fetched
    series - the front's cheap advection-speed estimate, stored so the
    propagation pass can turn cone distance into a timing phrase. None on
    any problem (propagation then says "soon")."""
    try:
        def _mean_tail(name):
            vals = _finite(float(x) for x in list(series[name])[-hours:])
            if len(vals) < 3:
                raise ValueError("too few wind samples")
            return sum(vals) / len(vals)

        u = (_mean_tail("wind_u_component_10m")
             + _mean_tail("wind_u_component_100m")) / 2.0
        v = (_mean_tail("wind_v_component_10m")
             + _mean_tail("wind_v_component_100m")) / 2.0
        speed = math.hypot(u, v)
        return round(speed, 1) if speed > 0 else None
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# evaluator hook (frappe writes; never raises into the evaluator)
# --------------------------------------------------------------------------- #

def evaluate_cell(loc, series, times, horizon, now=None, steering_deg=None):
    """Per-cell cold-front pass, called by evaluator._evaluate_location on
    the SAME series the frozen detector just consumed.

    Returns a short reason string (for tests/telemetry):
    "disabled" | "no_passage" | "stale" | "cooldown" | "error" |
    "issued:<record name>". Guaranteed never to raise.
    """
    try:
        return _evaluate(loc, series, times, horizon, now or _utcnow(),
                         steering_deg)
    except Exception:
        log_admin_error(TITLE_COLD_FRONT)
        return "error"


def _evaluate(loc, series, times, horizon, now, steering_deg):
    if not cold_front_enabled():
        return "disabled"
    cfg = load_config()
    passages = detect_passages(times, series, cfg)
    if not passages:
        return "no_passage"
    passage = passages[-1]
    age_h = (horizon - passage.time).total_seconds() / 3600.0
    if age_h > float(cfg["recent_h"]):
        return "stale"

    # per-cell cooldown: one advisory per front, not one per hourly pass
    cooldown_h = float(cfg["cooldown_h"])
    if cooldown_h > 0:
        recent = frappe.get_all(
            WARNING_DOCTYPE,
            filters={"watch_location": loc.name,
                     "event_class": FRONT_CLASS,
                     "issued_at": [">=", now - dt.timedelta(hours=cooldown_h)]},
            fields=["name"],
            limit=1,
        )
        if recent:
            return "cooldown"

    # copy scaling: unusual-for-here variant + data-gated rain mention
    unusual, spread = is_unusual(passage, series, cfg)
    post_rain_mm = rain_signal_mm(series, passage.index)
    rain = post_rain_mm >= float(cfg["rain_signal_mm"])

    # advisory-tier hard cap: cap_severity pins the class at "advisory"
    severity = messages.cap_severity(FRONT_CLASS, SEVERITY_ADVISORY)
    rendered = render_detection(loc.label, unusual=unusual, rain=rain)
    assert rendered["severity"] == severity == SEVERITY_ADVISORY
    precursors = json.dumps({
        "mode": MODE_DETECTION,
        "passage_at": passage.time.isoformat(),
        "temp_drop_c": passage.temp_drop_c,
        "shift_deg": passage.shift_deg,
        "trough_fall_hpa": passage.trough_fall_hpa,
        "trough_rise_hpa": passage.trough_rise_hpa,
        "gust_bump_ms": passage.gust_bump_ms,
        "data_horizon": horizon.isoformat(),
        "steering_deg": steering_deg,
        "steering_speed_ms": steering_speed_ms(series),
        # copy-scaling telemetry + the flags projected advisories mirror
        "unusual": unusual,
        "temp_spread_c": spread,
        "rain_signal": rain,
        "post_precip_mm": post_rain_mm,
    })
    doc = frappe.get_doc({
        "doctype": WARNING_DOCTYPE,
        "watch_location": loc.name,
        "event_class": FRONT_CLASS,
        "severity": rendered["severity"],
        "headline": rendered["headline"],
        "message": rendered["message"],
        "onset": passage.time,
        "valid_until": horizon + dt.timedelta(hours=float(cfg["validity_h"])),
        "issued_at": now,
        "status": "active",
        "precursors": precursors,
    }).insert(ignore_permissions=True)

    # admin telemetry: one rate-limited line per detection window. Never a
    # push - advisories are informational and push.py refuses the severity.
    log_admin_error(TITLE_DETECTED, (
        "cold front at {0} ({1}): passage {2}Z, temp drop {3} C, wind shift "
        "{4} deg, trough -{5}/+{6} hPa, gust bump +{7} m/s"
        .format(loc.name, loc.label or "?", passage.time.isoformat(),
                passage.temp_drop_c, passage.shift_deg,
                passage.trough_fall_hpa, passage.trough_rise_hpa,
                passage.gust_bump_ms)))
    return "issued:{0}".format(doc.name)
