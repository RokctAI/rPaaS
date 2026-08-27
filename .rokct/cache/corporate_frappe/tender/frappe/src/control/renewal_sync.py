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

# This file uses the composer's literal {app_name} template placeholder in
# imports (fleet SDK convention, cf. polaris) - it only parses after
# composition substitutes the real app package name.
# compliance-ignore-file: syntax-error

"""Renewal Watch - the frappe glue around the pure renewal ledger.

Persistence and wiring ONLY; every decision (duration parsing, gap
medians, window confirm/miss, lateness, trust) is computed by the pure,
standalone-testable ``compliance/renewal.py``. Two entry points:

- :func:`update_renewal_watches` - called additively at the end of every
  opportunities sync (``tasks.refresh_opportunities_cache``): appends new
  advert events to the ledger, settles open watches (confirm/miss) and
  opens new watches, exactly as :func:`renewal.plan_sync` planned.
- :func:`record_pack_duration` - called additively from the pack-parse
  endpoint: a successfully extracted pack text feeds its stated contract
  duration into the ledger (advert-text coverage is ~32%; pack text is
  the identified route to materially more - research section 8).
"""

import frappe
from frappe.utils import cint, nowdate

EVENT_FIELDS = (
	"name", "buyer", "buyer_normalized", "category", "event_type", "ocid",
	"event_date", "stated_duration_months", "source_field",
)
WATCH_FIELDS = (
	"name", "buyer", "buyer_normalized", "category", "anchor_ocid",
	"anchor_date", "source", "stated_duration_months", "predicted_date",
	"predicted_window_start", "predicted_window_end", "status",
	"confirmed_ocid", "confirmed_date", "error_days",
)


def _renewal():
	from {app_name}.tender.control.compliance import renewal

	return renewal


def _ledger_events():
	return frappe.get_all("Tender Renewal Event", fields=list(EVENT_FIELDS))


def _watches(statuses):
	return frappe.get_all(
		"Tender Renewal Watch",
		filters={"status": ("in", list(statuses))},
		fields=list(WATCH_FIELDS),
	)


def _insert_event(event):
	doc = dict(event, doctype="Tender Renewal Event")
	doc["stated_duration_months"] = cint(event.get("stated_duration_months"))
	frappe.get_doc(doc).insert(ignore_permissions=True)


def _insert_watch(watch):
	doc = dict(watch, doctype="Tender Renewal Watch")
	doc["stated_duration_months"] = cint(watch.get("stated_duration_months"))
	frappe.get_doc(doc).insert(ignore_permissions=True)


def _apply_watch_update(update):
	values = {"status": update["status"]}
	if update["status"] == "confirmed":
		values.update(
			{
				"confirmed_ocid": update.get("confirmed_ocid"),
				"confirmed_date": update.get("confirmed_date"),
				"error_days": cint(update.get("error_days")),
			}
		)
	frappe.db.set_value("Tender Renewal Watch", update["name"], values)


def update_renewal_watches():
	"""Runs the renewal ledger over the freshly synced opportunities.

	Control hub only (the tender module composes into every bench, but
	only control holds the ledger - tenants consume the radar via the
	gateway). Returns the plan's stats dict for observability.
	"""
	if frappe.conf.get("app_role") != "control":
		return None

	from {app_name}.tender.control.api.opportunity_utils import (
		get_cached_opportunities,
	)

	renewal = _renewal()
	cards = get_cached_opportunities("tenders") or []
	plan = renewal.plan_sync(
		cards,
		_ledger_events(),
		_watches(("open",)),
		_watches(("confirmed", "missed")),
		today=nowdate(),
	)

	for event in plan["new_events"]:
		_insert_event(event)
	for update in plan["watch_updates"]:
		_apply_watch_update(update)
	for watch in plan["new_watches"]:
		_insert_watch(watch)
	frappe.db.commit()
	return plan["stats"]


def record_pack_duration(bid_doc, pack_text):
	"""Feeds a parsed pack's stated contract duration into the ledger.

	Pack text states the term far more often than the advert does. When
	this bid's tender already has an advert event WITHOUT a stated
	duration, the pack-parsed months upgrade that event (source_field
	``pack_text``); when no stated-duration watch exists for the tender
	yet, one is opened, lateness-corrected for the buyer. Advert-parsed
	durations are never overwritten - the ledger appends and fills, it
	does not rewrite observations.
	"""
	if frappe.conf.get("app_role") != "control":
		return None

	renewal = _renewal()
	months = renewal.parse_contract_duration_months(pack_text)
	ocid = str(bid_doc.get("tender_slug") or "")
	if not months or not ocid:
		return None

	from {app_name}.tender.control.api.tenders.tender_entitlement import (
		find_tender_by_slug,
	)

	card = find_tender_by_slug(ocid) or {}
	buyer = card.get("institution") or bid_doc.get("institution")
	category = card.get("category") or ""
	closing = card.get("closing_date") or bid_doc.get("closing_date")
	if not buyer:
		return None

	stats = {"event": None, "watch_created": False, "months": months}

	existing = frappe.get_all(
		"Tender Renewal Event",
		filters={"ocid": ocid, "event_type": "advert"},
		fields=["name", "stated_duration_months"],
		limit=1,
	)
	if existing:
		if not cint(existing[0].stated_duration_months):
			frappe.db.set_value(
				"Tender Renewal Event",
				existing[0].name,
				{"stated_duration_months": months, "source_field": "pack_text"},
			)
			stats["event"] = "updated"
	else:
		event_date = renewal.parse_iso_date(
			card.get("date_published")
		) or renewal.parse_iso_date(closing)
		if event_date is None:
			return None
		_insert_event(
			{
				"buyer": str(buyer),
				"buyer_normalized": renewal.normalize_buyer(buyer),
				"category": str(category),
				"event_type": "advert",
				"ocid": ocid,
				"event_date": event_date.isoformat(),
				"stated_duration_months": months,
				"source_field": "pack_text",
			}
		)
		stats["event"] = "inserted"

	has_watch = frappe.get_all(
		"Tender Renewal Watch",
		filters={"anchor_ocid": ocid, "source": "stated_duration"},
		limit=1,
	)
	if not has_watch:
		lateness = renewal.buyer_lateness_days(
			_watches(("confirmed", "missed"))
		).get(renewal.normalize_buyer(buyer), 0)
		today = renewal.parse_iso_date(nowdate())
		anchor = renewal.parse_iso_date(closing) or renewal.parse_iso_date(
			card.get("date_published")
		)
		watch = renewal.build_stated_watch(
			buyer, category, ocid, anchor, months, today,
			lateness_days=lateness,
		)
		if watch:
			_insert_watch(watch)
			stats["watch_created"] = True

	frappe.db.commit()
	return stats
