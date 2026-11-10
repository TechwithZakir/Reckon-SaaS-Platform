"""Fixes from the AI-agent and performance test pass: offers on the home page, prices for agents, a plan table, deferred tracking."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from unittest.mock import Mock

from frappe_stub import _Dict, platform_modules
from test_marketing_site_unit import BASE, REPO_ROOT, _modules

try:
    import jinja2
except ModuleNotFoundError:
    jinja2 = None

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"


def plan(name, price, currency, trial=14):
    symbol = {"BDT": "৳", "USD": "$"}[currency]
    return {"name": name, "price": float(price), "currency": currency, "symbol": symbol, "cycle": "Monthly",
            "price_text": f"{symbol}{price:,} per month", "trial_days": trial, "features": ["One"], "modified": "2026-11-05"}


class AgentDataTests(unittest.TestCase):
    def setUp(self):
        ctx = platform_modules("marketing")
        self.frappe, (self.m,) = ctx.__enter__()
        self.addCleanup(ctx.__exit__, None, None, None)
        self.frappe.utils.nowdate = Mock(return_value="2026-11-10")
        self.m.get_plans = Mock(return_value={"distribution": [plan("Basic", 500, "BDT"), plan("Basic USD", 5, "USD")], "accounts": [plan("Std", 1000, "BDT")]})
        self.modules = _modules(self.m, self.frappe)

    def blocks(self, page):
        return {json.loads(b)["@type"]: json.loads(b) for b in page["jsonld"]}

    def test_home_page_software_data_lists_every_plan_in_every_currency(self):
        offers = self.blocks(self.m.home_page(BASE, self.modules))["SoftwareApplication"]["offers"]
        self.assertEqual(sorted((o["name"], o["priceCurrency"]) for o in offers), [("Basic", "BDT"), ("Basic USD", "USD"), ("Std", "BDT")])
        for offer in offers:
            self.assertTrue(all(k in offer for k in ("price", "priceCurrency", "availability", "url")))

    def test_module_software_data_carries_its_real_update_date_and_feature_list(self):
        record = {"name": "accounts", "module_name": "Accounts", "description": "d", "features": "", "modified": "2026-11-01 10:00:00"}
        modules = _modules(self.m, self.frappe, records=[record])
        module = next(x for x in modules if x["key"] == "accounts")
        data = self.blocks(self.m.module_page(BASE, module, modules))["SoftwareApplication"]
        self.assertEqual(data["dateModified"], "2026-11-01")
        self.assertEqual(data["featureList"], module["features"][:12]) if module["features"] else self.assertNotIn("featureList", data)

    def test_a_module_without_a_date_or_features_adds_neither_property(self):
        module = {**next(x for x in self.modules if x["key"] == "distribution"), "modified": "", "features": []}
        data = self.blocks(self.m.module_page(BASE, module, self.modules))["SoftwareApplication"]
        self.assertNotIn("dateModified", data)
        self.assertNotIn("featureList", data)

    def test_llms_full_lists_plan_prices_in_both_currencies_with_the_trial(self):
        text = self.m.llms_full_txt(BASE, self.modules)
        self.assertIn("Plans in BDT: Basic ৳500 per month. Free trial up to 14 days.", text)
        self.assertIn("Plans in USD: Basic USD $5 per month. Free trial up to 14 days.", text)


@unittest.skipUnless(jinja2, "jinja2 is not installed")
class PageTests(unittest.TestCase):
    def render(self, template, build, path="/"):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.utils.nowdate = Mock(return_value="2026-11-10")
            marketing.get_plans = Mock(return_value={"distribution": [plan("Basic", 500, "BDT"), plan("Basic USD", 5, "USD")], "accounts": [plan("Std", 1000, "BDT", trial=0)]})
            modules = _modules(marketing, frappe)
            frappe.local.request = Mock(path=path)
            context = _Dict()
            marketing.apply_context(context, build(marketing, modules), modules)
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(REPO_ROOT)))
            return env.get_template(f"reckon_saas_platform/www/{template}.html").render(**context)

    def _compare_page(self, path):
        def line(feature, included=True, value=""):
            return {"feature": feature, "included": included, "value": value}

        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.utils.nowdate = Mock(return_value="2026-11-10")
            basic = {**plan("Basic", 500, "BDT"), "comparison": [line("Users", value="Up to 5"), line("Reports"), line("API access", False)]}
            pro = {**plan("Pro", 900, "BDT"), "comparison": [line("users", value="Unlimited"), line("Reports"), line("API access"), line("Audit log")]}
            usd = {**plan("Basic USD", 5, "USD"), "comparison": [line("Users", value="Up to 5")]}
            marketing.get_plans = Mock(return_value={"distribution": [basic, pro, usd], "accounts": [plan("Std", 1000, "BDT", trial=0)]})
            modules = _modules(marketing, frappe)
            frappe.local.request = Mock(path=path)
            context = _Dict()
            marketing.apply_context(context, marketing.pricing_page(BASE, modules), modules)
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(REPO_ROOT)))
            return env.get_template("reckon_saas_platform/www/reckon_pricing.html").render(**context), modules

    def test_pricing_compares_the_plans_of_a_module_side_by_side(self):
        html, modules = self._compare_page("/pricing")
        sets = re.findall(r'<table class="cmp-table">.*?</table>', html, re.S)
        self.assertEqual(len(sets), 2)  # BDT and USD for the module with comparison lines
        bdt = sets[0]
        self.assertEqual(re.findall(r'<span class="cmp-plan">(.*?)</span>', bdt), ["Basic", "Pro"])
        rows = {r[0]: r[1] for r in re.findall(r'<tr><th scope="row">(.*?)</th>(.*?)</tr>', bdt, re.S)}
        self.assertEqual(list(rows), ["Users", "Reports", "API access", "Audit log"])  # features line up by wording, once each
        self.assertIn("Up to 5", rows["Users"])
        self.assertIn("Unlimited", rows["Users"])
        self.assertEqual(rows["API access"].count("cmp-no"), 1)  # Basic: not included, Pro: included
        self.assertEqual(rows["Audit log"].count("cmp-no"), 1)  # Basic does not list it
        self.assertIn("14-day free trial", bdt)
        self.assertEqual(bdt.count("Choose "), 2)
        self.assertNotIn("plans-table", html)
        # a module whose plans have no comparison lines keeps the simple plan cards
        self.assertIn('class="card"', html)

    def test_bangla_comparison_labels_are_translated(self):
        html, _ = self._compare_page("/bn/pricing")
        self.assertIn("অন্তর্ভুক্ত নয়", html)
        self.assertIn("প্রতি মাসে ৳500", re.search(r'<table class="cmp-table">.*?</table>', html, re.S).group(0))

    def test_module_without_comparison_lines_keeps_plan_cards_even_if_plans_list_features(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            marketing.get_plans = Mock(return_value={"distribution": [{**plan("A", 1, "BDT"), "comparison": []}]})
            module = next(m for m in _modules(marketing, frappe) if m["key"] == "distribution")
        self.assertEqual(module["comparison_by_currency"], {})

    def test_comparison_matrix_falls_back_to_the_plan_feature_list(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            matrix = marketing.comparison_matrix([{**plan("A", 1, "BDT"), "features": ["One", "Two"], "comparison": []}])
            self.assertEqual([r["feature"] for r in matrix["rows"]], ["One", "Two"])
            self.assertEqual(marketing.comparison_matrix([{**plan("A", 1, "BDT"), "features": [], "comparison": []}])["rows"], [])

    def test_plan_has_an_editable_comparison_table(self):
        import json

        base = PKG / "saas_platform" / "doctype"
        plan_json = json.loads((base / "saas_plan" / "saas_plan.json").read_text(encoding="utf-8"))
        field = next(f for f in plan_json["fields"] if f["fieldname"] == "comparison_features")
        self.assertEqual((field["fieldtype"], field["options"]), ("Table", "SaaS Plan Feature"))
        self.assertIn("comparison_features", plan_json["field_order"])
        child = json.loads((base / "saas_plan_feature" / "saas_plan_feature.json").read_text(encoding="utf-8"))
        self.assertEqual(child["istable"], 1)
        self.assertEqual([f["fieldname"] for f in child["fields"]], ["feature", "included", "value"])

    def test_home_page_says_in_plain_words_what_the_product_is(self):
        html = self.render("index", lambda m, mods: m.home_page(BASE, mods))
        main = re.search(r"<main.*?</main>", html, re.S).group(0)
        first = " ".join(re.sub(r"<[^>]+>", " ", main).split()[:120])
        self.assertIn("ReckonERP is a cloud ERP with built-in AI", first)  # near the top, where an agent looks first
        self.assertIn('<link rel="alternate" type="text/plain" href="/llms.txt"', html)


class SpeedTests(unittest.TestCase):
    def test_tracking_scripts_wait_for_load_and_idle_but_the_banner_and_consent_clicks_do_not(self):
        source = (PKG / "templates" / "marketing" / "tracking.html").read_text(encoding="utf-8")
        self.assertIn("requestIdleCallback", source)
        self.assertIn("window.addEventListener('load'", source)
        self.assertIn("if(!T.consent||home||saved==='yes'){later(load);return}", source)
        self.assertIn("store('yes');box.hidden=true;load()", source)  # an explicit Accept loads at once
        self.assertEqual(source.count("later(load)"), 1)

    def test_touch_targets_in_the_footer_are_padded(self):
        css = (PKG / "templates" / "marketing" / "style.css").read_text(encoding="utf-8")
        self.assertIn("footer.foot ul a,.foot-seo a,.foot-svc a{display:inline-block;padding:3px 0}", css)

    def test_conversion_events_reach_ga4_directly_as_well_as_the_data_layer_and_meta(self):
        source = (PKG / "templates" / "marketing" / "tracking.html").read_text(encoding="utf-8")
        self.assertIn("function ga(name,params){if(T.ga4&&w.gtag)w.gtag('event',name,params||{})}", source)
        self.assertIn("w.dataLayer.push({event:'signup_click'});ga('signup_click',{link_url:a.getAttribute('href')});if(w.fbq)w.fbq('track','Lead')", source)
        self.assertIn("w.dataLayer.push({event:'whatsapp_chat'});ga('whatsapp_chat');if(w.fbq)w.fbq('track','Contact')", source)


if __name__ == "__main__":
    unittest.main()
