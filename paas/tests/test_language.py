# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.language.language import (
    get_languages,
    get_default_language,
    get_translations,
)


class TestLanguage(FrappeTestCase):
    def setUp(self):
        # Create a test language
        if not frappe.db.exists("PaaS Language", "en"):
            frappe.get_doc(
                {
                    "doctype": "PaaS Language",
                    "title": "English",
                    "locale": "en",
                    "default": 1,
                    "active": 1,
                }
            ).insert()

        # Create a test translation
        if not frappe.db.exists("PaaS Translation", {"key": "hello", "locale": "en"}):
            frappe.get_doc(
                {
                    "doctype": "PaaS Translation",
                    "locale": "en",
                    "group": "messages",
                    "key": "hello",
                    "value": "Hello World",
                    "status": 1,
                }
            ).insert()

    def tearDown(self):
        frappe.db.rollback()

    def test_get_languages(self):
        langs = get_languages()
        self.assertTrue(len(langs) > 0)
        self.assertEqual(langs[0].locale, "en")

    def test_get_default_language(self):
        lang = get_default_language()
        self.assertEqual(lang["locale"], "en")

    def test_get_translations(self):
        # Test with group
        trans = get_translations("en", group="messages")
        self.assertEqual(trans["hello"], "Hello World")

        # Test without group (nested)
        trans_all = get_translations("en")
        self.assertEqual(trans_all["messages"]["hello"], "Hello World")
