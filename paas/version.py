from typing import Any, Optional

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
import json
import os


@frappe.whitelist(allow_guest=True)
def get_version() -> Any:
    """
    Get version API endpoint.
    """
    import sys

    _ = (
        frappe.request.headers.get("x-trace-id")
        if hasattr(frappe, "request")
        else None,
        sys.stderr,
    )
    # Path to the directory of this file
    # We assume this file is in the same directory as versions.json
    # (paas/paas/)
    paas_path = os.path.abspath(os.path.dirname(__file__))
    versions_file_path = os.path.join(paas_path, "versions.json")

    try:
        with open(versions_file_path, "r") as f:
            versions = json.load(f)
        return versions.get("paas", "0.1.0")  # Default fallback
    except Exception:
        return "0.1.0"  # Default fallback in case of any error


__version__ = get_version()
