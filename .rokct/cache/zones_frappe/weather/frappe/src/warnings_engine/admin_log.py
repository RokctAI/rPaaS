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

"""Rate-limited admin diagnostics for the severe-weather feature.

Everything admin-facing goes to Frappe's built-in Error Log (the mechanism
every zones module already uses) under STABLE titles - the grep keys admins
use in the desk Error Log list:

  "SevereWeather: source fetch failed"
  "SevereWeather: data source not configured"
  "SevereWeather: evaluation failed"
  "SevereWeather: warnings API error"
  "SevereWeather: detector config invalid"
  "SevereWeather: push delivery failed"
  "SevereWeather: outcome recorded"
  "SevereWeather: outcome pass failed"
  "SevereWeather: retraining report error"
  "SevereWeather: basin routing failed"   (title lives in basin.py)
  "SevereWeather: ack tracking error"
  "SevereWeather: sms fallback failed"
  "SevereWeather: escalation failed"
  "SevereWeather: CAP feed error"
  "SevereWeather: drill replay error"
  "SevereWeather: site notice pass failed"

The evaluator runs hourly on both shell products, so each title is
rate-limited (at most one entry per title per RATE_LIMIT_SECONDS) to keep the
Error Log useful. End users NEVER see any of this - the client-facing failure
contract is an empty warnings list.
"""
from __future__ import annotations

import re

import frappe

RATE_LIMIT_SECONDS = 6 * 3600  # at most one Error Log entry per title per 6 h

TITLE_SOURCE_FETCH = "SevereWeather: source fetch failed"
TITLE_SOURCE_CONFIG = "SevereWeather: data source not configured"
TITLE_EVALUATION = "SevereWeather: evaluation failed"
TITLE_API = "SevereWeather: warnings API error"
TITLE_DETECTOR_CONFIG = "SevereWeather: detector config invalid"
TITLE_PUSH = "SevereWeather: push delivery failed"
TITLE_OUTCOME = "SevereWeather: outcome recorded"
TITLE_OUTCOME_PASS = "SevereWeather: outcome pass failed"
TITLE_RETRAIN_REPORT = "SevereWeather: retraining report error"
TITLE_ACK = "SevereWeather: ack tracking error"
TITLE_SMS = "SevereWeather: sms fallback failed"
TITLE_ESCALATION = "SevereWeather: escalation failed"
TITLE_CAP_FEED = "SevereWeather: CAP feed error"
TITLE_DRILL = "SevereWeather: drill replay error"
TITLE_SITES = "SevereWeather: site notice pass failed"


def log_admin_error(title: str, message: str | None = None) -> None:
    """frappe.log_error under a stable title, at most once per rate window.

    Never raises: diagnostics must not break the caller's failure contract.
    """
    try:
        key = "sww_ratelimit_" + re.sub(r"[^a-z0-9]+", "_", title.lower())
        cache = frappe.cache()
        if cache.get_value(key):
            return
        cache.set_value(key, 1, expires_in_sec=RATE_LIMIT_SECONDS)
        frappe.log_error(message or frappe.get_traceback(), title)
    except Exception:
        pass
