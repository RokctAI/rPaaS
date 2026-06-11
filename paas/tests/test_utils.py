# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import unittest
from unittest.mock import MagicMock, patch
import paas.utils as utils


class TestUtils(unittest.TestCase):
    def test_get_subscription_details_standalone(self):
        # Force HAS_CORE to False
        with patch("paas.utils.HAS_CORE", False):
            details = utils.get_subscription_details()
            self.assertEqual(details["status"], "Active")
            self.assertEqual(details["plan"], "Standalone")
            self.assertEqual(details["modules"], ["all"])

    def test_get_subscription_details_core(self):
        # Force HAS_CORE to True and mock core_get_details
        with patch("paas.utils.HAS_CORE", True):
            # We need to ensure core_get_details is mocked if it wasn't imported correctly
            # But since we mocked rcore in setup, it should be a MagicMock
            # However, utils.py imported it as `core_get_details`

            # Since paas.utils is already imported, we patch the name in that
            # module
            with patch("paas.utils.core_get_details") as mock_core:
                mock_core.return_value = {"status": "Trialing"}
                details = utils.get_subscription_details()
                self.assertEqual(details["status"], "Trialing")
                mock_core.assert_called_once()

    def test_check_subscription_feature_standalone(self):
        # Force HAS_CORE to False
        with patch("paas.utils.HAS_CORE", False):

            @utils.check_subscription_feature("SomeFeature")
            def my_func(x):
                return x + 1

            # Should just call the function
            self.assertEqual(my_func(1), 2)

    def test_check_subscription_feature_core(self):
        # Force HAS_CORE to True
        with patch("paas.utils.HAS_CORE", True):
            mock_dec = MagicMock()
            mock_core_check = MagicMock(return_value=mock_dec)

            with patch("paas.utils.core_check_feature", mock_core_check):
                res = utils.check_subscription_feature("Feat")
                self.assertEqual(res, mock_dec)
                mock_core_check.assert_called_with("Feat")
