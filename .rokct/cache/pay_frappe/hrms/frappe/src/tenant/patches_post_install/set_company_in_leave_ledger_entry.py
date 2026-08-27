import frappe


def execute():
	frappe.reload_doc("HR", "doctype", "Leave Allocation")
	frappe.reload_doc("HR", "doctype", "Leave Ledger Entry")
	# compliance-ignore: sql-injection (static bulk-update SQL in an offline migration patch; no interpolated input)
	frappe.db.sql(
		"""
		UPDATE `tabLeave Ledger Entry` as lle
		SET company = (select company from `tabEmployee` where employee = lle.employee)
		WHERE company IS NULL
		"""
	)
	# compliance-ignore: sql-injection (static bulk-update SQL in an offline migration patch; no interpolated input)
	frappe.db.sql(
		"""
		UPDATE `tabLeave Allocation` as la
		SET company = (select company from `tabEmployee` where employee = la.employee)
		WHERE company IS NULL
		"""
	)
