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

"""Renewal Watch - the renewal-cycle ledger and its deterministic math.

"Keep a ledger, not a model" (approved design; evidence base:
``tender/Award-Outcomes-Research.md`` section 8, the renewal radar over
the 52,344-release radar population). Fixed-term public contracts come
back; this module learns WHEN, with counters and medians only - no AI,
no probabilities, no fitted parameters:

- **Ledger, not model.** Observed events (adverts, with any stated
  contract duration read from their text) are appended to a ledger;
  every aggregate below is recomputed deterministically from the ledger,
  never trained.
- **Stated durations give the prediction.** A tender stating a 36-month
  contract predicts re-advertisement ~36 months after its closing date
  (the research anchor: expected return = closing date + duration).
- **Observed gaps give the learned cycle.** When the same buyer +
  category re-advertises, the gap between adverts is recorded; the
  median observed gap per buyer + category cell is the learned cycle.
- **Outcomes give the correction.** When a predicted re-advert is
  actually observed, the signed error in days is recorded; the running
  median error per buyer becomes a lateness correction ("this buyer
  runs about 4 months late") applied to future stated-duration
  predictions.
- **Trust is a counter.** Per-buyer hit rate = predictions whose actual
  re-advert fell inside the predicted window / total resolved
  predictions. Counts, never probabilities.

Everything here is frappe-free, stdlib-only and standalone-testable
(``verify_renewal.py``), the same discipline as ``suitability.py`` /
``market_context.py``. The frappe glue (doctype persistence, the sync
hook) lives in ``control/renewal_sync.py``; the whole sync decision is
computed here by :func:`plan_sync` as a pure value.

The duration parser accepts ANY plain text - advert titles/descriptions
and text extracted from pack PDFs alike (section 8: advert-text coverage
is ~32%; most other durations are stated only inside the pack, so pack
text is the identified route to higher coverage).
"""

import calendar
import datetime
import re

# Same-package imports (F-09 pattern): relative on a composed bench,
# importlib fallback keeps this module importable standalone by file path.
try:
	from .market_context import normalize_buyer
except ImportError:  # standalone by-path import - load the sibling directly
	import importlib.util as _importlib_util
	import os as _os

	_spec = _importlib_util.spec_from_file_location(
		"tender_renewal_market_context",
		_os.path.join(
			_os.path.dirname(_os.path.abspath(__file__)), "market_context.py"
		),
	)
	_market_context = _importlib_util.module_from_spec(_spec)
	_spec.loader.exec_module(_market_context)
	normalize_buyer = _market_context.normalize_buyer


# --------------------------------------------------------------------------
# Constants (each argued from the research report, none fitted)
# --------------------------------------------------------------------------

# Accepted stated-duration range, in months (section 8's extraction band:
# "6-120 months accepted"; shorter is quotation/delivery noise, longer is
# not a term SA public contracting states).
MIN_DURATION_MONTHS = 6
MAX_DURATION_MONTHS = 120

# Predicted window around the predicted re-advert date. Asymmetric on
# purpose: the manually adjudicated renewals landed -0.9 to +2.2 months
# of schedule, and the known failure mode is LATE (buyers extend expiring
# contracts rather than re-advertise on time - section 8 caveat 2), so
# the window reaches further after the predicted date than before it.
WINDOW_BEFORE_DAYS = 90
WINDOW_AFTER_DAYS = 180

# Grace past window_end before an open watch is resolved as missed - the
# sync must not flap a watch to missed the day the window closes.
MISS_GRACE_DAYS = 60

# Observed advert-to-advert gaps outside this band are not renewal
# cycles: shorter is amendment/parallel-lot noise (re-posts of the same
# procurement), longer than ~10 years is unrelated demand.
MIN_CYCLE_GAP_DAYS = 180
MAX_CYCLE_GAP_DAYS = 3700

# An observed-cycle watch needs at least this many recorded gaps in its
# buyer + category cell - one gap is an anecdote, not a rhythm.
MIN_GAPS_FOR_CYCLE = 2

WATCH_STATUSES = ("open", "confirmed", "missed")
WATCH_SOURCES = ("stated_duration", "observed_cycle")
EVENT_TYPES = ("advert", "award", "close")


# --------------------------------------------------------------------------
# Duration parsing (plain text in, months out - adverts AND pack text)
# --------------------------------------------------------------------------

_WORD_ONES = {
	"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
	"seven": 7, "eight": 8, "nine": 9,
}
_WORD_TEENS = {
	"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
	"fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
	"nineteen": 19,
}
_WORD_TENS = {
	"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
	"seventy": 70, "eighty": 80, "ninety": 90,
}

_ONES_ALT = "|".join(_WORD_ONES)
_TEENS_ALT = "|".join(_WORD_TEENS)
_TENS_ALT = "|".join(_WORD_TENS)
# "three", "twelve", "twenty", "twenty four", "thirty-six", ...
_WORD_NUMBER = (
	r"(?:(?:" + _TENS_ALT + r")(?:[\s-](?:" + _ONES_ALT + r"))?"
	r"|(?:" + _TEENS_ALT + r")|(?:" + _ONES_ALT + r"))"
)

_UNIT = r"(months?|years?)"

# Digit forms: "36 months", "36-month contract", "5 years", optionally a
# confirming parenthetical after the digits ("36 (thirty six) months" is
# rare enough to skip; "thirty six (36) months" is the common SA form and
# is handled by _RE_WORD_PAREN below).
_RE_DIGIT = re.compile(r"\b(\d{1,3})[\s-]*" + _UNIT + r"\b", re.I)

# "three (3) years", "thirty-six (36) months" - the digit in parentheses
# is authoritative.
_RE_WORD_PAREN = re.compile(
	r"\b" + _WORD_NUMBER + r"\s*\(\s*(\d{1,3})\s*\)[\s-]*" + _UNIT + r"\b", re.I
)

# Bare word forms: "three years", "twenty four months".
_RE_WORD = re.compile(r"\b(" + _WORD_NUMBER + r")[\s-]+" + _UNIT + r"\b", re.I)

# Noise guards (section 8: "noise guards drop 'X years' experience',
# warranty periods and 'within N months' delivery phrases"). A candidate
# whose surrounding context matches any of these is dropped.
_RE_CONTEXT_NOISE = re.compile(
	r"\b(experience|experien\w*|warrant\w*|guarantee\w*|defects?\s+liability"
	r"|validity|valid\s+for|of\s+age|years?\s+old)\b",
	re.I,
)
# Tokens immediately BEFORE the number that mark a non-term phrase:
# "within 12 months" (delivery), "the past five years" (track record).
_RE_LEADING_NOISE = re.compile(
	r"\b(within|past|last|previous|preceding|next)\s*(?:the\s+)?$", re.I
)

_CONTEXT_BEFORE = 40
_CONTEXT_AFTER = 56
_LEADING_WINDOW = 24


def _word_number_value(words):
	"""'thirty six' / 'thirty-six' / 'three' -> integer value."""
	total = 0
	for token in re.split(r"[\s-]+", str(words or "").strip().lower()):
		if token in _WORD_TENS:
			total += _WORD_TENS[token]
		elif token in _WORD_TEENS:
			total += _WORD_TEENS[token]
		elif token in _WORD_ONES:
			total += _WORD_ONES[token]
	return total


def _to_months(value, unit):
	unit = str(unit or "").lower()
	if unit.startswith("year"):
		return value * 12
	return value


def extract_duration_candidates(text):
	"""Every plausible stated-duration mention in ``text``.

	Returns a list of ``{"months", "snippet", "position"}`` dicts in text
	order, already range-checked (6-120 months) and noise-guarded. Works
	on advert titles/descriptions and on text extracted from pack PDFs -
	the caller decides what text to feed it.
	"""
	text = str(text or "")
	if not text.strip():
		return []
	candidates = []
	seen_spans = []

	def overlaps(start, end):
		return any(s < end and start < e for s, e in seen_spans)

	def consider(start, end, months, snippet):
		if not (MIN_DURATION_MONTHS <= months <= MAX_DURATION_MONTHS):
			return
		if overlaps(start, end):
			return
		context = text[max(0, start - _CONTEXT_BEFORE):end + _CONTEXT_AFTER]
		if _RE_CONTEXT_NOISE.search(context):
			return
		leading = text[max(0, start - _LEADING_WINDOW):start]
		if _RE_LEADING_NOISE.search(leading):
			return
		seen_spans.append((start, end))
		candidates.append(
			{"months": months, "snippet": snippet.strip(), "position": start}
		)

	# Word-with-parenthetical first: its span contains a digit form that
	# _RE_DIGIT would otherwise double-count.
	for match in _RE_WORD_PAREN.finditer(text):
		months = _to_months(int(match.group(1)), match.group(2))
		consider(match.start(), match.end(), months, match.group(0))
	for match in _RE_DIGIT.finditer(text):
		months = _to_months(int(match.group(1)), match.group(2))
		consider(match.start(), match.end(), months, match.group(0))
	for match in _RE_WORD.finditer(text):
		months = _to_months(_word_number_value(match.group(1)), match.group(2))
		consider(match.start(), match.end(), months, match.group(0))

	candidates.sort(key=lambda c: c["position"])
	return candidates


def parse_contract_duration_months(text):
	"""The stated contract duration in ``text``, in months, or None.

	Deterministic selection over :func:`extract_duration_candidates`: the
	most frequently stated value wins (a pack repeats its real term on
	the cover, the SLA and the pricing schedule; noise values are one-off),
	ties broken by earliest mention.
	"""
	candidates = extract_duration_candidates(text)
	if not candidates:
		return None
	counts = {}
	first_at = {}
	for cand in candidates:
		months = cand["months"]
		counts[months] = counts.get(months, 0) + 1
		first_at.setdefault(months, cand["position"])
	return min(counts, key=lambda m: (-counts[m], first_at[m]))


# --------------------------------------------------------------------------
# Calendar helpers (stdlib, deterministic)
# --------------------------------------------------------------------------

_RE_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def parse_iso_date(value):
	"""'YYYY-MM-DD[ HH:MM[:SS]]' / date / datetime -> datetime.date | None.

	Placeholder years (the catalog's '0001-01-01' pattern) parse to None.
	"""
	if isinstance(value, datetime.datetime):
		value = value.date()
	if isinstance(value, datetime.date):
		return value if value.year >= 2000 else None
	match = _RE_ISO_DATE.match(str(value or "").strip())
	if not match:
		return None
	year, month, day = (int(g) for g in match.groups())
	if year < 2000:
		return None
	try:
		return datetime.date(year, month, day)
	except ValueError:
		return None


def add_months(day, months):
	"""Calendar-month addition with day-of-month clamping
	(2026-01-31 + 1 month -> 2026-02-28)."""
	month_index = day.month - 1 + int(months)
	year = day.year + month_index // 12
	month = month_index % 12 + 1
	dom = min(day.day, calendar.monthrange(year, month)[1])
	return datetime.date(year, month, dom)


def median_value(values):
	"""Plain median (mean of the middle pair for even counts); None on
	empty input. The ledger discipline: medians, never means."""
	ordered = sorted(values)
	if not ordered:
		return None
	mid = len(ordered) // 2
	if len(ordered) % 2:
		return ordered[mid]
	return (ordered[mid - 1] + ordered[mid]) / 2.0


# --------------------------------------------------------------------------
# Ledger aggregates (recomputed from events/watches, never stored as truth)
# --------------------------------------------------------------------------

def _normalize(value):
	return " ".join(str(value or "").lower().split())


def cell_key(buyer_normalized, category):
	"""The buyer + category cell key gap math and matching group by."""
	return (_normalize(buyer_normalized), _normalize(category))


def advert_events_by_cell(events):
	"""Groups advert ledger events into buyer + category cells.

	Returns ``{(buyer_normalized, category_normalized): [(date, event)]}``
	sorted by (date, ocid) - a total, deterministic order.
	"""
	cells = {}
	for event in events or []:
		if (event.get("event_type") or "advert") != "advert":
			continue
		buyer_norm = event.get("buyer_normalized") or normalize_buyer(
			event.get("buyer")
		)
		key = cell_key(buyer_norm, event.get("category"))
		if not key[0]:
			continue
		day = parse_iso_date(event.get("event_date"))
		if day is None:
			continue
		cells.setdefault(key, []).append((day, event))
	for entries in cells.values():
		entries.sort(key=lambda pair: (pair[0], str(pair[1].get("ocid") or "")))
	return cells


def observed_gap_days(dates):
	"""Consecutive advert-to-advert gaps (days) within the cycle band.

	Duplicate dates collapse first (parallel lots advertised the same day
	are one demand event, not a zero-day cycle).
	"""
	unique = sorted(set(dates))
	gaps = []
	for earlier, later in zip(unique, unique[1:]):
		gap = (later - earlier).days
		if MIN_CYCLE_GAP_DAYS <= gap <= MAX_CYCLE_GAP_DAYS:
			gaps.append(gap)
	return gaps


def median_cycle_days(gaps):
	"""The learned cycle for one buyer + category cell: the median of its
	observed gaps, published only at >= MIN_GAPS_FOR_CYCLE observations."""
	if len(gaps or []) < MIN_GAPS_FOR_CYCLE:
		return None
	return int(round(median_value(gaps)))


def buyer_lateness_days(resolved_watches):
	"""Per-buyer lateness correction: the running median of signed
	confirmation errors (days) over that buyer's CONFIRMED watches.
	Positive = the buyer re-advertises later than stated durations say."""
	errors = {}
	for watch in resolved_watches or []:
		if watch.get("status") != "confirmed":
			continue
		error = watch.get("error_days")
		if error is None:
			continue
		buyer_norm = _normalize(watch.get("buyer_normalized"))
		if not buyer_norm:
			continue
		errors.setdefault(buyer_norm, []).append(int(error))
	return {
		buyer: int(round(median_value(values)))
		for buyer, values in errors.items()
	}


def hit_rate(confirmed_count, missed_count):
	"""Trust as a counter: confirmed / resolved, carried as plain counts
	plus the derived percentage (None while nothing has resolved)."""
	resolved = int(confirmed_count) + int(missed_count)
	return {
		"confirmed": int(confirmed_count),
		"missed": int(missed_count),
		"resolved": resolved,
		"hit_rate_pct": (
			round(100.0 * int(confirmed_count) / resolved, 2) if resolved else None
		),
	}


def buyer_trust(resolved_watches):
	"""Per-buyer hit-rate counters over resolved (confirmed + missed)
	watches: {buyer_normalized: hit_rate(...) dict}."""
	counts = {}
	for watch in resolved_watches or []:
		status = watch.get("status")
		if status not in ("confirmed", "missed"):
			continue
		buyer_norm = _normalize(watch.get("buyer_normalized"))
		if not buyer_norm:
			continue
		cell = counts.setdefault(buyer_norm, [0, 0])
		cell[0 if status == "confirmed" else 1] += 1
	return {
		buyer: hit_rate(confirmed, missed)
		for buyer, (confirmed, missed) in sorted(counts.items())
	}


# --------------------------------------------------------------------------
# Watches: build, confirm, miss
# --------------------------------------------------------------------------

def _watch(buyer, category, anchor_ocid, anchor_date, source, predicted,
		today, stated_duration_months=None):
	window_start = predicted - datetime.timedelta(days=WINDOW_BEFORE_DAYS)
	window_end = predicted + datetime.timedelta(days=WINDOW_AFTER_DAYS)
	if window_end < today:
		# Historical anchors whose window already closed would be born
		# missed - the ledger keeps their EVENTS (gap math still learns
		# from them) but never opens a dead watch.
		return None
	return {
		"buyer": str(buyer or ""),
		"buyer_normalized": normalize_buyer(buyer),
		"category": str(category or ""),
		"anchor_ocid": str(anchor_ocid or ""),
		"anchor_date": anchor_date.isoformat(),
		"source": source,
		"stated_duration_months": stated_duration_months,
		"predicted_date": predicted.isoformat(),
		"predicted_window_start": window_start.isoformat(),
		"predicted_window_end": window_end.isoformat(),
		"status": "open",
	}


def build_stated_watch(buyer, category, anchor_ocid, anchor_date,
		duration_months, today, lateness_days=0):
	"""A stated-duration watch: predicted re-advert = anchor (closing
	date) + stated duration, shifted by the buyer's lateness correction.
	Returns the watch dict, or None when the window is already past."""
	anchor_date = parse_iso_date(anchor_date)
	if anchor_date is None or not duration_months:
		return None
	predicted = add_months(anchor_date, duration_months) + datetime.timedelta(
		days=int(lateness_days or 0)
	)
	return _watch(
		buyer, category, anchor_ocid, anchor_date, "stated_duration",
		predicted, today, stated_duration_months=int(duration_months),
	)


def build_cycle_watch(buyer, category, anchor_ocid, anchor_date, cycle_days,
		today):
	"""An observed-cycle watch: predicted re-advert = latest advert +
	the cell's median observed gap. No lateness correction - the observed
	gaps already embody the buyer's real timing."""
	anchor_date = parse_iso_date(anchor_date)
	if anchor_date is None or not cycle_days:
		return None
	predicted = anchor_date + datetime.timedelta(days=int(cycle_days))
	return _watch(
		buyer, category, anchor_ocid, anchor_date, "observed_cycle",
		predicted, today,
	)


def evaluate_watch(watch, candidate_events, today, grace_days=MISS_GRACE_DAYS):
	"""One open watch against its cell's candidate adverts.

	- earliest candidate advert dated inside [window_start, window_end]
	  -> ``confirm`` (with the confirming ocid/date and the signed
	  error_days against the predicted date);
	- no in-window candidate and today past window_end + grace ->
	  ``miss``;
	- otherwise ``hold`` (the watch stays open). A candidate BEFORE the
	  window neither confirms nor resolves - early re-adverts (section 8
	  caveat 3) are new demand the next sync records as its own event.
	"""
	predicted = parse_iso_date(watch.get("predicted_date"))
	window_start = parse_iso_date(watch.get("predicted_window_start"))
	window_end = parse_iso_date(watch.get("predicted_window_end"))
	if predicted is None or window_start is None or window_end is None:
		return {"action": "hold"}
	anchor_ocid = str(watch.get("anchor_ocid") or "")
	in_window = []
	for event in candidate_events or []:
		ocid = str(event.get("ocid") or "")
		if ocid and ocid == anchor_ocid:
			continue  # a watch never confirms on its own anchor advert
		day = parse_iso_date(event.get("event_date"))
		if day is None or not (window_start <= day <= window_end):
			continue
		in_window.append((day, ocid))
	if in_window:
		day, ocid = min(in_window)
		return {
			"action": "confirm",
			"confirmed_ocid": ocid,
			"confirmed_date": day.isoformat(),
			"error_days": (day - predicted).days,
		}
	if today > window_end + datetime.timedelta(days=int(grace_days)):
		return {"action": "miss"}
	return {"action": "hold"}


# --------------------------------------------------------------------------
# The sync plan - one pure value the frappe glue applies verbatim
# --------------------------------------------------------------------------

def card_ocid(card):
	return str(card.get("tender_number") or card.get("slug") or "")


def card_text(card):
	"""The card text the duration parser reads: title plus description
	when the catalog carries one (advert-level coverage ~32%; pack text
	arrives separately through the pack-parse hook)."""
	parts = [card.get("title"), card.get("description")]
	return " ".join(str(part) for part in parts if part)


def plan_sync(cards, events, open_watches, resolved_watches=None, today=None):
	"""Computes everything one opportunities sync should do to the ledger.

	Inputs are plain values (catalog cards, existing ledger events, open
	and resolved watches as dicts); the output is a plan the frappe glue
	applies without further decisions:

	- ``new_events``: adverts not yet in the ledger (deduped by ocid),
	  each with any stated duration parsed from its card text;
	- ``watch_updates``: open watches to resolve (confirm with
	  error_days, or miss past window_end + grace), referenced by the
	  watch's own ``name``/anchor identity;
	- ``new_watches``: stated-duration watches for newly stated terms
	  (lateness-corrected per buyer) plus observed-cycle watches for
	  cells whose median gap is established and unwatched.

	Deterministic: same inputs, same plan - re-running is a no-op.
	"""
	today = parse_iso_date(today) or datetime.date.today()
	events = list(events or [])
	open_watches = list(open_watches or [])
	resolved_watches = list(resolved_watches or [])

	known_ocids = {
		str(event.get("ocid") or "")
		for event in events
		if (event.get("event_type") or "advert") == "advert"
	}
	known_ocids.discard("")

	# 1. new advert events from cards (deduped by ocid)
	new_events = []
	cards_by_ocid = {}
	skipped_cards = 0
	for card in cards or []:
		ocid = card_ocid(card)
		if not ocid or ocid in known_ocids:
			continue
		buyer = card.get("institution") or card.get("organization")
		event_date = parse_iso_date(card.get("date_published")) or parse_iso_date(
			card.get("closing_date")
		)
		if not buyer or event_date is None:
			skipped_cards += 1
			continue
		known_ocids.add(ocid)
		cards_by_ocid[ocid] = card
		months = parse_contract_duration_months(card_text(card))
		new_events.append({
			"buyer": str(buyer),
			"buyer_normalized": normalize_buyer(buyer),
			"category": str(card.get("category") or ""),
			"event_type": "advert",
			"ocid": ocid,
			"event_date": event_date.isoformat(),
			"stated_duration_months": months,
			"source_field": "advert_text" if months else "",
		})

	all_events = events + new_events
	cells = advert_events_by_cell(all_events)
	lateness = buyer_lateness_days(resolved_watches)

	# 2. settle open watches against the (now-updated) advert ledger
	watch_updates = []
	still_open_cells = set()
	for watch in open_watches:
		key = cell_key(
			watch.get("buyer_normalized") or normalize_buyer(watch.get("buyer")),
			watch.get("category"),
		)
		anchor_date = parse_iso_date(watch.get("anchor_date"))
		candidates = [
			event
			for day, event in cells.get(key, [])
			if anchor_date is None or day > anchor_date
		]
		decision = evaluate_watch(watch, candidates, today)
		if decision["action"] == "hold":
			still_open_cells.add(key)
			continue
		update = {
			"name": watch.get("name"),
			"anchor_ocid": watch.get("anchor_ocid"),
			"source": watch.get("source"),
			"status": "confirmed" if decision["action"] == "confirm" else "missed",
		}
		if decision["action"] == "confirm":
			update["confirmed_ocid"] = decision["confirmed_ocid"]
			update["confirmed_date"] = decision["confirmed_date"]
			update["error_days"] = decision["error_days"]
		watch_updates.append(update)

	# 3. new stated-duration watches (anchor = the card's closing date)
	existing_anchor_keys = {
		(str(watch.get("anchor_ocid") or ""), watch.get("source"))
		for watch in open_watches + resolved_watches
	}
	new_watches = []
	for event in new_events:
		if not event["stated_duration_months"]:
			continue
		card = cards_by_ocid[event["ocid"]]
		anchor_date = parse_iso_date(card.get("closing_date")) or parse_iso_date(
			event["event_date"]
		)
		watch = build_stated_watch(
			event["buyer"], event["category"], event["ocid"], anchor_date,
			event["stated_duration_months"], today,
			lateness_days=lateness.get(event["buyer_normalized"], 0),
		)
		key = (event["ocid"], "stated_duration")
		if watch and key not in existing_anchor_keys:
			existing_anchor_keys.add(key)
			new_watches.append(watch)
			still_open_cells.add(
				cell_key(watch["buyer_normalized"], watch["category"])
			)

	# 4. observed-cycle watches for established, unwatched cells
	for key in sorted(cells):
		if key in still_open_cells:
			continue
		entries = cells[key]
		cycle = median_cycle_days(observed_gap_days([day for day, _ in entries]))
		if cycle is None:
			continue
		anchor_day, anchor_event = entries[-1]
		watch = build_cycle_watch(
			anchor_event.get("buyer"), anchor_event.get("category"),
			anchor_event.get("ocid"), anchor_day, cycle, today,
		)
		anchor_key = (str(anchor_event.get("ocid") or ""), "observed_cycle")
		if watch and anchor_key not in existing_anchor_keys:
			existing_anchor_keys.add(anchor_key)
			new_watches.append(watch)

	return {
		"new_events": new_events,
		"watch_updates": watch_updates,
		"new_watches": new_watches,
		"stats": {
			"cards_seen": len(cards or []),
			"cards_skipped": skipped_cards,
			"events_appended": len(new_events),
			"durations_stated": sum(
				1 for event in new_events if event["stated_duration_months"]
			),
			"watches_confirmed": sum(
				1 for u in watch_updates if u["status"] == "confirmed"
			),
			"watches_missed": sum(
				1 for u in watch_updates if u["status"] == "missed"
			),
			"watches_created": len(new_watches),
		},
	}
