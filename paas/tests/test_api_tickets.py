# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from paas.api.user.user import (
    create_ticket,
    get_user_tickets,
    get_user_ticket,
    reply_to_ticket,
)
import uuid


class TestTicketsAPI(FrappeTestCase):
    def setUp(self):
        # Create a test user
        if not frappe.db.exists("User", "test_tickets@example.com"):
            self.test_user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_tickets@example.com",
                    "first_name": "Test",
                    "last_name": "Tickets",
                    "send_welcome_email": 0,
                }
            ).insert(ignore_permissions=True)
            self.test_user.add_roles("System Manager")
        else:
            self.test_user = frappe.get_doc("User", "test_tickets@example.com")

        # Log in as the test user
        frappe.set_user(self.test_user.name)

    def tearDown(self):
        # Log out
        frappe.set_user("Administrator")

    def test_create_and_get_ticket(self):
        ticket = create_ticket(subject="Test Subject", content="Test Content")
        self.assertEqual(ticket.get("subject"), "Test Subject")
        self.assertEqual(ticket.get("created_by_user"), self.test_user.name)

        # Test get list
        tickets = get_user_tickets()
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0].get("subject"), "Test Subject")

        # Test get single
        retrieved_ticket = get_user_ticket(name=ticket.get("name"))
        self.assertEqual(retrieved_ticket.get("subject"), "Test Subject")
        self.assertTrue("replies" in retrieved_ticket)
        self.assertEqual(len(retrieved_ticket.get("replies")), 0)

    def test_reply_to_ticket(self):
        ticket = create_ticket(subject="Test Reply", content="Original message")

        reply = reply_to_ticket(name=ticket.get("name"), content="This is a reply")
        self.assertEqual(reply.get("parent_ticket"), ticket.get("name"))
        self.assertEqual(reply.get("content"), "This is a reply")

        # Check that the parent ticket status was updated
        parent_ticket = frappe.get_doc("Ticket", ticket.get("name"))
        self.assertEqual(parent_ticket.status, "Answered")

        # Check that the reply shows up in the get_user_ticket response
        full_ticket = get_user_ticket(name=ticket.get("name"))
        self.assertEqual(len(full_ticket.get("replies")), 1)
        self.assertEqual(
            full_ticket.get("replies")[0].get("content"), "This is a reply"
        )
