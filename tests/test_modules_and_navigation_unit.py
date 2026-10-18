"""Database-free tests for SaaS navigation (sidebar, dashboard) and module-wise selling."""

from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

from frappe_stub import _Dict, plan_lookup, platform_modules

ALL_SAAS_DOCTYPES = {
    "SaaS Module",
    "SaaS Plan",
    "SaaS Registration",
    "SaaS Subscription",
    "SaaS Payment",
    "Tenant User Assignment",
    "Tenant Provisioning Job",
    "SaaS Platform Settings",
    "Company",
}

DISTRIBUTION = {
    "key": "distribution",
    "label": "Distribution SaaS",
    "workspace": "app/distribution",
    "seed_handler": "reckon_distribution.seed.run_distribution_seed",
    "subscription_features": ["dsr_routes", "bangla_pwa"],
}
CRM = {"key": "crm", "label": "CRM", "workspace": "app/crm", "seed_handler": "reckon_crm.seed.run"}


def _hooks(frappe, by_app):
    frappe.get_installed_apps = Mock(return_value=list(by_app))
    frappe.get_hooks.side_effect = lambda hook, app_name=None: by_app.get(app_name, [])


class SidebarAndWorkspaceTests(unittest.TestCase):
    def test_sidebar_lists_dashboard_first_and_every_saas_doctype(self):
        with platform_modules("install") as (frappe, (install,)):
            frappe.db.exists.return_value = True
            sidebar = install._workspace_sidebar_doc()

        links = [item for item in sidebar["items"] if item["type"] == "Link"]
        self.assertEqual(links[0]["label"], "Dashboard")
        self.assertEqual((links[0]["link_type"], links[0]["link_to"]), ("Page", "saas-dashboard"))
        self.assertEqual({item["link_to"] for item in links if item["link_type"] == "DocType"}, ALL_SAAS_DOCTYPES)
        self.assertEqual(sidebar["module"], "SaaS Platform")
        self.assertTrue(any(item["type"] == "Section Break" for item in sidebar["items"]))

    def test_sidebar_skips_links_to_missing_doctypes(self):
        with platform_modules("install") as (frappe, (install,)):
            frappe.db.exists.side_effect = lambda doctype, name=None: name != "Company"
            sidebar = install._workspace_sidebar_doc()
        self.assertNotIn("Company", {item.get("link_to") for item in sidebar["items"]})

    def test_existing_module_sidebars_are_rebuilt(self):
        with platform_modules("install") as (frappe, (install,)):
            # Only the module's "SaaS Platform" sidebar exists, not a legacy one.
            frappe.db.exists.side_effect = lambda doctype, name=None: not (
                doctype == "Workspace Sidebar" and name == "Reckon SaaS Admin"
            )
            frappe.get_all.return_value = ["SaaS Platform"]
            sidebar = Mock()
            frappe.get_doc.return_value = sidebar
            install.ensure_workspace_sidebar()
            sidebar.set.assert_called_once()
            self.assertEqual(sidebar.set.call_args.args[0], "items")
            sidebar.save.assert_called_once_with(ignore_permissions=True)

    def test_sidebar_is_skipped_on_frappe_v15(self):
        with platform_modules("install") as (frappe, (install,)):
            frappe.db.exists.side_effect = lambda doctype, name=None: not (
                doctype == "DocType" and name == "Workspace Sidebar"
            )
            install.ensure_workspace_sidebar()
            frappe.get_doc.assert_not_called()

    def test_workspace_body_shows_a_card_for_every_shortcut(self):
        with platform_modules("install") as (_frappe, (install,)):
            workspace = install._workspace_doc()

        labels = [row["label"] for row in workspace["shortcuts"]]
        blocks = json.loads(workspace["content"])
        cards = [block["data"]["shortcut_name"] for block in blocks if block["type"] == "shortcut"]
        self.assertEqual(cards, labels)
        dashboard = workspace["shortcuts"][0]
        self.assertEqual((dashboard["type"], dashboard["link_to"]), ("Page", "saas-dashboard"))
        doctypes = {row["link_to"] for row in workspace["shortcuts"] if row["type"] == "DocType"}
        self.assertEqual(doctypes, ALL_SAAS_DOCTYPES)

    def test_dashboard_page_is_vendor_only(self):
        from pathlib import Path

        page = json.loads(
            (Path(__file__).resolve().parents[1] / "reckon_saas_platform" / "saas_platform" / "page"
             / "saas_dashboard" / "saas_dashboard.json").read_text()
        )
        self.assertEqual(page["name"], "saas-dashboard")
        self.assertEqual({row["role"] for row in page["roles"]}, {"Reckon Vendor Superuser", "System Manager"})

    def test_module_stats_count_without_sql_function_fields(self):
        with platform_modules("saas") as (frappe, (saas,)):
            def get_all(doctype, **kwargs):
                fields = kwargs.get("fields") or []
                # Frappe v16 rejects SQL functions written as strings, e.g. "count(name)".
                self.assertFalse([field for field in fields if "(" in str(field)], doctype)
                if doctype == "SaaS Module":
                    return [_Dict(name="distribution", module_name="Distribution SaaS"),
                            _Dict(name="crm", module_name="CRM")]
                return {
                    "SaaS Plan": ["distribution", "distribution", "crm"],
                    "SaaS Registration": ["distribution", None],
                    "SaaS Subscription": ["crm"],
                }[doctype]

            frappe.get_all.side_effect = get_all
            stats = {row["module"]: row for row in saas._module_stats()}

        self.assertEqual(
            (stats["distribution"]["plans"], stats["distribution"]["registrations"],
             stats["distribution"]["active_subscriptions"]),
            (2, 1, 0),
        )
        self.assertEqual((stats["crm"]["plans"], stats["crm"]["active_subscriptions"]), (1, 1))

    def test_vendor_dashboard_data_requires_vendor(self):
        with platform_modules("saas") as (frappe, (saas,)):
            with patch.object(saas, "is_vendor_user", return_value=False):
                with self.assertRaises(frappe.PermissionError):
                    saas.get_vendor_dashboard()


class ModuleRegistryTests(unittest.TestCase):
    def test_modules_are_collected_from_every_app_with_app_name(self):
        with platform_modules("module_registry") as (frappe, (registry,)):
            _hooks(frappe, {"frappe": [], "reckon_distribution": [DISTRIBUTION], "reckon_crm": [CRM]})
            modules = registry.get_saas_modules()
        self.assertEqual([m.key for m in modules], ["distribution", "crm"])
        self.assertEqual(modules[1].app, "reckon_crm")

    def test_seed_handlers_can_be_limited_to_subscribed_modules(self):
        with platform_modules("module_registry") as (frappe, (registry,)):
            _hooks(frappe, {"reckon_distribution": [DISTRIBUTION], "reckon_crm": [CRM]})
            self.assertEqual(len(registry.get_seed_handlers()), 2)
            self.assertEqual(registry.get_seed_handlers({"crm"}), ["reckon_crm.seed.run"])

    def test_sync_creates_missing_modules(self):
        with platform_modules("module_registry") as (frappe, (registry,)):
            _hooks(frappe, {"reckon_distribution": [DISTRIBUTION]})
            frappe.db.exists.side_effect = lambda doctype, name=None: doctype == "DocType"
            self.assertEqual(registry.sync_saas_modules(), ["distribution"])
            values = frappe.get_doc.call_args.args[0]
            self.assertEqual(values["module_key"], "distribution")
            self.assertEqual(values["module_name"], "Distribution SaaS")
            self.assertEqual(values["app_name"], "reckon_distribution")
            self.assertEqual(values["enabled"], 1)
            self.assertEqual(values["features"], "dsr_routes\nbangla_pwa")

    def test_sync_keeps_vendor_fields_and_refreshes_code_fields(self):
        with platform_modules("module_registry") as (frappe, (registry,)):
            _hooks(frappe, {"reckon_distribution": [DISTRIBUTION]})
            frappe.db.exists.return_value = True
            existing = _Dict(module_name="Vendor Renamed", enabled=0, app_name="old", landing_workspace="",
                             seed_handler="", features="")
            existing.save = Mock()
            frappe.get_doc.return_value = existing
            registry.sync_saas_modules()
            self.assertEqual(existing.module_name, "Vendor Renamed")
            self.assertEqual(existing.enabled, 0)
            self.assertEqual(existing.app_name, "reckon_distribution")
            existing.save.assert_called_once()


class ModuleWiseSellingTests(unittest.TestCase):
    def _create(self, saas, frappe, **lookup):
        frappe.db.get_value.side_effect = plan_lookup(**lookup)
        registration = Mock(flags=_Dict())
        frappe.get_doc.return_value.insert.return_value = registration
        saas.create_registration(
            business_name="New Co", owner_email="o@example.com", owner_name="O", plan="Plan"
        )
        return frappe.get_doc.call_args.args[0]

    def test_registration_records_the_plan_module(self):
        with platform_modules("saas") as (frappe, (saas,)):
            values = self._create(saas, frappe, saas_module="crm")
        self.assertEqual(values["saas_module"], "crm")

    def test_module_not_on_sale_is_refused(self):
        with platform_modules("saas") as (frappe, (saas,)):
            with self.assertRaises(saas.SignupValidationError):
                self._create(saas, frappe, saas_module="crm", module_enabled=0)
            frappe.get_doc.assert_not_called()

    def test_any_active_module_keeps_company_operational(self):
        with platform_modules("saas") as (_frappe, (saas,)):
            rows = [{"saas_module": "crm", "active": False}, {"saas_module": "distribution", "active": True}]
            with patch.object(saas, "get_company_module_subscriptions", return_value=rows):
                self.assertTrue(saas.is_subscription_active("Co"))
            with patch.object(saas, "get_company_module_subscriptions", return_value=rows[:1]):
                self.assertFalse(saas.is_subscription_active("Co"))

    def test_module_specific_check_uses_that_module_only(self):
        with platform_modules("saas") as (_frappe, (saas,)):
            active = _Dict(status="Active", grace_until=None, end_date=None)
            with patch.object(saas, "get_company_subscription", return_value=active) as lookup:
                self.assertTrue(saas.is_subscription_active("Co", saas_module="crm"))
            lookup.assert_called_once_with("Co", saas_module="crm")
            with patch.object(saas, "get_company_subscription", return_value=None):
                self.assertFalse(saas.is_subscription_active("Co", saas_module="crm"))

    def test_latest_subscription_per_module(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.get_all.return_value = [
                _Dict(name="SUB-3", saas_module="crm", status="Pending", end_date=None, grace_until=None),
                _Dict(name="SUB-2", saas_module="distribution", status="Active", end_date=None, grace_until=None),
                _Dict(name="SUB-1", saas_module="crm", status="Active", end_date=None, grace_until=None),
            ]
            rows = saas.get_company_module_subscriptions("Co")
        self.assertEqual([(row["name"], row["active"]) for row in rows], [("SUB-3", False), ("SUB-2", True)])


class SignupPlanGroupingTests(unittest.TestCase):
    def test_plans_are_grouped_by_module_and_hidden_when_not_on_sale(self):
        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            frappe.get_all.side_effect = [
                [_Dict(name="distribution", module_name="Distribution SaaS")],
                [
                    _Dict(name="Dist Basic", saas_module="distribution"),
                    _Dict(name="CRM Basic", saas_module="crm"),
                    _Dict(name="Legacy", saas_module=None),
                ],
            ]
            plans, groups = page.get_signup_plans()
        self.assertEqual([plan.name for plan in plans], ["Dist Basic", "Legacy"])
        self.assertEqual(
            [(group["module_name"], [p.name for p in group["plans"]]) for group in groups],
            [("Distribution SaaS", ["Dist Basic"]), ("Plans", ["Legacy"])],
        )

    def test_module_query_parameter_filters_plans(self):
        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            frappe.get_all.side_effect = [[_Dict(name="crm", module_name="CRM")], []]
            page.get_signup_plans("crm")
            self.assertEqual(frappe.get_all.call_args.kwargs["filters"], {"enabled": 1, "saas_module": "crm"})


if __name__ == "__main__":
    unittest.main()
