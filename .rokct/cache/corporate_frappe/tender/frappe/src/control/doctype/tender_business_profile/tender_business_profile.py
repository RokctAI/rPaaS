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


import frappe
from frappe.model.document import Document

# The pack builder auto-fills form templates from these profile fields
# (Tender Form Template Field.source_field with source_type "Profile Field").
# Keep this list in sync with the doctype JSON - the fixture-integrity test
# asserts every template mapping resolves against it.
FILL_FIELDS = (
	"trading_name",
	"registered_name",
	"company_registration_no",
	"vat_number",
	"csd_maaa_number",
	"tcs_pin",
	"enterprise_type",
	"bbbee_level",
	"bbbee_certificate_expiry",
	"cidb_grade",
	"physical_address",
	"postal_address",
	"contact_person",
	"contact_phone",
	"contact_email",
	"authorized_signatory_name",
	"authorized_signatory_capacity",
	"authorized_signatory_id_number",
	"directors",
	"capabilities",
)


class TenderBusinessProfile(Document):
	def validate(self):
		self.process_stamp_images()

	def process_stamp_images(self):
		"""Regenerates the transparent-PNG working copies of signature images.

		Runs once at upload (and again only when the source attachment
		changes): the uploaded scan's solid background is stripped by the
		deterministic Pillow pipeline in tender.imaging.signature_stamp so a
		signed pack stamps ink strokes, not a solid box, onto the form.
		"""
		before = self.get_doc_before_save()

		self.signature_image_processed = self._ensure_processed(
			self.signature_image,
			self.signature_image_processed,
			before.get("signature_image") if before else None,
			"signature",
		)
		self.initials_image_processed = self._ensure_processed(
			self.initials_image,
			self.initials_image_processed,
			before.get("initials_image") if before else None,
			"initials",
		)

		previous_witnesses = {}
		if before:
			for row in before.get("witnesses") or []:
				previous_witnesses[row.get("name")] = row.get("signature_image")
		for index, row in enumerate(self.get("witnesses") or []):
			row.signature_image_processed = self._ensure_processed(
				row.signature_image,
				row.signature_image_processed,
				previous_witnesses.get(row.name),
				f"witness_{index + 1}",
			)

	def _ensure_processed(self, source_url, processed_url, previous_source_url, label):
		"""Returns the processed-file URL for a source image, regenerating it
		only when the source is new or changed. No source -> no working copy."""
		if not source_url:
			return None
		if processed_url and previous_source_url == source_url:
			return processed_url

		from {app_name}.tender.control.imaging.signature_stamp import strip_background

		content = self._read_attachment(source_url)
		try:
			processed = strip_background(content)
		except Exception:
			frappe.throw(
				f"Could not process the {label} image - upload a clear scan of "
				"dark ink on plain WHITE paper (solid colors also work).",
				title="Signature Processing Failed",
			)
		return self._save_processed(processed, label)

	def _read_attachment(self, file_url):
		file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
		if not file_name:
			frappe.throw(f"Attached file not found: {file_url}")
		return frappe.get_doc("File", file_name).get_content()

	def _save_processed(self, content, label):
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{label}_stamp.png",
				"attached_to_doctype": self.doctype,
				"attached_to_name": self.name,
				"is_private": 1,
				"content": content,
			}
		)
		file_doc.insert(ignore_permissions=True)
		return file_doc.file_url
