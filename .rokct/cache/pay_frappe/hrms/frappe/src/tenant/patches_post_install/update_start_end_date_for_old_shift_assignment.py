# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt


import frappe


def execute():
	frappe.reload_doc("hr", "doctype", "shift_assignment")
	if frappe.db.has_column("Shift Assignment", "date"):
		# compliance-ignore: sql-injection (static bulk-update SQL in an offline migration patch; no interpolated input)
		frappe.db.sql(
			"""update `tabShift Assignment`
            set end_date=date, start_date=date
            where date IS NOT NULL and start_date IS NULL and end_date IS NULL;"""
		)
