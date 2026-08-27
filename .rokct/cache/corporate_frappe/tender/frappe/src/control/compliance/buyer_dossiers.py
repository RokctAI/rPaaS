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

"""Buyer-dossier lookups: per-buyer behavioural stats from the published
awards record.

Resolves the derived buyer-dossier tables (built from the committed
eTenders awards dataset ``tender/awards-dataset/awards_only.csv``, 32,589
published award rows, snapshot 2026-08-20) against one buyer name:

- **volume**: award count, flag-clean benchmark count;
- **typical award value**: median + IQR of flag-clean amounts, published
  only at N >= 30 (medians only, never means);
- **supplier concentration**: top-supplier share and distinct-supplier
  count over IDENTIFIED awards (placeholder supplier identities - id
  "0", 37.6% of the corpus - excluded from the math, still counted in
  ``award_count``), published only at N >= 30 identified awards;
- **newcomer-openness proxy**: share of identified awards won by
  suppliers appearing exactly once at that buyer - a PROXY computed
  within the published-awards dataset only.

Everything here is pure data lookup over a committed JSON fixture
(``data/buyer_dossiers.json``): no AI, no network, no fuzzy matching.
The fixture is generated deterministically by
``tender/frappe/tools/build_buyer_dossiers.py``; ``verify_buyer_dossiers.py``
re-runs the generator and fails when the committed tables drift from the
dataset.

Matching mirrors ``market_context.py`` exactly (its normalisation and
alias machinery is imported, not re-implemented): exact normalized-name
hit, then the deterministic alias index (suffix-stripped forms,
parenthetical acronyms). There is deliberately NO corpus-wide default
dossier - an unmatched buyer gets ``matched: False`` and no stats,
because averaged behavioural stats across 581 buyers describe nobody.

Honesty limits carried as machine-readable caveats on every payload:
winner-side data only, severe publication-discipline bias, proxy
semantics for newcomer openness, the placeholder exclusion, and
upper-bound supplier counts.
"""

import json
import os

# Same-package imports (F-09 pattern): relative on a composed bench,
# importlib fallback keeps this module importable standalone by file path.
try:
	from .market_context import buyer_aliases, normalize_buyer, strip_buyer_suffixes
except ImportError:  # standalone by-path import - load the sibling directly
	import importlib.util as _importlib_util
	import os as _os

	_spec = _importlib_util.spec_from_file_location(
		"tender_dossiers_market_context",
		_os.path.join(
			_os.path.dirname(_os.path.abspath(__file__)), "market_context.py"
		),
	)
	_market_context = _importlib_util.module_from_spec(_spec)
	_spec.loader.exec_module(_market_context)
	buyer_aliases = _market_context.buyer_aliases
	normalize_buyer = _market_context.normalize_buyer
	strip_buyer_suffixes = _market_context.strip_buyer_suffixes

# Cached parsed tables (the fixture is immutable data committed with the
# code; load once per process).
_TABLES_CACHE = None

DATA_PATH = os.path.join(
	os.path.dirname(os.path.abspath(__file__)), "data", "buyer_dossiers.json"
)

# The honesty layer: carried on EVERY dossier payload so no client renders
# these stats as the buyer's full procurement behaviour.
DOSSIER_CAVEATS = [
	"winner-side data only: the feed publishes successful awards "
	"(all 'active'), so win/loss base rates are unobservable - a dossier "
	"describes published winners, it NEVER predicts winning",
	"publication-discipline bias: only 19.95% of releases carry an award "
	"block, with severe per-buyer variance - a thin or absent dossier is "
	"usually a channel gap (awards published elsewhere), not low activity",
	"newcomer-openness is a PROXY computed within the published-awards "
	"dataset only: 'appearing once at this buyer' in the published record "
	"does not prove the supplier was genuinely new to the buyer",
	"supplier concentration excludes placeholder supplier identities "
	"(supplier id '0', 37.6% of the corpus; plus a handful of placeholder "
	"names) - placeholders still count in award_count, and the identified/"
	"placeholder split is published with every dossier",
	"distinct-supplier counts are UPPER bounds: conservative name "
	"normalisation only (trim, casefold, parenthesised-form unwrap), no "
	"fuzzy merging - so top-supplier shares are lower bounds",
	"amounts read as contract-total (possibly multi-year framework) "
	"values, not unit line prices",
]


def load_dossier_tables(path=None):
	"""Loads (and caches) the committed buyer-dossier tables; returns None
	when the fixture is absent (callers then report the block as
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


def _alias_index(tables):
	"""alias -> buyer key index, built once per tables dict and memoised on
	it (market_context's construction: collisions resolve to the buyer
	with the MOST awards, stable by count desc then key asc)."""
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


def resolve_dossier(institution, tables):
	"""Resolves a buyer name to its dossier entry.

	Returns (entry, match_type): ``exact`` (normalized name is a table
	key), ``alias`` (suffix-stripped / parenthetical-acronym alias hit),
	or (None, ``none``) - deliberately no averaged default entry.
	"""
	buyers = tables.get("buyers") or {}
	normalized = normalize_buyer(institution)
	if normalized and normalized in buyers:
		return buyers[normalized], "exact"
	index = _alias_index(tables)
	for candidate in (normalized, strip_buyer_suffixes(normalized)):
		if candidate and candidate in index:
			return buyers[index[candidate]], "alias"
	return None, "none"


def resolve_buyer_dossier(institution, tables=None):
	"""Builds the buyer-dossier payload for one buyer name.

	Self-describing: ``available`` False (with a reason) when the fixture
	is missing; ``matched`` False (no stats, caveats explaining why) when
	the buyer is not in the published record; otherwise the dossier entry
	verbatim. Every payload carries the honesty caveats. Never gates,
	never scores, never predicts.
	"""
	if tables is None:
		tables = load_dossier_tables()
	if not tables:
		return {
			"available": False,
			"reason": "buyer-dossier tables not present (data/buyer_dossiers.json)",
		}
	entry, match_type = resolve_dossier(institution, tables)
	meta = tables.get("meta") or {}
	payload = {
		"available": True,
		"matched": entry is not None,
		"match_type": match_type,
		"buyer_input": str(institution or ""),
		"dossier": dict(entry) if entry else None,
		"dataset": {
			"source": meta.get("source"),
			"snapshot_date": meta.get("snapshot_date"),
			"awards": meta.get("awards"),
			"buyers": meta.get("buyers"),
			"min_amount_n": meta.get("min_amount_n"),
			"min_concentration_n": meta.get("min_concentration_n"),
		},
		"semantics": (
			"per-buyer behavioural stats computed deterministically from the "
			"published eTenders award record - aggregate public data only, "
			"medians/IQR never means, every stat N-gated; describes the "
			"published market, never predicts winning"
		),
		"caveats": list(DOSSIER_CAVEATS),
	}
	if entry is None:
		payload["caveats"].insert(
			0,
			"buyer not found in the published award record - most likely a "
			"publication channel gap (e.g. municipal buyers publish award "
			"notices on their own websites), not evidence of no awards",
		)
	return payload
