"""Regression tests from the live-site test pass: signup SEO tags, llms-full industries, phone header."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock

from frappe_stub import platform_modules
from test_marketing_site_unit import BASE, _modules

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


if __name__ == "__main__":
    unittest.main()
