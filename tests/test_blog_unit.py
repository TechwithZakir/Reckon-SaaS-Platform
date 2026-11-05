"""Database-free tests for the blog and the agent that drafts for it."""

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
DEFINITIONS = [
    {"key": "distribution", "label": "Distribution SaaS", "description": "FMCG distribution.", "subscription_features": ["dsr_routes"]},
]
ROWS = [
    {"name": "route-planning-guide", "title": "How to plan FMCG delivery routes", "summary": "A practical guide to planning delivery routes, DSR visits and collections for distributors.",
     "category": "Tutorial", "published_on": "2026-11-03", "modified": "2026-11-04 10:00:00", "related_module": "distribution", "keywords": "routes, FMCG"},
    {"name": "weekly-update-nov", "title": "Weekly update: what is new this week", "summary": "A short weekly roundup of tips for getting more from your ReckonERP workspace this week.",
     "category": "Weekly Update", "published_on": "2026-11-05", "modified": "2026-11-05 09:00:00", "related_module": "", "keywords": ""},
]
BODY = ("## Why routes matter\n\nPlanning routes saves time. See [Distribution](/modules/distribution) and the [FAQ](/faq).\n\n"
        + " ".join(["Route planning keeps trucks full and collections on time."] * 60)
        + "\n\n## Steps\n\n- First step\n- Second step\n\n1. Do this\n2. Do that\n")


def _site(frappe, marketing, rows=()):
    frappe.get_installed_apps = Mock(return_value=["app"])
    frappe.get_hooks = Mock(return_value=[dict(d) for d in DEFINITIONS])
    frappe.db.exists = Mock(return_value=True)
    frappe.utils.nowdate = Mock(return_value="2026-11-05")
    frappe.utils.now_datetime = Mock(return_value="now")
    frappe.utils.cint = lambda v: int(v or 0)
    frappe.get_all = Mock(side_effect=lambda doctype, **kw: list(rows) if doctype == "SEO Article" else [])
    frappe.cache.delete_value("reckon_saas_blog_articles")
    return marketing.get_modules()


class MarkdownTests(unittest.TestCase):
    def test_markdown_is_escaped_and_limited(self):
        with platform_modules("blog") as (_f, (blog,)):
            out = blog.render_markdown(
                "# Title\n\nText with **bold**, *italic*, `code` and <script>alert(1)</script>.\n\n"
                "- one\n- two\n\n1. a\n2. b\n\n```\n<b>raw</b>\n```\n\n[ok](/modules) [ext](https://example.org/x) [bad](javascript:alert(1)) [http](http://x.test)"
            )
        self.assertIn("<h2>Title</h2>", out)
        self.assertIn("<strong>bold</strong>", out)
        self.assertIn("<em>italic</em>", out)
        self.assertIn("<code>code</code>", out)
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIn("<ul><li>one</li><li>two</li></ul>", out)
        self.assertIn("<ol><li>a</li><li>b</li></ol>", out)
        self.assertIn("<pre><code>&lt;b&gt;raw&lt;/b&gt;</code></pre>", out)
        self.assertIn('<a href="/modules">ok</a>', out)
        self.assertIn('<a href="https://example.org/x" rel="nofollow noopener" target="_blank">ext</a>', out)
        self.assertNotIn('href="javascript', out)
        self.assertNotIn('href="http://', out)

    def test_slug_and_reading_time(self):
        with platform_modules("blog") as (_f, (blog,)):
            self.assertEqual(blog.slugify("How to plan FMCG routes, fast!"), "how-to-plan-fmcg-routes-fast")
            self.assertEqual(blog.read_minutes("word " * 450), 2)
            self.assertEqual(blog.read_minutes(""), 1)


class BlogPageTests(unittest.TestCase):
    def test_published_posts_feed_pages_sitemap_rss_and_llms(self):
        with platform_modules("marketing", "blog") as (frappe, (marketing, blog)):
            modules = _site(frappe, marketing, ROWS)
            articles = blog.get_articles()
            index = blog.blog_page(BASE, articles)
            post = blog.article_page(BASE, {**articles[0], "body": BODY}, articles)
            sitemap = marketing.sitemap_xml(BASE, modules)
            rss = blog.rss_xml(BASE, articles)
            llms = marketing.llms_txt(BASE, modules)
            full = marketing.llms_full_txt(BASE, modules)
            home = marketing.home_page(BASE, modules)
            module = marketing.module_page(BASE, modules[0], modules)
        self.assertEqual([a["slug"] for a in articles], ["route-planning-guide", "weekly-update-nov"])
        self.assertFalse(index["noindex"])
        self.assertEqual(index["categories"], ["Tutorial", "Weekly Update"])
        kinds = [json.loads(b)["@type"] for b in post["jsonld"]]
        self.assertEqual(kinds, ["BlogPosting", "BreadcrumbList"])
        ld = json.loads(post["jsonld"][0])
        self.assertEqual((ld["datePublished"], ld["dateModified"]), ("2026-11-03", "2026-11-04"))
        self.assertEqual(ld["author"]["name"], "ReckonERP")
        self.assertEqual(post["canonical"], f"{BASE}/blog/route-planning-guide")
        self.assertLessEqual(len(post["title"]), 70)
        self.assertIn("<h2>Why routes matter</h2>", post["article_html"])
        self.assertEqual([a["slug"] for a in post["related"]], ["weekly-update-nov"])
        self.assertIn(f"<loc>{BASE}/blog</loc>", sitemap)
        self.assertIn(f"<loc>{BASE}/blog/route-planning-guide</loc><lastmod>2026-11-04</lastmod>", sitemap)
        self.assertIn(f"<link>{BASE}/blog/weekly-update-nov</link>", rss)
        self.assertIn("Tue, 03 Nov 2026", rss)
        self.assertIn("## Blog", llms)
        self.assertIn(f"]({BASE}/blog/route-planning-guide)", llms)
        self.assertIn("## Blog", full)
        self.assertEqual(len(home["latest_articles"]), 2)
        self.assertEqual([a["slug"] for a in module["module_articles"]], ["route-planning-guide"])

    def test_an_empty_blog_is_not_indexed_or_in_the_sitemap(self):
        with platform_modules("marketing", "blog") as (frappe, (marketing, blog)):
            modules = _site(frappe, marketing, [])
            page = blog.blog_page(BASE, [])
            sitemap = marketing.sitemap_xml(BASE, modules)
        self.assertTrue(page["noindex"])
        self.assertNotIn("/blog", sitemap)

    def test_unknown_or_unsafe_slugs_have_no_page(self):
        with platform_modules("marketing", "blog") as (frappe, (marketing, blog)):
            _site(frappe, marketing, ROWS)
            self.assertIsNone(blog.get_article("../etc/passwd"))
            self.assertIsNone(blog.get_article("Has Spaces"))
            frappe.get_all = Mock(return_value=[])
            self.assertIsNone(blog.get_article("missing-post"))

    @unittest.skipUnless(jinja2, "jinja2 is not installed")
    def test_blog_pages_render_with_one_h1_robots_and_links(self):
        import html.parser

        class Collect(html.parser.HTMLParser):
            def __init__(self):
                super().__init__()
                self.h1, self.hrefs = 0, []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                self.h1 += tag == "h1"
                if tag == "a" and attrs.get("href"):
                    self.hrefs.append(attrs["href"])

        with platform_modules("marketing", "blog") as (frappe, (marketing, blog)):
            frappe.utils.nowdate = Mock(return_value="2026-11-05")
            modules = _site(frappe, marketing, ROWS)
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(PKG.parent)))

            def render(template, page):
                context = _Dict()
                marketing.apply_context(context, page, modules)
                return env.get_template(f"reckon_saas_platform/www/{template}.html").render(**context)

            articles = blog.get_articles()
            index = render("reckon_blog", blog.blog_page(BASE, articles))
            post = render("reckon_blog", blog.article_page(BASE, {**articles[0], "body": BODY}, articles))
            home = render("index", marketing.home_page(BASE, modules))
            empty = render("reckon_blog", blog.blog_page(BASE, []))
        for html_text in (index, post):
            parser = Collect()
            parser.feed(html_text)
            self.assertEqual(parser.h1, 1)
            self.assertIn("index,follow", html_text)
            self.assertNotIn("frappe", html_text.lower())
        self.assertIn('href="/blog/route-planning-guide"', index)
        self.assertIn("min read", post)
        self.assertIn('<h2>Why routes matter</h2>', post)
        self.assertIn('rel="alternate" type="application/rss+xml"', post)
        self.assertIn("From the blog", home)
        self.assertIn('href="/blog"', home)
        self.assertIn("noindex,follow", empty)
        self.assertIn("Articles are on their way", empty)


class BlogAgentTests(unittest.TestCase):
    def reply(self, title="Plan FMCG delivery routes step by step", summary=None, body=BODY, extra=""):
        summary = summary or "A practical guide to planning delivery routes, DSR visits and collections for FMCG distributors."
        return (
            f"###TITLE###\n{title}\n###SUMMARY###\n{summary}\n###KEYWORDS###\nroutes, FMCG, delivery\n###BODY###\n{body}\n"
            "###LINKEDIN###\nNew guide on route planning. {LINK}\n###FACEBOOK###\nRoute planning made simple. {LINK}\n"
            f"###PITCH###\nHello, we published a guide you may like. {{LINK}}\n{extra}"
        )

    def test_reply_sections_and_article_rules(self):
        with platform_modules("marketing", "seo", "seo_agent", "blog", "blog_agent") as (_f, (_m, _s, _a, blog, agent)):
            parts = agent.parse_sections(self.reply())
            self.assertEqual(set(parts), set(agent.MARKERS))
            self.assertEqual(parts["TITLE"], "Plan FMCG delivery routes step by step")
            self.assertEqual(agent.valid_article(parts["TITLE"], parts["SUMMARY"], parts["BODY"]), "")
            good = (parts["TITLE"], parts["SUMMARY"])
            self.assertIn("20-58", agent.valid_article("Short", good[1], BODY))
            self.assertIn("words", agent.valid_article(*good, "## a\n## b\n[x](/modules) few words"))
            self.assertIn("unverifiable", agent.valid_article(*good, BODY + " This is the best ERP."))
            self.assertIn("unverifiable", agent.valid_article(*good, BODY + " Built on Frappe."))
            self.assertEqual(agent.valid_article(*good, BODY + " Follow best practices."), "")  # a normal phrase is fine
            self.assertIn("two ## sections", agent.valid_article(*good, BODY.replace("## Steps", "Steps")))
            self.assertIn("internal link", agent.valid_article(*good, BODY.replace("](/", "](#")))
            self.assertIn("https", agent.valid_article(*good, BODY + " [x](http://insecure.test)"))
            self.assertEqual(
                agent.categories_for_run(2, 3), [blog.CATEGORIES[3], blog.CATEGORIES[0]]
            )

    def run_writer(self, replies, **settings):
        with platform_modules("marketing", "seo", "seo_agent", "blog", "blog_agent") as (frappe, (marketing, seo, agent, blog, writer)):
            modules = _site(frappe, marketing, [])
            created = []
            frappe.db.exists = Mock(side_effect=lambda doctype, name=None: True if doctype == "DocType" else None)
            frappe.get_doc = Mock(side_effect=lambda values: Mock(insert=lambda ignore_permissions=False: created.append(values)))
            frappe.get_cached_doc = Mock(return_value=_Dict())
            frappe.utils.get_url = Mock(return_value="https://example.test/")
            replies = iter(replies)
            agent.call_model = Mock(side_effect=lambda s, prompt, max_tokens=1500: next(replies))
            conf = _Dict(seo_blog_enabled=1, seo_agent_articles_per_run=1, seo_target_keywords="FMCG route software", **settings)
            pages = seo.collect_pages(BASE, modules, None, None, [])
            frappe.get_all = Mock(return_value=[])
            written = writer.write_articles(conf, pages, modules, ["FMCG route software"], 3)
            return written, created, agent.call_model

    def test_drafts_are_created_unpublished_with_a_promotion_kit(self):
        plan = json.dumps([{"category": "Weekly Update", "title": "Weekly tips", "keyword": "distribution route software", "outline": "a, b"}])
        written, created, call = self.run_writer([plan, self.reply()])
        self.assertEqual(written, ["Plan FMCG delivery routes step by step"])
        doc = created[0]
        self.assertEqual((doc["doctype"], doc["status"], doc["source"], doc["category"]), ("SEO Article", "Draft", "AI", "Weekly Update"))
        self.assertEqual(doc["slug"], "plan-fmcg-delivery-routes-step-by-step")
        self.assertIn("https://", doc["promo_kit"])
        self.assertIn("/blog/plan-fmcg-delivery-routes-step-by-step", doc["promo_kit"])
        self.assertNotIn("{LINK}", doc["promo_kit"])
        for label in ("LinkedIn post:", "Facebook post:", "Outreach pitch:"):
            self.assertIn(label, doc["promo_kit"])
        self.assertEqual(doc["related_module"], "distribution")
        self.assertEqual(call.call_count, 2)  # one plan, one article

    def test_bad_drafts_and_wrong_categories_are_dropped(self):
        wrong = json.dumps([{"category": "Tutorial", "title": "Not asked for", "keyword": "x", "outline": "y"}])
        written, created, call = self.run_writer([wrong])
        self.assertEqual((written, created), ([], []))
        self.assertEqual(call.call_count, 1)
        plan = json.dumps([{"category": "Weekly Update", "title": "Weekly tips", "keyword": "k", "outline": "o"}])
        written, created, _call = self.run_writer([plan, self.reply(body=BODY + " This is the cheapest option.")])
        self.assertEqual((written, created), ([], []))

    def test_blog_writing_is_off_until_enabled(self):
        with platform_modules("marketing", "seo", "seo_agent", "blog", "blog_agent") as (frappe, (marketing, seo, agent, blog, writer)):
            frappe.utils.cint = lambda v: int(v or 0)
            agent.call_model = Mock()
            self.assertEqual(writer.write_articles(_Dict(seo_blog_enabled=0), [], [], [], 1), [])
            agent.call_model.assert_not_called()


class BlogWiringTests(unittest.TestCase):
    def test_routes_doctype_settings_and_permissions(self):
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        for rule in (
            '{"from_route": "/blog", "to_route": "reckon_blog"}',
            '{"from_route": "/blog/rss.xml", "to_route": "reckon_blog_rss.xml"}',
            '{"from_route": "/blog/<slug>", "to_route": "reckon_blog"}',
        ):
            self.assertIn(rule, hooks)
        self.assertLess(hooks.index("/blog/rss.xml"), hooks.index("/blog/<slug>"))
        self.assertIn('"SEO Article": "reckon_saas_platform.saas_security.get_vendor_only_query"', hooks)
        for name in ("reckon_blog.html", "reckon_blog.py", "reckon_blog_rss.xml", "reckon_blog_rss.py"):
            self.assertTrue((PKG / "www" / name).exists(), name)
        doctype = json.loads((PKG / "saas_platform" / "doctype" / "seo_article" / "seo_article.json").read_text(encoding="utf-8"))
        self.assertEqual(doctype["autoname"], "field:slug")
        self.assertEqual(doctype["field_order"], [f["fieldname"] for f in doctype["fields"]])
        status = next(f for f in doctype["fields"] if f["fieldname"] == "status")
        self.assertEqual((status["default"], status["options"].split("\n")[0]), ("Draft", "Draft"))
        settings = json.loads((PKG / "saas_platform" / "doctype" / "saas_platform_settings" / "saas_platform_settings.json").read_text(encoding="utf-8"))
        names = [f["fieldname"] for f in settings["fields"]]
        self.assertEqual(settings["field_order"], names)
        blog_enabled = next(f for f in settings["fields"] if f["fieldname"] == "seo_blog_enabled")
        self.assertEqual(blog_enabled["default"], "0")
        for field in ("seo_agent_articles_per_run", "seo_blog_notes"):
            self.assertIn(field, names)
        header = (PKG / "templates" / "marketing" / "header.html").read_text(encoding="utf-8")
        self.assertIn('href="/blog"', header)
        self.assertTrue(re.search(r"seo_blog_enabled", (PKG / "blog_agent.py").read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
