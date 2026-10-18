"""Database-free tests for running several SaaS modules on one site."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from frappe_stub import _Dict, platform_modules

DISTRIBUTION = {"key": "distribution", "admin_role": "Reckon Distribution Admin"}
ACCOUNTS = {"key": "accounts", "admin_role": "Reckon Accounts SaaS Admin"}


class CompanyModulesTests(unittest.TestCase):
    def test_company_modules_are_cached_and_invalidated(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.get_all.return_value = ["accounts", "distribution", "accounts"]
            self.assertEqual(saas.get_company_module_keys("Co"), ["accounts", "distribution"])
            frappe.get_all.return_value = []
            self.assertEqual(saas.get_company_module_keys("Co"), ["accounts", "distribution"])
            saas.invalidate_operational_access_cache("Co")
            self.assertEqual(saas.get_company_module_keys("Co"), [])

    def test_user_modules_union_their_companies(self):
        with platform_modules("saas") as (_frappe, (saas,)):
            with patch.object(saas, "get_user_companies", return_value=["A", "B"]), patch.object(
                saas, "get_company_module_keys", side_effect=lambda c: {"A": ["accounts"], "B": ["distribution"]}[c]
            ):
                self.assertEqual(saas.get_user_module_keys("u@example.com"), ["accounts", "distribution"])

    def test_no_company_means_no_modules(self):
        with platform_modules("saas") as (frappe, (saas,)):
            self.assertEqual(saas.get_company_module_keys(None), [])
            frappe.get_all.assert_not_called()


class ModuleAdminRoleTests(unittest.TestCase):
    def _role(self, saas_module, modules=(DISTRIBUTION, ACCOUNTS)):
        with platform_modules("saas") as (_frappe, (saas,)):
            with patch.object(
                saas, "get_module_definition",
                side_effect=lambda key: next((_Dict(m) for m in modules if m["key"] == key), None),
            ), patch.object(saas, "get_default_module", return_value=_Dict(modules[0]) if modules else None):
                return saas.get_module_admin_role(saas_module)

    def test_registration_module_decides_the_owner_role(self):
        self.assertEqual(self._role("accounts"), "Reckon Accounts SaaS Admin")
        self.assertEqual(self._role("distribution"), "Reckon Distribution Admin")

    def test_unknown_or_missing_module_falls_back_to_default(self):
        self.assertEqual(self._role(None), "Reckon Distribution Admin")
        self.assertEqual(self._role("crm"), "Reckon Distribution Admin")
        self.assertEqual(self._role(None, modules=()), "Reckon Distribution Admin")

    def test_admin_user_gets_the_module_role(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.db.exists.return_value = True
            frappe.get_doc.return_value = Mock()
            with patch.object(saas, "get_module_admin_role", return_value="Reckon Accounts SaaS Admin"):
                saas._create_tenant_admin_user("o@example.com", "Owner", None, "accounts")
            values = frappe.get_doc.call_args.args[0]
            self.assertEqual(values["roles"], [{"role": "Reckon Accounts SaaS Admin"}])


if __name__ == "__main__":
    unittest.main()
