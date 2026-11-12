"""Plan user limits: the rule, the refusal, and the Users row of the plan comparison."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from frappe_stub import platform_modules
from test_agent_and_speed_unit import plan

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"


class UserLimitRuleTests(unittest.TestCase):
    def rule(self, limits):
        with platform_modules("entitlements") as (_f, (entitlements,)):
            return entitlements.effective_user_limit(limits)

    def test_no_plan_or_a_blank_limit_means_unlimited(self):
        self.assertIsNone(self.rule([]))
        self.assertIsNone(self.rule([None]))
        self.assertIsNone(self.rule([0]))
        self.assertIsNone(self.rule([5, 0]))  # one unlimited plan frees the company

    def test_the_highest_limit_of_several_modules_applies(self):
        self.assertEqual(self.rule([5, 20, 10]), 20)
        self.assertEqual(self.rule([5]), 5)


class UserLimitEnforcementTests(unittest.TestCase):
    def check(self, limit, people, user="new@x.test"):
        with platform_modules("tenant_security") as (frappe, (security,)):
            frappe.get_all = Mock(side_effect=lambda doctype, **kw: ["PLAN"] if doctype == "SaaS Subscription" else list(people))
            frappe.db.get_value = Mock(return_value=limit)
            frappe.throw = Mock(side_effect=Exception("limit"))
            security.assert_user_limit_allows("Acme", user)

    def test_a_new_person_is_refused_at_the_limit(self):
        with self.assertRaises(Exception) as ctx:
            self.check(2, ["a@x.test", "b@x.test"])
        self.assertEqual(str(ctx.exception), "limit")

    def test_a_new_person_fits_below_the_limit(self):
        self.check(3, ["a@x.test", "b@x.test"])

    def test_someone_already_counted_is_never_refused(self):
        self.check(2, ["a@x.test", "b@x.test"], user="a@x.test")

    def test_blank_limit_is_unlimited(self):
        self.check(0, [f"u{i}@x.test" for i in range(500)])


class UserLimitWiringTests(unittest.TestCase):
    def test_every_way_of_adding_a_person_checks_the_limit(self):
        assignment = (PKG / "saas_platform" / "doctype" / "tenant_user_assignment" / "tenant_user_assignment.py").read_text(encoding="utf-8")
        self.assertIn("_validate_plan_user_limit", assignment)
        team = (PKG / "team.py").read_text(encoding="utf-8")
        self.assertLess(team.index("assert_user_limit_allows(company, email)"), team.index('"doctype": "User", "email": email'))

    def test_plan_has_a_maximum_users_field(self):
        data = json.loads((PKG / "saas_platform" / "doctype" / "saas_plan" / "saas_plan.json").read_text(encoding="utf-8"))
        field = next(f for f in data["fields"] if f["fieldname"] == "max_users")
        self.assertEqual(field["fieldtype"], "Int")
        self.assertIn("max_users", data["field_order"])

    def test_comparison_starts_with_a_users_row_from_the_plan_limit(self):
        with platform_modules("marketing") as (_f, (marketing,)):
            a = {**plan("A", 1, "BDT"), "max_users": 5, "comparison": [{"feature": "X", "included": True, "value": ""}]}
            b = {**plan("B", 2, "BDT"), "max_users": 0, "comparison": [{"feature": "X", "included": True, "value": ""}]}
            rows = marketing.comparison_matrix([a, b])["rows"]
        self.assertEqual([r["feature"] for r in rows], ["Users", "File storage", "X"])
        self.assertEqual([c["users"] for c in rows[0]["cells"]], [5, 0])


class FileStorageTests(unittest.TestCase):
    def run_hook(self, limit, used_bytes, size, company="Acme"):
        with platform_modules("plan_limits") as (frappe, (limits,)):
            frappe.get_all = Mock(return_value=["PLAN"])
            frappe.db.get_value = Mock(return_value=limit)
            frappe.db.sql = Mock(return_value=[[used_bytes]])
            frappe.throw = Mock(side_effect=Exception("full"))
            frappe.log_error = Mock()
            limits.file_company = Mock(return_value=company)
            doc = Mock(**{"get.side_effect": lambda k, d=None: {"file_size": size}.get(k, d)})
            limits.check_file_storage(doc)
            return doc, frappe

    def test_an_upload_past_the_plan_storage_is_refused(self):
        with self.assertRaises(Exception) as ctx:
            self.run_hook(limit=1, used_bytes=900_000, size=200_000)  # 1 MB plan, 0.9 MB used, 0.2 MB new
        self.assertEqual(str(ctx.exception), "full")

    def test_an_upload_within_the_storage_is_stamped_with_its_company(self):
        doc, _frappe = self.run_hook(limit=1, used_bytes=100, size=200_000)
        doc.set.assert_called_with("reckon_company", "Acme")

    def test_blank_storage_is_unlimited_and_files_without_a_company_are_not_counted(self):
        self.run_hook(limit=0, used_bytes=10**12, size=10**9)
        doc, _frappe = self.run_hook(limit=1, used_bytes=0, size=10**9, company=None)
        doc.set.assert_not_called()

    def test_a_broken_check_never_blocks_an_upload(self):
        with platform_modules("plan_limits") as (frappe, (limits,)):
            frappe.log_error = Mock()
            limits.file_company = Mock(side_effect=RuntimeError("boom"))
            limits.check_file_storage(Mock())
            frappe.log_error.assert_called_once()

    def test_wiring_and_the_plan_field(self):
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"before_insert": "reckon_saas_platform.plan_limits.check_file_storage"', hooks)
        self.assertIn("ensure_file_storage_tracking()", (PKG / "install.py").read_text(encoding="utf-8"))
        data = json.loads((PKG / "saas_platform" / "doctype" / "saas_plan" / "saas_plan.json").read_text(encoding="utf-8"))
        self.assertEqual(next(f for f in data["fields"] if f["fieldname"] == "max_storage_mb")["fieldtype"], "Int")

    def test_comparison_shows_file_storage_after_users(self):
        with platform_modules("marketing") as (_f, (marketing,)):
            a = {**plan("A", 1, "BDT"), "max_storage_mb": 500, "comparison": [{"feature": "X", "included": True, "value": ""}]}
            b = {**plan("B", 2, "BDT"), "max_storage_mb": 2048, "comparison": [{"feature": "X", "included": True, "value": ""}]}
            c = {**plan("C", 3, "BDT"), "max_storage_mb": 0, "comparison": [{"feature": "X", "included": True, "value": ""}]}
            rows = marketing.comparison_matrix([a, b, c])["rows"]
        self.assertEqual([r["feature"] for r in rows], ["Users", "File storage", "X"])
        self.assertEqual([x["text"] for x in rows[1]["cells"]], ["500 MB", "2 GB", ""])


class BillingCycleAndPaddlePriceTests(unittest.TestCase):
    def test_plans_group_by_currency_then_cycle_with_bdt_and_monthly_first(self):
        with platform_modules("marketing") as (_f, (marketing,)):
            usd_y = {**plan("Pro Y", 100, "USD"), "cycle": "Yearly"}
            sets = marketing.plan_sets([usd_y, plan("Pro", 10, "USD"), plan("Basic", 500, "BDT")])
        self.assertEqual([(s["cur"], s["cycle"]) for s in sets], [("BDT", "Monthly"), ("USD", "Monthly"), ("USD", "Yearly")])

    def paddle(self, **settings):
        from frappe_stub import _Dict

        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.get_cached_doc = Mock(return_value=_Dict(settings))
            return marketing.paddle_public()

    def test_paddle_is_public_only_when_on_with_a_matching_token_and_environment(self):
        token = "test_" + "a" * 27
        self.assertEqual(self.paddle(paddle_enabled=1, paddle_environment="Sandbox", paddle_client_token=token), {"environment": "sandbox", "client_token": token})
        self.assertIsNone(self.paddle(paddle_enabled=0, paddle_environment="Sandbox", paddle_client_token=token))
        self.assertIsNone(self.paddle(paddle_enabled=1, paddle_environment="", paddle_client_token=token))  # never guess the environment
        self.assertIsNone(self.paddle(paddle_enabled=1, paddle_environment="Production", paddle_client_token=token))  # sandbox token on live
        self.assertIsNone(self.paddle(paddle_enabled=1, paddle_environment="Sandbox", paddle_client_token="<script>"))

    def test_templates_carry_the_cycle_the_paddle_price_and_the_chosen_plan(self):
        macros = (PKG / "templates" / "marketing" / "macros.html").read_text(encoding="utf-8")
        self.assertEqual(macros.count('data-cycle="{{ set.cycle|e }}"'), 2)
        self.assertEqual(macros.count('data-paddle-price="{{ plan.paddle_price|e }}"'), 2)
        self.assertEqual(macros.count('"&plan=" ~ plan.id|urlencode'), 2)
        script = (PKG / "templates" / "marketing" / "paddle_prices.html").read_text(encoding="utf-8")
        self.assertIn("{% if paddle_public %}", script)
        self.assertIn("formattedTotals.total", script)
        self.assertNotIn("Intl.NumberFormat", script)  # Paddle's own formatted totals are shown as they come
        self.assertNotIn("customerIpAddress", script)
        self.assertNotIn("api_key", script)
        signup = (PKG / "www" / "reckonerp_signup.html").read_text(encoding="utf-8")
        self.assertIn('new URLSearchParams(window.location.search).get("plan")', signup)


class SubscriptionMenuTests(unittest.TestCase):
    def test_migrate_adds_the_subscription_menu_row_once(self):
        from frappe_stub import _Dict

        with platform_modules("install") as (frappe, (install,)):
            settings = Mock()
            settings.get = Mock(return_value=[])
            frappe.db.exists = Mock(return_value=True)
            frappe.get_single = Mock(return_value=settings)
            frappe.get_meta = Mock(return_value=Mock(has_field=Mock(return_value=True)))
            install.ensure_subscription_menu()
            field, row = settings.append.call_args[0]
            self.assertEqual((field, row["route"], row["item_type"], row["item_label"]), ("settings_dropdown", "/reckonerp-subscription", "Route", "Subscription"))
            self.assertIn("Reckon Vendor Superuser", row["condition"])
            settings.save.assert_called_once()
            # already there: nothing is added again
            again = Mock()
            again.get = Mock(return_value=[_Dict(route="/reckonerp-subscription")])
            frappe.get_single = Mock(return_value=again)
            install.ensure_subscription_menu()
            again.append.assert_not_called()
        self.assertIn("ensure_subscription_menu()", (PKG / "install.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
