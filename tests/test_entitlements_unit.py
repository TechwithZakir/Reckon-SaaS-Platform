"""Unit tests for module entitlements of a subscription."""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reckon_saas_platform"))

from entitlements import parse_covered_modules, subscription_covers  # noqa: E402


class EntitlementTests(unittest.TestCase):
    def test_primary_module_is_covered(self):
        self.assertTrue(subscription_covers("hrms", "hrms", None))

    def test_extra_module_is_covered(self):
        self.assertTrue(subscription_covers("crm", "hrms", "crm\nsales_agent\n"))

    def test_module_not_listed_is_not_covered(self):
        self.assertFalse(subscription_covers("distribution", "hrms", "crm"))

    def test_blank_and_whitespace_lines_ignored(self):
        self.assertEqual(parse_covered_modules("  crm \n\n  \nhrms"), {"crm", "hrms"})

    def test_no_module_key_is_never_covered(self):
        self.assertFalse(subscription_covers(None, "hrms", "crm"))


if __name__ == "__main__":
    unittest.main()
