"""Reckon CRM records are isolated company-wise, and /crm follows the Aura theme."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from frappe_stub import REPO_ROOT, _Dict, platform_modules

APP = REPO_ROOT / "reckon_saas_platform"
TENANT = "tenant@acme.test"
STAFF = "rep@reckon.test"
VENDOR = "vendor@reckon.test"


class CrmDoc(_Dict):
    def __init__(self, doctype, new=True, **values):
        super().__init__(doctype=doctype, **values)
        self["_new"] = new

    def is_new(self):
        return self["_new"]

    def set(self, key, value):
        self[key] = value


def tenancy(frappe, tenant, *, companies=None, stored=None, column=True):
    """``companies``: user -> assigned companies; vendors are listed in ``bypass``."""
    companies = companies or {TENANT: ["Acme Traders"]}
    stored = stored or {}
    tenant.user_can_bypass_tenant = Mock(side_effect=lambda user=None: user in {VENDOR, "Administrator"})
    tenant.get_user_companies = Mock(side_effect=lambda user=None: companies.get(user, []))
    frappe.db.has_column = Mock(return_value=column)
    frappe.db.escape = Mock(side_effect=lambda value: "'" + str(value).replace("'", "''") + "'")
    frappe.db.get_value = Mock(side_effect=lambda doctype, name, field: stored.get((doctype, name)))
    frappe.local = _Dict()


class QueryTests(unittest.TestCase):
    def test_each_user_lists_only_what_is_theirs(self):
        with platform_modules("crm_tenant") as (frappe, (tenant,)):
            tenancy(frappe, tenant, companies={TENANT: ["Acme Traders", "Acme Retail"]})
            self.assertEqual(tenant.lead_query(VENDOR), "")
            self.assertEqual(
                tenant.deal_query(TENANT), "`tabCRM Deal`.`company` in ('Acme Traders', 'Acme Retail')"
            )
            # The vendor's own staff see vendor records, never the SaaS signup pipeline.
            staff = tenant.lead_query(STAFF)
            self.assertIn("ifnull(`tabCRM Lead`.`company`, '') = ''", staff)
            self.assertIn("reckon_saas_registration", staff)
            self.assertNotIn("reckon_saas", tenant.task_query(STAFF))

    def test_tenant_sees_nothing_until_migrate_adds_the_field(self):
        with platform_modules("crm_tenant") as (frappe, (tenant,)):
            tenancy(frappe, tenant, column=False)
            self.assertEqual(tenant.organization_query(TENANT), "1 = 0")

    def test_every_tenant_doctype_has_a_query_hook(self):
        hooks = (APP / "hooks.py").read_text(encoding="utf-8")
        with platform_modules("crm_tenant") as (frappe, (tenant,)):
            for doctype in tenant.TENANT_DOCTYPES:
                self.assertIn(f'"{doctype}": "reckon_saas_platform.crm_tenant.', hooks, doctype)
                self.assertIn(f'"{doctype}"', hooks.split("has_permission = {")[1], doctype)


class DocumentTests(unittest.TestCase):
    def test_another_companys_record_is_denied(self):
        with platform_modules("crm_tenant") as (frappe, (tenant,)):
            tenancy(frappe, tenant)
            self.assertIsNone(tenant.has_permission(_Dict(doctype="CRM Lead", company="Acme Traders"), TENANT, "read"))
            self.assertFalse(tenant.has_permission(_Dict(doctype="CRM Lead", company="Other Co"), TENANT, "read"))
            self.assertFalse(tenant.has_permission(_Dict(doctype="CRM Deal", company=""), TENANT, "read"))
            self.assertFalse(tenant.has_permission(_Dict(doctype="CRM Lead", company="Acme Traders"), STAFF, "read"))
            self.assertFalse(
                tenant.has_permission(_Dict(doctype="CRM Lead", reckon_saas_registration="REG-1"), STAFF, "read")
            )
            self.assertIsNone(tenant.has_permission(_Dict(doctype="CRM Lead", company="Other Co"), VENDOR, "write"))

    def test_new_record_gets_the_tenant_company(self):
        with platform_modules("crm_tenant") as (frappe, (tenant,)):
            tenancy(frappe, tenant)
            frappe.session.user = TENANT
            doc = CrmDoc("CRM Lead")
            tenant.bind_company(doc)
            self.assertEqual(doc.company, "Acme Traders")

    def test_child_records_follow_their_lead_or_deal(self):
        with platform_modules("crm_tenant") as (frappe, (tenant,)):
            tenancy(frappe, tenant, companies={TENANT: ["Acme Traders", "Acme Retail"]},
                    stored={("CRM Deal", "CRM-DEAL-1"): "Acme Retail", ("CRM Lead", "CRM-LEAD-1"): "Acme Retail"})
            frappe.session.user = TENANT
            task = CrmDoc("CRM Task", reference_doctype="CRM Deal", reference_docname="CRM-DEAL-1")
            tenant.bind_company(task)
            self.assertEqual(task.company, "Acme Retail")
            visit = CrmDoc("CRM Field Visit", reference_doctype="CRM Deal", reference_name="CRM-DEAL-1",
                           company="Acme Traders")
            with self.assertRaises(tenant.CrossCompanyAccessError):
                tenant.bind_company(visit)
            deal = CrmDoc("CRM Deal", lead="CRM-LEAD-1")
            tenant.bind_company(deal)
            self.assertEqual(deal.company, "Acme Retail")

    def test_tenant_cannot_write_into_another_company(self):
        with platform_modules("crm_tenant") as (frappe, (tenant,)):
            tenancy(frappe, tenant)
            frappe.session.user = TENANT
            with self.assertRaises(tenant.CrossCompanyAccessError):
                tenant.bind_company(CrmDoc("CRM Organization", company="Other Co"))

    def test_company_cannot_change_after_insert(self):
        with platform_modules("crm_tenant") as (frappe, (tenant,)):
            tenancy(frappe, tenant, stored={("CRM Lead", "CRM-LEAD-1"): "Acme Traders"})
            frappe.session.user = VENDOR
            doc = CrmDoc("CRM Lead", new=False, name="CRM-LEAD-1", company="Other Co")
            with self.assertRaises(tenant.CrossCompanyAccessError):
                tenant.bind_company(doc)

    def test_signups_and_vendor_staff_make_vendor_records(self):
        with platform_modules("crm_tenant") as (frappe, (tenant,)):
            tenancy(frappe, tenant)
            frappe.session.user = "Guest"  # public signup creating its lead
            lead = CrmDoc("CRM Lead")
            tenant.bind_company(lead)
            self.assertFalse(lead.get("company"))
            frappe.session.user = STAFF
            with self.assertRaises(tenant.CrossCompanyAccessError):
                tenant.bind_company(CrmDoc("CRM Lead", company="Acme Traders"))

    def test_custom_fields_skip_doctypes_that_are_not_installed(self):
        with platform_modules("crm_tenant") as (frappe, (tenant,)):
            installed = {"CRM Lead", "CRM Deal", "CRM Field Visit"}
            frappe.db.exists = Mock(side_effect=lambda doctype, name=None: doctype == "DocType" and name in installed)
            frappe.get_meta = Mock(return_value=SimpleNamespace(has_field=lambda field: False))
            fields = tenant.tenant_custom_fields()
        self.assertEqual(set(fields), installed)
        self.assertEqual(fields["CRM Lead"][0]["options"], "Company")
        self.assertNotIn("insert_after", fields["CRM Field Visit"][0])


class Response:
    def __init__(self, html, content_type="text/html; charset=utf-8", status=200):
        self.data = html
        self.content_type = content_type
        self.status_code = status
        self.direct_passthrough = False

    def get_data(self, as_text=False):
        return self.data

    def set_data(self, value):
        self.data = value


AURA = {"enabled": 1, "accent": "ember", "custom_accent": "", "aurora_background": 1, "allow_user_override": 1}


class ThemeTests(unittest.TestCase):
    def _inject(self, path="/crm/deals", html="<html><head><title>CRM</title></head><body></body></html>",
                apps=("frappe", "crm", "reckon_aura_theme"), config=None, follow=1, **response):
        with platform_modules("crm_theme") as (frappe, (theme,)):
            frappe.get_installed_apps = Mock(return_value=list(apps))
            frappe.db.get_single_value = Mock(return_value=follow)
            aura = Mock(return_value=dict(AURA, **(config or {})))
            import sys
            from types import ModuleType

            api = ModuleType("reckon_aura_theme.api")
            api.get_public_config = aura
            saved = {k: sys.modules.get(k) for k in ("reckon_aura_theme", "reckon_aura_theme.api")}
            sys.modules["reckon_aura_theme"] = ModuleType("reckon_aura_theme")
            sys.modules["reckon_aura_theme.api"] = api
            try:
                res = Response(html, **response)
                theme.inject_theme(res, SimpleNamespace(path=path))
            finally:
                for k, v in saved.items():
                    if v is None:
                        sys.modules.pop(k, None)
                    else:
                        sys.modules[k] = v
            return res.data, frappe

    def test_crm_page_gets_the_aura_stylesheet_once(self):
        html, _frappe = self._inject()
        self.assertIn("/assets/reckon_saas_platform/css/saas_crm_theme.css", html)
        self.assertIn('"accent":"ember"', html)
        self.assertLess(html.index("saas_crm_theme.css"), html.index("</head>"))
        again, _frappe = self._inject(html=html)
        self.assertEqual(again.count("saas_crm_theme.css"), 1)

    def test_other_pages_and_non_html_are_left_alone(self):
        plain = "<html><head></head></html>"
        for kwargs in ({"path": "/app/crm-lead"}, {"path": "/crmx"}, {"content_type": "application/json"},
                       {"status": 302}):
            html, _frappe = self._inject(html=plain, **kwargs)
            self.assertEqual(html, plain, kwargs)

    def test_off_without_the_theme_or_when_switched_off(self):
        plain = "<html><head></head></html>"
        self.assertEqual(self._inject(html=plain, apps=("frappe", "crm"))[0], plain)
        self.assertEqual(self._inject(html=plain, follow=0)[0], plain)
        self.assertEqual(self._inject(html=plain, config={"enabled": 0})[0], plain)

    def test_custom_colours_are_checked_and_script_is_not_breakable(self):
        html, _frappe = self._inject(config={"accent": "custom", "custom_accent": "red;}</script><script>alert(1)",
                                             "custom_accent_2": "#00ff88"})
        self.assertNotIn("alert(1)", html)
        self.assertIn('"custom_accent":""', html)
        self.assertIn('"custom_accent_2":"#00ff88"', html)

    def test_stylesheet_covers_both_frappe_ui_token_sets_and_dark_mode(self):
        css = (APP / "public" / "css" / "saas_crm_theme.css").read_text(encoding="utf-8")
        for token in ("--surface-white", "--surface-base", "--surface-menu-bar", "--surface-sidebar",
                      "--surface-gray-10", "--ink-gray-9", "--outline-gray-modals"):
            self.assertIn(token + ":", css)
        self.assertIn('html[data-reckon-theme="aura"][data-theme="dark"]', css)
        self.assertNotIn(":root {", css)  # nothing changes unless the script marked the page


if __name__ == "__main__":
    unittest.main()
