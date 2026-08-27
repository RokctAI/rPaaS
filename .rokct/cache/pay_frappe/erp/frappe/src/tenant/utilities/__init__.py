## temp utility

from contextlib import contextmanager
from importlib.util import find_spec

import frappe
from frappe import _
from frappe.utils import cstr

from {app_name}.erp.tenant.utilities.activation import get_level


def update_doctypes():
	for d in frappe.db.sql(
		"""select df.parent, df.fieldname
		from tabDocField df, tabDocType dt where df.fieldname
		like "%description%" and df.parent = dt.name and dt.istable = 1""",
		as_dict=1,
	):
		dt = frappe.get_doc("DocType", d.parent)

		for f in dt.fields:
			if f.fieldname == d.fieldname and f.fieldtype in ("Text", "Small Text"):
				f.fieldtype = "Text Editor"
				dt.save()
				break


def get_site_info(site_info):
	# called via hook
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	domain = None

	if not company:
		company = frappe.db.sql("select name from `tabCompany` order by creation asc")
		company = company[0][0] if company else None

	if company:
		domain = frappe.get_cached_value("Company", cstr(company), "domain")

	return {"company": company, "domain": domain, "activation": get_level(site_info)}


def gateways_module_available():
	"""True when the composed `gateways` module (pay SDK's frappe/payments
	port) is part of this app. Replaces upstream's check for the separate
	`payments` app (ROKCT self-containment remap)."""
	try:
		return find_spec("{app_name}.gateways") is not None
	except (ImportError, ValueError):
		return False


@contextmanager
def payment_app_import_guard():
	msg = _(
		"The gateways module (pay SDK's frappe/payments port) is not part of this app. "
		"Compose the gateways module alongside erp to enable payment gateway features."
	)

	if not gateways_module_available():
		frappe.throw(msg, title=_("Missing gateways Module"), exc=frappe.AppNotInstalledError)

	try:
		yield
	except ImportError:
		frappe.throw(msg, title=_("Missing gateways Module"), exc=frappe.AppNotInstalledError)
