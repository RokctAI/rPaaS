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

"""Preference-framework conflict lint (findings F-12).

One live pack can simultaneously carry MORE THAN ONE preference framework:
the Musina 18-2025/26 helpdesk pack contains the operative PPR 2022
specific-goals MBD 6.1 table, a pre-2011 HDI equity-ownership section
(PPPFA 2000 regulations, Form C "...% = ... Points out of 20"), AND a
Local Government Ordinance 1939 local-content/SABS certificate (Form D) -
only one framework scores, but every form must still be completed
(non-completion forfeits the preference).

This module is the smallest deterministic surface for that reality: a pure
text lint over whatever pack-derived texts the caller has (form names, kill
notes, captured returnable titles, spec notes). It detects which framework
families the texts signal and produces a warning string when more than one
is present. No data-model change, no AI, no network, no frappe import -
standalone importable like pack_builder.

The signal patterns are ordinary normalized-substring patterns (same style
as rules.text_matches_any). They also ship as desk-editable fixture data on
rule WARN-PREF-CONFLICT (params.framework_patterns); pass those params in
to override the defaults baked here for standalone use.
"""

# Framework label -> normalized-substring signal patterns. Patterns are
# deliberately SPECIFIC to each framework's own instruments so the ordinary
# single-framework pack never trips the lint: e.g. plain "specific goals" /
# SBD-MBD 6.1 wording signals PPR 2022, while only the legacy equity-claim
# wording ("equity ownership", "points out of 20", the NEP=NOP*EP/100
# formula) signals the pre-2011 HDI framework, and only the 1939-Ordinance
# wording signals the ordinance local-content certificate (the lawful
# SATS 1286 / SBD-MBD 6.2 local-content instrument does NOT).
DEFAULT_FRAMEWORK_PATTERNS = {
	"PPR 2022 specific goals (SBD/MBD 6.1)": [
		"ppr 2022",
		"preferential procurement regulations, 2022",
		"preferential procurement regulations 2022",
		"specific goals",
		"specific-goals",
	],
	"Pre-2011 HDI equity-ownership (PPPFA 2000 regulations)": [
		"hdi equity",
		"equity ownership",
		"nep = nop",
		"points out of 20",
		"preferential procurement regulations, 2001",
		"preferential procurement regulations 2001",
	],
	"Local Government Ordinance 1939 local content / SABS": [
		"ordinance, 1939",
		"ordinance 1939",
		"local government ordinance",
		"sabs mark",
	],
}


def _normalize(value):
	"""Lowercases and collapses whitespace (mirrors rules.normalize_text).

	Duplicated two-liner rather than imported: rules.py imports frappe, and
	this module must stay standalone-importable (cf. findings F-09).
	"""
	return " ".join(str(value or "").lower().split())


def detect_preference_frameworks(texts, framework_patterns=None):
	"""Returns the sorted list of framework labels the texts signal.

	``texts`` is any iterable of strings (or None entries) drawn from the
	pack: form names, kill notes, instructions, captured returnable titles.
	A framework counts as present when ANY of its patterns appears as a
	normalized substring in ANY of the texts. Deterministic set arithmetic.
	"""
	patterns = framework_patterns or DEFAULT_FRAMEWORK_PATTERNS
	haystack = " \n ".join(_normalize(text) for text in (texts or []) if text)
	if not haystack.strip():
		return []
	found = []
	for label, needles in patterns.items():
		for needle in needles or []:
			normalized = _normalize(needle)
			if normalized and normalized in haystack:
				found.append(label)
				break
	return sorted(found)


def preference_framework_conflict(texts, operative_system=None, framework_patterns=None):
	"""Returns the lint warning string, or None when at most one framework is present.

	``operative_system`` (e.g. "80/20" / "90/10" or a framework label) is
	echoed into the warning when known - the operative scoring system stays
	whatever the pack's evaluation clause says; the warning only surfaces
	that the OTHER frameworks' forms must still be completed and signed.
	"""
	frameworks = detect_preference_frameworks(texts, framework_patterns)
	if len(frameworks) < 2:
		return None
	operative = f" Operative scoring system: {operative_system}." if operative_system else ""
	return (
		"Pack contains conflicting preference frameworks: "
		+ "; ".join(frameworks)
		+ ". Only one framework scores, but complete and sign EVERY framework's "
		"form anyway - the legacy forms state that non-completion forfeits the "
		"preference." + operative + " [WARN-PREF-CONFLICT]"
	)
