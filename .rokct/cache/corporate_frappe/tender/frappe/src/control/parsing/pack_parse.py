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

"""Deterministic pattern extraction over pack text (findings F-02 full).

Fixed regular-expression rules calibrated against the three returnable-list
styles the mock-samples corpus documents verbatim:

- RNM 8/2/RNM0614's T2.1 lettered schedule ("The tenderer must complete and
  return documents A1 to A21; B1 to B2; C1.1 and C3 ..." followed by
  "A1  Authority To Sign Documents" lines);
- DFFE B005's annexures ("Annexure A - Pricing Schedule", "Annexure B -
  CV template", "Annexure C - Consent and Indemnity Form") plus its
  numbered Phase-1 administrative list;
- Musina 18-2025/26's buyer form letters ("Form A - Form of Bid" ...
  "Form E") and its section-5.1 paren-lettered mandatory requirements.

Confidence model - exactly TWO levels, no fuzzy middle:

- ``QUOTED``: a verbatim pattern hit; the matched source line travels with
  the value so the desk can check the quote against the pack.
- ``NOT-FOUND``: the pattern did not hit. The parser never guesses,
  interpolates or "best-efforts" a value - a pack outside the standard
  formats simply comes back NOT-FOUND and the desk captures by hand,
  exactly as before.

Calibration round (F-02 follow-up, verified against the REAL Musina buyer
PDF - 65 pages, full text layer):

- list markers accept the dot style the real pack uses ("a." as well as
  "a)" / "(a)");
- a bare "Form A" / "Annexure C" heading joins forward to its title on the
  following lines (the buyer's PDF puts the form letter and its ALL-CAPS
  title on separate lines);
- every scalar finder tolerates a label/value wrap across two adjacent
  lines ("TENDER" / "NUMBER 18-2025/26"), single-line hits always winning.

QUOTED lines may now span the joined lines - ``source_line`` then carries
BOTH verbatim lines separated by a newline. Still no guessing: every
character of a quote is pack text.

O-01 round (F-02 residual, verified against the same real Musina PDF):
bare MBD/SBD regime-code HEADINGS ("MBD 6.1" / "MBD8" / "MBD 9" alone on
their line) are now a fourth accepted style - heading-only, never an
inline mention; see RE_ITEM_REGIME_BARE.

Pure functions, plain dict out. No frappe import, no AI, no OCR, no
network - standalone-importable like pack_builder (findings F-09).
"""

import re

QUOTED = "QUOTED"
NOT_FOUND = "NOT-FOUND"

# --------------------------------------------------------------------------
# scalar field patterns
# --------------------------------------------------------------------------

MONTHS = {
	"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
	"july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
	"december": 12,
}
_MONTH_ALT = "|".join(MONTHS)

RE_DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
RE_DATE_LONG = re.compile(r"\b(\d{1,2})\s+(" + _MONTH_ALT + r")\s+(\d{4})\b", re.I)
RE_DATE_SLASH = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
RE_TIME = re.compile(r"\b(\d{1,2})[:hH](\d{2})\b")

# the reference itself, then only continuation tokens that carry a digit
# ("DFFE-B005 26/27" continues; "8/2/RNM0614 Closing Date" stops at the ref)
RE_TENDER_NO_LABELLED = re.compile(
	r"\b(?:tender|bid)\s+(?:no|number|ref(?:erence)?)\s*\.?\s*:?\s*"
	r"([A-Z0-9][A-Z0-9/.\-]*(?:\s[A-Z0-9/.\-]*\d[A-Z0-9/.\-]*)*)",
	re.I,
)
RE_TENDER_NO_HEADING = re.compile(r"\bTENDER\s+(\d[\d\-]*/\d{2,4}(?:/\d{2})?)\b")

RE_THRESHOLD_PCT = re.compile(r"minimum\s+(?:number\s+)?of\s+(\d{1,3})\s*%", re.I)
RE_THRESHOLD_POINTS = re.compile(r"\(\s*(\d{1,3})\s+out\s+of\s+(\d{1,3})\s*\)", re.I)
RE_FUNC_MAX = re.compile(
	r"total\s+points\s+(?:on|for)\s+functionality\D{0,10}(\d{2,3})", re.I
)
# context words that must accompany a "minimum of N%" hit before it is read
# as a functionality threshold - bare "points" is deliberately excluded (a
# subcontracting/local-content minimum near preference-points language must
# stay NOT-FOUND, not become a fake threshold)
FUNCTIONALITY_CONTEXT = ("functionality", "quality", "phase 2")

RE_PREFERENCE = re.compile(r"\b(80\s*/\s*20|90\s*/\s*10)\b")
PREFERENCE_CONTEXT = ("preference", "point")

# submission-channel signals -> the Tender Bid submission_channel options
CHANNEL_SIGNALS = (
	("sealed_envelope", re.compile(r"sealed\s+envelope", re.I)),
	("tender_box", re.compile(r"\b(?:tender|bid)\s+box\b", re.I)),
	("portal", re.compile(r"\b(?:e-?tender(?:ing)?\s+portal|online\s+portal|electronic\s+submission\s+portal)\b", re.I)),
	("email_prohibited", re.compile(
		r"(?:facsimile|telex|telegram|e-?mail)[^.\n]{0,80}(?:will\s+not\s+be|shall\s+not\s+be|not\s+be)\s+(?:considered|accepted)", re.I)),
	("email_allowed", re.compile(
		r"(?:submit(?:ted)?|submission[s]?)\s[^.\n]{0,60}\b(?:by|via|per)\s+e-?mail", re.I)),
)

RE_WET_INK = re.compile(
	r"(?:completed\s+in\s+(?:black\s+)?ink|in\s+black\s+ink|wet\s+ink|"
	r"original\s+signature)", re.I)

# --------------------------------------------------------------------------
# returnable-list patterns (the three documented styles)
# --------------------------------------------------------------------------

# RNM style: "A1  Authority To Sign Documents", "C1.1  Form of Offer ..."
# Letters restricted to A-C (the returnable-schedule range the samples use);
# CIDB pack-structure section codes (T1.1, T2.1 ...) are deliberately NOT
# treated as returnables.
RE_ITEM_LETTERED = re.compile(r"^\(?([A-C]\d{1,2}(?:\.\d)?)\)?[\s.:–\-]+(\S.{2,140})$")
# DFFE style: "Annexure A - Pricing Schedule"
RE_ITEM_ANNEXURE = re.compile(r"^annexure\s+([A-Z])\b\s*[:–—\-]?\s*(\S.{2,140})$", re.I)
# Musina style: "Form A - Form of Bid"
RE_ITEM_FORM = re.compile(r"^form\s+([A-Z])\b\s*[:–—\-]?\s*(\S.{2,140})$", re.I)
# The real Musina buyer PDF (F-02 follow-up) writes the form letter and its
# title on SEPARATE lines ("Form A" ... "FORM OF BID"): a bare marker line
# joins forward to the next ALL-CAPS title line (see _lookahead_title).
RE_ITEM_FORM_BARE = re.compile(r"^form\s+([A-Z])\s*[:–—\-]?\s*$", re.I)
RE_ITEM_ANNEXURE_BARE = re.compile(r"^annexure\s+([A-Z])\s*[:–—\-]?\s*$", re.I)
# O-01 (F-02 residual): bare regime-code HEADINGS - "MBD 6.1", "MBD8",
# "MBD 9" standing alone on their line, the way the real Musina buyer PDF
# opens each MBD form page. The code must be ALONE on the line (trailing
# whitespace and a trailing ":"/dash tolerated, same as the other bare
# markers) - an inline mention in body text ("...the attached Certificate
# of Bid Determination (MBD 9)...") NEVER matches. Where an ALL-CAPS title
# follows, the same _lookahead_title join applies; a genuinely titleless
# heading is still captured with an empty title (the regime code itself
# identifies the standard form) - the title is never guessed. The code is
# stored space-normalised ("MBD8" -> "MBD 8") so repeated headings dedupe
# across the pack's own spelling variants; the verbatim spelling stays in
# ``source_line``.
RE_ITEM_REGIME_BARE = re.compile(
	r"^\(?(MBD|SBD)\s*\.?\s*(\d+(?:\.\d+)?)\)?\s*[:–—\-]?\s*$", re.I
)
# a parenthetical instruction line between marker and title, skipped during
# the join ("(To be completed by Bidder)") - never part of the title
RE_TITLE_SKIP = re.compile(r"^\(.{0,80}\)$")
TITLE_SKIP_MAX = 2   # instruction lines skipped between marker and title
TITLE_JOIN_MAX = 2   # extra ALL-CAPS lines joined onto a wrapped title
# numbered admin/checklist rows: "1. Master Bid Document ..." (list-mode only)
RE_ITEM_NUMBERED = re.compile(r"^(\d{1,2})[.)]\s+(\S.{2,140})$")
# lettered mandatory items (list-mode only) - all three marker spellings the
# corpus documents: "(a) ...", "a) ..." AND the dot style "a. ..." the real
# Musina pack's section 5.1 uses (F-02 follow-up fix 1)
RE_ITEM_PAREN_LETTER = re.compile(r"^\(?([a-z])[.)]\s+(\S.{2,140})$")

# a line that opens a returnables/mandatory list - gates the ambiguous
# numbered / paren-lettered item styles so stray numbering elsewhere in a
# 65-page pack is not harvested as a returnable
RE_LIST_HEADER = re.compile(
	r"(checklist\s+of\s+documentation|documents?\s+to\s+be\s+attached|"
	r"must\s+complete\s+and\s+return|returnable\s+(?:documents?|schedules?)|"
	r"mandatory\s+(?:bid\s+)?requirements|administrative\s+(?:compliance\s+)?requirements|"
	r"documentation\s+to\s+be\s+attached|proposal\s+is\s+considered\s+for\s+evaluation)",
	re.I,
)
RE_SECTION_NO = re.compile(r"\b(\d+(?:\.\d+)+)\b")
LIST_MODE_GRACE_LINES = 3  # consecutive non-item lines before list mode ends

MAX_TITLE_LEN = 140


def parse_pack_text(text):
	"""The full deterministic parse of one pack's extracted text.

	Returns a plain dict; every entry carries ``status`` (QUOTED/NOT-FOUND)
	and, when QUOTED, the verbatim ``source_line`` of the hit.
	"""
	lines = [ln.strip() for ln in (text or "").splitlines()]
	lines = [ln for ln in lines if ln]
	return {
		"tender_number": _find_tender_number(lines),
		"closing_date": _find_closing(lines),
		"functionality": _find_functionality(lines),
		"preference_system": _find_preference(lines),
		"submission_channel": _find_channel(lines),
		"wet_ink": _find_wet_ink(lines),
		"returnables": _find_returnables(lines),
	}


def _quoted(value, line, **extra):
	out = {"status": QUOTED, "value": value, "source_line": line}
	out.update(extra)
	return out


def _not_found(**extra):
	out = {"status": NOT_FOUND, "value": None, "source_line": None}
	out.update(extra)
	return out


def _wrap_pairs(lines):
	"""Adjacent lines joined with a newline - the wrap-tolerance surface.

	The real Musina pack wraps "TENDER" / "NUMBER 18-2025/26" across two
	lines (F-02 follow-up fix 3); joining each adjacent pair with "\\n" lets
	the existing single-line patterns hit across the wrap while the quoted
	``source_line`` remains EXACTLY the two verbatim pack lines (separated
	by the newline they were split at). Deterministic, no reflow guessing.
	"""
	return [lines[i] + "\n" + lines[i + 1] for i in range(len(lines) - 1)]


def _with_wrap_tolerance(scan, lines):
	"""Runs a scalar scanner over single lines first, then over adjacent-pair
	joins ONLY when the single-line pass found nothing - a single-line hit
	always wins, so no previously-QUOTED result can change."""
	result = scan(lines)
	if result.get("status") == QUOTED:
		return result
	wrapped = scan(_wrap_pairs(lines))
	if wrapped.get("status") == QUOTED:
		return wrapped
	return result


def _find_tender_number(lines):
	return _with_wrap_tolerance(_scan_tender_number, lines)


def _scan_tender_number(lines):
	for line in lines:
		match = RE_TENDER_NO_LABELLED.search(line)
		if match:
			value = match.group(1).strip().rstrip(".,;:")
			if any(ch.isdigit() for ch in value):
				return _quoted(value, line)
		match = RE_TENDER_NO_HEADING.search(line)
		if match:
			return _quoted(match.group(1), line)
	return _not_found()


def _find_closing(lines):
	return _with_wrap_tolerance(_scan_closing, lines)


def _scan_closing(lines):
	"""Closing date/time: a line naming closing, carrying a parseable date."""
	for line in lines:
		low = line.lower()
		if "closing" not in low and "closes" not in low:
			continue
		date_iso = _parse_date(line)
		if not date_iso:
			continue
		time_match = RE_TIME.search(line)
		time_value = None
		if time_match:
			hour, minute = int(time_match.group(1)), int(time_match.group(2))
			if hour < 24 and minute < 60:
				time_value = f"{hour:02d}:{minute:02d}"
		return _quoted(date_iso, line, time=time_value)
	return _not_found(time=None)


def _parse_date(line):
	"""First date on the line as ISO yyyy-mm-dd, or None. Three fixed formats
	(ISO, '11 May 2026', dd/mm/yyyy - SA packs write day-first)."""
	match = RE_DATE_ISO.search(line)
	if match:
		return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
	match = RE_DATE_LONG.search(line)
	if match:
		day, month_name, year = match.groups()
		month = MONTHS[month_name.lower()]
		return f"{int(year):04d}-{month:02d}-{int(day):02d}"
	match = RE_DATE_SLASH.search(line)
	if match:
		day, month, year = (int(g) for g in match.groups())
		if 1 <= month <= 12 and 1 <= day <= 31:
			return f"{year:04d}-{month:02d}-{day:02d}"
	return None


def _find_functionality(lines):
	return _with_wrap_tolerance(_scan_functionality, lines)


def _scan_functionality(lines):
	"""Functionality threshold % (context-gated) and, when quoted, the
	points pair / max-points line."""
	threshold = None
	for line in lines:
		match = RE_THRESHOLD_PCT.search(line)
		if not match:
			continue
		low = line.lower()
		if not any(ctx in low for ctx in FUNCTIONALITY_CONTEXT):
			continue
		threshold = _quoted(float(match.group(1)), line)
		points = RE_THRESHOLD_POINTS.search(line)
		if points:
			threshold["threshold_points"] = int(points.group(1))
			threshold["max_points"] = int(points.group(2))
		break
	if threshold is None:
		return _not_found(max_points=None)
	if "max_points" not in threshold:
		threshold["max_points"] = None
		for line in lines:
			match = RE_FUNC_MAX.search(line)
			if match:
				threshold["max_points"] = int(match.group(1))
				threshold["max_points_source_line"] = line
				break
	return threshold


def _find_preference(lines):
	return _with_wrap_tolerance(_scan_preference, lines)


def _scan_preference(lines):
	"""80/20 vs 90/10, only on a line that talks preference/points. Both
	systems quoted in one pack -> the FIRST hit wins the value but every
	distinct hit is listed so a straddling pack is visible."""
	hits = []
	seen = set()
	for line in lines:
		match = RE_PREFERENCE.search(line)
		if not match:
			continue
		low = line.lower()
		if not any(ctx in low for ctx in PREFERENCE_CONTEXT):
			continue
		system = re.sub(r"\s", "", match.group(1))
		if system not in seen:
			seen.add(system)
			hits.append({"system": system, "source_line": line})
	if not hits:
		return _not_found(all_hits=[])
	return _quoted(hits[0]["system"], hits[0]["source_line"], all_hits=hits)


def _find_channel(lines):
	return _with_wrap_tolerance(_scan_channel, lines)


def _scan_channel(lines):
	"""Submission-channel signals -> a proposed Tender Bid channel option.

	Physical signals outrank portal outrank email (a pack that demands a
	sealed envelope in the tender box AND forbids e-mail is the common
	municipal case); an email_allowed signal never proposes 'Email allowed'
	when an email_prohibited signal is also present.
	"""
	signals = []
	seen = set()
	for line in lines:
		for name, pattern in CHANNEL_SIGNALS:
			if name in seen:
				continue
			if pattern.search(line):
				seen.add(name)
				signals.append({"signal": name, "source_line": line})
	if not signals:
		return _not_found(signals=[])

	by_name = {sig["signal"]: sig for sig in signals}
	for name in ("sealed_envelope", "tender_box"):
		if name in by_name:
			return _quoted(
				"Physical tender box", by_name[name]["source_line"], signals=signals
			)
	if "portal" in by_name:
		return _quoted("Portal upload", by_name["portal"]["source_line"], signals=signals)
	if "email_allowed" in by_name and "email_prohibited" not in by_name:
		return _quoted(
			"Email allowed", by_name["email_allowed"]["source_line"], signals=signals
		)
	# only a prohibition signal: the pack says what the channel is NOT -
	# that is not a quoted channel value
	return _not_found(signals=signals)


def _find_wet_ink(lines):
	return _with_wrap_tolerance(_scan_wet_ink, lines)


def _scan_wet_ink(lines):
	for line in lines:
		match = RE_WET_INK.search(line)
		if match:
			return _quoted(True, line, matched_phrase=match.group(0))
	return _not_found(matched_phrase=None)


def _caps_line(line):
	"""A heading-style line: has letters and no lowercase ("FORM OF BID")."""
	return line == line.upper() and any(ch.isalpha() for ch in line)


def _lookahead_title(lines, start):
	"""The title for a bare "Form X" / "Annexure C" marker line, or None.

	The real Musina pack (F-02 follow-up fix 2) prints the marker, then an
	optional parenthetical instruction line ("(To be completed by Bidder)"),
	then the ALL-CAPS title - sometimes wrapped over two lines ("...LOCAL
	CONTENT AND" / "SABS MARK"). Deterministic join: skip up to
	TITLE_SKIP_MAX fully-parenthesised instruction lines, take the first
	ALL-CAPS heading line as the title and append up to TITLE_JOIN_MAX
	further ALL-CAPS lines while the wrap continues. Anything else (prose,
	another marker, end of text) means NO title - the marker is not
	harvested, never guessed at. Returns (title, [source lines used],
	[indices of those lines]) - the indices let the caller mark title lines
	as consumed so a joined title line (e.g. the "MBD 4" under "ANNEXURE C")
	is never re-harvested as its own bare regime heading.
	"""
	index = start
	skipped = 0
	while index < len(lines) and skipped < TITLE_SKIP_MAX and RE_TITLE_SKIP.match(lines[index]):
		index += 1
		skipped += 1
	if index >= len(lines):
		return None, [], []
	candidate = lines[index]
	if not _caps_line(candidate) or len(candidate) < 3:
		return None, [], []
	if (
		RE_ITEM_FORM_BARE.match(candidate)
		or RE_ITEM_ANNEXURE_BARE.match(candidate)
		or RE_LIST_HEADER.search(candidate)
	):
		return None, [], []
	title_lines = [candidate]
	indices = [index]
	index += 1
	while (
		index < len(lines)
		and len(title_lines) <= TITLE_JOIN_MAX
		and _caps_line(lines[index])
		and not RE_ITEM_FORM_BARE.match(lines[index])
		and not RE_ITEM_ANNEXURE_BARE.match(lines[index])
	):
		title_lines.append(lines[index])
		indices.append(index)
		index += 1
	return " ".join(title_lines), title_lines, indices


def _find_returnables(lines):
	"""The pack's returnable-document list(s), three documented styles.

	Distinctive styles (Annexure X / Form X / a bare MBD/SBD regime-code
	heading, O-01) are collected anywhere - on one line ("Form A - Form of
	Bid") or as a bare marker whose ALL-CAPS title follows on its own
	line(s) (the real Musina pack's layout; source_line then spans the
	joined lines). A joined title line is marked consumed so it is never
	re-harvested as its own bare regime heading (the real pack's "ANNEXURE
	C" / "MBD 4" pairing). The lettered A1-style needs at least two items
	sharing a letter prefix (a lone 'A4 ...' line is not a schedule);
	ambiguous numbered / lettered items ("1.", "(a)", "a)", "a.") are
	collected ONLY while inside a list opened by a recognised header line
	(LIST_MODE_GRACE_LINES of slack for blank-ish interleaves). Items dedupe
	by normalised ref code, first occurrence winning - except that a titled
	occurrence completes an earlier TITLELESS capture of the same code (a
	regime heading repeated as a running page header can precede its true
	title page; both quotes are pack text, nothing is guessed).
	"""
	items = []
	lettered = []
	list_mode = False
	list_section = None
	grace = 0
	consumed_title_indices = set()

	for position, line in enumerate(lines):
		header = RE_LIST_HEADER.search(line)
		if header:
			list_mode = True
			grace = 0
			section = RE_SECTION_NO.search(line)
			list_section = section.group(1) if section else None
			continue

		matched = False
		match = RE_ITEM_ANNEXURE.match(line)
		if match:
			items.append(_item(f"Annexure {match.group(1).upper()}", match.group(2), "annexure", line))
			matched = True
		if not matched:
			match = RE_ITEM_FORM.match(line)
			if match:
				items.append(_item(f"Form {match.group(1).upper()}", match.group(2), "form", line))
				matched = True
		if not matched:
			# bare "Form X" / "Annexure C" marker: title on the following
			# line(s) - the real buyer-PDF layout (F-02 follow-up fix 2)
			for pattern, prefix, style in (
				(RE_ITEM_FORM_BARE, "Form", "form"),
				(RE_ITEM_ANNEXURE_BARE, "Annexure", "annexure"),
			):
				match = pattern.match(line)
				if not match:
					continue
				title, title_lines, used = _lookahead_title(lines, position + 1)
				if title:
					items.append(_item(
						f"{prefix} {match.group(1).upper()}", title, style,
						"\n".join([line] + title_lines),
					))
					consumed_title_indices.update(used)
					matched = True
				break
		if not matched and position not in consumed_title_indices:
			# bare regime-code heading ("MBD 6.1" / "MBD8" / "MBD 9" alone
			# on the line - O-01): join a following ALL-CAPS title where one
			# exists, otherwise capture the code alone (title empty, never
			# guessed). Lines already consumed as a joined title (the
			# "MBD 4" under "ANNEXURE C") are skipped - the Annexure row
			# already quotes them.
			match = RE_ITEM_REGIME_BARE.match(line)
			if match:
				ref_code = f"{match.group(1).upper()} {match.group(2)}"
				title, title_lines, used = _lookahead_title(lines, position + 1)
				if title:
					items.append(_item(
						ref_code, title, "regime",
						"\n".join([line] + title_lines),
					))
					consumed_title_indices.update(used)
				else:
					items.append(_item(ref_code, "", "regime", line))
				matched = True
		if not matched:
			match = RE_ITEM_LETTERED.match(line)
			if match:
				lettered.append(_item(match.group(1).upper(), match.group(2), "lettered", line))
				matched = True
		if not matched and list_mode:
			match = RE_ITEM_NUMBERED.match(line)
			if match:
				code = f"{list_section}({match.group(1)})" if list_section else match.group(1)
				items.append(_item(code, match.group(2), "numbered", line))
				matched = True
			else:
				match = RE_ITEM_PAREN_LETTER.match(line)
				if match:
					code = (
						f"{list_section}({match.group(1)})" if list_section
						else f"({match.group(1)})"
					)
					items.append(_item(code, match.group(2), "paren-letter", line))
					matched = True

		if list_mode:
			if matched:
				grace = 0
			else:
				grace += 1
				if grace > LIST_MODE_GRACE_LINES:
					list_mode = False
					list_section = None

	# lettered schedule lines only count in groups of >= 2 per letter prefix.
	# CALIBRATION NOTE (F-02 follow-up): this >=2 rule deliberately DROPS a
	# single-item lettered schedule (a pack whose schedule genuinely lists
	# one lone "A1 ..." row parses to zero lettered items). Documented
	# tradeoff, kept as-is: relaxing it would harvest every stray "A4 paper"
	# style line in a 65-page pack as a returnable; the desk hand-captures
	# the (rare) one-row schedule instead, exactly as before.
	groups = {}
	for item in lettered:
		groups.setdefault(item["ref_code"][0], []).append(item)
	for letter in sorted(groups):
		if len(groups[letter]) >= 2:
			items.extend(groups[letter])

	deduped = []
	kept = {}
	for item in items:
		key = " ".join(item["ref_code"].lower().split())
		if key in kept:
			# title completion, never value change: a titled occurrence
			# fills in an earlier titleless capture of the same code (only
			# bare regime headings can be titleless; every other family
			# always carries a title, so their first-wins dedupe is
			# unchanged). The kept quote becomes the titled occurrence's.
			if not kept[key]["title"] and item["title"]:
				kept[key]["title"] = item["title"]
				kept[key]["source_line"] = item["source_line"]
			continue
		kept[key] = item
		deduped.append(item)

	if not deduped:
		return {"status": NOT_FOUND, "items": [], "count": 0}
	return {"status": QUOTED, "items": deduped, "count": len(deduped)}


def _item(ref_code, title, style, line):
	title = " ".join(title.split()).strip(" .;:,–—-\"'")
	if len(title) > MAX_TITLE_LEN:
		title = title[:MAX_TITLE_LEN].rstrip()
	return {
		"ref_code": ref_code,
		"title": title,
		"style": style,
		"source_line": line,
	}
