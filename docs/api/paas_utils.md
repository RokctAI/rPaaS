# API Reference: utils

Source file: `paas/utils.py`

## Documented Module Functions

### `def check_subscription_feature(feature_module)`
Decorator to check if a feature is enabled in the subscription.
If rokct is installed, it delegates to rokct's checker.
If not, it allows the feature (standalone mode).

### `def get_subscription_details()`
Retrieves subscription details.
If rokct is installed, delegates to rokct.
If not, returns a default 'Active' subscription with all modules.
