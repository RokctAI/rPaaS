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

"""Config-switchable warnings data source: the commercial Open-Meteo API.

STUB implementation of the lag-free path (site config
severe_weather_source = "openmeteo_api"). It is wired, validated, and safe -
but intentionally minimal until a commercial plan exists:

  - "openmeteo_api_url" and "openmeteo_api_key" MUST come from tenant site
    config (frappe.conf). Nothing is hardcoded; a missing value raises
    SourceNotConfigured and the factory falls back to the S3 source with a
    rate-limited admin log. No credentials live in this repository.
  - hourly_series() calls the configured base URL with the standard
    Open-Meteo query shape via frappe.make_get_request (the get_weather
    pattern) and converts returned units to the ERA5 storage units the
    feature module expects (API pressure_msl is hPa -> Pa).
  - neighborhood_precipitation() returns None (the flash_flood neighborhood
    conditions simply never arm on this source).
  - The frozen detector was tuned on ERA5; feature transfer to API "best
    match" model data is NOT yet validated. Enabling this source is a
    deliberate operator decision, not a default.
"""
from __future__ import annotations

import datetime as dt

from .base import SourceNotConfigured, WarningsDataSource

#: ERA5 storage-unit variable -> (API hourly variable, multiplier to ERA5 units)
API_VARIABLE_MAP = {
    "precipitation": ("precipitation", 1.0),
    "soil_moisture_0_to_7cm": ("soil_moisture_0_to_7cm", 1.0),
    "pressure_msl": ("pressure_msl", 100.0),  # API hPa -> stored Pa
    "wind_gusts_10m": ("wind_gusts_10m", 1.0),
    "wind_u_component_10m": ("wind_u_component_10m", 1.0),
    "wind_v_component_10m": ("wind_v_component_10m", 1.0),
    "wind_u_component_100m": ("wind_u_component_100m", 1.0),
    "wind_v_component_100m": ("wind_v_component_100m", 1.0),
    "temperature_2m": ("temperature_2m", 1.0),
    "dew_point_2m": ("dew_point_2m", 1.0),
    "total_column_integrated_water_vapour":
        ("total_column_integrated_water_vapour", 1.0),
}


class OpenMeteoApiSource(WarningsDataSource):
    """Open-Meteo commercial API source (stub; requires site config)."""

    name = "openmeteo_api"

    def __init__(self):
        import frappe

        self.base_url = (frappe.conf.get("openmeteo_api_url") or "").strip()
        self.api_key = (frappe.conf.get("openmeteo_api_key") or "").strip()
        if not self.base_url:
            raise SourceNotConfigured("openmeteo_api_url is not set in site config")
        if not self.api_key:
            raise SourceNotConfigured("openmeteo_api_key is not set in site config")

    def data_horizon_utc(self) -> dt.datetime:
        # The API serves near-real-time analysis: horizon = the current hour.
        return dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    def hourly_series(self, latitude, longitude, variables, start_utc, end_utc):
        import frappe
        import numpy as np

        api_names = []
        for var in variables:
            if var not in API_VARIABLE_MAP:
                raise KeyError(f"no API mapping for variable {var!r}")
            api_names.append(API_VARIABLE_MAP[var][0])

        params = {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "hourly": ",".join(api_names),
            "start_date": start_utc.strftime("%Y-%m-%d"),
            "end_date": (end_utc - dt.timedelta(hours=1)).strftime("%Y-%m-%d"),
            "timezone": "UTC",
            "apikey": self.api_key,
        }
        payload = frappe.make_get_request(self.base_url, params=params)
        hourly = (payload or {}).get("hourly") or {}
        times = hourly.get("time") or []

        n_out = int((end_utc - start_utc).total_seconds() // 3600)
        index = {}
        for i, stamp in enumerate(times):
            t = dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M")
            off = int((t - start_utc).total_seconds() // 3600)
            if 0 <= off < n_out:
                index[i] = off

        out = {}
        for var in variables:
            api_name, factor = API_VARIABLE_MAP[var]
            arr = np.full(n_out, np.nan, dtype=np.float64)
            values = hourly.get(api_name) or []
            for i, off in index.items():
                if i < len(values) and values[i] is not None:
                    arr[off] = float(values[i]) * factor
            out[var] = arr
        return out

    def neighborhood_precipitation(self, latitude, longitude, start_utc, end_utc):
        return None  # not available from the point API; nbr conditions stay off
