"""Adding another module from the tenant Subscription page, and what a verified payment refreshes."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock

from frappe_stub import _Dict, platform_modules

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"
MODS = ("marketing", "module_registry", "saas", "tenant_security", "invoices")


class Env:
    def __init__(self, test, held=(), role="Company Admin", plan_enabled=1, module_enabled=1, installed=True):
        ctx = platform_modules(*MODS)
        self.frappe, mods = ctx.__enter__()
        test.addCleanup(ctx.__exit__, None, None, None)
        self.by = dict(zip(MODS, mods, strict=True))
        saas, frappe = self.by["saas"], self.frappe
        frappe.session = _Dict(user="owner@example.test")
        frappe.utils.nowdate = Mock(return_value="2026-11-08")
        frappe.db.savepoint = Mock()
        frappe.enqueue = Mock()
        self.rows = [_Dict(saas_module=k, covered_modules="", status="Active") for k in held]
        frappe.get_all = Mock(side_effect=self.get_all)
        self.created = []
        frappe.get_doc = Mock(side_effect=self.get_doc)
        self.values = {
            ("Tenant User Assignment", "role_profile"): role,
            ("SaaS Module", "enabled"): module_enabled,
        }
        self.plan_row = _Dict(name="HRMS Basic", enabled=plan_enabled, saas_module="hrms", billing_cycle="Monthly")
        frappe.db.get_value = Mock(side_effect=self.get_value)
        saas.resolve_tenant = Mock(return_value=_Dict(user="owner@example.test", company="Acme Ltd"))
        saas.get_module_definition = Mock(return_value={"key": "hrms"} if installed else None)
        saas.get_seed_handlers = Mock(return_value=["reckon_hrms.seed.run_hrms_seed"])
        saas.module_label = Mock(return_value="Reckon HRMS")
        saas.invalidate_operational_access_cache = Mock()
        self.handler = Mock()
        frappe.get_attr = Mock(return_value=self.handler)
        self.reconciled = []
        team = type("Team", (), {"reconcile_user": lambda user: self.reconciled.append(user)})
        import sys

        sys.modules["reckon_saas_platform.team"] = team  # the real one needs a database

    def get_all(self, doctype, **kw):
        if doctype == "SaaS Subscription":
            return self.rows
        if doctype == "Tenant User Assignment":
            return ["owner@example.test", "staff@example.test"]
        return []

    def get_doc(self, arg, name=None):
        if isinstance(arg, dict):
            doc = _Dict(arg)
            doc.name = f"{arg['doctype'][:3].upper()}-1"
            doc.insert = Mock(side_effect=lambda ignore_permissions=False: self.created.append(doc) or doc)
            return doc
        return _Dict(name=name, saas_module="hrms", plan_version="1", price=900, currency="BDT", trial_days=0, grace_days=2)

    def get_value(self, doctype, filters, fields=None, **kw):
        if doctype == "SaaS Plan":
            return self.plan_row
        return self.values.get((doctype, fields if isinstance(fields, str) else None))


class AddModuleTests(unittest.TestCase):
    def test_modules_a_company_holds_include_covered_ones_and_ignore_closed_subscriptions(self):
        env = Env(self)
        env.rows = [
            _Dict(saas_module="distribution", covered_modules="accounts\ncrm", status="Active"),
            _Dict(saas_module="hrms", covered_modules="", status="Cancelled"),
            _Dict(saas_module="sales_agent", covered_modules="", status="Trial"),
        ]
        self.assertEqual(env.by["saas"]._open_module_keys("Acme Ltd"), {"distribution", "accounts", "crm", "sales_agent"})

    def test_only_modules_with_plans_that_the_company_lacks_are_offered(self):
        env = Env(self, held=("distribution",))
        modules = [
            {"key": "distribution", "name": "D", "tagline": "t", "plans": [1], "url": "/modules/distribution"},
            {"key": "hrms", "name": "HRMS", "tagline": "t", "plans": [{"name": "HRMS Basic"}], "url": "/modules/hrms"},
            {"key": "crm", "name": "CRM", "tagline": "t", "plans": [], "url": "/modules/crm"},
        ]
        env.by["marketing"].get_modules = Mock(return_value=modules)
        offered = env.by["saas"].get_addable_modules("Acme Ltd")
        self.assertEqual([m["key"] for m in offered], ["hrms"])

    def test_subscribing_creates_a_subscription_payment_seed_roles_and_an_invoice(self):
        env = Env(self)
        saas = env.by["saas"]
        saas._create_registration_subscription = Mock(return_value=_Dict(name="SUB-9", status="Pending"))
        result = saas.add_module_subscription("HRMS Basic")
        self.assertTrue(result["ok"])
        self.assertEqual(result["subscription"], "SUB-9")
        args = saas._create_registration_subscription.call_args.args
        self.assertEqual((args[0].billing_cycle, args[2], args[3]), ("Monthly", "Acme Ltd", "owner@example.test"))
        payment = env.created[0]
        self.assertEqual((payment["doctype"], payment["subscription"], payment["company"], payment["status"], payment["amount"]), ("SaaS Payment", "SUB-9", "Acme Ltd", "Pending Verification", 900))
        env.handler.assert_called_once_with(company="Acme Ltd", seed_version=saas.CURRENT_SEED_VERSION)
        self.assertEqual(env.reconciled, ["owner@example.test", "staff@example.test"])
        saas.invalidate_operational_access_cache.assert_called_with("Acme Ltd")
        enqueued = env.frappe.enqueue.call_args
        self.assertEqual(enqueued.args[0], "reckon_saas_platform.invoices.issue_and_send")
        self.assertEqual(enqueued.kwargs["subscription"], "SUB-9")
        self.assertTrue(enqueued.kwargs["enqueue_after_commit"])
        self.assertIn("Pay the invoice", result["message"])

    def test_a_trial_module_says_it_opens_now(self):
        env = Env(self)
        saas = env.by["saas"]
        saas._create_registration_subscription = Mock(return_value=_Dict(name="SUB-9", status="Trial"))
        self.assertIn("free trial", saas.add_module_subscription("HRMS Basic")["message"])

    def test_only_the_company_admin_can_add_a_module(self):
        env = Env(self, role="Company Manager")
        with self.assertRaises(env.frappe.PermissionError):
            env.by["saas"].add_module_subscription("HRMS Basic")
        env.frappe.enqueue.assert_not_called()

    def test_bad_plans_unavailable_modules_and_repeats_are_refused(self):
        for kwargs, plan in (
            ({"plan_enabled": 0}, "HRMS Basic"),
            ({"module_enabled": 0}, "HRMS Basic"),
            ({"installed": False}, "HRMS Basic"),
            ({"held": ("hrms",)}, "HRMS Basic"),
        ):
            env = Env(self, **kwargs)
            env.by["saas"]._create_registration_subscription = Mock()
            with self.assertRaises(env.by["saas"].SignupValidationError):
                env.by["saas"].add_module_subscription(plan)
            env.by["saas"]._create_registration_subscription.assert_not_called()
        env = Env(self)
        for bad in ("", None, 5):
            with self.assertRaises(env.by["saas"].SignupValidationError):
                env.by["saas"].add_module_subscription(bad)

    def test_a_failure_while_creating_rolls_back_and_a_seed_failure_keeps_the_subscription(self):
        env = Env(self)
        saas = env.by["saas"]
        saas._rollback_to = Mock()
        saas._create_registration_subscription = Mock(side_effect=RuntimeError("db"))
        with self.assertRaises(RuntimeError):
            saas.add_module_subscription("HRMS Basic")
        saas._rollback_to.assert_called_once()
        env.frappe.enqueue.assert_not_called()
        env2 = Env(self)
        saas2 = env2.by["saas"]
        saas2._rollback_to = Mock()
        saas2._create_registration_subscription = Mock(return_value=_Dict(name="SUB-9", status="Pending"))
        env2.handler.side_effect = RuntimeError("seed broke")
        result = saas2.add_module_subscription("HRMS Basic")
        self.assertTrue(result["ok"])
        self.assertFalse(result["seeded"])  # logged, and the invoice still goes out
        env2.frappe.enqueue.assert_called_once()

    def test_a_verified_payment_refreshes_the_companys_roles_without_undoing_the_payment(self):
        env = Env(self)
        saas = env.by["saas"]
        saas._after_payment(_Dict(name="SUB-9", company="Acme Ltd"))
        self.assertEqual(env.reconciled, ["owner@example.test", "staff@example.test"])
        saas._reconcile_company_users = Mock(side_effect=RuntimeError("roles"))
        saas._after_payment(_Dict(name="SUB-9", company="Acme Ltd"))
        env.frappe.log_error.assert_called()
        source = (PKG / "saas.py").read_text(encoding="utf-8")
        self.assertIn("_settle_invoice(subscription.name, payment_doc.name)\n    _after_payment(subscription)", source)


class SubscriptionPageTests(unittest.TestCase):
    def test_page_shows_invoices_payment_instructions_and_the_add_module_form(self):
        html = (PKG / "www" / "reckonerp_subscription.html").read_text(encoding="utf-8")
        for needle in ("How to pay", "payment_instructions", "{% for inv in invoices %}", 'id="add-module"', "data-add-module", "can_add_modules", "sub.invoice", "add_module_subscription"):
            self.assertIn(needle, html, needle)
        page = (PKG / "www" / "reckonerp_subscription.py").read_text(encoding="utf-8")
        for needle in ("_safely(", "get_addable_modules", "invoices_for_company", "_is_company_admin"):
            self.assertIn(needle, page, needle)

    def test_the_template_parses(self):
        try:
            import jinja2
        except ModuleNotFoundError:
            self.skipTest("jinja2 is not installed")
        jinja2.Environment().parse((PKG / "www" / "reckonerp_subscription.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
