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

"""SOFT integration between Tender Bid and the erp module's Quotation.

The erp module (forked ERPNext living in the pay repo) is OPTIONAL at compose
time, so every touchpoint here is guarded by ``frappe.db.exists("DocType",
"Quotation")`` and no erp file is ever modified:

- ``ensure_quotation_tender_field`` adds a ``tender_bid`` Custom Field to
  Quotation in guarded code (after_install hook + weekly sweep), NOT as a
  custom-field fixture - a fixture would break install on benches without
  the erp module. Idempotent; a no-op wherever Quotation does not exist.
- ``sync_quotation_link`` is a Quotation doc_event registered
  unconditionally in the manifest (hooks cannot be conditional; frappe
  consults doc_events by doctype name at runtime, so an entry for an absent
  doctype simply never fires). It keeps Tender Bid.quotation - the CANONICAL
  side of the link - in sync when a user picks a bid on the Quotation form
  in ERP, so the pack generator always finds pricing from the bid.

Deterministic and additive only. No AI.
"""

import frappe


def quotation_doctype_available():
	"""True when the erp module's Quotation doctype exists on this bench."""
	try:
		return bool(frappe.db.exists("DocType", "Quotation"))
	except Exception:
		return False


def ensure_quotation_tender_field():
	"""Creates the Quotation.tender_bid Custom Field where erp is composed.

	Guarded, idempotent, additive: runs from after_install and the weekly
	scheduler so a bench that gains the erp module later still picks the
	field up without a reinstall. Never touches the erp module's own files.
	"""
	if not quotation_doctype_available():
		return
	if not frappe.db.exists("DocType", "Tender Bid"):
		return
	if frappe.db.exists("Custom Field", "Quotation-tender_bid"):
		return

	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": "Quotation",
			"fieldname": "tender_bid",
			"label": "Tender Bid",
			"fieldtype": "Link",
			"options": "Tender Bid",
			"insert_after": "order_type",
			"description": (
				"Link this quotation to a claimed tender bid - the tender "
				"module's pack generator prices the bid's pricing schedule "
				"from these line items. Tender Bid.quotation is the canonical "
				"side of the link and syncs from this field on save."
			),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()


def sync_quotation_link(doc, method=None):
	"""Quotation validate doc_event: Quotation.tender_bid -> Tender Bid.quotation.

	No-ops when the erp module is absent (the event then never fires anyway),
	when the custom field has not been created yet, or when the named bid
	does not exist. Latest linked quotation wins on the bid.
	"""
	tender_bid = doc.get("tender_bid")
	if not tender_bid:
		return
	if not frappe.db.exists("DocType", "Tender Bid"):
		return
	if not frappe.db.exists("Tender Bid", tender_bid):
		return
	current = frappe.db.get_value("Tender Bid", tender_bid, "quotation")
	if current != doc.name:
		frappe.db.set_value("Tender Bid", tender_bid, "quotation", doc.name)
