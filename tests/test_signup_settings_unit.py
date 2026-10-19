"""Database-free tests for signup settings: rate limits, optional email check, reCAPTCHA v3."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from frappe_stub import FakeSettings, _Dict, plan_lookup, platform_modules


def _response(json_data):
    response = Mock(status_code=200)
    response.json.return_value = json_data
    return response


class RateLimitSettingsTests(unittest.TestCase):
    def test_settings_win_over_site_config_and_default(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.conf.reckon_saas_signup_rate_limit = 9
            frappe.settings = FakeSettings(signup_rate_limit_per_hour=30, verify_rate_limit_per_hour=50)
            self.assertEqual(saas._signup_rate_limit(), 30)
            self.assertEqual(saas._verify_rate_limit(), 50)

    def test_zero_falls_back_to_site_config_then_default(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.settings = FakeSettings(signup_rate_limit_per_hour=0)
            frappe.conf.reckon_saas_signup_rate_limit = 9
            self.assertEqual(saas._signup_rate_limit(), 9)
            frappe.conf.reckon_saas_signup_rate_limit = None
            self.assertEqual(saas._signup_rate_limit(), saas.SIGNUP_RATE_LIMIT_PER_HOUR)
            self.assertEqual(saas._verify_rate_limit(), saas.VERIFY_RATE_LIMIT_PER_HOUR)

    def test_missing_settings_never_blocks_signup(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.get_cached_doc.side_effect = Exception("DocType SaaS Platform Settings not found")
            self.assertEqual(saas._signup_rate_limit(), saas.SIGNUP_RATE_LIMIT_PER_HOUR)

    def test_reset_clears_only_platform_counters_and_is_vendor_only(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.cache.store.update(
                {
                    "rl:reckon_saas_platform.saas.public_signup:203.0.113.5": 5,
                    "rl:reckon_saas_platform.saas.verify_registration_phone:203.0.113.5": 3,
                    "rl:frappe.core.doctype.user.user.reset_password:203.0.113.5": 2,
                }
            )
            with patch.object(saas, "is_vendor_user", return_value=False):
                with self.assertRaises(frappe.PermissionError):
                    saas.reset_signup_rate_limits()
            with patch.object(saas, "is_vendor_user", return_value=True):
                self.assertEqual(saas.reset_signup_rate_limits(), 2)
            self.assertEqual(
                list(frappe.cache.store), ["rl:frappe.core.doctype.user.user.reset_password:203.0.113.5"]
            )


class OptionalEmailVerificationTests(unittest.TestCase):
    def _create(self, saas, frappe):
        frappe.db.get_value.side_effect = plan_lookup()
        registration = Mock(flags=_Dict())
        frappe.get_doc.return_value.insert.return_value = registration
        saas.create_registration(
            business_name="New Co", owner_email="owner@example.com", owner_name="Owner", plan="Plan"
        )
        return registration, frappe.get_doc.call_args.args[0]

    def test_email_check_is_required_by_default(self):
        with platform_modules("saas") as (frappe, (saas,)):
            self.assertTrue(saas.email_verification_required())
            registration, values = self._create(saas, frappe)
        self.assertEqual(values["email_verification_required"], 1)
        self.assertEqual(values["email_verified"], 0)
        self.assertTrue(values["email_verification_hash"])
        self.assertTrue(registration.flags.verification_token)

    def test_email_check_switched_off_trusts_the_address(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.settings = FakeSettings(require_email_verification=0)
            registration, values = self._create(saas, frappe)
            self.assertEqual(values["email_verification_required"], 0)
            self.assertEqual(values["email_verified"], 1)
            self.assertIsNone(values["email_verification_hash"])
            self.assertIsNone(registration.flags.verification_token)
            saas.send_registration_verification(registration)
            frappe.sendmail.assert_not_called()

    def test_no_checks_at_all_starts_provisioning_immediately(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.settings = FakeSettings(require_email_verification=0)
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
            ), patch.object(saas, "enqueue_registration_provisioning") as enqueue:
                result = saas.public_signup(
                    business_name="New Co", owner_email="owner@example.com", owner_name="Owner", plan="Plan"
                )
            registration.db_set.assert_called_once_with("status", "Provisioning")
            enqueue.assert_called_once_with("REG-1")
        self.assertFalse(result["email_verification_required"])
        self.assertFalse(result["phone_verification_required"])

    def test_email_still_required_waits_for_the_link(self):
        with platform_modules("saas") as (_frappe, (saas,)):
            registration = _Dict(
                name="REG-1",
                flags=_Dict(),
                email_verification_required=1,
                email_verified=0,
                phone_verification_required=0,
                phone_verified=0,
            )
            registration.db_set = Mock()
            with patch.object(saas, "verify_signup_captcha"), patch.object(
                saas, "create_registration", return_value=registration
            ), patch.object(saas, "send_registration_verification"), patch.object(
                saas, "enqueue_registration_provisioning"
            ) as enqueue:
                saas.public_signup(
                    business_name="New Co", owner_email="owner@example.com", owner_name="Owner", plan="Plan"
                )
            enqueue.assert_not_called()


class RecaptchaV3Tests(unittest.TestCase):
    def _settings(self, **values):
        return FakeSettings(
            recaptcha_site_key="site-key",
            recaptcha_type="v3 Invisible",
            passwords={"recaptcha_secret_key": "captcha-secret"},
            **values,
        )

    def test_type_defaults_to_v2_checkbox(self):
        with platform_modules("recaptcha") as (frappe, (recaptcha,)):
            frappe.settings = FakeSettings()
            self.assertEqual(recaptcha.get_recaptcha_type(), "v2 Checkbox")
            frappe.settings = FakeSettings(recaptcha_type="something else")
            self.assertEqual(recaptcha.get_recaptcha_type(), "v2 Checkbox")

    def test_v3_accepts_human_scores_for_the_signup_action(self):
        with platform_modules("recaptcha") as (frappe, (recaptcha,)):
            frappe.settings = self._settings()
            frappe.requests.post.return_value = _response(
                {"success": True, "score": 0.9, "action": "signup"}
            )
            self.assertTrue(recaptcha.verify_recaptcha("tok"))

    def test_v3_refuses_low_scores_wrong_action_and_v2_tokens(self):
        cases = {
            "low score": {"success": True, "score": 0.3, "action": "signup"},
            "other action": {"success": True, "score": 0.9, "action": "login"},
            "v2 token": {"success": True},
            "boolean score": {"success": True, "score": True, "action": "signup"},
        }
        for label, data in cases.items():
            with self.subTest(label), platform_modules("recaptcha") as (frappe, (recaptcha,)):
                frappe.settings = self._settings()
                frappe.requests.post.return_value = _response(data)
                self.assertFalse(recaptcha.verify_recaptcha("tok"))

    def test_v3_minimum_score_is_configurable(self):
        with platform_modules("recaptcha") as (frappe, (recaptcha,)):
            frappe.settings = self._settings(recaptcha_min_score=0.2)
            frappe.requests.post.return_value = _response(
                {"success": True, "score": 0.3, "action": "signup"}
            )
            self.assertTrue(recaptcha.verify_recaptcha("tok"))


if __name__ == "__main__":
    unittest.main()
