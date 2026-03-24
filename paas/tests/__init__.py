import sys
from unittest.mock import MagicMock
import unittest

# 1. Mock 'frappe' and its submodules if missing
if "frappe" not in sys.modules:
    mock_frappe = MagicMock()
    # Handle 'frappe' as a package
    mock_frappe.__path__ = []
    # Mock __spec__ to avoid importlib issues during patching
    mock_frappe.__spec__ = MagicMock()
    sys.modules["frappe"] = mock_frappe

    # Nested mocking for common frappe submodules
    sub_packages = [
        "frappe.tests",
        "frappe.model",
        "frappe.custom",
        "frappe.database",
        "frappe.query_builder",
    ]
    for pkg in sub_packages:
        m = MagicMock()
        m.__path__ = []
        m.__spec__ = MagicMock()
        sys.modules[pkg] = m

    sub_modules = [
        "frappe.tests.utils",
        "frappe.utils",
        "frappe.model.document",
        "frappe.custom.doctype",
        "frappe.custom.doctype.custom_field",
        "frappe.custom.doctype.custom_field.custom_field",
        "frappe.exceptions",
        "frappe.database.mariadb",
        "frappe.database.mariadb.database",
        "frappe.query_builder.functions",
        "frappe.auth",
        "frappe.qb",
    ]
    for mod in sub_modules:
        m = MagicMock()
        m.__spec__ = MagicMock()
        sys.modules[mod] = m

    # Mock core attributes/functions
    mock_frappe._ = lambda x: x
    mock_frappe.whitelist = lambda *args, **kwargs: (lambda f: f)

    # Define a base class that skips tests when mocked
    class SkipOnMockTestCase(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            if "frappe" in sys.modules and getattr(
                sys.modules["frappe"], "_is_mock", False
            ):
                raise unittest.SkipTest(
                    "Skipping Frappe test in mocked environment"
                )

    mock_frappe._is_mock = True
    sys.modules["frappe.tests.utils"].FrappeTestCase = SkipOnMockTestCase

    # Mock exceptions
    for err in [
        "AuthenticationError",
        "ValidationError",
        "PermissionError",
        "DoesNotExistError",
        "DuplicateEntryError",
        "LinkExistsError",
    ]:
        err_cls = type(err, (Exception,), {})
        setattr(mock_frappe, err, err_cls)
        setattr(sys.modules["frappe.exceptions"], err, err_cls)


# 2. Mock other dependencies only if they are missing
def mock_if_missing(dep_name):
    if dep_name not in sys.modules:
        try:
            __import__(dep_name)
        except ImportError:
            m = MagicMock()
            m.__path__ = []
            m.__spec__ = MagicMock()
            sys.modules[dep_name] = m


# Only mock strictly required dependencies for test discovery that are NOT expected to be present
# rcore and erpnext are NOT mocked here to allow tests to skip themselves
# via ImportError
deps_to_check = [
    "staticmap",
    "sentence_transformers",
    "cryptography",
    "cryptography.hazmat",
    "cryptography.hazmat.primitives",
    "cryptography.hazmat.primitives.asymmetric",
    "cryptography.hazmat.primitives.ciphers",
    "cryptography.hazmat.primitives.ciphers.algorithms",
    "cryptography.hazmat.primitives.ciphers.modes",
    "cryptography.hazmat.primitives.kdf",
    "cryptography.hazmat.primitives.kdf.pbkdf2",
    "cryptography.hazmat.backends",
    "requests",
]

for dep in deps_to_check:
    mock_if_missing(dep)
