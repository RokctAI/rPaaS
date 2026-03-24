import frappe
from functools import wraps

# Try to import from core, otherwise use fallback
try:
    from rcore.utils.subscription_checker import (
        check_subscription_feature as core_check_feature,
    )
    from rcore.tenant.api import get_subscription_details as core_get_details

    HAS_CORE = True
except ImportError:
    HAS_CORE = False

    def core_check_feature(feature_module):
        """Mock decorator that always allows the feature."""

        def decorator(fn):
            return fn

        return decorator

    def core_get_details():
        """Mock returning default active subscription."""
        return {
            "status": "Active",
            "plan": "Standalone",
            "modules": ["all"],
            "subscription_cache_duration": 86400,
        }


def check_subscription_feature(feature_module):
    """
    Decorator to check if a feature is enabled in the subscription.
    If rokct is installed, it delegates to rokct's checker.
    If not, it allows the feature (standalone mode).
    """
    if HAS_CORE:
        return core_check_feature(feature_module)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # In standalone mode, we assume all features are enabled
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def get_subscription_details():
    """
    Retrieves subscription details.
    If rokct is installed, delegates to rokct.
    If not, returns a default 'Active' subscription with all modules.
    """
    if HAS_CORE:
        return core_get_details()

    # Default fallback for standalone PaaS
    return {
        "status": "Active",
        "plan": "Standalone",
        "modules": ["all"],
        "subscription_cache_duration": 86400,
    }
