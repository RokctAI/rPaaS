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

"""Advert-only source-record detection and enrichment coverage (findings F-08).

Advert-only registry records (~1.7KB: description, closing, contact, a link
to the advert PDF) bound what the compliance layer can confirm - the
checklist beyond the universal spine, the real functionality matrix, even
the threshold are all DERIVED, not grounded, for a bid created from one.
This module classifies a catalog record as "Full" or "Advert-Only" with a
pure, deterministic heuristic and computes per-category enrichment stats so
thin categories are visible before bid/no-bid.

Calibration (live published catalog, 2026-08-20): all 517 records in
published/api/tenders.json carry the same advert-level key set and
serialize to 859-1813 bytes; none embeds pack content inline. Registry-side
full records keep their extracted pack text in a ``{slug}_content.md`` the
catalog does NOT publish, so the SDK-visible signals of fullness are:

1. an ``advanced_enrichment`` entry for the slug in meta.json (pack-derived
   tasks - the same signal claim_tender uses for enrichment_level), or
2. an inline pack-content field on the record itself
   (``params.pack_content_fields``), or
3. a serialized record larger than ``params.advert_only_max_bytes`` -
   defensive headroom above the largest advert-level record observed live
   (1,813 bytes; the finding's "~1.7KB each").

The thresholds ship as data on the GATE-PACK-COLLECT rule's ``params`` so
the desk can recalibrate without a code change. Pure functions, no AI.

Composition-independent on purpose (findings F-09): no frappe import at
module level, so samples/tests/CI can import it standalone by file path.
"""

import json

FULL = "Full"
ADVERT_ONLY = "Advert-Only"

# Defaults mirrored in the GATE-PACK-COLLECT fixture's params; the fixture
# wins when present (load_gate_params) - these keep the pure functions
# usable standalone.
DEFAULT_PARAMS = {
	"advert_only_max_bytes": 2048,
	"pack_content_fields": [
		"advanced_enrichment",
		"pack_content",
		"content",
		"documents_content",
	],
}


def _merged_params(params):
	merged = dict(DEFAULT_PARAMS)
	if isinstance(params, dict):
		merged.update({k: v for k, v in params.items() if v not in (None, "")})
	return merged


def classify_source_record(record, enrichment_entry=None, params=None):
	"""Classifies one catalog record as "Full" or "Advert-Only".

	Deterministic field/byte checks only. ``record`` is the tender item from
	the published catalog (tenders.json); ``enrichment_entry`` is the slug's
	``advanced_enrichment`` entry from meta.json, or None.
	"""
	if not isinstance(record, dict) or not record:
		return ADVERT_ONLY
	merged = _merged_params(params)

	# 1. pack-derived enrichment published for this slug
	if isinstance(enrichment_entry, dict) and enrichment_entry.get("tasks"):
		return FULL

	# 2. inline pack content on the record itself
	for field in merged.get("pack_content_fields") or []:
		if record.get(field):
			return FULL

	# 3. record substantially larger than the advert-level shape
	try:
		size = len(json.dumps(record, default=str))
	except (TypeError, ValueError):
		size = 0
	if size > int(merged.get("advert_only_max_bytes") or 0):
		return FULL

	return ADVERT_ONLY


def enrichment_stats(records, enrichment_map=None, params=None):
	"""Per-category counts of full vs advert-only records (pure function).

	Returns ``{"total", "full", "advert_only", "categories": {category:
	{"total", "full", "advert_only", "advert_only_pct"}}}`` computed over the
	cached published catalog - the coverage metric findings F-08 asks for.
	"""
	enrichment_map = enrichment_map if isinstance(enrichment_map, dict) else {}
	categories = {}
	total_full = 0
	total_advert = 0
	for record in records or []:
		if not isinstance(record, dict):
			continue
		slug = record.get("slug") or record.get("tender_number") or record.get("ocid")
		entry = enrichment_map.get(slug) if slug else None
		verdict = classify_source_record(record, entry, params)
		category = record.get("category") or "Uncategorised"
		bucket = categories.setdefault(
			category, {"total": 0, "full": 0, "advert_only": 0, "advert_only_pct": 0.0}
		)
		bucket["total"] += 1
		if verdict == FULL:
			bucket["full"] += 1
			total_full += 1
		else:
			bucket["advert_only"] += 1
			total_advert += 1
	for bucket in categories.values():
		if bucket["total"]:
			bucket["advert_only_pct"] = round(
				bucket["advert_only"] / bucket["total"] * 100.0, 1
			)
	return {
		"total": total_full + total_advert,
		"full": total_full,
		"advert_only": total_advert,
		"categories": categories,
	}


def load_gate_params():
	"""Loads GATE-PACK-COLLECT's params from the fixture-shipped rule record.

	Frappe-touching by necessity, so imported lazily; falls back to
	DEFAULT_PARAMS when the rule (or frappe) is unavailable so the pure
	callers above always get a usable dict.
	"""
	try:
		import frappe

		raw = frappe.db.get_value("Tender Compliance Rule", "GATE-PACK-COLLECT", "params")
	except Exception:
		return dict(DEFAULT_PARAMS)
	if not raw:
		return dict(DEFAULT_PARAMS)
	try:
		parsed = json.loads(raw) if isinstance(raw, str) else raw
	except (TypeError, ValueError):
		return dict(DEFAULT_PARAMS)
	return _merged_params(parsed if isinstance(parsed, dict) else None)
