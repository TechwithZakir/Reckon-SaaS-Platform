"""Database-free regression tests for the P0 go-live fixes.

The bench integration tests live in reckon_distribution
(``reckon_distribution/tests/test_go_live_blockers.py``); these cover the same
rules with a stubbed ``frappe`` so CI can run them without a site.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from frappe_stub import _Dict, platform_modules


class SignupValidationTests(unittest.TestCase):
    def test_existing_company_is_refused_before_any_tenant_record(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.db.get_value.return_value = 1  # plan enabled
            frappe.db.exists.side_effect = lambda doctype, *args: doctype == "Company"
            with self.assertRaises(saas.SignupConflictError) as raised:
                saas.create_registration(
                    business_name="Existing Co",
                    owner_email="guest@example.com",
                    owner_name="Guest",
                    plan="Plan",
                )
            self.assertEqual(raised.exception.http_status_code, 409)
            frappe.get_doc.assert_not_called()

    def test_existing_user_is_refused(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.db.get_value.return_value = 1
            frappe.db.exists.side_effect = lambda doctype, *args: doctype == "User"
            with self.assertRaises(saas.SignupConflictError):
                saas.create_registration(
                    business_name="New Co",
                    owner_email="admin@victim.example",
                    owner_name="Guest",
                    plan="Plan",
                )
            frappe.get_doc.assert_not_called()

    def test_new_signup_creates_only_a_pending_registration(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.db.get_value.return_value = 1
            registration = Mock(flags=_Dict())
            frappe.get_doc.return_value.insert.return_value = registration
            result = saas.create_registration(
                business_name="New Co",
                owner_email="Owner@Example.com ",
                owner_name="Owner",
                plan="Plan",
            )
            self.assertIs(result, registration)
            frappe.get_doc.assert_called_once()
            values = frappe.get_doc.call_args.args[0]
            self.assertEqual(values["doctype"], "SaaS Registration")
            self.assertEqual(values["status"], "Pending Verification")
            self.assertEqual(values["owner_email"], "owner@example.com")
            self.assertNotEqual(values["email_verification_hash"], "token")
            self.assertEqual(registration.flags.verification_token, "token")

    def test_invalid_input_is_a_400(self):
        cases = [
            {"business_name": ""},
            {"business_name": "<b>x</b>"},
            {"business_name": "x" * 141},
            {"business_name": ["list"]},
            {"owner_email": "nope"},
            {"billing_cycle": "Daily"},
        ]
        for case in cases:
            with self.subTest(case=case), platform_modules("saas") as (frappe, (saas,)):
                frappe.db.get_value.return_value = 1
                values = {
                    "business_name": "Co",
                    "owner_email": "o@example.com",
                    "owner_name": "Owner",
                    "plan": "Plan",
                    **case,
                }
                with self.assertRaises(saas.SignupValidationError) as raised:
                    saas.create_registration(**values)
                self.assertEqual(raised.exception.http_status_code, 400)

    def test_disabled_or_unknown_plan_is_a_400(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.db.get_value.return_value = 0
            with self.assertRaises(saas.SignupValidationError):
                saas.create_registration(
                    business_name="Co", owner_email="o@example.com", owner_name="O", plan="Old"
                )

    def test_captcha_hook(self):
        with platform_modules("saas") as (frappe, (saas,)):
            saas.verify_signup_captcha(None)  # no verifier, not required
            frappe.conf.reckon_saas_require_captcha = 1
            with self.assertRaises(saas.SignupValidationError):
                saas.verify_signup_captcha(None)
            frappe.get_hooks.return_value = ["site.captcha.verify"]
            frappe.get_attr.return_value = Mock(return_value=False)
            with self.assertRaises(saas.SignupValidationError):
                saas.verify_signup_captcha("bad")
            frappe.get_attr.return_value = Mock(return_value=True)
            saas.verify_signup_captcha("good")


class ProvisioningTests(unittest.TestCase):
    def test_verification_enqueues_deduplicated_provisioning(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.db.get_value.return_value = "REG-1"
            registration = Mock(name="registration")
            registration.name = "REG-1"
            frappe.get_doc.return_value = registration
            with patch.object(saas, "_verification_expired", return_value=False):
                saas.confirm_registration_email("token")
            update = registration.db_set.call_args.args[0]
            self.assertEqual(update["status"], "Provisioning")
            self.assertIsNone(update["email_verification_hash"])
            kwargs = frappe.enqueue.call_args.kwargs
            self.assertEqual(frappe.enqueue.call_args.args[0], "reckon_saas_platform.saas.provision_registration")
            self.assertTrue(kwargs["deduplicate"])
            self.assertEqual(kwargs["registration"], "REG-1")

    def test_unknown_verification_key_is_a_400(self):
        with platform_modules("saas") as (frappe, (saas,)):
            with self.assertRaises(saas.SignupValidationError):
                saas.confirm_registration_email("wrong")
            frappe.enqueue.assert_not_called()

    def test_provisioning_failure_rolls_back_and_marks_failed(self):
        with platform_modules("saas") as (frappe, (saas,)):
            doc = SimpleNamespace(
                name="REG-1",
                status="Provisioning",
                email_verified=1,
                business_name="Co",
                owner_email="o@example.com",
                owner_name="O",
                plan="Plan",
                db_set=Mock(),
            )
            frappe.get_doc.return_value = doc
            with patch.object(
                saas, "_assert_signup_identity_available", side_effect=saas.SignupConflictError("taken")
            ), patch.object(saas, "_create_tenant_company") as create_company:
                result = saas._provision_registration("REG-1")
            self.assertIs(result, doc)
            create_company.assert_not_called()
            frappe.db.rollback.assert_called_once_with(save_point="reckon_saas_provision")
            status = doc.db_set.call_args.args[0]
            self.assertEqual(status["status"], "Failed")
            self.assertIn("taken", status["error"])

    def test_already_provisioned_registration_is_not_reprocessed(self):
        with platform_modules("saas") as (frappe, (saas,)):
            doc = SimpleNamespace(status="Pending Payment", db_set=Mock())
            frappe.get_doc.return_value = doc
            with patch.object(saas, "_create_tenant_company") as create_company:
                saas._provision_registration("REG-1")
            create_company.assert_not_called()
            doc.db_set.assert_not_called()


class SeedJobTests(unittest.TestCase):
    def _job(self):
        job = Mock()
        job.name = "TPJ-1"
        return job

    def test_handler_failure_marks_failed_without_raising(self):
        with platform_modules("saas") as (frappe, (saas,)):
            job = self._job()
            frappe.db.get_value.return_value = "Pending"
            frappe.get_attr.return_value = Mock(side_effect=RuntimeError("boom"))
            with patch.object(saas, "ensure_tenant_seed_job", return_value=job), patch.object(
                saas, "get_seed_handlers", return_value=["mod.seed"]
            ):
                result = saas.run_tenant_seed_job("Co")
            self.assertIs(result, job)
            frappe.db.savepoint.assert_called_once_with("reckon_saas_tenant_seed")
            frappe.db.rollback.assert_called_once_with(save_point="reckon_saas_tenant_seed")
            final = job.db_set.call_args.args[0]
            self.assertEqual(final["status"], "Failed")
            self.assertIn("boom", final["error"])
            frappe.log_error.assert_called_once()

    def test_lost_savepoint_falls_back_to_full_rollback(self):
        with platform_modules("saas") as (frappe, (saas,)):
            job = self._job()
            frappe.db.get_value.return_value = "Failed"
            frappe.get_attr.return_value = Mock(side_effect=RuntimeError("boom"))
            frappe.db.rollback.side_effect = [Exception("no savepoint"), None]
            with patch.object(saas, "ensure_tenant_seed_job", return_value=job), patch.object(
                saas, "get_seed_handlers", return_value=["mod.seed"]
            ):
                saas.run_tenant_seed_job("Co")
            self.assertEqual(frappe.db.rollback.call_count, 2)
            self.assertEqual(job.db_set.call_args.args[0]["status"], "Failed")

    def test_complete_job_is_locked_and_not_rerun(self):
        with platform_modules("saas") as (frappe, (saas,)):
            job = self._job()
            frappe.db.get_value.return_value = "Complete"
            with patch.object(saas, "ensure_tenant_seed_job", return_value=job), patch.object(
                saas, "get_seed_handlers", return_value=["mod.seed"]
            ):
                saas.run_tenant_seed_job("Co")
            self.assertTrue(frappe.db.get_value.call_args.kwargs["for_update"])
            frappe.get_attr.assert_not_called()
            job.db_set.assert_not_called()

    def test_success_marks_complete_and_invalidates_gate_cache(self):
        with platform_modules("saas") as (frappe, (saas,)):
            job = self._job()
            frappe.db.get_value.return_value = "Pending"
            frappe.cache.set_value("reckon_saas_operational_access::Co", 0)
            with patch.object(saas, "ensure_tenant_seed_job", return_value=job), patch.object(
                saas, "get_seed_handlers", return_value=["mod.seed"]
            ):
                saas.run_tenant_seed_job("Co")
            self.assertEqual(job.db_set.call_args.args[0]["status"], "Complete")
            self.assertIsNone(frappe.cache.get_value("reckon_saas_operational_access::Co"))


class OperationalAccessCacheTests(unittest.TestCase):
    def test_access_is_cached_per_company_and_invalidated(self):
        with platform_modules("saas") as (frappe, (saas,)):
            with patch.object(saas, "_has_operational_access", return_value=False) as check:
                self.assertFalse(saas.has_operational_access("Co"))
                self.assertFalse(saas.has_operational_access("Co"))
                self.assertEqual(check.call_count, 1)
            saas.invalidate_operational_access_cache("Co")
            frappe.db.after_commit.add.assert_called_once()
            with patch.object(saas, "_has_operational_access", return_value=True):
                self.assertTrue(saas.has_operational_access("Co"))


class SubscriptionGateTests(unittest.TestCase):
    def _enforce(self, gate, frappe, path, cmd=None, user="tenant@example.com"):
        frappe.session.user = user
        frappe.local.form_dict = _Dict(cmd=cmd)
        frappe.local.request = SimpleNamespace(path=path)
        gate.enforce_operational_access()

    def test_blocked_tenant_gets_403_on_api_and_redirect_on_desk(self):
        with platform_modules("saas", "saas_gate") as (frappe, (saas, gate)):
            with patch.object(gate, "is_user_gated", return_value=True):
                for path in ("/api/method/frappe.client.get_list", "/api/resource/Item"):
                    with self.subTest(path=path), self.assertRaises(saas.SubscriptionGateError):
                        self._enforce(gate, frappe, path)
                with self.assertRaises(saas.SubscriptionGateError):
                    self._enforce(gate, frappe, "/", cmd="frappe.client.get_list")
                for path in ("/app", "/app/item", "/desk/distribution"):
                    with self.subTest(path=path):
                        self._enforce(gate, frappe, path)
                        self.assertEqual(frappe.flags.saas_gate_redirect, "/reckonerp-subscription")

    def test_exempt_routes_and_platform_users_are_not_gated(self):
        with platform_modules("saas", "saas_gate") as (frappe, (saas, gate)):
            with patch.object(gate, "is_user_gated", return_value=True) as gated:
                for path in (
                    "/api/method/login",
                    "/api/method/logout",
                    "/api/method/reckon_saas_platform.saas.get_subscription_summary",
                    "/assets/app.js",
                    "/reckonerp-subscription",
                    "/application-form",
                ):
                    with self.subTest(path=path):
                        self._enforce(gate, frappe, path)
                        self.assertFalse(frappe.flags.saas_gate_redirect)
                self._enforce(gate, frappe, "/", cmd="web_logout")
                gated.assert_not_called()
                for user in ("Guest", "Administrator"):
                    self._enforce(gate, frappe, "/api/method/frappe.client.get_list", user=user)
                gated.assert_not_called()

    def test_redirect_hook_replaces_response(self):
        with platform_modules("saas", "saas_gate") as (frappe, (saas, gate)):
            response = Mock(headers={})
            gate.redirect_blocked_response(response, None)
            response.set_data.assert_not_called()
            frappe.flags.saas_gate_redirect = "/reckonerp-subscription"
            gate.redirect_blocked_response(response, None)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"], "/reckonerp-subscription")

    def test_is_user_gated(self):
        with platform_modules("saas", "saas_gate") as (frappe, (saas, gate)):
            with patch.object(gate, "get_user_companies", return_value=[]):
                self.assertFalse(gate.is_user_gated("vendor@example.com"))
            with patch.object(gate, "get_user_companies", return_value=["Co"]), patch.object(
                gate, "has_operational_access", return_value=False
            ):
                self.assertTrue(gate.is_user_gated("tenant@example.com"))
            with patch.object(gate, "get_user_companies", return_value=["Co"]), patch.object(
                gate, "has_operational_access", return_value=True
            ):
                self.assertFalse(gate.is_user_gated("tenant@example.com"))


class TenantPlatformRoleTests(unittest.TestCase):
    def test_tenant_user_with_system_manager_cannot_bypass(self):
        with platform_modules("tenant_security") as (frappe, (security,)):
            frappe.get_roles.return_value = ["System Manager"]
            frappe.db.exists.return_value = "TUA-1"
            self.assertFalse(security.user_can_bypass_tenant("tenant@example.com"))
            frappe.db.exists.return_value = None
            self.assertTrue(security.user_can_bypass_tenant("ops@example.com"))
            self.assertTrue(security.user_can_bypass_tenant("Administrator"))

    def test_plain_tenant_user_skips_assignment_lookup(self):
        with platform_modules("tenant_security") as (frappe, (security,)):
            frappe.get_roles.return_value = ["Reckon Distribution User"]
            self.assertFalse(security.user_can_bypass_tenant("dsr@example.com"))
            frappe.db.exists.assert_not_called()

    def test_user_validate_refuses_platform_roles_for_tenant_user(self):
        with platform_modules("tenant_security") as (frappe, (security,)):
            doc = Mock()
            doc.name = "tenant@example.com"
            doc.is_new.return_value = False
            doc.get.return_value = [SimpleNamespace(role="System Manager")]
            frappe.db.exists.return_value = "TUA-1"
            with self.assertRaises(frappe.PermissionError):
                security.validate_user_tenant_roles(doc)
            frappe.db.exists.return_value = None
            security.validate_user_tenant_roles(doc)

    def test_assignment_refuses_platform_user(self):
        with platform_modules("tenant_security") as (frappe, (security,)):
            for role in ("System Manager", "Reckon Vendor Superuser"):
                frappe.get_roles.return_value = [role]
                with self.subTest(role=role), self.assertRaises(frappe.PermissionError):
                    security.assert_user_has_no_platform_roles("ops@example.com")
            frappe.get_roles.return_value = ["Reckon Distribution Admin"]
            security.assert_user_has_no_platform_roles("admin@tenant.example")

    def test_audit_lists_existing_violations(self):
        with platform_modules("tenant_security") as (frappe, (security,)):
            frappe.db.exists.return_value = True
            frappe.get_all.side_effect = [
                [
                    _Dict(name="TUA-1", user="bad@example.com", company="Co"),
                    _Dict(name="TUA-2", user="ok@example.com", company="Co"),
                ],
                [_Dict(parent="bad@example.com", role="System Manager")],
            ]
            with patch("builtins.print"):
                violations = security.audit_tenant_role_violations()
            self.assertEqual(
                violations,
                [{"user": "bad@example.com", "company": "Co", "assignment": "TUA-1", "roles": ["System Manager"]}],
            )
            frappe.log_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
