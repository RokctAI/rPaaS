# API Reference: utils

Source file: `paas/builder/utils.py`

## Documented Module Functions

### `def prevent_uninstall_if_build_active()`
This function is called by the `on_uninstall` hook.
It prevents the app from being uninstalled if there are active builds.
