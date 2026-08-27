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

"""TENANT-side acknowledge link target for the escalation ladder (sw6).

Escalation contacts are notified by email/SMS and may not have a login, so
this endpoint is guest-reachable and authenticates by the single-use opaque
token minted per escalation step (stored on the contact's Weather Notice
Delivery row). A valid token acks that row (event "opened") which stops any
further escalation for the warning; unknown or replayed tokens are
log-and-200. The token authorizes exactly one thing - marking one notice
step acknowledged - and leaks nothing: the response carries no warning
details.
"""
from __future__ import annotations

import frappe

from ....warnings_engine.admin_log import TITLE_ACK, log_admin_error
from ... import delivery

#: end-user-facing confirmation strings (SAWS-safe: calm, no official
#: taxonomy). Kept here, next to the only surface that shows them.
ACK_THANKS = "Thank you. This notice is now marked as being handled."
ACK_ALREADY = "This notice was already acknowledged."


@frappe.whitelist(allow_guest=True)
def ack_weather_escalation(token=None):
    """Acknowledge one escalation step by its emailed/SMSed token."""
    try:
        outcome = delivery.record_escalation_ack(token)
        if outcome == delivery.ACK_NOOP:
            return {"status": "ok", "message": ACK_ALREADY}
        if outcome != delivery.ACK_RECORDED:
            log_admin_error(TITLE_ACK,
                            f"ack_weather_escalation {outcome}: "
                            f"token={str(token)[:8]!r}...")
        return {"status": "ok", "message": ACK_THANKS}
    except Exception:
        log_admin_error(TITLE_ACK)
        return {"status": "ok", "message": ACK_THANKS}
