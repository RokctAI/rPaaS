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

"""Builds the market-context reference tables from the committed awards
dataset.

Deterministic, stdlib-only: reads ``tender/awards-dataset/awards_only.csv``
(32,589 published award rows, snapshot 2026-08-20 - see
``tender/awards-dataset/README.md`` and ``tender/Award-Outcomes-Research.md``)
and writes the small derived JSON fixture the suitability engine ships:
``tender/frappe/src/control/compliance/data/market_context.json``.

Identical input -> byte-identical output (sorted keys, fixed rounding), so
``verify_market_context.py`` can re-run this builder and diff against the
committed fixture. Re-run whenever the dataset refreshes:

    python3 tender/frappe/tools/build_market_context.py

Discipline (from the research report, #53):

- **medians / IQR only, never means** - the corpus mean is 23x the median;
- **flag-cleaned amounts only** - rows whose ``amount_flag`` marks
  zero / lt_R100 / gt_R10bn amounts are excluded from every price cell
  (they still count in award counts and shares);
- **N >= 30 per published price cell** - buyer medians, category x
  province cells, category and province fallbacks all respect it;
- supplier normalisation is conservative (trim, casefold, whitespace
  collapse, trailing punctuation) with NO fuzzy merging, so entrant
  shares are upper bounds (the report's stated caveat);
- per-buyer publication rates are NOT derivable from the awards-only CSV
  (they need the releases-without-awards denominator), so the documented
  top-30 coverage figures from Award-Outcomes-Research.md section 2 are
  carried as a curated transcription - including the three documented
  zero-publisher municipalities, committed as award_count-0 rows so their
  channel-gap behaviour is still resolvable.
"""

import csv
import hashlib
import io
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DEFAULT_CSV = os.path.join(REPO, "tender", "awards-dataset", "awards_only.csv")
DEFAULT_OUT = os.path.join(
	HERE, "..", "src", "control", "compliance", "data", "market_context.json"
)

# The engine module owns buyer normalisation; import it by path so the
# fixture keys and the runtime lookups match by construction.
import importlib.util

_spec = importlib.util.spec_from_file_location(
	"tender_market_context",
	os.path.join(HERE, "..", "src", "control", "compliance", "market_context.py"),
)
market_context = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(market_context)
normalize_buyer = market_context.normalize_buyer

TOP_BUYERS = 200          # top-N buyers by award count get a table row
MIN_CELL_N = 30           # the N >= 30 price-cell discipline (#53)
ENTRANT_MAX_WINS = 2      # "entrant" = supplier with <= 2 lifetime wins
INCUMBENT_MIN_WINS = 3    # at-buyer incumbency = >= 3 wins at that buyer

# Publication behaviour thresholds over the documented coverage figures.
PUBLICATION_HIGH_PCT = 40.0
PUBLICATION_LOW_PCT = 15.0

# Curated transcription of the per-buyer award-publication coverage
# documented in tender/Award-Outcomes-Research.md section 2 (top-30 buyers
# by release count; the denominator - releases without awards - is not in
# the awards-only CSV). Keys are the exact buyer strings in the CSV.
PUBLICATION_RATE_PCT = {
	"South African Revenue Service": 75.74,
	"Justice & Constitutional Development": 71.96,
	"THE MVULA TRUST": 63.05,
	"Council for Scientific and Industrial Research (CSIR)": 51.97,
	"South African National Roads Agency Soc Limited (SANRAL)": 40.20,
	"ESKOM": 9.87,
	"Independent Development Trust": 8.74,
	"Airports Company of South Africa": 6.56,
	"Johannesburg Water": 4.08,
	"Rand Water": 4.06,
	"Agricultural Research Council": 2.22,
	"Air Traffic and Navigation Services Company Limited": 0.95,
}

# Documented zero publishers (0 award rows in the feed, so they can never
# earn a computed table row): committed as award_count-0 entries so a card
# from these buyers still resolves their channel-gap behaviour.
ZERO_PUBLISHERS = (
	("City of Tshwane", 1254),
	("Mnquma Local Municipality", 978),
	("City Council of Johannesburg", 909),
)


def normalize_supplier(name):
	"""Conservative supplier key: trim, casefold, whitespace collapse,
	trailing punctuation - the report's normalisation, NO fuzzy merging."""
	return " ".join(str(name or "").lower().split()).rstrip(".,;:")


def publication_behavior(rate_pct):
	if rate_pct is None:
		return "unknown"
	if rate_pct == 0:
		return "zero"
	if rate_pct >= PUBLICATION_HIGH_PCT:
		return "high"
	if rate_pct < PUBLICATION_LOW_PCT:
		return "low"
	return "medium"


def price_cell(amounts):
	"""Median + IQR cell over flag-clean amounts, or None below N >= 30.

	Rounded to whole rand; quartiles via the inclusive method (matches the
	report's published Q1 R1.74m / Q3 R150.00m on the full benchmark set).
	"""
	if len(amounts) < MIN_CELL_N:
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


def build_tables(csv_path=DEFAULT_CSV):
	with open(csv_path, newline="", encoding="utf-8") as fh:
		rows = list(csv.DictReader(fh))
	with open(csv_path, "rb") as fh:
		sha256 = hashlib.sha256(fh.read()).hexdigest()

	# Corpus-wide lifetime win counts (all rows - win COUNTS measure
	# frequency, zero-value awards included, per the report).
	lifetime_wins = Counter(normalize_supplier(r["supplier_names"]) for r in rows)
	entrants = {s for s, c in lifetime_wins.items() if c <= ENTRANT_MAX_WINS}

	benchmark_all = [
		float(r["award_value"]) for r in rows if r["amount_flag"] == ""
	]

	# ---- per-buyer stats (top-N by award count + curated zero publishers) --
	by_buyer = defaultdict(list)
	for r in rows:
		by_buyer[r["buyer"]].append(r)
	ranked = sorted(
		by_buyer.items(), key=lambda item: (-len(item[1]), item[0])
	)[:TOP_BUYERS]

	buyers = {}
	for buyer_name, buyer_rows in ranked:
		clean = [
			float(r["award_value"]) for r in buyer_rows if r["amount_flag"] == ""
		]
		cell = price_cell(clean)
		entrant_awards = sum(
			1 for r in buyer_rows
			if normalize_supplier(r["supplier_names"]) in entrants
		)
		at_buyer = Counter(
			normalize_supplier(r["supplier_names"]) for r in buyer_rows
		)
		incumbent_awards = sum(
			c for c in at_buyer.values() if c >= INCUMBENT_MIN_WINS
		)
		zero_awards = sum(1 for r in buyer_rows if r["amount_flag"] == "zero")
		rate = PUBLICATION_RATE_PCT.get(buyer_name)
		buyers[normalize_buyer(buyer_name)] = {
			"buyer": buyer_name,
			"award_count": len(buyer_rows),
			"benchmark_count": len(clean),
			"median_rand": cell["median_rand"] if cell else None,
			"iqr_rand": cell["iqr_rand"] if cell else None,
			"entrant_share_pct": pct(entrant_awards, len(buyer_rows)),
			"incumbency_share_pct": pct(incumbent_awards, len(buyer_rows)),
			"zero_amount_share_pct": pct(zero_awards, len(buyer_rows)),
			"publication_rate_pct": rate,
			"publication_behavior": publication_behavior(rate),
		}
	for buyer_name, release_count in ZERO_PUBLISHERS:
		buyers[normalize_buyer(buyer_name)] = {
			"buyer": buyer_name,
			"award_count": 0,
			"benchmark_count": 0,
			"median_rand": None,
			"iqr_rand": None,
			"entrant_share_pct": None,
			"incumbency_share_pct": None,
			"zero_amount_share_pct": None,
			"publication_rate_pct": 0.0,
			"publication_behavior": "zero",
			"release_count": release_count,
			"note": (
				"documented zero publisher: 0 of {0} releases carry an award "
				"block in the OCDS feed - municipal award notices go to the "
				"buyer's own website (channel gap, not zero awards)".format(
					release_count
				)
			),
		}

	# ---- corpus-wide default buyer entry (the fallback) ----
	entrant_awards_all = sum(
		1 for r in rows if normalize_supplier(r["supplier_names"]) in entrants
	)
	default_buyer = {
		"buyer": None,
		"award_count": len(rows),
		"benchmark_count": len(benchmark_all),
		"median_rand": None,  # never price from the corpus-wide pool
		"iqr_rand": None,
		"entrant_share_pct": pct(entrant_awards_all, len(rows)),
		"incumbency_share_pct": None,
		"zero_amount_share_pct": pct(
			sum(1 for r in rows if r["amount_flag"] == "zero"), len(rows)
		),
		"publication_rate_pct": None,
		"publication_behavior": "unknown",
	}

	# ---- category x province cells + category / province fallbacks ----
	cat_prov = defaultdict(list)
	cat_only = defaultdict(list)
	prov_only = defaultdict(list)
	for r in rows:
		if r["amount_flag"] != "":
			continue
		amount = float(r["award_value"])
		category = r["category"].strip().lower()
		province = " ".join(r["province"].lower().split())
		if category and province:
			cat_prov[category + "|" + province].append(amount)
		if category:
			cat_only[category].append(amount)
		if province:
			prov_only[province].append(amount)

	def cells(pool):
		out = {}
		for key, amounts in pool.items():
			cell = price_cell(amounts)
			if cell:
				out[key] = cell
		return out

	overall = price_cell(benchmark_all)
	tables = {
		"meta": {
			"source": "tender/awards-dataset/awards_only.csv",
			"source_sha256": sha256,
			"snapshot_date": "2026-08-20",
			"generator": "tender/frappe/tools/build_market_context.py",
			"awards": len(rows),
			"benchmark_rows": len(benchmark_all),
			"min_cell_n": MIN_CELL_N,
			"top_buyers": TOP_BUYERS,
			"entrant_definition": "supplier with <= 2 lifetime wins corpus-wide "
			"(conservative name normalisation, no fuzzy merging - shares are "
			"upper bounds)",
			"incumbency_definition": "share of a buyer's awards to suppliers "
			"with >= 3 wins at that buyer",
			"publication_rates_source": "Award-Outcomes-Research.md section 2 "
			"(curated transcription - the releases-without-awards denominator "
			"is not in the awards-only CSV)",
			"overall": overall,
		},
		"buyers": buyers,
		"default_buyer": default_buyer,
		"category_province": cells(cat_prov),
		"category": cells(cat_only),
		"province": cells(prov_only),
	}
	return tables


def render(tables):
	"""Canonical JSON bytes: sorted keys, 1-space indent, trailing newline."""
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
	print(
		"wrote {0}: {1} buyer rows, {2} category x province cells, "
		"{3} category / {4} province fallbacks".format(
			out_path,
			len(tables["buyers"]),
			len(tables["category_province"]),
			len(tables["category"]),
			len(tables["province"]),
		)
	)
	return 0


if __name__ == "__main__":
	sys.exit(main(sys.argv))
