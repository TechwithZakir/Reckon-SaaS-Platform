"""Module pages: detailed content, real pricing, unique banners and the service FAQs every buyer asks."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path
from unittest.mock import Mock

from frappe_stub import _Dict, platform_modules

try:
    import jinja2
except ModuleNotFoundError:
    jinja2 = None

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"
BASE = "https://example.test"
KEYS = ("distribution", "accounts", "sales_agent", "hrms", "crm")
DEFINITIONS = [
    {"key": "distribution", "label": "Distribution SaaS", "description": "FMCG distribution.", "subscription_features": ["dsr_routes", "bangla_pwa"]},
    {"key": "accounts", "label": "Accounts", "description": "Accounting.", "subscription_features": ["stock_and_warehouses"]},
    {"key": "sales_agent", "label": "Sales AI Agent", "description": "AI sales.", "subscription_features": ["frappe_crm_sync"]},
    {"key": "hrms", "label": "Reckon HRMS", "description": "Compact HR and payroll.", "subscription_features": ["employees", "attendance_shifts", "leave", "payroll"]},
    {"key": "crm", "label": "Reckon CRM", "description": "Leads and deals.", "subscription_features": ["leads", "deals", "organizations"]},
    {"key": "payroll_plus", "label": "Payroll Plus", "description": "A module added later with no written copy.", "subscription_features": ["bonus_runs"]},
]
PLANS = [
    {"name": "Distribution Starter", "plan_name": "Distribution Starter", "saas_module": "distribution", "currency": "BDT", "price": 1500, "billing_cycle": "Monthly", "trial_days": 14, "features": "dsr_routes\nbangla_pwa"},
    {"name": "Distribution Pro", "plan_name": "Distribution Pro", "saas_module": "distribution", "currency": "BDT", "price": 15000, "billing_cycle": "Yearly", "trial_days": 0, "features": ""},
    {"name": "HRMS Basic", "plan_name": "HRMS Basic", "saas_module": "hrms", "currency": "USD", "price": 9.5, "billing_cycle": "Monthly", "trial_days": 7, "features": "payroll"},
]


def site(frappe, marketing, plans=PLANS, definitions=DEFINITIONS):
    frappe.get_installed_apps = Mock(return_value=["app"])
    frappe.get_hooks = Mock(return_value=[dict(d) for d in definitions])
    frappe.db.exists = Mock(return_value=True)
    frappe.utils.nowdate = Mock(return_value="2026-11-08")
    frappe.get_all = Mock(side_effect=lambda doctype, **kw: list(plans) if doctype == "SaaS Plan" else [])
    return marketing.get_modules()


class ModuleContentTests(unittest.TestCase):
    def test_every_module_has_overview_highlights_inclusions_exclusions_and_service_faqs(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = site(frappe, marketing)
        self.assertEqual([m["key"] for m in modules], [*KEYS, "payroll_plus"])
        for module in modules:
            self.assertTrue(module["overview"], module["key"])
            self.assertTrue(module["highlights"], module["key"])
            self.assertTrue(module["inclusions"] and module["exclusions"], module["key"])
            questions = " ".join(q for q, _a in module["faqs"]).lower()
            for topic in ("how much does", "free trial", "what is included", "not included", "support", "training", "on-site", "requirement analysis", "customised", "existing data", "add or change modules", "how do i pay"):
                self.assertIn(topic, questions, f"{module['key']}: {topic}")
            for _q, answer in module["faqs"]:
                self.assertNotIn("frappe", answer.lower())

    def test_new_hrms_and_crm_modules_get_their_own_copy(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = {m["key"]: m for m in site(frappe, marketing)}
            hrms = marketing.module_page(BASE, modules["hrms"], list(modules.values()))
            crm = marketing.module_page(BASE, modules["crm"], list(modules.values()))
            late = marketing.module_page(BASE, modules["payroll_plus"], list(modules.values()))
        self.assertIn("HR", hrms["h1"])
        self.assertIn("payroll", hrms["description"].lower())
        self.assertIn("Leads", [h[0] for h in modules["crm"]["highlights"]])
        self.assertEqual(modules["hrms"]["features"], ["Employees", "Attendance shifts", "Leave", "Payroll"])
        self.assertTrue(crm["title"].endswith("| ReckonERP") and len(crm["title"]) <= 70)
        self.assertEqual(late["h1"], "Payroll Plus")  # a module with no written copy still gets a full page

    def test_exclusions_state_the_paid_services_and_extra_charges(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = {m["key"]: m for m in site(frappe, marketing)}
        text = " ".join(modules["sales_agent"]["exclusions"]).lower()
        self.assertIn("ai usage", text)  # AI and integration tools are billed in addition
        shared = " ".join(modules["distribution"]["exclusions"]).lower()
        for word in ("migration", "training", "on-site", "custom", "third-party"):
            self.assertIn(word, shared)


class PricingTests(unittest.TestCase):
    def test_prices_come_from_the_live_plans_and_nowhere_else(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = {m["key"]: m for m in site(frappe, marketing)}
            none = {m["key"]: m for m in site(frappe, marketing, plans=[])}
        plans = modules["distribution"]["plans"]
        self.assertEqual([p["name"] for p in plans], ["Distribution Starter", "Distribution Pro"])
        self.assertEqual(plans[0]["price_text"], "৳1,500 per month")
        self.assertEqual(plans[1]["price_text"], "৳15,000 per year")
        self.assertEqual(modules["hrms"]["plans"][0]["price_text"], "$9.50 per month")
        pricing = dict(modules["distribution"]["faqs"])["How much does Distribution SaaS cost?"]
        self.assertIn("Distribution Starter: ৳1,500 per month", pricing)
        trial = dict(modules["distribution"]["faqs"])["Is there a free trial for Distribution SaaS?"]
        self.assertIn("14 days", trial)
        self.assertEqual(none["distribution"]["plans"], [])
        self.assertIn("shown at signup", dict(none["distribution"]["faqs"])["How much does Distribution SaaS cost?"])
        source = (PKG / "module_content.py").read_text(encoding="utf-8")
        self.assertNotRegex(source, r"[৳$]\s?\d")  # no price is written into the copy

    def test_structured_data_offers_match_the_plans(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = site(frappe, marketing)
            module = next(m for m in modules if m["key"] == "distribution")
            page = marketing.module_page(BASE, module, modules)
            bare = marketing.module_page(BASE, next(m for m in modules if m["key"] == "crm"), modules)
        offers = json.loads(page["jsonld"][0])["offers"]
        self.assertEqual([(o["name"], o["price"], o["priceCurrency"]) for o in offers], [("Distribution Starter", "1500.00", "BDT"), ("Distribution Pro", "15000.00", "BDT")])
        self.assertEqual(offers[0]["url"], f"{BASE}/reckonerp-signup?module=distribution")
        self.assertNotIn("offers", json.loads(bare["jsonld"][0]))  # no plans, no invented offer

    def test_pricing_page_lists_only_modules_with_plans_and_is_in_the_sitemap(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = site(frappe, marketing)
            page = marketing.pricing_page(BASE, modules)
            sitemap = marketing.sitemap_xml(BASE, modules)
            llms = marketing.llms_txt(BASE, modules)
        self.assertEqual([m["key"] for m in page["priced"]], ["distribution", "hrms"])
        self.assertEqual(page["canonical"], f"{BASE}/pricing")
        self.assertLessEqual(len(page["title"]), 70)
        self.assertIn(f"<loc>{BASE}/pricing</loc>", sitemap)
        self.assertIn(f"]({BASE}/pricing)", llms)
        self.assertTrue(page["faqs"])


class BannerTests(unittest.TestCase):
    def test_each_shipped_module_has_its_own_picture_and_social_image(self):
        sizes = set()
        for key in KEYS:
            for name in (f"{key}.webp", f"{key}-og.png"):
                path = PKG / "public" / "images" / "banners" / name
                self.assertTrue(path.exists(), name)
            sizes.add(hashlib.sha256((PKG / "public" / "images" / "banners" / f"{key}.webp").read_bytes()).hexdigest())
        self.assertEqual(len(sizes), len(KEYS))  # every banner is different

    def test_modules_without_a_drawn_picture_get_a_unique_generated_one(self):
        with platform_modules("module_assets") as (_f, (assets,)):
            known = assets.banner("distribution", "Distribution SaaS")
            one = assets.banner("payroll_plus", "Payroll Plus")
            two = assets.banner("field_service", "Field Service")
            again = assets.banner("payroll_plus", "Payroll Plus")
            bad = assets.banner("../etc/passwd", "x")
        self.assertEqual(known["src"], "/assets/reckon_saas_platform/images/banners/distribution.webp")
        self.assertTrue(known["og"].endswith("distribution-og.png"))
        self.assertTrue(one["src"].startswith("data:image/svg+xml"))
        self.assertEqual(one["src"], again["src"])  # stable
        self.assertNotEqual(one["src"], two["src"])  # unique
        self.assertTrue(bad["src"].startswith("data:image/svg+xml"))  # an unsafe key never reaches a file path
        self.assertNotIn("<script", one["src"].lower())
        self.assertEqual((one["width"], one["height"]), (1600, 480))

    def test_banner_reaches_the_module_page_and_social_preview(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = site(frappe, marketing)
            page = marketing.module_page(BASE, next(m for m in modules if m["key"] == "hrms"), modules)
        self.assertEqual(page["og_image"], f"{BASE}/assets/reckon_saas_platform/images/banners/hrms-og.png")


@unittest.skipUnless(jinja2, "jinja2 is not installed")
class RenderTests(unittest.TestCase):
    def render(self, template, page, modules, marketing):
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(PKG.parent)))
        context = _Dict()
        marketing.apply_context(context, page, modules)
        return env.get_template(f"reckon_saas_platform/www/{template}.html").render(**context)

    def test_module_and_pricing_pages_render_every_section(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = site(frappe, marketing)
            module = next(m for m in modules if m["key"] == "distribution")
            html = self.render("reckon_modules", marketing.module_page(BASE, module, modules), modules, marketing)
            pricing = self.render("reckon_pricing", marketing.pricing_page(BASE, modules), modules, marketing)
        for needle in (
            'class="banner"', "About Distribution SaaS", "What is inside Distribution SaaS", "Who uses Distribution SaaS",
            "plans and pricing", "৳1,500 per month", "14-day free trial", "Included", "Not included",
            "Do you provide training for Distribution SaaS?", "Can you support us on-site?", "requirement analysis",
            "application/ld+json",
        ):
            self.assertIn(needle, html, needle)
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)
        self.assertNotIn("frappe", html.lower())
        self.assertIn("৳15,000 per year", pricing)
        self.assertIn("Reckon HRMS", pricing)
        self.assertIn('font-size:1.5rem"><a href="/modules/hrms"', pricing)
        self.assertNotIn('font-size:1.5rem"><a href="/modules/crm"', pricing)  # no plans, so no section
        self.assertEqual(len(re.findall(r"<h1[ >]", pricing)), 1)
        self.assertIn('href="/pricing"', html)


if __name__ == "__main__":
    unittest.main()
