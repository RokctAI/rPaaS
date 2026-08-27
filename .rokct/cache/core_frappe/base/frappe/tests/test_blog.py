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

import frappe
from frappe.utils import now_datetime
from frappe.tests.utils import FrappeTestCase
from {app_name}.api.blog.blog import create_blog, get_blogs


class TestBlog(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_blog_crud(self):
        # 1. Create Blog
        data = {
            "title": "Welcome to PaaS",
            "description": "This is the first post.",
            "type": "blog",
            "published_at": now_datetime()
        }
        blog = create_blog(data)
        self.assertEqual(blog["data"]["title"], "Welcome to PaaS")

        # 2. Get Blogs
        blogs = get_blogs(type="blog")
        self.assertTrue(len(blogs["data"]) > 0)
        self.assertEqual(blogs["data"][0]["title"], "Welcome to PaaS")
