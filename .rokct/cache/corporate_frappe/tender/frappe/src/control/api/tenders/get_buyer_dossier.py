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

import sys

import frappe
from frappe.utils import nowdate

try:
	from {app_name}.tender.control.api.telemetry import log_api_call
except Exception:  # standalone verify-suite load: no composed package to import from

	def log_api_call(endpoint, trace_id=None, **fields):
		"""Legacy stderr fallback, format-identical to the old print lines."""
		extras = "".join(f" {key}={value}" for key, value in fields.items())
		print(f"[tender.api] {endpoint}{extras} trace_id={trace_id}", file=sys.stderr)


@frappe.whitelist()
def get_buyer_dossier(buyer: str = "") -> dict:
	"""
	Per-buyer behavioural dossier from the published eTenders award
	record: award volume, typical award value (median/IQR, N-gated),
	supplier concentration over identified awards, and the
	newcomer-openness proxy - plus the honesty caveats on every response
	(winner-side data only, publication-discipline bias, proxy
	semantics).

	Aggregate PUBLIC data only - everything served here was computed
	deterministically at build time from the committed awards dataset
	(``tools/build_buyer_dossiers.py``); this endpoint only reads the
	fixture, it never scores and never predicts.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("get_buyer_dossier", trace_id)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)

	if frappe.session.user == "Guest":
		frappe.throw("Please log in to view buyer dossiers.", frappe.PermissionError)

	from {app_name}.tender.control.compliance.buyer_dossiers import (
		resolve_buyer_dossier,
	)

	payload = resolve_buyer_dossier(buyer)
	payload["renewal"] = _renewal_hooks(buyer, payload)
	payload["generated_on"] = str(nowdate())
	return payload


def _renewal_hooks(buyer, payload):
	"""Renewal Watch lateness/trust counters for this buyer, or None.

	ADDITIVE hook into the renewal ledger (Renewal Watch, #56): where this
	buyer has RESOLVED renewal predictions, the dossier also carries the
	counter-based trust (confirmed / missed / hit rate - counts, never
	probabilities) and the median lateness correction in days ("this buyer
	re-advertises about N days late against stated durations"). The join
	key is the shared ``normalize_buyer`` normalization both the dossier
	fixture and the ledger use. Guarded: any failure (no doctype yet, no
	ledger rows) serves the dossier exactly as before, with None here.
	"""
	try:
		from {app_name}.tender.control.compliance.market_context import normalize_buyer
		from {app_name}.tender.control.compliance.renewal import (
			buyer_lateness_days,
			buyer_trust,
		)

		candidates = {normalize_buyer(buyer)}
		dossier = payload.get("dossier") or {}
		if dossier.get("buyer"):
			candidates.add(normalize_buyer(dossier["buyer"]))
		candidates.discard("")
		if not candidates:
			return None
		resolved = frappe.get_all(
			"Tender Renewal Watch",
			filters={
				"status": ("in", ("confirmed", "missed")),
				"buyer_normalized": ("in", sorted(candidates)),
			},
			fields=["buyer_normalized", "status", "error_days"],
		)
		if not resolved:
			return None
		trust_by_buyer = buyer_trust(resolved)
		lateness_by_buyer = buyer_lateness_days(resolved)
		# Deterministic merge across alias keys: sum the counters, take the
		# lateness of the key with the most resolved predictions (ties by
		# key order) - one buyer, one block.
		confirmed = sum(t["confirmed"] for t in trust_by_buyer.values())
		missed = sum(t["missed"] for t in trust_by_buyer.values())
		resolved_total = confirmed + missed
		best_key = sorted(
			trust_by_buyer,
			key=lambda key: (-trust_by_buyer[key]["resolved"], key),
		)[0]
		return {
			"trust": {
				"confirmed": confirmed,
				"missed": missed,
				"resolved": resolved_total,
				"hit_rate_pct": (
					round(100.0 * confirmed / resolved_total, 2)
					if resolved_total else None
				),
			},
			"lateness_days": lateness_by_buyer.get(best_key),
			"semantics": (
				"renewal-ledger counters (Renewal Watch): resolved "
				"re-advertisement predictions for this buyer - counts and a "
				"median lateness correction, never probabilities"
			),
		}
	except Exception:
		return None
