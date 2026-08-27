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

try:
	from {app_name}.tender.control.api.telemetry import log_api_call
except Exception:  # standalone verify-suite load: no composed package to import from

	def log_api_call(endpoint, trace_id=None, **fields):
		"""Legacy stderr fallback, format-identical to the old print lines."""
		extras = "".join(f" {key}={value}" for key, value in fields.items())
		print(f"[tender.api] {endpoint}{extras} trace_id={trace_id}", file=sys.stderr)


@frappe.whitelist()
def get_pack_status(bid: str) -> dict:
	"""
	Returns the pack manifest for one of the caller's Tender Bids WITHOUT
	rendering the HTML: which forms the bid's regime demands, the fill
	coverage from the caller's Tender Business Profile, the fields still
	needing user input, and any open fatal compliance gates. Lets the UI
	show pack readiness before the user generates the printable pack.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("get_pack_status", trace_id, bid=bid)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)
	if frappe.session.user == "Guest":
		frappe.throw("Please log in to view pack status.", frappe.PermissionError)

	from {app_name}.tender.control.api.tenders.generate_bid_pack import (
		apply_custom_returnables,
		build_bid_context,
		load_profile,
		load_regime,
		load_templates,
	)
	from {app_name}.tender.control.api.tenders.tender_entitlement import get_owned_bid
	from {app_name}.tender.control.pack_builder import build_pack
	from {app_name}.tender.control.compliance.submission_gate import (
		submission_readiness_warnings,
		validate_submission_readiness,
	)

	bid_doc = get_owned_bid(bid)
	# Same pack assembly as generate_bid_pack (F-02: per-pack captured
	# returnables included) so the readiness view never disagrees with the
	# pack the user then generates.
	regime = apply_custom_returnables(load_regime(bid_doc), bid_doc)
	profile_doc, profile_values = load_profile(bid_doc.user)
	bid_ctx = build_bid_context(bid_doc)
	templates = load_templates()
	gate_failures = validate_submission_readiness(bid_doc)
	gate_warnings = submission_readiness_warnings(bid_doc)

	pack = build_pack(
		regime, templates, profile_values, bid_ctx, gate_failures, {"sign": False}, gate_warnings
	)
	manifest = pack["manifest"]
	manifest["has_profile"] = profile_doc is not None
	manifest["has_signature_image"] = bool(
		profile_doc and (profile_doc.get("signature_image_processed") or profile_doc.get("signature_image"))
	)
	return manifest
