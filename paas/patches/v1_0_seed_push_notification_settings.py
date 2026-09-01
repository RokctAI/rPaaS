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

import frappe


def execute():
    if frappe.local.site == "juvo.tenant.rokct.ai":
        settings = frappe.get_single("Push Notification Settings")
        settings.api_key = frappe.conf.get("push_notification_api_key")
        settings.ios_api_key = frappe.conf.get("push_notification_ios_api_key")
        settings.android_api_key = frappe.conf.get("push_notification_android_api_key")
        settings.server_key = frappe.conf.get("push_notification_server_key")
        settings.vapid_key = frappe.conf.get("push_notification_vapid_key")
        settings.auth_domain = "juvofood.firebaseapp.com"
        settings.project_id = "juvofood"
        settings.storage_bucket = "juvofood.appspot.com"
        settings.messaging_sender_id = "728921419683"
        settings.app_id = "1:728921419683:web:81a97b726ba3fa120db416"
        settings.measurement_id = "G-PKYDE4B9DS"
        settings.save(ignore_permissions=True)
