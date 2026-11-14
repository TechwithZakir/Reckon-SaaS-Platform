"""What a tenant sees and can reach in the Desk: its own apps, Subscription, Team; and payment clean-up."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from frappe_stub import _Dict, platform_modules

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"
MODULES = [
    {"key": "accounts", "app": "reckon_accounts_saas"},
    {"key": "crm", "app": "reckon_crm"},
    {"key": "hrms", "app": "reckon_hrms"},
]


class TenantAppsTests(unittest.TestCase):
    def allowed(self, held, companies=("Acme",), bypass=False):
        with platform_modules("desk_apps", "saas") as (_frappe, (desk_apps, saas)):
            with patch.object(desk_apps, "get_saas_modules", return_value=[_Dict(m) for m in MODULES]), \
                    patch.object(desk_apps, "get_user_companies", return_value=list(companies)), \
                    patch.object(desk_apps, "user_can_bypass_tenant", return_value=bypass), \
                    patch.object(saas, "_open_module_keys", return_value=set(held)):
                return desk_apps.allowed_apps_for_user("u@x.test")

    def test_a_tenant_sees_only_the_apps_of_its_modules(self):
        self.assertEqual(self.allowed({"accounts"}), {"reckon_accounts_saas"})
        self.assertEqual(self.allowed({"accounts", "crm"}), {"reckon_accounts_saas", "reckon_crm"})
        self.assertEqual(self.allowed(set()), set())  # nothing held: nothing offered

    def test_vendor_staff_and_users_without_a_company_are_not_restricted(self):
        self.assertIsNone(self.allowed({"accounts"}, bypass=True))
        self.assertIsNone(self.allowed({"accounts"}, companies=()))

    def test_bootinfo_takes_other_apps_off_the_apps_menu_and_flags_the_admin(self):
        with platform_modules("desk_apps") as (_frappe, (desk_apps,)):
            boot = _Dict(app_data=[
                {"app_name": "erpnext", "on_apps_screen": True, "dock": ["x"]},
                {"app_name": "reckon_accounts_saas", "on_apps_screen": True, "dock": ["y"]},
                {"app_name": "crm", "on_apps_screen": True, "dock": []},
            ])
            with patch.object(desk_apps, "allowed_apps_for_user", return_value={"reckon_accounts_saas"}), \
                    patch.object(desk_apps, "is_company_admin", return_value=True):
                desk_apps.filter_bootinfo(boot)
            self.assertEqual([a["on_apps_screen"] for a in boot["app_data"]], [False, True, False])
            self.assertEqual(boot["app_data"][0]["dock"], ["x"])  # only the menu changes; nothing else is removed
            self.assertTrue(boot["reckon_company_admin"])

            untouched = _Dict(app_data=[{"app_name": "erpnext", "on_apps_screen": True}])
            with patch.object(desk_apps, "allowed_apps_for_user", return_value=None), \
                    patch.object(desk_apps, "is_company_admin", return_value=False):
                desk_apps.filter_bootinfo(untouched)
            self.assertTrue(untouched["app_data"][0]["on_apps_screen"])

    def test_a_broken_filter_never_breaks_the_desk(self):
        with platform_modules("desk_apps") as (frappe, (desk_apps,)):
            frappe.log_error = Mock()
            with patch.object(desk_apps, "is_company_admin", side_effect=RuntimeError("boom")):
                desk_apps.filter_bootinfo(_Dict(app_data=[]))
            frappe.log_error.assert_called_once()

    def test_hooks_wire_the_filter_and_the_team_route(self):
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('extend_bootinfo = "reckon_saas_platform.desk_apps.filter_bootinfo"', hooks)
        self.assertIn('"frappe.apps.get_apps": "reckon_saas_platform.desk_apps.get_apps"', hooks)
        self.assertIn('{"from_route": "/reckonerp-team", "to_route": "reckonerp_team"}', hooks)


class DeskGuardTests(unittest.TestCase):
    def guarded(self, active_keys):
        modules = [
            _Dict(key="accounts", label="Accounts"),
            _Dict(key="hrms", label="Reckon HRMS", desk_guard=True),
            _Dict(key="crm", label="Reckon CRM", desk_guard=True),
        ]
        with platform_modules("desk_module_guard", "saas") as (_frappe, (guard, saas)):
            with patch.object(guard, "get_saas_modules", return_value=modules), \
                    patch.object(guard, "get_user_companies", return_value=["Acme"]), \
                    patch.object(guard, "user_can_bypass_tenant", return_value=False), \
                    patch.object(saas, "is_subscription_active", side_effect=lambda company, key: key in active_keys):
                module = guard.guarded_module_for_user("u@x.test")
        return module.get("key") if module else None

    def test_a_company_with_only_a_guarded_module_is_kept_inside_it(self):
        self.assertEqual(self.guarded({"hrms"}), "hrms")

    def test_a_second_module_lifts_the_guard_even_when_it_is_not_a_guarded_one(self):
        # Accounts plus HRMS used to be shut inside HRMS: "Your subscription covers Reckon HRMS only."
        self.assertIsNone(self.guarded({"accounts", "hrms"}))
        self.assertIsNone(self.guarded({"hrms", "crm"}))

    def test_an_unguarded_module_alone_is_not_restricted_here(self):
        self.assertIsNone(self.guarded({"accounts"}))
        self.assertIsNone(self.guarded(set()))


class SignupStartModeTests(unittest.TestCase):
    def subscription(self, start_mode, trial_days=15):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.get_doc = Mock(side_effect=lambda values: Mock(insert=Mock(return_value=values)))
            frappe.utils.nowdate = Mock(return_value="2026-11-15")
            saas.nowdate = Mock(return_value="2026-11-15")
            doc = _Dict(name="REG-1", billing_cycle="Monthly", start_mode=start_mode, saas_module="crm")
            plan = _Dict(name="CRM Basic (USD)", saas_module="crm", plan_version="1", price=5, currency="USD", trial_days=trial_days, grace_days=5)
            plan.get = lambda key, default=None: plan[key] if key in plan else default
            return saas._create_registration_subscription(doc, plan, "Acme", "a@x.test")

    def test_free_trial_opens_a_trial_and_pay_now_has_none(self):
        trial = self.subscription("Free Trial")
        self.assertEqual((trial["status"], trial["trial_end_date"] is not None), ("Trial", True))
        paying = self.subscription("Pay Now")
        self.assertEqual((paying["status"], paying["trial_end_date"]), ("Pending", None))

    def test_the_form_offers_the_choice_only_for_a_plan_with_a_trial_and_the_backend_reads_it(self):
        html = (PKG / "www" / "reckonerp_signup.html").read_text(encoding="utf-8")
        for needle in ('name="start_mode" value="trial"', 'name="start_mode" value="pay"', "data-trial-days=", 'data-label-pay="{{ t.submit_pay|e }}"'):
            self.assertIn(needle, html)
        saas = (PKG / "saas.py").read_text(encoding="utf-8")
        self.assertIn('"start_mode": "Pay Now" if', saas)
        self.assertIn("(plan_row.billing_cycle or billing_cycle)", saas)  # a Yearly plan bills yearly
        import json

        data = json.loads((PKG / "saas_platform" / "doctype" / "saas_registration" / "saas_registration.json").read_text(encoding="utf-8"))
        self.assertEqual(next(f for f in data["fields"] if f["fieldname"] == "start_mode")["options"].split(chr(10)), ["Free Trial", "Pay Now"])


class AccountAreaTests(unittest.TestCase):
    def test_subscription_and_team_share_one_header_with_tabs(self):
        header = (PKG / "templates" / "account" / "header.html").read_text(encoding="utf-8")
        for needle in ("/reckonerp-subscription", "/reckonerp-team", "aria-current", "/logout"):
            self.assertIn(needle, header)
        for page in ("reckonerp_subscription", "reckonerp_team"):
            html = (PKG / "www" / f"{page}.html").read_text(encoding="utf-8")
            self.assertIn("templates/account/header.html", html)
            self.assertNotIn("<style>", html)  # one stylesheet, the same look as the website
        css = (PKG / "public" / "css" / "saas_portal.css").read_text(encoding="utf-8")
        self.assertIn('data-theme="dark"', css)


class AddModulePlansTests(unittest.TestCase):
    def test_plans_group_by_billing_period_and_tier_with_short_labels(self):
        with platform_modules("saas") as (_frappe, (saas,)):
            plans = [
                {"name": "Standard - Accounts (USD, Yearly)", "cycle": "Yearly"},
                {"name": "Basic - Accounts (USD)", "cycle": "Monthly"},
                {"name": "Enterprise (USD)", "cycle": "Monthly"},
                {"name": "Sales Agent Standard (USD)", "cycle": "Monthly"},
            ]
            groups = saas.plan_cycles(plans)
        self.assertEqual([g["cycle"] for g in groups], ["Monthly", "Yearly"])  # monthly first
        self.assertEqual([p["tier"] for p in groups[0]["plans"]], ["Basic", "Enterprise", "Standard"])
        self.assertEqual(groups[1]["plans"][0]["tier"], "Standard")

    def test_the_subscription_page_has_tabs_and_a_monthly_yearly_choice_per_module(self):
        html = (PKG / "www" / "reckonerp_subscription.html").read_text(encoding="utf-8")
        for needle in ('data-tab="plans"', 'data-tab="modules"', 'data-panel="setup"', "data-cycle-set=", "data-add-module=", "mod.cycles"):
            self.assertIn(needle, html)


class TenantMenuTests(unittest.TestCase):
    def test_migrate_adds_subscription_and_team_once(self):
        with platform_modules("install") as (frappe, (install,)):
            settings = Mock()
            settings.get = Mock(return_value=[])
            frappe.db.exists = Mock(return_value=True)
            frappe.get_single = Mock(return_value=settings)
            frappe.get_meta = Mock(return_value=Mock(has_field=Mock(return_value=True)))
            install.ensure_subscription_menu()
            rows = [call.args[1] for call in settings.append.call_args_list]
            self.assertEqual([(r["item_label"], r["route"]) for r in rows], [("Subscription", "/reckonerp-subscription"), ("Team", "/reckonerp-team")])
            self.assertIn("Reckon Vendor Superuser", rows[0]["condition"])
            self.assertIn("frappe.boot.reckon_company_admin", rows[1]["condition"])  # Team is for the company admin
            settings.save.assert_called_once()

            # a site that already has Subscription gets only Team; one that has both gets nothing
            partial = Mock()
            partial.get = Mock(return_value=[_Dict(route="/reckonerp-subscription")])
            frappe.get_single = Mock(return_value=partial)
            install.ensure_subscription_menu()
            self.assertEqual([c.args[1]["route"] for c in partial.append.call_args_list], ["/reckonerp-team"])
            done = Mock()
            done.get = Mock(return_value=[_Dict(route="/reckonerp-subscription"), _Dict(route="/reckonerp-team")])
            frappe.get_single = Mock(return_value=done)
            install.ensure_subscription_menu()
            done.append.assert_not_called()
            done.save.assert_not_called()


class TeamPageTests(unittest.TestCase):
    def overview(self, assignments, access_rows):
        with platform_modules("team", "saas", "tenant_security") as (frappe, (team, saas, security)):
            def get_all(doctype, **kw):
                if doctype == "Tenant Module Access":
                    return [_Dict(r) for r in access_rows.get(kw["filters"]["parent"], [])]
                return [_Dict(a) for a in assignments]

            frappe.get_all = Mock(side_effect=get_all)
            frappe.db.get_value = Mock(return_value="Person")
            modules = [{"key": "accounts", "name": "Accounts", "choices": ["Manager", "Accountant"]}, {"key": "hrms", "name": "HRMS", "choices": ["HR Manager"]}]
            with patch.object(security, "company_user_limit", return_value=5), patch.object(team, "company_modules", return_value=modules):
                return team.team_overview("Acme")

    def test_overview_lists_each_persons_modules_and_roles_and_the_plan_limit(self):
        overview = self.overview(
            [
                dict(name="TUA-1", user="a@x.test", role_profile="Company Admin", module_role=""),
                dict(name="TUA-2", user="b@x.test", role_profile="Company Manager", module_role=""),
                dict(name="TUA-3", user="c@x.test", role_profile="Company Manager", module_role=""),
            ],
            {"TUA-3": [dict(module="accounts", role_profile="Accountant", module_role="")]},
        )
        self.assertEqual((overview["used"], overview["limit"]), (3, 5))
        by_user = {m["user"]: m["access"] for m in overview["members"]}
        self.assertEqual(by_user["a@x.test"], {"accounts": "Admin", "hrms": "Admin"})
        self.assertEqual(by_user["b@x.test"], {"accounts": "All access", "hrms": "All access"})  # no module list: as before
        self.assertEqual(by_user["c@x.test"], {"accounts": "Accountant"})  # only the module they were given

    def test_a_persons_module_and_role_resolve_from_the_catalog_not_from_the_browser(self):
        modules = [_Dict(key="accounts"), _Dict(key="hrms")]
        with platform_modules("team") as (frappe, (team,)):
            frappe.throw = Mock(side_effect=ValueError("refused"))
            with patch.object(team, "get_saas_modules", return_value=modules),                     patch.object(team, "company_modules", return_value=[{"key": "accounts"}, {"key": "hrms"}]):
                rows = team.resolve_access("Acme", [{"module": "accounts", "choice": "Accountant"}, {"module": "hrms", "choice": "HR Manager"}, {"module": "accounts", "choice": "Manager"}])
                self.assertEqual(rows, [
                    {"module": "accounts", "role_profile": "Accountant", "module_role": ""},
                    {"module": "hrms", "role_profile": "Company Manager", "module_role": "HR Manager"},
                ])  # a repeated module counts once
                for bad in ([{"module": "crm", "choice": "Manager"}], [{"module": "accounts", "choice": "Owner"}], []):
                    with self.assertRaisesRegex(ValueError, "refused"):
                        team.resolve_access("Acme", bad)

    def test_module_profile_gives_each_app_the_persons_role_in_its_module(self):
        with platform_modules("team") as (frappe, (team,)):
            frappe.db.get_value = Mock(return_value="TUA-1")
            frappe.get_all = Mock(return_value=[_Dict(module="accounts", role_profile="Accountant", module_role="")])
            self.assertEqual(team.module_profile("u@x.test", "Acme", "accounts", "Company Manager"), {"role_profile": "Accountant", "module_role": ""})
            self.assertIsNone(team.module_profile("u@x.test", "Acme", "crm", "Company Manager"))  # not given crm
            self.assertEqual(team.module_profile("u@x.test", "Acme", "crm", "Company Admin")["role_profile"], "Company Admin")  # admin: everything
            frappe.get_all = Mock(return_value=[])
            self.assertEqual(team.module_profile("u@x.test", "Acme", "crm", "Company Manager")["role_profile"], "Company Manager")  # no list: as before

    def test_page_is_for_the_company_admin_and_never_trusts_the_browser_for_the_company(self):
        code = (PKG / "www" / "reckonerp_team.py").read_text(encoding="utf-8")
        self.assertIn("team._admin_company(frappe.session.user)", code)
        self.assertIn('frappe.session.user == "Guest"', code)
        html = (PKG / "www" / "reckonerp_team.html").read_text(encoding="utf-8")
        for needle in ('"/api/method/reckon_saas_platform.team." + method', "X-Frappe-CSRF-Token", "data-remove=", "overview.limit and overview.used >= overview.limit"):
            self.assertIn(needle, html)
        self.assertNotIn("company:", html.split("<script>")[1])  # the company comes from the session on the server
        team = (PKG / "team.py").read_text(encoding="utf-8")
        self.assertIn('"send_welcome_email": _welcome_email_flag()', team)


class PaymentCleanupTests(unittest.TestCase):
    def test_card_payment_closes_only_unreported_placeholder_payments(self):
        with platform_modules("paddle") as (frappe, (paddle,)):
            frappe.get_all = Mock(return_value=["PAY-7"])
            paddle._close_placeholder_payments("SUB-1", "PAY-8", "txn_1")
            kwargs = frappe.get_all.call_args.kwargs
            self.assertEqual(kwargs["filters"], {"subscription": "SUB-1", "status": "Pending Verification", "name": ["!=", "PAY-8"]})
            self.assertEqual(kwargs["or_filters"], [["gateway_reference", "is", "not set"], ["gateway_reference", "=", ""]])
            doctype, name, values = frappe.db.set_value.call_args.args
            self.assertEqual((doctype, name, values["status"]), ("SaaS Payment", "PAY-7", "Rejected"))
            self.assertIn("txn_1", values["notes"])
        source = (PKG / "paddle.py").read_text(encoding="utf-8")
        self.assertLess(source.index("verify_payment(payment_name"), source.index("_close_placeholder_payments(row.name"))


class AddModuleCurrencyTests(unittest.TestCase):
    def test_add_a_module_offers_plans_in_the_companys_currency(self):
        with platform_modules("saas", "marketing") as (frappe, (saas, marketing)):
            usd, bdt = [{"name": "CRM Basic (USD)"}], [{"name": "CRM Basic"}]
            modules = [
                {"key": "crm", "name": "CRM", "tagline": "t", "plans": bdt, "plans_by_currency": {"BDT": bdt, "USD": usd}, "url": "/modules/crm"},
                {"key": "hrms", "name": "HRMS", "tagline": "t", "plans": bdt, "plans_by_currency": {"BDT": bdt}, "url": "/modules/hrms"},
                {"key": "accounts", "name": "Accounts", "tagline": "t", "plans": bdt, "plans_by_currency": {"BDT": bdt}, "url": "/a"},
            ]
            frappe.db.get_value = Mock(return_value="USD")
            with patch.object(saas, "_open_module_keys", return_value={"accounts"}), \
                    patch.object(marketing, "get_modules", return_value=modules):
                offered = {m["key"]: m["plans"] for m in saas.get_addable_modules("Acme")}
        self.assertEqual(offered, {"crm": usd, "hrms": bdt})  # USD where the module has it, else its default plans


if __name__ == "__main__":
    unittest.main()
