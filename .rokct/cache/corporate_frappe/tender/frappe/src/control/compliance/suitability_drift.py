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

"""Suitability recalibration drift report (assessment plan #9).

The suitability model was calibrated ONCE against 1,990 live cards
(Suitability-Scoring-Model.md, today = 2026-08-23). Cards churn; this
module recomputes the same corpus-run measurements on a schedule so the
fit score stays honest over time:

- **gates fired**: per-code counts of stage-1 hard failures over the
  live catalog (the model doc's "gate causes" column);
- **band distribution**: strong / review / marginal / poor / no_bid /
  unscored counts (the model doc's "bands" column);
- **confidence mix**: pack_verified vs advert_only (the enrichment
  coverage the score actually ran with);
- **enrichment coverage**: the existing ``enrichment_gate.
  enrichment_stats`` breakdown, reused verbatim (findings F-08).

Everything is scored against FIXED, COMMITTED reference profiles - the
calibration run's own P1/P2/P3 personas with synthetic registration
values - never against any user's data: the report measures how the
CATALOG drifts under a constant yardstick, so a shifted band histogram
means the card population moved, not a bidder. Cheap and deterministic
(the scoring engine is pure, the catalog is already cached); no AI, no
new statistics machinery - counts and medians only, per the module's
medians-never-means discipline.

Pure module: frappe-free, standalone-testable. The frappe glue
(``drift_report.py``) feeds it the cached catalog + fixture rules and
stores one Tender Suitability Drift Snapshot per run.
"""

# Same-package imports (F-09 pattern): relative on a composed bench, importlib
# fallback keeps this module importable standalone by file path.
try:
	from .enrichment_gate import enrichment_stats
	from .renewal import median_value
	from .suitability import score_suitability
except ImportError:  # standalone by-path import - load the siblings directly
	import importlib.util as _importlib_util
	import os as _os

	def _load_sibling(_module_name, _filename):
		_spec = _importlib_util.spec_from_file_location(
			_module_name,
			_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), _filename),
		)
		_module = _importlib_util.module_from_spec(_spec)
		_spec.loader.exec_module(_module)
		return _module

	enrichment_stats = _load_sibling(
		"tender_drift_enrichment_gate", "enrichment_gate.py"
	).enrichment_stats
	median_value = _load_sibling("tender_drift_renewal", "renewal.py").median_value
	score_suitability = _load_sibling(
		"tender_drift_suitability", "suitability.py"
	).score_suitability


BANDS = ("strong", "review", "marginal", "poor", "no_bid", "unscored")
CONFIDENCES = ("pack_verified", "advert_only")

# The calibration run's own reference personas (Suitability-Scoring-Model.md
# section "Validation", 1,990 cards, 2026-08-23), frozen as the drift
# yardstick. Registration values are SYNTHETIC reference constants - these
# are NOT user profiles and must never be replaced with one: a moving
# yardstick cannot measure drift.
REFERENCE_PROFILES = {
	"p1_services_smme": {
		# services SMME: 7 sectors, Gauteng, no CIDB grading
		"csd_maaa_number": "MAAA0000001",
		"tcs_pin": "PIN0000000001",
		"company_registration_no": "2020/000001/07",
		"vat_number": "4000000001",
		"enterprise_type": "EME (turnover under R10m - sworn affidavit)",
		"bbbee_level": "1",
		"bbbee_certificate_expiry": "2030-01-01",
		"cidb_grade": "",
		"operating_sectors": (
			"ICT, software, helpdesk, cleaning, security, catering, training"
		),
		"operating_provinces": "Gauteng",
		"briefing_travel_radius": "",
		"capability_texts": ["SYNTHETIC drift-reference persona P1"],
		"coida_good_standing": "1",
		"municipal_rates_current": "1",
		"psira_registered": "",
		"nhbrc_registered": "",
		"track_record_evidence": "1",
	},
	"p2_construction_smme": {
		# construction SMME: CIDB 2GB, Limpopo + Gauteng
		"csd_maaa_number": "MAAA0000002",
		"tcs_pin": "PIN0000000002",
		"company_registration_no": "2020/000002/07",
		"vat_number": "4000000002",
		"enterprise_type": "QSE (turnover R10m-R50m)",
		"bbbee_level": "2",
		"bbbee_certificate_expiry": "2030-01-01",
		"cidb_grade": "2GB",
		"operating_sectors": "construction, civil engineering, building maintenance",
		"operating_provinces": "Limpopo, Gauteng",
		"briefing_travel_radius": "",
		"capability_texts": ["SYNTHETIC drift-reference persona P2"],
		"coida_good_standing": "1",
		"municipal_rates_current": "1",
		"psira_registered": "",
		"nhbrc_registered": "1",
		"track_record_evidence": "1",
	},
	# the empty profile: every card must gate on PROFILE-INCOMPLETE - a
	# fixed canary that the profile-side gates still fire
	"p3_empty_profile": {},
}

SEMANTICS = (
	"scheduled suitability recalibration drift report - the calibration "
	"corpus run (gates fired, band distribution, confidence mix, "
	"enrichment coverage) recomputed over the live cached catalog against "
	"FIXED synthetic reference personas; deterministic counts and medians, "
	"no AI, measures catalog drift only - never a win probability, never "
	"a user's fit"
)

CAVEATS = [
	"scored against fixed SYNTHETIC reference personas (the calibration "
	"run's P1/P2/P3), never against user data - a drifted band histogram "
	"means the card population moved, not any bidder",
	"factor weights remain argued-not-fitted (the corpus holds no "
	"award-outcome data): this report keeps the yardstick honest, it does "
	"not validate the weights",
	"confidence mix tracks published enrichment coverage - a falling "
	"pack_verified share is a catalog/enrichment change, not a scoring "
	"regression",
]


def _profile_snapshot(records, profile, enrichment_map, rules_list,
		functionality_params, today):
	"""One reference persona's corpus run: counts only, deterministic."""
	bands = {band: 0 for band in BANDS}
	confidence = {conf: 0 for conf in CONFIDENCES}
	gates = {}
	scores = []
	scored = 0
	for record in records or []:
		if not isinstance(record, dict) or not record:
			continue
		slug = record.get("slug") or record.get("tender_number") or record.get("ocid")
		entry = (enrichment_map or {}).get(slug) if slug else None
		result = score_suitability(
			record,
			profile,
			rules_list=rules_list,
			enrichment_entry=entry,
			functionality_params=functionality_params,
			opportunity_type="tenders",
			today=today,
		)
		scored += 1
		band = result.get("band")
		bands[band if band in bands else "unscored"] += 1
		conf = result.get("confidence")
		if conf in confidence:
			confidence[conf] += 1
		for failure in result.get("hard_failures") or []:
			code = str((failure or {}).get("code") or "")
			if code:
				gates[code] = gates.get(code, 0) + 1
		if result.get("score") is not None:
			scores.append(result["score"])
	return {
		"cards_scored": scored,
		"bands": bands,
		"confidence": confidence,
		"gates_fired": {code: gates[code] for code in sorted(gates)},
		"scores": {
			"scored": len(scores),
			"distinct": len(set(scores)),
			"min": min(scores) if scores else None,
			"median": median_value(scores),
			"max": max(scores) if scores else None,
		},
	}


def drift_snapshot(records, enrichment_map=None, rules_list=None,
		functionality_params=None, gate_params=None, today=None,
		profiles=None):
	"""The full drift report for one run - a plain, storable dict.

	``records`` is the cached published tender catalog, ``enrichment_map``
	the meta.json ``advanced_enrichment`` map, ``rules_list`` /
	``functionality_params`` / ``gate_params`` the fixture-shipped rule
	state (exactly what the live endpoints load). Deterministic: identical
	inputs give an identical snapshot, key order included.
	"""
	profiles = profiles or REFERENCE_PROFILES
	enrichment_map = enrichment_map if isinstance(enrichment_map, dict) else {}
	catalog = enrichment_stats(records, enrichment_map, gate_params)
	return {
		"run_on": str(today or ""),
		"catalog": catalog,
		"profiles": {
			key: _profile_snapshot(
				records, profiles[key], enrichment_map, rules_list,
				functionality_params, today,
			)
			for key in sorted(profiles)
		},
		"semantics": SEMANTICS,
		"caveats": list(CAVEATS),
	}


def _share_pct(count, total):
	return round(count / total * 100.0, 1) if total else None


def compare_snapshots(previous, current):
	"""Band/confidence/gate drift between two snapshots, in plain deltas.

	Percentage-point deltas for band and confidence SHARES (so catalog
	growth alone reads as zero drift) and raw count deltas per gate code.
	``previous`` may be None (first run): the result then says so instead
	of inventing a baseline.
	"""
	if not isinstance(previous, dict) or not previous:
		return {"available": False, "reason": "no previous snapshot"}
	delta = {
		"available": True,
		"previous_run_on": str(previous.get("run_on") or ""),
		"catalog_total_delta": (
			(current.get("catalog") or {}).get("total", 0)
			- (previous.get("catalog") or {}).get("total", 0)
		),
		"profiles": {},
	}
	prev_profiles = previous.get("profiles") or {}
	for key, cur in sorted((current.get("profiles") or {}).items()):
		prev = prev_profiles.get(key)
		if not prev:
			delta["profiles"][key] = {"available": False, "reason": "new profile"}
			continue
		cur_total = cur.get("cards_scored") or 0
		prev_total = prev.get("cards_scored") or 0
		bands = {}
		for band in BANDS:
			cur_share = _share_pct((cur.get("bands") or {}).get(band, 0), cur_total)
			prev_share = _share_pct((prev.get("bands") or {}).get(band, 0), prev_total)
			bands[band] = (
				round(cur_share - prev_share, 1)
				if cur_share is not None and prev_share is not None
				else None
			)
		confidence = {}
		for conf in CONFIDENCES:
			cur_share = _share_pct(
				(cur.get("confidence") or {}).get(conf, 0), cur_total
			)
			prev_share = _share_pct(
				(prev.get("confidence") or {}).get(conf, 0), prev_total
			)
			confidence[conf] = (
				round(cur_share - prev_share, 1)
				if cur_share is not None and prev_share is not None
				else None
			)
		cur_gates = cur.get("gates_fired") or {}
		prev_gates = prev.get("gates_fired") or {}
		gates = {
			code: cur_gates.get(code, 0) - prev_gates.get(code, 0)
			for code in sorted(set(cur_gates) | set(prev_gates))
		}
		delta["profiles"][key] = {
			"available": True,
			"cards_scored_delta": cur_total - prev_total,
			"band_share_delta_pct": bands,
			"confidence_share_delta_pct": confidence,
			"gates_fired_delta": gates,
		}
	return delta
