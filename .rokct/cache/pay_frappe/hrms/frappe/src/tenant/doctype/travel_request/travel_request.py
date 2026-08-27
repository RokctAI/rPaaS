# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document

from {app_name}.hrms.tenant.hr.utils import validate_active_employee


class TravelRequest(Document):
	def validate(self):
		validate_active_employee(self.employee)
