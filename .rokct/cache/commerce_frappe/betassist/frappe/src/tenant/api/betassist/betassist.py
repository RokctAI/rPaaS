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
from typing import Optional


@frappe.whitelist(allow_guest=True)
def register_user(
    partner_id: str,
    partner_user_id: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    email: Optional[str] = None,
    age: Optional[int] = None,
    id_number: Optional[str] = None,
) -> dict:
	"""Registers a new user profile under a specific partner.
	Supports full app-side signup variables or anonymous client tokens.
	If partner_user_id is not provided, a unique anonymous hash is generated.
	On repeat calls for the same user, optionally updates supplied profile fields.
	"""
	import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
	if not partner_id:
		frappe.throw("Missing partner_id parameter.")

	if not partner_user_id:
		partner_user_id = "usr_" + frappe.generate_hash(length=12)

	unique_user_id = f"{partner_id}_{partner_user_id}"

	profile_name = frappe.db.get_value("User Profile", {"user": unique_user_id})

	if not profile_name:
		profile = frappe.get_doc({
			"doctype": "User Profile",
			"user": unique_user_id,
			"partner_id": partner_id,
			"partner_user_id": partner_user_id,
			"username": username,
			"password": password,
			"email": email,
			"age": int(age) if age else None,
			"id_number": id_number,
			"monthly_budget": 5000.00,
			"remaining_budget": 5000.00,
			"budget_lock": 0
		})
		profile.insert(ignore_permissions=True)
		frappe.db.commit()
	else:
		profile = frappe.get_doc("User Profile", profile_name)
		updated = False
		if username and profile.username != username:
			profile.username = username
			updated = True
		if password and profile.password != password:
			profile.password = password
			updated = True
		if email and profile.email != email:
			profile.email = email
			updated = True
		if age and profile.age != int(age):
			profile.age = int(age)
			updated = True
		if id_number and profile.id_number != id_number:
			profile.id_number = id_number
			updated = True

		if updated:
			profile.save(ignore_permissions=True)
			frappe.db.commit()

	return {
		"status": "success",
		"partner_id": partner_id,
		"partner_user_id": partner_user_id,
		"unique_user_id": unique_user_id
	}


@frappe.whitelist(allow_guest=True)
def get_matches_feed(partner_id: Optional[str] = None, user_id: Optional[str] = None) -> dict:
	"""Retrieves live and upcoming matches with AI analysis confidence scores.
	Optionally accepts a user_id to annotate each match with is_following status
	based on the user's followed teams in the database.
	"""
	import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
	matches = frappe.get_all(
		"Match",
		filters={"status": ["in", ["Scheduled", "In Play"]]},
		fields=["name", "team_a", "team_b", "kickoff_time", "league", "status", "score"]
	)

	followed_teams = []
	if user_id:
		followed_teams = [
			f.team for f in frappe.get_all(
				"Followed Team",
				filters={"user": user_id},
				fields=["team"]
			)
		]

	results = []
	for m in matches:
		team_a_name, team_a_logo = frappe.db.get_value("Team", m.team_a, ["team_name", "logo_url"]) or (m.team_a, "⚽")
		team_b_name, team_b_logo = frappe.db.get_value("Team", m.team_b, ["team_name", "logo_url"]) or (m.team_b, "⚽")

		analysis = frappe.db.get_value(
			"Match Analysis",
			{"match": m.name},
			["confidence_score", "prediction", "why_win_text", "why_lose_text"],
			as_dict=True
		) or {}

		is_following = (m.team_a in followed_teams or m.team_b in followed_teams)

		results.append({
			"id": m.name,
			"teamA": team_a_name,
			"teamB": team_b_name,
			"teamALogo": team_a_logo,
			"teamBLogo": team_b_logo,
			"kickoff_time": str(m.kickoff_time),
			"league": m.league,
			"status": m.status,
			"score": m.score or "0-0",
			"is_following": is_following,
			"analysis": {
				"confidence_score": float(analysis.get("confidence_score") or 50.0),
				"prediction": analysis.get("prediction") or "Draw",
				"why_win": analysis.get("why_win_text") or "No analysis available.",
				"why_lose": analysis.get("why_lose_text") or "No vulnerabilities reports."
			}
		})

	return {
		"status": "success",
		"matches": results
	}


@frappe.whitelist(allow_guest=True)
def log_bet(
    partner_id: str,
    user_id: str,
    match_id: str,
    bet_amount: float,
    selection: str,
    bookmaker: Optional[str] = None,
) -> dict:
	"""Logs a placed bet for an anonymous user under a specific partner.
	Enforces three discipline rules before recording:
	  1. The bet amount must not exceed 2% of the user's monthly budget.
	  2. The user's budget must not be exhausted or locked.
	  3. The match must not involve the user's favorite (bias-locked) team.
	On success, deducts the amount from remaining_budget and tracks 5% affiliate commission.
	"""
	import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
	if not partner_id or not user_id:
		frappe.throw("Parameters partner_id and user_id are required.")

	profile_name = frappe.db.get_value("User Profile", {"user": user_id, "partner_id": partner_id})
	if not profile_name:
		frappe.throw(f"User Profile not found for {user_id} under partner {partner_id}.")

	profile = frappe.get_doc("User Profile", profile_name)
	amount = float(bet_amount)

	max_allowed_stake = profile.monthly_budget * 0.02
	if amount > max_allowed_stake:
		frappe.throw(f"Disciplined Bet Cap violation: Bet R{amount:.2f} exceeds your 2% maximum limit of R{max_allowed_stake:.2f}.")

	if profile.budget_lock or amount > profile.remaining_budget:
		frappe.throw("Budget Exhausted: Your account's betting budget limit has been reached.")

	match_doc = frappe.get_doc("Match", match_id)
	is_bias_match = (profile.local_favorite_team in [match_doc.team_a, match_doc.team_b] or
	                  profile.intl_favorite_team in [match_doc.team_a, match_doc.team_b])

	if is_bias_match:
		frappe.throw("Personal Bias Block: You are prohibited from betting on matches involving your favorite locked teams.")

	commission = amount * 0.05
	bet_rec = frappe.get_doc({
		"doctype": "Bet Record",
		"user": user_id,
		"partner_id": partner_id,
		"match": match_id,
		"amount": amount,
		"selection": selection,
		"outcome": "Pending",
		"commission_earned": commission,
		"bookmaker": bookmaker or "Partner Bookmaker"
	})
	bet_rec.insert(ignore_permissions=True)

	profile.remaining_budget = profile.remaining_budget - amount
	if profile.remaining_budget <= 0:
		profile.budget_lock = 1
	profile.save(ignore_permissions=True)

	frappe.db.commit()

	return {
		"status": "success",
		"bet_record_id": bet_rec.name,
		"commission_tracked": commission
	}


@frappe.whitelist()
def offboard_partner(partner_id: str) -> dict:
	"""Purges all user profiles and transaction records for a given partner_id.
	Restricted to System Manager administrators only.
	Deletes User Profile, Bet Record, Followed Team, and Unfollow Log rows
	matching the partner_id. Shared Match and Match Analysis data is preserved.
	"""
	import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
	if "System Manager" not in frappe.get_roles(frappe.session.user):
		frappe.throw("Unauthorized. System Manager role required.", frappe.PermissionError)

	if not partner_id:
		frappe.throw("Partner ID is required.")

	frappe.db.delete("User Profile", {"partner_id": partner_id})
	frappe.db.delete("Bet Record", {"partner_id": partner_id})
	frappe.db.delete("Followed Team", {"partner_id": partner_id})
	frappe.db.delete("Unfollow Log", {"partner_id": partner_id})

	frappe.db.commit()

	return {
		"status": "success",
		"message": f"Successfully purged all user data for offboarded partner: {partner_id}"
	}
