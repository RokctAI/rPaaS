# API Reference: install

Source file: `paas/install.py`

## Documented Module Functions

### `def check_site_role()`
Checks the site role before PaaS installation.
PaaS can be installed on both tenant and control sites:
- Tenant sites: Full PaaS functionality with seeders
- Control sites: For Swagger documentation (no seeders)

### `def after_install()`
Wrapper to run all post-installation tasks.
