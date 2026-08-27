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

"""Preference-aware tender delivery (opt-in personalization).

Pure, frappe-free filtering and ranking of a catalog-card list against one
Tender Business Profile snapshot - the OPT-IN layer behind the
``personalized`` parameter of ``get_relevant_tenders``. Callers that never
opt in are untouched: the endpoint returns the exact legacy passthrough
(the SDK backward-compat rule), and this module is never even imported on
that path.

The comparison logic is NOT re-implemented here: the sector and geography
factors are the suitability engine's own pure functions
(``suitability._factor_sector`` / ``suitability._factor_geography``),
imported so a declared sector or province means exactly the same thing in
the daily delivery as it does in "Check my fit". On top of them this
module only decides three deterministic things:

- **drop**: a card whose province EXPLICITLY mismatches the profile's
  declared operating provinces (the factor's ``GEO-MISMATCH`` reason) is
  dropped. National / unspecified-province cards and cards scored against
  a profile with no declared provinces are always kept - positive
  evidence only, an unknown never filters;
- **rank**: cards sort by the deterministic sector-match value, ties kept
  in catalog order (stable sort). Unknown sector fit (no declared
  sectors) ranks between a capability overlap and an explicit mismatch -
  an unknown is never punished below a known mismatch;
- **annotate**: each returned card carries a lightweight additive
  ``preference_fit`` block (band + machine-readable reason codes), so the
  tenant-side consumer can render "why this is here" without re-scoring.

No probabilities, no AI, no per-subscriber data: the input list is the
same public catalog every caller sees - personalization only reorders,
filters and annotates it for the caller's OWN profile.
"""

# Same-package imports (F-09 pattern): relative on a composed bench, importlib
# fallback keeps this module importable standalone by file path.
try:
	from .suitability import _factor_geography, _factor_sector
except ImportError:  # standalone by-path import - load the sibling directly
	import importlib.util as _importlib_util
	import os as _os

	_spec = _importlib_util.spec_from_file_location(
		"tender_preference_suitability",
		_os.path.join(
			_os.path.dirname(_os.path.abspath(__file__)), "suitability.py"
		),
	)
	_suitability = _importlib_util.module_from_spec(_spec)
	_spec.loader.exec_module(_suitability)
	_factor_geography = _suitability._factor_geography
	_factor_sector = _suitability._factor_sector


# Fit bands over the sector factor's deterministic value (the factor
# returns 0.7-1.0 for declared-sector matches, 0.6 for capability-register
# overlap, None for an undeclared-sectors profile, 0.1 for an explicit
# mismatch). Documented, not fitted.
BAND_SECTOR_MATCH = "sector_match"
BAND_CAPABILITY_OVERLAP = "capability_overlap"
BAND_UNKNOWN = "unknown"
BAND_OUTSIDE_SECTORS = "outside_declared_sectors"

# Rank stand-in for an unknown sector value: between capability overlap
# (0.6) and explicit mismatch (0.1) - an unknown never outranks a known
# match and is never punished below a known mismatch.
UNKNOWN_RANK_VALUE = 0.35

GEO_DROP_CODE = "GEO-MISMATCH"


def sector_band(value):
	"""Maps the sector factor's value to its lightweight fit band."""
	if value is None:
		return BAND_UNKNOWN
	if value >= 0.7:
		return BAND_SECTOR_MATCH
	if value >= 0.6:
		return BAND_CAPABILITY_OVERLAP
	return BAND_OUTSIDE_SECTORS


def personalize_tenders(items, profile):
	"""Filters, ranks and annotates catalog cards for one profile snapshot.

	``items`` is the legacy passthrough list (already filter-processed);
	``profile`` a Tender Business Profile snapshot in the
	``profile_snapshot`` shape the suitability endpoint builds. Returns a
	NEW list of card copies - the input list and its dicts are never
	mutated. Deterministic: identical inputs give identical output.
	"""
	profile = profile or {}
	ranked = []
	for index, item in enumerate(items or []):
		if not isinstance(item, dict):
			continue
		geo_value, geo_reasons = _factor_geography(item, profile)
		geo_code = (geo_reasons[0] or {}).get("code") if geo_reasons else None
		if geo_code == GEO_DROP_CODE:
			# Explicit province mismatch - the ONLY dropping condition.
			continue
		sector_value, sector_reasons = _factor_sector(item, profile)
		sector_reason = (sector_reasons[0] or {}) if sector_reasons else {}
		card = item.copy()
		card["preference_fit"] = {
			"band": sector_band(sector_value),
			"sector_code": sector_reason.get("code"),
			"sector_detail": sector_reason.get("detail"),
			"geo_code": geo_code,
			"semantics": (
				"deterministic profile fit annotation (declared sectors / "
				"provinces vs the public card) - never a win prediction"
			),
		}
		rank_value = sector_value if sector_value is not None else UNKNOWN_RANK_VALUE
		ranked.append((rank_value, index, card))
	# Stable, deterministic: sector value desc, catalog order for ties.
	ranked.sort(key=lambda entry: (-entry[0], entry[1]))
	return [card for _value, _index, card in ranked]
