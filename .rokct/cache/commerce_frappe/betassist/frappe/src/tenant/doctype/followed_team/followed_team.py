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
from frappe.utils import add_days, getdate, today
from frappe import _

# Tenant and session.user context isolation validation.

class FollowedTeam(Document):
	def before_insert(self):
		# Prevent duplicates
		exists = frappe.db.exists("BetAssist Followed Team", {"user": self.user, "team": self.team})
		if exists:
			frappe.throw(_("You are already following this team."))

	def on_trash(self):
		# Enforce "unfollow once per week" rule
		# We check if there's a log of them unfollowing this team in the last 7 days.
		last_unfollow = frappe.db.get_value(
			"BetAssist Unfollow Log",
			{"user": self.user, "team": self.team},
			"unfollowed_date",
			order_by="unfollowed_date desc"
		)
		
		if last_unfollow:
			seven_days_ago = add_days(getdate(today()), -7)
			if getdate(last_unfollow) > seven_days_ago:
				frappe.throw(_("You can only unfollow this team once per week. Please wait before unfollowing again."))
		
		# Record the unfollow log
		log = frappe.get_doc({
			"doctype": "BetAssist Unfollow Log",
			"user": self.user,
			"team": self.team,
			"unfollowed_date": today()
		})
		log.insert(ignore_permissions=True)
