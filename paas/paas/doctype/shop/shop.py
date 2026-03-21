import frappe
from frappe.model.document import Document


class Shop(Document):
    def before_insert(self):
        if not self.shared_secret:
            self.shared_secret = frappe.generate_hash(length=32)
