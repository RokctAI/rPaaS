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

"""Per-location severe-weather warning detector - core state machine.

Production port of the research detector (weather/research/severe_weather/
detector/detector.py on the research branch): the pure-Python causal state
machine, stripped of the research-only pandas adapters. The core loop uses
only the standard library, so it runs inside a Frappe scheduled job with no
extra dependencies.

The detector turns a causal feature time series for ONE location into
time-indexed warning states per event class:

  conditions   each has: feature, direction ("above"/"below"), on/off
               thresholds (hysteresis: arms when the value crosses `on` and
               has held for persistence_h consecutive hours; stays active
               until the value falls back past `off`), weight.
  required     condition names that must ALL be active for any alarm.
  groups       list of name-lists; each group needs >= 1 active member.
  score        sum of active weights / sum of all weights -> confidence.
  severity_on  score thresholds for watch < warning < severe; a tier is
               retained until score < (threshold - severity_off_margin).
  cooldown_h   after a warning-or-worse episode ends, re-entry into warning+
               is suppressed for this many hours (watch remains possible).
  nan_tolerance_h  a condition holds its state across a NaN gap up to this
               many hours, then de-arms.

Causality: state at time t depends only on feature values at times <= t.
Hourly cadence is assumed throughout.

The shipped rule set is the FROZEN dev-tuned configuration whose provenance
and holdout backtest are recorded in the research branch
(weather/research/severe_weather/BACKTEST.md). It must not be edited here:
``load_rules()`` verifies the packaged file's sha256 against
``CONFIG_SHA256`` and refuses to run on a mismatch.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass, field

#: sha256 of the frozen tuned config (detector_config.json, byte-identical to
#: the research branch's detector/detector_config_tuned.json).
CONFIG_SHA256 = "758ba92bb6ce69c11fc6586c2f64722321e51d19d4c864906cbead9046162ac8"

CONFIG_FILENAME = "detector_config.json"

SEVERITY_LEVELS = ("none", "watch", "warning", "severe")
WARNING_TIER = 2   # tiers: 0 none, 1 watch, 2 warning, 3 severe


def _is_missing(v) -> bool:
    if v is None:
        return True
    try:
        return math.isnan(v)
    except TypeError:
        return False


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Condition:
    name: str
    feature: str
    direction: str          # "above" | "below"
    on: float               # arming threshold
    off: float              # release threshold (hysteresis)
    weight: float
    persistence_h: int = 1  # consecutive on-side hours required to arm

    def __post_init__(self):
        if self.direction not in ("above", "below"):
            raise ValueError(f"condition {self.name}: bad direction {self.direction!r}")
        if self.direction == "above" and not self.off <= self.on:
            raise ValueError(f"condition {self.name}: need off <= on for 'above'")
        if self.direction == "below" and not self.off >= self.on:
            raise ValueError(f"condition {self.name}: need off >= on for 'below'")
        if self.weight < 0:
            raise ValueError(f"condition {self.name}: negative weight")
        if self.persistence_h < 1:
            raise ValueError(f"condition {self.name}: persistence_h must be >= 1")


@dataclass(frozen=True)
class ClassRule:
    event_class: str
    conditions: tuple            # tuple[Condition, ...]
    required: tuple = ()         # names that must all be active
    groups: tuple = ()           # tuple[tuple[str, ...]]: each needs any-of
    severity_on: dict = field(default_factory=lambda: {"watch": 0.35, "warning": 0.55,
                                                       "severe": 0.80})
    severity_off_margin: float = 0.10
    cooldown_h: int = 24
    nan_tolerance_h: int = 6
    notes: str = ""

    def __post_init__(self):
        names = [c.name for c in self.conditions]
        if len(set(names)) != len(names):
            raise ValueError(f"{self.event_class}: duplicate condition names")
        known = set(names)
        for n in list(self.required) + [n for g in self.groups for n in g]:
            if n not in known:
                raise ValueError(f"{self.event_class}: unknown condition {n!r} referenced")
        so = self.severity_on
        if not (0 < so["watch"] <= so["warning"] <= so["severe"] <= 1):
            raise ValueError(f"{self.event_class}: severity_on must be ordered in (0, 1]")
        if sum(c.weight for c in self.conditions) <= 0:
            raise ValueError(f"{self.event_class}: total weight must be positive")

    @property
    def feature_names(self):
        return sorted({c.feature for c in self.conditions})


def rule_from_dict(event_class: str, d: dict) -> ClassRule:
    conds = tuple(Condition(name=c["name"], feature=c["feature"],
                            direction=c["direction"], on=float(c["on"]),
                            off=float(c["off"]), weight=float(c["weight"]),
                            persistence_h=int(c.get("persistence_h", 1)))
                  for c in d["conditions"])
    return ClassRule(
        event_class=event_class, conditions=conds,
        required=tuple(d.get("required", [])),
        groups=tuple(tuple(g) for g in d.get("groups", [])),
        severity_on=dict(d.get("severity_on",
                               {"watch": 0.35, "warning": 0.55, "severe": 0.80})),
        severity_off_margin=float(d.get("severity_off_margin", 0.10)),
        cooldown_h=int(d.get("cooldown_h", 24)),
        nan_tolerance_h=int(d.get("nan_tolerance_h", 6)),
        notes=str(d.get("notes", "")))


def config_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)


def load_rules(path: str | None = None, verify: bool = True) -> dict:
    """Load the frozen config -> {event_class: ClassRule}.

    Verifies the file's sha256 against CONFIG_SHA256 (provenance guard: the
    shipped rules must be byte-identical to the backtested research config).
    Raises on tamper/parse/validation failure - callers treat that as "no
    warnings can be computed", never as a user-visible error.
    """
    path = path or config_path()
    with open(path, "rb") as f:
        raw_bytes = f.read()
    if verify:
        digest = hashlib.sha256(raw_bytes).hexdigest()
        if digest != CONFIG_SHA256:
            raise ValueError(
                f"detector config sha256 mismatch: got {digest}, "
                f"expected {CONFIG_SHA256}")
    raw = json.loads(raw_bytes.decode("utf-8"))
    return {k: rule_from_dict(k, v) for k, v in raw["classes"].items()}


# --------------------------------------------------------------------------- #
# evaluation
# --------------------------------------------------------------------------- #

@dataclass
class Alarm:
    """One warning episode (a contiguous run of severity >= warning)."""
    event_class: str
    first_fired_at: object          # timestamp of the first warning-tier hour
    last_active_at: object          # last hour the episode was still warning+
    max_severity: str = "warning"   # highest tier reached ("warning" | "severe")
    max_confidence: float = 0.0
    fired_conditions: tuple = ()    # active precursor conditions at first firing


@dataclass
class DetectionResult:
    """Time-indexed warning states for one (location, event class)."""
    event_class: str
    times: list
    tier: list                      # int 0..3 per hour
    confidence: list                # float 0..1 per hour (gated score)
    alarms: list                    # list[Alarm]


class _CondState:
    """Forward hysteresis + persistence state machine for one condition."""
    __slots__ = ("c", "active", "streak", "nan_run", "nan_tol")

    def __init__(self, c: Condition, nan_tolerance_h: int):
        self.c = c
        self.active = False
        self.streak = 0
        self.nan_run = 0
        self.nan_tol = nan_tolerance_h

    def step(self, v) -> bool:
        c = self.c
        if _is_missing(v):
            self.nan_run += 1
            if self.nan_run > self.nan_tol:          # gap too long: no information
                self.active, self.streak = False, 0
            return self.active                       # else hold previous state
        self.nan_run = 0
        if c.direction == "above":
            arm, hold = v >= c.on, v >= c.off
        else:
            arm, hold = v <= c.on, v <= c.off
        if self.active:
            self.active = hold                       # hysteresis: release at `off`
            if not self.active:
                self.streak = 0
        else:
            self.streak = self.streak + 1 if arm else 0
            if self.streak >= c.persistence_h:       # persistence: must hold N hours
                self.active = True
        return self.active


def run_class(times, features, rule: ClassRule) -> DetectionResult:
    """Run one class rule over one location's feature series.

    times:    sequence of timestamps (hourly, ascending).
    features: mapping feature name -> sequence of floats aligned with `times`
              (NaN/None where undefined). Every feature the rule references
              must be present.
    """
    missing = [f for f in rule.feature_names if f not in features]
    if missing:
        raise KeyError(f"{rule.event_class}: features not provided: {missing}")
    n = len(times)
    cols = {c.name: features[c.feature] for c in rule.conditions}
    states = [_CondState(c, rule.nan_tolerance_h) for c in rule.conditions]
    total_w = sum(c.weight for c in rule.conditions)
    on_w, on_wn, on_s = (rule.severity_on["watch"], rule.severity_on["warning"],
                         rule.severity_on["severe"])
    margin = rule.severity_off_margin

    tier_out = [0] * n
    conf_out = [0.0] * n
    alarms: list = []
    cur_tier = 0
    cooldown = 0
    open_alarm = None

    for i in range(n):
        active = set()
        score = 0.0
        for st in states:
            if st.step(cols[st.c.name][i]):
                active.add(st.c.name)
                score += st.c.weight
        score /= total_w

        gate = all(r in active for r in rule.required) and \
            all(any(m in active for m in g) for g in rule.groups)
        eff = score if gate else 0.0

        # severity with retention margin (tier-level hysteresis)
        new_tier = 3 if eff >= on_s else 2 if eff >= on_wn else 1 if eff >= on_w else 0
        if new_tier < cur_tier:
            retain_at = (on_s, on_wn, on_w)[3 - cur_tier] - margin
            if eff >= retain_at:
                new_tier = cur_tier
        # cooldown after an episode: cap at watch so alarms cannot flap
        if cooldown > 0:
            cooldown -= 1
            new_tier = min(new_tier, 1)

        # episode bookkeeping
        if new_tier >= WARNING_TIER:
            if open_alarm is None:
                open_alarm = Alarm(event_class=rule.event_class,
                                   first_fired_at=times[i], last_active_at=times[i],
                                   fired_conditions=tuple(sorted(active)))
            open_alarm.last_active_at = times[i]
            if new_tier == 3:
                open_alarm.max_severity = "severe"
            open_alarm.max_confidence = max(open_alarm.max_confidence, eff)
        elif open_alarm is not None:
            alarms.append(open_alarm)
            open_alarm = None
            cooldown = rule.cooldown_h

        cur_tier = new_tier
        tier_out[i] = new_tier
        conf_out[i] = eff

    if open_alarm is not None:
        alarms.append(open_alarm)
    return DetectionResult(rule.event_class, list(times), tier_out, conf_out, alarms)


def run_all(times, features, rules: dict) -> dict:
    """Run every class rule over one location: {event_class: DetectionResult}."""
    return {k: run_class(times, features, r) for k, r in rules.items()}
