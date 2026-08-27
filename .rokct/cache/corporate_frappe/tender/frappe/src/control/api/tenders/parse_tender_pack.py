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

import json
import sys

import frappe
from frappe.utils import cint

try:
	from {app_name}.tender.control.api.telemetry import log_api_call
except Exception:  # standalone verify-suite load: no composed package to import from

	def log_api_call(endpoint, trace_id=None, **fields):
		"""Legacy stderr fallback, format-identical to the old print lines."""
		extras = "".join(f" {key}={value}" for key, value in fields.items())
		print(f"[tender.api] {endpoint}{extras} trace_id={trace_id}", file=sys.stderr)


@frappe.whitelist()
def parse_tender_pack(
	bid: str, file_url: str = None, pack_text: str = None, apply: int = 0,
	selected_refs=None,
) -> dict:
	"""
	Deterministic pack parsing (findings F-02 full, first pass): reads the
	text layer of the buyer's actual pack document and PREVIEWS what the
	desk currently types by hand - the pack's returnable-document list as
	proposed Tender Bid Returnable rows (each with the quoted source line as
	guidance) and proposed field values (closing date, functionality
	threshold, preference system, submission channel) with [PARSE-CONFLICT]
	warnings where the pack disagrees with what the bid already holds.

	Fixed pattern rules only - NO AI, NO OCR, no network. Anything the
	patterns cannot read verbatim comes back NOT-FOUND, never guessed.

	Input: ``file_url`` of a file attached to this bid or to one of the
	caller's Compliance Artifacts (PDF or plain text), or ``pack_text``
	pasted directly. PDF extraction needs pypdf (declared dependency) or
	pdfminer.six on the bench; without either, PDFs return an explicit
	extractor-missing error and pack_text still works.

	Apply convention (same as seed_bid_returnables): ``apply=0`` (default)
	only returns the preview - the bid is NEVER modified. ``apply=1``
	appends the proposed returnable rows to the bid's custom_returnables
	(``selected_refs`` - a JSON array or comma-separated string of ref
	codes - restricts which; omitted = all proposed), skipping ref codes the
	bid already carries. Proposed FIELD values are never applied by this
	endpoint at all - the desk sets them by hand off the preview.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("parse_tender_pack", trace_id, bid=bid, file_url=file_url, apply=apply)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)
	if frappe.session.user == "Guest":
		frappe.throw("Please log in to parse a tender pack.", frappe.PermissionError)

	from {app_name}.tender.control.api.tenders.tender_entitlement import get_owned_bid
	from {app_name}.tender.control.parsing.text_extract import extract_pack_text
	from {app_name}.tender.control.parsing.pack_parse import parse_pack_text
	from {app_name}.tender.control.parsing.pack_ingest import build_ingest_preview

	bid_doc = get_owned_bid(bid)

	if pack_text and str(pack_text).strip():
		extraction = extract_pack_text(str(pack_text))
	elif file_url:
		content, file_name = read_owned_pack_file(bid_doc, file_url)
		extraction = extract_pack_text(content, filename=file_name)
	else:
		frappe.throw(
			"Provide file_url (a pack file attached to this bid or to one of "
			"your Compliance Artifacts) or pack_text (the pack's text pasted "
			"directly).",
			title="No Pack Provided",
		)

	if extraction["status"] != "ok":
		# Explicit degradation - a scan or a missing extractor is reported,
		# never silently parsed as empty (the parser must not "find nothing"
		# on a pack it could not read).
		return {
			"extraction": {k: v for k, v in extraction.items() if k != "text"},
			"parse": None,
			"preview": None,
			"applied": 0,
		}

	# Renewal Watch learning hook (pack-duration coverage, research
	# section 8: adverts state the term ~32% of the time, packs far more
	# often): a successfully extracted pack text feeds its stated contract
	# duration into the renewal ledger. Additive - never breaks parsing.
	try:
		from {app_name}.tender.control.renewal_sync import record_pack_duration

		record_pack_duration(bid_doc, extraction["text"])
	except Exception:
		try:
			frappe.log_error(frappe.get_traceback(), "tender renewal pack duration")
		except Exception:
			pass  # best-effort logging - the hook must NEVER break parsing

	parse_result = parse_pack_text(extraction["text"])
	preview = build_ingest_preview(
		parse_result, bid_snapshot(bid_doc), known_template_codes()
	)
	result = {
		"extraction": {k: v for k, v in extraction.items() if k != "text"},
		"parse": parse_result,
		"preview": preview,
		"applied": 0,
		"note": (
			"Preview only - nothing has been applied. Re-call with apply=1 "
			"(optionally selected_refs) to append the selected proposed "
			"returnable rows; field values are never applied automatically."
		),
	}
	if not cint(apply):
		return result

	appended = 0
	for row in select_rows(preview["proposed_returnables"], selected_refs):
		bid_doc.append("custom_returnables", row)
		appended += 1
	if appended:
		bid_doc.save(ignore_permissions=True)
		frappe.db.commit()
	result["applied"] = appended
	return result


def select_rows(proposed_rows, selected_refs):
	"""The proposed rows the caller selected (all when no selection given).

	``selected_refs`` accepts a JSON array or a comma-separated string of
	ref codes; matching is whitespace/case-insensitive. Pure function.
	"""
	refs = parse_selected_refs(selected_refs)
	if refs is None:
		return list(proposed_rows or [])

	def norm(value):
		return " ".join(str(value or "").lower().split())

	wanted = {norm(ref) for ref in refs} - {""}
	return [row for row in proposed_rows or [] if norm(row.get("ref_code")) in wanted]


def parse_selected_refs(selected_refs):
	"""selected_refs -> list of ref codes, or None for 'no selection made'."""
	if selected_refs in (None, ""):
		return None
	if isinstance(selected_refs, (list, tuple)):
		return list(selected_refs)
	if isinstance(selected_refs, str):
		try:
			parsed = json.loads(selected_refs)
			if isinstance(parsed, list):
				return parsed
		except (TypeError, ValueError):
			pass
		return [part.strip() for part in selected_refs.split(",") if part.strip()]
	return None


def bid_snapshot(bid_doc) -> dict:
	"""The plain-dict slice of the bid the ingest preview compares against."""
	return {
		"closing_date": str(bid_doc.get("closing_date") or "") or None,
		"functionality_threshold": bid_doc.get("functionality_threshold"),
		"preference_system": bid_doc.get("preference_system"),
		"submission_channel": bid_doc.get("submission_channel"),
		"custom_returnables": [
			{"ref_code": row.get("ref_code")}
			for row in (bid_doc.get("custom_returnables") or [])
		],
	}


def known_template_codes():
	"""Existing Tender Form Template codes, or None when unknowable (the
	ingest preview then proposes no template links rather than guessing)."""
	try:
		return frappe.get_all("Tender Form Template", pluck="template_code")
	except Exception:
		return None


def read_owned_pack_file(bid_doc, file_url):
	"""(content_bytes, file_name) for a file_url the caller may read.

	The file must be attached to THIS bid or to a Compliance Artifact
	belonging to the caller - never an arbitrary File record (private packs
	of other users stay private).
	"""
	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not file_name:
		frappe.throw(f"Attached file not found: {file_url}", title="File Not Found")
	file_doc = frappe.get_doc("File", file_name)

	attached_doctype = file_doc.get("attached_to_doctype")
	attached_name = file_doc.get("attached_to_name")
	allowed = False
	if attached_doctype == "Tender Bid" and attached_name == bid_doc.name:
		allowed = True
	elif attached_doctype == "Compliance Artifact" and attached_name:
		owner_user = frappe.db.get_value("Compliance Artifact", attached_name, "user")
		allowed = owner_user == frappe.session.user
	if not allowed:
		frappe.throw(
			"That file is not attached to this bid or to one of your "
			"Compliance Artifacts.",
			frappe.PermissionError,
		)
	return file_doc.get_content(), file_doc.get("file_name")
