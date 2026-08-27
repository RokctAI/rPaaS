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

"""Open-Meteo FORECAST API source - the forward-looking feed (sw7).

Serves the same hourly series contract as the other sources, but from the
public Open-Meteo forecast API (open-meteo.com), whose timeline extends INTO
THE FUTURE. One request returns `past_days` of the model's own recent
analysis plus `forecast_days` of forecast, so a single call covers the full
trailing feature window (408 h: causal soil-moisture percentile, 168 h TCWV
baseline, 24 h MSLP tendency) AND the forward horizon the forecast pass
(warnings_engine/forecast.py) evaluates.

This source is used ONLY by the config-gated forecast pass. It is never
returned by sources.base.get_data_source(), so the observed-basis evaluator,
outcome ledger, climatology and basin passes cannot accidentally consume
forecast data.

Units returned (ERA5 storage units, as every source): precipitation mm/h;
winds m/s (wind_speed_unit=ms is requested explicitly - the API default is
km/h); pressure_msl Pa (API hPa * 100); temperature_2m / dew_point_2m degC;
soil moisture m3/m3; TCWV kg/m2.

DOCUMENTED TRANSFER APPROXIMATIONS (see also warnings_engine/FUSION.md) -
the frozen detector was tuned on ERA5, and these three inputs cannot be
reproduced exactly from the forecast API:

  1. Soil moisture layers: ERA5 stores a single 0-7 cm layer; the forecast
     API exposes 0-1 / 1-3 / 3-9 cm. We approximate 0-7 cm with a
     depth-weighted mean (weights 1/7, 2/7, 4/7 - the 3-9 cm layer stands in
     for its 3-7 cm portion, assuming moisture is roughly uniform within the
     layer). The engine only uses this series through the CAUSAL PERCENTILE
     (rank within its own history from the same source), which absorbs a
     constant bias but not a different dynamic range.
  2. 100 m wind: the forecast API (best_match) exposes wind at 80 m and
     120 m as speed/direction, not u/v at 100 m. We convert each level to
     u/v and take the 80/120 mean (linear interpolation lands exactly on
     100 m); hours where either level is missing yield NaN, which de-arms
     rather than guesses. The tornado bulk-shear feature built on this is
     the LEAST validated transfer of the three.
  3. u/v at 10 m are likewise derived from speed/direction (meteorological
     "blowing from" convention: u = -speed*sin(dir), v = -speed*cos(dir)).

Configuration (frappe.conf, all optional - the public endpoint needs none):
  severe_weather_forecast_url      base URL (default the public forecast API)
  severe_weather_forecast_api_key  appended as apikey= when set (commercial)
  severe_weather_forecast_model    passed as models= when set (e.g.
                                   "ecmwf_ifs025"); default best_match
"""
from __future__ import annotations

import datetime as dt

import numpy as np

from .base import WarningsDataSource
from .openmeteo_s3 import GRID_STEP, N_LAT, N_LON, NBR_HALF, grid_index

DEFAULT_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

#: API bounds (public forecast endpoint).
MAX_PAST_DAYS = 92
MAX_FORECAST_DAYS = 16

#: depth-weighted aggregation of the forecast API's shallow soil layers into
#: an ERA5-style 0-7 cm value (approximation 1 in the module docstring).
SOIL_LAYER_WEIGHTS = (
    ("soil_moisture_0_to_1cm", 1.0),
    ("soil_moisture_1_to_3cm", 2.0),
    ("soil_moisture_3_to_9cm", 4.0),
)

#: wind profile levels averaged to approximate 100 m (approximation 2).
WIND_LEVELS_M = (80, 120)

#: every hourly variable one point request asks the API for.
HOURLY_VARIABLES = (
    "precipitation",
    "soil_moisture_0_to_1cm",
    "soil_moisture_1_to_3cm",
    "soil_moisture_3_to_9cm",
    "pressure_msl",
    "wind_gusts_10m",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_speed_80m",
    "wind_direction_80m",
    "wind_speed_120m",
    "wind_direction_120m",
    "temperature_2m",
    "dew_point_2m",
    "total_column_integrated_water_vapour",
)


def required_past_days(start_utc: dt.datetime, now_utc: dt.datetime) -> int:
    """`past_days` so the API timeline starts at/before start_utc.

    past_days=N makes the hourly timeline begin at 00:00 UTC N days before
    the current UTC day, so covering start_utc needs the full calendar-day
    difference. Clamped to the API bound; a window even deeper than 92 days
    simply yields NaN-padded leading hours (the features then stay NaN there,
    which the detector treats as no information - never a guess).
    """
    days = (now_utc.date() - start_utc.date()).days
    return max(0, min(int(days), MAX_PAST_DAYS))


def required_forecast_days(end_utc: dt.datetime, now_utc: dt.datetime) -> int:
    """`forecast_days` so the API timeline reaches the last hour < end_utc."""
    last_needed = end_utc - dt.timedelta(hours=1)
    days = (last_needed.date() - now_utc.date()).days + 1
    return max(1, min(int(days), MAX_FORECAST_DAYS))


def uv_from_speed_direction(speed_ms, direction_deg):
    """(u, v) m/s from speed + meteorological "blowing from" direction."""
    speed = np.asarray(speed_ms, dtype=np.float64)
    theta = np.deg2rad(np.asarray(direction_deg, dtype=np.float64))
    return -speed * np.sin(theta), -speed * np.cos(theta)


class OpenMeteoForecastSource(WarningsDataSource):
    """Open-Meteo forecast API source (forecast pass only)."""

    name = "openmeteo_forecast"

    def __init__(self):
        import frappe

        self.base_url = (frappe.conf.get("severe_weather_forecast_url")
                         or DEFAULT_FORECAST_URL).strip()
        self.api_key = (frappe.conf.get("severe_weather_forecast_api_key")
                        or "").strip()
        self.model = (frappe.conf.get("severe_weather_forecast_model")
                      or "").strip()

    # -- WarningsDataSource interface ------------------------------------- #

    def data_horizon_utc(self) -> dt.datetime:
        # The API serves through its forecast horizon; the OBSERVED part of
        # its timeline ends at the current hour. The forecast pass owns the
        # forward horizon explicitly, so this stays the honest "now".
        return dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    def hourly_series(self, latitude, longitude, variables, start_utc, end_utc):
        payload = self._request({
            "latitude": float(latitude),
            "longitude": float(longitude),
            "hourly": ",".join(HOURLY_VARIABLES),
        }, start_utc, end_utc)
        hourly = (payload or {}).get("hourly") or {}
        index, n_out = self._time_index(hourly, start_utc, end_utc)

        def col(api_name, factor=1.0):
            return _column(hourly, api_name, index, n_out, factor)

        out = {}
        for var in variables:
            if var == "pressure_msl":
                out[var] = col("pressure_msl", 100.0)   # API hPa -> stored Pa
            elif var == "soil_moisture_0_to_7cm":
                out[var] = _soil_0_to_7cm(col)
            elif var in ("wind_u_component_10m", "wind_v_component_10m"):
                u, v = uv_from_speed_direction(col("wind_speed_10m"),
                                               col("wind_direction_10m"))
                out[var] = u if var.startswith("wind_u") else v
            elif var in ("wind_u_component_100m", "wind_v_component_100m"):
                u, v = _uv_100m(col)
                out[var] = u if var.startswith("wind_u") else v
            elif var in ("precipitation", "wind_gusts_10m", "temperature_2m",
                         "dew_point_2m",
                         "total_column_integrated_water_vapour"):
                out[var] = col(var)
            else:
                raise KeyError(f"no forecast API mapping for variable {var!r}")
        return out

    def neighborhood_precipitation(self, latitude, longitude, start_utc, end_utc):
        """(n_hours, 49) precipitation for the 7x7 box around the point.

        One multi-location call: comma-separated latitude/longitude lists at
        the ERA5 0.25 deg spacing (+-0.75 deg), same cell ordering as the S3
        source (row-major, north-offset rows first). Off-grid latitude rows
        stay NaN; longitude wraps at the date line. NOTE: these are point
        samples the API interpolates from its own model grid - not true
        0.25 deg cell means (documented transfer caveat in FUSION.md).
        """
        la, lo = grid_index(latitude, longitude)
        width = 2 * NBR_HALF + 1
        n_out = int((_floor_hour(end_utc) - _floor_hour(start_utc)
                     ).total_seconds() // 3600)
        cells = np.full((n_out, width * width), np.nan, dtype=np.float64)

        lats, lons, col_ids = [], [], []
        for r in range(width):
            row_la = la + (r - NBR_HALF)
            if row_la < 0 or row_la >= N_LAT:
                continue  # off-grid latitudes stay NaN
            for c in range(width):
                col_lo = (lo + (c - NBR_HALF)) % N_LON
                lats.append(round(row_la * GRID_STEP - 90.0, 2))
                lons.append(round(col_lo * GRID_STEP - 180.0, 2))
                col_ids.append(r * width + c)
        if not lats:
            return cells

        payload = self._request({
            "latitude": ",".join(f"{v:g}" for v in lats),
            "longitude": ",".join(f"{v:g}" for v in lons),
            "hourly": "precipitation",
        }, start_utc, end_utc)
        blocks = payload if isinstance(payload, list) else [payload]
        for block, col_id in zip(blocks, col_ids):
            hourly = (block or {}).get("hourly") or {}
            index, _ = self._time_index(hourly, start_utc, end_utc)
            cells[:, col_id] = _column(hourly, "precipitation", index, n_out)
        return cells

    # -- plumbing --------------------------------------------------------- #

    def _request(self, params, start_utc, end_utc):
        import frappe

        now = self.data_horizon_utc()
        params = dict(params)
        params.update({
            "past_days": required_past_days(start_utc, now),
            "forecast_days": required_forecast_days(end_utc, now),
            "wind_speed_unit": "ms",   # the API default is km/h
            "timezone": "UTC",
        })
        if self.model:
            params["models"] = self.model
        if self.api_key:
            params["apikey"] = self.api_key
        return frappe.make_get_request(self.base_url, params=params)

    @staticmethod
    def _time_index(hourly, start_utc, end_utc):
        """{payload row -> output offset} for hours inside [start, end)."""
        t0, t1 = _floor_hour(start_utc), _floor_hour(end_utc)
        n_out = int((t1 - t0).total_seconds() // 3600)
        index = {}
        for i, stamp in enumerate(hourly.get("time") or []):
            t = dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M")
            off = int((t - t0).total_seconds() // 3600)
            if 0 <= off < n_out:
                index[i] = off
        return index, n_out


def _floor_hour(t: dt.datetime) -> dt.datetime:
    return t.replace(minute=0, second=0, microsecond=0, tzinfo=None)


def _column(hourly, api_name, index, n_out, factor=1.0):
    arr = np.full(n_out, np.nan, dtype=np.float64)
    values = hourly.get(api_name) or []
    for i, off in index.items():
        if i < len(values) and values[i] is not None:
            arr[off] = float(values[i]) * factor
    return arr


def _soil_0_to_7cm(col):
    """Depth-weighted 0-7 cm approximation from the API's shallow layers.

    NaN wherever ANY layer is missing - a partial-depth average would shift
    the causal percentile's distribution mid-series.
    """
    total = None
    weight_sum = 0.0
    for api_name, weight in SOIL_LAYER_WEIGHTS:
        layer = col(api_name) * weight
        total = layer if total is None else total + layer
        weight_sum += weight
    return total / weight_sum


def _uv_100m(col):
    """u/v at 100 m as the mean of the 80 m and 120 m u/v (linear interp).

    NaN where either level is missing: the bulk-shear feature must never be
    computed from a guessed profile (least-validated transfer - docstring).
    """
    u_sum = v_sum = None
    for level in WIND_LEVELS_M:
        u, v = uv_from_speed_direction(col(f"wind_speed_{level}m"),
                                       col(f"wind_direction_{level}m"))
        u_sum = u if u_sum is None else u_sum + u
        v_sum = v if v_sum is None else v_sum + v
    n = float(len(WIND_LEVELS_M))
    return u_sum / n, v_sum / n
