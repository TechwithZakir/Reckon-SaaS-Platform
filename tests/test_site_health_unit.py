"""Regression tests from the live-site test pass: signup SEO tags, llms-full industries, phone header."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from frappe_stub import _Dict, platform_modules
from test_marketing_site_unit import BASE, _modules, all_pages

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"


class SiteHealthTests(unittest.TestCase):
    def test_signup_page_declares_canonical_description_alternates_and_language(self):
        html = (PKG / "www" / "reckonerp_signup.html").read_text(encoding="utf-8")
        for needle in (
            'rel="canonical" href="{{ canonical_url|e }}"',
            'name="description" content="{{ meta_description|e }}"',
            'hreflang="bn"',
            'hreflang="x-default"',
            'document.documentElement.lang="{{ lang|e }}"',
        ):
            self.assertIn(needle, html, needle)
        code = (PKG / "www" / "reckonerp_signup.py").read_text(encoding="utf-8")
        for needle in ("context.canonical_url", "context.alternate_urls", "context.meta_description"):
            self.assertIn(needle, code, needle)
        canonical_line = next(line for line in code.splitlines() if "context.canonical_url =" in line)
        self.assertNotIn("lang=", canonical_line)  # the canonical never carries a language or currency parameter
        self.assertNotIn("currency", canonical_line)

    def test_llms_full_text_lists_every_industry_page(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.utils.nowdate = Mock(return_value="2026-11-09")
            text = marketing.llms_full_txt(BASE, _modules(marketing, frappe))
            from reckon_saas_platform.industries import INDUSTRIES
        self.assertIn("## Industries", text)
        for industry in INDUSTRIES:
            self.assertIn(f"{BASE}/industries/{industry['slug']}", text)

    def test_the_header_is_compact_on_phones_and_switches_stay_easy_to_tap(self):
        css = (PKG / "templates" / "marketing" / "chrome.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"@media\(max-width:720px\)\{\s*header\.top \.bar\{gap:6px 10px\}")
        self.assertIn("min-height:32px", css)

    def test_changing_a_plan_module_or_setting_refreshes_the_cached_public_pages(self):
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        for doctype in ("SaaS Plan", "SaaS Module"):
            block = hooks[hooks.index(f'"{doctype}": {{'):]
            block = block[: block.index("},")]
            for event in ("after_insert", "on_update", "on_trash"):
                self.assertIn(f'"{event}": "reckon_saas_platform.marketing.refresh_public_pages"', block, f"{doctype} {event}")
        settings = hooks[hooks.index('"SaaS Platform Settings": {'):]
        self.assertIn("refresh_public_pages", settings[: settings.index("},")])

    def test_refresh_public_pages_clears_the_page_cache_and_never_raises(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.clear_cache = Mock()
            marketing.refresh_public_pages()  # falls back to the general cache when the website cache is unavailable
            marketing.refresh_public_pages(doc=Mock(), method="on_update")
        self.assertEqual(frappe.clear_cache.call_count, 2)  # one per call, in this stub the website cache module is absent

    def test_duplicate_raw_routes_are_disallowed_but_never_flagged_noindex_per_request(self):
        """Frappe shares one cached copy between a route name and its public address, so a per-request noindex flag
        set when someone opens ``/reckon_pricing`` would leak onto ``/pricing``. The page keeps its public canonical
        instead, and robots.txt keeps crawlers off the raw routes."""
        with platform_modules("marketing") as (frappe, (marketing,)):
            robots = marketing.robots_txt(BASE)
            modules = _modules(marketing, frappe)
            page = marketing.pricing_page(BASE, modules)
            frappe.local.request = Mock(path="/reckon_pricing")
            marketing.apply_context(_Dict(), page, modules)
        self.assertIn("Disallow: /reckon_" + chr(10), robots)
        self.assertIn("Disallow: /index" + chr(10), robots)
        self.assertNotIn("Disallow: /industries", robots)
        self.assertFalse(page["noindex"])  # a request path must never change what is cached for the public address
        self.assertEqual(page["canonical"], f"{BASE}/pricing")  # the raw route still points search engines at the real page

    def test_bangla_titles_stay_short_enough_not_to_be_cut_in_results(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            bn = marketing.marketing_bn
            modules = _modules(marketing, frappe)
            frappe.local.request = Mock(path="/bn")
            titles = [bn.translate(p["title"]) for p in all_pages(marketing, modules)]
        self.assertTrue(titles)
        self.assertLessEqual(max(len(t) for t in titles), 58, [t for t in titles if len(t) > 58])

    def test_structured_data_has_stable_ids_language_and_service_area(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.get_cached_doc = Mock(return_value=_Dict(social_profiles=""))
            home = marketing.home_page(BASE, _modules(marketing, frappe), None, marketing.get_profiles())
            blocks = {json.loads(b)["@type"]: json.loads(b) for b in home["jsonld"]}
        org, office, site = blocks["Organization"], blocks["ProfessionalService"], blocks["WebSite"]
        self.assertEqual(org["@id"], f"{BASE}/#organization")
        self.assertEqual(office["parentOrganization"], {"@id": org["@id"]})
        self.assertEqual(site["publisher"], {"@id": org["@id"]})
        self.assertEqual(site["inLanguage"], ["en", "bn"])
        self.assertEqual(org["contactPoint"]["availableLanguage"], ["English", "Bengali"])
        self.assertIn({"@type": "City", "name": "Dhaka"}, office["areaServed"])
        self.assertEqual(blocks["FAQPage"]["inLanguage"], "en")

    def test_llms_files_point_to_the_bangla_edition_and_the_bangla_footer_is_translated(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.utils.nowdate = Mock(return_value="2026-11-09")
            modules = _modules(marketing, frappe)
            short, full = marketing.llms_txt(BASE, modules), marketing.llms_full_txt(BASE, modules)
            bn = marketing.marketing_bn
            address, hours = bn.translate(marketing.ADDRESS_TEXT), bn.translate(marketing.OPEN_HOURS_TEXT)
        self.assertIn(f"{BASE}/bn", short)
        self.assertIn("## Languages", short)
        self.assertIn(f"{BASE}/bn", full)
        self.assertEqual(address, "উত্তরা, ঢাকা, বাংলাদেশ")
        self.assertIn("রবি–বৃহস্পতি", hours)

    def test_a_forced_language_beats_the_request_path(self):
        """``/reckon_bn_home`` is a raw address for the Bangla page; it must not cache an English copy."""
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.local.request = Mock(path="/reckon_bn_home")
            self.assertEqual(marketing.current_lang(), "en")
            frappe.local.reckon_forced_lang = "bn"
            self.assertEqual(marketing.current_lang(), "bn")
            page = marketing.pricing_page(BASE, _modules(marketing, frappe))
        self.assertEqual((page["lang"], page["canonical"]), ("bn", f"{BASE}/bn/pricing"))

    def test_pixel_is_loaded_by_the_site_unless_the_container_owns_it(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.get_cached_doc = Mock(return_value=_Dict(google_tag_manager_id="GTM-M6LCK4P8", google_analytics_id="G-QNDNXFPWSZ", meta_pixel_id="1357499629607234"))
            default = marketing.get_tracking()
            frappe.get_cached_doc = Mock(return_value=_Dict(google_tag_manager_id="GTM-M6LCK4P8", meta_pixel_id="1357499629607234", meta_pixel_in_tag_manager=1))
            owned = marketing.get_tracking()
        self.assertEqual((default["gtm"], default["ga4"], default["pixel"], default["pixel_in_gtm"]), ("GTM-M6LCK4P8", "G-QNDNXFPWSZ", "1357499629607234", False))
        self.assertTrue(owned["pixel_in_gtm"])
        path = PKG / "saas_platform" / "doctype" / "saas_platform_settings" / "saas_platform_settings.json"
        field = next(f for f in json.loads(path.read_text(encoding="utf-8"))["fields"] if f["fieldname"] == "meta_pixel_in_tag_manager")
        self.assertEqual((field["fieldtype"], field["default"]), ("Check", "0"))


if __name__ == "__main__":
    unittest.main()
