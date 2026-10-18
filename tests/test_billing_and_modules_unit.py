"""Database-free tests: SaaS modules on registrations and subscriptions, trial and
grace billing with the dues gate, and the signup page CSRF fix."""

from __future__ import annotations

import json
import re
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from frappe_stub import REPO_ROOT, _Dict, platform_modules

APP = REPO_ROOT / "reckon_saas_platform"
TODAY = "2026-10-19"
D = date.fromisoformat


def _sub(**values):
    row = _Dict(status="Pending", start_date=None, end_date=None, trial_end_date=None, grace_until=None, grace_days=0)
    row.update(values)
    return row


class BillingStateTests(unittest.TestCase):
    def state(self, **values):
        with platform_modules("saas") as (_frappe, (saas,)):
            return saas.subscription_billing_state(_sub(**values), today=TODAY)

    def test_plan_has_trial_and_grace_days_and_subscription_keeps_its_own_copy(self):
        plan = json.loads((APP / "saas_platform/doctype/saas_plan/saas_plan.json").read_text(encoding="utf-8"))
        sub = json.loads(
            (APP / "saas_platform/doctype/saas_subscription/saas_subscription.json").read_text(encoding="utf-8")
        )
        plan_fields = {f["fieldname"]: f for f in plan["fields"]}
        sub_fields = {f["fieldname"] for f in sub["fields"]}
        for fieldname in ("trial_days", "grace_days"):
            self.assertEqual(plan_fields[fieldname]["fieldtype"], "Int")
            self.assertIn(fieldname, plan["field_order"])
        self.assertTrue({"trial_end_date", "grace_days", "grace_until"} <= sub_fields)
        self.assertTrue({"trial_end_date", "grace_days"} <= set(sub["field_order"]))

    def test_inside_trial_has_access_without_dues(self):
        state = self.state(status="Trial", start_date="2026-10-10", trial_end_date="2026-10-23")
        self.assertEqual((state["state"], state["access"], state["dues"]), ("trial", True, False))
        self.assertEqual(state["days_left"], 4)

    def test_trial_over_unpaid_is_grace_then_blocked(self):
        values = {"status": "Trial", "start_date": "2026-10-01", "trial_end_date": "2026-10-14", "grace_days": 7}
        state = self.state(**values)
        self.assertEqual((state["state"], state["access"], state["dues"]), ("grace", True, True))
        self.assertEqual(state["grace_end"], D("2026-10-21"))
        state = self.state(**{**values, "grace_days": 3})
        self.assertEqual((state["state"], state["access"], state["dues"]), ("blocked", False, True))

    def test_paid_period_then_grace_after_it_ends(self):
        self.assertEqual(self.state(status="Active", end_date="2026-11-01")["state"], "active")
        state = self.state(status="Active", end_date="2026-10-17", grace_days=5)
        self.assertEqual((state["state"], state["grace_end"]), ("grace", D("2026-10-22")))
        state = self.state(status="Expired", end_date="2026-10-01", grace_days=5)
        self.assertEqual((state["state"], state["access"], state["dues"]), ("blocked", False, True))

    def test_vendor_grace_until_extends_but_never_shortens(self):
        state = self.state(status="Active", end_date="2026-10-01", grace_days=2, grace_until="2026-10-25")
        self.assertEqual((state["state"], state["grace_end"]), ("grace", D("2026-10-25")))
        state = self.state(status="Active", end_date="2026-10-17", grace_days=5, grace_until="2026-10-18")
        self.assertEqual((state["state"], state["grace_end"]), ("grace", D("2026-10-22")))

    def test_new_unpaid_subscription_without_trial_or_grace_stays_locked(self):
        state = self.state(status="Pending", start_date=TODAY)
        self.assertEqual((state["state"], state["access"]), ("blocked", False))
        # With grace days the owner can start working before the first payment.
        state = self.state(status="Pending", start_date=TODAY, grace_days=3)
        self.assertEqual((state["state"], state["grace_end"]), ("grace", D("2026-10-21")))

    def test_vendor_suspension_blocks_whatever_the_dates(self):
        for status in ("Suspended", "Cancelled"):
            with self.subTest(status=status):
                state = self.state(status=status, end_date="2027-01-01", trial_end_date="2027-01-01")
                self.assertEqual((state["access"], state["dues"]), (False, False))

    def test_legacy_rows_keep_their_old_meaning(self):
        self.assertTrue(self.state(status="Active")["access"])  # no end date: open-ended
        self.assertTrue(self.state(status="Trial")["access"])  # trial without dates
        self.assertTrue(self.state(status="Trial", end_date="2026-10-30")["access"])
        self.assertFalse(self.state(status="Trial", end_date="2026-10-01")["access"])
        self.assertTrue(self.state(status="Grace", grace_until="2026-10-20")["access"])
        self.assertFalse(self.state(status="Grace", grace_until="2026-10-18")["access"])

    def test_status_follows_the_state(self):
        with platform_modules("saas") as (_frappe, (saas,)):
            for values, expected in (
                ({"status": "Trial", "trial_end_date": "2026-10-30"}, "Trial"),
                ({"status": "Trial", "trial_end_date": "2026-10-01"}, "Expired"),
                ({"status": "Active", "end_date": "2026-10-17", "grace_days": 5}, "Grace"),
                ({"status": "Pending", "start_date": TODAY}, "Pending"),
                ({"status": "Suspended", "end_date": "2027-01-01"}, "Suspended"),
            ):
                with self.subTest(values=values):
                    row = _sub(**values)
                    state = saas.subscription_billing_state(row, today=TODAY)
                    self.assertEqual(saas.subscription_status_for_state(row, state), expected)


class BillingFlowTests(unittest.TestCase):
    def test_provisioned_subscription_starts_trial_and_copies_grace_days(self):
        with platform_modules("saas") as (frappe, (saas,)):
            plan = _Dict(name="Acc Pro", saas_module="accounts", plan_version="1", price=500, currency="BDT",
                         trial_days=14, grace_days=5)
            registration = _Dict(name="REG-1", billing_cycle="Monthly", saas_module="accounts")
            with patch.object(saas, "nowdate", return_value=TODAY):
                saas._create_registration_subscription(registration, plan, "Co", "o@example.com")
                values = frappe.get_doc.call_args.args[0]
                self.assertEqual(values["status"], "Trial")
                self.assertEqual(values["trial_end_date"], D("2026-11-01"))
                self.assertEqual((values["grace_days"], values["saas_module"]), (5, "accounts"))

                saas._create_registration_subscription(registration, _Dict(plan, trial_days=0), "Co", "o@x.com")
                values = frappe.get_doc.call_args.args[0]
                self.assertEqual((values["status"], values["trial_end_date"]), ("Pending", None))

    def _verify(self, subscription, payment_status="Pending Verification"):
        with platform_modules("saas") as (frappe, (saas,)):
            payment = Mock(status=payment_status, subscription="SUB-1")
            frappe.get_doc.side_effect = lambda doctype, name: payment if doctype == "SaaS Payment" else subscription
            with patch.object(saas, "nowdate", return_value=TODAY):
                saas.verify_payment("PAY-1", reference="TRX1")
        return subscription, payment

    def test_payment_during_trial_starts_after_the_trial(self):
        sub = Mock(status="Trial", start_date="2026-10-10", end_date=None, trial_end_date="2026-10-23",
                   grace_until=None, billing_cycle="Monthly")
        sub.get = lambda key, default=None: getattr(sub, key, default)
        self._verify(sub)
        self.assertEqual((sub.status, sub.end_date, sub.grace_until), ("Active", D("2026-11-23"), None))
        sub.save.assert_called_once()

    def test_renewal_extends_from_the_paid_end_and_late_payment_from_today(self):
        sub = Mock(status="Active", start_date="2026-01-01", end_date="2026-10-25", trial_end_date=None,
                   grace_until=None, billing_cycle="Quarterly")
        sub.get = lambda key, default=None: getattr(sub, key, default)
        self._verify(sub)
        self.assertEqual(sub.end_date, D("2027-01-25"))

        sub = Mock(status="Grace", start_date="2026-01-01", end_date="2026-10-01", trial_end_date=None,
                   grace_until="2026-10-20", billing_cycle="Monthly")
        sub.get = lambda key, default=None: getattr(sub, key, default)
        self._verify(sub)
        self.assertEqual((sub.end_date, sub.grace_until), (D("2026-11-19"), None))

    def test_verifying_a_payment_twice_does_not_buy_a_second_period(self):
        sub = Mock(status="Active", end_date="2026-11-19")
        _sub_doc, payment = self._verify(sub, payment_status="Verified")
        payment.save.assert_not_called()
        sub.save.assert_not_called()

    def test_daily_refresh_moves_statuses_and_drops_the_gate_cache(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.get_all.return_value = [
                _sub(name="SUB-1", company="A", status="Trial", trial_end_date="2026-10-15", grace_days=7),
                _sub(name="SUB-2", company="B", status="Active", end_date="2026-10-01"),
                _sub(name="SUB-3", company="C", status="Active", end_date="2026-12-01"),
            ]
            with patch.object(saas, "nowdate", return_value=TODAY), patch.object(
                saas, "invalidate_operational_access_cache"
            ) as invalidate:
                self.assertEqual(saas.refresh_subscription_statuses(), 2)
            calls = {c.args[1]: c.args[2] for c in frappe.db.set_value.call_args_list}
            self.assertEqual(calls["SUB-1"], {"status": "Grace", "grace_until": D("2026-10-22")})
            self.assertEqual(calls["SUB-2"], {"status": "Expired"})
            self.assertNotIn("SUB-3", calls)
            self.assertEqual({c.args[0] for c in invalidate.call_args_list}, {"A", "B"})

    def test_daily_job_and_grace_patch_are_registered(self):
        with platform_modules("hooks") as (_frappe, (hooks,)):
            self.assertIn("reckon_saas_platform.saas.refresh_subscription_statuses", hooks.scheduler_events["daily"])
        patches = (APP / "patches.txt").read_text(encoding="utf-8")
        self.assertIn("reckon_saas_platform.patches.copy_plan_grace_days_to_subscriptions", patches)
        with platform_modules("patches.copy_plan_grace_days_to_subscriptions") as (frappe, (patch_module,)):
            frappe.db.has_column = Mock(return_value=True)
            frappe.get_all.side_effect = [
                [_Dict(name="Pro", grace_days=5), _Dict(name="Free", grace_days=0)],
                [_Dict(name="SUB-1", plan="Pro")],
            ]
            patch_module.execute()
            self.assertEqual(frappe.get_all.call_args.kwargs["filters"]["plan"], ["in", ["Pro"]])
            frappe.db.set_value.assert_called_once_with(
                "SaaS Subscription", "SUB-1", "grace_days", 5, update_modified=False
            )


class DuesGateTests(unittest.TestCase):
    def test_dues_after_grace_lock_the_company_and_grace_keeps_it_open(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.db.exists.return_value = "JOB-1"  # seed complete
            frappe.get_all.side_effect = lambda doctype, **kwargs: (
                [_Dict(name="accounts", module_name="Reckon Accounts")]
                if doctype == "SaaS Module"
                else rows
            )
            rows = [_sub(name="SUB-1", saas_module="accounts", status="Trial", trial_end_date="2026-10-10",
                         grace_days=3)]
            with patch.object(saas, "nowdate", return_value=TODAY):
                with self.assertRaises(saas.SubscriptionGateError):
                    saas.assert_operational_access("Co")
                rows[0]["grace_days"] = 30
                saas.assert_operational_access("Co")

    def test_blocked_tenant_can_still_reach_the_payment_endpoint(self):
        with platform_modules("saas_gate") as (frappe, (gate,)):
            frappe.session = _Dict(user="owner@example.com")
            frappe.local.request = SimpleNamespace(path="/api/method/reckon_saas_platform.saas.submit_payment_reference")
            with patch.object(gate, "is_user_gated", return_value=True):
                gate.enforce_operational_access()
                self.assertFalse(frappe.flags.saas_gate_blocked)
                frappe.local.request = SimpleNamespace(path="/app/accounts")
                gate.enforce_operational_access()
                self.assertEqual(frappe.flags.saas_gate_redirect, "/reckonerp-subscription")

    def _submit(self, frappe, saas, subscription_company="Co", pending=None, **kwargs):
        frappe.db.get_value.side_effect = lambda doctype, *args, **kw: (
            _Dict(name="SUB-1", company=subscription_company, price=500, currency="BDT", status="Grace")
            if doctype == "SaaS Subscription"
            else pending
        )
        with patch.object(saas, "resolve_tenant", return_value=SimpleNamespace(company="Co")):
            return saas.submit_payment_reference(**{"subscription": "SUB-1", "reference": "TRX9", **kwargs})

    def test_tenant_reports_a_payment_for_its_own_subscription(self):
        with platform_modules("saas") as (frappe, (saas,)):
            result = self._submit(frappe, saas, provider="bKash")
            values = frappe.get_doc.call_args.args[0]
            self.assertTrue(result["ok"])
            self.assertEqual(
                (values["doctype"], values["subscription"], values["company"], values["status"]),
                ("SaaS Payment", "SUB-1", "Co", "Pending Verification"),
            )
            self.assertEqual((values["gateway_provider"], values["gateway_reference"], values["amount"]),
                             ("bKash", "TRX9", 500))

    def test_open_payment_is_updated_not_duplicated(self):
        with platform_modules("saas") as (frappe, (saas,)):
            self._submit(frappe, saas, pending="PAY-7", provider="Nagad")
            frappe.get_doc.assert_called_once_with("SaaS Payment", "PAY-7")
            payment = frappe.get_doc.return_value
            self.assertEqual((payment.gateway_provider, payment.gateway_reference), ("Nagad", "TRX9"))
            payment.save.assert_called_once()

    def test_payment_for_another_company_or_bad_input_is_refused(self):
        with platform_modules("saas") as (frappe, (saas,)):
            with self.assertRaises(frappe.PermissionError):
                self._submit(frappe, saas, subscription_company="Other Co")
            for kwargs in ({"reference": ""}, {"reference": "<script>"}, {"provider": "PayPal"}):
                with self.subTest(kwargs=kwargs), self.assertRaises(saas.SignupValidationError):
                    self._submit(frappe, saas, **kwargs)
            frappe.get_doc.assert_not_called()


class ModuleRecordTests(unittest.TestCase):
    def _controller(self, plan_module):
        with platform_modules("saas_platform.doctype.saas_subscription.saas_subscription") as (frappe, (mod,)):
            frappe.db.get_value.side_effect = lambda doctype, name, field: plan_module
            return frappe, mod

    def test_registration_and_subscription_take_the_plan_module(self):
        with platform_modules("saas_platform.doctype.saas_subscription.saas_subscription") as (frappe, (mod,)):
            frappe.db.get_value.side_effect = lambda doctype, name, field: "accounts"
            doc = _Dict(plan="Acc Pro", saas_module=None)
            mod.set_module_from_plan(doc)
            self.assertEqual(doc.saas_module, "accounts")
            with self.assertRaises(frappe.ValidationError):
                mod.set_module_from_plan(_Dict(plan="Acc Pro", saas_module="distribution"))

    def test_registration_controller_validates_the_module(self):
        with platform_modules("saas_platform.doctype.saas_registration.saas_registration") as (frappe, (mod,)):
            frappe.db.get_value.side_effect = lambda doctype, name, field: "accounts"
            doc = SimpleNamespace(plan="Acc Pro", saas_module="")
            mod.SaaSRegistration.validate(doc)
            self.assertEqual(doc.saas_module, "accounts")

    def test_company_subscriptions_carry_module_label_and_billing(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.get_all.side_effect = lambda doctype, **kwargs: (
                [_Dict(name="accounts", module_name="Reckon Accounts")]
                if doctype == "SaaS Module"
                else [_sub(name="SUB-1", saas_module="accounts", status="Active", end_date="2026-12-01")]
            )
            with patch.object(saas, "nowdate", return_value=TODAY):
                (row,) = saas.get_company_module_subscriptions("Co")
        self.assertEqual((row["module_name"], row["billing"]["state"], row["active"]), ("Reckon Accounts", "active", True))

    def test_vendor_dashboard_labels_every_list_with_its_module(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.db.count = Mock(return_value=0)
            tables = {
                "SaaS Module": [_Dict(name="accounts", module_name="Reckon Accounts"),
                                _Dict(name="distribution", module_name="Distribution SaaS")],
                "SaaS Plan": [_Dict(name="Acc Pro", saas_module="accounts")],
                "SaaS Registration": [_Dict(name="REG-1", saas_module="distribution")],
                "SaaS Payment": [_Dict(name="PAY-1", subscription="SUB-1")],
                "SaaS Subscription": [_sub(name="SUB-1", saas_module="accounts", status="Trial",
                                           trial_end_date="2026-10-30")],
                "Tenant Provisioning Job": [],
            }

            def get_all(doctype, **kwargs):
                if doctype == "SaaS Module" and kwargs.get("fields") == ["name", "module_name"]:
                    return tables[doctype]
                rows = [_Dict(row) for row in tables[doctype]]
                if kwargs.get("pluck"):
                    return [row.get(kwargs["pluck"]) for row in rows]
                return rows

            frappe.get_all.side_effect = get_all
            with patch.object(saas, "is_vendor_user", return_value=True), patch.object(
                saas, "nowdate", return_value=TODAY
            ):
                data = saas.get_vendor_dashboard()
        self.assertEqual(data["plans"][0]["module_name"], "Reckon Accounts")
        self.assertEqual(data["registrations"][0]["module_name"], "Distribution SaaS")
        self.assertEqual(data["subscriptions"][0]["module_name"], "Reckon Accounts")
        self.assertEqual(data["subscriptions"][0]["billing"]["state"], "trial")
        self.assertEqual((data["pending_payments"][0]["saas_module"], data["pending_payments"][0]["module_name"]),
                         ("accounts", "Reckon Accounts"))

    def test_admin_and_desk_dashboards_show_module_labels(self):
        admin = (APP / "www/reckon_saas_admin.html").read_text(encoding="utf-8")
        desk = (APP / "saas_platform/page/saas_dashboard/saas_dashboard.js").read_text(encoding="utf-8")
        self.assertNotIn("saas_module or \"\"", admin)
        self.assertGreaterEqual(admin.count(".module_name|e"), 4)  # plans, payments, registrations, subscriptions
        self.assertNotIn("esc(r.saas_module)", desk)
        self.assertNotIn("esc(s.saas_module)", desk)
        self.assertGreaterEqual(desk.count("moduleCell("), 5)


class SignupModuleTests(unittest.TestCase):
    def test_module_signup_shows_only_that_modules_plans_with_trial(self):
        modules = [_Dict(name="accounts", module_name="Reckon Accounts", description="", features=""),
                   _Dict(name="distribution", module_name="Distribution SaaS", description="", features="")]
        plans = [_Dict(name="Acc Pro", plan_name="Acc Pro", saas_module="accounts", price=500, currency="BDT",
                       billing_cycle="Monthly", trial_days=14),
                 _Dict(name="Dist Basic", plan_name="Dist Basic", saas_module="distribution", price=900,
                       currency="BDT", billing_cycle="Monthly", trial_days=0)]
        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            frappe.form_dict = _Dict(module="accounts")
            frappe.local.form_dict = frappe.form_dict
            frappe.local.request = SimpleNamespace(cookies={}, headers={})

            def get_all(doctype, **kwargs):
                if doctype == "SaaS Module":
                    return modules
                wanted = (kwargs.get("filters") or {}).get("saas_module")
                return [p for p in plans if not wanted or p.saas_module == wanted]

            frappe.get_all.side_effect = get_all
            context = _Dict()
            with patch.object(page, "get_recaptcha_site_key", return_value=None):
                page.get_context(context)
        self.assertEqual([card["name"] for card in context.plan_cards], ["Acc Pro"])
        self.assertEqual(context.plan_cards[0]["module_name"], "Reckon Accounts")
        self.assertEqual(context.plan_cards[0]["trial"], "14-day free trial")
        self.assertEqual(context.selected_module, "accounts")

    def test_signup_refuses_a_plan_from_another_module(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.db.get_value.side_effect = lambda doctype, *args, **kwargs: (
                _Dict(enabled=1, saas_module="distribution") if doctype == "SaaS Plan" else 1
            )
            with self.assertRaises(saas.SignupValidationError):
                saas.create_registration(business_name="Co", owner_email="o@example.com", owner_name="O",
                                         plan="Dist Basic", saas_module="accounts")
            frappe.get_doc.assert_not_called()

    def test_subscription_page_lists_each_module_with_its_billing(self):
        with platform_modules("www.reckonerp_subscription") as (frappe, (page,)):
            card = page.subscription_card({
                "name": "SUB-1", "saas_module": "accounts", "module_name": "Reckon Accounts", "status": "Grace",
                "billing": {"state": "grace", "access": True, "dues": True, "grace_end": D("2026-10-22")},
                "landing_route": "/app/reckon-accounts",
                "payment": {"status": "Pending Verification", "gateway_reference": "TRX1"},
            })
        self.assertEqual((card["module_name"], card["state_label"]), ("Reckon Accounts", "Payment due"))
        self.assertIn("2026-10-22", card["detail"])
        self.assertTrue(card["can_pay"] and card["payment_pending"] and card["dues"])


class SignupCsrfTests(unittest.TestCase):
    """POST /api/method/...public_signup returned 400 "Invalid Request".

    Frappe writes the token as ``frappe.csrf_token``; the page sent
    ``window.csrf_token``, which is never set, so any browser with a saved
    session token (a signed-in user) failed the CSRF check.
    """

    def _script(self, name):
        return (APP / "www" / name).read_text(encoding="utf-8")

    def test_signup_and_subscription_pages_send_frappe_csrf_token(self):
        for name in ("reckonerp_signup.html", "reckonerp_subscription.html"):
            with self.subTest(page=name):
                html = self._script(name)
                self.assertNotRegex(html, r"window\.csrf_token\s*\|\|")
                self.assertIn("window.frappe.csrf_token", html)
                self.assertRegex(html, r'"X-Frappe-CSRF-Token":\s*csrfToken\(\)')

    def test_token_is_read_when_the_request_is_sent(self):
        # base.html writes frappe.csrf_token after the page's own scripts, so the
        # page must not copy it into a variable while it loads.
        html = self._script("reckonerp_signup.html")
        body = re.search(r"function csrfToken\(\) \{(.*?)\n    \}", html, re.S)
        self.assertIsNotNone(body)
        self.assertIn("window.frappe.csrf_token", body.group(1))
        self.assertEqual(html.count("window.frappe.csrf_token"), html.count("window.frappe.csrf_token", *body.span(1)))

    def test_public_signup_accepts_the_module_from_the_form(self):
        with platform_modules("saas") as (_frappe, (saas,)):
            registration = Mock(name="REG-1", phone_verification_required=0)
            with patch.object(saas, "verify_signup_captcha"), patch.object(
                saas, "create_registration", return_value=registration
            ) as create, patch.object(saas, "send_registration_verification"):
                result = saas.public_signup(business_name="Co", owner_email="o@example.com", owner_name="O",
                                            plan="Acc Pro", module="accounts")
        self.assertEqual(create.call_args.kwargs["saas_module"], "accounts")
        self.assertTrue(result["ok"])

    def test_signup_endpoints_stay_open_to_guests_through_the_gate(self):
        with platform_modules("saas_gate") as (_frappe, (gate,)):
            self.assertIn("reckon_saas_platform.saas.public_signup", gate.EXEMPT_METHODS)
        source = (APP / "saas.py").read_text(encoding="utf-8")
        self.assertRegex(source, r'@frappe\.whitelist\(allow_guest=True, methods=\["POST"\]\)\n'
                                 r"@rate_limit\([^)]*\)\ndef public_signup\(")


if __name__ == "__main__":
    unittest.main()
