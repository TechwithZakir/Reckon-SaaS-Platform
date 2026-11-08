"""The ten comparison posts: quality rules, links, structured data, the closing section and the draft-only seed."""

from __future__ import annotations

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
MODS = ("marketing", "seo", "seo_agent", "blog", "blog_agent", "blog_seed", "blog_html")
DEFINITIONS = [
    {"key": k, "label": k.title(), "description": "d", "subscription_features": []}
    for k in ("distribution", "accounts", "sales_agent", "hrms", "crm")
]


def load():
    ctx = platform_modules(*MODS)
    frappe, mods = ctx.__enter__()
    return ctx, frappe, dict(zip(MODS, mods, strict=True))


class ContentTests(unittest.TestCase):
    def setUp(self):
        ctx, self.frappe, self.by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        self.posts = self.by["blog_seed"].POSTS

    def test_ten_distinct_comparison_posts_that_publish_cleanly(self):
        agent, clean = self.by["blog_agent"], self.by["blog_html"]
        self.assertEqual(len(self.posts), 10)
        self.assertEqual(len({p["slug"] for p in self.posts}), 10)
        self.assertEqual(len({p["title"] for p in self.posts}), 10)
        self.assertEqual(len({p["summary"] for p in self.posts}), 10)
        for post in self.posts:
            slug = post["slug"]
            self.assertRegex(slug, r"^[a-z0-9][a-z0-9-]{2,78}$")
            self.assertTrue(20 <= len(post["title"]) <= 58, slug)
            self.assertTrue(70 <= len(post["summary"]) <= 160, slug)
            words = len(re.findall(r"\w+", clean.plain_text(post["body"])))
            self.assertTrue(350 <= words <= 2200, f"{slug}: {words} words")
            text = post["title"] + post["summary"] + post["body"]
            self.assertIsNone(agent.FORBIDDEN_ARTICLE.search(text), slug)  # the same rule that blocks publishing
            self.assertNotIn("http://", post["body"], slug)
            self.assertFalse(agent.cliches(post["body"]), f"{slug}: {agent.cliches(post['body'])}")

    def test_every_post_opens_with_a_short_answer_and_has_a_table_and_a_faq(self):
        blog, clean = self.by["blog"], self.by["blog_html"]
        for post in self.posts:
            body = post["body"]
            self.assertTrue(body.startswith("<p><strong>Short answer:</strong>"), post["slug"])
            self.assertEqual(body.count("<table>"), 1, post["slug"])
            self.assertGreaterEqual(body.count("<h2>"), 4, post["slug"])
            pairs = blog.extract_faqs(clean.sanitize_html(body))
            self.assertGreaterEqual(len(pairs), 3, post["slug"])
            for question, answer in pairs:
                self.assertTrue(question.endswith("?") and len(answer) > 30, post["slug"])
            kept = clean.sanitize_html(body)
            for tag in ("<table>", "<th>", "<td>", "<h2>", "<ul>"):
                self.assertIn(tag, kept, f"{post['slug']} lost {tag}")

    def test_internal_links_all_resolve_and_posts_link_to_each_other_correctly(self):
        slugs = {p["slug"] for p in self.posts}
        known = {
            "/pricing", "/faq", "/integrations", "/reckonerp-signup", "/features/modular-erp", "/features/reckon-ai-assistant",
            "/features/ai-assisted-selling", "/modules/distribution", "/modules/accounts", "/modules/hrms", "/modules/crm", "/modules/sales_agent",
        } | {f"/blog/{s}" for s in slugs}
        for post in self.posts:
            links = re.findall(r'href="(/[^"]*)"', post["body"])
            self.assertTrue(links, post["slug"])
            for link in links:
                self.assertIn(link, known, f"{post['slug']}: {link}")
            if post["module"]:
                self.assertIn(f"/modules/{post['module']}", links, post["slug"])

    def test_the_site_never_names_competitors_or_the_framework(self):
        for post in self.posts:
            self.assertNotRegex(post["body"].lower(), r"frappe|odoo|\bsap\b|oracle|netsuite|tally prime|zoho|microsoft dynamics", post["slug"])

    def test_enterprise_post_states_multi_currency_multi_language_and_customisation(self):
        post = next(p for p in self.posts if p["slug"] == "standard-vs-customised-erp-for-enterprises")
        for needle in ("Multi-currency", "Multi-language", "easy to customise", "BDT, USD, EUR or INR", "English and Bangla"):
            self.assertIn(needle, post["body"])


class SeedTests(unittest.TestCase):
    def test_drafts_are_created_once_unpublished_with_covers_and_promo_kits(self):
        ctx, frappe, by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        seed = by["blog_seed"]
        frappe.utils.get_url = Mock(return_value=BASE + "/")
        existing = {"cloud-erp-vs-on-premises-erp"}
        frappe.db.exists = Mock(side_effect=lambda doctype, name=None: name in existing)
        made, covers = [], []
        frappe.get_doc = Mock(side_effect=lambda values: Mock(insert=lambda ignore_permissions=False: made.append(values)))
        frappe.db.set_value = Mock()
        image = type("Image", (), {"attach_cover": staticmethod(lambda slug, title, category: covers.append((slug, category)) or f"/files/{slug}-cover.webp")})
        import sys

        sys.modules["reckon_saas_platform.blog_image"] = image
        created = seed.seed_drafts()
        self.assertEqual(len(created), 9)  # the one that already exists is left alone
        self.assertNotIn("cloud-erp-vs-on-premises-erp", created)
        for values in made:
            self.assertEqual((values["doctype"], values["status"], values["category"], values["source"]), ("SEO Article", "Draft", "Comparison", "Manual"))
            self.assertIn(f"{BASE}/blog/{values['slug']}", values["promo_kit"])
            for label in ("LinkedIn post:", "Facebook post:", "Outreach pitch:"):
                self.assertIn(label, values["promo_kit"])
        self.assertEqual({c for _s, c in covers}, {"Comparison"})
        self.assertEqual(len(covers), 9)
        self.assertEqual(frappe.db.set_value.call_count, 9)

    def test_a_cover_failure_never_loses_the_draft(self):
        ctx, frappe, by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        frappe.utils.get_url = Mock(return_value=BASE + "/")
        frappe.db.exists = Mock(return_value=None)
        made = []
        frappe.get_doc = Mock(side_effect=lambda values: Mock(insert=lambda ignore_permissions=False: made.append(values)))
        image = type("Image", (), {"attach_cover": staticmethod(lambda *a: (_ for _ in ()).throw(RuntimeError("no pillow")))})
        import sys

        sys.modules["reckon_saas_platform.blog_image"] = image
        self.assertEqual(len(by["blog_seed"].seed_drafts()), 10)
        self.assertEqual(len(made), 10)
        self.assertEqual(frappe.log_error.call_count, 10)

    def test_the_patch_runs_once_through_patches_txt_and_publishes_nothing(self):
        patches = (PKG / "patches.txt").read_text(encoding="utf-8")
        self.assertIn("reckon_saas_platform.patches.seed_comparison_blog_drafts", patches)
        self.assertTrue(patches.index("[post_model_sync]") < patches.index("seed_comparison_blog_drafts"))
        source = (PKG / "patches" / "seed_comparison_blog_drafts.py").read_text(encoding="utf-8")
        self.assertIn("seed_drafts()", source)
        self.assertNotIn("Published", (PKG / "blog_seed.py").read_text(encoding="utf-8").replace("publishes it", ""))

    def test_comparison_is_a_category_of_the_article_form_cover_and_agent(self):
        article = json.loads((PKG / "seo_agent_studio" / "doctype" / "seo_article" / "seo_article.json").read_text(encoding="utf-8"))
        category = next(f for f in article["fields"] if f["fieldname"] == "category")
        self.assertIn("Comparison", category["options"].split("\n"))
        ctx, _frappe, by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        self.assertIn("Comparison", by["blog"].CATEGORIES)
        self.assertIn("Comparison", by["blog_agent"].CATEGORY_BRIEF)


class PageTests(unittest.TestCase):
    def test_post_page_has_faq_and_article_structured_data(self):
        ctx, frappe, by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        marketing, blog, seed = by["marketing"], by["blog"], by["blog_seed"]
        post = seed.POSTS[0]
        article = {"slug": post["slug"], "title": post["title"], "summary": post["summary"], "category": "Comparison", "published": "2026-11-08",
                   "modified": "2026-11-08", "module": "", "keywords": post["keywords"], "url": f"/blog/{post['slug']}", "image": "/files/x-cover.webp", "body": post["body"]}
        frappe.utils.get_url = Mock(return_value=BASE + "/")
        page = marketing.make_page  # keep a reference so the call below is explicit
        self.assertTrue(callable(page))
        result = blog.article_page(BASE, article, [])
        kinds = [json.loads(b)["@type"] for b in result["jsonld"]]
        self.assertEqual(sorted(kinds), ["BlogPosting", "BreadcrumbList", "FAQPage"])
        faq = next(json.loads(b) for b in result["jsonld"] if '"FAQPage"' in b)
        self.assertGreaterEqual(len(faq["mainEntity"]), 3)
        self.assertEqual(result["og_image"], f"{BASE}/files/x-cover.webp")

    @unittest.skipUnless(jinja2, "jinja2 is not installed")
    def test_every_post_ends_with_the_company_section_services_and_contact(self):
        ctx, frappe, by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        marketing, blog, seed = by["marketing"], by["blog"], by["blog_seed"]
        frappe.utils.get_url = Mock(return_value=BASE + "/")
        frappe.utils.nowdate = Mock(return_value="2026-11-08")
        frappe.get_installed_apps = Mock(return_value=["app"])
        frappe.get_hooks = Mock(return_value=[dict(d) for d in DEFINITIONS])
        frappe.db.exists = Mock(return_value=True)
        frappe.get_all = Mock(return_value=[])
        modules = marketing.get_modules()
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(PKG.parent)))
        post = seed.POSTS[-1]
        article = {"slug": post["slug"], "title": post["title"], "summary": post["summary"], "category": "Comparison", "published": "2026-11-08",
                   "modified": "2026-11-08", "module": "", "keywords": "", "url": f"/blog/{post['slug']}", "image": "/files/x-cover.webp", "body": post["body"]}
        context = _Dict()
        marketing.apply_context(context, blog.article_page(BASE, article, []), modules)
        html = env.get_template("reckon_saas_platform/www/reckon_blog.html").render(**context)
        body_end = html.index("ReckonERP by Reckon Technologies Ltd.")
        self.assertGreater(body_end, html.index("Frequently asked questions"))  # the company section closes the article
        for needle in ("Our services", "Multi-currency", "Multi-language", "Easy to customise", "We solve it best with our expertise", "hello@reckon.tech",
                       "+8801325-009955", "https://wa.me/8801325009955", "www.reckon.tech", 'class="cover"', "<table>", "Start free"):
            self.assertIn(needle, html, needle)
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)
        self.assertNotIn("frappe", html.lower())
        home = env.get_template("reckon_saas_platform/www/index.html")
        home_context = _Dict()
        marketing.apply_context(home_context, marketing.home_page(BASE, modules), modules)
        home_html = home.render(**home_context)
        for needle in ("Our services", "Multi-currency", "Multi-language", "Easy to customise"):
            self.assertIn(needle, home_html, needle)

    def test_services_and_summary_state_the_requested_strengths(self):
        ctx, _frappe, by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        marketing = by["marketing"]
        titles = [t for t, _x in marketing.SERVICES]
        for expected in ("Multi-currency", "Multi-language", "Easy to customise", "Dedicated cloud or on-premises", "Implementation and training"):
            self.assertIn(expected, titles)
        custom = dict(marketing.SERVICES)["Easy to customise"]
        self.assertIn("enterprise package", custom)
        self.assertIn("worldwide", marketing.COMPANY_SUMMARY)
        self.assertNotIn("frappe", (marketing.COMPANY_SUMMARY + marketing.EXPERTISE).lower())


if __name__ == "__main__":
    unittest.main()
