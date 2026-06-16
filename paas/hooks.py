app_name = "paas"
app_title = "PaaS"
app_publisher = "ROKCT INTELLIGENCE (PTY) LTD"
app_description = "PaaS App for Rokct"
app_email = "admin@rokct.ai"
app_license = "AGPL-3.0"

required_apps = ["erpnext"]

# Testing
# -------
before_tests = "paas.tests.utils.before_tests"

# Installation
# ------------
before_install = "paas.install.check_site_role"
after_install = "paas.install.after_install"
before_uninstall = ["paas.builder.utils.prevent_uninstall_if_build_active"]

# Authentication
# --------------
auth_hooks = []

    return events


scheduler_events = get_safe_scheduler_events()

# Whitelisted Methods
# -------------------
whitelisted_methods = {}

# Fixtures
# ---------
fixtures = []
]

# Website Route Rules
website_route_rules = [
    {
        "from_route": "/.well-known/assetlinks.json",
        "to_route": "paas.api.app_links.get_assetlinks",
    },
    {
        "from_route": "/.well-known/apple-app-site-association",
        "to_route": "paas.api.app_links.get_apple_app_site_association",
    },
]

# Document Events
# ---------------
doc_events = {}
