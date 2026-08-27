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

from typing import Any, Optional
# Copyright (c) 2025, ROKCT and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from ..utils import get_whatsapp_config


@frappe.whitelist()
def create_flow() -> Any:
    """
    Automates the creation of the 'Product Customizer' flow on Meta.
    """
    config = frappe.get_single("WhatsApp Tenant Config")
    if not config.access_token or not config.waba_id:
        frappe.throw("Please ensure Access Token and WABA ID are saved first.")

    api_version = "v21.0"
    base_url = f"https://graph.facebook.com/{api_version}"
    headers = {
        "Authorization": f"Bearer {config.access_token}",
        "Content-Type": "application/json"
    }

    # 1. Create Flow Container
    # Name must be unique per WABA? Ideally yes.
    flow_name = f"Rokct Customizer {frappe.utils.random_string(4)}"
    create_url = f"{base_url}/{config.waba_id}/flows"
    payload = {
        "name": flow_name,
        "categories": ["SHOPPING"]
    }

    try:
        resp = requests.post(create_url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        flow_id = resp.json().get("id")
    except Exception as e:
        frappe.log_error(
            f"Flow Creation Failed: {str(e)} -> {resp.text if 'resp' in locals() else ''}")
        frappe.throw(f"Failed to create Flow container: {str(e)}")

    # 2. Upload Layout (flow.json)
    # We define a standard layout that consumes our Data Endpoint
    layout = get_generic_flow_layout()
    asset_url = f"{base_url}/{flow_id}/assets"
    payload = {
        "name": "flow.json",
        "asset_type": "FLOW_JSON",
        # Meta expects it as a file upload usually? Or JSON body?
        "file": json.dumps(layout)
        # Graph API v18+ for Flows allows JSON body for updates?
        # Actually documentation says 'file' parameter with multipart/form-data usually?
        # Let's check typical usage.
        # API: POST /{flow_id}/assets
    }

    # Python requests for multipart
    files = {
        'file': ('flow.json', json.dumps(layout), 'application/json')
    }
    data = {
        'name': 'flow.json',
        'asset_type': 'FLOW_JSON'
    }
    # Remove Content-Type header for multipart to let requests set boundary
    headers_multipart = {"Authorization": f"Bearer {config.access_token}"}

    try:
        resp = requests.post(
            asset_url,
            headers=headers_multipart,
            data=data,
            files=files,
            timeout=10)
        resp.raise_for_status()
    except Exception as e:
        frappe.log_error(
            f"Flow Asset Upload Failed: {str(e)} -> {resp.text if 'resp' in locals() else ''}")
        frappe.throw(f"Failed to upload Flow JSON: {str(e)}")

    # 3. Publish Flow
    publish_url = f"{base_url}/{flow_id}/publish"
    try:
        resp = requests.post(publish_url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        frappe.log_error(
            f"Flow Publish Failed: {str(e)} -> {resp.text if 'resp' in locals() else ''}")
        # We warn but don't stop, saving the ID is useful
        frappe.msgprint(
            "Flow created but failed to publish. Check Meta Business Manager.")

    # 4. Save ID
    config.flow_id = flow_id
    config.save(ignore_permissions=True)

    endpoint_url = frappe.utils.get_url(
        "/api/v1/method/paas.api.whatsapp_flow_endpoint")
    msg = f"Flow '{flow_name}' created! ID: {flow_id}. <br><b>IMPORTANT:</b> Go to Meta Business Manager -> Flows -> {flow_name} -> Endpoint and paste this URL:<br><b>{endpoint_url}</b>"

    return {"status": "success", "flow_id": flow_id, "message": msg}


def get_generic_flow_layout():
    """
    Returns the JSON structure for a dynamic Product Customizer flow.
    """
    return {
        "version": "3.0",
        "screens": [
            {
                "id": "screen_0",
                "title": "Customize Product",
                "data": {
                    "product_name": {
                        "type": "string",
                        "__example__": "Burger"
                    },
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"}
                            }
                        },
                        "__example__": [
                            {"id": "c1", "title": "Cheese"}
                        ]
                    }
                },
                "terminal": True,  # Or link to success screen
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Text",
                            "text": "Customize ${data.product_name}"
                        },
                        {
                            "type": "CheckboxGroup",
                            "name": "selected_options",
                            "label": "Select Options",
                            "data-source": "${data.options}"
                        },
                        {
                            "type": "Footer",
                            "label": "Add to Cart",
                            "on-click-action": {
                                "name": "complete",
                                "payload": {
                                    # Pass context back
                                    "original_product": "${data.product_name}",
                                    "options": "${form.selected_options}"
                                }
                            }
                        }
                    ]
                }
            }
        ]
    }
