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

"""CONTROL-side ADMIN endpoints: run and clear severe-weather drills (sw6).

Thin, whitelisted, System-Manager-only wrappers around the drill replay
runner (warnings_engine/drill.py - the module docstring there is the design
reference: what a drill writes, the fail-closed drill fence, the honest
scope/limits of synchronous replay).

run_drill(start_date, end_date, locations, speed):
  * start_date/end_date: ISO dates or datetimes (UTC) bounding the replayed
    archive window; end is clamped to the data source's real horizon.
  * locations: JSON list (or comma-separated string) naming EXISTING watch
    locations - either by name/grid key ("-23.00,30.50") or as "lat,lon"
    coordinates, which are grid-rounded and matched against registered
    cells. Unknown entries are reported back as skipped, never created: a
    drill must not enlarge live evaluator coverage as a side effect.
  * speed: replay pacing in archive-hours per step (default 24 = one step
    per archived day, each step one simulated hourly-evaluator tick).

clear_drill(run_id): delete drill records (one run's, or all when omitted).
Deletion is query-scoped to is_drill=1, so real records are untouchable.

Failure contract: input problems come back as {"error": ..., "ok": false}
with a plain-language reason; internal errors are admin-logged
(rate-limited) and reported the same way - never a traceback.
"""
from __future__ import annotations

import datetime as dt
import json

try:  # composed into the control product
    import frappe
    from ....warnings_engine.admin_log import TITLE_DRILL, log_admin_error
except ImportError:  # standalone/offline reuse
    frappe = None

    def log_admin_error(title, message=None):  # noqa: D103 - stand-in
        pass

    TITLE_DRILL = "SevereWeather: drill replay error"

WATCH_DOCTYPE = "Weather Watch Location"

GRID_STEP = 0.25  # the evaluation grid (see warnings_engine/sources)


def _require_system_manager():
    """Drills write records: any caller without System Manager is refused."""
    roles = set(frappe.get_roles())
    if "System Manager" not in roles:
        raise frappe.PermissionError(
            "run_drill/clear_drill are admin-only (System Manager)")


def _error(reason: str) -> dict:
    return {"ok": False, "error": reason}


def parse_when(value, label: str) -> dt.datetime:
    """ISO date or datetime -> naive UTC datetime; ValueError with the field
    name on anything else. Pure."""
    if isinstance(value, dt.datetime):
        parsed = value
    elif isinstance(value, dt.date):
        parsed = dt.datetime(value.year, value.month, value.day)
    else:
        try:
            parsed = dt.datetime.fromisoformat(
                str(value).strip().replace("Z", "+00:00"))
        except (TypeError, ValueError):
            raise ValueError(f"{label} must be an ISO date or datetime "
                             f"(got {value!r})")
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed.replace(microsecond=0)


def parse_locations(raw) -> list:
    """locations parameter -> list of requested cell keys. Accepts a JSON
    array, a Python list/tuple, or a semicolon-separated string; each entry
    is a watch-location name/grid key or a "lat,lon" pair (grid-rounded to
    the matching cell key). Pure; ValueError on unusable input."""
    if raw is None or raw == "":
        raise ValueError("locations is required (a JSON list of watch "
                         "location names or lat,lon pairs)")
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("["):
            raw = json.loads(text)
        else:
            raw = [part for part in text.split(";") if part.strip()]
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("locations must be a non-empty list")
    keys = []
    for entry in raw:
        key = _cell_key(entry)
        if key not in keys:
            keys.append(key)
    return keys


def _cell_key(entry) -> str:
    """One locations entry -> its grid-cell key string."""
    if isinstance(entry, (list, tuple)) and len(entry) == 2:
        lat, lng = float(entry[0]), float(entry[1])
    elif isinstance(entry, dict):
        lat, lng = float(entry["latitude"]), float(entry["longitude"])
    else:
        text = str(entry).strip()
        parts = text.split(",")
        try:
            lat, lng = float(parts[0]), float(parts[1])
        except (IndexError, ValueError):
            return text  # a watch-location name / grid key as-is
    lat = round(lat / GRID_STEP) * GRID_STEP
    lng = round(lng / GRID_STEP) * GRID_STEP
    return f"{lat:.2f},{lng:.2f}"


def _resolve_locations(keys: list) -> tuple:
    """(existing watch-location rows, skipped keys). Only EXISTING cells
    are drillable - see the module docstring."""
    rows = frappe.get_all(
        WATCH_DOCTYPE,
        filters={"name": ["in", keys]},
        fields=["name", "latitude", "longitude", "label"],
        limit_page_length=0,
    )
    found = {row.name for row in rows}
    return rows, [k for k in keys if k not in found]


def _whitelist(fn):
    return frappe.whitelist()(fn) if frappe is not None else fn


@_whitelist
def run_drill(start_date=None, end_date=None, locations=None, speed=None):
    """Replay an archived window through the live pipeline as a drill.

    System Manager only. Returns the runner's summary (run_id, steps,
    record counts, skipped locations) or {"ok": false, "error": reason}.
    """
    _require_system_manager()
    from ...warnings_engine import drill

    try:
        start = parse_when(start_date, "start_date")
        end = parse_when(end_date, "end_date")
        keys = parse_locations(locations)
    except ValueError as exc:
        return _error(str(exc))
    except Exception:
        log_admin_error(TITLE_DRILL)
        return _error("could not parse the drill parameters")

    try:
        rows, skipped = _resolve_locations(keys)
        if not rows:
            return _error("none of the requested locations is a registered "
                          "watch location - drills only replay cells the "
                          "live engine already covers")
        if len(rows) > drill.MAX_LOCATIONS:
            return _error(f"at most {drill.MAX_LOCATIONS} locations per "
                          "drill run")
        summary = drill.run_drill_replay(rows, start, end, step_hours=speed)
        summary["ok"] = True
        summary["skipped_locations"] = skipped
        return summary
    except ValueError as exc:  # clamp_window's plain-language refusals
        return _error(str(exc))
    except Exception:
        log_admin_error(TITLE_DRILL)
        return _error("drill run failed - see the Error Log entry titled "
                      f"{TITLE_DRILL!r}")


@_whitelist
def clear_drill(run_id=None):
    """Delete drill records (one run's, or ALL drill records when run_id is
    omitted). System Manager only; can never touch a real record."""
    _require_system_manager()
    from ...warnings_engine import drill

    try:
        deleted = drill.clear_drill_records(
            str(run_id).strip() if run_id else None)
        return {"ok": True, "deleted": deleted,
                "run_id": run_id or "all"}
    except Exception:
        log_admin_error(TITLE_DRILL)
        return _error("clear_drill failed - see the Error Log entry titled "
                      f"{TITLE_DRILL!r}")
