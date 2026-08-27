"""Unit checks for the detector core on synthetic series (no data files needed).

Covers: persistence arming, hysteresis release, required/any-of gating,
severity tiers with retention margin, cooldown suppression, NaN tolerance,
and causality (past output unchanged by future input).
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import detector as dz

FAILS = []


def check(name, ok):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}")
    if not ok:
        FAILS.append(name)


def rule(**kw):
    base = dict(
        event_class="t",
        conditions=(dz.Condition("a", "x", "above", 10.0, 5.0, 1.0,
                                 persistence_h=kw.pop("persistence_h", 2)),),
        severity_on={"watch": 0.3, "warning": 0.6, "severe": 0.9},
        cooldown_h=kw.pop("cooldown_h", 4),
        nan_tolerance_h=kw.pop("nan_tolerance_h", 2))
    base.update(kw)
    return dz.ClassRule(**base)


def main():
    n = 40
    times = list(range(n))

    print("persistence: one hot hour must not arm (needs 2)")
    x = [0.0] * n
    x[10] = 20.0
    r = dz.run_class(times, {"x": x}, rule())
    check("no alarm from single spike", not r.alarms and max(r.tier) == 0)

    print("persistence + hysteresis: arms after 2 h, holds until < off")
    x = [0.0] * n
    for i in range(10, 20):
        x[i] = 20.0        # >= on
    for i in range(20, 24):
        x[i] = 7.0         # between off(5) and on(10): hysteresis holds
    r = dz.run_class(times, {"x": x}, rule())
    check("first fire at t=11 (2nd hot hour)",
          r.alarms and r.alarms[0].first_fired_at == 11)
    check("holds through 7.0 zone, releases at t=24",
          r.alarms[0].last_active_at == 23)
    check("severity reaches warning-level tier", r.tier[12] >= dz.WARNING_TIER)

    print("cooldown: quick re-spike cannot re-fire warning")
    x = [0.0] * n
    for i in range(10, 14):
        x[i] = 20.0
    for i in range(16, 20):
        x[i] = 20.0        # entirely inside the cooldown after episode end at t=14
    r = dz.run_class(times, {"x": x}, rule(cooldown_h=8))
    check("only one alarm episode", len(r.alarms) == 1)
    check("cooldown caps at watch", max(r.tier[16:20]) <= 1)

    print("NaN tolerance: short gap holds state, long gap de-arms")
    x = [20.0] * n
    x[15] = x[16] = math.nan                    # <= tolerance (2): hold
    r = dz.run_class(times, {"x": x}, rule())
    check("short gap does not break the episode", len(r.alarms) == 1)
    x2 = [20.0] * n
    for i in range(15, 21):
        x2[i] = math.nan                        # > tolerance: de-arm
    r2 = dz.run_class(times, {"x": x2}, rule())
    check("long gap splits the episode", len(r2.alarms) == 2)

    print("required / any-of gating")
    two = dz.ClassRule(
        event_class="t",
        conditions=(dz.Condition("a", "x", "above", 10, 5, 0.5, 1),
                    dz.Condition("b", "y", "above", 10, 5, 0.5, 1)),
        required=("b",), severity_on={"watch": 0.3, "warning": 0.5, "severe": 0.9},
        cooldown_h=2, nan_tolerance_h=2)
    x = [20.0] * n
    y = [0.0] * n
    r = dz.run_class(times, {"x": x, "y": y}, two)
    check("required 'b' inactive -> confidence gated to 0, no alarm",
          not r.alarms and max(r.confidence) == 0.0)
    y2 = [20.0] * n
    r = dz.run_class(times, {"x": x, "y": y2}, two)
    check("both active -> severe confidence 1.0", max(r.confidence) == 1.0
          and r.alarms and r.alarms[0].max_severity == "severe")
    check("fired conditions recorded", r.alarms[0].fired_conditions == ("a", "b"))

    print("causality: output up to t unaffected by future values")
    x = [0.0] * n
    for i in range(10, 25):
        x[i] = 20.0
    full = dz.run_class(times, {"x": x}, rule())
    trunc = dz.run_class(times[:20], {"x": x[:20]}, rule())
    check("tiers identical on shared prefix", full.tier[:20] == trunc.tier)

    print("config loads and references only known mining features")
    from features import FEATURE_NAMES  # mining feature library
    rules = dz.load_config(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "detector_config.json"))
    unknown = {f for rl in rules.values() for f in rl.feature_names} - set(FEATURE_NAMES)
    check("all 4 classes present", set(rules) == {"flash_flood", "flood",
                                                  "destructive_wind", "tornado"})
    check("no unknown features referenced", not unknown)

    if FAILS:
        print(f"\n{len(FAILS)} FAILURES: {FAILS}")
        sys.exit(1)
    print("\nall detector unit checks passed")


if __name__ == "__main__":
    sys.path.insert(0, os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "mining")))
    main()
