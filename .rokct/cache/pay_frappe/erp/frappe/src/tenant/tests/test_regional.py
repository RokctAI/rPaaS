import unittest

import frappe

from {app_name}.erp.tenant import erp_init as erpnext
from {app_name}.erp.tenant.tests.utils import ERPNextTestSuite


@erpnext.allow_regional
def test_method():
	return "original"


class TestInit(ERPNextTestSuite):
	def test_regional_overrides(self):
		frappe.flags.country = "Maldives"
		self.assertEqual(test_method(), "original")
