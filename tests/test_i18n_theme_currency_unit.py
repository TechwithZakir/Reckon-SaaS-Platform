"""Bangla pages under /bn, the BDT/USD plan switch and the dark/light theme control."""

from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import Mock

from frappe_stub import _Dict, platform_modules
from test_marketing_site_unit import BASE, REPO_ROOT, _modules, all_pages

try:
    import jinja2
except ModuleNotFoundError:
    jinja2 = None

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"
BENGALI = re.compile("[ঀ-৿]")


def request_path(frappe, path):
    frappe.local.request = Mock(path=path)


def plan(name, price, currency, symbol=None):
    return {"name": name, "price": float(price), "currency": currency, "symbol": symbol or {"BDT": "৳", "USD": "$"}[currency],
            "cycle": "Monthly", "price_text": f"{symbol or {'BDT': '৳', 'USD': '$'}[currency]}{price:,} per month", "trial_days": 14, "features": ["One"]}


class LanguageHelperTests(unittest.TestCase):
    def test_known_text_is_translated_and_unknown_text_is_left_alone(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            bn = marketing.marketing_bn
        self.assertEqual(bn.translate("Pricing"), "মূল্য")
        self.assertEqual(bn.translate("A sentence nobody translated yet"), "A sentence nobody translated yet")
        self.assertEqual(bn.translate("Questions about Reckon HRMS"), "Reckon HRMS সম্পর্কে প্রশ্ন")
        self.assertEqual(bn.translate("৳1,500 per month"), "প্রতি মাসে ৳1,500")
        self.assertEqual(bn.translate("$99 per year"), "প্রতি বছরে $99")
        self.assertEqual(bn.translate("৳5,000 per 6 months"), "প্রতি ৬ মাসে ৳5,000")
        self.assertTrue(bn.translate("Distribution management software in Bangladesh | ReckonERP").endswith(" | ReckonERP"))
        self.assertEqual(bn.deep({"url": "/pricing", "title": "Pricing", "list": ["Home", ("Blog", 3)]}),
                         {"url": "/pricing", "title": "মূল্য", "list": ["হোম", ("ব্লগ", 3)]})

    def test_paths_and_links(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            bn = marketing.marketing_bn
            link = bn.make_url_filter("bn")
            plain = bn.make_url_filter("en")
        self.assertEqual([bn.bn_path(p) for p in ("/", "/pricing", "/modules/hrms", "/blog", "/login")],
                         ["/bn", "/bn/pricing", "/bn/modules/hrms", "/blog", "/login"])
        self.assertEqual(link("/pricing"), "/bn/pricing")
        self.assertEqual(link("/"), "/bn")
        self.assertEqual(link("/bn/faq"), "/bn/faq")  # never prefixed twice
        self.assertEqual(link("/blog"), "/blog")  # no Bangla blog, so the link stays English
        self.assertEqual(link("/reckonerp-signup"), "/reckonerp-signup?lang=bn")
        self.assertEqual(link("/reckonerp-signup?module=crm"), "/reckonerp-signup?module=crm&lang=bn")
        self.assertEqual(plain("/pricing"), "/pricing")

    def test_every_translated_page_path_is_routed_and_language_follows_the_path(self):
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        for route in ("/bn", "/bn/features", "/bn/features/<slug>", "/bn/modules", "/bn/modules/<slug>", "/bn/industries",
                      "/bn/industries/<slug>", "/bn/pricing", "/bn/faq", "/bn/integrations"):
            self.assertIn(f'"from_route": "{route}"', hooks, route)
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.form_dict = {}
            self.assertEqual(marketing.current_lang(), "en")
            request_path(frappe, "/bn/pricing")
            self.assertEqual(marketing.current_lang(), "bn")
            self.assertEqual(marketing.requested("slug"), "")
            request_path(frappe, "/bn/modules/hrms")
            self.assertEqual(marketing.requested("slug"), "hrms")
            request_path(frappe, "/bnx/pricing")
            self.assertEqual(marketing.current_lang(), "en")
            request_path(frappe, "/blog/some-post")
            self.assertEqual(marketing.current_lang(), "en")

    def test_pages_without_a_slug_never_share_a_cached_copy_between_languages(self):
        """Frappe caches one copy per route name, so ``/`` and ``/bn`` must not point at the same page."""
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        rules = dict(re.findall(r'\{"from_route": "([^"]+)", "to_route": "([^"]+)"\}', hooks))
        english = {k: v for k, v in rules.items() if not k.startswith("/bn") and "<" not in k}
        for route, target in rules.items():
            if not route.startswith("/bn") or "<" in route:
                continue
            twin = "/" if route == "/bn" else route[len("/bn"):]
            twin_target = "index" if twin == "/" else english[twin]
            self.assertNotEqual(target, twin_target, f"{route} shares the cache entry of {twin}")
            self.assertTrue((PKG / "www" / f"{target}.py").exists(), target)
            template = (PKG / "www" / f"{target}.html").read_text(encoding="utf-8")
            self.assertIn(f'{{% extends "reckon_saas_platform/www/{twin_target}.html" %}}', template, target)
            code = (PKG / "www" / f"{target}.py").read_text(encoding="utf-8")
            self.assertIn(f"from reckon_saas_platform.www import {twin_target} as _english_page", code)
            self.assertIn('frappe.local.reckon_forced_lang = "bn"', code)  # the raw route name must also render Bangla
        self.assertEqual(len([r for r in rules if r.startswith("/bn") and "<" not in r]), 7)

    def test_module_headlines_audiences_benefits_and_common_lists_are_all_translated(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            from reckon_saas_platform import module_content

            bn = marketing.marketing_bn
            missing = []
            for key, copy in marketing.MODULE_COPY.items():
                for text in [copy["headline"], copy["audience"], copy["tagline"], copy["seo_title"], *copy["benefits"]]:
                    if bn.translate(text) == text:
                        missing.append((key, text))
            for text in [*module_content.COMMON_INCLUSIONS, *module_content.COMMON_EXCLUSIONS]:
                if bn.translate(text) == text:
                    missing.append(("common", text))
        self.assertEqual(missing, [])

    def test_the_translated_text_keeps_technical_words_in_english_and_never_uses_old_transliterations(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            values = " ".join(marketing.marketing_bn.BN.values())
        for good in ("ERP", "CRM", "AI", "Workspace", "Cloud", "Integration", "Customization", "Plan"):
            self.assertIn(good, values)
        for stiff in ("ইআরপি", "সিআরএম", "অটোমেশন", "ওয়ার্কস্পেস", "ইন্টিগ্রেশন করুন", "ক্লাউড", "কাস্টমাইজেশন", "ইমপ্লিমেন্টেশন", "ডেপ্লয়মেন্ট", "ডাটা মাইগ্রেশন"):
            self.assertNotIn(stiff, values, stiff)

    def test_every_sentence_template_keeps_its_slot_in_the_translation(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            table = marketing.marketing_bn.BN
        for key, value in table.items():
            self.assertEqual(key.count("{name}"), value.count("{name}"), key)
            self.assertEqual(key.count("{n}"), value.count("{n}"), key)

    def test_the_framework_name_is_scrubbed_from_module_text(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            self.assertEqual(marketing.scrub_brand("then follow them up from Frappe CRM, with approval"), "then follow them up from CRM, with approval")
            self.assertEqual(marketing.scrub_brand("Built on Frappe."), "Built on.")
            self.assertEqual(marketing.scrub_brand("Nothing to change"), "Nothing to change")

    def test_every_module_feature_industry_and_home_faq_text_has_a_bangla_version(self):
        import importlib

        with platform_modules("marketing") as (_frappe, (marketing,)):
            from reckon_saas_platform import module_content

            bn = marketing.marketing_bn
            industries = importlib.import_module("reckon_saas_platform.industries")
            texts = []
            for details in module_content.MODULE_DETAILS.values():
                texts += details.get("overview", []) + details.get("use_cases", []) + details.get("inclusions", []) + details.get("exclusions", [])
                texts += [t for pair in details.get("highlights", []) for t in pair]
                texts += [t for pair in details.get("faqs", []) for t in pair]
            for copy in marketing.MODULE_COPY.values():
                texts += [t for pair in copy.get("faqs", []) or [] for t in pair]
            for feature in marketing.FEATURE_LIST:
                texts += [feature["description"], feature["intro"], *feature["points"], *[t for pair in feature["faqs"] for t in pair]]
            texts.append(industries.STANDARD)
            for industry in industries.INDUSTRIES:
                texts += [industry["description"], industry["intro"], *industry["standard"], *industry["custom"], *[t for pair in industry["faqs"] for t in pair]]
            texts += [t for pair in marketing.HOME_FAQS for t in pair]
            texts += ["About ReckonERP", "More answers"]
            missing = sorted({t[:90] for t in texts if bn.translate(t) == t and t not in bn.BN})
        self.assertEqual(missing, [])

    def test_shared_module_questions_and_answers_translate_with_the_module_name_and_prices(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            from reckon_saas_platform import module_content

            bn = marketing.marketing_bn
            plans = [{"name": "Basic", "price_text": "৳500 per month", "trial_days": 15}, {"name": "Pro", "price_text": "৳1,000 per quarter", "trial_days": 0}]
            for name in ("Distribution SaaS", "Reckon CRM"):
                for question, answer in module_content.service_faqs(name, plans, ["One thing", "Two things"], ["Not this"]) + module_content.service_faqs(name, [], ["One"], ["Two"]):
                    self.assertNotEqual(bn.translate(question), question, question)
                    self.assertNotEqual(bn.translate(answer), answer, answer[:60])
            translated = bn.translate(module_content.service_faqs("Reckon CRM", plans, [], [])[0][1])
        self.assertIn("Reckon CRM সাবস্ক্রিপশন হিসেবে বিক্রি হয়", translated)
        self.assertIn("Basic: প্রতি মাসে ৳500", translated)
        self.assertIn("Pro: প্রতি ৩ মাসে ৳1,000", translated)

    def test_product_list_integration_groups_and_cta_translate(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            bn = marketing.marketing_bn
            texts = [marketing.FAMILY_NOTE, *[app["text"] for app in marketing.FAMILY_APPS], *[label for _key, label in marketing.INTEGRATION_GROUPS]]
            missing = [t[:70] for t in texts if bn.translate(t) == t and t not in bn.BN]
            self.assertEqual(missing, [])
            self.assertEqual(bn.translate("Start with Reckon HRMS"), "Reckon HRMS দিয়ে শুরু করুন")


@unittest.skipUnless(jinja2, "jinja2 is not installed")
class BanglaPageTests(unittest.TestCase):
    def render(self, path, builder):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.utils.nowdate = Mock(return_value="2026-11-05")
            modules = _modules(marketing, frappe)
            request_path(frappe, path)
            page = builder(marketing, modules)
            context = _Dict()
            marketing.apply_context(context, page, modules)
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(REPO_ROOT)))
            template = "index" if page["path"] == "/" else {"features": "reckon_features", "modules": "reckon_modules", "pricing": "reckon_pricing",
                                                              "faq": "reckon_faq", "integrations": "reckon_integrations", "industries": "reckon_industries"}[page["path"].split("/")[1]]
            return page, env.get_template(f"reckon_saas_platform/www/{template}.html").render(**context), marketing

    def test_home_in_bangla_has_its_own_address_language_and_hreflang(self):
        page, html, _m = self.render("/bn", lambda m, mods: m.home_page(BASE, mods))
        self.assertEqual(page["canonical"], f"{BASE}/bn")
        self.assertIn('<html lang="bn">', html)
        self.assertIn(f'<link rel="canonical" href="{BASE}/bn">', html)
        for needle in (f'hreflang="en" href="{BASE}/"', f'hreflang="bn" href="{BASE}/bn"', f'hreflang="x-default" href="{BASE}/"', 'property="og:locale" content="bn_BD"'):
            self.assertIn(needle, html, needle)
        for needle in ("মডিউল", "সাইন আপ", "লগইন", "ERP Module", "আপনার ERP, এখন", "সব লেজার পড়তে পারে এমন AI-এর সাথে"):
            self.assertIn(needle, html, needle)
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)
        self.assertTrue(BENGALI.search(page["title"]) and BENGALI.search(page["description"]))

    def test_links_on_a_bangla_page_stay_in_bangla_where_a_twin_exists(self):
        _page, html, _m = self.render("/bn", lambda m, mods: m.home_page(BASE, mods))
        for kept in ('href="/bn/pricing"', 'href="/bn/modules"', 'href="/bn/features"', 'href="/bn/industries"', 'href="/bn"', 'href="/bn/modules/distribution"'):
            self.assertIn(kept, html, kept)
        self.assertIn('href="/blog"', html)  # the blog has no Bangla edition
        self.assertIn('href="/reckonerp-signup?lang=bn"', html)
        self.assertNotIn('href="/pricing"', html)
        self.assertNotIn('href="/modules"', html)

    def test_every_translated_page_renders_in_bangla_with_one_h1(self):
        for path, build in (
            ("/bn/pricing", lambda m, mods: m.pricing_page(BASE, mods)),
            ("/bn/modules", lambda m, mods: m.modules_page(BASE, mods)),
            ("/bn/features", lambda m, mods: m.features_page(BASE)),
            ("/bn/faq", lambda m, mods: m.faq_page(BASE, mods)),
            ("/bn/integrations", lambda m, mods: m.integrations_page(BASE)),
            ("/bn/industries", lambda m, mods: m.industries_page(BASE)),
        ):
            page, html, _m = self.render(path, build)
            self.assertEqual(page["lang"], "bn", path)
            self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1, path)
            self.assertTrue(BENGALI.search(page["h1"]), f"{path}: {page['h1']}")
            self.assertIn('<html lang="bn">', html, path)
            self.assertIn(f'<link rel="canonical" href="{BASE}{path}">', html, path)

    def test_module_feature_and_industry_pages_have_bangla_titles_and_breadcrumbs(self):
        page, html, _m = self.render("/bn/modules/distribution", lambda m, mods: m.module_page(BASE, next(x for x in mods if x["key"] == "distribution"), mods))
        self.assertEqual(page["canonical"], f"{BASE}/bn/modules/distribution")
        self.assertTrue(BENGALI.search(page["title"]) and page["title"].endswith("| ReckonERP"))
        self.assertIn('href="/bn/modules"', html)
        page, html, _m = self.render("/bn/features/modular-erp", lambda m, mods: m.feature_page(BASE, m.get_feature("modular-erp")))
        self.assertIn("Modular ERP", page["title"])
        self.assertTrue(page["title"].endswith("ReckonERP ফিচার"))
        page, html, _m = self.render("/bn/industries/garments", lambda m, mods: m.industry_page(BASE, m.get_industry("garments"), mods))
        self.assertIn("গার্মেন্টস", page["title"])
        breadcrumbs = [json.loads(b) for b in page["jsonld"] if '"BreadcrumbList"' in b][0]
        self.assertEqual(breadcrumbs["itemListElement"][0]["name"], "হোম")
        self.assertTrue(breadcrumbs["itemListElement"][0]["item"].endswith("/bn"))

    def test_english_pages_offer_the_bangla_twin_and_the_switch_links_to_it(self):
        page, html, _m = self.render("/pricing", lambda m, mods: m.pricing_page(BASE, mods))
        self.assertEqual(page["lang"], "en")
        self.assertIn(f'<link rel="alternate" hreflang="bn" href="{BASE}/bn/pricing">', html)
        self.assertIn('href="/bn/pricing" data-lang="bn"', html)
        self.assertIn('href="/pricing" data-lang="en" class="is-active"', html)

    def test_pages_without_a_twin_have_no_language_switch(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = _modules(marketing, frappe)
            page = marketing.make_page(BASE, path="/blog", title="Blog", description="d" * 60, h1="Blog")
            context = _Dict()
            marketing.apply_context(context, page, modules)
        self.assertNotIn("alt_bn", page)
        self.assertFalse(context.get("lang_links"))

    def test_untranslated_text_falls_back_to_english_instead_of_disappearing(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            request_path(frappe, "/bn/faq")
            page = marketing.make_page(BASE, path="/faq", title="Pricing", description="d" * 60, h1="Pricing",
                                       faqs=[("What is ReckonERP?", "x"), ("A question nobody has translated?", "An answer nobody has translated.")])
        questions = [q for q, _a in page["faqs"]]
        self.assertEqual(questions, ["ReckonERP কী?", "A question nobody has translated?"])
        self.assertEqual(page["faqs"][1][1], "An answer nobody has translated.")

    def test_all_pages_still_build_in_english(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            pages = all_pages(marketing, _modules(marketing, frappe))
        for page in pages:
            self.assertEqual(page["lang"], "en")
            self.assertEqual(page["canonical"], BASE + page["path"])


@unittest.skipUnless(jinja2, "jinja2 is not installed")
class CurrencySwitchTests(unittest.TestCase):
    def build(self, plans):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.utils.nowdate = Mock(return_value="2026-11-05")
            marketing.get_plans = Mock(return_value={"distribution": plans})
            modules = _modules(marketing, frappe)
            module = next(m for m in modules if m["key"] == "distribution")
            pricing = marketing.pricing_page(BASE, modules)
            context = _Dict()
            marketing.apply_context(context, pricing, modules)
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(REPO_ROOT)))
            return module, pricing, env.get_template("reckon_saas_platform/www/reckon_pricing.html").render(**context), marketing, modules

    def test_plans_are_grouped_by_currency_with_bdt_first(self):
        module, pricing, html, _m, _mods = self.build([plan("Starter", 500, "BDT"), plan("Starter USD", 5, "USD"), plan("Pro", 1500, "BDT")])
        self.assertEqual(module["currencies"], ["BDT", "USD"])
        self.assertEqual([p["name"] for p in module["plans"]], ["Starter", "Pro"])  # the default view is BDT
        self.assertEqual([p["name"] for p in module["plans_by_currency"]["USD"]], ["Starter USD"])
        self.assertEqual(pricing["currencies"], ["BDT", "USD"])
        self.assertEqual(html.count('class="rk-cur"'), 1)
        self.assertIn('data-cur-set="BDT"', html)
        self.assertIn('data-cur-set="USD"', html)
        self.assertEqual(len(re.findall(r'class="grid plans cur-set', html)), 2)
        self.assertEqual(len(re.findall(r'cur-set primary', html)), 1)
        self.assertIn("$5 per month", html)
        self.assertIn("৳500 per month", html)

    def test_a_single_currency_shows_no_switch(self):
        module, pricing, html, _m, _mods = self.build([plan("Starter", 500, "BDT")])
        self.assertEqual(module["currencies"], ["BDT"])
        self.assertNotIn('class="rk-cur"', html)
        self.assertEqual(len(re.findall(r'class="grid plans cur-set', html)), 1)

    def test_offers_in_search_data_cover_every_currency(self):
        module, _pricing, _html, marketing, modules = self.build([plan("Starter", 500, "BDT"), plan("Starter USD", 5, "USD")])
        offers = marketing.plan_offers(BASE, module)
        self.assertEqual({o["priceCurrency"] for o in offers}, {"BDT", "USD"})  # so "how much in USD" is answerable from the page data

    def test_choosing_a_plan_links_to_signup_and_bangla_pages_keep_the_language(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.utils.nowdate = Mock(return_value="2026-11-05")
            marketing.get_plans = Mock(return_value={"distribution": [plan("Starter", 500, "BDT"), plan("Starter USD", 5, "USD")]})
            modules = _modules(marketing, frappe)
            request_path(frappe, "/bn/pricing")
            pricing = marketing.pricing_page(BASE, modules)
            context = _Dict()
            marketing.apply_context(context, pricing, modules)
            html = jinja2.Environment(loader=jinja2.FileSystemLoader(str(REPO_ROOT))).get_template("reckon_saas_platform/www/reckon_pricing.html").render(**context)
        self.assertIn('href="/reckonerp-signup?module=distribution&amp;currency=BDT&amp;lang=bn"', html)
        self.assertIn('href="/reckonerp-signup?module=distribution&amp;currency=USD&amp;lang=bn"', html)  # a USD plan opens signup on USD plans
        self.assertIn("Starter বেছে নিন", html)
        self.assertIn("14 দিনের ফ্রি ট্রায়াল", html)
        self.assertIn('aria-label="মুদ্রা"', html)


class _Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.buttons = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "button" and "data-theme-set" in attrs:
            self.buttons.append(attrs["data-theme-set"])


@unittest.skipUnless(jinja2, "jinja2 is not installed")
class ThemeTests(unittest.TestCase):
    def render_home(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.utils.nowdate = Mock(return_value="2026-11-05")
            modules = _modules(marketing, frappe)
            context = _Dict()
            marketing.apply_context(context, marketing.home_page(BASE, modules), modules)
            return jinja2.Environment(loader=jinja2.FileSystemLoader(str(REPO_ROOT))).get_template("reckon_saas_platform/www/index.html").render(**context)

    def test_header_offers_dark_and_light_and_the_choice_is_applied_before_first_paint(self):
        html = self.render_home()
        parser = _Collect()
        parser.feed(html)
        self.assertEqual(parser.buttons, ["dark", "light"])
        self.assertIn('class="rk-theme"', html)
        head = html[: html.index("</head>")]
        self.assertIn('localStorage.getItem("reckon_theme")', head)  # runs before the styles, so there is no flash
        self.assertLess(head.index("reckon_theme"), head.index("<style>"))
        self.assertIn("data-theme-set", html)
        self.assertIn("reckon_theme", html[html.index("</head>"):])  # the buttons store the choice

    def test_hero_picture_can_follow_the_chosen_theme(self):
        html = self.render_home()
        self.assertIn('<source data-dark data-media="(prefers-color-scheme: dark)"', html)

    def test_css_defines_both_themes_and_still_follows_the_system_by_default(self):
        css = (PKG / "templates" / "marketing" / "chrome.css").read_text(encoding="utf-8")
        self.assertIn(':root[data-theme="dark"]{', css)
        self.assertIn(':root[data-theme="light"]{', css)
        self.assertIn('@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){', css)  # no explicit choice: follow the system
        style = (PKG / "templates" / "marketing" / "style.css").read_text(encoding="utf-8")
        self.assertIn(':root[data-theme="dark"] .mk', style)
        self.assertNotIn("@media(prefers-color-scheme:dark){.mk", style)

    def test_dark_and_light_use_the_same_variables(self):
        css = (PKG / "templates" / "marketing" / "chrome.css").read_text(encoding="utf-8")
        auto = re.search(r'prefers-color-scheme:dark\)\{:root:not\(\[data-theme="light"\]\)\{([^}]*)\}', css).group(1)
        explicit = re.search(r':root\[data-theme="dark"\]\{([^}]*)\}', css).group(1)
        self.assertEqual(explicit.replace(";color-scheme:dark", ""), auto)

    def test_signup_page_does_not_get_a_theme_control_it_cannot_honour(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            context = _Dict()
            marketing.shared_context(context, [], "en")
        self.assertFalse(context.show_theme)


if __name__ == "__main__":
    unittest.main()
