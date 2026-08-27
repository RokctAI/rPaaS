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
from frappe.utils import cint, now

try:
	from {app_name}.tender.control.api.telemetry import log_api_call
except Exception:  # standalone verify-suite load: no composed package to import from

	def log_api_call(endpoint, trace_id=None, **fields):
		"""Legacy stderr fallback, format-identical to the old print lines."""
		extras = "".join(f" {key}={value}" for key, value in fields.items())
		print(f"[tender.api] {endpoint}{extras} trace_id={trace_id}", file=sys.stderr)


@frappe.whitelist()
def attach_returnable_artifact(
	bid: str, ref_code: str, file_url: str = None, attest: int = 0, detach: int = 0
) -> dict:
	"""
	F-15(b): satisfies a captured returnable with a GENERATED artifact that
	is already attached to this bid - the TenderAssist-side hook of the
	studio integration (the studio/designer side is a separate workstream).

	The flow is deliberately two-step, mirroring review-then-sign and the
	F-13 dispatch discipline:

	1. attach: ``file_url`` must be a file attached to THIS Tender Bid (the
	   generated company profile the desk uploaded/attached) - never an
	   arbitrary File record. The row records the artifact but it does NOT
	   yet count: ``validate_submission_readiness`` fails with
	   [RETURNABLE-ARTIFACT-UNATTESTED] until the desk attests, and dispatch
	   gates on that list, so an unattested artifact never dispatches.
	2. attest: ``attest=1`` (with or after the attach) records the explicit
	   review of the generated document - only then is the returnable
	   satisfied (generated-and-attested).

	``detach=1`` clears the artifact and its attestation from the row.
	Deterministic, no AI; nothing is generated here - this endpoint only
	links an artifact the caller already holds.

	Plan #11 extension: the artifact's bytes are sha256-fingerprinted into
	``artifact_sha256`` on attach and RE-hashed at attest time, so the
	stored digest always fingerprints the document as reviewed - a later
	edit to the file is detectable (compliance.dispatch_ledger.
	artifact_unaltered). Hashing is guarded: a hash failure is logged and
	leaves the digest empty, it never blocks the attach/attest itself.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call(
		"attach_returnable_artifact", trace_id, bid=bid, ref_code=ref_code,
		attest=attest, detach=detach,
	)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)
	if frappe.session.user == "Guest":
		frappe.throw("Please log in to attach a returnable artifact.", frappe.PermissionError)

	from {app_name}.tender.control.api.tenders.tender_entitlement import get_owned_bid

	bid_doc = get_owned_bid(bid)
	row = find_returnable_row(bid_doc, ref_code)
	if row is None:
		frappe.throw(
			f"This bid has no captured returnable with ref code '{ref_code}' - "
			"capture the returnable row first (seed_bid_returnables / "
			"parse_tender_pack apply=1), then attach its artifact.",
			title="Returnable Not Found",
		)

	if cint(detach):
		row.generated_artifact = None
		row.artifact_attested = 0
		row.artifact_attached_on = None
		row.artifact_sha256 = None
	else:
		if file_url:
			require_file_attached_to_bid(bid_doc, file_url)
			row.generated_artifact = file_url
			row.artifact_attached_on = now()
			# a NEW artifact always resets the attestation - attest applies
			# to the document actually attached, never carried over
			row.artifact_attested = 1 if cint(attest) else 0
			# fingerprint the attached bytes (plan #11); attest-with-attach
			# hashes the same bytes the desk is attesting right now
			row.artifact_sha256 = compute_artifact_sha256(file_url)
		elif cint(attest):
			if not (row.get("generated_artifact") or "").strip():
				frappe.throw(
					"Nothing to attest - this returnable has no satisfying "
					"artifact attached yet; pass file_url first (or together "
					"with attest=1).",
					title="No Artifact Attached",
				)
			row.artifact_attested = 1
			# RE-hash at attest time (plan #11): the stored digest must
			# fingerprint the bytes as reviewed, not as first attached
			row.artifact_sha256 = compute_artifact_sha256(row.get("generated_artifact"))
		else:
			frappe.throw(
				"Pass file_url (attach a generated artifact already attached "
				"to this bid), attest=1 (attest the attached artifact), or "
				"detach=1 (clear it).",
				title="Nothing To Do",
			)

	bid_doc.save(ignore_permissions=True)
	frappe.db.commit()

	artifact = (row.get("generated_artifact") or "").strip()
	attested = bool(cint(row.get("artifact_attested")))
	return {
		"ref_code": row.get("ref_code"),
		"generated_artifact": artifact or None,
		"artifact_attested": attested,
		"artifact_attached_on": str(row.get("artifact_attached_on") or "") or None,
		"artifact_sha256": (row.get("artifact_sha256") or "").strip() or None,
		"satisfied": bool(artifact) and attested,
		"note": (
			"Satisfied: generated-and-attested." if bool(artifact) and attested
			else (
				"Artifact attached but NOT attested - readiness fails with "
				"[RETURNABLE-ARTIFACT-UNATTESTED] and the pack will not "
				"dispatch until the desk attests (attest=1) or detaches."
				if artifact else "No satisfying artifact on this returnable."
			)
		),
	}


def find_returnable_row(bid_doc, ref_code):
	"""The bid's custom_returnables row matching ref_code (case/whitespace-
	insensitive), or None. First match wins - ref codes are deduped on
	capture, so duplicates only arise from hand edits."""

	def norm(value):
		return " ".join(str(value or "").lower().split())

	wanted = norm(ref_code)
	if not wanted:
		return None
	for row in bid_doc.get("custom_returnables") or []:
		if norm(row.get("ref_code")) == wanted:
			return row
	return None


def require_file_attached_to_bid(bid_doc, file_url):
	"""Throws unless file_url is a File attached to THIS Tender Bid.

	Same entitlement discipline as parse_tender_pack's pack reading: the
	satisfying artifact must live on the bid it satisfies - other users'
	files (or free-floating uploads) are refused, never silently linked.
	"""
	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not file_name:
		frappe.throw(f"Attached file not found: {file_url}", title="File Not Found")
	file_doc = frappe.get_doc("File", file_name)
	if not (
		file_doc.get("attached_to_doctype") == "Tender Bid"
		and file_doc.get("attached_to_name") == bid_doc.name
	):
		frappe.throw(
			"That file is not attached to this bid - attach the generated "
			"artifact to the Tender Bid first, then link it to the returnable.",
			frappe.PermissionError,
		)


def compute_artifact_sha256(file_url):
	"""Hex sha256 of the artifact File's current bytes (plan #11 attest-time
	fingerprint), or None when it cannot be computed.

	GUARDED - never raises: the digest is audit sugar on top of the
	attach/attest flow, so a missing File record, an unreadable backing
	file, or any storage hiccup is logged and yields None instead of
	blocking the desk (the same failure-isolation contract as the dispatch
	ledger write). The hash itself is the ledger's single primitive,
	compliance.dispatch_ledger.sha256_hex.
	"""
	try:
		if not (file_url or "").strip():
			return None
		from {app_name}.tender.control.compliance.dispatch_ledger import sha256_hex

		file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
		if not file_name:
			return None
		file_doc = frappe.get_doc("File", file_name)
		content = file_doc.get_content()
		if content is None:
			return None
		return sha256_hex(content)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Returnable Artifact Hash Failed")
		return None
