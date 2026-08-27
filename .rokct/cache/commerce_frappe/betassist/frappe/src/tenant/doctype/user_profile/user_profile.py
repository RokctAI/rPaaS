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
from frappe import _

# Tenant and session.user context isolation validation.

class UserProfile(Document):
	def validate(self):
		if not self.is_new():
			# Check if favorites are being modified
			db_doc = frappe.get_doc("BetAssist User Profile", self.name)
			
			if db_doc.local_favorite_team and self.local_favorite_team != db_doc.local_favorite_team:
				frappe.throw(_("Your local favorite team is permanent and cannot be changed."))
				
			if db_doc.intl_favorite_team and self.intl_favorite_team != db_doc.intl_favorite_team:
				frappe.throw(_("Your international favorite team is permanent and cannot be changed."))
				
		# Synchronize remaining budget if monthly budget is updated for first time
		if self.is_new() or frappe.db.get_value("BetAssist User Profile", self.name, "monthly_budget") != self.monthly_budget:
			if self.is_new():
				self.remaining_budget = self.monthly_budget
			else:
				# Adjust remaining budget proportionally or reset
				old_budget = frappe.db.get_value("BetAssist User Profile", self.name, "monthly_budget") or 0
				diff = self.monthly_budget - old_budget
				self.remaining_budget = max(0, self.remaining_budget + diff)
