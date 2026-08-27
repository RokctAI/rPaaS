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

"""Data-source abstraction for the severe-weather evaluator.

One tiny interface, two implementations, switched by tenant site config
(mirroring how get_weather reads frappe.conf):

  "severe_weather_source": "openmeteo_s3" (default) | "openmeteo_api"
  "openmeteo_api_url":    API base URL   (openmeteo_api only)
  "openmeteo_api_key":    API key        (openmeteo_api only)

Unknown values fall back to the default source; a selected-but-unconfigured
API source logs once (rate-limited) and falls back to S3 - never a
user-visible failure. No credentials are ever hardcoded.

All sources return hourly series in the ERA5 storage units (see the S3
source module) so the feature computation is source-independent.
"""
from __future__ import annotations


class SourceNotConfigured(Exception):
    """Raised by a source whose site-config prerequisites are missing."""


class WarningsDataSource:
    """Interface every warnings data source implements."""

    #: identifier used in logs / precursor records
    name = "base"

    def hourly_series(self, latitude, longitude, variables, start_utc, end_utc):
        """{variable: numpy float array} hourly over [start_utc, end_utc),
        at the grid cell nearest (latitude, longitude), NaN where the source
        has no data. Units: ERA5 storage units."""
        raise NotImplementedError

    def neighborhood_precipitation(self, latitude, longitude, start_utc, end_utc):
        """(n_hours, n_cells) precipitation (mm/h) for the 7x7 grid box
        around the point, or None when the source cannot provide it (the
        flash_flood neighborhood conditions then simply never arm)."""
        raise NotImplementedError

    def data_horizon_utc(self):
        """Last datetime (UTC, hour precision) the source has data for.
        Used by the evaluator's freshness short-circuit."""
        raise NotImplementedError


def get_data_source():
    """Resolve the configured source; fall back to the S3 default on any
    configuration problem (rate-limited admin log, no user-visible failure)."""
    import frappe

    from ....warnings_engine.admin_log import TITLE_SOURCE_CONFIG, log_admin_error
    from .openmeteo_s3 import OpenMeteoS3Source

    selected = (frappe.conf.get("severe_weather_source") or "openmeteo_s3").strip()
    if selected == "openmeteo_api":
        try:
            from .openmeteo_api import OpenMeteoApiSource
            return OpenMeteoApiSource()
        except SourceNotConfigured as exc:
            log_admin_error(
                TITLE_SOURCE_CONFIG,
                f"severe_weather_source=openmeteo_api but {exc}; "
                "falling back to openmeteo_s3.",
            )
    return OpenMeteoS3Source()
