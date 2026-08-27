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

"""Offline synthetic-grid tests for the sw2 propagation pass.

Pure unit tests over plan_propagation / apply_plan (no frappe DB, no
network): direction gating, radii, consensus K, idempotency, tier bounds,
outranking, and the calm-copy rules. Grid geometry uses a synthetic
equatorial grid where 1 degree of latitude ~ 111.19 km, so distances are
easy to reason about.
"""

import datetime as dt
import importlib
import importlib.util
import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FRAPPE_MODULE_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
COMMON_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "warnings_engine")
ENGINE_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "control", "warnings_engine")


def _ensure_frappe_stub():
    try:
        import frappe  # noqa: F401
        # A sibling test module's stub may already be installed (shared
        # process under unittest discover) - top it up with what this
        # module's engine imports need.
        if not hasattr(frappe.utils, "flt"):
            def flt(value):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return 0.0
            frappe.utils.flt = flt
            sys.modules["frappe.utils"].flt = flt
        return
    except ImportError:
        pass
    frappe_mod = types.ModuleType("frappe")
    utils_mod = types.ModuleType("frappe.utils")

    def cint(value):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    def flt(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    utils_mod.cint = cint
    utils_mod.flt = flt
    utils_mod.get_datetime = lambda v: v
    utils_mod.now_datetime = MagicMock()
    frappe_mod.utils = utils_mod
    frappe_mod.conf = {}
    frappe_mod.db = MagicMock()
    frappe_mod.cache = MagicMock()
    frappe_mod.get_doc = MagicMock()
    frappe_mod.get_all = MagicMock()
    frappe_mod.get_traceback = MagicMock(return_value="traceback")
    frappe_mod.log_error = MagicMock()
    frappe_mod.make_get_request = MagicMock()
    frappe_mod.whitelist = lambda *a, **k: (lambda f: f)
    sys.modules["frappe"] = frappe_mod
    sys.modules["frappe.utils"] = utils_mod


def _load_pkg(name, pkg_dir):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name,
        os.path.join(pkg_dir, "__init__.py"),
        submodule_search_locations=[pkg_dir],
    )
    pkg = importlib.util.module_from_spec(spec)
    sys.modules[name] = pkg
    spec.loader.exec_module(pkg)
    return pkg


def _load_engine():
    """Load the split src/ trees exactly as they compose: wmod.warnings_engine
    (common: messages/push/admin_log) and wmod.control.warnings_engine (the
    engine), so the engine's relative imports into common resolve."""
    _ensure_frappe_stub()
    for name in ("wmod", "wmod.control"):
        if name not in sys.modules:
            parent = types.ModuleType(name)
            parent.__path__ = []
            sys.modules[name] = parent
    _load_pkg("wmod.warnings_engine", COMMON_DIR)
    return _load_pkg("wmod.control.warnings_engine", ENGINE_DIR)


_load_engine()
propagation = importlib.import_module("wmod.control.warnings_engine.propagation")
messages = importlib.import_module("wmod.warnings_engine.messages")

KM_PER_DEG_LAT = 111.19


def loc(name, north_km=0.0, east_km=0.0, label=None):
    """A synthetic watch cell placed km north/east of the equatorial origin."""
    return {
        "name": name,
        "latitude": north_km / KM_PER_DEG_LAT,
        "longitude": east_km / KM_PER_DEG_LAT,  # ~exact at the equator
        "label": label or name.capitalize(),
    }


def warning(name, location, event_class="destructive_wind",
            severity="heads_up", steering=None, confidence=0.6,
            onset=None, valid_until=None, status="active", message="msg",
            precursors_extra=None):
    precursors = {"confidence": confidence}
    if steering is not None:
        precursors["steering_deg"] = steering
    if precursors_extra:
        precursors.update(precursors_extra)
    return {
        "name": name,
        "watch_location": location,
        "event_class": event_class,
        "severity": severity,
        "status": status,
        "onset": onset or dt.datetime(2026, 1, 1, 0),
        "valid_until": valid_until or dt.datetime(2026, 1, 3, 0),
        "headline": "hl",
        "message": message,
        "precursors": json.dumps(precursors),
    }


class TestGeometry(unittest.TestCase):
    def test_haversine_one_degree_of_latitude(self):
        self.assertAlmostEqual(propagation.haversine_km(0, 0, 1, 0),
                               KM_PER_DEG_LAT, delta=0.3)

    def test_bearing_cardinals(self):
        self.assertAlmostEqual(propagation.bearing_deg(0, 0, 1, 0), 0.0, places=5)
        self.assertAlmostEqual(propagation.bearing_deg(0, 0, 0, 1), 90.0, places=5)
        self.assertAlmostEqual(propagation.bearing_deg(0, 0, -1, 0), 180.0, places=5)
        self.assertAlmostEqual(propagation.bearing_deg(0, 0, 0, -1), 270.0, places=5)

    def test_steering_from_uv_is_direction_toward(self):
        self.assertAlmostEqual(propagation.steering_deg_from_uv(0.0, 5.0), 0.0)
        self.assertAlmostEqual(propagation.steering_deg_from_uv(5.0, 0.0), 90.0)
        self.assertAlmostEqual(propagation.steering_deg_from_uv(0.0, -5.0), 180.0)
        self.assertAlmostEqual(propagation.steering_deg_from_uv(-5.0, 0.0), 270.0)

    def test_angular_diff_wraps(self):
        self.assertAlmostEqual(propagation.angular_diff_deg(350.0, 10.0), 20.0)
        self.assertAlmostEqual(propagation.angular_diff_deg(90.0, 270.0), 180.0)


class TestDirectionGating(unittest.TestCase):
    def test_downwind_target_gets_advisory_crosswind_does_not(self):
        locations = [loc("src"), loc("north", north_km=100),
                     loc("east", east_km=100)]
        warnings = [warning("W1", "src", steering=0.0)]  # blowing north
        plan = propagation.plan_propagation(locations, warnings)
        targets = {a.target for a in plan.advisories}
        self.assertEqual(targets, {"north"})
        adv = plan.advisories[0]
        self.assertEqual(adv.gating, "directional")
        self.assertEqual(adv.source, "src")
        self.assertEqual(adv.event_class, "destructive_wind")

    def test_cone_half_angle_is_configurable(self):
        locations = [loc("src"), loc("east", east_km=100)]
        warnings = [warning("W1", "src", steering=0.0)]
        wide = propagation.plan_propagation(
            locations, warnings, {"direction_half_angle_deg": 95.0})
        self.assertEqual({a.target for a in wide.advisories}, {"east"})

    def test_no_steering_falls_back_to_reduced_isotropic(self):
        # without a stored steering direction a directional class degrades to
        # the conservative reduced radius (150 * 0.6 = 90 km), any direction
        locations = [loc("src"), loc("near", east_km=80),
                     loc("far", north_km=120)]
        warnings = [warning("W1", "src", steering=None)]
        plan = propagation.plan_propagation(locations, warnings)
        self.assertEqual({a.target for a in plan.advisories}, {"near"})
        self.assertEqual(plan.advisories[0].gating, "isotropic")
        self.assertIsNone(plan.advisories[0].steering_deg)


class TestRadii(unittest.TestCase):
    def test_directional_radius_default_150km(self):
        locations = [loc("src"), loc("in", north_km=140),
                     loc("out", north_km=160)]
        warnings = [warning("W1", "src", steering=0.0)]
        plan = propagation.plan_propagation(locations, warnings)
        self.assertEqual({a.target for a in plan.advisories}, {"in"})

    def test_flood_is_isotropic_at_reduced_radius(self):
        # flood ignores steering entirely and reaches only 90 km by default
        locations = [loc("src"), loc("near_s", north_km=-80),
                     loc("mid", north_km=120), loc("far", north_km=200)]
        warnings = [warning("W1", "src", event_class="flood", steering=0.0)]
        plan = propagation.plan_propagation(locations, warnings)
        self.assertEqual({a.target for a in plan.advisories}, {"near_s"})
        self.assertEqual(plan.advisories[0].gating, "isotropic")

    def test_radius_config_override(self):
        locations = [loc("src"), loc("t", north_km=200)]
        warnings = [warning("W1", "src", steering=0.0)]
        plan = propagation.plan_propagation(
            locations, warnings, {"neighbor_radius_km": 250.0})
        self.assertEqual({a.target for a in plan.advisories}, {"t"})


class TestAdvisoryBounds(unittest.TestCase):
    def test_real_record_at_target_blocks_advisory(self):
        locations = [loc("src"), loc("tgt", north_km=100)]
        warnings = [warning("W1", "src", steering=0.0),
                    warning("W2", "tgt", severity="heads_up")]
        plan = propagation.plan_propagation(locations, warnings)
        self.assertEqual(plan.advisories, [])

    def test_different_class_at_target_does_not_block(self):
        locations = [loc("src"), loc("tgt", north_km=100)]
        warnings = [warning("W1", "src", steering=0.0),
                    warning("W2", "tgt", event_class="flood")]
        plan = propagation.plan_propagation(locations, warnings)
        self.assertEqual({(a.target, a.event_class) for a in plan.advisories},
                         {("tgt", "destructive_wind")})

    def test_advisory_never_seeds_another_advisory(self):
        # an advisory at B must not propagate onward to C (no chains)
        locations = [loc("a"), loc("b", north_km=100), loc("c", north_km=200)]
        warnings = [warning("W1", "a", steering=0.0)]
        plan = propagation.plan_propagation(locations, warnings)
        state = propagation.apply_plan(warnings, plan)
        plan2 = propagation.plan_propagation(locations, state)
        self.assertTrue(plan2.is_empty())
        self.assertNotIn("c", {w["watch_location"] for w in state})

    def test_advisory_expired_when_real_episode_arrives(self):
        locations = [loc("src"), loc("tgt", north_km=100)]
        adv = {
            "name": "ADV-tgt-destructive_wind", "watch_location": "tgt",
            "event_class": "destructive_wind",
            "severity": propagation.SEVERITY_ADVISORY, "status": "active",
            "onset": dt.datetime(2026, 1, 1), "valid_until": dt.datetime(2026, 1, 3),
            "message": "m", "precursors": "{}",
        }
        warnings = [warning("W1", "src", steering=0.0),
                    warning("W2", "tgt"), adv]
        plan = propagation.plan_propagation(locations, warnings)
        self.assertEqual([e.name for e in plan.expiries],
                         ["ADV-tgt-destructive_wind"])
        self.assertEqual(plan.advisories, [])

    def test_advisory_valid_until_never_outlives_source(self):
        locations = [loc("src"), loc("tgt", north_km=100)]
        until = dt.datetime(2026, 1, 2, 6)
        warnings = [warning("W1", "src", steering=0.0, valid_until=until)]
        plan = propagation.plan_propagation(locations, warnings)
        self.assertEqual(plan.advisories[0].valid_until, until)

    def test_refresh_only_when_source_validity_advances(self):
        locations = [loc("src"), loc("tgt", north_km=100)]
        warnings = [warning("W1", "src", steering=0.0,
                            valid_until=dt.datetime(2026, 1, 3))]
        state = propagation.apply_plan(
            warnings, propagation.plan_propagation(locations, warnings))
        # unchanged validity: nothing to do
        self.assertTrue(propagation.plan_propagation(locations, state).is_empty())
        # source validity advances (episode still live at a newer horizon)
        state[0]["valid_until"] = dt.datetime(2026, 1, 4)
        plan = propagation.plan_propagation(locations, state)
        self.assertEqual(len(plan.advisories), 1)
        self.assertEqual(plan.advisories[0].existing_name,
                         "ADV-tgt-destructive_wind")


class TestConsensus(unittest.TestCase):
    def _grid(self, n, spacing_km=90, event_class="flood", severity="heads_up"):
        locations = [loc("c%d" % i, north_km=i * spacing_km) for i in range(n)]
        warnings = [warning("W%d" % i, "c%d" % i, event_class=event_class,
                            severity=severity) for i in range(n)]
        return locations, warnings

    def test_k_members_escalate_fewer_do_not(self):
        locations, warnings = self._grid(4)
        plan = propagation.plan_propagation(locations, warnings)
        self.assertEqual(len(plan.escalations), 4)
        for esc in plan.escalations:
            self.assertEqual(esc.count, 4)
            self.assertEqual(esc.new_severity, "warning")
            self.assertEqual(len(esc.members), 4)
        locations3, warnings3 = self._grid(3)
        self.assertEqual(
            propagation.plan_propagation(locations3, warnings3).escalations, [])

    def test_far_cell_not_counted(self):
        # 3 clustered cells + 1 beyond the 300 km basin radius: no consensus
        locations = [loc("a"), loc("b", north_km=100), loc("c", east_km=100),
                     loc("far", north_km=500)]
        warnings = [warning("W-%s" % n, n, event_class="flood")
                    for n in ("a", "b", "c", "far")]
        plan = propagation.plan_propagation(locations, warnings)
        self.assertEqual(plan.escalations, [])

    def test_consensus_k_config_override(self):
        locations, warnings = self._grid(3)
        plan = propagation.plan_propagation(locations, warnings,
                                            {"consensus_k": 3})
        self.assertEqual({e.count for e in plan.escalations}, {3})

    def test_mixed_classes_do_not_pool(self):
        locations = [loc("c%d" % i, north_km=i * 100) for i in range(4)]
        warnings = [
            warning("W0", "c0", event_class="flood"),
            warning("W1", "c1", event_class="flood"),
            warning("W2", "c2", event_class="flash_flood"),
            warning("W3", "c3", event_class="flash_flood"),
        ]
        plan = propagation.plan_propagation(locations, warnings)
        self.assertEqual(plan.escalations, [])

    def test_tier_bounds(self):
        # heads_up -> warning is the ONLY raise; warning stays warning;
        # tornado is capped and only annotated; advisories never escalate.
        locations, warnings = self._grid(4)
        warnings[0]["severity"] = "warning"
        plan = propagation.plan_propagation(locations, warnings)
        by_name = {e.name: e for e in plan.escalations}
        self.assertIsNone(by_name["W0"].new_severity)  # never re-raise
        self.assertEqual(by_name["W1"].new_severity, "warning")
        state = propagation.apply_plan(warnings, plan)
        sev = {w["name"]: w["severity"] for w in state}
        self.assertEqual(sev["W0"], "warning")   # never downgraded
        self.assertEqual(sev["W1"], "warning")

        locations_t, warnings_t = self._grid(4, event_class="tornado")
        plan_t = propagation.plan_propagation(locations_t, warnings_t)
        self.assertEqual(len(plan_t.escalations), 4)
        for esc in plan_t.escalations:
            self.assertIsNone(esc.new_severity)  # capped at heads_up
            self.assertIn("basin_consensus", esc.precursors)

    def test_consensus_never_invents_an_episode(self):
        locations, warnings = self._grid(4)
        locations.append(loc("quiet", east_km=50))  # active cell, no episode
        plan = propagation.plan_propagation(locations, warnings)
        escalated = {e.name for e in plan.escalations}
        self.assertEqual(escalated, {"W0", "W1", "W2", "W3"})
        # consensus itself creates no records (advisories are pass 1's job,
        # capped at the advisory tier)
        state = propagation.apply_plan(warnings, plan)
        quiet = [w for w in state if w["watch_location"] == "quiet"]
        for w in quiet:
            self.assertEqual(w["severity"], propagation.SEVERITY_ADVISORY)

    def test_advisories_do_not_count_toward_consensus(self):
        locations, warnings = self._grid(3)
        warnings.append({
            "name": "ADV-x", "watch_location": "c0", "event_class": "flood",
            "severity": propagation.SEVERITY_ADVISORY, "status": "active",
            "onset": dt.datetime(2026, 1, 1), "valid_until": dt.datetime(2026, 1, 3),
            "message": "m", "precursors": "{}",
        })
        plan = propagation.plan_propagation(locations, warnings)
        self.assertEqual(plan.escalations, [])

    def test_confidence_boost_recorded_and_bounded(self):
        locations, warnings = self._grid(4)
        plan = propagation.plan_propagation(locations, warnings)
        pre = json.loads(plan.escalations[0].precursors)
        self.assertAlmostEqual(pre["consensus_confidence"], 0.65)  # 0.6 + 0.05
        self.assertEqual(pre["basin_consensus"]["count"], 4)
        self.assertEqual(pre["basin_consensus"]["k"], 4)
        self.assertFalse(set(pre["basin_consensus"]["members"])
                         - {"c0", "c1", "c2", "c3"})
        high = [warning("W%d" % i, "c%d" % i, event_class="flood",
                        confidence=0.99) for i in range(4)]
        plan2 = propagation.plan_propagation(locations, high)
        pre2 = json.loads(plan2.escalations[0].precursors)
        self.assertEqual(pre2["consensus_confidence"], 1.0)


class TestIdempotency(unittest.TestCase):
    def test_full_pass_is_idempotent(self):
        # a busy mixed state: directional advisories + flood consensus
        locations = [loc("a"), loc("b", north_km=100), loc("c", east_km=100),
                     loc("d", north_km=100, east_km=100), loc("e", north_km=250)]
        warnings = [
            warning("W-a", "a", event_class="flood"),
            warning("W-b", "b", event_class="flood"),
            warning("W-c", "c", event_class="flood"),
            warning("W-d", "d", event_class="flood"),
            warning("S-a", "a", event_class="destructive_wind", steering=0.0),
        ]
        plan1 = propagation.plan_propagation(locations, warnings)
        self.assertFalse(plan1.is_empty())
        state = propagation.apply_plan(warnings, plan1)
        plan2 = propagation.plan_propagation(locations, state)
        self.assertTrue(plan2.is_empty(),
                        "second pass must plan nothing, got %r" % plan2)
        state2 = propagation.apply_plan(state, plan2)
        self.assertEqual(state, state2)

    def test_consensus_annotation_updates_only_when_count_changes(self):
        locations = [loc("c%d" % i, north_km=i * 70) for i in range(5)]
        warnings = [warning("W%d" % i, "c%d" % i, event_class="flood")
                    for i in range(4)]
        state = propagation.apply_plan(
            warnings, propagation.plan_propagation(locations, warnings))
        # a fifth cell fires: counts change 4 -> 5, so annotations refresh
        state.append(warning("W4", "c4", event_class="flood"))
        plan = propagation.plan_propagation(locations, state)
        recounted = {e.name: e.count for e in plan.escalations}
        self.assertEqual(recounted.get("W4"), 5)
        self.assertTrue(all(c == 5 for c in recounted.values()))


class TestCopyRules(unittest.TestCase):
    def test_advisory_copy_calm_and_legal(self):
        # iterate propagation's own copy table: classes outside it (e.g.
        # the basin-routed upstream_flood) are gated out of the pass
        # entirely and render their copy via messages.py instead
        for event_class in propagation.ADVISORY_HEADLINES:
            out = propagation.render_advisory(event_class, "Musina")
            self.assertEqual(out["severity"], "advisory")
            self.assertIn("Musina", out["headline"])
            for text in (out["headline"], out["message"],
                         out["severity_label"]):
                self.assertNotIn("warning", text.lower())
        out = propagation.render_advisory("flood", None)
        self.assertIn("your area", out["message"])

    def test_wide_area_notes_calm_and_legal(self):
        for text in propagation.WIDE_AREA_NOTES.values():
            self.assertNotIn("warning", text.lower())

    def test_escalated_copy_has_no_banned_wording(self):
        locations = [loc("c%d" % i, north_km=i * 90) for i in range(4)]
        warnings = [warning("W%d" % i, "c%d" % i, event_class="flood",
                            message="Rivers are getting very wet.")
                    for i in range(4)]
        plan = propagation.plan_propagation(locations, warnings)
        for esc in plan.escalations:
            for text in (esc.headline, esc.message):
                if text:
                    self.assertNotIn("warning", text.lower())
            self.assertIn("wide area", esc.message)

    def test_advisory_is_below_heads_up_in_prominence(self):
        order = propagation.SEVERITY_ORDER
        self.assertLess(order.index("advisory"), order.index("heads_up"))
        self.assertLess(order.index("heads_up"), order.index("warning"))


class TestConfigFlag(unittest.TestCase):
    def test_pass_is_a_noop_unless_enabled(self):
        import frappe
        frappe.conf = {}
        frappe.get_all = MagicMock()
        propagation.run_propagation_pass()
        frappe.get_all.assert_not_called()

    def test_config_overrides_parse(self):
        import frappe
        frappe.conf = {
            "weather_propagation_enabled": 1,
            "weather_propagation_neighbor_radius_km": "200",
            "weather_propagation_consensus_k": "5",
        }
        try:
            cfg = propagation.load_config()
        finally:
            frappe.conf = {}
        self.assertEqual(cfg["enabled"], 1)
        self.assertEqual(cfg["neighbor_radius_km"], 200.0)
        self.assertEqual(cfg["consensus_k"], 5)
        self.assertEqual(cfg["basin_radius_km"], 300.0)  # untouched default


# --------------------------------------------------------------------------- #
# wave-2 integration: advisory enum coherence + evaluator wiring
# --------------------------------------------------------------------------- #

class TestAdvisoryEnumCoherence(unittest.TestCase):
    def test_severity_label_served_for_advisory(self):
        # the endpoint serves messages.SEVERITY_LABELS - the advisory label
        # must exist there and mirror propagation's approved string
        self.assertEqual(messages.SEVERITY_LABELS.get("advisory"),
                         propagation.ADVISORY_LABEL)

    def test_cap_severity_passes_advisory_through_unchanged(self):
        # advisory sits strictly below every per-class cap: clamping must
        # never raise it (tornado's heads_up cap included)
        for event_class in messages.CLASS_MAX_SEVERITY:
            self.assertEqual(
                "advisory", messages.cap_severity(event_class, "advisory"))

    def test_detector_copy_surface_has_no_advisory_rendering(self):
        # advisory copy is owned by propagation.render_advisory; the detector
        # copy surface must fail closed ("no approved copy - do not surface")
        with self.assertRaises(KeyError):
            messages.render("flood", "advisory", "Musina")

    def test_severity_words_exclude_advisory(self):
        # detector-driven severity handling (tier mapping, push ranking)
        # must never be able to produce or act on an advisory
        self.assertNotIn("advisory", messages.SEVERITY_WORDS)


class TestEvaluatorWiring(unittest.TestCase):
    """The three merge-time evaluator hooks for the propagation pass."""

    def test_upsert_excludes_advisories_and_stashes_steering(self):
        import frappe
        from types import SimpleNamespace
        evaluator = importlib.import_module("wmod.control.warnings_engine.evaluator")
        saved_db, saved_conf = frappe.db, frappe.conf
        try:
            frappe.db = MagicMock()
            frappe.db.get_value = MagicMock(return_value="SWW-2026-00007")
            frappe.conf = {}
            now = dt.datetime(2026, 8, 19, 8, 0, 0)
            loc_row = SimpleNamespace(name="-23.00,30.50", label="Thohoyandou")
            episode = SimpleNamespace(
                fired_conditions=("p72_wet",), max_confidence=0.8,
                first_fired_at=dt.datetime(2026, 8, 18, 20, 0, 0))
            result = SimpleNamespace(tier=[2], confidence=[0.6],
                                     alarms=[episode])
            source = SimpleNamespace(name="test_source")
            evaluator._upsert_warning(
                loc_row, "flood", result, source, now, now,
                None, 123.4)
            # (a) the existing-record lookup leaves advisory rows alone -
            # their lifecycle is owned by the propagation pass
            filters = frappe.db.get_value.call_args_list[0][0][1]
            self.assertEqual(["!=", "advisory"], filters.get("severity"))
            # (b) the steering direction is stashed in the precursors JSON
            # for the direction-aware neighbor advisory pass
            fields = frappe.db.set_value.call_args[0][2]
            precursors = json.loads(fields["precursors"])
            self.assertEqual(123.4, precursors["steering_deg"])
        finally:
            frappe.db, frappe.conf = saved_db, saved_conf

    def test_steering_deg_helper_matches_uv_convention(self):
        evaluator = importlib.import_module("wmod.control.warnings_engine.evaluator")
        hours = evaluator.STEERING_HOURS
        # pure westerly (u > 0, v = 0): wind blows TOWARD the east -> 90 deg
        series = {
            "wind_u_component_10m": [10.0] * hours,
            "wind_u_component_100m": [10.0] * hours,
            "wind_v_component_10m": [0.0] * hours,
            "wind_v_component_100m": [0.0] * hours,
        }
        self.assertEqual(90.0, evaluator._steering_deg(series))
        # unusable series (too few samples) -> None -> isotropic fallback
        short = {key: [10.0, 10.0] for key in series}
        self.assertIsNone(evaluator._steering_deg(short))

    def test_propagation_pass_wired_after_the_location_loop(self):
        path = os.path.join(ENGINE_DIR, "evaluator.py")
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        call_at = source.index("run_propagation_pass(now)")
        loop_at = source.index("for loc in locations:")
        self.assertGreater(call_at, loop_at)
        # the wrapper guards the call itself (per-record isolation is inside)
        self.assertIn("except Exception:",
                      source[call_at:call_at + 200])


if __name__ == "__main__":
    unittest.main()
