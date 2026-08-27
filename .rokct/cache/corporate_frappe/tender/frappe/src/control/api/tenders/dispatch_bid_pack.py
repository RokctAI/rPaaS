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
from frappe.utils import now

try:
	from {app_name}.tender.control.api.telemetry import log_api_call
except Exception:  # standalone verify-suite load: no composed package to import from

	def log_api_call(endpoint, trace_id=None, **fields):
		"""Legacy stderr fallback, format-identical to the old print lines."""
		extras = "".join(f" {key}={value}" for key, value in fields.items())
		print(f"[tender.api] {endpoint}{extras} trace_id={trace_id}", file=sys.stderr)


MODE_PACK = "pack"
MODE_CORRESPONDENCE = "correspondence"

EMAIL_ALLOWED_CHANNEL = "Email allowed"


def normalize_email(value):
	"""Normalizes an address for the retype-to-confirm comparison: stripped,
	lowercased (mailbox addresses are case-insensitive in practice; demanding
	case-exact retyping punishes the user without adding safety). Pure."""
	return str(value or "").strip().lower()


@frappe.whitelist()
def dispatch_bid_pack(
	bid: str,
	mode: str = MODE_CORRESPONDENCE,
	confirm_email: str = None,
	subject: str = None,
	message: str = None,
) -> dict:
	"""
	Tiered, gated outbound email to the bid's named buyer contact (F-13).
	NOTHING sends without the caller retyping the stored destination address
	(``confirm_email``) - there is no automatic dispatch anywhere.

	``mode="pack"`` (tier a - the EXCEPTION path, RFQ-class): attaches the
	freshly regenerated bid pack - SIGNED (``generate_bid_pack(sign=1)``)
	whenever the caller's Tender Business Profile carries a signature image,
	i.e. whenever the review-then-sign flow can produce the signed pack
	(review follow-up: dispatching an unsigned regeneration when a signed
	pack was generated sent the wrong document). Without a signature image
	the unsigned pack is sent exactly as before, and the result names which
	one went out (``pack_signed``). Refused unless ALL of:
	  - the bid's submission_channel is "Email allowed" (all five mock-sample
	    packs demand sealed-envelope/tender-box submission and Musina
	    explicitly kills emailed bids - wrong channel = late = out);
	  - validate_submission_readiness returns no failures (a pack with open
	    fatal gates is undispatchable - a hard gate, not a setting);
	  - confirm_email matches the stored buyer_contact_email.

	``mode="correspondence"`` (tier b - what the packs DO allow): a plain
	message to the named contact (written clarification questions, briefing
	confirmations, cure-window replies - Musina is written-queries-only).
	No channel/readiness requirement, NEVER attaches the pack; the retype
	confirmation still applies.

	Sends through the notify() seam (plan #14) - the same frappe.sendmail
	call in the same try/except + log_error pattern, now shared with every
	other outbound notification: on a bench without a configured Email
	Account the endpoint degrades gracefully - the failure is logged and
	reported, audit fields stay unset.
	On success the read-only dispatched_on/dispatched_to audit fields are
	written and returned, and an append-only Tender Dispatch Record is
	appended (plan #11 immutability ledger): sha256 of the pack HTML +
	manifest exactly as attached (correspondence: the message body), with
	the sent bytes stored as private Files on the bid. The ledger write is
	guarded - dispatch NEVER fails because of it. Deterministic - no AI
	anywhere.
	"""
	trace_id = frappe.get_request_header("X-Trace-Id") if getattr(frappe.local, "request", None) else None
	log_api_call("dispatch_bid_pack", trace_id, bid=bid, mode=mode)
	if frappe.conf.get("app_role") != "control":
		frappe.throw(
			"This action can only be performed on the control panel site.", title="Action Not Allowed"
		)
	if frappe.session.user == "Guest":
		frappe.throw("Please log in to dispatch bid correspondence.", frappe.PermissionError)
	if mode not in (MODE_PACK, MODE_CORRESPONDENCE):
		frappe.throw(
			f"Unknown dispatch mode '{mode}' - use '{MODE_PACK}' or '{MODE_CORRESPONDENCE}'.",
			title="Invalid Mode",
		)

	from {app_name}.tender.control.api.tenders.tender_entitlement import get_owned_bid
	from {app_name}.tender.control.compliance.submission_gate import (
		validate_submission_readiness,
	)
	from {app_name}.tender.control.notify import notify

	bid_doc = get_owned_bid(bid)
	recipient = (bid_doc.get("buyer_contact_email") or "").strip()
	if not recipient:
		frappe.throw(
			"This bid has no buyer contact email captured - record the pack's "
			"named contact address on the bid first (it seeds from the "
			"opportunity record on claim when the registry carries one).",
			title="No Buyer Contact Email",
		)

	# Explicit per-send confirmation: the caller must retype the stored
	# destination address. Nothing leaves the system automatically.
	if normalize_email(confirm_email) != normalize_email(recipient):
		frappe.throw(
			"Dispatch requires retyping the stored buyer contact email as "
			f"confirmation. Stored address: {recipient} - pass it as "
			"confirm_email to confirm the destination.",
			title="Destination Not Confirmed",
		)

	attachments = None
	pack_signed = False
	if mode == MODE_PACK:
		channel = bid_doc.get("submission_channel") or ""
		if channel != EMAIL_ALLOWED_CHANNEL:
			frappe.throw(
				"Full-pack email dispatch is only available when this bid's "
				f"Submission Channel is '{EMAIL_ALLOWED_CHANNEL}' (currently: "
				f"'{channel or 'not recorded'}'). This pack must be delivered "
				"as the tender document prescribes - emailing a bid a buyer "
				"wants in a sealed tender box is not a submission and can "
				"disqualify outright. Use correspondence mode for allowed "
				"written contact.",
				title="Channel Does Not Allow Email Submission",
			)
		gate_failures = validate_submission_readiness(bid_doc)
		if gate_failures:
			frappe.throw(
				"This bid is not submission-ready - a pack with open fatal "
				"gates is undispatchable:\n- " + "\n- ".join(gate_failures),
				title="Submission Gates Open",
			)

		from {app_name}.tender.control.api.tenders.generate_bid_pack import (
			generate_bid_pack,
			load_profile,
		)

		# Send the SIGNED pack when one can be generated (review follow-up):
		# the review-then-sign flow's second step is generate_bid_pack(sign=1),
		# available exactly when the profile carries a signature image - an
		# email submission of the unsigned review pack is the wrong document.
		# No signature image -> the unsigned pack, exactly as before.
		profile_doc, _profile_values = load_profile(bid_doc.user)
		pack_signed = bool(
			profile_doc
			and (
				profile_doc.get("signature_image_processed")
				or profile_doc.get("signature_image")
			)
		)
		pack = generate_bid_pack(bid, sign=1 if pack_signed else 0)
		pack_suffix = "-signed" if pack_signed else ""
		attachments = [
			{"fname": f"{bid_doc.name}-bid-pack{pack_suffix}.html", "fcontent": pack["html"]},
			{
				"fname": f"{bid_doc.name}-manifest.json",
				"fcontent": json.dumps(pack["manifest"], indent=2, default=str),
			},
		]
		subject = subject or (
			f"Bid submission: {bid_doc.get('tender_title') or bid_doc.name} "
			f"({bid_doc.get('tender_slug') or bid_doc.name})"
		)
		message = message or (
			"Please find attached our bid pack for "
			f"{bid_doc.get('tender_title') or bid_doc.name}."
		)
	else:
		if not (message or "").strip():
			frappe.throw(
				"Correspondence mode needs a message body - this tier sends "
				"your written text to the named contact and never attaches "
				"the pack.",
				title="No Message",
			)
		subject = subject or (
			f"Regarding: {bid_doc.get('tender_title') or bid_doc.name} "
			f"({bid_doc.get('tender_slug') or bid_doc.name})"
		)

	# Through the notify() seam (plan #14): the same sendmail call in the
	# same try/except + log_error pattern, now living in one place. Delivery
	# still depends on the bench's configured Email Account: without one
	# this degrades gracefully instead of tracebacking, and the audit fields
	# are only written on an accepted send. Buyer-contact mail is gated by
	# the retype-to-confirm check above, never by the user opt-in flag.
	outcome = notify(
		recipients=[recipient],
		subject=subject,
		message=message,
		attachments=attachments,
		failure_log_title="Bid Pack Dispatch Failed",
	)
	if not outcome.get("sent"):
		return {
			"sent": False,
			"mode": mode,
			"reason": (
				"Email could not be handed to the mail system - the site may "
				"have no outgoing Email Account configured. Nothing was "
				"dispatched; the failure has been logged for the administrator."
			),
		}

	dispatched_on = now()
	bid_doc.db_set("dispatched_on", dispatched_on)
	bid_doc.db_set("dispatched_to", recipient)
	ledger = record_dispatch_ledger(
		bid_doc=bid_doc,
		mode=mode,
		recipient=recipient,
		subject=subject,
		message=message,
		attachments=attachments,
		pack_signed=pack_signed,
		dispatched_on=dispatched_on,
	)
	return {
		"sent": True,
		"mode": mode,
		"dispatched_to": recipient,
		"dispatched_on": dispatched_on,
		"subject": subject,
		"pack_attached": bool(attachments),
		"pack_signed": pack_signed,
		"ledger": ledger,
	}


def record_dispatch_ledger(
	bid_doc, mode, recipient, subject, message, attachments, pack_signed, dispatched_on
):
	"""Appends the immutability-ledger record for an ACCEPTED send (plan
	#11): sha256 of the dispatched pack HTML + manifest (correspondence:
	the message body) computed from the EXACT payloads handed to sendmail,
	the sent bytes stored as private Files on the bid, one append-only
	Tender Dispatch Record row tying it together.

	GUARDED - never raises. The email has already left the system when
	this runs, so a ledger failure must not fail the dispatch (the same
	graceful-degradation contract as the sendmail try/except above): any
	exception is logged and reported as recorded=False in the result,
	while sent stays True and the audit fields stand. Within that guard
	the File writes are individually best-effort too - a File store
	failure drops the file_url but never the digest (the checksum is the
	dispute evidence; the stored copy is convenience).
	"""
	try:
		from {app_name}.tender.control.compliance.dispatch_ledger import (
			build_dispatch_record,
		)

		record = build_dispatch_record(
			bid=bid_doc.name,
			mode=mode,
			recipient=recipient,
			subject=subject,
			message=message,
			dispatched_on=dispatched_on,
			attachments=attachments,
			pack_signed=pack_signed,
		)
		entries = record.pop("attachments")
		for entry, attachment in zip(entries, attachments or []):
			entry["file_url"] = store_sent_bytes(bid_doc, attachment)
		record_doc = frappe.get_doc(
			dict(
				record,
				doctype="Tender Dispatch Record",
				dispatched_by=frappe.session.user,
				attachments_json=json.dumps(entries, indent=1),
			)
		)
		record_doc.insert(ignore_permissions=True)
		return {
			"recorded": True,
			"record": record_doc.name,
			"pack_sha256": record["pack_sha256"] or None,
			"manifest_sha256": record["manifest_sha256"] or None,
			"message_sha256": record["message_sha256"] or None,
			"sent_files": [e.get("file_url") for e in entries if e.get("file_url")],
		}
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Dispatch Ledger Write Failed")
		return {
			"recorded": False,
			"note": (
				"The send succeeded but the dispatch ledger record could not "
				"be written; the failure has been logged for the administrator."
			),
		}


def store_sent_bytes(bid_doc, attachment):
	"""Stores one sent attachment's EXACT bytes as a private File on the
	bid; returns its file_url, or None on failure (best-effort inside the
	ledger guard - the digest in the record stands either way)."""
	try:
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"dispatched-{attachment['fname']}",
				"attached_to_doctype": "Tender Bid",
				"attached_to_name": bid_doc.name,
				"is_private": 1,
				"content": attachment["fcontent"],
			}
		)
		file_doc.insert(ignore_permissions=True)
		return file_doc.get("file_url")
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Dispatch Ledger File Store Failed")
		return None
