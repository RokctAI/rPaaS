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

"""TENANT-side ack endpoint for severe-weather push notices (sw6).

PINNED CONTRACT (the mobile client emits this fire-and-forget - do not
change shape without a coordinated client release):

  cmd      {app_name}.tenant.api.ack_weather_notice
  payload  {"warning_id": str,
            "event": "delivered" | "seen" | "opened",
            "client_ts": iso-8601 str}
  reply    {"status": "ok"}   - ALWAYS, for any input, any internal state

The endpoint upgrades the caller's Weather Notice Delivery row (written by
the push-sync job at send time) through delivery.record_ack: idempotent and
upgrade-only (opened beats seen beats delivered), so replays and reordered
events are harmless. Unknown warning ids, unknown users, bad events, Guest
sessions, and internal errors are all log-and-200 - a fire-and-forget
client must never see an error for telling us it saw a notice. Rate-sane by
construction: only a strict upgrade writes (at most three writes per
warning x user, ever); everything else is one indexed read.
"""
from __future__ import annotations

import frappe

from ....warnings_engine.admin_log import TITLE_ACK, log_admin_error
from ... import delivery


@frappe.whitelist()
def ack_weather_notice(warning_id=None, event=None, client_ts=None):
    """Record one delivery acknowledgment for the calling user."""
    try:
        user = getattr(getattr(frappe, "session", None), "user", None)
        if not user or user == "Guest":
            return {"status": "ok"}  # anonymous ack: nothing to attribute
        outcome = delivery.record_ack(warning_id, user, event, client_ts)
        if outcome in (delivery.ACK_UNKNOWN, delivery.ACK_BAD_REQUEST,
                       delivery.ACK_ERROR):
            log_admin_error(TITLE_ACK, (
                f"ack_weather_notice {outcome}: user={user!r} "
                f"warning_id={str(warning_id)[:160]!r} "
                f"event={str(event)[:32]!r}"))
        return {"status": "ok"}
    except Exception:
        log_admin_error(TITLE_ACK)
        return {"status": "ok"}
