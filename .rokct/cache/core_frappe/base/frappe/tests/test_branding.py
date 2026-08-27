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

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import unittest
from unittest.mock import MagicMock, patch
import frappe
from {app_name}.branding import get_paas_branding, get_paas_brand_html


class TestBranding(unittest.TestCase):
    def setUp(self):
        # Patching methods
        self.db_get_value_patcher = patch('frappe.db.get_value')
        self.get_doc_patcher = patch('frappe.get_doc')
        self.get_single_patcher = patch('frappe.get_single')

        self.mock_db_get_value = self.db_get_value_patcher.start()
        self.mock_get_doc = self.get_doc_patcher.start()
        self.mock_get_single = self.get_single_patcher.start()

        # Ensure defaults mock is set up
        if not hasattr(frappe, 'defaults'):
            frappe.defaults = MagicMock()
        frappe.defaults.get_user_default = MagicMock(
            return_value="Test Company")

    def tearDown(self):
        self.db_get_value_patcher.stop()
        self.get_doc_patcher.stop()
        self.get_single_patcher.stop()

    def test_get_paas_branding_no_subscription(self):
        # Mock no subscription found
        frappe.db.get_value.return_value = None

        result = get_paas_branding()
        self.assertEqual(result, {'enabled': False})

    def test_get_paas_branding_no_paas_module(self):
        # Mock subscription found but no PaaS module
        frappe.db.get_value.return_value = MagicMock(
            subscription_plan='Basic Plan')

        mock_plan = MagicMock()
        mock_plan.modules = [MagicMock(module_name='Other')]
        frappe.get_doc.return_value = mock_plan

        result = get_paas_branding()
        self.assertEqual(result, {'enabled': False})

    def test_get_paas_branding_enabled_defaults(self):
        # Mock subscription with PaaS module
        frappe.db.get_value.return_value = MagicMock(
            subscription_plan='Pro Plan')

        mock_plan = MagicMock()
        mock_plan.modules = [MagicMock(module_name='PaaS')]
        frappe.get_doc.return_value = mock_plan

        # Mock Settings (empty/defaults)
        mock_settings = MagicMock()
        mock_settings.logo = None
        mock_settings.favicon = None
        mock_settings.project_title = None
        frappe.get_single.return_value = mock_settings

        result = get_paas_branding()
        self.assertEqual(result['enabled'], True)
        self.assertEqual(result['logo'], '/assets/rokct/images/logo.svg')
        self.assertEqual(result['app_name'], 'ROKCT')

    def test_get_paas_branding_enabled_custom(self):
        # Mock subscription with PaaS module
        frappe.db.get_value.return_value = MagicMock(
            subscription_plan='Pro Plan')

        mock_plan = MagicMock()
        mock_plan.modules = [MagicMock(module_name='PaaS')]
        frappe.get_doc.return_value = mock_plan

        # Mock Settings with values
        mock_settings = MagicMock()
        mock_settings.logo = '/files/my_logo.png'
        mock_settings.favicon = '/files/my_favicon.ico'
        mock_settings.project_title = 'My App'
        frappe.get_single.return_value = mock_settings

        result = get_paas_branding()
        self.assertEqual(result['enabled'], True)
        self.assertEqual(result['logo'], '/files/my_logo.png')
        self.assertEqual(result['app_name'], 'My App')

    def test_get_paas_brand_html_disabled(self):
        # Mock get_paas_branding returning disabled
        with patch('{app_name}.branding.get_paas_branding') as mock_get_branding:
            mock_get_branding.return_value = {'enabled': False}
            result = get_paas_brand_html()
            self.assertEqual(result, "")

    def test_get_paas_brand_html_enabled(self):
        # Mock get_paas_branding returning enabled
        with patch('{app_name}.branding.get_paas_branding') as mock_get_branding:
            mock_get_branding.return_value = {
                'enabled': True,
                'logo': '/logo.png',
                'app_name': 'Test App'
            }
            result = get_paas_brand_html()
            self.assertIn("frappe.ready(function()", result)
            self.assertIn("/logo.png", result)
            self.assertIn("Test App", result)
