"""Database-free tests for the public marketing site: pages, SEO data, links and crawler files."""

from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from unittest.mock import Mock

from frappe_stub import REPO_ROOT, _Dict, platform_modules

try:
    import jinja2
except ModuleNotFoundError:  # CI installs only ruff; the render tests run where jinja2 exists.
    jinja2 = None

BASE = "https://example.test"
PKG = REPO_ROOT / "reckon_saas_platform"

# The three real registrations (labels and feature keys as the product apps publish them).
DEFINITIONS = [
    {
        "key": "distribution",
        "label": "Distribution SaaS",
        "description": "Bangla-first SR/DSR distribution for FMCG businesses.",
        "subscription_features": ["dsr_routes", "bangla_pwa", "unknown_future_feature"],
    },
    {
        "key": "accounts",
        "label": "Accounts",
        "description": "Sales, purchase, stock and accounting for any small business.",
        "subscription_features": ["stock_and_warehouses"],
    },
    {
        "key": "sales_agent",
        "label": "Sales AI Agent",
        "description": "Find, research and qualify B2B customers in Bangladesh.",
        "subscription_features": ["frappe_crm_sync"],
    },
]


def _modules(marketing, frappe, definitions=DEFINITIONS, disabled=(), records=()):
    """Modules as the site would list them; ``records`` are SaaS Module rows."""
    frappe.get_installed_apps = Mock(return_value=["app"])
    frappe.get_hooks = Mock(return_value=[dict(d) for d in definitions])
    frappe.db.exists = Mock(return_value=True)
    rows = [_Dict(name=name, enabled=0) for name in disabled]
    rows += [_Dict({"enabled": 1, **row}) for row in records]
    frappe.get_all = Mock(return_value=rows)
    return marketing.get_modules()


def all_pages(marketing, modules):
    pages = [
        marketing.home_page(BASE, modules),
        marketing.features_page(BASE),
        marketing.modules_page(BASE, modules),
        marketing.integrations_page(BASE),
    ]
    pages += [marketing.feature_page(BASE, f) for f in marketing.FEATURE_LIST]
    pages += [marketing.module_page(BASE, m, modules) for m in modules]
    return pages


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.h1 = [], 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if tag in ("a", "img", "link") and (attrs.get("href") or attrs.get("src")):
            self.hrefs.append(attrs.get("href") or attrs.get("src"))


class MarketingDataTests(unittest.TestCase):
    def test_site_never_names_the_framework(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = _modules(marketing, frappe)
            pages = all_pages(marketing, modules)
            text = json.dumps(pages, default=str) + marketing.llms_txt(BASE, modules)
            text += marketing.robots_txt(BASE) + marketing.sitemap_xml(BASE, modules)
        self.assertNotIn("frappe", text.lower())

    def test_family_products_are_listed_on_the_modules_page(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = _modules(marketing, frappe)
            page = marketing.modules_page(BASE, modules)
            llms = marketing.llms_txt(BASE, modules)
            slugs = {f["slug"] for f in marketing.FEATURE_LIST}
        names = [a["name"] for a in page["family"]]
        for expected in ("Reckon AI assistant", "Reckon CRM", "Reckon Constructions", "Reckon Real Estate", "Reckon HRMS"):
            self.assertIn(expected, names)
            self.assertIn(expected, llms)
        for app in page["family"]:
            if app.get("url"):
                self.assertIn(app["url"].rsplit("/", 1)[1], slugs)

    def test_signed_in_users_go_to_their_module_not_the_marketing_page(self):
        with platform_modules("marketing", "module_registry", "saas", "saas_gate", "saas_security") as (
            frappe,
            (marketing, registry, saas, gate, security),
        ):
            frappe.get_installed_apps = Mock(return_value=["app"])
            hooks = {
                "reckon_saas_modules": [dict(DEFINITIONS[0], home_route="/desk/distribution")],
                "get_website_user_home_page": [],
            }
            frappe.get_hooks = Mock(side_effect=lambda name, app_name=None: hooks.get(name, []))
            self.assertIsNone(marketing.landing_for_user("Guest"))
            self.assertIsNone(marketing.landing_for_user(None))

            saas.get_user_module_keys = Mock(return_value=["distribution"])
            gate.is_user_gated = Mock(return_value=False)
            security.is_vendor_user = Mock(return_value=False)
            self.assertEqual(marketing.landing_for_user("owner@example.test"), "/desk/distribution")

            gate.is_user_gated = Mock(return_value=True)
            self.assertEqual(marketing.landing_for_user("owner@example.test"), "/reckonerp-subscription")

            security.is_vendor_user = Mock(return_value=True)
            self.assertEqual(marketing.landing_for_user("vendor@example.test"), "/reckon-saas-admin")

            security.is_vendor_user = Mock(return_value=False)
            gate.is_user_gated = Mock(return_value=False)
            saas.get_user_module_keys = Mock(return_value=[])
            self.assertEqual(marketing.landing_for_user("staff@example.test"), "/desk")

            # A module app that claims the user wins, and bare routes get a leading slash.
            hooks["get_website_user_home_page"] = ["x.home"]
            frappe.get_attr = Mock(return_value=lambda user: "desk/sales-agent")
            self.assertEqual(marketing.landing_for_user("rep@example.test"), "/desk/sales-agent")

    def test_home_page_redirects_signed_in_users(self):
        import importlib.util

        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.Redirect = type("Redirect", (Exception,), {})
            frappe.session = _Dict(user="owner@example.test")
            frappe.local.flags = _Dict()
            marketing.landing_for_user = Mock(return_value="/desk/distribution")
            spec = importlib.util.spec_from_file_location("home_page_under_test", PKG / "www" / "index.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with self.assertRaises(frappe.Redirect):
                module.get_context(_Dict())
            self.assertEqual(frappe.local.flags.redirect_location, "/desk/distribution")

    def test_modules_come_from_the_registry(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = _modules(marketing, frappe)
        self.assertEqual([m["key"] for m in modules], ["distribution", "accounts", "sales_agent"])
        distribution = modules[0]
        self.assertEqual(distribution["url"], "/modules/distribution")
        self.assertEqual(
            distribution["features"],
            ["DSR route planning and delivery tracking", "Bangla-first mobile app", "Unknown future feature"],
        )
        self.assertTrue(distribution["benefits"])

    def test_module_switched_off_for_sale_has_no_page(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = _modules(marketing, frappe, disabled=["accounts"])
        self.assertEqual([m["key"] for m in modules], ["distribution", "sales_agent"])

    def test_vendor_edited_module_record_wins_over_the_hook(self):
        record = {
            "name": "accounts",
            "module_name": "Reckon Books",
            "description": "Edited by the vendor.",
            "features": "stock_and_warehouses\ncustom_thing",
        }
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = _modules(marketing, frappe, records=[record])
        accounts = modules[1]
        self.assertEqual(accounts["name"], "Reckon Books")
        self.assertEqual(accounts["description"], "Edited by the vendor.")
        self.assertEqual(accounts["features"], ["Stock and warehouses", "Custom thing"])

    def test_apps_can_publish_integrations(self):
        published = [
            {"name": "Acme Pay", "group": "email", "glyph": "billing", "color": "#123456"},
            {"name": "whatsapp", "group": "messaging"},
            {"name": "Odd", "group": "nope", "glyph": "bad", "color": "red", "mark": "ab"},
        ]
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.get_installed_apps = Mock(return_value=["app"])
            frappe.get_hooks = Mock(return_value=[published])
            items = marketing.get_integrations()
            builtin = len(marketing.INTEGRATIONS_LIST)
        self.assertEqual(len(items), builtin + 2)
        acme = next(i for i in items if i["name"] == "Acme Pay")
        self.assertEqual((acme["group"], acme["glyph"], acme["color"]), ("email", "billing", "#123456"))
        odd = next(i for i in items if i["name"] == "Odd")
        self.assertEqual((odd["group"], odd["mark"], odd["color"]), ("platform", "ab", "#475569"))

    def test_module_without_written_copy_still_gets_a_page(self):
        extra = {"key": "payroll", "label": "Payroll", "description": "Pay your team."}
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = _modules(marketing, frappe, definitions=[extra])
            page = marketing.module_page(BASE, modules[0], modules)
        self.assertEqual(page["h1"], "Payroll")
        self.assertEqual(page["canonical"], f"{BASE}/modules/payroll")

    def test_titles_and_descriptions_are_unique_and_sized(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            pages = all_pages(marketing, _modules(marketing, frappe))
        titles = [p["title"] for p in pages]
        descriptions = [p["description"] for p in pages]
        self.assertEqual(len(set(titles)), len(titles))
        self.assertEqual(len(set(descriptions)), len(descriptions))
        for page in pages:
            self.assertLessEqual(len(page["title"]), 70, page["title"])
            self.assertTrue(50 <= len(page["description"]) <= 160, page["description"])
            self.assertEqual(page["canonical"], BASE + page["path"])

    def test_json_ld_is_valid_and_matches_the_page(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = _modules(marketing, frappe)
            home = marketing.home_page(BASE, modules)
            module = marketing.module_page(BASE, modules[0], modules)
            features = marketing.features_page(BASE)
        kinds = lambda page: [json.loads(b)["@type"] for b in page["jsonld"]]  # noqa: E731
        self.assertEqual(kinds(home), ["Organization", "SoftwareApplication", "FAQPage"])
        self.assertEqual(json.loads(home["jsonld"][0])["email"], "hello@reckon.tech")
        self.assertEqual(kinds(module), ["SoftwareApplication", "FAQPage", "BreadcrumbList"])
        self.assertEqual(kinds(features), ["BreadcrumbList"])
        crumbs = json.loads(module["jsonld"][-1])["itemListElement"]
        self.assertEqual([c["position"] for c in crumbs], [1, 2, 3])
        self.assertEqual(crumbs[-1]["item"], f"{BASE}/modules/distribution")

    def test_json_ld_cannot_close_the_script_tag(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            text = marketing.dumps_ld({"name": "</script><b>"})
        self.assertNotIn("</", text)
        self.assertEqual(json.loads(text)["name"], "</script><b>")

    def test_sitemap_lists_every_public_page_on_the_given_domain(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = _modules(marketing, frappe)
            xml = marketing.sitemap_xml(BASE, modules)
            paths = marketing.public_paths(modules)
        locs = re.findall(r"<loc>([^<]+)</loc>", xml)
        self.assertEqual(locs, [BASE + p for p in paths])
        self.assertIn(f"{BASE}/reckonerp-signup", locs)
        self.assertIn(f"{BASE}/modules/sales_agent", locs)
        self.assertEqual(len(locs), len(set(locs)))

    def test_robots_welcomes_search_and_ai_crawlers_and_hides_the_app(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            text = marketing.robots_txt(BASE)
        for agent in ("*", "Googlebot", "GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended"):
            self.assertIn(f"User-agent: {agent}\n", text)
        self.assertIn("Allow: /\n", text)
        self.assertIn("Disallow: /app\n", text)
        self.assertNotIn("Disallow: /\n", text)
        self.assertTrue(text.rstrip().endswith(f"Sitemap: {BASE}/sitemap.xml"))

    def test_llms_txt_summarises_the_product_with_absolute_links(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            text = marketing.llms_txt(BASE, _modules(marketing, frappe))
        self.assertTrue(text.startswith("# ReckonERP\n\n> "))
        for expected in ("/modules/distribution", "/features/modular-erp", "/integrations", "/reckonerp-signup"):
            self.assertIn(f"]({BASE}{expected})", text)

    def test_integrations_cover_the_sales_agent_channels(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            names = {i["name"] for i in marketing.INTEGRATIONS_LIST}
            glyphs = marketing.GLYPHS
            items = marketing.INTEGRATIONS_LIST
        for expected in (
            "WhatsApp", "Facebook Messenger", "Instagram", "LinkedIn", "Twilio", "Brevo",
            "Twilio SendGrid", "Email", "Google Search", "Google Places", "BulkSMSBD",
        ):
            self.assertIn(expected, names)
        for item in items:
            self.assertTrue(item.get("mark") or item["glyph"] in glyphs, item)
            self.assertRegex(item["color"], r"^#[0-9a-f]{6}$")

    def test_feature_slugs_are_unique_url_safe_and_have_icons(self):
        with platform_modules("marketing") as (_frappe, (marketing,)):
            slugs = [f["slug"] for f in marketing.FEATURE_LIST]
            icons = [f["icon"] for f in marketing.FEATURE_LIST]
            glyphs = marketing.GLYPHS
        self.assertEqual(len(set(slugs)), len(slugs))
        for slug in slugs:
            self.assertRegex(slug, r"^[a-z0-9-]+$")
        self.assertTrue(set(icons) <= set(glyphs))

    def test_requested_reads_the_rule_match_or_the_url(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.form_dict = _Dict(slug="Modular-ERP")
            self.assertEqual(marketing.requested("slug"), "modular-erp")
            frappe.form_dict = _Dict()
            frappe.local.request = _Dict(path="/modules/distribution")
            self.assertEqual(marketing.requested("slug"), "distribution")
            frappe.local.request = _Dict(path="/modules")
            self.assertEqual(marketing.requested("slug"), "")


class MarketingWiringTests(unittest.TestCase):
    def test_routes_and_home_page_are_declared(self):
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('home_page = "index"', hooks)
        for source, target in (
            ("/features/<slug>", "reckon_features"),
            ("/modules/<slug>", "reckon_modules"),
            ("/integrations", "reckon_integrations"),
            ("/sitemap.xml", "reckon_sitemap.xml"),
            ("/robots.txt", "reckon_robots.txt"),
            ("/llms.txt", "reckon_llms.txt"),
            ("/reckonerp-signup", "reckonerp_signup"),
        ):
            self.assertIn(f'{{"from_route": "{source}", "to_route": "{target}"}}', hooks)
            if not target.endswith((".xml", ".txt")):
                self.assertTrue((PKG / "www" / f"{target}.html").exists(), target)
        for name in ("index", "reckon_sitemap", "reckon_robots", "reckon_llms"):
            self.assertTrue((PKG / "www" / f"{name}.py").exists(), name)

    def test_signup_page_exists_for_the_signup_link(self):
        self.assertTrue((PKG / "www" / "reckonerp_signup.html").exists())

    def test_no_production_domain_is_hard_coded(self):
        scanned = [PKG / "marketing.py", *(PKG / "templates" / "marketing").iterdir()]
        scanned += [p for p in (PKG / "www").glob("*") if p.stem.startswith(("index", "reckon_"))]
        for path in scanned:
            if path.suffix not in (".py", ".html", ".css", ".txt", ".xml"):
                continue
            text = path.read_text(encoding="utf-8")
            # The company's own website is a deliberate outbound link, not this site's address.
            text = text.replace("https://www.reckon.tech/", "").replace("hello@reckon.tech", "")
            self.assertNotRegex(text, r"https?://[a-z0-9.-]*reckon", path.name)
            self.assertNotIn("distribution.reckon", text, path.name)
            self.assertNotIn("app.reckon", text, path.name)

    def test_machine_readable_pages_only_echo_a_body(self):
        for name in ("reckon_sitemap.xml", "reckon_robots.txt", "reckon_llms.txt"):
            self.assertEqual((PKG / "www" / name).read_text(encoding="utf-8").strip(), "{{ body }}")


@unittest.skipUnless(jinja2, "jinja2 is not installed")
class MarketingRenderTests(unittest.TestCase):
    def _render(self, template, page, modules, marketing):
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(REPO_ROOT)))
        context = _Dict()
        marketing.apply_context(context, page, modules)
        return env.get_template(f"reckon_saas_platform/www/{template}.html").render(**context)

    def test_every_page_renders_one_h1_and_only_resolving_links(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.utils.nowdate = Mock(return_value="2026-11-05")
            modules = _modules(marketing, frappe)
            known = set(marketing.public_paths(modules)) | {"/", "/login", marketing.SIGNUP}
            rendered = []
            for page in all_pages(marketing, modules):
                if page["path"] == "/":
                    template = "index"
                elif page["path"].startswith("/features"):
                    template = "reckon_features"
                elif page["path"].startswith("/modules"):
                    template = "reckon_modules"
                else:
                    template = "reckon_integrations"
                rendered.append((page, self._render(template, page, modules, marketing)))
            asset_root = PKG / "public"
        for page, html in rendered:
            parser = _Links()
            parser.feed(html)
            self.assertEqual(parser.h1, 1, page["path"])
            self.assertIn(f'<link rel="canonical" href="{page["canonical"]}">', html)
            self.assertIn('property="og:title"', html)
            self.assertIn('name="twitter:card"', html)
            self.assertIn("application/ld+json", html)
            self.assertEqual(html.count("<title>"), 1)
            self.assertNotIn("frappe", html.lower(), page["path"])
            for href in parser.hrefs:
                if href.startswith(("#", "mailto:", "https://wa.me/", "https://www.reckon.tech/")):
                    continue
                if href.startswith("/assets/reckon_saas_platform/"):
                    target = asset_root / href.removeprefix("/assets/reckon_saas_platform/")
                    self.assertTrue(target.exists(), f"{page['path']}: {href}")
                    continue
                if href.startswith(BASE):
                    href = href.removeprefix(BASE)
                path = href.split("?")[0]
                self.assertTrue(path in known, f"{page['path']}: broken link {href}")
            self.assertIn('href="/reckonerp-signup', html)
            self.assertIn('href="/login"', html)

    def test_home_page_has_marquees_with_pause_and_reduced_motion(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.utils.nowdate = Mock(return_value="2026-11-05")
            modules = _modules(marketing, frappe)
            html = self._render("index", marketing.home_page(BASE, modules), modules, marketing)
        self.assertEqual(html.count("data-marquee "), 2)
        self.assertIn("data-marquee-toggle", html)
        self.assertIn("prefers-reduced-motion", html)
        self.assertIn('loading="lazy"', html)
        for name in ("WhatsApp", "Facebook Messenger", "Brevo", "Twilio SendGrid"):
            self.assertIn(name, html)

    def test_branding_contact_footer_faqs_and_chat(self):
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.utils.nowdate = Mock(return_value="2026-11-05")
            modules = _modules(marketing, frappe)
            page = marketing.home_page(BASE, modules)
            html = self._render("index", page, modules, marketing)
            asset_root = PKG / "public" / "images"
        self.assertEqual(page["h1"], "Your ERP, now with an AI that reads every ledger.")
        self.assertIn("an AI that reads every ledger.", html)
        self.assertIn("Invoices, orders, stock and people", html)
        for name in ("reckonerp-logo.webp", "reckonerp-logo-512.png", "reckonerp-icon-64.png"):
            self.assertTrue((asset_root / name).exists(), name)
        self.assertIn("reckonerp-logo.webp", html)
        self.assertIn(f"{BASE}/assets/reckon_saas_platform/images/reckonerp-logo-512.png", html)
        self.assertIn('href="https://www.reckon.tech/"', html)
        self.assertIn('href="mailto:hello@reckon.tech"', html)
        self.assertIn('href="https://wa.me/8801325009955"', html)
        self.assertIn("+8801325-009955", html)
        self.assertIn("data-chat", html)
        self.assertIn("Continue on WhatsApp", html)
        questions = " ".join(q for q, _a in page["faqs"]).lower()
        for topic in ("deployed", "pricing", "implementation", "ai and integration", "on our own servers", "licences", "help"):
            self.assertIn(topic, questions)
        faq_text = " ".join(a for _q, a in page["faqs"])
        self.assertIn("dedicated", faq_text)
        self.assertIn("on-premises", faq_text)
        self.assertIn("additional", faq_text)

    def test_text_from_modules_is_escaped(self):
        hostile = [{"key": "x1", "label": "<script>alert(1)</script>", "description": "d"}]
        with platform_modules("marketing") as (frappe, (marketing,)):
            frappe.utils.nowdate = Mock(return_value="2026-11-05")
            modules = _modules(marketing, frappe, definitions=hostile)
            html = self._render("reckon_modules", marketing.module_page(BASE, modules[0], modules), modules, marketing)
        self.assertNotIn("alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)", html)


if __name__ == "__main__":
    unittest.main()
