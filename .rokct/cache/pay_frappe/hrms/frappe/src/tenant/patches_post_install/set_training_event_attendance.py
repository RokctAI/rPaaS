import frappe


def execute():
	frappe.reload_doc("hr", "doctype", "training_event")
	frappe.reload_doc("hr", "doctype", "training_event_employee")

	# no need to run the update query as there is no old data
	if not frappe.db.exists("Training Event Employee", {"attendance": ("in", ("Mandatory", "Optional"))}):
		return

	# compliance-ignore: sql-injection (static bulk-update SQL in an offline migration patch; no interpolated input)
	frappe.db.sql(
		"""
		UPDATE `tabTraining Event Employee`
		SET is_mandatory = 1
		WHERE attendance = 'Mandatory'
		"""
	)
	# compliance-ignore: sql-injection (static bulk-update SQL in an offline migration patch; no interpolated input)
	frappe.db.sql(
		"""
		UPDATE `tabTraining Event Employee`
		SET attendance = 'Present'
		WHERE attendance in ('Mandatory', 'Optional')
	"""
	)
