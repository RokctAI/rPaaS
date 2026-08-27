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

"""Market-context lookups for the suitability scorer.

Resolves the derived award-outcome reference tables (built from the
committed eTenders awards dataset ``tender/awards-dataset/awards_only.csv``,
32,589 published award rows, snapshot 2026-08-20 - see
``tender/Award-Outcomes-Research.md``) against one opportunity card:

- **buyer stats**: award count, publication behaviour, entrant share
  ("small entrants win X% of published awards at this buyer"), at-buyer
  incumbency concentration - matched by normalized buyer name with a
  corpus-wide default fallback;
- **typical winning-price band**: median + IQR of flag-clean published
  award amounts, resolved down a fixed fallback chain
  buyer -> category x province -> category -> province -> absent, each
  level published only where its cell holds N >= 30 clean amounts (the
  research report's discipline: medians of tight comparable sets, never
  means).

Everything here is pure data lookup over a committed JSON fixture
(``data/market_context.json``): no AI, no network, no fuzzy matching.
The fixture is generated deterministically by
``tender/frappe/tools/build_market_context.py`` - regenerate it whenever
the awards dataset refreshes; ``verify_market_context.py`` re-runs the
generator and fails when the committed tables drift from the dataset.

Honesty limits carried as machine-readable caveats: the awards feed
publishes successes only (no win/loss base rates -> no win probability),
19.95% of releases carry an award block with severe per-buyer
publication bias, and amounts read as contract-total semantics. The
market context NEVER moves gates and never predicts winning - it prices
the market the card lives in.
"""

import json
import os
import re

# Cached parsed tables (the fixture is immutable data committed with the
# code; load once per process).
_TABLES_CACHE = None

DATA_PATH = os.path.join(
	os.path.dirname(os.path.abspath(__file__)), "data", "market_context.json"
)

# Corporate-suffix tokens stripped (right to left) from a normalized buyer
# name before the suffix-stripped match: "eskom soc ltd" -> "eskom".
# Whitelisted tokens only - never a fuzzy merge.
BUYER_SUFFIX_TOKENS = (
	"soc", "ltd", "limited", "pty", "(pty)", "(soc)", "(ltd)", "inc",
)

# Price-band fallback chain, most-comparable first. Each level is
# published in the fixture only where the cell held N >= 30 flag-clean
# amounts, so a lookup that reaches no level returns NO band (absent -
# never a guess).
PRICE_BAND_LEVELS = ("buyer", "category_province", "category", "province")

# Card-category -> coarse OCDS mainProcurementCategory mapping. The
# awards dataset only carries the coarse category (services / goods /
# works), while cards carry the detailed eTenders taxonomy - this
# whitelist bridges them deterministically. Order: exact works set, then
# goods prefixes, then the services default for the activity taxonomy.
WORKS_CATEGORIES = (
	"civil engineering",
	"construction",
	"construction of buildings",
	"specialised construction activities",
	"services: building",
	"services: civil",
)
GOODS_PREFIXES = ("supplies:", "manufacture", "manufacturing", "other manufacturing")
# Categories too generic to map - the band lookup skips the category
# levels and falls through to province.
UNMAPPED_CATEGORIES = ("general procurement", "disposals: general", "")

RE_PARENTHETICAL = re.compile(r"\(([^)]{2,40})\)")


def _normalize(value):
	"""Lowercases and collapses whitespace (rules.normalize_text doctrine,
	duplicated here so the module imports standalone and the GENERATOR can
	share it without dragging in the rules module)."""
	return " ".join(str(value or "").lower().split())


def normalize_buyer(name):
	"""Normalized buyer key: lowercase, whitespace-collapsed, trailing
	punctuation stripped. The generator uses the same function, so table
	keys and lookups match by construction."""
	return _normalize(name).rstrip(".,;:")


def strip_buyer_suffixes(normalized):
	"""Removes whitelisted corporate suffix tokens from the right end of a
	normalized buyer name ("eskom soc ltd" -> "eskom")."""
	tokens = str(normalized or "").split()
	while tokens and tokens[-1] in BUYER_SUFFIX_TOKENS:
		tokens.pop()
	return " ".join(tokens)


def buyer_aliases(buyer_name):
	"""Deterministic alias keys for one buyer table entry: the normalized
	name, its suffix-stripped form, the name with parentheticals removed,
	and any parenthetical acronym ("... (SANRAL)" -> "sanral")."""
	normalized = normalize_buyer(buyer_name)
	aliases = {normalized}
	stripped = strip_buyer_suffixes(normalized)
	if stripped:
		aliases.add(stripped)
	without_parens = normalize_buyer(RE_PARENTHETICAL.sub(" ", str(buyer_name or "")))
	if without_parens:
		aliases.add(without_parens)
		stripped_parens = strip_buyer_suffixes(without_parens)
		if stripped_parens:
			aliases.add(stripped_parens)
	for match in RE_PARENTHETICAL.finditer(str(buyer_name or "")):
		acronym = normalize_buyer(match.group(1))
		# Only short single-token parentheticals are acronyms (SANRAL,
		# CSIR) - "(Including Cleaning...)" style text never aliases.
		if acronym and " " not in acronym and 2 <= len(acronym) <= 12:
			aliases.add(acronym)
	return aliases


def coarse_category(card_category):
	"""Maps a card's detailed eTenders category to the awards dataset's
	coarse mainProcurementCategory (works / goods / services), or None
	for the generic buckets that map to nothing."""
	normalized = _normalize(card_category)
	if normalized in UNMAPPED_CATEGORIES:
		return None
	if normalized in WORKS_CATEGORIES:
		return "works"
	if any(normalized.startswith(prefix) for prefix in GOODS_PREFIXES):
		return "goods"
	# The remaining taxonomy ("Services: ...", the activity categories
	# like "Human health activities") describes procured services.
	return "services"


def load_market_tables(path=None):
	"""Loads (and caches) the committed market-context tables; returns None
	when the fixture is absent (the scorer then reports the block as
	unavailable instead of failing)."""
	global _TABLES_CACHE
	if path is None:
		if _TABLES_CACHE is not None:
			return _TABLES_CACHE
		path = DATA_PATH
	try:
		with open(path, encoding="utf-8") as fh:
			tables = json.load(fh)
	except (OSError, ValueError):
		return None
	if path == DATA_PATH:
		_TABLES_CACHE = tables
	return tables


def _buyer_lookup_index(tables):
	"""alias -> buyer key index, built once per tables dict and memoised on
	it. Collisions resolve to the buyer with the MOST awards (stable:
	count desc, then key asc)."""
	index = tables.get("_alias_index")
	if index is not None:
		return index
	index = {}
	buyers = tables.get("buyers") or {}
	ranked = sorted(
		buyers.items(),
		key=lambda item: (-(item[1].get("award_count") or 0), item[0]),
	)
	for key, entry in ranked:
		for alias in buyer_aliases(entry.get("buyer") or key):
			index.setdefault(alias, key)
	tables["_alias_index"] = index
	return index


def resolve_buyer(institution, tables):
	"""Resolves a card's institution to a buyer table entry.

	Returns (entry, match_type): match_type is ``exact`` (normalized name
	is a table key), ``alias`` (suffix-stripped / parenthetical-acronym
	alias hit), or ``default`` with the corpus-wide default entry.
	"""
	buyers = tables.get("buyers") or {}
	normalized = normalize_buyer(institution)
	if normalized and normalized in buyers:
		return buyers[normalized], "exact"
	index = _buyer_lookup_index(tables)
	for candidate in (normalized, strip_buyer_suffixes(normalized)):
		if candidate and candidate in index:
			return buyers[index[candidate]], "alias"
	return tables.get("default_buyer") or {}, "default"


def _band_from(cell, level, basis):
	return {
		"level": level,
		"basis": basis,
		"median_rand": cell.get("median_rand"),
		"iqr_rand": cell.get("iqr_rand"),
		"n": cell.get("n"),
		"semantics": (
			"published contract-total award amounts, flag-cleaned; median/IQR "
			"only (means are unusable - corpus mean is 23x the median)"
		),
	}


def resolve_price_band(tables, buyer_entry, match_type, category, province):
	"""Typical winning-price band down the fixed fallback chain.

	buyer (matched, N >= 30) -> category x province cell -> category ->
	province -> None. Every published level already respects the N >= 30
	discipline; the chain never averages across levels.
	"""
	if (
		match_type != "default"
		and buyer_entry.get("median_rand") is not None
		and (buyer_entry.get("benchmark_count") or 0) >= 30
	):
		return _band_from(
			{
				"median_rand": buyer_entry.get("median_rand"),
				"iqr_rand": buyer_entry.get("iqr_rand"),
				"n": buyer_entry.get("benchmark_count"),
			},
			"buyer",
			"buyer={0}".format(buyer_entry.get("buyer")),
		)
	coarse = coarse_category(category)
	province_key = _normalize(province)
	if coarse and province_key:
		cell = (tables.get("category_province") or {}).get(
			coarse + "|" + province_key
		)
		if cell:
			return _band_from(
				cell,
				"category_province",
				"category={0}, province={1}".format(coarse, province_key),
			)
	if coarse:
		cell = (tables.get("category") or {}).get(coarse)
		if cell:
			return _band_from(cell, "category", "category={0}".format(coarse))
	if province_key:
		cell = (tables.get("province") or {}).get(province_key)
		if cell:
			return _band_from(cell, "province", "province={0}".format(province_key))
	return None


def resolve_market_context(card, tables=None):
	"""Builds the ``market_context`` payload block for one tender card.

	Additive and self-describing: ``available`` False (with a reason) when
	the fixture is missing; otherwise buyer stats (matched or the
	corpus-wide default), the typical winning-price band with its table
	level, and the honesty caveats. Never gates, never scores.
	"""
	card = card or {}
	if tables is None:
		tables = load_market_tables()
	if not tables:
		return {
			"available": False,
			"reason": "market-context tables not present (data/market_context.json)",
		}
	institution = card.get("institution") or card.get("organization")
	entry, match_type = resolve_buyer(institution, tables)
	buyer_stats = {
		"matched": match_type != "default",
		"match_type": match_type,
		"buyer": entry.get("buyer"),
		"award_count": entry.get("award_count"),
		"benchmark_count": entry.get("benchmark_count"),
		"entrant_share_pct": entry.get("entrant_share_pct"),
		"incumbency_share_pct": entry.get("incumbency_share_pct"),
		"zero_amount_share_pct": entry.get("zero_amount_share_pct"),
		"publication_rate_pct": entry.get("publication_rate_pct"),
		"publication_behavior": entry.get("publication_behavior"),
	}
	if entry.get("entrant_share_pct") is not None:
		scope = (
			"at this buyer" if match_type != "default"
			else "across the published corpus (buyer not in the awards table)"
		)
		buyer_stats["entrant_note"] = (
			"small entrants (<= 2 lifetime wins in the published record) win "
			"{0}% of published awards {1}".format(entry["entrant_share_pct"], scope)
		)
	band = resolve_price_band(
		tables, entry, match_type, card.get("category"), card.get("province")
	)
	meta = tables.get("meta") or {}
	context = {
		"available": True,
		"dataset": {
			"source": meta.get("source"),
			"snapshot_date": meta.get("snapshot_date"),
			"awards": meta.get("awards"),
			"benchmark_rows": meta.get("benchmark_rows"),
		},
		"buyer_stats": buyer_stats,
		"coarse_category": coarse_category(card.get("category")),
		"price_band": band,
		"caveats": [
			"published-award records only: 19.95% of releases carry an award "
			"block, with severe per-buyer publication bias - absence from the "
			"feed is a channel gap, not evidence of no awards",
			"the feed records successes only (all awards 'active'), so "
			"win/loss base rates are unobservable - this context prices the "
			"market, it NEVER predicts winning",
			"amounts read as contract-total (possibly multi-year framework) "
			"values, not unit line prices",
		],
	}
	if band is None:
		context["caveats"].insert(
			0,
			"no price band: no comparable cell reached the N>=30 discipline "
			"for this buyer/category/province",
		)
	return context
