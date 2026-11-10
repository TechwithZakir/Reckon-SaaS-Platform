"""Links from the product site to the company site, company structured data, the feed and the sitemap dates."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from unittest.mock import Mock

from frappe_stub import _Dict, platform_modules
from test_marketing_site_unit import BASE, REPO_ROOT, _modules, all_pages

try:
    import jinja2
except ModuleNotFoundError:
    jinja2 = None

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"
MODS = ("marketing", "seo", "seo_agent", "blog", "blog_agent", "blog_seed", "blog_guides", "blog_html", "company_links")
COMPANY = "https://www.reckon.tech/"


def load():
    ctx = platform_modules(*MODS)
    frappe, mods = ctx.__enter__()
    return ctx, frappe, dict(zip(MODS, mods, strict=True))


def render(env, template, page, modules, marketing, request_path=None):
    context = _Dict()
    marketing.apply_context(context, page, modules)
    return env.get_template(f"reckon_saas_platform/www/{template}.html").render(**context)


class DataTests(unittest.TestCase):
    def setUp(self):
        ctx, self.frappe, self.by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        self.links = self.by["company_links"]

    def test_every_published_post_title_has_its_company_article(self):
        titles = [p["title"] for p in self.by["blog_seed"].POSTS] + [p["title"] for p in self.by["blog_guides"].GUIDES]
        self.assertEqual(len(titles), 19)
        for title in titles:
            view = self.links.blog_view(title)
            self.assertIsNotNone(view, title)
            self.assertTrue(view["url"].startswith(COMPANY) and view["url"].endswith("/"), view)
            self.assertTrue(view["title"])
        self.assertEqual(len(self.links.BLOG_VIEWS), 19)
        self.assertEqual(len({v[0] for v in self.links.BLOG_VIEWS.values()}), 19)  # each post has its own company article

    def test_matching_ignores_curly_quotes_and_case_and_unmapped_posts_get_nothing(self):
        self.assertEqual(self.links.blog_view("ERP Software in Bangladesh: A Buyer’s Guide")["url"], COMPANY + "erp-selection-consulting-bangladesh/")
        self.assertEqual(self.links.blog_view("  cloud erp vs on-premises erp: how to choose ")["title"], "Cloud or On-Premises ERP: Infrastructure Questions We Ask Every Client")
        self.assertIsNone(self.links.blog_view("A post nobody mapped"))
        self.assertIsNone(self.links.blog_view(""))

    def test_module_help_follows_the_agreed_mapping_with_a_default(self):
        help_for = self.links.module_help
        self.assertEqual(help_for("crm")["url"], COMPANY + "salesforce-consulting-bangladesh/")
        self.assertEqual(help_for("crm")["text"], "Talk to our Salesforce consultants")
        for key in ("accounts", "distribution", "hrms"):
            self.assertEqual(help_for(key)["url"], COMPANY + "service/reckonerp/", key)
            self.assertEqual(help_for(key)["text"], "Implementation, data migration and training by Reckon Technologies")
        self.assertEqual(help_for("sales_agent")["url"], COMPANY + "ai-agent-development/")
        self.assertEqual(help_for("a_future_module")["url"], COMPANY + "contact/")  # no entry needed for a new module
        help_for("crm")["url"] = "changed"
        self.assertNotEqual(help_for("crm")["url"], "changed")  # callers get a copy

    def test_footer_services_and_company_data(self):
        self.assertEqual(
            [url for _label, url in self.links.SERVICES],
            [COMPANY + "salesforce-consulting-bangladesh/", COMPANY + "erpnext-implementation-bangladesh/",
             COMPANY + "ai-agent-development/", COMPANY + "offshore-salesforce-development/"],
        )
        self.assertEqual(self.links.company_org(), {
            "@type": "Organization", "name": "Reckon Technologies Ltd.", "url": COMPANY,
            "sameAs": ["https://www.linkedin.com/company/reckontech", "https://www.facebook.com/reckontechnologies"],
        })

    def test_every_company_link_text_has_a_bangla_version(self):
        bn = self.by["marketing"].marketing_bn
        texts = [label for label, _u in self.links.SERVICES]
        for entry in [*self.links.MODULE_HELP.values(), self.links.DEFAULT_MODULE_HELP]:
            texts += [entry["lead"], entry["text"]]
        texts += ["Services", "Need help implementing it?", "see all industries we serve", "Book a consultation", "Reckon ERP is a product of {company}.",
                  "Implementation for {name} companies by Reckon Technologies"]
        self.assertEqual([t for t in texts if bn.translate(t) == t and t not in bn.BN], [])
        for text in ("Reckon ERP is a product of {company}.", "Implementation for {name} companies by Reckon Technologies"):
            self.assertIn("{", bn.translate(text))  # the slot survives translation


@unittest.skipUnless(jinja2, "jinja2 is not installed")
class RenderTests(unittest.TestCase):
    def setUp(self):
        ctx, self.frappe, self.by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        self.frappe.utils.get_url = Mock(return_value=BASE + "/")
        self.frappe.utils.nowdate = Mock(return_value="2026-11-09")
        self.m = self.by["marketing"]
        self.modules = _modules(self.m, self.frappe)
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(REPO_ROOT)))

    def anchors(self, html):
        return re.findall(r"<a ([^>]*)>(.*?)</a>", html, re.S)

    def test_module_page_has_the_help_box_above_the_final_call_to_action(self):
        module = next(x for x in self.modules if x["key"] == "distribution")
        html = render(self.env, "reckon_modules", self.m.module_page(BASE, module, self.modules), self.modules, self.m)
        self.assertIn("Need help implementing it?", html)
        self.assertIn(f'<a href="{COMPANY}service/reckonerp/">Implementation, data migration and training by Reckon Technologies</a>', html)
        self.assertLess(html.index("Need help implementing it?"), html.index("Start with Distribution SaaS"))
        self.assertNotIn("nofollow", html)

    def test_each_module_shows_its_own_link(self):
        for key, expected in (("sales_agent", "ai-agent-development/"), ("distribution", "service/reckonerp/")):
            module = next(x for x in self.modules if x["key"] == key)
            html = render(self.env, "reckon_modules", self.m.module_page(BASE, module, self.modules), self.modules, self.m)
            self.assertIn(f'href="{COMPANY}{expected}"', html, key)

    def test_industry_page_has_the_line_and_both_links(self):
        from reckon_saas_platform.industries import INDUSTRIES

        industry = INDUSTRIES[0]
        html = render(self.env, "reckon_industries", self.m.industry_page(BASE, industry, self.modules), self.modules, self.m)
        self.assertIn(f"Implementation for {industry['name']} companies by Reckon Technologies", html)
        self.assertIn(f'<a href="{COMPANY}industries/">see all industries we serve</a>', html)
        self.assertIn(f'<a href="{COMPANY}contact/">Book a consultation</a>', html)
        self.assertNotIn("nofollow", html)

    def test_footer_on_every_page_names_the_company_and_lists_services(self):
        for page in (self.m.home_page(BASE, self.modules), self.m.pricing_page(BASE, self.modules)):
            html = render(self.env, "index" if page["path"] == "/" else "reckon_pricing", page, self.modules, self.m)
            self.assertIn(f'Reckon ERP is a product of <a href="{COMPANY}">Reckon Technologies Ltd.</a>.', html)
            for label, url in (("Salesforce consulting", "salesforce-consulting-bangladesh/"), ("ERPNext implementation", "erpnext-implementation-bangladesh/"),
                               ("AI agent development", "ai-agent-development/"), ("Offshore Salesforce development", "offshore-salesforce-development/")):
                self.assertIn(f'<a href="{COMPANY}{url}">{label}</a>', html)
            self.assertNotIn("nofollow", html)
            self.assertEqual(html.count(f'href="{COMPANY}"'), html.count(f'href="{COMPANY}"'))

    def test_bangla_pages_share_the_footer_and_boxes_with_translated_text_and_the_same_addresses(self):
        self.frappe.local.request = Mock(path="/bn/modules/crm")
        module = next(x for x in self.modules if x["key"] == "crm") if any(x["key"] == "crm" for x in self.modules) else self.modules[0]
        html = render(self.env, "reckon_modules", self.m.module_page(BASE, module, self.modules), self.modules, self.m)
        self.assertIn("বাস্তবায়নে সাহায্য লাগবে?", html)
        self.assertIn("Reckon ERP একটি", html)
        self.assertIn(f'href="{COMPANY}"', html)
        self.assertIn("Salesforce কনসাল্টিং", html)
        self.assertIn(f'href="{COMPANY}salesforce-consulting-bangladesh/"', html)  # same address, translated text
        self.assertIn("সেবা", html)

    def test_blog_post_shows_the_consultants_view_only_when_mapped(self):
        blog = self.by["blog"]
        post = self.by["blog_seed"].POSTS[0]
        base_article = {"slug": post["slug"], "title": post["title"], "summary": post["summary"], "category": "Comparison", "published": "2026-11-08",
                        "modified": "2026-11-08", "module": "", "keywords": "", "url": f"/blog/{post['slug']}", "image": "", "body": post["body"]}
        html = render(self.env, "reckon_blog", blog.article_page(BASE, base_article, []), self.modules, self.m)
        self.assertIn("Consultant's view:", html)
        self.assertIn(f'<a href="{COMPANY}cloud-vs-on-premises-erp-infrastructure-questions/">Cloud or On-Premises ERP: Infrastructure Questions We Ask Every Client</a>', html)
        self.assertIn("how Reckon Technologies approaches this in client projects.", html)
        self.assertLess(html.index("Consultant's view:"), html.index("More articles"))
        self.assertNotIn("nofollow", html[html.index("Consultant's view:"):html.index("More articles")])
        unmapped = render(self.env, "reckon_blog", blog.article_page(BASE, {**base_article, "title": "An unmapped post"}, []), self.modules, self.m)
        self.assertNotIn("Consultant's view", unmapped)


class StructuredDataTests(unittest.TestCase):
    def test_company_is_publisher_manufacturer_parent_and_blog_publisher(self):
        ctx, frappe, by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        m, blog, links = by["marketing"], by["blog"], by["company_links"]
        frappe.utils.nowdate = Mock(return_value="2026-11-09")
        frappe.get_cached_doc = Mock(return_value=_Dict(social_profiles=""))
        home = m.home_page(BASE, _modules(m, frappe), None, m.get_profiles())
        blocks = {json.loads(b)["@type"]: json.loads(b) for b in home["jsonld"]}
        company = links.company_org()
        self.assertEqual(blocks["SoftwareApplication"]["publisher"], company)
        self.assertEqual(blocks["SoftwareApplication"]["manufacturer"], company)
        self.assertEqual(blocks["Organization"]["parentOrganization"], company)
        article = {"slug": "x", "title": "T", "summary": "s", "category": "Article", "published": "2026-11-08", "modified": "2026-11-08",
                   "module": "", "keywords": "", "url": "/blog/x", "image": ""}
        self.assertEqual(blog.article_ld(BASE, article)["publisher"], company)

    def test_company_section_in_both_llms_files(self):
        ctx, frappe, by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        m = by["marketing"]
        frappe.utils.nowdate = Mock(return_value="2026-11-09")
        modules = _modules(m, frappe)
        short, full = m.llms_txt(BASE, modules), m.llms_full_txt(BASE, modules)
        self.assertIn(f"## Company\n\n- [Reckon Technologies Ltd.]({COMPANY}): Salesforce Partner in Bangladesh; consulting, ERPNext implementation, AI agent development, IT and custom software", short)
        for url in ("salesforce-consulting-bangladesh/", "erpnext-implementation-bangladesh/", "ai-agent-development/", "offshore-salesforce-development/"):
            self.assertIn(f"]({COMPANY}{url})", short)
            self.assertIn(f"]({COMPANY}{url})", full)
        self.assertIn("## Company", full)


class DescriptionTests(unittest.TestCase):
    def setUp(self):
        ctx, self.frappe, self.by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        self.m = self.by["marketing"]

    def test_the_crm_description_no_longer_repeats_itself(self):
        text = self.m.join_description(
            "Leads, deals and organizations for sales teams, in a private workspace.",
            "Leads, deals and organizations for sales teams, one Company per tenant.",
        )
        self.assertEqual(text, "Leads, deals and organizations for sales teams, in a private workspace.")

    def test_the_more_informative_of_two_overlapping_sentences_wins(self):
        text = self.m.join_description(
            "Routes, deliveries, collections and stock for FMCG distributors.",
            "Bangla-first SR/DSR distribution for FMCG businesses: routes, deliveries, collections and stock in one place.",
        )
        self.assertEqual(text, "Bangla-first SR/DSR distribution for FMCG businesses: routes, deliveries, collections and stock in one place.")

    def test_different_sentences_are_both_kept_and_long_text_is_cut_at_a_word(self):
        self.assertEqual(self.m.join_description("Find leads.", "Approve every message."), "Find leads. Approve every message.")
        long = self.m.join_description("word " * 60)
        self.assertLessEqual(len(long), 160)
        self.assertTrue(long.endswith("..."))
        self.assertEqual(self.m.join_description("", None), "")

    def test_no_page_description_repeats_a_sentence_and_all_fit(self):
        modules = _modules(self.m, self.frappe)
        for page in all_pages(self.m, modules):
            description = page["description"]
            self.assertLessEqual(len(description), 160, page["path"])
            self.assertEqual(self.m.join_description(description, limit=1000), description, f"{page['path']} repeats itself: {description}")


class FeedAndSitemapTests(unittest.TestCase):
    def setUp(self):
        ctx, self.frappe, self.by = load()
        self.addCleanup(ctx.__exit__, None, None, None)
        self.blog, self.m = self.by["blog"], self.by["marketing"]

    def post(self, slug, day, clock="00:00:00", **extra):
        return {"slug": slug, "title": slug.title(), "summary": "s", "category": "Article", "published": day, "published_at": f"{day} {clock}",
                "modified": day, "module": "", "keywords": "", "url": f"/blog/{slug}", "image": "", **extra}

    def test_each_item_carries_its_own_publish_moment_newest_first_and_links_stay_put(self):
        posts = [self.post("old", "2026-11-08", "09:00:00"), self.post("newer", "2026-11-09", "10:15:00"), self.post("newest", "2026-11-09", "17:45:34")]
        xml = self.blog.rss_xml(BASE, posts)
        dates = re.findall(r"<pubDate>([^<]+)</pubDate>", xml)
        self.assertEqual(len(dates), 3)
        self.assertEqual(len(set(dates)), 3)  # no two items share a date any more
        self.assertEqual(re.findall(r"<link>[^<]*/blog/([a-z]+)</link>", xml), ["newest", "newer", "old"])  # newest first
        for date in dates:
            self.assertRegex(date, r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{2} (Nov) 2026 \d{2}:\d{2}:\d{2} [+-]\d{4}$")  # RFC 822
        self.assertIn("17:45:34", dates[0])
        self.assertEqual(re.findall(r'<guid isPermaLink="true">([^<]+)</guid>', xml), re.findall(r"<link>([^<]+)</link>", xml)[1:])  # guid equals link

    def test_a_day_only_post_still_gets_a_valid_date(self):
        xml = self.blog.rss_xml(BASE, [{**self.post("a", "2026-11-08"), "published_at": ""}])
        self.assertRegex(xml, r"<pubDate>Sun, 08 Nov 2026 00:00:00 [+-]\d{4}</pubDate>")

    def test_saved_time_is_used_only_when_it_is_the_publish_day(self):
        row = {"published_on": "2026-11-08", "modified": "2026-11-09 17:45:34.006919"}
        self.assertEqual(self.blog._published_at(row), "2026-11-08 00:00:00")
        row = {"published_on": "2026-11-09", "modified": "2026-11-09 17:45:34.006919"}
        self.assertEqual(self.blog._published_at(row), "2026-11-09 17:45:34")
        self.assertEqual(self.blog._published_at({"published_on": None, "modified": None}), "")

    def test_sitemap_dates_come_from_real_records_and_are_left_out_when_unknown(self):
        record = {"name": "accounts", "module_name": "Accounts", "description": "d", "features": "", "modified": "2026-11-01 10:00:00"}
        self.frappe.utils.nowdate = Mock(return_value="2026-11-09")
        modules = _modules(self.m, self.frappe, records=[record])
        self.m.get_plans = Mock(return_value={"accounts": [{"modified": "2026-11-03"}, {"modified": "2026-11-05"}], "crm": [{"modified": ""}]})
        xml = self.m.sitemap_xml(BASE, modules)
        self.assertIn(f"<loc>{BASE}/modules/accounts</loc><lastmod>2026-11-01</lastmod>", xml)
        self.assertIn(f"<loc>{BASE}/pricing</loc><lastmod>2026-11-05</lastmod>", xml)  # the newest plan edit
        self.assertIn(f"<loc>{BASE}/</loc><lastmod>2026-11-05</lastmod>", xml)  # the home page lists plans, so it follows them
        for path in ("/features", "/faq", "/integrations", "/industries", "/modules"):
            self.assertRegex(xml, rf"<loc>{re.escape(BASE + path)}</loc><xhtml", path)  # no date is invented for code-written pages


if __name__ == "__main__":
    unittest.main()
