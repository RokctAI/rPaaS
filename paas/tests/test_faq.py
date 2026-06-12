# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.faq.faq import create_faq, get_faqs


class TestFAQ(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_faq_crud(self):
        # 1. Create FAQ
        data = {
            "question": "How do I order?",
            "answer": "Just click the button.",
            "type": "web",
        }
        faq = create_faq(data)
        self.assertEqual(faq.question, "How do I order?")

        # 2. Get FAQs
        faqs = get_faqs(type="web")
        self.assertTrue(len(faqs) > 0)
        self.assertEqual(faqs[0].question, "How do I order?")
