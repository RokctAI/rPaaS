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

"""Bid deadline watcher (plan #10) - the daily clock on claimed bids.

Every claimed Tender Bid carries a closing_date, an active status
(Watching / Preparing) and open-gate state, but until this sweep nothing
watched the clock: the only scheduled user notification was the weekly
compliance-artifact expiry email. This daily sweep (module manifest, the
artifact_expiry.py scheduling convention) attacks the #1 real-world kill
rule - KILL-01, late = cannot be admitted - while there is still time:

- bids in an active status closing within N days that STILL carry open
  compliance work - the submission-gate failure list (open Fatal checklist
  items, missing/expired compliance artifacts, functionality eliminations,
  unattested generated artifacts) plus mandatory returnables with no
  artifact attached yet - are emailed to their owner. A bid inside the
  window with nothing open sends nothing: the reminder is for work left,
  not for having claimed a tender;
- briefing reminders BEFORE the briefing: suitability already gates on
  MISSED compulsory briefings post-mortem; here the cached published
  catalog card for the bid's slug is checked for a real upcoming
  briefing_date_and_time inside the same window and reminded in advance -
  the save instead of the post-mortem. Registry placeholder dates
  (0001-01-01) are never treated as a real briefing (the positive-evidence
  rule), and an absent/expired catalog cache simply means no briefing
  reminders this run - the cache is read, never refreshed here.

N = Tender Control Settings.deadline_watch_days (default 7 when unset).
Sending goes through the notify() seam (plan #14) with the same
User.receive_tender_notifications opt-in gate as the artifact-expiry
email. Date arithmetic only, no AI, no network.
"""

import datetime

import frappe
from frappe.utils import cint, nowdate

# Same-package imports (F-09): the relative imports work on a composed
# bench; the importlib fallback keeps this module importable standalone by
# file path, matching the proven submission_gate.py pattern.
try:
	from .submission_gate import validate_submission_readiness
	from .suitability import is_placeholder_date, parse_card_datetime
	from ..notify import notify
except ImportError:  # standalone by-path import - load the siblings directly
	import importlib.util as _importlib_util
	import os as _os

	def _load_sibling(_module_name, _filename):
		_spec = _importlib_util.spec_from_file_location(
			_module_name,
			_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), _filename),
		)
		_module = _importlib_util.module_from_spec(_spec)
		_spec.loader.exec_module(_module)
		return _module

	_gate = _load_sibling("tender_deadline_watch_gate", "submission_gate.py")
	_suitability = _load_sibling("tender_deadline_watch_suitability", "suitability.py")
	_notify_module = _load_sibling(
		"tender_deadline_watch_notify", _os.path.join("..", "notify.py")
	)
	validate_submission_readiness = _gate.validate_submission_readiness
	is_placeholder_date = _suitability.is_placeholder_date
	parse_card_datetime = _suitability.parse_card_datetime
	notify = _notify_module.notify

DEFAULT_DEADLINE_WATCH_DAYS = 7

# Statuses with a live clock: Watching / Preparing. Submitted is out of the
# user's hands; Awarded / Lost / Withdrawn have no deadline left to save.
ACTIVE_STATUSES = ("Watching", "Preparing")

# The published-catalog cache key get_cached_opportunities maintains
# (f"opp_data_{opt_type}") - read here for briefing dates, never refreshed.
CATALOG_CACHE_KEY = "opp_data_tenders"  # compliance-ignore: py-hardcoded-secret (Redis cache-key name, not a credential)

NOTIFICATION_SUBJECT = "Tender deadlines are coming up"
NOTIFICATION_LOG_TITLE = "Bid Deadline Notification Failed"


def deadline_watch_days():
	"""The sweep window N from Tender Control Settings, default-safe.

	Blank / 0 / unreadable falls back to DEFAULT_DEADLINE_WATCH_DAYS (the
	refetch_window_ids convention: 0 means unset, not disabled)."""
	try:
		days = cint(
			frappe.db.get_single_value("Tender Control Settings", "deadline_watch_days")
		)
	except Exception:
		days = 0
	return days if days > 0 else DEFAULT_DEADLINE_WATCH_DAYS


def sweep_bid_deadlines():
	"""cron hook
	Daily scheduled task (module manifest): emails each opted-in bid owner
	about active bids closing within N days that still carry open
	compliance work, and about upcoming briefings inside the window.
	Runs on the control hub only, like the sibling scheduled tasks.
	"""
	if frappe.conf.get("app_role") != "control":
		return

	today = _as_date(nowdate())
	if today is None:
		return
	window_days = deadline_watch_days()
	cards = _cards_by_slug()

	lines_by_user = {}
	for name in frappe.get_all(
		"Tender Bid", filters={"status": ["in", list(ACTIVE_STATUSES)]}, pluck="name"
	):
		bid = frappe.get_doc("Tender Bid", name)
		lines = bid_deadline_lines(
			bid, today, window_days, cards.get(str(bid.get("tender_slug") or ""))
		)
		if lines:
			lines_by_user.setdefault(bid.get("user"), []).extend(lines)

	for user, lines in lines_by_user.items():
		if not user:
			continue
		notify(
			recipients=[user],
			subject=NOTIFICATION_SUBJECT,
			message=(
				"The clock is running on these bids - closing dates and "
				"briefings inside your reminder window:\n\n" + "\n".join(lines)
			),
			require_opt_in=True,
			failure_log_title=NOTIFICATION_LOG_TITLE,
		)


def bid_deadline_lines(bid, today, window_days, card=None):
	"""The reminder lines for one bid: [] when there is nothing to say.

	A closing date inside [today, today + N] earns a block ONLY when open
	compliance work remains (no-notify on a clean bid); an upcoming real
	briefing inside the window always earns its advance reminder."""
	lines = []
	label = _bid_label(bid)

	closing = _as_date(bid.get("closing_date"))
	if closing is not None and today <= closing <= today + datetime.timedelta(days=window_days):
		issues = open_deadline_issues(bid)
		if issues:
			days_left = (closing - today).days
			if days_left == 0:
				when = "closes TODAY"
			elif days_left == 1:
				when = "closes TOMORROW"
			else:
				when = f"closes in {days_left} days"
			lines.append(
				f"- {label} {when} ({closing.isoformat()}) and still has open "
				"compliance work - a late bid cannot be admitted:"
			)
			lines.extend(f"    - {issue}" for issue in issues)

	briefing_line = briefing_reminder_line(bid, today, window_days, card)
	if briefing_line:
		lines.append(briefing_line)
	return lines


def open_deadline_issues(bid):
	"""Open compliance work that still kills this bid before closing.

	The submission-gate failure list verbatim (open Fatal checklist items,
	missing/expired compliance artifacts, functionality eliminations,
	unattested generated artifacts - the gate module is reused, not
	re-implemented) plus mandatory returnables with NO artifact attached
	yet (disjoint from the gate's unattested check, which only fires once
	an artifact exists). Reminder input only - the submission gate itself
	is unchanged."""
	issues = list(validate_submission_readiness(bid))
	for row in bid.get("custom_returnables") or []:
		if not cint(row.get("mandatory")) or row.get("generated_artifact"):
			continue
		label = " - ".join(
			str(part) for part in (row.get("ref_code"), row.get("title")) if part
		) or "unnamed returnable"
		issues.append(f"Mandatory returnable with no artifact attached yet: {label}")
	return issues


def briefing_reminder_line(bid, today, window_days, card=None):
	"""An advance briefing reminder from the bid's cached catalog card.

	Positive evidence only: no card, no briefing value, an unparseable
	value, or a registry placeholder date (0001-01-01) all stay silent -
	a reminder must never invent a date. Past briefings are the
	suitability gate's business, not a reminder's."""
	if not card:
		return None
	raw = card.get("briefing_date_and_time")
	if not raw or is_placeholder_date(raw):
		return None
	parsed = parse_card_datetime(raw)
	if not parsed:
		return None
	briefing_day = parsed.date()
	if not (today <= briefing_day <= today + datetime.timedelta(days=window_days)):
		return None
	when = str(raw).strip()[:16]
	label = _bid_label(bid)
	if str(card.get("is_it_compulsory") or "").strip().lower() == "yes":
		return (
			f"- {label} has a COMPULSORY briefing on {when} - missing it is a "
			"fatal gate, so attending keeps this bid alive."
		)
	return f"- {label} has a briefing on {when} - attendance is optional but noted."


def _bid_label(bid):
	"""'Title (BID-NAME)' with slug/name fallbacks - never blank."""
	title = bid.get("tender_title") or bid.get("tender_slug") or bid.get("name") or "bid"
	name = bid.get("name")
	return f"{title} ({name})" if name and name != title else str(title)


def _as_date(value):
	"""A datetime.date from a doc date, a catalog string, or None.

	Accepts date/datetime objects (frappe rows) and the two catalog string
	formats via suitability's parser; anything else is None - the caller
	then simply skips the comparison rather than guessing."""
	if isinstance(value, datetime.datetime):
		return value.date()
	if isinstance(value, datetime.date):
		return value
	parsed = parse_card_datetime(value)
	return parsed.date() if parsed else None


def _cards_by_slug():
	"""The cached published tender cards keyed by slug AND tender_number.

	Read-only: the daily refresh task owns the cache. Unavailable or empty
	means {} - the sweep still runs, just without briefing reminders."""
	try:
		cards = frappe.cache().get_value(CATALOG_CACHE_KEY) or []
	except Exception:
		return {}
	mapped = {}
	for card in cards:
		if not isinstance(card, dict):
			continue
		for key in (card.get("slug"), card.get("tender_number")):
			if key:
				mapped.setdefault(str(key), card)
	return mapped
