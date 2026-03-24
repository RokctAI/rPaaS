import frappe


@frappe.whitelist(allow_guest=True)
def get_assetlinks():
    frappe.response["type"] = "json"
    try:
        config = frappe.get_single("Flutter App Configuration")
        package_name = config.package_name
        fingerprints = (
            config.sha256_fingerprint.splitlines()
            if config.sha256_fingerprint
            else []
        )

        # Clean up fingerprints (remove empty lines or whitespace)
        fingerprints = [f.strip() for f in fingerprints if f.strip()]

        if not package_name:
            return []

        return [
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": package_name,
                    "sha256_cert_fingerprints": fingerprints,
                },
            }
        ]
    except Exception:
        frappe.log_error("Error generating assetlinks.json")
        return []


@frappe.whitelist(allow_guest=True)
def get_apple_app_site_association():
    frappe.response["type"] = "json"
    try:
        config = frappe.get_single("Flutter App Configuration")
        team_id = config.apple_team_id
        bundle_id = config.ios_package_name

        if not team_id or not bundle_id:
            return {}

        app_id = f"{team_id}.{bundle_id}"

        return {
            "applinks": {
                "apps": [],
                "details": [{"appID": app_id, "paths": ["*"]}],
            }
        }
    except Exception:
        frappe.log_error("Error generating apple-app-site-association")
        return {}
