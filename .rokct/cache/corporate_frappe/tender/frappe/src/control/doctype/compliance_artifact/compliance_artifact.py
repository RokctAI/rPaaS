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


import frappe
from frappe.model.document import Document
from frappe.utils import cint, date_diff, nowdate

# Days before valid_until at which an artifact turns Amber when the record
# carries no explicit renewal_window_days. Purely a date comparison - no AI.
DEFAULT_RENEWAL_WINDOW_DAYS = 30

# Artifact types with no expiry date of their own - everything else is a scan
# whose expiry CANNOT be read from the image deterministically, so the upload
# step must capture it as a user-entered field. Keep in sync with the
# mandatory_depends_on expression in compliance_artifact.json.
NON_EXPIRING_ARTIFACT_TYPES = ("Board Resolution", "JV Agreement", "Other")


class ComplianceArtifact(Document):
	def validate(self):
		self.require_expiry_for_expiring_types()
		self.status = self.compute_status()

	def require_expiry_for_expiring_types(self):
		"""Expiring artifact types must carry the user-entered expiry date."""
		if self.artifact_type in NON_EXPIRING_ARTIFACT_TYPES:
			return
		if not self.valid_until:
			frappe.throw(
				f"Enter the Expiry Date for this {self.artifact_type} - read it "
				"off the certificate itself. Expiry checks and bid gather-lists "
				"run off this field; a scan cannot be read automatically.",
				title="Expiry Date Required",
			)

	def compute_status(self):
		"""Deterministic traffic light from valid_until vs today.

		Expired: valid_until is in the past.
		Amber:   valid_until falls inside the renewal window.
		Green:   everything else (including artifacts with no expiry date).
		"""
		if not self.valid_until:
			return "Green"
		remaining = date_diff(self.valid_until, nowdate())
		if remaining < 0:
			return "Expired"
		window = cint(self.renewal_window_days) or DEFAULT_RENEWAL_WINDOW_DAYS
		if remaining <= window:
			return "Amber"
		return "Green"
