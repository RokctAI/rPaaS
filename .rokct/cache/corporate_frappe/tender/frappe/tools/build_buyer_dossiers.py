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

"""Builds the per-buyer behavioural dossiers from the committed awards
dataset.

Deterministic, stdlib-only sibling of ``build_market_context.py``: reads
``tender/awards-dataset/awards_only.csv`` (32,589 published award rows,
snapshot 2026-08-20 - see ``tender/awards-dataset/README.md`` and
``tender/Award-Outcomes-Research.md``) and writes the derived JSON fixture
``tender/frappe/src/control/compliance/data/buyer_dossiers.json``.

Identical input -> byte-identical output (sorted keys, fixed rounding), so
``verify_buyer_dossiers.py`` can re-run this builder and diff against the
committed fixture. Re-run whenever the dataset refreshes:

    python3 tender/frappe/tools/build_buyer_dossiers.py

One dossier per buyer that appears in the awards feed (581 buyers - the
dataset is small enough that no top-N cut is needed; thin buyers simply
publish nulls for every gated stat). Discipline, following the
market-context rules (#53/#55):

- **medians / IQR only, never means** over flag-clean amounts
  (``amount_flag`` empty), published only at N >= 30 clean amounts;
- **supplier concentration** (top-supplier share, distinct-supplier
  count) and the **newcomer-openness proxy** (share of awards to
  suppliers appearing exactly once at that buyer) are computed over
  IDENTIFIED awards only: rows whose supplier id is the ``"0"``
  placeholder (12,250 rows, 37.6% of the corpus) or whose supplier name
  is a placeholder artifact ("None", single characters - 12 rows) are
  excluded from concentration math, while still counting toward
  ``award_count``. Both counts are published so the exclusion is visible;
- concentration stats are published only at N >= 30 identified awards
  (same style judgment as the N >= 30 price-cell floor - top-supplier
  share over 5 awards is noise, not signal);
- supplier-name normalisation extends the report's conservative recipe
  (trim, casefold, whitespace collapse, trailing punctuation, NO fuzzy
  merging) with exactly one dataset-specific quirk fix: 8,923 rows carry
  a leading-space name and 7,340 of those are FULLY parenthesised forms
  like ``" (AGRI EXPERTS JV)"`` - the source name field was blank and
  only the parenthetical alternate survived - which unwrap to the inner
  name (4,583 of them then merge with a bare form of the same supplier).
  Partial parentheticals ("SULZER PUMPS (SOUTH AFRICA)") are NEVER
  unwrapped. Distinct-supplier counts remain upper bounds;
- true per-buyer publication rates need the releases-without-awards
  denominator, which the awards-only CSV cannot supply - they are NOT
  computed here (market_context.json carries the curated transcription
  from the research report; the dossier lookup states the bias as a
  caveat instead of guessing).
"""

import csv
import hashlib
import io
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DEFAULT_CSV = os.path.join(REPO, "tender", "awards-dataset", "awards_only.csv")
DEFAULT_OUT = os.path.join(
	HERE, "..", "src", "control", "compliance", "data", "buyer_dossiers.json"
)

# The lookup module owns buyer normalisation (shared with market_context);
# import it by path so fixture keys and runtime lookups match by
# construction.
import importlib.util

_spec = importlib.util.spec_from_file_location(
	"tender_dossier_market_context",
	os.path.join(HERE, "..", "src", "control", "compliance", "market_context.py"),
)
market_context = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(market_context)
normalize_buyer = market_context.normalize_buyer

SNAPSHOT_DATE = "2026-08-20"
MIN_AMOUNT_N = 30         # N >= 30 flag-clean amounts per published median/IQR
MIN_CONCENTRATION_N = 30  # N >= 30 identified awards per concentration stat
PLACEHOLDER_SUPPLIER_ID = "0"
# Placeholder supplier-name artifacts (research report section 2: "None",
# single characters - 12 rows). Compared against the NORMALISED name.
PLACEHOLDER_SUPPLIER_NAMES = ("", "none", "null")

# A fully parenthesised supplier name - the whole (stripped) string is one
# parenthetical. These are the blank-name-with-alternate rows; the inner
# name is the supplier.
RE_FULLY_PARENTHESIZED = re.compile(r"^\((.+)\)$")


def normalize_supplier_name(raw):
	"""Conservative supplier key with the dataset's two documented quirks
	fixed: leading/trailing spaces trimmed and FULLY parenthesised forms
	(" (NAME)") unwrapped to the inner name. Then the report's recipe:
	casefold, whitespace collapse, trailing punctuation. NO fuzzy merging -
	distinct counts stay upper bounds."""
	text = str(raw or "").strip()
	match = RE_FULLY_PARENTHESIZED.match(text)
	if match:
		text = match.group(1).strip()
	return " ".join(text.lower().split()).rstrip(".,;:")


def display_supplier_name(raw):
	"""Human-readable form of one supplier cell: trimmed, fully
	parenthesised forms unwrapped, original casing kept."""
	text = str(raw or "").strip()
	match = RE_FULLY_PARENTHESIZED.match(text)
	if match:
		text = match.group(1).strip()
	return " ".join(text.split())


def supplier_identity(row):
	"""Normalised supplier key for concentration math, or None when the
	row carries only a placeholder identity (supplier id "0", or a
	placeholder name artifact). Placeholder rows still count toward
	``award_count`` - they are only excluded from concentration."""
	if str(row.get("supplier_ids") or "").strip() == PLACEHOLDER_SUPPLIER_ID:
		return None
	key = normalize_supplier_name(row.get("supplier_names"))
	if key in PLACEHOLDER_SUPPLIER_NAMES or len(key) <= 1:
		return None
	return key


def price_cell(amounts):
	"""Median + IQR over flag-clean amounts, or None below N >= 30 (same
	math as build_market_context.price_cell: inclusive quartiles, whole
	rand)."""
	if len(amounts) < MIN_AMOUNT_N:
		return None
	ordered = sorted(amounts)
	quartiles = statistics.quantiles(ordered, n=4, method="inclusive")
	return {
		"n": len(ordered),
		"median_rand": int(round(statistics.median(ordered))),
		"iqr_rand": [int(round(quartiles[0])), int(round(quartiles[2]))],
	}


def pct(part, whole):
	return round(100.0 * part / whole, 2) if whole else None


def buyer_dossier(buyer_name, buyer_rows):
	"""One buyer's dossier entry from its award rows (deterministic)."""
	award_count = len(buyer_rows)
	clean = [
		float(r["award_value"]) for r in buyer_rows if r["amount_flag"] == ""
	]
	cell = price_cell(clean)
	zero_awards = sum(1 for r in buyer_rows if r["amount_flag"] == "zero")

	# Identified rows only feed concentration; placeholders are counted so
	# the exclusion is visible in the published entry.
	identified = []
	for row in buyer_rows:
		key = supplier_identity(row)
		if key is not None:
			identified.append((key, display_supplier_name(row["supplier_names"])))
	identified_count = len(identified)
	placeholder_count = award_count - identified_count

	distinct_suppliers = None
	top_supplier = None
	top_supplier_share_pct = None
	single_win_share_pct = None
	if identified_count >= MIN_CONCENTRATION_N:
		wins = Counter(key for key, _ in identified)
		distinct_suppliers = len(wins)
		# Deterministic top pick: most wins, ties broken by key.
		top_key = min(wins, key=lambda k: (-wins[k], k))
		top_supplier_share_pct = pct(wins[top_key], identified_count)
		# Deterministic display form: most frequent spelling, ties broken
		# lexicographically.
		spellings = Counter(
			disp for key, disp in identified if key == top_key
		)
		top_supplier = min(spellings, key=lambda d: (-spellings[d], d))
		single_win_awards = sum(1 for c in wins.values() if c == 1)
		single_win_share_pct = pct(single_win_awards, identified_count)

	return {
		"buyer": buyer_name,
		"award_count": award_count,
		"benchmark_count": len(clean),
		"median_rand": cell["median_rand"] if cell else None,
		"iqr_rand": cell["iqr_rand"] if cell else None,
		"zero_amount_share_pct": pct(zero_awards, award_count),
		"identified_award_count": identified_count,
		"placeholder_award_count": placeholder_count,
		"placeholder_share_pct": pct(placeholder_count, award_count),
		"distinct_supplier_count": distinct_suppliers,
		"top_supplier": top_supplier,
		"top_supplier_share_pct": top_supplier_share_pct,
		"single_win_supplier_share_pct": single_win_share_pct,
	}


def build_tables(csv_path=DEFAULT_CSV):
	with open(csv_path, newline="", encoding="utf-8") as fh:
		rows = list(csv.DictReader(fh))
	with open(csv_path, "rb") as fh:
		sha256 = hashlib.sha256(fh.read()).hexdigest()

	by_buyer = defaultdict(list)
	for row in rows:
		by_buyer[row["buyer"]].append(row)

	buyers = {}
	for buyer_name in sorted(by_buyer):
		buyers[normalize_buyer(buyer_name)] = buyer_dossier(
			buyer_name, by_buyer[buyer_name]
		)

	identified_total = sum(v["identified_award_count"] for v in buyers.values())
	tables = {
		"meta": {
			"source": "tender/awards-dataset/awards_only.csv",
			"source_sha256": sha256,
			"snapshot_date": SNAPSHOT_DATE,
			"generator": "tender/frappe/tools/build_buyer_dossiers.py",
			"awards": len(rows),
			"buyers": len(buyers),
			"identified_awards": identified_total,
			"placeholder_awards": len(rows) - identified_total,
			"min_amount_n": MIN_AMOUNT_N,
			"min_concentration_n": MIN_CONCENTRATION_N,
			"definitions": {
				"award_count": "every published award row for the buyer, "
				"placeholder supplier identities included",
				"median_rand/iqr_rand": "median + IQR of flag-clean award "
				"amounts (zero / lt_R100 / gt_R10bn excluded), published "
				"only at N >= {0} clean amounts - medians only, never "
				"means".format(MIN_AMOUNT_N),
				"identified_award_count": "awards whose supplier identity is "
				"real: supplier id not the '0' placeholder and the name not "
				"a placeholder artifact - the concentration denominator",
				"top_supplier_share_pct": "share of the buyer's IDENTIFIED "
				"awards won by its most-awarded supplier (conservative name "
				"normalisation, no fuzzy merging), published only at "
				"N >= {0} identified awards".format(MIN_CONCENTRATION_N),
				"distinct_supplier_count": "distinct normalised supplier "
				"names over identified awards - an UPPER bound (name "
				"variants under-merge), same gate",
				"single_win_supplier_share_pct": "newcomer-openness PROXY: "
				"share of identified awards won by suppliers appearing "
				"exactly once at this buyer in the published record, same "
				"gate - a proxy within the published-awards dataset only",
			},
		},
		"buyers": buyers,
	}
	return tables


def render(tables):
	"""Canonical JSON bytes: sorted keys, 1-space indent, trailing newline
	(byte-compatible with build_market_context.render)."""
	buf = io.StringIO()
	json.dump(tables, buf, indent=1, sort_keys=True, ensure_ascii=False)
	buf.write("\n")
	return buf.getvalue()


def main(argv):
	csv_path = argv[1] if len(argv) > 1 else DEFAULT_CSV
	out_path = os.path.abspath(argv[2] if len(argv) > 2 else DEFAULT_OUT)
	tables = build_tables(csv_path)
	os.makedirs(os.path.dirname(out_path), exist_ok=True)
	with open(out_path, "w", encoding="utf-8") as fh:
		fh.write(render(tables))
	buyers = tables["buyers"]
	print(
		"wrote {0}: {1} buyer dossiers ({2} with a price cell, {3} with "
		"concentration stats)".format(
			out_path,
			len(buyers),
			sum(1 for v in buyers.values() if v["median_rand"] is not None),
			sum(
				1 for v in buyers.values()
				if v["top_supplier_share_pct"] is not None
			),
		)
	)
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv))
