"""Unit tests for per-company tenant role names."""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reckon_saas_platform"))

from tenant_roles import role_kind_for_profile, tenant_role_name  # noqa: E402


class TenantRoleNameTests(unittest.TestCase):
    def test_name_per_company(self):
        self.assertEqual(tenant_role_name("Reckon CRM", "User", "Acme Ltd"), "Reckon CRM User - Acme Ltd")
        self.assertNotEqual(tenant_role_name("Reckon CRM", "User", "A"), tenant_role_name("Reckon CRM", "User", "B"))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            tenant_role_name("Reckon CRM", "Manager", "Acme")

    def test_missing_parts_rejected(self):
        with self.assertRaises(ValueError):
            tenant_role_name("", "Admin", "Acme")

    def test_length_capped(self):
        self.assertLessEqual(len(tenant_role_name("Reckon HRMS", "Admin", "x" * 300)), 140)

    def test_profile_mapping(self):
        self.assertEqual(role_kind_for_profile("Company Admin"), "Admin")
        self.assertEqual(role_kind_for_profile("Company Manager"), "User")
        self.assertEqual(role_kind_for_profile(None), "User")


if __name__ == "__main__":
    unittest.main()
