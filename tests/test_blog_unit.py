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
        self.assertIn('<h2 id="why-routes-matter">Why routes matter</h2>', post["article_html"])
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
        self.assertIn('<h2 id="why-routes-matter">Why routes matter</h2>', post)
        self.assertIn('class="standfirst"', post)
        self.assertIn('By the ReckonERP team', post)
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
                agent.categories_for_run(2, 3), [blog.CATEGORIES[3], blog.CATEGORIES[4]]
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


try:
    import PIL.Image as _PILImage
except ModuleNotFoundError:  # CI installs only ruff; the drawing tests run where Pillow exists.
    _PILImage = None


class HumanVoiceAndCoverTests(unittest.TestCase):
    def test_stock_phrases_are_found_and_tidied(self):
        with platform_modules("marketing", "seo", "seo_agent", "blog", "blog_agent") as (_f, (_m, _s, _a, _b, agent)):
            found = agent.cliches("In today's fast-paced world we leverage a seamless, robust tool. Moreover, it's important to note this.")
            self.assertGreaterEqual(len(found), 5)
            self.assertEqual(agent.cliches("We plan routes at 6am and check stock before loading the van."), [])
            self.assertEqual(agent.tidy("Plan routes — then load the van — and go."), "Plan routes, then load the van, and go.")
            self.assertIn("first person plural", agent.STYLE)
            self.assertIn("Do not invent customers", agent.STYLE)

    def test_one_cleanup_call_only_when_stock_phrases_are_present(self):
        clean = BODY
        stock = BODY + " We leverage a seamless approach."
        with platform_modules("marketing", "seo", "seo_agent", "blog", "blog_agent") as (_f, (_m, _s, seo_agent, _b, agent)):
            seo_agent.call_model = Mock(return_value=BODY + " We use a simple approach.")
            body, left = agent.humanise(_Dict(), clean)
            self.assertEqual((body, left), (clean, []))
            seo_agent.call_model.assert_not_called()
            body, left = agent.humanise(_Dict(), stock)
            self.assertEqual(left, [])
            self.assertIn("simple approach", body)
            self.assertEqual(seo_agent.call_model.call_count, 1)
            self.assertIn("leverage", seo_agent.call_model.call_args.args[1])
            # When the monthly cap stops the call, the draft is kept and the phrases are reported.
            seo_agent.call_model = Mock(side_effect=seo_agent.AgentLimit("cap"))
            body, left = agent.humanise(_Dict(), stock)
            self.assertEqual(body, stock)
            self.assertTrue(left)

    def test_monthly_cadence_skips_scheduled_runs_but_not_the_button(self):
        plan = json.dumps([{"category": "Weekly Update", "title": "Weekly tips", "keyword": "distribution", "outline": "a"}])
        with platform_modules("marketing", "seo", "seo_agent", "blog", "blog_agent") as (frappe, (marketing, seo, agent, blog, writer)):
            modules = _site(frappe, marketing, [])
            frappe.get_all = Mock(return_value=["existing-ai-draft"])  # an AI draft already exists this month
            agent.call_model = Mock(side_effect=AssertionError("must not call the model"))
            conf = _Dict(seo_blog_enabled=1, seo_blog_frequency="Monthly", seo_agent_articles_per_run=1)
            self.assertEqual(writer.write_articles(conf, [], modules, [], 3), [])
            filters = frappe.get_all.call_args.kwargs["filters"]
            self.assertEqual((filters["source"], filters["creation"]), ("AI", [">=", "2026-11-01"]))
            # Weekly frequency and forced runs do not check the month.
            frappe.get_all = Mock(return_value=[])
            replies = iter([plan, "no markers here"])
            agent.call_model = Mock(side_effect=lambda s, prompt, max_tokens=1500: next(replies))
            writer.write_articles(_Dict(seo_blog_enabled=1, seo_blog_frequency="Weekly", seo_agent_articles_per_run=1), [], modules, [], 3)
            self.assertEqual(agent.call_model.call_count, 2)

    def test_each_draft_gets_a_cover_and_a_failed_cover_does_not_lose_the_post(self):
        plan = json.dumps([{"category": "Weekly Update", "title": "Weekly tips", "keyword": "distribution", "outline": "a"}])
        reply = BlogAgentTests().reply()
        for cover_result in ("/files/plan-fmcg-delivery-routes-step-by-step-cover.webp", RuntimeError("no pillow")):
            with platform_modules("marketing", "seo", "seo_agent", "blog", "blog_image", "blog_agent") as (frappe, (marketing, seo, agent, blog, image, writer)):
                modules = _site(frappe, marketing, [])
                frappe.db.exists = Mock(side_effect=lambda doctype, name=None: True if doctype == "DocType" else None)
                frappe.get_doc = Mock(return_value=Mock())
                frappe.db.set_value = Mock()
                frappe.utils.get_url = Mock(return_value="https://example.test/")
                frappe.get_all = Mock(return_value=[])
                agent.call_model = Mock(side_effect=[plan, reply])
                image.attach_cover = Mock(side_effect=[cover_result]) if isinstance(cover_result, Exception) else Mock(return_value=cover_result)
                written = writer.write_articles(_Dict(seo_blog_enabled=1, seo_blog_frequency="Weekly"), [], modules, [], 3)
                self.assertEqual(written, ["Plan FMCG delivery routes step by step"])
                if isinstance(cover_result, Exception):
                    frappe.log_error.assert_called()
                else:
                    frappe.db.set_value.assert_called_once_with("SEO Article", "plan-fmcg-delivery-routes-step-by-step", "cover_image", cover_result)

    def test_cover_urls_must_be_files_and_reach_cards_posts_and_social_previews(self):
        row = dict(ROWS[0], cover_image="/files/route-planning-guide-cover.webp")
        bad = dict(ROWS[1], cover_image="/files/evil.svg")
        with platform_modules("marketing", "blog") as (frappe, (marketing, blog)):
            _site(frappe, marketing, [row, bad])
            articles = blog.get_articles()
            page = blog.article_page(BASE, {**articles[0], "body": BODY}, articles)
        self.assertEqual(articles[0]["image"], "/files/route-planning-guide-cover.webp")
        self.assertEqual(articles[1]["image"], "")  # an svg or foreign path is never used
        self.assertEqual(page["og_image"], f"{BASE}/files/route-planning-guide-cover.webp")
        self.assertEqual(json.loads(page["jsonld"][0])["image"], f"{BASE}/files/route-planning-guide-cover.webp")

    @unittest.skipUnless(_PILImage, "Pillow is not installed")
    def test_cover_is_drawn_for_every_kind_and_long_titles(self):
        import io

        with platform_modules("blog", "blog_image") as (_f, (blog, image)):
            for category in blog.CATEGORIES:
                data = image.make_cover("How to plan FMCG delivery routes and collections without the spreadsheet chaos", category)
                picture = _PILImage.open(io.BytesIO(data))
                self.assertEqual((picture.size, picture.format), ((1200, 630), "WEBP"))
            self.assertLess(len(data), 200_000)


class RichTextTests(unittest.TestCase):
    def test_editor_html_is_cleaned_to_an_allow_list(self):
        with platform_modules("blog_html") as (_f, (clean,)):
            dirty = (
                '<div class="ql-editor read-mode"><h1>Big</h1><p onclick="x()">Hi <b>there</b> <i>you</i></p>'
                '<script>alert(1)</script><style>p{}</style><iframe src="https://evil.test"></iframe>'
                '<a href="javascript:alert(1)">bad</a> <a href="/modules">ok</a> <a href="https://example.org/x" onmouseover="y()">ext</a> '
                '<a href="http://insecure.test">http</a><img src="https://example.org/a.png" alt="A" width="300" onerror="z()">'
                '<img src="javascript:alert(1)"><ul><li>one<li>two</ul><table><tr><td colspan="2">c</td></tr></table>'
                '<p>unclosed <strong>bold</div></div>'
            )
            out = clean.sanitize_html(dirty)
        self.assertNotIn("<script", out)
        self.assertNotIn("alert(1)", out)
        self.assertNotIn("onclick", out)
        self.assertNotIn("onerror", out)
        self.assertNotIn("onmouseover", out)
        self.assertNotIn("iframe", out)
        self.assertNotIn("<style", out)
        self.assertNotIn("<div", out)
        self.assertNotIn("javascript:", out)
        self.assertNotIn("http://", out)
        self.assertIn("<h2>Big</h2>", out)  # a second h1 never reaches the page
        self.assertIn("<strong>there</strong>", out)
        self.assertIn("<em>you</em>", out)
        self.assertIn('<a href="/modules">ok</a>', out)
        self.assertIn('<a href="https://example.org/x" rel="nofollow noopener" target="_blank">ext</a>', out)
        self.assertIn('<img src="https://example.org/a.png" alt="A" width="300" loading="lazy" decoding="async">', out)
        self.assertEqual(out.count("<img"), 1)
        self.assertIn('<td colspan="2">c</td>', out)
        self.assertTrue(out.endswith("</strong></p>"))  # tags left open are closed

    def test_html_posts_use_the_sanitizer_and_markdown_posts_still_render(self):
        with platform_modules("blog") as (_f, (blog,)):
            html_out = blog.render_body("<p>Hello <script>x()</script><strong>world</strong></p>")
            md_out = blog.render_body("## Heading\n\nSome **bold** text.")
            minutes = blog.read_minutes("<p>" + "word " * 450 + "</p>")
        self.assertEqual(html_out, "<p>Hello <strong>world</strong></p>")
        self.assertIn("<h2>Heading</h2>", md_out)
        self.assertIn("<strong>bold</strong>", md_out)
        self.assertEqual(minutes, 2)  # tags are not counted as words

    def test_words_are_counted_without_tags_and_the_body_field_is_a_rich_text_editor(self):
        import json as _json

        with platform_modules("marketing", "seo", "seo_agent", "blog", "blog_agent") as (_f, (_m, _s, _a, _b, agent)):
            self.assertEqual(agent.word_count("<p>one two</p><ul><li>three</li></ul>"), 3)
        doctype = _json.loads((PKG / "seo_agent_studio" / "doctype" / "seo_article" / "seo_article.json").read_text(encoding="utf-8"))
        body = next(f for f in doctype["fields"] if f["fieldname"] == "body")
        self.assertEqual(body["fieldtype"], "Text Editor")

    def test_agent_drafts_are_stored_as_html_for_the_editor(self):
        plan = json.dumps([{"category": "Weekly Update", "title": "Weekly tips", "keyword": "distribution", "outline": "a"}])
        with platform_modules("marketing", "seo", "seo_agent", "blog", "blog_agent") as (frappe, (marketing, seo, agent, blog, writer)):
            modules = _site(frappe, marketing, [])
            created = []
            frappe.db.exists = Mock(side_effect=lambda doctype, name=None: True if doctype == "DocType" else None)
            frappe.get_doc = Mock(side_effect=lambda values: Mock(insert=lambda ignore_permissions=False: created.append(values)))
            frappe.utils.get_url = Mock(return_value="https://example.test/")
            frappe.get_all = Mock(return_value=[])
            agent.call_model = Mock(side_effect=[plan, BlogAgentTests().reply()])
            writer.write_articles(_Dict(seo_blog_enabled=1, seo_blog_frequency="Weekly"), [], modules, [], 3)
        body = created[0]["body"]
        self.assertIn("<h2>Why routes matter</h2>", body)
        self.assertIn('<a href="/modules/distribution">Distribution</a>', body)
        self.assertNotIn("## ", body)


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
        doctype = json.loads((PKG / "seo_agent_studio" / "doctype" / "seo_article" / "seo_article.json").read_text(encoding="utf-8"))
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
        self.assertIn('u("/blog")', header)
        self.assertTrue(re.search(r"seo_blog_enabled", (PKG / "blog_agent.py").read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
