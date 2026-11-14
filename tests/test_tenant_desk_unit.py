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
    def test_overview_counts_people_and_reports_the_plan_limit(self):
        with platform_modules("team", "saas", "tenant_security") as (frappe, (team, saas, security)):
            frappe.get_all = Mock(return_value=[
                _Dict(user="a@x.test", role_profile="Company Admin", module_role=""),
                _Dict(user="b@x.test", role_profile="Company Manager", module_role="HR User"),
            ])
            frappe.db.get_value = Mock(return_value="Person")
            with patch.object(saas, "_open_module_keys", return_value={"hrms"}), \
                    patch.object(security, "company_user_limit", return_value=5), \
                    patch.object(team, "tenant_modules", return_value=[
                        {"key": "hrms", "tenant_role_map": {"HR User": "x", "HR Manager": "y"}},
                        {"key": "crm", "tenant_role_map": {"Sales User": "z"}},
                    ]):
                overview = team.team_overview("Acme")
        self.assertEqual((overview["used"], overview["limit"]), (2, 5))
        self.assertEqual(overview["module_roles"], ["HR Manager", "HR User"])  # only roles of modules the company holds
        self.assertEqual(overview["profiles"], ["Company Manager", "Company Admin"])

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
