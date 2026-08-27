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

"""Parse result -> the EXISTING capture surface, strictly as a preview.

The parser never invents a parallel data model: its output maps onto the
surfaces the desk already uses -

- proposed **Tender Bid Returnable** rows (the F-02 child table that
  apply_custom_returnables folds into the pack), each carrying the quoted
  source line as its ``guidance`` and, when the pack names a form whose
  code matches an existing Tender Form Template (e.g. "MBD 4"), that
  ``template_code`` so the pre-filled worksheet renders;
- proposed **field values** for the bid (closing_date,
  functionality_threshold, preference_system, submission_channel), each
  tagged propose / already-set-match / conflict / not-found against what
  the bid currently holds;
- **disagreement warnings** ([PARSE-CONFLICT]) whenever a QUOTED value
  contradicts a value the bid/catalog already carries - surfaced, never
  silently resolved in either direction.

NOTHING here writes anything. The endpoint applies SELECTED returnable
rows only on an explicit apply=1 (seed_bid_returnables convention);
proposed field values are never auto-applied at all - the desk sets them
by hand off the preview. Pure functions, no frappe import, no AI.

Template-code linking (F-02 follow-up fix 4): the documented list styles
put the MBD/SBD token in the item TITLE, not the ref code ("Annexure C"
whose title reads "MBD 4 DECLARATION OF INTEREST") - so linking matches
the ref_code first and then a LEADING "MBD n"/"SBD n(.n)" token from the
title, both exact-only against existing template codes, never fuzzy.
"""

import re

QUOTED = "QUOTED"
NOT_FOUND = "NOT-FOUND"

PARSE_CONFLICT_TAG = "[PARSE-CONFLICT]"
PARSE_SUGGEST_TAG = "[PARSE-PACK-AVAILABLE]"

# parsed list style -> Tender Bid Returnable category (Select options)
STYLE_CATEGORY = {
	"annexure": "Buyer Form",
	"form": "Buyer Form",
	"lettered": "Buyer Form",
	"numbered": "Technical Returnable",
	"paren-letter": "Technical Returnable",
	# O-01: bare MBD/SBD regime-code headings ("MBD 6.1" alone on its line)
	# are standard-regime buyer forms; their ref_code compacts straight to
	# the template code, so _template_code_for links them ("MBD 8" -> MBD8)
	"regime": "Buyer Form",
}

PARSE_SUGGESTION_WARNING = (
	"This bid was created from an advert-only record (GATE-PACK-COLLECT is "
	"open) but a pack file is now attached - run the deterministic pack "
	"parser (control:parse_tender_pack) to preview the pack's returnables "
	"and key values instead of typing them from scratch. "
	+ PARSE_SUGGEST_TAG
)


def _norm(value):
	return " ".join(str(value or "").lower().split())


def _template_code_for(ref_code, known_template_codes):
	"""An existing Tender Form Template code the pack's ref matches, or None.

	Exact match after stripping spaces/dots and case ('MBD 4' -> 'MBD4',
	'SBD 6.1' -> 'SBD6.1' when that code exists) - never fuzzy.
	"""
	if not known_template_codes:
		return None
	compact = str(ref_code or "").upper().replace(" ", "")
	candidates = {compact, compact.replace(".", "")}
	for code in known_template_codes:
		code_compact = str(code or "").upper().replace(" ", "")
		if code_compact and (
			code_compact in candidates
			or code_compact.replace(".", "") in candidates
		):
			return code
	return None


# a LEADING MBD/SBD token in an item title ("MBD 4 DECLARATION OF INTEREST",
# "SBD 6.1 - Preference Points Claim Form") - anchored at the start so an
# incidental mention mid-title never links (exact-only discipline)
RE_TITLE_TEMPLATE_TOKEN = re.compile(
	r"^\(?\s*((?:MBD|SBD)\s*\.?\s*\d+(?:\.\d+)?)\b", re.I
)


def _template_code_from_title(title, known_template_codes):
	"""The template code named by a LEADING MBD/SBD token in the item title,
	or None (F-02 follow-up fix 4: the documented styles carry the MBD/SBD
	token in the title, not the ref code). Same exact-only matching as
	``_template_code_for`` - the extracted token must equal an existing code
	after the identical compaction, never a fuzzy/contains match.
	"""
	if not known_template_codes:
		return None
	match = RE_TITLE_TEMPLATE_TOKEN.match(str(title or ""))
	if not match:
		return None
	return _template_code_for(match.group(1), known_template_codes)


def build_ingest_preview(parse_result, bid=None, known_template_codes=None):
	"""Maps one parse_pack_text result onto the bid's capture surfaces.

	``bid`` is a plain-dict snapshot of the Tender Bid (or None); only its
	closing_date, functionality_threshold, preference_system,
	submission_channel and custom_returnables are read. Returns::

	    {"proposed_returnables": [Tender Bid Returnable-shaped dicts],
	     "already_captured": [ref codes the bid already carries],
	     "proposed_fields": {field: {...}},
	     "warnings": [str],
	     "not_found": [parse keys that came back NOT-FOUND]}
	"""
	parse_result = parse_result or {}
	bid = bid or {}
	warnings = []

	proposed_rows, already = _propose_returnables(
		parse_result.get("returnables") or {},
		bid.get("custom_returnables") or [],
		known_template_codes,
	)

	fields = {
		"closing_date": _propose_field(
			parse_result.get("closing_date"), bid.get("closing_date"), warnings,
			label="closing date",
		),
		"functionality_threshold": _propose_field(
			parse_result.get("functionality"), bid.get("functionality_threshold"),
			warnings, label="functionality threshold",
			compare=_numbers_equal,
		),
		"preference_system": _propose_field(
			parse_result.get("preference_system"), bid.get("preference_system"),
			warnings, label="preference system",
		),
		"submission_channel": _propose_field(
			parse_result.get("submission_channel"), bid.get("submission_channel"),
			warnings, label="submission channel",
		),
	}

	pref = parse_result.get("preference_system") or {}
	if len(pref.get("all_hits") or []) > 1:
		systems = ", ".join(hit["system"] for hit in pref["all_hits"])
		warnings.append(
			f"The pack quotes MORE THAN ONE preference point system ({systems}) - "
			"a straddling/self-contradicting pack (findings F-12); confirm the "
			"operative system against the evaluation pages before setting it. "
			+ PARSE_CONFLICT_TAG
		)

	not_found = sorted(
		key for key, entry in parse_result.items()
		if isinstance(entry, dict) and entry.get("status") == NOT_FOUND
	)

	return {
		"proposed_returnables": proposed_rows,
		"already_captured": already,
		"proposed_fields": fields,
		"warnings": warnings,
		"not_found": not_found,
	}


def _propose_returnables(returnables, existing_rows, known_template_codes):
	"""Parsed items as Tender Bid Returnable-shaped dicts, skipping ref codes
	the bid already carries (the existing captured row always wins)."""
	existing_codes = {
		_norm(row.get("ref_code") if hasattr(row, "get") else getattr(row, "ref_code", None))
		for row in existing_rows or []
	} - {""}

	proposed = []
	already = []
	for item in returnables.get("items") or []:
		code = _norm(item.get("ref_code"))
		if not code:
			continue
		if code in existing_codes:
			already.append(item.get("ref_code"))
			continue
		existing_codes.add(code)
		proposed.append(
			{
				"ref_code": item.get("ref_code"),
				"title": item.get("title"),
				"mandatory": 1,
				"category": STYLE_CATEGORY.get(item.get("style"), "Attachment"),
				"kill_note": "",
				"template_code": (
					_template_code_for(item.get("ref_code"), known_template_codes)
					or _template_code_from_title(item.get("title"), known_template_codes)
				),
				"guidance": (
					f'Parsed from the pack ({QUOTED}): "{item.get("source_line")}" '
					"- verify this row against the pack before generating."
				),
			}
		)
	return proposed, already


def _numbers_equal(parsed, current):
	try:
		return float(parsed) == float(current)
	except (TypeError, ValueError):
		return _norm(parsed) == _norm(current)


def _propose_field(entry, current, warnings, label, compare=None):
	"""One proposed field value vs what the bid holds. Never applied here."""
	entry = entry or {}
	if entry.get("status") != QUOTED:
		return {
			"status": NOT_FOUND,
			"parsed_value": None,
			"current_value": current,
			"source_line": None,
			"action": "not-found",
		}
	parsed = entry.get("value")
	result = {
		"status": QUOTED,
		"parsed_value": parsed,
		"current_value": current,
		"source_line": entry.get("source_line"),
	}
	if current in (None, ""):
		result["action"] = "propose"
	elif (compare or (lambda a, b: _norm(a) == _norm(b)))(parsed, current):
		result["action"] = "already-set-match"
	else:
		result["action"] = "conflict"
		warnings.append(
			f"Parsed {label} disagrees with the bid: the pack quotes "
			f"'{parsed}' (\"{entry.get('source_line')}\") but the bid holds "
			f"'{current}'. Neither value was changed - resolve by hand. "
			+ PARSE_CONFLICT_TAG
		)
	return result


def parse_pack_suggestion_warning(checklist_rows, has_pack_file):
	"""The [PARSE-PACK-AVAILABLE] advisory, or None (pure function).

	Fires only when BOTH hold: the bid's checklist carries an OPEN
	GATE-PACK-COLLECT row (the bid started advert-only) and a pack file is
	now attached - the exact moment running the parser saves the desk the
	hand-capture.
	"""
	if not has_pack_file:
		return None
	for row in checklist_rows or []:
		get = row.get if hasattr(row, "get") else lambda key, _row=row: getattr(_row, key, None)
		if (get("rule_code") or "").strip().upper() == "GATE-PACK-COLLECT" and (
			get("status") or "Open"
		) != "Done":
			return PARSE_SUGGESTION_WARNING
	return None
