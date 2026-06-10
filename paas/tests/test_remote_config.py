# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import unittest
from unittest.mock import MagicMock, patch
import frappe
from paas.api.remote_config import get_remote_config
from types import SimpleNamespace


class TestRemoteConfig(unittest.TestCase):
    def setUp(self):
        # Patching database and doc methods
        self.db_get_single_value_patcher = patch("frappe.db.get_single_value")
        self.db_get_value_patcher = patch("frappe.db.get_value")
        self.get_doc_patcher = patch("frappe.get_doc")

        self.mock_db_get_single_value = self.db_get_single_value_patcher.start()
        self.mock_db_get_value = self.db_get_value_patcher.start()
        self.mock_get_doc = self.get_doc_patcher.start()

        # Patch frappe.throw to raise Exception with the message
        self.throw_patcher = patch(
            "frappe.throw",
            side_effect=lambda msg, **kwargs: (_ for _ in ()).throw(Exception(msg)),
        )
        self.mock_throw = self.throw_patcher.start()

        # Ensure frappe.local is set up
        if not hasattr(frappe, "local"):
            frappe.local = MagicMock()
        frappe.local.site = "test_site"

    def tearDown(self):
        self.throw_patcher.stop()
        self.db_get_single_value_patcher.stop()
        self.db_get_value_patcher.stop()
        self.get_doc_patcher.stop()

    @patch("paas.api.remote_config.get_subscription_details")
    def test_get_remote_config_inactive_subscription(self, mock_get_sub):
        mock_get_sub.return_value = {"status": "Inactive"}

        with self.assertRaises(Exception) as cm:
            get_remote_config()
        self.assertIn("Could not verify subscription status", str(cm.exception))

    @patch("paas.api.remote_config.get_subscription_details")
    def test_get_remote_config_active_subscription(self, mock_get_sub):  # noqa: C901
        mock_get_sub.return_value = {"status": "Active"}

        # Mock Settings
        def get_single_value_side_effect(doctype, field):
            if doctype == "Settings":
                if field == "project_title":
                    return "My Project"
                if field == "enable_marketplace":
                    return 1
                if field == "default_shop":
                    return "Shop1"
            return None

        frappe.db.get_single_value.side_effect = get_single_value_side_effect

        # Mock Remote Config names
        def get_value_side_effect(doctype, filters, fieldname):
            if doctype == "Remote Config":
                if filters.get("app_type") == "Common":
                    return "RC-Common"
                if filters.get("app_type") == "Customer":
                    return "RC-Customer"
            return None

        frappe.db.get_value.side_effect = get_value_side_effect

        # Mock Remote Config Docs using SimpleNamespace to avoid MagicMock
        # auto-creation
        def get_doc_side_effect(doctype, name):
            if name == "RC-Common":
                return SimpleNamespace(
                    pin_loading_min=10,
                    pin_loading_max=20,
                    locale_code_en="en",
                    show_flag=0,
                )
            if name == "RC-Customer":
                return SimpleNamespace(
                    pin_loading_min=5,  # Overrides common
                    show_flag="",  # Should use common because empty string
                    country_code_iso="US",
                )
            return None

        frappe.get_doc.side_effect = get_doc_side_effect

        config = get_remote_config(app_type="Customer")

        self.assertEqual(config["projectTitle"], "My Project")
        self.assertEqual(config["enableMarketplace"], 1)

        # Verify Overrides
        # pinLoadingMin: Customer has 5, Common has 10. Should be 5.
        self.assertEqual(config["pinLoadingMin"], 5)

        # Verify Inheritance
        # pinLoadingMax: Customer None, Common 20. Should be 20.
        self.assertEqual(config["pinLoadingMax"], 20)

        # Verify Empty String Fallback
        # showFlag: Customer "", Common 0.
        # Logic: if app_config.show_flag ("") -> pass.
        # Fallback to common.show_flag (0) -> val = 0.
        self.assertEqual(config["showFlag"], 0)

        # Verify Unique to App
        self.assertEqual(config["countryCodeISO"], "US")

        # Verify Unique to Common
        self.assertEqual(config["localeCodeEn"], "en")
