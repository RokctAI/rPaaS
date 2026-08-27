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

"""Award-outcome ledger (plan #12): two composable, deterministic halves.

(i) **Own-outcome aggregation** - counters over the caller's OWN Tender
Bid records (statuses Awarded / Lost / Submitted / ... plus
``estimated_value`` / ``outcome_value``): win rate as a share of DECIDED
bids only, per-buyer counters, and quoted-vs-awarded value deltas placed
against the same market-context pricing band the bid was shown
(``pricing_bands.bid_pricing_band`` - selection and N >= 30 discipline
delegated verbatim, never re-implemented). Per-subscriber PRIVATE data:
the caller must pass bids already scoped to one user (get_my_bids
doctrine) and the payload only ever goes back to that user.

(ii) **Published-award matching** - joins the claimed tenders' ocids
against re-fetched OCDS releases (tasks.py's ingester keeps compiled
releases in Raw Tender Cache; the same ocid gains its award block on a
later re-fetch) to record who actually won, even when the user never
updates their bid. Detection is a NON-EMPTY ``awards[]`` ONLY - this
feed tags every release ``["compiled"]``, so release tags carry no award
signal and are never consulted.

The Award-Outcomes-Research bounds are the design constraints, carried
as machine-readable caveats on every payload:

- winner-side feed: only published successes appear (every award
  "active"), so win/loss base rates are unobservable - this ledger is
  market-context-style calibration plus the user's own record, NEVER a
  win-probability claim;
- publication is severely buyer-skewed (19.95% of releases carry an
  award block; SARS 75.74% / Justice 71.96% vs ESKOM 9.87% and Tshwane /
  Joburg / Mnquma 0.00%) - a claimed tender at a non-publishing buyer
  will simply never match, and "no award published" is NEVER evidence of
  "lost";
- only 72.01% of award blocks carry a usable non-zero amount - amounts
  ride flagged (``zero`` / ``lt_R100`` / ``gt_R10bn``), never dropped,
  with contract-total semantics;
- the feed carries no award dates at all - the release date is the only
  (weak) time proxy, award lag is unmeasurable, and awards surfacing
  after the ingester's trailing re-fetch window are only recoverable by
  re-enumerating old ids.

Frappe-free and stdlib-only, standalone-testable like the sibling
compliance modules (suitability.py / renewal.py doctrine). Nothing here
mutates a bid: a published award is REPORTED, the bid status is never
auto-flipped (the user settles their own record).
"""

import re

# Same-package imports (F-09 pattern): relative on a composed bench,
# importlib fallback keeps this module importable standalone by file path.
try:
	from .pricing_bands import bid_pricing_band, card_index
except ImportError:  # standalone by-path import - load the sibling directly
	import importlib.util as _importlib_util
	import os as _os

	_spec = _importlib_util.spec_from_file_location(
		"tender_award_ledger_pricing_bands",
		_os.path.join(
			_os.path.dirname(_os.path.abspath(__file__)), "pricing_bands.py"
		),
	)
	_pricing_bands = _importlib_util.module_from_spec(_spec)
	_spec.loader.exec_module(_pricing_bands)
	bid_pricing_band = _pricing_bands.bid_pricing_band
	card_index = _pricing_bands.card_index


# The Tender Bid status vocabulary (update_bid_status.VALID_STATUSES).
BID_STATUSES = ("Watching", "Preparing", "Submitted", "Awarded", "Lost", "Withdrawn")
DECIDED_STATUSES = ("Awarded", "Lost")

# OCDS ocid shape on this feed: ocds-{registered prefix}-{sequential id}
# (eTenders: ocds-9t57fa-166390). Deterministic shape check, no fuzz.
OCID_RE = re.compile(r"^ocds-[0-9a-z]{6}-\S+$")

# Amount-quality flags, exactly the committed CSV's amount_flag classes
# (Award-Outcomes-Research section 2): flagged, NEVER dropped.
AMOUNT_FLAG_MAX_LOW = 100  # non-zero below R100 -> lt_R100
AMOUNT_FLAG_MIN_HIGH = 10_000_000_000  # above R10bn -> gt_R10bn

# Supplier strings the feed uses as non-winner placeholders (the research
# doc's Midvaal "non-award" rows and the "None" / single-character class).
# Whitelisted literals plus the single-character rule - no fuzzy matching.
PLACEHOLDER_SUPPLIERS = ("non-award", "none", "n/a", "not awarded", "no award")

LEDGER_SEMANTICS = (
	"deterministic award-outcome ledger: counters over the user's OWN "
	"decided bids plus published-award matches for their claimed ocids - "
	"counts, deltas and medians for market-context-style calibration and "
	"the user's own record; no model, NEVER a win probability"
)

# The honesty layer, carried on every payload (Award-Outcomes-Research
# sections 2 and 8 - the dataset's own bounds ARE the design constraint).
LEDGER_CAVEATS = [
	"winner-side feed: the public award record publishes successes only "
	"(every award 'active'), so win/loss base rates are unobservable - "
	"this ledger calibrates market context and records your own history, "
	"it NEVER computes or implies a win probability",
	"publication is severely buyer-skewed (19.95% of releases carry an "
	"award block; SARS 75.74% and Justice 71.96% vs ESKOM 9.87% and "
	"Tshwane / Johannesburg / Mnquma 0.00%) - a claimed tender at a "
	"non-publishing buyer will simply never match, so 'no award "
	"published' is NEVER evidence the bid was lost",
	"only 72.01% of published award blocks carry a usable non-zero "
	"amount - amounts ride flagged (zero / lt_R100 / gt_R10bn), never "
	"dropped, and read as contract-total semantics, not unit prices",
	"the feed carries no award dates at all - the release date is the "
	"only (weak) proxy for when an award surfaced, award lag is "
	"unmeasurable, and awards published after the ingester's trailing "
	"re-fetch window are only recoverable by re-enumerating old ids",
]

OWN_OUTCOMES_PRIVACY = (
	"per-subscriber PRIVATE data: computed from this user's own Tender "
	"Bid records and served only to them (get_my_bids scoping) - never "
	"aggregated across subscribers, never published"
)

# Match-row notes (fixed strings so clients and tests key off them).
NOTE_NO_OCID = (
	"tender_slug does not resolve to an OCDS ocid - nothing to match"
)
NOTE_NO_RELEASE = (
	"no re-fetched release cached for this ocid yet - either the ingester "
	"has not covered it or the award surfaced after the trailing re-fetch "
	"window (older ids need re-enumeration)"
)
NOTE_NO_AWARD = (
	"no award published for this ocid - with this feed's buyer-skewed "
	"publication that is NEVER evidence the bid was lost"
)
NOTE_AWARD_PUBLISHED = (
	"published award recorded from the winner-side feed - the bid status "
	"is never auto-flipped; update your own outcome if this settles it"
)


def _num(value):
	"""Float or None - never guesses on junk input."""
	if value is None:
		return None
	try:
		result = float(value)
	except (TypeError, ValueError):
		return None
	if result != result:  # NaN
		return None
	return result


def amount_flag(amount):
	"""The committed CSV's amount_flag classes for one award amount:
	``zero`` / ``lt_R100`` / ``gt_R10bn`` / None (clean). A missing or
	non-numeric amount returns ``missing`` - the 27.99%-of-blocks class
	the 72.01% usable-value bound describes."""
	value = _num(amount)
	if value is None:
		return "missing"
	if value == 0:
		return "zero"
	if 0 < value < AMOUNT_FLAG_MAX_LOW:
		return "lt_R100"
	if value > AMOUNT_FLAG_MIN_HIGH:
		return "gt_R10bn"
	return None


def is_placeholder_supplier(name):
	"""True for the feed's non-winner placeholder strings ('non-award',
	'None', single characters). Whitelist + length rule only."""
	normalized = " ".join(str(name or "").strip().lower().split()).rstrip(".,;:")
	if not normalized:
		return True
	if normalized in PLACEHOLDER_SUPPLIERS:
		return True
	return len(normalized) == 1


def looks_like_ocid(value):
	"""Deterministic OCDS-ocid shape check (ocds-{prefix}-{id})."""
	return bool(OCID_RE.match(str(value or "")))


def resolve_bid_ocid(bid, cards_by_key=None):
	"""The claimed tender's ocid, or None.

	A bid's ``tender_slug`` holds whatever key the claim used (slug OR
	tender_number - find_tender_by_slug's contract). On this catalog the
	ocid rides as the card's ``tender_number`` (e.g. ocds-9t57fa-155126),
	so: the slug itself when ocid-shaped, else the matched card's
	tender_number when THAT is ocid-shaped, else None (advert sources
	without OCDS ids simply never match - no fallback guessing)."""
	slug = str((bid or {}).get("tender_slug") or "")
	if looks_like_ocid(slug):
		return slug
	card = (cards_by_key or {}).get(slug)
	if card:
		tender_number = str(card.get("tender_number") or "")
		if looks_like_ocid(tender_number):
			return tender_number
	return None


def extract_awards(release):
	"""The published award blocks of one compiled OCDS release.

	Detection is a NON-EMPTY ``awards[]`` ONLY: this feed tags every
	release ``["compiled"]``, so tags carry no award signal and are
	deliberately never read. Returns [] for a missing / empty / non-list
	awards field (the 80.05% no-award-published class and the "{}"
	placeholder release alike).

	Every award row carries: the named winner (first supplier - the feed
	publishes exactly one supplier per award) with its placeholder flag,
	the amount with its quality flag (flagged, never dropped), and
	``award_date`` None + the release date as ``date_proxy`` - the feed
	structurally carries no award dates."""
	release = release if isinstance(release, dict) else {}
	awards = release.get("awards")
	if not isinstance(awards, list) or not awards:
		return []
	release_date = str(release.get("date") or "") or None
	rows = []
	for award in awards:
		if not isinstance(award, dict):
			continue
		suppliers = award.get("suppliers")
		suppliers = suppliers if isinstance(suppliers, list) else []
		names = [
			str(s.get("name"))
			for s in suppliers
			if isinstance(s, dict) and s.get("name") is not None
		]
		winner = names[0] if names else None
		value = award.get("value") if isinstance(award.get("value"), dict) else {}
		amount = _num(value.get("amount"))
		flag = amount_flag(value.get("amount"))
		rows.append(
			{
				"winner": winner,
				"winner_placeholder": is_placeholder_supplier(winner),
				"supplier_count": len(names),
				"value_rand": amount,
				"currency": value.get("currency"),
				"amount_flag": flag,
				"value_usable": amount is not None and flag is None,
				"status": award.get("status"),
				# No award dates on this feed - ever. The release date is
				# the only (weak) proxy for when the award surfaced.
				"award_date": None,
				"date_proxy": release_date,
			}
		)
	return rows


def match_bid_awards(bids, releases_by_ocid, cards_by_key=None):
	"""Joins the user's claimed tenders against re-fetched releases.

	``releases_by_ocid``: ocid -> parsed release dict (from Raw Tender
	Cache; absent keys mean the ingester holds nothing for that ocid).
	One row per bid, reporting - never deciding: a published award adds
	the winner block; an awardless release or a missing cache row states
	exactly what is (not) known, and NEVER reads as "lost"."""
	releases_by_ocid = releases_by_ocid or {}
	rows = []
	summary = {
		"claimed": 0,
		"with_ocid": 0,
		"release_cached": 0,
		"published_award": 0,
		"no_award_published": 0,
	}
	for bid in bids or []:
		summary["claimed"] += 1
		ocid = resolve_bid_ocid(bid, cards_by_key)
		row = {
			"bid": bid.get("name"),
			"tender_slug": bid.get("tender_slug"),
			"tender_title": bid.get("tender_title"),
			"institution": bid.get("institution"),
			"bid_status": bid.get("status"),
			"ocid": ocid,
			"release_cached": False,
			"release_date": None,
			"published_award": False,
			"awards": [],
			"note": NOTE_NO_OCID,
		}
		if ocid:
			summary["with_ocid"] += 1
			release = releases_by_ocid.get(ocid)
			if not isinstance(release, dict) or not release.get("ocid"):
				row["note"] = NOTE_NO_RELEASE
			else:
				summary["release_cached"] += 1
				row["release_cached"] = True
				row["release_date"] = str(release.get("date") or "") or None
				awards = extract_awards(release)
				if awards:
					summary["published_award"] += 1
					row["published_award"] = True
					row["awards"] = awards
					row["note"] = NOTE_AWARD_PUBLISHED
				else:
					summary["no_award_published"] += 1
					row["note"] = NOTE_NO_AWARD
		rows.append(row)
	return {"matches": rows, "summary": summary}


def band_position(value, band):
	"""Places one rand value against a pricing-band block (median / IQR
	from ``pricing_bands.bid_pricing_band``): ratio to the median plus a
	below/within/above-IQR position. None when either side is missing -
	never a guess."""
	value = _num(value)
	if value is None or not band:
		return None
	median = _num(band.get("median_rand"))
	if not median:
		return None
	iqr = band.get("iqr_rand") or (None, None)
	position = None
	low, high = _num(iqr[0]), _num(iqr[1])
	if low is not None and high is not None:
		if value < low:
			position = "below_iqr"
		elif value > high:
			position = "above_iqr"
		else:
			position = "within_iqr"
	return {
		"ratio_to_median_pct": round(value / median * 100.0, 1),
		"position": position,
		"band_level": band.get("level"),
		"band_median_rand": median,
	}


def quoted_vs_awarded_rows(bids, cards_by_key=None, tables=None):
	"""Quoted-vs-awarded value deltas for the user's OWN Awarded bids.

	One row per Awarded bid carrying at least one of estimated_value
	(the quote) / outcome_value (what was actually awarded): the rand and
	percent delta where both exist, each value additionally placed
	against the same market-context pricing band the bid was shown
	(band selection delegated verbatim to pricing_bands - absent bands
	stay absent, never guessed)."""
	rows = []
	for bid in bids or []:
		if str(bid.get("status") or "") != "Awarded":
			continue
		quoted = _num(bid.get("estimated_value"))
		awarded = _num(bid.get("outcome_value"))
		if quoted is None and awarded is None:
			continue
		row = {
			"bid": bid.get("name"),
			"tender_slug": bid.get("tender_slug"),
			"tender_title": bid.get("tender_title"),
			"institution": bid.get("institution"),
			"quoted_rand": quoted,
			"awarded_rand": awarded,
			"delta_rand": None,
			"delta_pct": None,
			"quoted_band_position": None,
			"awarded_band_position": None,
			"band_headline": None,
		}
		if quoted is not None and awarded is not None:
			row["delta_rand"] = awarded - quoted
			if quoted > 0:
				row["delta_pct"] = round((awarded - quoted) / quoted * 100.0, 1)
		card = (cards_by_key or {}).get(str(bid.get("tender_slug") or ""))
		band = bid_pricing_band(card, tables=tables) if card else None
		if band:
			row["quoted_band_position"] = band_position(quoted, band)
			row["awarded_band_position"] = band_position(awarded, band)
			row["band_headline"] = band.get("headline")
		rows.append(row)
	return rows


def aggregate_own_outcomes(bids, cards_by_key=None, tables=None):
	"""Counters over one user's own bids (already scoped by the caller).

	Counts by status, decided total, win rate as a share of DECIDED bids
	only (None when nothing is decided - no rate over zero), per-buyer
	counters (rates only where that buyer has decided bids), and the
	quoted-vs-awarded delta rows. Counts and shares of the user's own
	record - never a probability of winning anything future."""
	bids = list(bids or [])
	by_status = {status: 0 for status in BID_STATUSES}
	for bid in bids:
		status = str(bid.get("status") or "")
		if status in by_status:
			by_status[status] += 1
	awarded = by_status["Awarded"]
	lost = by_status["Lost"]
	decided = awarded + lost
	win_rate = None
	if decided:
		win_rate = {
			"awarded": awarded,
			"decided": decided,
			"rate_pct": round(awarded / decided * 100.0, 1),
			"semantics": (
				"share of this user's OWN decided bids (awarded vs lost) - "
				"a historical record over small N, never a probability of "
				"winning the next bid"
			),
		}
	buyers = {}
	for bid in bids:
		buyer = str(bid.get("institution") or "") or "(unknown buyer)"
		entry = buyers.setdefault(
			buyer,
			{"buyer": buyer, "tracked": 0, "decided": 0, "awarded": 0,
			 "lost": 0, "rate_pct": None},
		)
		entry["tracked"] += 1
		status = str(bid.get("status") or "")
		if status in DECIDED_STATUSES:
			entry["decided"] += 1
			key = "awarded" if status == "Awarded" else "lost"
			entry[key] += 1
	per_buyer = sorted(
		buyers.values(), key=lambda e: (-e["tracked"], e["buyer"])
	)
	for entry in per_buyer:
		if entry["decided"]:
			entry["rate_pct"] = round(
				entry["awarded"] / entry["decided"] * 100.0, 1
			)
	return {
		"tracked": len(bids),
		"by_status": by_status,
		"decided": decided,
		"awaiting_outcome": by_status["Submitted"],
		"win_rate": win_rate,
		"per_buyer": per_buyer,
		"quoted_vs_awarded": quoted_vs_awarded_rows(
			bids, cards_by_key=cards_by_key, tables=tables
		),
		"privacy": OWN_OUTCOMES_PRIVACY,
	}


def build_award_ledger(bids, releases_by_ocid, cards=None, tables=None):
	"""The full two-half ledger payload for one user's bids.

	``bids`` must already be scoped to the requesting user; ``cards`` is
	the cached published catalog (for slug -> ocid resolution and the
	pricing-band context); ``releases_by_ocid`` the re-fetched compiled
	releases for the claimed ocids. Pure assembly - the endpoint adds
	only the frappe glue."""
	cards_by_key = card_index(cards or [])
	return {
		"own_outcomes": aggregate_own_outcomes(
			bids, cards_by_key=cards_by_key, tables=tables
		),
		"published_matches": match_bid_awards(
			bids, releases_by_ocid, cards_by_key=cards_by_key
		),
		"semantics": LEDGER_SEMANTICS,
		"caveats": list(LEDGER_CAVEATS),
	}
