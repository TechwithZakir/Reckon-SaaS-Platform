"""A signup's password passes Frappe's policy up front, and a registration never points at a
Company it did not create (runs without a database).
"""

from __future__ import annotations

import importlib
import sys
import unittest
from unittest.mock import Mock, patch

from frappe_stub import REPO_ROOT, FakeSettings, _Dict, plan_lookup, platform_modules

WEAK = {
    "score": 1,
    "feedback": {
        "password_policy_validation_passed": False,
        "warning": "This is a very common password.",
        "suggestions": ["All-uppercase is almost as easy to guess as all-lowercase."],
    },
}
STRONG = {"score": 4, "feedback": {"password_policy_validation_passed": True}}


def _create(saas, frappe, **extra):
    frappe.db.get_value.side_effect = plan_lookup()
    registration = Mock(flags=_Dict())
    frappe.get_doc.return_value.insert.return_value = registration
    saas.create_registration(
        business_name="Rahman Traders",
        owner_email="owner@example.com",
        owner_name="Rahman",
        plan="Plan",
        **extra,
    )
    return frappe.get_doc.call_args.args[0]


class PasswordPolicyAtSignupTests(unittest.TestCase):
    def test_weak_password_is_refused_before_anything_is_saved(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.settings = FakeSettings(require_email_verification=0)
            frappe.test_password_strength.return_value = WEAK
            with self.assertRaises(saas.SignupValidationError) as caught:
                _create(saas, frappe, owner_password="PASSWORD1", owner_password_confirm="PASSWORD1")
            frappe.get_doc.assert_not_called()
        message = str(caught.exception)
        self.assertIn("stronger password", message)
        self.assertIn("very common password", message)
        self.assertIn("All-uppercase", message)

    def test_policy_gets_the_same_inputs_as_frappe_user(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.settings = FakeSettings(require_email_verification=0)
            frappe.test_password_strength.return_value = STRONG
            values = _create(saas, frappe, owner_password="Kx9!river-lamp", owner_password_confirm="Kx9!river-lamp")
            args, kwargs = frappe.test_password_strength.call_args
        self.assertEqual(args[0], "Kx9!river-lamp")
        self.assertEqual(kwargs["user_data"], ("Rahman", None, None, "owner@example.com", None))
        self.assertEqual(values["owner_password"], "Kx9!river-lamp")

    def test_policy_off_accepts_any_long_enough_password(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.settings = FakeSettings(require_email_verification=0)
            values = _create(saas, frappe, owner_password="password", owner_password_confirm="password")
        self.assertEqual(values["owner_password"], "password")

    def test_provisioning_never_fails_on_the_policy_again(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.db.exists.return_value = False
            user = Mock(flags=_Dict())
            frappe.get_doc.return_value = user
            with patch.object(saas, "get_module_admin_role", return_value=None):
                saas._create_tenant_admin_user("o@example.com", "Owner", None, "accounts", password="Kx9!river-lamp")
        self.assertTrue(user.flags.ignore_password_policy)
        user.insert.assert_called_once()

    def test_link_flow_keeps_the_policy_for_the_welcome_link(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.db.exists.return_value = False
            user = Mock(flags=_Dict())
            frappe.get_doc.return_value = user
            with patch.object(saas, "get_module_admin_role", return_value=None):
                saas._create_tenant_admin_user("o@example.com", "Owner", None, "accounts")
        self.assertNotIn("ignore_password_policy", user.flags)


class NoBorrowedCompanyTests(unittest.TestCase):
    def test_new_registration_blanks_every_result_link(self):
        # Frappe's insert fills only fields that are None, so "" keeps the global
        # default Company off the registration.
        with platform_modules("saas") as (frappe, (saas,)):
            values = _create(saas, frappe)
        for field in ("company", "company_admin", "subscription", "payment", "provisioning_job"):
            with self.subTest(field=field):
                self.assertEqual(values[field], "")

    def test_failed_provisioning_unlinks_everything(self):
        with platform_modules("saas") as (frappe, (saas,)):
            doc = Mock()
            doc.name = "REG-00002"
            saas._mark_registration_failed(doc, Exception("boom"))
        values = doc.db_set.call_args.args[0]
        self.assertEqual(values["status"], "Failed")
        for field in ("company", "company_admin", "subscription", "payment", "provisioning_job"):
            with self.subTest(field=field):
                self.assertIsNone(values[field])


class RepairPatchTests(unittest.TestCase):
    def _run(self, rows):
        frappe = Mock()
        frappe.get_all.return_value = [_Dict(row) for row in rows]
        sys.path.insert(0, str(REPO_ROOT))
        try:
            with patch.dict(sys.modules, {"frappe": frappe}):
                sys.modules.pop("reckon_saas_platform.patches.clear_default_company_on_unprovisioned_registrations", None)
                patch_module = importlib.import_module(
                    "reckon_saas_platform.patches.clear_default_company_on_unprovisioned_registrations"
                )
                patch_module.execute()
        finally:
            sys.path.remove(str(REPO_ROOT))
            sys.modules.pop("reckon_saas_platform.patches.clear_default_company_on_unprovisioned_registrations", None)
        return frappe

    def test_unprovisioned_rows_lose_the_borrowed_company(self):
        frappe = self._run([{"name": "REG-00002", "company_admin": None}])
        filters = frappe.get_all.call_args.kwargs["filters"]
        self.assertNotIn("Pending Payment", filters["status"][1])
        self.assertNotIn("Active", filters["status"][1])
        frappe.db.set_value.assert_called_once()
        name, values = frappe.db.set_value.call_args.args[1:3]
        self.assertEqual(name, "REG-00002")
        self.assertIsNone(values["company"])

    def test_rows_with_an_admin_user_are_left_alone(self):
        frappe = self._run([{"name": "REG-00003", "company_admin": "owner@example.com"}])
        frappe.db.set_value.assert_not_called()

    def test_patch_is_registered(self):
        patches = (REPO_ROOT / "reckon_saas_platform/patches.txt").read_text(encoding="utf-8")
        self.assertIn("reckon_saas_platform.patches.clear_default_company_on_unprovisioned_registrations", patches)


if __name__ == "__main__":
    unittest.main()
