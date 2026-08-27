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

"""Tender Bid computed fields - recalculated on every save (doc-event hook).

Registered in the module manifest as the Tender Bid ``validate`` doc_event.
All values derive from checklist rows and fixture-shipped scoring constants:
pure arithmetic, no AI.
"""

from frappe.utils import flt

from {app_name}.tender.control.compliance.checklist import sync_compliance_checklist
from {app_name}.tender.control.compliance.rules import get_scoring_rule
from {app_name}.tender.control.compliance.scoring import preference_system_for_value


def update_computed_fields(doc, method=None):
	"""validate hook: syncs the rule checklist and recomputes derived fields."""
	sync_compliance_checklist(doc)

	fatal_rows = [row for row in (doc.get("checklist") or []) if row.get("severity") == "Fatal"]
	open_fatal = [row for row in fatal_rows if row.get("status") != "Done"]
	doc.open_fatal_gates = len(open_fatal)
	doc.readiness_score = _weighted_done_pct(fatal_rows)
	doc.preference_system = preference_system_for_value(
		doc.get("estimated_value"), get_scoring_rule("SCORE-SYSTEM")
	)


def _weighted_done_pct(rows):
	"""Weighted done-percentage of the given rows; 100 when there are none."""
	total = sum(max(flt(row.get("weight")), 1.0) for row in rows)
	if not total:
		return 100.0
	done = sum(
		max(flt(row.get("weight")), 1.0) for row in rows if row.get("status") == "Done"
	)
	return round(done / total * 100.0, 2)
