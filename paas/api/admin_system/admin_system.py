from typing import Any, Optional
import frappe
from frappe.utils import get_site_path, get_url
import os


@frappe.whitelist()
def get_system_info() -> Any:
    """
    Returns the system information from the System Information singleton.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    # Fetch the System Information document
    doc = frappe.get_single("System Information")

    # Trigger version fetch/update logic (onload usually runs on desk access, do we need to trigger it?)
    # Document.onload is not called by get_single automatically for API response usually,
    # but specific logic might be needed.
    # Our version fetching logic is in onload().
    # Let's manually trigger it to ensure fresh data if it's not persistent.
    if hasattr(doc, "onload"):
        doc.onload()

    return doc.as_dict()


@frappe.whitelist()
def get_backups() -> Any:
    """
    Returns the list of backups available for the current site.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Unauthorized")

    backups_path = get_site_path("private", "backups")
    if not os.path.exists(backups_path):
        return []

    backups = []
    for fname in os.listdir(backups_path):
        if fname.endswith(".sql.gz"):
            backups.append(
                {
                    "filename": fname,
                    "size": os.path.getsize(os.path.join(backups_path, fname)),
                    "path": f"/private/backups/{fname}",
                }
            )

    # Sort by filename (date prefix) desc
    backups.sort(key=lambda x: x["filename"], reverse=True)
    return backups


@frappe.whitelist()
def create_backup() -> Any:
    """
    Triggers a backup creation.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Unauthorized")

    # This usually requires background worker.
    # For simplicity, we might just enqueue it or allow it if system permits.
    # Frappe's backup capability is usually CLI driven or scheduled.
    # We can try to trigger it via enqueue.
    from frappe.integrations.utils import make_backup

    frappe.enqueue(make_backup, queue="long")
    return {"status": "success", "message": "Backup started in background."}


@frappe.whitelist()
def clear_system_cache() -> Any:
    """
    Clears the system cache.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Unauthorized")

    frappe.clear_cache()
    return {"status": "success", "message": "Cache cleared."}
