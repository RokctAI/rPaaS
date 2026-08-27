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

# This file uses the composer's literal {app_name} template placeholder in
# imports (fleet SDK convention, cf. polaris) - it only parses after
# composition substitutes the real app package name.
# compliance-ignore-file: syntax-error

"""Suitability drift report - the frappe glue around the pure corpus run
(assessment plan #9). Persistence and wiring ONLY: every measurement is
computed by the pure, standalone-testable
``compliance/suitability_drift.py`` (the renewal_sync.py pattern).

One entry point, :func:`run_suitability_drift_report`, scheduled weekly
via the module manifest: recomputes the calibration corpus run (gates
fired, band distribution, confidence mix, enrichment coverage) over the
cached live catalog against the FIXED reference personas, diffs it
against the latest stored snapshot, and stores the result as one Tender
Suitability Drift Snapshot per run. Deterministic, no AI.
"""

import json

import frappe
from frappe.utils import nowdate


def run_suitability_drift_report():
	"""cron hook
	Weekly scheduled task (module manifest): stores one suitability drift
	snapshot for today's cached catalog. Control hub only; idempotent per
	run date (a re-run on the same day is a no-op); an empty catalog cache
	stores nothing (an all-zero snapshot would read as drift, not as "the
	cache was cold"). Returns the inserted document name, or None.
	"""
	if frappe.conf.get("app_role") != "control":
		return None

	from {app_name}.tender.control.api.opportunity_utils import (
		get_cached_opportunities,
	)
	from {app_name}.tender.control.compliance.enrichment_gate import (
		load_gate_params,
	)
	from {app_name}.tender.control.compliance.rules import (
		get_scoring_rule,
		load_rules,
	)
	from {app_name}.tender.control.compliance.suitability_drift import (
		compare_snapshots,
		drift_snapshot,
	)

	records = get_cached_opportunities("tenders") or []
	if not records:
		return None
	meta = get_cached_opportunities("meta") or {}

	run_on = nowdate()
	if frappe.db.exists("Tender Suitability Drift Snapshot", {"run_on": run_on}):
		return None

	snapshot = drift_snapshot(
		records,
		enrichment_map=meta.get("advanced_enrichment"),
		rules_list=load_rules(),
		functionality_params=get_scoring_rule("SCORE-FUNCTIONALITY"),
		gate_params=load_gate_params(),
		today=run_on,
	)

	# Drift vs the latest stored snapshot (share deltas, count deltas) -
	# first run honestly says "no previous snapshot" instead of a fake
	# zero baseline.
	previous = frappe.get_all(
		"Tender Suitability Drift Snapshot",
		fields=["name", "payload"],
		order_by="run_on desc, name desc",
		limit=1,
	)
	previous_payload = None
	if previous:
		try:
			previous_payload = json.loads(previous[0].get("payload") or "null")
		except (TypeError, ValueError):
			previous_payload = None
	snapshot["drift_vs_previous"] = compare_snapshots(previous_payload, snapshot)

	catalog = snapshot.get("catalog") or {}
	doc = frappe.get_doc({
		"doctype": "Tender Suitability Drift Snapshot",
		"run_on": run_on,
		"catalog_total": catalog.get("total") or 0,
		"full_records": catalog.get("full") or 0,
		"advert_only_records": catalog.get("advert_only") or 0,
		"profiles_scored": len(snapshot.get("profiles") or {}),
		"payload": json.dumps(snapshot, sort_keys=True),
		"semantics": snapshot.get("semantics"),
	})
	doc.insert(ignore_permissions=True)
	return doc.name
