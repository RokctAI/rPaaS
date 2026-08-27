# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe

page_title = "Partners"


def get_context(context):
	# compliance-ignore: sql-injection (static query, no interpolated input)
	partners = frappe.db.sql(
		"""select * from `tabSales Partner`
			where show_in_website=1 order by name asc""",
		as_dict=True,
	)

	return {"partners": partners, "title": page_title}
