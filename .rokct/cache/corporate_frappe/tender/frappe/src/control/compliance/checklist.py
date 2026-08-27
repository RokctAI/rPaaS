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

"""Checklist generation from compliance rules (idempotent, additive).

Applicable rules with a ``checklist_text`` each guarantee one row on the
bid's checklist, keyed by ``rule_code``. Rows a user already has are never
touched or removed - resyncing after a rule/fixture update only appends the
newly applicable rows, so rule updates change future and open checklists
with zero code changes.
"""

# Same-package import (F-09): the relative import works on a composed bench;
# the importlib fallback keeps this module importable standalone by file path,
# matching the proven pack_builder.py pattern. Zero behaviour change composed.
try:
	from .rules import get_applicable_rules
except ImportError:  # standalone by-path import - load the sibling directly
	import importlib.util as _importlib_util
	import os as _os

	_spec = _importlib_util.spec_from_file_location(
		"tender_checklist_rules",
		_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "rules.py"),
	)
	_module = _importlib_util.module_from_spec(_spec)
	_spec.loader.exec_module(_module)
	get_applicable_rules = _module.get_applicable_rules


def compliance_checklist_rows(bid):
	"""Checklist row dicts for every applicable rule with checklist text."""
	rows = []
	for rule in get_applicable_rules(bid):
		if not rule.get("checklist_text"):
			continue
		rows.append(
			{
				"task_text": rule["checklist_text"],
				"weight": 0,
				"severity": rule.get("severity"),
				"rule_code": rule.get("rule_code"),
				"status": "Open",
			}
		)
	return rows


def sync_compliance_checklist(bid):
	"""Appends missing rule-generated rows to a Tender Bid's checklist.

	Idempotent by rule_code; returns the number of rows appended. Called from
	claim_tender seeding and the Tender Bid validate doc-event, so a bid picks
	up newly applicable rules when its regime or estimated value changes.
	"""
	existing_codes = {row.rule_code for row in (bid.get("checklist") or []) if row.get("rule_code")}
	appended = 0
	for row in compliance_checklist_rows(bid):
		if row["rule_code"] in existing_codes:
			continue
		bid.append("checklist", row)
		appended += 1
	return appended
