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


class TenderDispatchRecord(Document):
	"""One accepted outbound send in the dispatch LEDGER (plan #11:
	ledger, not state - the forex checksummed-and-frozen discipline).
	Each record freezes what actually left the system: the sha256 of the
	dispatched pack HTML + manifest (correspondence: the message body)
	computed from the EXACT bytes handed to sendmail, plus File links to
	those bytes. Append-only, enforced here in code, not just by
	permissions: a ledger row that can be edited or deleted proves
	nothing in a dispute (KILL-ALT-OFFER territory) - so updates and
	deletes are refused for every role, and corrections are new records,
	never edits."""

	def validate(self):
		if not self.is_new():
			frappe.throw(
				"Tender Dispatch Record is an append-only ledger - records "
				"freeze what was actually sent and are never edited. Append "
				"a new record instead.",
				title="Dispatch Ledger Is Append-Only",
			)

	def on_trash(self):
		frappe.throw(
			"Tender Dispatch Record is an append-only ledger - records "
			"freeze what was actually sent and are never deleted.",
			title="Dispatch Ledger Is Append-Only",
		)
