# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime
from frappe.tests.utils import FrappeTestCase
from paas.api.blog.blog import create_blog, get_blogs


class TestBlog(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_blog_crud(self):
        # 1. Create Blog
        data = {
            "title": "Welcome to PaaS",
            "description": "This is the first post.",
            "type": "blog",
            "published_at": now_datetime(),
        }
        blog = create_blog(data)
        self.assertEqual(blog["data"]["title"], "Welcome to PaaS")

        # 2. Get Blogs
        blogs = get_blogs(type="blog")
        self.assertTrue(len(blogs["data"]) > 0)
        self.assertEqual(blogs["data"][0]["title"], "Welcome to PaaS")
