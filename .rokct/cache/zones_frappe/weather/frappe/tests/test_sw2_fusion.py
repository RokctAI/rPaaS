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

"""Offline tests for wave-2 forecast fusion (warnings_engine/fusion.py).

Pure unit tests: frappe is stubbed when no bench is available and no network
is touched (forecast payloads are weatherapi.com-shaped fixtures injected via
fuse_warning's `fetch` parameter), so they run with `python3 -m unittest`
anywhere.
"""

import calendar
import datetime as dt
import importlib
import importlib.util
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
    """Install a minimal frappe stub when no bench is available."""
    try:
        import frappe  # noqa: F401
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

    utils_mod.cint = cint
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
fusion = importlib.import_module("wmod.control.warnings_engine.fusion")
messages = importlib.import_module("wmod.warnings_engine.messages")
evaluator = importlib.import_module("wmod.control.warnings_engine.evaluator")

import frappe  # noqa: E402  (stub or real, after the loader)


# --------------------------------------------------------------------------- #
# fixture helpers (weatherapi.com payload shape)
# --------------------------------------------------------------------------- #

def _epoch(when_utc):
    return calendar.timegm(when_utc.timetuple())


def make_payload(hours, tz_id="Africa/Johannesburg", wrap=False):
    """Build a weatherapi.com-shaped payload from [(utc_dt, mm, gust), ...]."""
    by_date = {}
    for when, precip, gust in hours:
        entry = {
            "time_epoch": _epoch(when),
            "time": when.strftime("%Y-%m-%d %H:%M"),
            "precip_mm": precip,
            "wind_kph": (gust or 0) * 0.7,
            "gust_kph": gust,
            "temp_c": 20.0,
        }
        by_date.setdefault(when.strftime("%Y-%m-%d"), []).append(entry)
    payload = {
        "location": ({"tz_id": tz_id} if tz_id else {}),
        "current": {"precip_mm": 0.0},
        "forecast": {"forecastday": [
            {"date": date,
             "day": {"totalprecip_mm": sum(h["precip_mm"] or 0 for h in hrs)},
             "hour": hrs}
            for date, hrs in sorted(by_date.items())
        ]},
    }
    return {"message": payload} if wrap else payload


def flat_hours(start_utc, count, precip=0.0, gust=10.0):
    return [(start_utc + dt.timedelta(hours=i), precip, gust)
            for i in range(count)]


def loc(label="Testville", lat=-25.75, lng=28.25):
    return types.SimpleNamespace(label=label, latitude=lat, longitude=lng)


#: fixed reference instant: Tuesday 2026-08-18 12:00 UTC.
NOW = dt.datetime(2026, 8, 18, 12, 0)


class FusionCase(unittest.TestCase):
    def setUp(self):
        self._saved_flag = frappe.conf.pop(fusion.SITE_CONFIG_FLAG, None) \
            if isinstance(frappe.conf, dict) else None

    def tearDown(self):
        if isinstance(frappe.conf, dict):
            frappe.conf.pop(fusion.SITE_CONFIG_FLAG, None)
            if self._saved_flag is not None:
                frappe.conf[fusion.SITE_CONFIG_FLAG] = self._saved_flag

    # ---------------------------------------------------------------- flag

    def test_flag_off_skips_fusion_and_fetch(self):
        frappe.conf[fusion.SITE_CONFIG_FLAG] = 0
        fetch = MagicMock()
        severity, rendered, meta = fusion.fuse_warning(
            loc(), "flood", "heads_up", 0.9, NOW, fetch=fetch)
        fetch.assert_not_called()
        self.assertEqual(severity, "heads_up")
        self.assertEqual(rendered, messages.render("flood", "heads_up", "Testville"))
        self.assertIsNone(meta)

    def test_flag_default_is_on(self):
        self.assertTrue(fusion.fusion_enabled())
        for off in (0, "0", "false", "off", "no"):
            frappe.conf[fusion.SITE_CONFIG_FLAG] = off
            self.assertFalse(fusion.fusion_enabled(), repr(off))
        frappe.conf[fusion.SITE_CONFIG_FLAG] = "1"
        self.assertTrue(fusion.fusion_enabled())

    # ------------------------------------------------------------- failure

    def test_fetch_failure_falls_back_silently_and_logs(self):
        def boom(query):
            raise RuntimeError("control plane down")
        frappe.cache.return_value.get_value.return_value = None  # rate limit open
        frappe.log_error.reset_mock()
        severity, rendered, meta = fusion.fuse_warning(
            loc(), "flash_flood", "heads_up", 0.9, NOW, fetch=boom)
        self.assertEqual(severity, "heads_up")
        self.assertEqual(rendered,
                         messages.render("flash_flood", "heads_up", "Testville"))
        self.assertIsNone(meta)
        titles = [call.args[1] for call in frappe.log_error.call_args_list]
        self.assertIn(fusion.TITLE_FUSION, titles)

    def test_garbage_payload_falls_back(self):
        for junk in (None, "nope", [], {"forecast": {}}, {"message": "x"}):
            severity, rendered, meta = fusion.fuse_warning(
                loc(), "flood", "heads_up", 0.9, NOW, fetch=lambda q, j=junk: j)
            self.assertEqual(severity, "heads_up")
            self.assertIsNone(meta)

    # -------------------------------------------------------------- timing

    def test_timing_on_weekday_with_timezone(self):
        # heavy rain Thursday afternoon local (America/New_York), 2 days out
        hours = flat_hours(NOW, 60, precip=0.2)
        heavy_start = dt.datetime(2026, 8, 20, 18, 0)  # Thu 14:00 EDT
        hours = [(w, 8.0 if w >= heavy_start else p, g) for w, p, g in hours]
        payload = make_payload(hours, tz_id="America/New_York")
        severity, rendered, meta = fusion.fuse_warning(
            loc(), "flood", "heads_up", 0.3, NOW, fetch=lambda q: payload)
        self.assertEqual(severity, "heads_up")  # confidence below upgrade bar
        self.assertIn("heavy rain forecast on Thursday", rendered["headline"])
        self.assertIn("arriving on Thursday.", rendered["message"])
        self.assertEqual(meta["timing"], "on Thursday")
        self.assertEqual(meta["tz"], "America/New_York")

    def test_timing_later_today_and_tomorrow(self):
        # heavy rain 3 h from now, same local day (UTC+2)
        hours = flat_hours(NOW, 24, precip=0.0)
        hours[3] = (hours[3][0], 12.0, 10.0)
        payload = make_payload(hours, tz_id="Africa/Johannesburg")
        _s, rendered, meta = fusion.fuse_warning(
            loc(), "flash_flood", "heads_up", 0.2, NOW, fetch=lambda q: payload)
        self.assertEqual(meta["timing"], "later today")
        self.assertIn("later today", rendered["message"])

        # heavy rain next local day
        hours = flat_hours(NOW, 30, precip=0.0)
        hours[20] = (hours[20][0], 12.0, 10.0)  # 2026-08-19 08:00 UTC
        payload = make_payload(hours, tz_id="Africa/Johannesburg")
        _s, rendered, meta = fusion.fuse_warning(
            loc(), "flash_flood", "heads_up", 0.2, NOW, fetch=lambda q: payload)
        self.assertEqual(meta["timing"], "tomorrow")

    def test_timing_without_timezone_uses_around_weekday(self):
        hours = flat_hours(NOW, 60, precip=0.0)
        hours[50] = (hours[50][0], 12.0, 10.0)  # Thu 2026-08-20 14:00 UTC
        payload = make_payload(hours, tz_id=None)
        _s, rendered, meta = fusion.fuse_warning(
            loc(), "flood", "heads_up", 0.2, NOW, fetch=lambda q: payload)
        self.assertEqual(meta["timing"], "around Thursday")
        self.assertIn("around Thursday", rendered["headline"])

    def test_wind_timing_uses_gusts(self):
        hours = flat_hours(NOW, 30, precip=0.0, gust=20.0)
        hours[22] = (hours[22][0], 0.0, 120.0)  # strong gusts tomorrow
        payload = make_payload(hours, tz_id="Africa/Johannesburg")
        severity, rendered, meta = fusion.fuse_warning(
            loc(), "destructive_wind", "heads_up", 0.9, NOW,
            fetch=lambda q: payload)
        self.assertEqual(severity, "heads_up")  # wind never upgrades
        self.assertIn("strong winds forecast tomorrow", rendered["headline"])
        self.assertIn("strongest winds arriving tomorrow.", rendered["message"])

    # ------------------------------------------------------------- upgrade

    def test_flood_upgrade_heads_up_to_warning(self):
        hours = flat_hours(NOW, 48, precip=4.0)  # 96 mm / 24 h
        payload = make_payload(hours)
        severity, rendered, meta = fusion.fuse_warning(
            loc(), "flood", "heads_up", 0.60, NOW, fetch=lambda q: payload)
        self.assertEqual(severity, "warning")
        self.assertEqual(meta["adjusted_from"], "heads_up")
        self.assertEqual(rendered["severity"], "warning")
        self.assertEqual(rendered["headline"].split(" - ")[0],
                         messages.render("flood", "warning", "Testville")["headline"])

    def test_no_upgrade_below_confidence_bar(self):
        hours = flat_hours(NOW, 48, precip=4.0)
        payload = make_payload(hours)
        severity, _r, _m = fusion.fuse_warning(
            loc(), "flood", "heads_up", fusion.UPGRADE_MIN_CONFIDENCE - 0.05,
            NOW, fetch=lambda q: payload)
        self.assertEqual(severity, "heads_up")

    def test_no_upgrade_below_rain_bar(self):
        hours = flat_hours(NOW, 48, precip=1.0)  # 24 mm / 24 h < 50
        payload = make_payload(hours)
        severity, _r, _m = fusion.fuse_warning(
            loc(), "flood", "heads_up", 0.9, NOW, fetch=lambda q: payload)
        self.assertEqual(severity, "heads_up")

    def test_warning_severity_never_exceeded(self):
        hours = flat_hours(NOW, 48, precip=20.0)  # extreme forecast
        payload = make_payload(hours)
        severity, _r, _m = fusion.fuse_warning(
            loc(), "flash_flood", "warning", 0.99, NOW, fetch=lambda q: payload)
        self.assertEqual(severity, "warning")

    # ---------------------------------------------- never suppress/downgrade

    def test_dry_forecast_softens_but_never_downgrades(self):
        hours = flat_hours(NOW, 48, precip=0.0)
        payload = make_payload(hours)
        severity, rendered, meta = fusion.fuse_warning(
            loc(), "flood", "warning", 0.7, NOW, fetch=lambda q: payload)
        self.assertEqual(severity, "warning")  # observed episode untouched
        self.assertTrue(meta["softened"])
        self.assertIn("conditions can change quickly", rendered["message"])
        base = messages.render("flood", "warning", "Testville")
        self.assertTrue(rendered["message"].startswith(base["message"]))
        self.assertEqual(rendered["headline"], base["headline"])

    def test_short_forecast_cannot_be_called_dry(self):
        hours = flat_hours(NOW, 8, precip=0.0)  # only 8 h of forecast
        payload = make_payload(hours)
        severity, rendered, meta = fusion.fuse_warning(
            loc(), "flood", "warning", 0.7, NOW, fetch=lambda q: payload)
        self.assertEqual(severity, "warning")
        self.assertIsNone(meta)  # nothing fused
        self.assertEqual(rendered, messages.render("flood", "warning", "Testville"))

    # ------------------------------------------------------------- tornado

    def test_tornado_is_untouched_and_never_fetches(self):
        fetch = MagicMock()
        severity, rendered, meta = fusion.fuse_warning(
            loc(), "tornado", "heads_up", 0.9, NOW, fetch=fetch)
        fetch.assert_not_called()
        self.assertEqual(severity, "heads_up")
        self.assertEqual(rendered, messages.render("tornado", "heads_up", "Testville"))
        self.assertIsNone(meta)

    # ---------------------------------------------------------- unit sanity

    def test_absurd_values_are_discarded(self):
        hours = flat_hours(NOW, 48, precip=0.0)
        hours[5] = (hours[5][0], 10000.0, 10.0)   # corrupt rain value
        hours[6] = (hours[6][0], -3.0, 900.0)     # negative rain, absurd gust
        payload = make_payload(hours)
        severity, rendered, meta = fusion.fuse_warning(
            loc(), "flood", "heads_up", 0.9, NOW, fetch=lambda q: payload)
        self.assertEqual(severity, "heads_up")    # no upgrade from garbage
        self.assertNotIn("heaviest rain arriving", rendered["message"])
        if meta is not None:                       # softening may legitimately fire
            self.assertNotIn("timing", meta)

    def test_short_horizon_no_upgrade(self):
        hours = flat_hours(NOW, 4, precip=30.0)   # 120 mm but only 4 h of data
        payload = make_payload(hours)
        severity, _r, _m = fusion.fuse_warning(
            loc(), "flood", "heads_up", 0.9, NOW, fetch=lambda q: payload)
        self.assertEqual(severity, "heads_up")    # span < MIN_FORECAST_HOURS

    # ----------------------------------------------------------- envelopes

    def test_wrapped_message_envelope_is_unwrapped(self):
        hours = flat_hours(NOW, 48, precip=4.0)
        payload = make_payload(hours, wrap=True)
        severity, _r, meta = fusion.fuse_warning(
            loc(), "flood", "heads_up", 0.9, NOW, fetch=lambda q: payload)
        self.assertEqual(severity, "warning")
        self.assertEqual(meta["adjusted_from"], "heads_up")

    # ------------------------------------------------------------ copy law

    def test_no_user_facing_string_contains_the_word_warning(self):
        scenarios = [
            ("flood", "heads_up", flat_hours(NOW, 48, precip=4.0)),        # upgrade
            ("flash_flood", "warning", flat_hours(NOW, 48, precip=0.0)),   # soften
            ("destructive_wind", "heads_up",
             [(w, 0.0, 120.0) for w, _p, _g in flat_hours(NOW, 30)]),      # timing
        ]
        for event_class, severity, hours in scenarios:
            payload = make_payload(hours)
            _s, rendered, _m = fusion.fuse_warning(
                loc(), event_class, severity, 0.9, NOW, fetch=lambda q: payload)
            for key in ("headline", "message", "severity_label"):
                self.assertNotIn("warning", rendered[key].lower(),
                                 f"{event_class}/{severity}/{key}")

    # -------------------------------------------------------------- wiring

    def test_evaluator_is_wired_to_fusion(self):
        self.assertIs(evaluator.fusion, fusion)
        self.assertTrue(callable(fusion.fuse_warning))


class TimingPhraseCase(unittest.TestCase):
    def test_weekday_names_are_locale_safe(self):
        self.assertEqual(len(fusion.WEEKDAY_NAMES), 7)
        self.assertEqual(fusion.WEEKDAY_NAMES[dt.date(2026, 8, 20).weekday()],
                         "Thursday")

    def test_local_calendar_crosses_utc_midnight(self):
        # 23:00 UTC today is already "tomorrow" in UTC+2
        now = dt.datetime(2026, 8, 18, 12, 0)
        when = dt.datetime(2026, 8, 18, 23, 0)
        self.assertEqual(
            fusion._timing_phrase(when, now, "Africa/Johannesburg"), "tomorrow")
        self.assertEqual(fusion._timing_phrase(when, now, None),
                         "around Tuesday")

    def test_unresolvable_timezone_falls_back_to_around(self):
        now = dt.datetime(2026, 8, 18, 12, 0)
        when = dt.datetime(2026, 8, 21, 6, 0)
        self.assertEqual(fusion._timing_phrase(when, now, "Not/AZone"),
                         "around Friday")


if __name__ == "__main__":
    unittest.main()
