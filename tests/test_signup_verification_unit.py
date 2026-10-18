"""Database-free tests for SMS (BulkSMSBD) OTP, Google reCAPTCHA and vendor retry."""

from __future__ import annotations

import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from frappe_stub import FakeSettings, _Dict, plan_lookup, platform_modules

NOW = datetime(2026, 10, 18, 12, 0, 0)


class FakeDoc(_Dict):
    def db_set(self, field, value=None, **kwargs):
        if isinstance(field, dict):
            self.update(field)
        else:
            self[field] = value


def _response(status=200, json_data=None, text=""):
    response = Mock(status_code=status, text=text)
    if json_data is None:
        response.json.side_effect = ValueError("not json")
    else:
        response.json.return_value = json_data
    return response


def configured_settings(**values):
    return FakeSettings(
        require_phone_verification=1,
        bulksmsbd_sender_id="8809617600000",
        recaptcha_site_key="site-key",
        passwords={"bulksmsbd_api_key": "sms-secret", "recaptcha_secret_key": "captcha-secret"},
        **values,
    )


@contextmanager
def saas_with_clock(settings=None):
    with platform_modules("saas", "sms", "recaptcha") as (frappe, (saas, sms, recaptcha)):
        if settings is not None:
            frappe.settings = settings
        with patch.object(saas, "now_datetime", return_value=NOW), patch.object(
            saas, "add_to_date", side_effect=lambda value, **delta: value + timedelta(**delta)
        ), patch.object(saas, "get_datetime", side_effect=lambda value: value):
            yield frappe, saas, sms, recaptcha


class MobileNumberTests(unittest.TestCase):
    def test_normalizes_bangladesh_mobile_formats(self):
        with platform_modules("sms") as (_frappe, (sms,)):
            for raw in ("01712345678", "+8801712345678", "8801712345678", "1712345678",
                        "017-1234-5678", "0088 01712345678"):
                with self.subTest(raw=raw):
                    self.assertEqual(sms.normalize_bd_mobile(raw), "8801712345678")
            for raw in ("01212345678", "0171234567", "phone", "", None, ["01712345678"], "+1 415 555 0100"):
                with self.subTest(raw=raw):
                    self.assertIsNone(sms.normalize_bd_mobile(raw))


class BulkSMSBDTests(unittest.TestCase):
    def test_sends_with_documented_parameters(self):
        with platform_modules("sms") as (frappe, (sms,)):
            frappe.settings = configured_settings()
            frappe.requests.post.return_value = _response(
                json_data={"response_code": 202, "message_id": 77, "success_message": "SMS Submitted Successfully"}
            )
            self.assertEqual(sms.send_sms("8801712345678", "code 123456"), 77)
            args, kwargs = frappe.requests.post.call_args
            self.assertEqual(args[0], "https://bulksmsbd.net/api/smsapi")
            self.assertEqual(
                kwargs["data"],
                {"api_key": "sms-secret", "senderid": "8809617600000", "number": "8801712345678", "message": "code 123456"},
            )
            self.assertTrue(kwargs["timeout"])

    def test_plain_text_202_is_success(self):
        with platform_modules("sms") as (frappe, (sms,)):
            frappe.settings = configured_settings()
            frappe.requests.post.return_value = _response(text="202")
            sms.send_sms("8801712345678", "hi")

    def test_gateway_error_raises_and_logs_without_secrets(self):
        with platform_modules("sms") as (frappe, (sms,)):
            frappe.settings = configured_settings()
            frappe.requests.post.return_value = _response(json_data={"response_code": 1007, "error_message": "x"})
            with self.assertRaises(sms.SMSDeliveryError) as raised:
                sms.send_sms("8801712345678", "hi")
            self.assertEqual(raised.exception.http_status_code, 502)
            logged = frappe.log_error.call_args.kwargs["message"]
            self.assertIn("1007", logged)
            self.assertIn("Insufficient balance", logged)
            self.assertNotIn("sms-secret", logged)
            self.assertNotIn("8801712345678", logged)

    def test_network_error_raises_delivery_error(self):
        with platform_modules("sms") as (frappe, (sms,)):
            frappe.settings = configured_settings()
            frappe.requests.post.side_effect = frappe.requests.RequestException("timeout")
            with self.assertRaises(sms.SMSDeliveryError):
                sms.send_sms("8801712345678", "hi")

    def test_unconfigured_gateway_is_refused(self):
        with platform_modules("sms") as (frappe, (sms,)):
            self.assertFalse(sms.is_sms_configured())
            with self.assertRaises(sms.SMSNotConfiguredError):
                sms.send_sms("8801712345678", "hi")
            frappe.requests.post.assert_not_called()


class RecaptchaTests(unittest.TestCase):
    def test_verifies_token_with_google(self):
        with platform_modules("recaptcha") as (frappe, (recaptcha,)):
            frappe.settings = configured_settings()
            frappe.requests.post.return_value = _response(json_data={"success": True})
            self.assertTrue(recaptcha.verify_recaptcha("tok", ip="203.0.113.5"))
            args, kwargs = frappe.requests.post.call_args
            self.assertEqual(args[0], "https://www.google.com/recaptcha/api/siteverify")
            self.assertEqual(
                kwargs["data"], {"secret": "captcha-secret", "response": "tok", "remoteip": "203.0.113.5"}
            )

    def test_fails_closed(self):
        with platform_modules("recaptcha") as (frappe, (recaptcha,)):
            frappe.settings = configured_settings()
            self.assertFalse(recaptcha.verify_recaptcha(""))
            self.assertFalse(recaptcha.verify_recaptcha(None))
            frappe.requests.post.return_value = _response(json_data={"success": False})
            self.assertFalse(recaptcha.verify_recaptcha("tok"))
            frappe.requests.post.return_value = _response(json_data={"success": "true"})
            self.assertFalse(recaptcha.verify_recaptcha("tok"))
            frappe.requests.post.side_effect = frappe.requests.RequestException()
            self.assertFalse(recaptcha.verify_recaptcha("tok"))

    def test_site_key_only_exposed_when_secret_configured(self):
        with platform_modules("recaptcha") as (frappe, (recaptcha,)):
            frappe.settings = FakeSettings(recaptcha_site_key="site-key")
            self.assertIsNone(recaptcha.get_recaptcha_site_key())
            frappe.settings = configured_settings()
            self.assertEqual(recaptcha.get_recaptcha_site_key(), "site-key")

    def test_signup_captcha_uses_recaptcha_when_configured(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _sms, _recaptcha):
            frappe.requests.post.return_value = _response(json_data={"success": False})
            with self.assertRaises(saas.SignupValidationError):
                saas.verify_signup_captcha("bad")
            frappe.requests.post.return_value = _response(json_data={"success": True})
            saas.verify_signup_captcha("good")

    def test_required_captcha_without_keys_is_503(self):
        with saas_with_clock(FakeSettings(require_captcha=1)) as (_frappe, saas, _sms, _recaptcha):
            with self.assertRaises(saas.SignupUnavailableError) as raised:
                saas.verify_signup_captcha(None)
            self.assertEqual(raised.exception.http_status_code, 503)


class PhoneSignupTests(unittest.TestCase):
    def _create(self, saas, frappe, **overrides):
        frappe.db.get_value.side_effect = plan_lookup()
        registration = Mock(flags=_Dict())
        frappe.get_doc.return_value.insert.return_value = registration
        values = {
            "business_name": "New Co",
            "owner_email": "owner@example.com",
            "owner_name": "Owner",
            "plan": "Plan",
            "owner_phone": "01712345678",
            **overrides,
        }
        return saas.create_registration(**values), frappe.get_doc.call_args.args[0]

    def test_phone_required_rejects_missing_or_invalid_numbers(self):
        for phone in (None, "", "12345"):
            with self.subTest(phone=phone), saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
                with self.assertRaises(saas.SignupValidationError) as raised:
                    self._create(saas, frappe, owner_phone=phone)
                self.assertEqual(raised.exception.http_status_code, 400)
                frappe.get_doc.assert_not_called()

    def test_phone_required_without_gateway_is_503(self):
        with saas_with_clock(FakeSettings(require_phone_verification=1)) as (frappe, saas, _s, _r):
            with self.assertRaises(saas.SignupUnavailableError):
                self._create(saas, frappe)
            frappe.get_doc.assert_not_called()

    def test_registration_stores_hashed_code_and_sends_sms(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
            registration, values = self._create(saas, frappe)
            otp = registration.flags.phone_otp
            self.assertRegex(otp, r"^[0-9]{6}$")
            self.assertEqual(values["owner_phone"], "8801712345678")
            self.assertEqual(values["phone_verification_required"], 1)
            self.assertNotIn(otp, values["phone_otp_hash"])
            self.assertTrue(saas._otp_matches(otp, values["phone_otp_hash"]))

            registration.owner_phone = "8801712345678"
            registration.owner_email = "owner@example.com"
            frappe.requests.post.return_value = _response(json_data={"response_code": 202})
            saas.send_registration_verification(registration)
            self.assertIn(otp, frappe.requests.post.call_args.kwargs["data"]["message"])
            frappe.sendmail.assert_called_once()

    def test_existing_mobile_is_a_conflict(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
            frappe.db.exists.side_effect = lambda doctype, filters=None: (
                doctype == "User" and isinstance(filters, dict) and "mobile_no" in filters
            )
            with self.assertRaises(saas.SignupConflictError):
                self._create(saas, frappe)


class PhoneOTPTests(unittest.TestCase):
    def _doc(self, saas, otp="123456", **values):
        doc = FakeDoc(
            name="REG-1",
            status="Pending Verification",
            owner_phone="8801712345678",
            phone_verification_required=1,
            phone_verified=0,
            email_verified=0,
            verification_sent_on=NOW - timedelta(minutes=5),
            phone_otp_sent_on=NOW - timedelta(minutes=2),
            phone_otp_attempts=0,
            phone_otp_resends=0,
            phone_otp_hash=saas._hash_otp(otp),
        )
        doc.update(values)
        return doc

    def _wire(self, frappe, doc):
        frappe.db.get_value.return_value = doc.name
        frappe.get_doc.return_value = doc

    def test_wrong_code_counts_attempts_then_locks(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
            doc = self._doc(saas)
            self._wire(frappe, doc)
            for expected in range(1, 6):
                with self.assertRaises(saas.InvalidOTPError):
                    saas.confirm_registration_phone("REG-1", "000000")
                self.assertEqual(doc.phone_otp_attempts, expected)
            with self.assertRaises(saas.OTPThrottledError) as raised:
                saas.confirm_registration_phone("REG-1", "123456")
            self.assertEqual(raised.exception.http_status_code, 429)
            self.assertFalse(doc.phone_verified)

    def test_expired_code_is_rejected(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
            doc = self._doc(saas, phone_otp_sent_on=NOW - timedelta(minutes=11))
            self._wire(frappe, doc)
            with self.assertRaises(saas.SignupValidationError):
                saas.confirm_registration_phone("REG-1", "123456")
            self.assertFalse(doc.phone_verified)

    def test_correct_code_waits_for_email_before_provisioning(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
            doc = self._doc(saas)
            self._wire(frappe, doc)
            saas.confirm_registration_phone("REG-1", " 123456 ")
            self.assertTrue(doc.phone_verified)
            self.assertIsNone(doc.phone_otp_hash)
            self.assertEqual(doc.status, "Pending Verification")
            frappe.enqueue.assert_not_called()

    def test_correct_code_after_email_starts_provisioning(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
            doc = self._doc(saas, email_verified=1)
            self._wire(frappe, doc)
            saas.confirm_registration_phone("REG-1", "123456")
            self.assertEqual(doc.status, "Provisioning")
            self.assertEqual(frappe.enqueue.call_args.kwargs["registration"], "REG-1")

    def test_email_verification_waits_for_phone(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
            doc = self._doc(saas, email_verification_hash=saas._hash_token("key"))
            self._wire(frappe, doc)
            saas.confirm_registration_email("key")
            self.assertTrue(doc.email_verified)
            self.assertEqual(doc.status, "Pending Verification")
            frappe.enqueue.assert_not_called()

    def test_unknown_or_finished_registration_is_rejected(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
            frappe.db.get_value.return_value = None
            with self.assertRaises(saas.SignupValidationError):
                saas.confirm_registration_phone("REG-404", "123456")
            with self.assertRaises(saas.SignupValidationError):
                saas.resend_registration_phone_otp("REG-404")

    def test_resend_respects_cooldown_and_limit(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
            doc = self._doc(saas, phone_otp_sent_on=NOW - timedelta(seconds=30))
            self._wire(frappe, doc)
            with self.assertRaises(saas.OTPThrottledError):
                saas.resend_registration_phone_otp("REG-1")
            doc.phone_otp_sent_on = NOW - timedelta(seconds=61)
            doc.phone_otp_resends = 5
            with self.assertRaises(saas.OTPThrottledError):
                saas.resend_registration_phone_otp("REG-1")
            frappe.requests.post.assert_not_called()

    def test_resend_issues_new_code(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
            doc = self._doc(saas, phone_otp_sent_on=NOW - timedelta(minutes=2), phone_otp_attempts=3)
            old_hash = doc.phone_otp_hash
            self._wire(frappe, doc)
            frappe.requests.post.return_value = _response(json_data={"response_code": 202})
            saas.resend_registration_phone_otp("REG-1")
            self.assertNotEqual(doc.phone_otp_hash, old_hash)
            self.assertEqual(doc.phone_otp_attempts, 0)
            self.assertEqual(doc.phone_otp_resends, 1)
            self.assertEqual(doc.phone_otp_sent_on, NOW)
            frappe.requests.post.assert_called_once()

    def test_provisioning_refuses_unverified_phone(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
            doc = self._doc(saas, status="Provisioning", email_verified=1)
            frappe.get_doc.return_value = doc
            with self.assertRaises(saas.SignupValidationError):
                saas._provision_registration("REG-1")

    def test_wrong_code_attempt_is_committed_by_endpoint(self):
        with saas_with_clock(configured_settings()) as (frappe, saas, _s, _r):
            doc = self._doc(saas)
            self._wire(frappe, doc)
            with self.assertRaises(saas.InvalidOTPError):
                saas.verify_registration_phone("REG-1", "000000")
            frappe.db.commit.assert_called_once()


class VendorRetryTests(unittest.TestCase):
    def test_only_vendor_can_retry(self):
        with saas_with_clock() as (frappe, saas, _s, _r):
            with patch.object(saas, "is_vendor_user", return_value=False):
                with self.assertRaises(frappe.PermissionError):
                    saas.retry_registration_provisioning("REG-1")
            frappe.enqueue.assert_not_called()

    def test_only_failed_registrations_are_retried(self):
        with saas_with_clock() as (frappe, saas, _s, _r):
            frappe.db.get_value.return_value = "Pending Payment"
            with patch.object(saas, "is_vendor_user", return_value=True):
                with self.assertRaises(saas.SignupValidationError):
                    saas.retry_registration_provisioning("REG-1")
            frappe.enqueue.assert_not_called()

    def test_failed_registration_is_requeued(self):
        with saas_with_clock() as (frappe, saas, _s, _r):
            frappe.db.get_value.return_value = "Failed"
            with patch.object(saas, "is_vendor_user", return_value=True):
                self.assertEqual(saas.retry_registration_provisioning("REG-1"), "REG-1")
            frappe.db.set_value.assert_called_once_with("SaaS Registration", "REG-1", "status", "Provisioning")
            self.assertEqual(frappe.enqueue.call_args.kwargs["registration"], "REG-1")


if __name__ == "__main__":
    unittest.main()
