"""Database-free tests for the public signup page: module URL parameter and verification step."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from frappe_stub import _Dict, plan_lookup, platform_modules

NOW = datetime(2026, 10, 18, 12, 0, 0)

DISTRIBUTION = _Dict(name="distribution", module_name="Distribution SaaS", description="FMCG", features="dsr_routes\nbangla_pwa")
CRM = _Dict(name="crm", module_name="CRM", description="", features="")


def _page_context(page, frappe, form_dict, modules=(DISTRIBUTION, CRM), plans=()):
    frappe.form_dict = _Dict(form_dict)
    frappe.local.form_dict = frappe.form_dict

    def get_all(doctype, **kwargs):
        if doctype == "SaaS Module":
            return list(modules)
        filters = kwargs.get("filters") or {}
        return [p for p in plans if not filters.get("saas_module") or p.saas_module == filters["saas_module"]]

    frappe.get_all.side_effect = get_all
    context = _Dict()
    with patch.object(page, "get_recaptcha_site_key", return_value=None), patch.object(
        page, "nowdate", return_value="2026-10-18"
    ):
        page.get_context(context)
    return context


class SignupPageModuleParamTests(unittest.TestCase):
    PLANS = (
        _Dict(name="Dist Basic", saas_module="distribution"),
        _Dict(name="CRM Basic", saas_module="crm"),
    )

    def test_module_param_selects_module_and_its_plans(self):
        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            context = _page_context(page, frappe, {"module": "distribution"}, plans=self.PLANS)
        self.assertEqual(context.module["name"], "Distribution SaaS")
        self.assertEqual(context.module["features"], ["DSR routes", "Bangla PWA"])
        self.assertEqual(context.selected_module, "distribution")
        self.assertEqual([p.name for p in context.plans], ["Dist Basic"])
        self.assertFalse(context.show_module_picker)
        self.assertFalse(context.module_unavailable)

    def test_without_param_several_modules_show_the_picker(self):
        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            context = _page_context(page, frappe, {}, plans=self.PLANS)
        self.assertIsNone(context.module)
        self.assertTrue(context.show_module_picker)
        self.assertEqual(len(context.plans), 2)

    def test_unknown_or_unsafe_module_param_shows_notice_and_no_plans(self):
        for value in ("hr", '"><script>', "Distribution"):
            with self.subTest(value=value), platform_modules("www.reckonerp_signup") as (frappe, (page,)):
                context = _page_context(page, frappe, {"module": value}, plans=self.PLANS)
                self.assertTrue(context.module_unavailable)
                self.assertEqual(context.plans, [])
                self.assertEqual(context.selected_module, "")

    def test_registration_param_opens_verify_step_only_for_valid_names(self):
        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            self.assertEqual(_page_context(page, frappe, {"registration": "REG-00042"}).registration, "REG-00042")
        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            self.assertEqual(_page_context(page, frappe, {"registration": "REG-1\"><b>"}).registration, "")

    def test_footer_company_details(self):
        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            context = _page_context(page, frappe, {})
        self.assertEqual(context.company["name"], "Reckon Technologies Ltd.")
        self.assertEqual(context.company["email"], "hello@reckon.tech")
        self.assertEqual(context.company["phone"], "+8801325-009955")
        self.assertEqual(context.company["website"], "https://www.reckon.tech/")
        self.assertTrue(context.company["logo"].endswith("reckon-tech-logo.png"))
        self.assertEqual(context.current_year, "2026")


class ModuleSpecificSignupTests(unittest.TestCase):
    def _create(self, saas, frappe, saas_module):
        frappe.db.get_value.side_effect = plan_lookup(saas_module="distribution")
        frappe.get_doc.return_value.insert.return_value = Mock(flags=_Dict())
        return saas.create_registration(
            business_name="Co", owner_email="o@example.com", owner_name="O", plan="Dist Basic",
            saas_module=saas_module,
        )

    def test_plan_from_another_module_is_refused(self):
        with platform_modules("saas") as (frappe, (saas,)):
            with self.assertRaises(saas.SignupValidationError):
                self._create(saas, frappe, "crm")
            frappe.get_doc.assert_not_called()

    def test_matching_or_absent_module_is_accepted(self):
        for value in ("distribution", None, ""):
            with self.subTest(value=value), platform_modules("saas") as (frappe, (saas,)):
                self._create(saas, frappe, value)
                self.assertEqual(frappe.get_doc.call_args.args[0]["saas_module"], "distribution")


class VerificationStatusTests(unittest.TestCase):
    def test_status_exposes_only_stage_and_booleans(self):
        cases = {
            "Pending Verification": "verify",
            "Provisioning": "provisioning",
            "Pending Payment": "ready",
            "Active": "ready",
            "Failed": "failed",
            "Cancelled": "closed",
        }
        for status, stage in cases.items():
            with self.subTest(status=status), platform_modules("saas") as (frappe, (saas,)):
                frappe.db.get_value.return_value = _Dict(
                    status=status, email_verified=1, phone_verification_required=1, phone_verified=0
                )
                result = saas.registration_verification_status("REG-1")
                self.assertEqual(
                    result,
                    {"stage": stage, "email_verified": True, "phone_required": True, "phone_verified": False},
                )

    def test_unknown_registration_is_a_400(self):
        with platform_modules("saas") as (_frappe, (saas,)):
            with self.assertRaises(saas.SignupValidationError):
                saas.registration_verification_status("REG-404")
            with self.assertRaises(saas.SignupValidationError):
                saas.registration_verification_status(None)


class ResendEmailTests(unittest.TestCase):
    def _doc(self):
        doc = _Dict(
            name="REG-1",
            owner_email="o@example.com",
            owner_name="O",
            business_name="Co",
            verification_sent_on=NOW - timedelta(minutes=5),
            email_verification_hash="old",
        )

        def db_set(field, value=None, **kwargs):
            doc.update(field if isinstance(field, dict) else {field: value})

        doc.db_set = db_set
        return doc

    def _resend(self, saas, frappe, doc):
        frappe.db.get_value.return_value = doc.name
        frappe.get_doc.return_value = doc
        frappe.generate_hash.return_value = "fresh-token"
        with patch.object(saas, "now_datetime", return_value=NOW), patch.object(
            saas, "add_to_date", side_effect=lambda value, **delta: value + timedelta(**delta)
        ), patch.object(saas, "get_datetime", side_effect=lambda value: value), patch.object(
            saas, "get_url", side_effect=lambda path: f"https://example.test{path}"
        ):
            saas.resend_registration_verification_email("REG-1")

    def test_resend_replaces_link_and_emails_it(self):
        with platform_modules("saas") as (frappe, (saas,)):
            doc = self._doc()
            self._resend(saas, frappe, doc)
            self.assertEqual(doc.email_verification_hash, saas._hash_token("fresh-token"))
            self.assertIn("fresh-token", frappe.sendmail.call_args.kwargs["message"])

    def test_resend_cooldown_and_daily_limit(self):
        with platform_modules("saas") as (frappe, (saas,)):
            doc = self._doc()
            self._resend(saas, frappe, doc)
            with self.assertRaises(saas.OTPThrottledError):
                self._resend(saas, frappe, doc)
            frappe.cache.delete_value("reckon_saas_email_resend_cooldown::REG-1")
            frappe.cache.set_value("reckon_saas_email_resend_count::REG-1", 5)
            with self.assertRaises(saas.OTPThrottledError):
                self._resend(saas, frappe, doc)
            self.assertEqual(frappe.sendmail.call_count, 1)

    def test_resend_refused_for_verified_or_unknown_registration(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.db.get_value.return_value = None
            with self.assertRaises(saas.SignupValidationError):
                saas.resend_registration_verification_email("REG-1")
            frappe.sendmail.assert_not_called()


if __name__ == "__main__":
    unittest.main()
