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

"""Offline tests for forecast fusion (sw7): the Open-Meteo forecast source
and the forecast-feed detection pass.

All HTTP is mocked (frappe.make_get_request is replaced by a recording
fixture fetcher); the pass tests inject fake sources and use the shared
in-memory FakeLedgerDB. No bench, no network - runs with
`python3 -m unittest` anywhere. Covers: point-payload parsing and unit
conversion, past_days / forecast_days sizing, u/v derivation from
speed+direction, the depth-weighted soil 0-7 cm aggregation, the 80/120 m ->
100 m wind interpolation (NaN on a missing level), the 7x7 multi-location
neighborhood call shaping (spacing, ordering, polar clamp, date-line wrap),
forecast-basis signal firing over the REAL frozen detector, default-OFF
gating (fail-closed), refresh high-water marks, strict separation from
Severe Weather Warning records, and the fire-and-verify ledger (hit /
false_alarm / data-gap retry / missed_event accounting).
"""

import datetime as dt
import importlib
import importlib.util
import json
import math
import os
import sys
import types
import unittest

import numpy as np

from sw6_harness import FakeLedgerDB, ensure_frappe_stub

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FRAPPE_MODULE_DIR = os.path.abspath(os.path.join(TESTS_DIR, ".."))
COMMON_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "warnings_engine")
ENGINE_DIR = os.path.join(FRAPPE_MODULE_DIR, "src", "control", "warnings_engine")


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
    ensure_frappe_stub()
    for name in ("wmod", "wmod.control"):
        if name not in sys.modules:
            parent = types.ModuleType(name)
            parent.__path__ = []
            sys.modules[name] = parent
    _load_pkg("wmod.warnings_engine", COMMON_DIR)
    return _load_pkg("wmod.control.warnings_engine", ENGINE_DIR)


_load_engine()
detector = importlib.import_module("wmod.control.warnings_engine.detector")
features = importlib.import_module("wmod.control.warnings_engine.features")
forecast = importlib.import_module("wmod.control.warnings_engine.forecast")
fsrc = importlib.import_module(
    "wmod.control.warnings_engine.sources.openmeteo_forecast")

import frappe  # noqa: E402  (stubbed by the harness)

NOW = dt.datetime(2026, 8, 20, 12, 0)
WINDOW = forecast.WINDOW_HOURS


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

class _AttrDict(dict):
    """dict rows with frappe._dict-style attribute access."""
    __getattr__ = dict.get


class EngineDB(FakeLedgerDB):
    def get_all(self, *args, **kwargs):
        return [_AttrDict(r) for r in super().get_all(*args, **kwargs)]


class _FakeCache:
    def __init__(self):
        self.store = {}

    def get_value(self, key):
        return self.store.get(key)

    def set_value(self, key, value):
        self.store[key] = value


def _payload(start, hours, **series):
    """A forecast-API-shaped point payload starting at `start`."""
    times = [(start + dt.timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M")
             for i in range(hours)]
    hourly = {"time": times}
    for name, value in series.items():
        if callable(value):
            hourly[name] = [value(i) for i in range(hours)]
        else:
            hourly[name] = [value] * hours
    return {"hourly": hourly}


def _full_point_payload(start, hours):
    """A payload carrying every variable the source requests."""
    return _payload(
        start, hours,
        precipitation=lambda i: float(i),
        soil_moisture_0_to_1cm=0.1,
        soil_moisture_1_to_3cm=0.2,
        soil_moisture_3_to_9cm=0.4,
        pressure_msl=1013.25,
        wind_gusts_10m=7.0,
        wind_speed_10m=5.0,
        wind_direction_10m=180.0,
        wind_speed_80m=10.0,
        wind_direction_80m=270.0,
        wind_speed_120m=20.0,
        wind_direction_120m=270.0,
        temperature_2m=20.0,
        dew_point_2m=15.0,
        total_column_integrated_water_vapour=30.0,
    )


def _make_source(payload, conf=None):
    """A forecast source with recorded requests and a fixed clock."""
    frappe.conf = dict(conf or {})
    src = fsrc.OpenMeteoForecastSource()
    src.data_horizon_utc = lambda: NOW
    calls = []

    def fake_get(url, params=None):
        calls.append((url, dict(params or {})))
        return payload

    frappe.make_get_request = fake_get
    return src, calls


# --------------------------------------------------------------------------- #
# past_days / forecast_days sizing
# --------------------------------------------------------------------------- #

class TestWindowSizing(unittest.TestCase):
    def test_past_days_covers_the_full_feature_window(self):
        # the engine's 408 h trailing window (causal sm percentile, 168 h
        # TCWV baseline, 24 h MSLP tendency) must be fully inside past_days
        start = NOW - dt.timedelta(hours=WINDOW)
        days = fsrc.required_past_days(start, NOW)
        timeline_start = dt.datetime.combine(
            NOW.date() - dt.timedelta(days=days), dt.time())
        self.assertLessEqual(timeline_start, start)
        self.assertEqual(days, 17)  # 408 h = 17 days

    def test_past_days_zero_when_window_starts_today(self):
        self.assertEqual(fsrc.required_past_days(NOW, NOW), 0)

    def test_past_days_clamped_to_api_bound(self):
        start = NOW - dt.timedelta(days=400)
        self.assertEqual(fsrc.required_past_days(start, NOW),
                         fsrc.MAX_PAST_DAYS)

    def test_forecast_days_covers_the_horizon(self):
        for hour in (0, 1, 11, 23):
            now = NOW.replace(hour=hour)
            for horizon in (24, 48, 72, 120):
                end = now + dt.timedelta(hours=horizon)
                days = fsrc.required_forecast_days(end, now)
                timeline_end = dt.datetime.combine(
                    now.date() + dt.timedelta(days=days), dt.time())
                self.assertGreaterEqual(
                    timeline_end, end,
                    f"forecast_days={days} too short at {now} +{horizon}h")

    def test_forecast_days_clamped_to_api_bound(self):
        end = NOW + dt.timedelta(days=40)
        self.assertEqual(fsrc.required_forecast_days(end, NOW),
                         fsrc.MAX_FORECAST_DAYS)


# --------------------------------------------------------------------------- #
# point request + parsing
# --------------------------------------------------------------------------- #

class TestPointSeries(unittest.TestCase):
    START = NOW - dt.timedelta(hours=30)
    END = NOW + dt.timedelta(hours=6)
    PAYLOAD_START = dt.datetime(2026, 8, 19, 0, 0)  # past_days=1 timeline

    def _series(self, payload=None, conf=None, variables=None):
        payload = payload or _full_point_payload(self.PAYLOAD_START, 48)
        src, calls = _make_source(payload, conf)
        out = src.hourly_series(
            -25.87, 28.13, variables or list(features.POINT_VARIABLES),
            self.START, self.END)
        return out, calls

    def test_request_shape(self):
        _, calls = self._series()
        self.assertEqual(len(calls), 1)
        url, params = calls[0]
        self.assertEqual(url, fsrc.DEFAULT_FORECAST_URL)
        # start is 30 h back (06:00 the previous UTC day): past_days=1
        # makes the timeline begin 00:00 that day, covering it
        self.assertEqual(params["past_days"], 1)
        self.assertEqual(params["forecast_days"], 1)
        self.assertEqual(params["wind_speed_unit"], "ms")
        self.assertEqual(params["timezone"], "UTC")
        self.assertNotIn("apikey", params)
        self.assertNotIn("models", params)
        for name in fsrc.HOURLY_VARIABLES:
            self.assertIn(name, params["hourly"].split(","))

    def test_optional_key_and_model_config(self):
        _, calls = self._series(conf={
            "severe_weather_forecast_api_key": "k123",
            "severe_weather_forecast_model": "ecmwf_ifs025",
        })
        _, params = calls[0]
        self.assertEqual(params["apikey"], "k123")
        self.assertEqual(params["models"], "ecmwf_ifs025")

    def test_alignment_and_length(self):
        out, _ = self._series()
        n = int((self.END - self.START).total_seconds() // 3600)
        precip = out["precipitation"]
        self.assertEqual(precip.shape, (n,))
        # payload hour i carries value float(i); the window starts 6 h into
        # the payload timeline (payload 00:00 Aug 19, window 06:00 Aug 19)
        self.assertEqual(precip[0], 6.0)
        self.assertEqual(precip[-1], 6.0 + n - 1)

    def test_unit_conversions(self):
        out, _ = self._series()
        self.assertTrue(np.allclose(out["pressure_msl"], 101325.0))
        # soil: depth-weighted (1*0.1 + 2*0.2 + 4*0.4) / 7 = 0.3
        self.assertTrue(np.allclose(out["soil_moisture_0_to_7cm"], 0.3))
        self.assertTrue(np.allclose(out["temperature_2m"], 20.0))
        self.assertTrue(
            np.allclose(out["total_column_integrated_water_vapour"], 30.0))

    def test_uv_from_speed_direction(self):
        out, _ = self._series()
        # 10 m: 5 m/s from 180 deg (southerly) -> u ~ 0, v = +5
        self.assertTrue(np.allclose(out["wind_u_component_10m"], 0.0,
                                    atol=1e-9))
        self.assertTrue(np.allclose(out["wind_v_component_10m"], 5.0))
        # 100 m: mean of 80 m (10 m/s) and 120 m (20 m/s), both from 270 deg
        # (westerly) -> u = +15, v ~ 0
        self.assertTrue(np.allclose(out["wind_u_component_100m"], 15.0))
        self.assertTrue(np.allclose(out["wind_v_component_100m"], 0.0,
                                    atol=1e-9))

    def test_missing_wind_level_yields_nan_not_a_guess(self):
        payload = _full_point_payload(self.PAYLOAD_START, 48)
        payload["hourly"]["wind_speed_120m"] = [None] * 48
        out, _ = self._series(payload=payload)
        self.assertTrue(np.isnan(out["wind_u_component_100m"]).all())
        self.assertTrue(np.isnan(out["wind_v_component_100m"]).all())

    def test_missing_soil_layer_yields_nan(self):
        payload = _full_point_payload(self.PAYLOAD_START, 48)
        payload["hourly"]["soil_moisture_1_to_3cm"] = [None] * 48
        out, _ = self._series(payload=payload)
        self.assertTrue(np.isnan(out["soil_moisture_0_to_7cm"]).all())

    def test_null_hours_become_nan_and_gaps_stay_nan(self):
        payload = _full_point_payload(self.PAYLOAD_START, 48)
        payload["hourly"]["precipitation"][10] = None  # inside the window
        out, _ = self._series(payload=payload)
        self.assertTrue(math.isnan(out["precipitation"][4]))  # payload h 10

    def test_short_payload_leaves_trailing_nan(self):
        payload = _full_point_payload(self.PAYLOAD_START, 20)  # ends early
        out, _ = self._series(payload=payload)
        self.assertTrue(np.isnan(out["precipitation"][-1]))

    def test_unknown_variable_raises(self):
        with self.assertRaises(KeyError):
            self._series(variables=["no_such_variable"])


# --------------------------------------------------------------------------- #
# neighborhood multi-location call
# --------------------------------------------------------------------------- #

class TestNeighborhood(unittest.TestCase):
    START = NOW - dt.timedelta(hours=12)
    END = NOW + dt.timedelta(hours=12)

    def _run(self, lat, lon):
        n = int((self.END - self.START).total_seconds() // 3600)
        captured = {}

        def fake_get(url, params=None):
            captured["params"] = dict(params or {})
            lats = [float(v) for v in params["latitude"].split(",")]
            payloads = []
            for k in range(len(lats)):
                payloads.append(_payload(
                    dt.datetime(2026, 8, 20, 0, 0), 48,
                    precipitation=float(k)))
            return payloads

        frappe.conf = {}
        src = fsrc.OpenMeteoForecastSource()
        src.data_horizon_utc = lambda: NOW
        frappe.make_get_request = fake_get
        cells = src.neighborhood_precipitation(lat, lon, self.START, self.END)
        return cells, captured.get("params"), n

    def test_grid_shape_spacing_and_ordering(self):
        cells, params, n = self._run(-25.87, 28.13)
        self.assertEqual(cells.shape, (n, 49))
        lats = [float(v) for v in params["latitude"].split(",")]
        lons = [float(v) for v in params["longitude"].split(",")]
        self.assertEqual(len(lats), 49)
        self.assertEqual(len(lons), 49)
        # centered on the grid-rounded point (-25.75, 28.25), +-0.75 deg at
        # 0.25 deg spacing, row-major south-to-north like the S3 source
        self.assertEqual(lats[0], -26.5)
        self.assertEqual(lats[-1], -25.0)
        self.assertEqual(lons[:7], [27.5, 27.75, 28.0, 28.25, 28.5,
                                    28.75, 29.0])
        self.assertEqual(sorted(set(lats)),
                         [-26.5, -26.25, -26.0, -25.75, -25.5, -25.25, -25.0])
        # hourly: only precipitation; sizing params present
        self.assertEqual(params["hourly"], "precipitation")
        self.assertIn("past_days", params)
        self.assertIn("forecast_days", params)

    def test_cell_columns_map_to_locations(self):
        cells, _, _ = self._run(-25.87, 28.13)
        for col in range(49):
            self.assertTrue(np.allclose(cells[:, col], float(col)),
                            f"column {col} not mapped to its location")

    def test_polar_clamp_leaves_offgrid_rows_nan(self):
        cells, params, _ = self._run(89.95, 10.0)
        lats = [float(v) for v in params["latitude"].split(",")]
        self.assertEqual(len(lats), 28)          # 4 valid rows x 7
        self.assertTrue(max(lats) <= 90.0)
        self.assertTrue(np.isnan(cells[:, 28:]).all())   # rows past the pole
        self.assertFalse(np.isnan(cells[:, :28]).any())

    def test_dateline_wrap_keeps_longitudes_in_range(self):
        _, params, _ = self._run(0.0, 179.9)
        lons = [float(v) for v in params["longitude"].split(",")]
        self.assertEqual(len(lons), 49)
        for v in lons:
            self.assertTrue(-180.0 <= v < 180.0, f"bad wrapped longitude {v}")


# --------------------------------------------------------------------------- #
# fake sources + DB base for the pass tests
# --------------------------------------------------------------------------- #

class FakeForecastSource:
    """Series that keep every class quiet in the past window and drive the
    REAL frozen flood rule to warning tier a few hours into the forecast."""

    name = "openmeteo_forecast"
    model = ""

    def __init__(self, future_rain_mm_h=10.0):
        self.future_rain = future_rain_mm_h
        self.point_calls = 0
        self.nbr_calls = 0

    def hourly_series(self, latitude, longitude, variables, start, end):
        self.point_calls += 1
        n = int((end - start).total_seconds() // 3600)
        hours = [start + dt.timedelta(hours=i) for i in range(n)]
        precip = np.array([self.future_rain if t >= NOW else 0.0
                           for t in hours])
        soil = np.linspace(0.1, 0.5, n)      # rising: causal pctl -> 1.0
        const = lambda v: np.full(n, float(v))  # noqa: E731
        return {
            "precipitation": precip,
            "soil_moisture_0_to_7cm": soil,
            "pressure_msl": const(101325.0),
            "wind_gusts_10m": const(0.0),
            "wind_u_component_10m": const(0.0),
            "wind_v_component_10m": const(0.0),
            "wind_u_component_100m": const(0.0),
            "wind_v_component_100m": const(0.0),
            "temperature_2m": const(20.0),
            "dew_point_2m": const(15.0),
            "total_column_integrated_water_vapour": const(30.0),
        }

    def neighborhood_precipitation(self, latitude, longitude, start, end):
        self.nbr_calls += 1
        return None   # nbr conditions stay off (flash_flood cannot arm)


class FakeObservedSource:
    """Observed-basis source for verification: constant precip + gusts."""

    name = "openmeteo_s3"

    def __init__(self, horizon, precip_mm_h=0.0, gust_ms=0.0, all_nan=False):
        self.horizon = horizon
        self.precip = precip_mm_h
        self.gust = gust_ms
        self.all_nan = all_nan

    def data_horizon_utc(self):
        return self.horizon

    def hourly_series(self, latitude, longitude, variables, start, end):
        n = int((end - start).total_seconds() // 3600)
        if self.all_nan:
            return {v: np.full(n, np.nan) for v in variables}
        return {"precipitation": np.full(n, self.precip),
                "wind_gusts_10m": np.full(n, self.gust)}


class ForecastPassCase(unittest.TestCase):
    """Base: fake DB + captured admin log + clean config per test."""

    def setUp(self):
        self.db = EngineDB()
        self._saved = {
            "conf": frappe.conf, "db": frappe.db,
            "get_all": frappe.get_all, "get_doc": frappe.get_doc,
            "cache": getattr(frappe, "cache", None),
        }
        frappe.conf = {"severe_weather_forecast_detection": "1"}
        frappe.db = types.SimpleNamespace(
            get_value=self.db.get_value,
            set_value=self.db.set_value,
            get_single_value=self.db.get_single_value,
        )
        frappe.get_all = self.db.get_all
        frappe.get_doc = self.db.get_doc
        self.cache = _FakeCache()
        frappe.cache = lambda: self.cache

        self.admin_logs = []
        self._saved_log = forecast.log_admin_error
        forecast.log_admin_error = (
            lambda title, message=None: self.admin_logs.append((title,
                                                                message)))
        self.loc = self.db.seed(
            "Weather Watch Location", name="-25.75,28.25", active=1,
            latitude=-25.75, longitude=28.25, label=None,
            last_requested_at=NOW - dt.timedelta(hours=2))

    def tearDown(self):
        forecast.log_admin_error = self._saved_log
        frappe.conf = self._saved["conf"]
        frappe.db = self._saved["db"]
        frappe.get_all = self._saved["get_all"]
        frappe.get_doc = self._saved["get_doc"]
        if self._saved["cache"] is None:
            if hasattr(frappe, "cache"):
                delattr(frappe, "cache")
        else:
            frappe.cache = self._saved["cache"]

    def signals(self):
        return self.db.rows(forecast.SIGNAL_DOCTYPE)


# --------------------------------------------------------------------------- #
# firing pass
# --------------------------------------------------------------------------- #

class TestForecastPassFiring(ForecastPassCase):
    def test_default_off_no_fetch_no_rows(self):
        frappe.conf = {}   # flag absent -> fail-closed OFF
        src = FakeForecastSource()
        forecast.run_forecast_pass(source=src, now=NOW)
        self.assertEqual(src.point_calls, 0)
        self.assertEqual(self.signals(), [])

    def test_explicit_falsy_stays_off(self):
        for value in ("0", "false", "no", "off", ""):
            frappe.conf = {"severe_weather_forecast_detection": value}
            self.assertFalse(forecast.is_enabled())
        frappe.conf = {"severe_weather_forecast_detection": "1"}
        self.assertTrue(forecast.is_enabled())

    def test_fires_forecast_basis_flood_signal(self):
        src = FakeForecastSource()
        forecast.run_forecast_pass(source=src, now=NOW)
        rows = self.signals()
        self.assertEqual(len(rows), 1)
        sig = rows[0]
        self.assertEqual(sig["event_class"], "flood")
        self.assertEqual(sig["basis"], "forecast")
        self.assertEqual(sig["status"], "open")
        self.assertEqual(sig["source"], "openmeteo_forecast")
        self.assertEqual(sig["model"], "best_match")
        self.assertEqual(sig["config_sha256"], detector.CONFIG_SHA256)
        self.assertEqual(sig["horizon_hours"], 72)
        # heavy rain starts AT now, so the frozen flood gates need a few
        # accumulation hours: strictly-future firing with an honest lead
        self.assertGreater(sig["lead_hours"], 0)
        self.assertLess(sig["lead_hours"], 24)
        self.assertEqual(sig["first_forecast_at"],
                         NOW + dt.timedelta(hours=sig["lead_hours"]))
        self.assertGreaterEqual(sig["peak_tier"], detector.WARNING_TIER)
        evidence = json.loads(sig["evidence"])
        self.assertEqual(evidence["basis"], "forecast")
        self.assertEqual(evidence["config_sha256"], detector.CONFIG_SHA256)
        self.assertTrue(evidence["fired_conditions"])

    def test_never_touches_warning_records(self):
        forecast.run_forecast_pass(source=FakeForecastSource(), now=NOW)
        self.assertEqual(self.db.rows("Severe Weather Warning"), [])

    def test_quiet_forecast_fires_nothing(self):
        src = FakeForecastSource(future_rain_mm_h=0.0)
        forecast.run_forecast_pass(source=src, now=NOW)
        self.assertEqual(self.signals(), [])
        self.assertEqual(src.point_calls, 1)   # it did look

    def test_refresh_updates_open_signal_with_high_water_marks(self):
        forecast.run_forecast_pass(source=FakeForecastSource(), now=NOW)
        first_peak = self.signals()[0]["peak_tier"]
        later = NOW + dt.timedelta(hours=1)
        forecast.run_forecast_pass(source=FakeForecastSource(), now=later)
        rows = self.signals()
        self.assertEqual(len(rows), 1)          # refreshed, not duplicated
        sig = rows[0]
        self.assertEqual(sig["refresh_count"], 1)
        self.assertEqual(sig["refreshed_at"], later)
        self.assertEqual(sig["issued_at"], NOW)
        # peaks are high-water marks: a refresh can never shrink the claim
        self.assertGreaterEqual(sig["peak_tier"], first_peak)

    def test_weakened_forecast_never_deletes_a_fired_signal(self):
        forecast.run_forecast_pass(source=FakeForecastSource(), now=NOW)
        later = NOW + dt.timedelta(hours=1)
        # the next run shows nothing at all - the open signal must survive
        forecast.run_forecast_pass(source=FakeForecastSource(0.0), now=later)
        rows = self.signals()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "open")
        self.assertEqual(rows[0]["refresh_count"], 0)   # not refreshed

    def test_hour_short_circuit(self):
        src = FakeForecastSource()
        forecast.run_forecast_pass(source=src, now=NOW)
        forecast.run_forecast_pass(source=src, now=NOW)
        self.assertEqual(src.point_calls, 1)

    def test_stale_location_skipped(self):
        self.loc["last_requested_at"] = NOW - dt.timedelta(days=40)
        src = FakeForecastSource()
        forecast.run_forecast_pass(source=src, now=NOW)
        self.assertEqual(src.point_calls, 0)

    def test_source_failure_is_isolated_and_logged(self):
        class Boom(FakeForecastSource):
            def hourly_series(self, *a, **k):
                raise RuntimeError("api down")

        forecast.run_forecast_pass(source=Boom(), now=NOW)   # must not raise
        self.assertEqual(self.signals(), [])
        self.assertIn(forecast.TITLE_FORECAST_PASS,
                      [t for t, _ in self.admin_logs])

    def test_first_forecast_firing_helper(self):
        result = types.SimpleNamespace(tier=[0, 0, 2, 0, 3], confidence=[])
        self.assertEqual(forecast.first_forecast_firing(result, 3), (4, 1))
        self.assertIsNone(forecast.first_forecast_firing(
            types.SimpleNamespace(tier=[3, 3, 0, 0], confidence=[]), 2))


# --------------------------------------------------------------------------- #
# verification (fire-and-verify ledger)
# --------------------------------------------------------------------------- #

class TestForecastVerification(ForecastPassCase):
    def _seed_open_signal(self, issued_offset_h=-120, predicted_offset_h=-110,
                          event_class="flood"):
        return self.db.seed(
            forecast.SIGNAL_DOCTYPE,
            watch_location=self.loc["name"], event_class=event_class,
            basis="forecast", status="open",
            issued_at=NOW + dt.timedelta(hours=issued_offset_h),
            first_forecast_at=NOW + dt.timedelta(hours=predicted_offset_h),
            lead_hours=predicted_offset_h - issued_offset_h,
            peak_tier=2, peak_confidence=0.7)

    def test_hit_when_extremes_materialized(self):
        sig = self._seed_open_signal()
        observed = FakeObservedSource(horizon=NOW, precip_mm_h=5.0)
        forecast.verify_forecast_signals(observed_source=observed, now=NOW)
        self.assertEqual(sig["status"], "hit")
        self.assertEqual(sig["verified_at"], NOW)
        verification = json.loads(sig["verification"])
        self.assertEqual(verification["verdict"], "verified")
        self.assertEqual(verification["observed_source"], "openmeteo_s3")

    def test_false_alarm_when_nothing_followed(self):
        sig = self._seed_open_signal()
        observed = FakeObservedSource(horizon=NOW, precip_mm_h=0.0)
        forecast.verify_forecast_signals(observed_source=observed, now=NOW)
        self.assertEqual(sig["status"], "false_alarm")

    def test_data_gap_never_judged_blind(self):
        sig = self._seed_open_signal()
        observed = FakeObservedSource(horizon=NOW, all_nan=True)
        forecast.verify_forecast_signals(observed_source=observed, now=NOW)
        self.assertEqual(sig["status"], "open")   # retried later

    def test_waits_for_observed_data_to_catch_up(self):
        sig = self._seed_open_signal(issued_offset_h=-12,
                                     predicted_offset_h=-2)
        # window end = predicted + 48 (flood validity) + 48 aftermath;
        # the horizon is far behind that
        observed = FakeObservedSource(horizon=NOW, precip_mm_h=5.0)
        forecast.verify_forecast_signals(observed_source=observed, now=NOW)
        self.assertEqual(sig["status"], "open")

    def test_settling_runs_even_with_the_switch_off(self):
        frappe.conf = {}   # firing disabled - fired claims still settle
        sig = self._seed_open_signal()
        observed = FakeObservedSource(horizon=NOW, precip_mm_h=5.0)
        forecast.verify_forecast_signals(observed_source=observed, now=NOW)
        self.assertEqual(sig["status"], "hit")

    def _seed_episode(self, onset_offset_h=-48, **extra):
        return self.db.seed(
            "Severe Weather Warning", watch_location=self.loc["name"],
            event_class="flood", severity="warning",
            onset=NOW + dt.timedelta(hours=onset_offset_h), status="expired",
            **extra)

    def test_missed_event_recorded_for_unpredicted_episode(self):
        ep = self._seed_episode()
        observed = FakeObservedSource(horizon=NOW)
        forecast.verify_forecast_signals(observed_source=observed, now=NOW)
        misses = [r for r in self.signals()
                  if r["status"] == "missed_event"]
        self.assertEqual(len(misses), 1)
        self.assertEqual(misses[0]["warning"], ep["name"])
        self.assertEqual(misses[0]["basis"], "forecast")
        # idempotent: a second run files nothing new
        forecast.verify_forecast_signals(observed_source=observed, now=NOW)
        self.assertEqual(
            len([r for r in self.signals()
                 if r["status"] == "missed_event"]), 1)

    def test_predicted_episode_is_not_a_miss(self):
        self._seed_episode()
        self.db.seed(
            forecast.SIGNAL_DOCTYPE, watch_location=self.loc["name"],
            event_class="flood", basis="forecast", status="false_alarm",
            issued_at=NOW - dt.timedelta(hours=60),
            first_forecast_at=NOW - dt.timedelta(hours=50))
        forecast.verify_forecast_signals(
            observed_source=FakeObservedSource(horizon=NOW), now=NOW)
        self.assertEqual([r for r in self.signals()
                          if r["status"] == "missed_event"], [])

    def test_drill_episode_never_counts_as_miss(self):
        self._seed_episode(is_drill=1)
        forecast.verify_forecast_signals(
            observed_source=FakeObservedSource(horizon=NOW), now=NOW)
        self.assertEqual([r for r in self.signals()
                          if r["status"] == "missed_event"], [])

    def test_miss_scan_gated_by_master_switch(self):
        frappe.conf = {}   # pass off: "never predicted" reflects config
        self._seed_episode()
        forecast.verify_forecast_signals(
            observed_source=FakeObservedSource(horizon=NOW), now=NOW)
        self.assertEqual(self.signals(), [])

    def test_verification_never_raises(self):
        class Boom:
            name = "boom"

            def data_horizon_utc(self):
                raise RuntimeError("meta down")

        forecast.verify_forecast_signals(observed_source=Boom(), now=NOW)
        self.assertIn(forecast.TITLE_FORECAST_PASS,
                      [t for t, _ in self.admin_logs])


# --------------------------------------------------------------------------- #
# frozen-config discipline
# --------------------------------------------------------------------------- #

class TestFrozenDiscipline(unittest.TestCase):
    def test_pass_uses_the_sha_verified_frozen_rules(self):
        # forecast.py calls detector.load_rules() (sha-verified) and stamps
        # detector.CONFIG_SHA256 on every row - no private rule copy exists
        self.assertTrue(hasattr(forecast, "detector"))
        rules = forecast.detector.load_rules()
        self.assertEqual(set(rules),
                         {"flash_flood", "flood", "destructive_wind",
                          "tornado"})

    def test_horizon_clamped(self):
        frappe.conf = {"severe_weather_forecast_horizon_hours": "500"}
        self.assertEqual(forecast.horizon_hours(), forecast.MAX_HORIZON_HOURS)
        frappe.conf = {"severe_weather_forecast_horizon_hours": "1"}
        self.assertEqual(forecast.horizon_hours(), forecast.MIN_HORIZON_HOURS)
        frappe.conf = {}
        self.assertEqual(forecast.horizon_hours(),
                         forecast.DEFAULT_HORIZON_HOURS)


if __name__ == "__main__":
    unittest.main()
