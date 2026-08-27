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

"""Unified compliance calendar - ASSEMBLY of the four existing date
streams into one dated feed (assessment plan #13). No new logic: every
date served here is already computed and served elsewhere -

- **bid closings**: the caller's open Tender Bids' ``closing_date``
  (exactly the field get_my_bids orders by; KILL-01: late = cannot be
  admitted);
- **briefings**: the ``briefing_date_and_time`` on the catalog card of
  each open bid, with the suitability engine's placeholder-date
  discipline (a 0001-01-01 date is UNKNOWN, never an event);
- **compliance-artifact expiries**: the caller's Compliance Artifacts'
  user-entered ``valid_until`` (the same field the weekly
  ``artifact_expiry.sweep_compliance_artifacts`` email runs off);
- **renewal expected-advertisement windows**: open Tender Renewal Watch
  predictions, exactly as ``get_renewal_radar`` serves them.

Honesty constraint carried as a hard invariant: the three deadline
streams are ``commitment`` items (real dates on real obligations), but
every renewal entry is a ``watch`` item - a lead-calendar "prepare now"
window, NEVER a commitment. The Award-Outcomes research validation
confirmed only 2 of 12 sampled due predictions as unambiguous
same-service returns, so no client may render a predicted window as a
deadline; the caveat rides every payload.

Pure module: stdlib only, frappe-free, standalone-testable (same
doctrine as renewal.py / suitability.py). Date parsing is REUSED from
the renewal ledger (``parse_iso_date`` already handles catalog dates,
datetimes and the 0001-01-01 placeholder pattern). Deterministic:
identical inputs give identical output.
"""

import datetime

# Same-package imports (F-09 pattern): relative on a composed bench, importlib
# fallback keeps this module importable standalone by file path.
try:
	from .renewal import buyer_trust, parse_iso_date
except ImportError:  # standalone by-path import - load the sibling directly
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

	_renewal = _load_sibling("tender_calendar_renewal", "renewal.py")
	buyer_trust = _renewal.buyer_trust
	parse_iso_date = _renewal.parse_iso_date


# The four streams, in deterministic same-day precedence order: the
# thing that kills a bid outright (closing) sorts before the thing to
# attend (briefing), before the standing document to renew (expiry),
# before the lead-calendar watch (renewal window).
STREAM_BID_CLOSING = "bid_closing"
STREAM_BRIEFING = "briefing"
STREAM_ARTIFACT_EXPIRY = "artifact_expiry"
STREAM_RENEWAL_WINDOW = "renewal_window"
STREAM_ORDER = (
	STREAM_BID_CLOSING,
	STREAM_BRIEFING,
	STREAM_ARTIFACT_EXPIRY,
	STREAM_RENEWAL_WINDOW,
)

# Item classes - the calendar's honesty axis. A commitment is a real
# date on a real obligation (miss it and something concrete is lost); a
# watch is a deterministic prediction to start preparing against, never
# a certainty. ONLY the renewal stream may emit watches.
ITEM_CLASS_COMMITMENT = "commitment"
ITEM_CLASS_WATCH = "watch"

# Bid statuses with a live clock. Submitted / Awarded / Lost / Withdrawn
# bids have no upcoming closing or briefing to keep.
OPEN_BID_STATUSES = ("Watching", "Preparing")

DEFAULT_DAYS_AHEAD = 90
MAX_DAYS_AHEAD = 366
DEFAULT_LIMIT = 200
MAX_LIMIT = 500

SEMANTICS = (
	"unified compliance calendar - assembly of four existing date streams "
	"(bid closings, briefings, compliance-artifact expiries, renewal "
	"expected-advertisement windows) into one dated feed; deterministic, "
	"no AI, nothing predicted here that the renewal ledger did not "
	"already predict"
)

CALENDAR_CAVEATS = [
	"renewal_window entries are WATCH items, never commitments: the "
	"Award-Outcomes research validation confirmed only 2 of 12 sampled "
	"due predictions as unambiguous same-service returns (both within "
	"~2.2 months of schedule) - render them as 'prepare now' windows, "
	"never as deadlines",
	"a predicted window is a LEAD CALENDAR entry - match the successor "
	"by buyer + category when it actually appears, and expect buyers to "
	"run late (extensions delay returns)",
	"briefing and closing dates come from the published catalog card; "
	"placeholder registry dates (the 0001-01-01 pattern) are treated as "
	"unknown and never become calendar entries - re-verify against the "
	"original advert",
	"artifact expiry dates are user-entered off the certificate itself "
	"(CSD has no supplier API) - an empty inventory means nothing is "
	"tracked, not that nothing expires",
]


def _entry(stream, item_class, date, today, title, detail, ref):
	"""One unified calendar row. ``date`` is a datetime.date."""
	return {
		"date": date.isoformat(),
		"days_away": (date - today).days,
		"stream": stream,
		"item_class": item_class,
		"title": str(title or ""),
		"detail": str(detail or ""),
		"ref": ref,
	}


def _in_horizon(date, today, horizon):
	return date is not None and today <= date <= horizon


def bid_closing_entries(bids, today, horizon):
	"""Closing-date entries for the caller's OPEN bids (Watching /
	Preparing) - the same rows and field get_my_bids serves, re-cut as a
	dated feed. Past closings and unparseable dates are silently absent
	(a placeholder date is unknown, not an event)."""
	entries = []
	for bid in bids or []:
		if (bid or {}).get("status") not in OPEN_BID_STATUSES:
			continue
		closing = parse_iso_date(bid.get("closing_date"))
		if not _in_horizon(closing, today, horizon):
			continue
		entries.append(_entry(
			STREAM_BID_CLOSING, ITEM_CLASS_COMMITMENT, closing, today,
			bid.get("tender_title") or bid.get("tender_slug"),
			"Bid closes ({0}) - late submission cannot be admitted "
			"(KILL-01)".format(bid.get("status")),
			{
				"doctype": "Tender Bid",
				"name": str(bid.get("name") or ""),
				"tender_slug": str(bid.get("tender_slug") or ""),
				"institution": str(bid.get("institution") or "") or None,
			},
		))
	return entries


def briefing_entries(bids, cards_by_slug, today, horizon):
	"""Briefing-date entries for the caller's open bids, read off each
	bid's catalog card (``briefing_date_and_time``) with the suitability
	engine's placeholder discipline via parse_iso_date. A compulsory
	briefing missed is a fatal gate after the fact - this entry is the
	save before it."""
	entries = []
	for bid in bids or []:
		if (bid or {}).get("status") not in OPEN_BID_STATUSES:
			continue
		slug = str(bid.get("tender_slug") or "")
		card = (cards_by_slug or {}).get(slug) or {}
		briefing = parse_iso_date(card.get("briefing_date_and_time"))
		if not _in_horizon(briefing, today, horizon):
			continue
		compulsory = str(card.get("is_it_compulsory") or "").strip().lower() == "yes"
		entries.append(_entry(
			STREAM_BRIEFING, ITEM_CLASS_COMMITMENT, briefing, today,
			bid.get("tender_title") or slug,
			(
				"COMPULSORY briefing - non-attendance is a fatal gate"
				if compulsory
				else "Briefing session (not marked compulsory on the card)"
			),
			{
				"doctype": "Tender Bid",
				"name": str(bid.get("name") or ""),
				"tender_slug": slug,
				"institution": str(bid.get("institution") or "") or None,
				"compulsory": compulsory,
			},
		))
	return entries


def artifact_expiry_entries(artifacts, today, horizon):
	"""Expiry entries for the caller's Compliance Artifacts - the same
	``valid_until`` field the weekly expiry sweep emails about, served as
	dated feed rows. Already-expired artifacts are the sweep's business
	(status Expired), not upcoming calendar entries."""
	entries = []
	for artifact in artifacts or []:
		expiry = parse_iso_date((artifact or {}).get("valid_until"))
		if not _in_horizon(expiry, today, horizon):
			continue
		label = str(artifact.get("artifact_type") or "Compliance artifact")
		reference = str(artifact.get("reference") or "").strip()
		if reference:
			label = "{0} ({1})".format(label, reference)
		entries.append(_entry(
			STREAM_ARTIFACT_EXPIRY, ITEM_CLASS_COMMITMENT, expiry, today,
			label,
			"Standing compliance document expires - renew before bids "
			"gather it (current status: {0})".format(
				artifact.get("status") or "Green"
			),
			{
				"doctype": "Compliance Artifact",
				"name": str(artifact.get("name") or ""),
				"artifact_type": str(artifact.get("artifact_type") or ""),
				"status": str(artifact.get("status") or "") or None,
			},
		))
	return entries


def renewal_window_entries(open_watches, resolved_watches, today, horizon):
	"""WATCH entries from the renewal radar's open watches - the exact
	rows get_renewal_radar serves (open status, predicted_date within the
	horizon), re-cut as calendar rows. item_class is ``watch`` on every
	row, without exception: only 2 of 12 sampled due predictions
	validated, so these are never commitments."""
	trust = buyer_trust(resolved_watches or [])
	entries = []
	for watch in open_watches or []:
		if (watch or {}).get("status") != "open":
			continue
		predicted = parse_iso_date(watch.get("predicted_date"))
		if not _in_horizon(predicted, today, horizon):
			continue
		window_start = parse_iso_date(watch.get("predicted_window_start"))
		window_end = parse_iso_date(watch.get("predicted_window_end"))
		entries.append(_entry(
			STREAM_RENEWAL_WINDOW, ITEM_CLASS_WATCH, predicted, today,
			"{0} - {1}".format(
				watch.get("buyer") or "?", watch.get("category") or "?"
			),
			"Expected re-advertisement window (WATCH item - prepare now, "
			"never a certainty; only 2 of 12 sampled due predictions "
			"validated)",
			{
				"doctype": "Tender Renewal Watch",
				"name": str(watch.get("name") or ""),
				"source": str(watch.get("source") or "") or None,
				"predicted_window_start": (
					window_start.isoformat() if window_start else None
				),
				"predicted_window_end": (
					window_end.isoformat() if window_end else None
				),
				"trust": trust.get(str(watch.get("buyer_normalized") or "")),
			},
		))
	return entries


def build_compliance_calendar(
	bids,
	artifacts,
	cards_by_slug,
	open_watches,
	resolved_watches,
	today,
	days_ahead=DEFAULT_DAYS_AHEAD,
	limit=DEFAULT_LIMIT,
):
	"""Merges the four streams into one dated feed, soonest first.

	``today`` is a datetime.date (or ISO string). Ordering is total and
	deterministic: (date, stream precedence, title, ref name). The
	summary counts every in-horizon entry per stream BEFORE the limit
	cut, so a truncated feed still reports the true stream sizes.
	"""
	today = parse_iso_date(today)
	if today is None:
		raise ValueError("build_compliance_calendar needs a real 'today'")
	days_ahead = max(1, min(int(days_ahead or DEFAULT_DAYS_AHEAD), MAX_DAYS_AHEAD))
	limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
	horizon = today + datetime.timedelta(days=days_ahead)

	entries = (
		bid_closing_entries(bids, today, horizon)
		+ briefing_entries(bids, cards_by_slug, today, horizon)
		+ artifact_expiry_entries(artifacts, today, horizon)
		+ renewal_window_entries(open_watches, resolved_watches, today, horizon)
	)
	entries.sort(key=lambda e: (
		e["date"],
		STREAM_ORDER.index(e["stream"]),
		e["title"],
		e["ref"].get("name") or "",
	))

	streams = {stream: 0 for stream in STREAM_ORDER}
	for entry in entries:
		streams[entry["stream"]] += 1
	shown = entries[:limit]

	return {
		"entries": shown,
		"summary": {
			"total": len(entries),
			"shown": len(shown),
			"days_ahead": days_ahead,
			"horizon": horizon.isoformat(),
			"streams": streams,
			"commitments": sum(
				1 for e in entries if e["item_class"] == ITEM_CLASS_COMMITMENT
			),
			"watches": sum(
				1 for e in entries if e["item_class"] == ITEM_CLASS_WATCH
			),
		},
		"semantics": SEMANTICS,
		"caveats": list(CALENDAR_CAVEATS),
		"generated_on": today.isoformat(),
	}
