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

class BetRecord(Document):
	def validate(self):
		# 1. Fetch User Profile
		profile = frappe.get_doc("BetAssist User Profile", {"user": self.user})
		if not profile:
			frappe.throw(_("Please complete your onboarding profile setup before placing a bet."))
			
		# 2. Get Match Details
		match_doc = frappe.get_doc("BetAssist Match", self.match)
		
		# 3. Favorite Team Bias Verification (Absolute Blocks)
		is_fav_team = (
			match_doc.team_a in [profile.local_favorite_team, profile.intl_favorite_team] or
			match_doc.team_b in [profile.local_favorite_team, profile.intl_favorite_team]
		)
		if is_fav_team:
			frappe.throw(_("Betting on matches involving your favorite teams (local or international) is strictly blocked to eliminate bias."))

		# 4. Check Follow List (Must follow at least one team in the match to bet)
		is_following_team_a = frappe.db.exists("BetAssist Followed Team", {"user": self.user, "team": match_doc.team_a})
		is_following_team_b = frappe.db.exists("BetAssist Followed Team", {"user": self.user, "team": match_doc.team_b})
		
		if not (is_following_team_a or is_following_team_b):
			frappe.throw(_("You can only bet on matches involving teams you actively follow. Follow one of these teams to open betting markets."))

		# 5. Enforce 2% Monthly Budget Cap rule
		max_allowed_bet = profile.monthly_budget * 0.02
		if self.amount > max_allowed_bet:
			frappe.throw(_("Risk Enforced: Maximum bet limit per match is 2% of your monthly budget (R{0}). Your maximum stake is R{1}.").format(profile.monthly_budget, max_allowed_bet))

		# 6. Budget Sufficiency Check
		if profile.remaining_budget < self.amount:
			frappe.throw(_("Insufficient Budget: You have R{0} left in your monthly budget. Your stake is R{1}.").format(profile.remaining_budget, self.amount))

	def on_submit(self):
		# Deduct bet amount from user's remaining budget
		profile = frappe.get_doc("BetAssist User Profile", {"user": self.user})
		profile.remaining_budget = max(0, profile.remaining_budget - self.amount)
		if profile.remaining_budget <= 0:
			profile.budget_lock = 1
		profile.save(ignore_permissions=True)
		
		# Trigger budget threshold warning alerts if needed (e.g. remaining is 50% or 20%)
		self.check_budget_alerts(profile)

	def check_budget_alerts(self, profile):
		pct_used = ((profile.monthly_budget - profile.remaining_budget) / profile.monthly_budget) * 100
		
		# We log notification warnings (or queue push alerts)
		if pct_used >= 100:
			self.log_alert("100% Budget Exhausted. Betting is locked until next month.")
		elif pct_used >= 80:
			self.log_alert("Warning: You have used 80% of your monthly betting budget.")
		elif pct_used >= 50:
			self.log_alert("Info: You have used 50% of your monthly betting budget.")

	def log_alert(self, message):
		# Simulates putting alert in standard notification log
		log = frappe.get_doc({
			"doctype": "Notification Log",
			"for_user": self.user,
			"subject": "BetAssist Risk Alert",
			"email_content": message,
			"type": "Alert"
		})
		log.insert(ignore_permissions=True)
