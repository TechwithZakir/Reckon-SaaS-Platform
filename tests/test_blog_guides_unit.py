"""The nine buyer-guide and AI posts: publish rules, structure, links and the draft-only seed."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

from frappe_stub import platform_modules

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"
BASE = "https://example.test"
MODS = ("marketing", "seo", "seo_agent", "blog", "blog_agent", "blog_seed", "blog_html", "blog_guides")


def load():
    ctx = platform_modules(*MODS)
    frappe, mods = ctx.__enter__()
    return ctx, frappe, dict(zip(MODS, mods, strict=True))


class GuideContentTests(unittest.TestCase):
    def setUp(self):
        ctx, self.frappe, self.by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        self.posts = self.by["blog_guides"].GUIDES

    def test_nine_distinct_posts_that_pass_the_publish_rules(self):
        agent, clean = self.by["blog_agent"], self.by["blog_html"]
        existing = {p["slug"] for p in self.by["blog_seed"].POSTS}
        self.assertEqual(len(self.posts), 9)
        self.assertEqual(len({p["slug"] for p in self.posts} | existing), 19)  # no clash with the comparison posts
        self.assertEqual(len({p["title"] for p in self.posts}), 9)
        for post in self.posts:
            slug = post["slug"]
            self.assertRegex(slug, r"^[a-z0-9][a-z0-9-]{2,78}$")
            self.assertTrue(20 <= len(post["title"]) <= 58, f"{slug}: {len(post['title'])}")
            self.assertTrue(70 <= len(post["summary"]) <= 160, f"{slug}: {len(post['summary'])}")
            words = len(re.findall(r"\w+", clean.plain_text(post["body"])))
            self.assertTrue(800 <= words <= 2200, f"{slug}: {words} words")
            self.assertIsNone(agent.FORBIDDEN_ARTICLE.search(post["title"] + post["summary"] + post["body"]), slug)
            self.assertNotIn("http://", post["body"], slug)
            self.assertFalse(agent.cliches(post["body"]), f"{slug}: {agent.cliches(post['body'])}")
            self.assertIn(post["category"], self.by["blog"].CATEGORIES)

    def test_structure_matches_the_comparison_posts(self):
        blog, clean = self.by["blog"], self.by["blog_html"]
        for post in self.posts:
            body = post["body"]
            self.assertTrue(body.startswith("<p><strong>Short answer:</strong>"), post["slug"])
            self.assertEqual(body.count("<table>"), 1, post["slug"])
            headings = re.findall(r"<h2>(.*?)</h2>", body)
            for needed in ("The problem", "The solution: a practical path", "Where ReckonERP fits", "Conclusion", "Frequently asked questions"):
                self.assertIn(needed, headings, post["slug"])
            self.assertEqual(headings[0], post["story_title"], post["slug"])
            self.assertGreaterEqual(len(blog.extract_faqs(clean.sanitize_html(body))), 4, post["slug"])

    def test_links_resolve_and_a_module_post_links_its_module(self):
        slugs = {p["slug"] for p in self.posts} | {p["slug"] for p in self.by["blog_seed"].POSTS}
        known = {
            "/pricing", "/faq", "/integrations", "/industries", "/reckonerp-signup", "/features/modular-erp",
            "/features/reckon-ai-assistant", "/features/ai-assisted-selling", "/features/ai-agent-development",
            "/industries/fmcg-distribution", "/modules/distribution", "/modules/accounts", "/modules/hrms",
            "/modules/crm", "/modules/sales_agent",
        } | {f"/blog/{s}" for s in slugs}
        for post in self.posts:
            links = re.findall(r'href="(/[^"]*)"', post["body"])
            self.assertTrue(links, post["slug"])
            for link in links:
                self.assertIn(link, known, f"{post['slug']}: {link}")
            if post["module"]:
                self.assertIn(f"/modules/{post['module']}", links, post["slug"])

    def test_no_competitors_framework_names_or_invented_numbers(self):
        for post in self.posts:
            text = post["body"].lower()
            self.assertNotRegex(text, r"frappe|odoo|\bsap\b|oracle|netsuite|zoho|salesforce|microsoft dynamics", post["slug"])
            self.assertNotRegex(post["body"], r"\d+\s?%", post["slug"])  # no statistics we cannot back
            self.assertNotRegex(post["body"], r"[৳$€]\s?\d", post["slug"])  # no invented prices

    def test_styles_are_real_cover_styles(self):
        valid = {"cloud", "spreadsheet", "route", "servers", "people", "crm", "stack", "ai", "privacy", "globe"}
        for post in self.posts:
            self.assertIn(post["style"], valid, post["slug"])


class GuideSeedTests(unittest.TestCase):
    def test_drafts_are_created_once_with_covers_and_never_published(self):
        ctx, frappe, by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        frappe.utils.get_url = Mock(return_value=BASE + "/")
        existing = {"ai-agent-vs-ai-chatbot"}
        frappe.db.exists = Mock(side_effect=lambda doctype, name=None: name in existing)
        made, covers = [], []
        frappe.get_doc = Mock(side_effect=lambda values: Mock(insert=lambda ignore_permissions=False: made.append(values)))
        frappe.db.set_value = Mock()
        image = type("Image", (), {"attach_cover": staticmethod(lambda slug, title, category, style=None: covers.append((slug, category, style)) or "/files/c.webp")})
        sys.modules["reckon_saas_platform.blog_image"] = image
        created = by["blog_guides"].seed_guides()
        self.assertEqual(len(created), 8)
        self.assertNotIn("ai-agent-vs-ai-chatbot", created)
        for values in made:
            self.assertEqual((values["doctype"], values["status"], values["source"]), ("SEO Article", "Draft", "Manual"))
            self.assertIn(f"{BASE}/blog/{values['slug']}", values["promo_kit"])
        self.assertEqual(len(covers), 8)

    def test_the_patch_is_registered_after_model_sync_and_publishes_nothing(self):
        patches = (PKG / "patches.txt").read_text(encoding="utf-8")
        self.assertIn("reckon_saas_platform.patches.seed_guide_blog_drafts", patches)
        self.assertTrue(patches.index("[post_model_sync]") < patches.index("seed_guide_blog_drafts"))
        self.assertIn("seed_guides()", (PKG / "patches" / "seed_guide_blog_drafts.py").read_text(encoding="utf-8"))
        self.assertNotIn("Published", (PKG / "blog_guides.py").read_text(encoding="utf-8").replace("publishes them", ""))


if __name__ == "__main__":
    unittest.main()
