# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import unittest
from unittest.mock import MagicMock, patch
import {app_name}.utils as utils


class TestUtils(unittest.TestCase):
    def test_get_subscription_details_standalone(self):
        # Force HAS_CORE to False
        with patch('{app_name}.utils.HAS_CORE', False):
            details = utils.get_subscription_details()
            self.assertEqual(details['status'], 'Active')
            self.assertEqual(details['plan'], 'Standalone')
            self.assertEqual(details['modules'], ['all'])

    def test_get_subscription_details_core(self):
        # Force HAS_CORE to True and mock core_get_details
        with patch('{app_name}.utils.HAS_CORE', True):
            # We need to ensure core_get_details is mocked if it wasn't imported correctly
            # But since we mocked rcore in setup, it should be a MagicMock
            # However, utils.py imported it as `core_get_details`

            # Since {app_name}.utils is already imported, we patch the name in that
            # module
            with patch('{app_name}.utils.core_get_details') as mock_core:
                mock_core.return_value = {'status': 'Trialing'}
                details = utils.get_subscription_details()
                self.assertEqual(details['status'], 'Trialing')
                mock_core.assert_called_once()

    def test_check_subscription_feature_standalone(self):
        # Force HAS_CORE to False
        with patch('{app_name}.utils.HAS_CORE', False):
            @utils.check_subscription_feature("SomeFeature")
            def my_func(x):
                return x + 1

            # Should just call the function
            self.assertEqual(my_func(1), 2)

    def test_check_subscription_feature_core(self):
        # Force HAS_CORE to True
        with patch('{app_name}.utils.HAS_CORE', True):
            mock_dec = MagicMock()
            mock_core_check = MagicMock(return_value=mock_dec)

            with patch('{app_name}.utils.core_check_feature', mock_core_check):
                res = utils.check_subscription_feature("Feat")
                self.assertEqual(res, mock_dec)
                mock_core_check.assert_called_with("Feat")
