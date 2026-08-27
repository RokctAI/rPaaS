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

"""The single notification seam for TenderAssist outbound comms (plan #14).

Before this module, outbound comms were two direct ``frappe.sendmail`` call
sites (the weekly compliance-artifact expiry email and bid-pack dispatch),
each carrying its own copy of the graceful-degradation pattern. Every
feature that notifies now goes through :func:`notify` instead, so that
pattern - try/except around the send, ``log_error`` on failure, success
reported to the caller so audit writes happen ONLY on an accepted send -
lives in exactly one place.

Channel-pluggable by registry: ``email`` is the only channel today and it
makes the exact ``frappe.sendmail(recipients=..., subject=..., message=...,
attachments=...)`` call the prior call sites made - behaviour-identical
wiring, not a behaviour change. A future channel (the core ``comms``
module, in-app, SMS) plugs in via :func:`register_channel` instead of
copying a new sendmail call site per feature.

Opt-in stays where it was: user-facing notifications pass
``require_opt_in=True`` and are gated per recipient on the
``User.receive_tender_notifications`` custom field (missing-safe, exactly
the artifact-expiry check). Buyer-facing dispatch mail is caller-confirmed
(the retype-to-confirm gate) and never opt-in-gated - unchanged.

Stub-safe by construction: imports only ``frappe`` + ``frappe.utils.cint``
at module top, no ``{app_name}`` placeholder, so the verify suites load it
by file path against their in-memory frappe stub.
"""

import frappe
from frappe.utils import cint

CHANNEL_EMAIL = "email"
DEFAULT_FAILURE_LOG_TITLE = "Tender Notification Failed"


def _send_email(recipients, subject, message, attachments=None):
	"""The email channel: the exact frappe.sendmail call the two prior
	direct call sites (artifact_expiry, dispatch_bid_pack) made."""
	frappe.sendmail(
		recipients=recipients,
		subject=subject,
		message=message,
		attachments=attachments,
	)


# Channel registry: name -> sender(recipients, subject, message, attachments).
# Email is the only built-in; future channels register instead of adding
# new direct call sites.
_CHANNELS = {CHANNEL_EMAIL: _send_email}


def register_channel(name, sender):
	"""Plugs a notification channel into the seam.

	``sender`` is called as ``sender(recipients=..., subject=...,
	message=..., attachments=...)`` and signals failure by raising -
	notify() owns the try/except + log_error degradation for every channel.
	Registering an existing name replaces it (deliberate: a composed bench
	may swap the email transport).
	"""
	_CHANNELS[str(name)] = sender


def registered_channels():
	"""The currently registered channel names (introspection/verify use)."""
	return sorted(_CHANNELS)


def wants_notifications(user):
	"""The User.receive_tender_notifications opt-in, missing-safe.

	Moved verbatim from artifact_expiry.py so every user-facing
	notification shares the one gate. Any failure (field not installed,
	no db) reads as NOT opted in - never a traceback, never a surprise
	email.
	"""
	try:
		return cint(frappe.db.get_value("User", user, "receive_tender_notifications"))
	except Exception:
		return False


def notify(
	recipients,
	subject,
	message,
	attachments=None,
	channel=CHANNEL_EMAIL,
	require_opt_in=False,
	failure_log_title=DEFAULT_FAILURE_LOG_TITLE,
):
	"""Sends one notification through the named channel, degrading gracefully.

	Returns a dict, never raises:

	- ``{"sent": True, "channel": ..., "recipients": [...]}`` on an
	  accepted send - the ONLY outcome on which callers may write audit
	  fields (the dispatch discipline);
	- ``{"sent": False, ..., "reason": "no-recipients"}`` when nothing is
	  addressable (empty list, or every recipient opted out under
	  ``require_opt_in``) - nothing is sent and nothing is logged, exactly
	  the old per-call-site skip;
	- ``{"sent": False, ..., "reason": "unknown-channel"}`` when no sender
	  is registered under ``channel`` - logged, not raised;
	- ``{"sent": False, ..., "reason": "send-failed"}`` when the channel
	  raised (e.g. no outgoing Email Account on the bench) - the failure is
	  logged under ``failure_log_title`` so each call site keeps its own
	  recognizable error-log title.
	"""
	recipients = [r for r in (recipients or []) if r]
	if require_opt_in:
		recipients = [r for r in recipients if wants_notifications(r)]
	if not recipients:
		return {
			"sent": False,
			"channel": channel,
			"recipients": [],
			"reason": "no-recipients",
		}

	sender = _CHANNELS.get(channel)
	if sender is None:
		_log_failure(
			f"No notification channel registered under '{channel}' - "
			f"registered: {', '.join(registered_channels())}",
			failure_log_title,
		)
		return {
			"sent": False,
			"channel": channel,
			"recipients": recipients,
			"reason": "unknown-channel",
		}

	try:
		sender(
			recipients=recipients,
			subject=subject,
			message=message,
			attachments=attachments,
		)
	except Exception:
		_log_failure(_traceback_text(), failure_log_title)
		return {
			"sent": False,
			"channel": channel,
			"recipients": recipients,
			"reason": "send-failed",
		}

	return {
		"sent": True,
		"channel": channel,
		"recipients": recipients,
		"reason": None,
	}


def _traceback_text():
	"""frappe.get_traceback, guarded - the seam must never raise."""
	try:
		return frappe.get_traceback()
	except Exception:
		return "traceback unavailable"


def _log_failure(text, title):
	"""frappe.log_error, guarded - logging must never break the caller."""
	try:
		frappe.log_error(text, title)
	except Exception:
		pass
