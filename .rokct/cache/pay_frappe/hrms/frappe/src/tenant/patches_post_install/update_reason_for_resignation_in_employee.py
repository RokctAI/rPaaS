# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe


def execute():
	frappe.reload_doc("setup", "doctype", "employee")

	if frappe.db.has_column("Employee", "reason_for_resignation"):
		# compliance-ignore: sql-injection (static bulk-update SQL in an offline migration patch; no interpolated input)
		frappe.db.sql(
			""" UPDATE `tabEmployee`
            SET reason_for_leaving = reason_for_resignation
            WHERE status = 'Left' and reason_for_leaving is null and reason_for_resignation is not null
        """
		)
