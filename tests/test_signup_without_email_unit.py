"""Signup works with no outgoing Email Account and no email check (runs without a database).

With email verification off, or no Email Account to send from, nothing at signup or
provisioning may call ``frappe.sendmail``. Without an account Frappe raises "Please setup
default outgoing Email Account". The owner picks a password on the form instead.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from frappe_stub import FakeSettings, _Dict, plan_lookup, platform_modules

REPO_ROOT = Path(__file__).resolve().parents[1]
APP = REPO_ROOT / "reckon_saas_platform"


def _create(saas, frappe, **extra):
    frappe.db.get_value.side_effect = plan_lookup()
    registration = Mock(flags=_Dict())
    frappe.get_doc.return_value.insert.return_value = registration
    saas.create_registration(
        business_name="New Co", owner_email="owner@example.com", owner_name="Owner", plan="Plan", **extra
    )
    return registration, frappe.get_doc.call_args.args[0]


class EmailVerificationNeedsAnAccountTests(unittest.TestCase):
    def test_no_outgoing_account_skips_the_email_check(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.EmailAccount.find_outgoing.return_value = None
            self.assertFalse(saas.email_verification_required())
            registration, values = _create(saas, frappe, owner_password="s3cret-pass")
            saas.send_registration_verification(registration)
            frappe.sendmail.assert_not_called()
        self.assertEqual(values["email_verification_required"], 0)
        self.assertEqual(values["email_verified"], 1)
        self.assertEqual(values["owner_password"], "s3cret-pass")

    def test_muted_mail_counts_as_no_account(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.conf.mute_emails = 1
            self.assertFalse(saas.is_outgoing_email_configured())

    def test_lookup_errors_count_as_no_account(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.EmailAccount.find_outgoing.side_effect = Exception("no table")
            self.assertFalse(saas.is_outgoing_email_configured())

    def test_setting_on_and_account_present_still_requires_the_link(self):
        with platform_modules("saas") as (frappe, (saas,)):
            registration, values = _create(saas, frappe)
        self.assertEqual(values["email_verification_required"], 1)
        self.assertNotIn("owner_password", values)
        self.assertTrue(registration.flags.verification_token)


class OwnerPasswordTests(unittest.TestCase):
    def test_password_is_required_without_the_email_check(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.settings = FakeSettings(require_email_verification=0)
            for password in (None, "", "short"):
                with self.subTest(password=password), self.assertRaises(saas.SignupValidationError):
                    _create(saas, frappe, owner_password=password)

    def test_password_is_ignored_when_the_link_is_emailed(self):
        with platform_modules("saas") as (frappe, (saas,)):
            _registration, values = _create(saas, frappe, owner_password="s3cret-pass")
        self.assertNotIn("owner_password", values)

    def test_public_signup_passes_the_password_through(self):
        with platform_modules("saas") as (_frappe, (saas,)):
            registration = _Dict(
                name="REG-1",
                flags=_Dict(),
                email_verification_required=0,
                email_verified=1,
                phone_verification_required=0,
                phone_verified=0,
            )
            registration.db_set = Mock()
            with patch.object(saas, "verify_signup_captcha"), patch.object(
                saas, "create_registration", return_value=registration
            ) as create, patch.object(saas, "enqueue_registration_provisioning"):
                result = saas.public_signup(
                    business_name="New Co",
                    owner_email="owner@example.com",
                    owner_name="Owner",
                    plan="Plan",
                    owner_password="s3cret-pass",
                )
        self.assertEqual(create.call_args.kwargs["owner_password"], "s3cret-pass")
        self.assertIn("password", result["message"])


class OwnerUserTests(unittest.TestCase):
    def _user_values(self, frappe, saas, **kwargs):
        frappe.db.exists.return_value = False
        frappe.get_doc.return_value = Mock()
        with patch.object(saas, "get_module_admin_role", return_value=None):
            saas._create_tenant_admin_user("o@example.com", "Owner", None, "accounts", **kwargs)
        return frappe.get_doc.call_args.args[0]

    def test_chosen_password_is_set_and_no_welcome_email_is_sent(self):
        with platform_modules("saas") as (frappe, (saas,)):
            values = self._user_values(frappe, saas, password="s3cret-pass")
        self.assertEqual(values["new_password"], "s3cret-pass")
        self.assertEqual(values["send_welcome_email"], 0)

    def test_no_account_means_no_welcome_email(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.EmailAccount.find_outgoing.return_value = None
            values = self._user_values(frappe, saas)
        self.assertEqual(values["send_welcome_email"], 0)
        self.assertNotIn("new_password", values)

    def test_verified_email_still_gets_the_welcome_link(self):
        with platform_modules("saas") as (frappe, (saas,)):
            values = self._user_values(frappe, saas)
        self.assertEqual(values["send_welcome_email"], 1)

    def test_password_is_read_from_the_registration_and_then_forgotten(self):
        with platform_modules("saas") as (_frappe, (saas,)):
            doc = Mock(doctype="SaaS Registration")
            doc.name = "REG-1"
            doc.meta.has_field.return_value = True
            doc.get_password.return_value = "s3cret-pass"
            self.assertEqual(saas._registration_password(doc), "s3cret-pass")
            password_module = Mock()
            with patch.dict("sys.modules", {"frappe.utils.password": password_module}):
                saas._forget_registration_password(doc)
            password_module.remove_encrypted_password.assert_called_once_with(
                "SaaS Registration", "REG-1", "owner_password"
            )


class SignupPageTests(unittest.TestCase):
    def test_registration_keeps_the_password_encrypted_and_hidden(self):
        doctype = json.loads(
            (APP / "saas_platform/doctype/saas_registration/saas_registration.json").read_text("utf-8")
        )
        field = next(f for f in doctype["fields"] if f["fieldname"] == "owner_password")
        self.assertEqual(field["fieldtype"], "Password")
        self.assertEqual(field["hidden"], 1)
        self.assertIn("owner_password", doctype["field_order"])

    def test_form_asks_for_a_password_only_without_the_email_check(self):
        html = (APP / "www/reckonerp_signup.html").read_text(encoding="utf-8")
        block = html.split("{% if not email_required %}\n            <div class=\"rk-field\">", 1)[1]
        self.assertIn('name="owner_password"', block.split("{% endif %}", 1)[0])

    def test_both_languages_have_the_password_strings(self):
        with platform_modules("signup_i18n") as (_frappe, (i18n,)):
            for lang in i18n.LANGUAGES:
                strings = i18n.get_strings(lang)
                for key in ("password", "password_hint", "form_sub_phone", "form_sub_quick"):
                    with self.subTest(lang=lang, key=key):
                        self.assertTrue(strings[key])


if __name__ == "__main__":
    unittest.main()
