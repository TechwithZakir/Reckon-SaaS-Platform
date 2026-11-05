"""Database-free tests for the SEO agent: validation, the monthly cap, approvals and what reaches the site."""

from __future__ import annotations

import json
import unittest
from unittest.mock import Mock

from frappe_stub import _Dict, platform_modules

DEFINITIONS = [
    {"key": "distribution", "label": "Distribution SaaS", "description": "FMCG distribution.", "subscription_features": ["dsr_routes"]},
]
BASE = "https://example.test"


def _site(frappe, marketing):
    frappe.get_installed_apps = Mock(return_value=["app"])
    frappe.get_hooks = Mock(return_value=[dict(d) for d in DEFINITIONS])
    frappe.db.exists = Mock(return_value=True)
    frappe.get_all = Mock(return_value=[])
    frappe.utils.nowdate = Mock(return_value="2026-11-05")
    frappe.utils.now_datetime = Mock(return_value="now")
    frappe.utils.cint = lambda v: int(v or 0)
    return marketing.get_modules()


class Settings(_Dict):
    """SaaS Platform Settings with an AI key."""

    def get_password(self, fieldname, raise_exception=True):
        return "sk-test" if fieldname == "seo_agent_api_key" else None


GOOD_TITLE = "FMCG route sales software with collections"
GOOD_DESC = "Plan routes, deliveries, collections and stock for FMCG distributors in one cloud workspace with mobile apps."


class SeoAgentTests(unittest.TestCase):
    def test_model_output_is_parsed_and_validated(self):
        with platform_modules("marketing", "seo", "seo_agent") as (_f, (_m, _s, agent)):
            rows = agent.parse_json_list('Sure!\n[{"path": "/modules", "title": "x"}, 5, "no"]\nDone')
            self.assertEqual(rows, [{"path": "/modules", "title": "x"}])
            self.assertEqual(agent.parse_json_list("no json here"), [])
            self.assertEqual(agent.parse_json_list("[not json]"), [])
            self.assertEqual(agent._clean("<b>Hello</b>   there\n", 50), "Hello there")
            self.assertTrue(agent.valid_title(GOOD_TITLE))
            self.assertFalse(agent.valid_title("Short"))
            self.assertFalse(agent.valid_title("The best ERP software for every business"))
            self.assertFalse(agent.valid_title("ERP built on the Frappe framework for you"))
            self.assertTrue(agent.valid_description(GOOD_DESC))
            self.assertFalse(agent.valid_description(GOOD_DESC + " Guaranteed results, " * 5))
            self.assertTrue(agent.valid_faq("Does it work offline?", "Field staff can keep working in the mobile app and sync later."))
            self.assertFalse(agent.valid_faq("Is it cheap", "Yes it is the cheapest option available on the market today."))

    def test_keyword_gaps_find_topics_no_page_covers(self):
        pages = [{"title": "FMCG distribution software", "h1": "Route sales", "description": "Collections and stock"}]
        with platform_modules("marketing", "seo", "seo_agent") as (_f, (_m, _s, agent)):
            gaps = agent.keyword_gaps(["FMCG distribution software", "restaurant billing app"], pages)
        self.assertEqual(gaps, ["restaurant billing app"])

    def test_calls_stop_at_the_monthly_cap_and_without_a_key(self):
        with platform_modules("marketing", "seo", "seo_agent") as (frappe, (marketing, seo, agent)):
            _site(frappe, marketing)
            stored = {"seo_agent_calls": 1, "seo_agent_month": "2026-11"}
            frappe.db.get_single_value = Mock(side_effect=lambda dt, f: stored.get(f))
            frappe.db.set_single_value = Mock(side_effect=lambda dt, f, v: stored.update({f: v}))
            frappe.requests.post = Mock(return_value=Mock(raise_for_status=Mock(), json=Mock(return_value={"content": [{"text": "ok"}]})))
            settings = Settings(seo_agent_monthly_call_cap=2, seo_agent_model="m", seo_agent_provider="Anthropic")
            self.assertEqual(agent.call_model(settings, "hi"), "ok")
            self.assertEqual(stored["seo_agent_calls"], 2)
            with self.assertRaises(agent.AgentLimit):
                agent.call_model(settings, "again")  # cap of 2 reached
            stored.update(seo_agent_month="2026-10", seo_agent_calls=99)  # a new month resets the count
            self.assertEqual(agent.call_model(settings, "hi"), "ok")
            self.assertEqual(stored["seo_agent_calls"], 1)
            request = frappe.requests.post.call_args
            self.assertEqual(request.args[0], "https://api.anthropic.com/v1/messages")
            self.assertEqual(request.kwargs["headers"]["x-api-key"], "sk-test")
            with self.assertRaises(agent.AgentLimit):
                agent.call_model(Settings(seo_agent_model=""), "no model")

    def test_a_run_creates_only_pending_suggestions_and_reports(self):
        replies = iter(
            [
                json.dumps([
                    {"path": "/modules", "title": GOOD_TITLE, "description": GOOD_DESC, "reason": "clearer"},
                    {"path": "/modules", "title": "The best ERP software ever made", "description": GOOD_DESC},
                    {"path": "/reckonerp-signup", "title": GOOD_TITLE, "description": GOOD_DESC},
                    {"path": "/nowhere", "title": GOOD_TITLE, "description": GOOD_DESC},
                ]),
                json.dumps([
                    {"question": "Does it work offline?", "answer": "Field staff can keep working in the mobile app and sync later.", "reason": "buyers ask"},
                    {"question": "How does pricing work?", "answer": "Duplicate of an existing question, so it must be skipped."},
                ]),
                "Popular choices are SAP and Odoo.",
                "ReckonERP is one option for FMCG distributors.",
            ]
        )
        with platform_modules("marketing", "seo", "seo_agent") as (frappe, (marketing, seo, agent)):
            _site(frappe, marketing)
            stored = {"seo_agent_calls": 0, "seo_agent_month": "2026-11"}
            frappe.db.get_single_value = Mock(side_effect=lambda dt, f: stored.get(f))
            frappe.db.set_single_value = Mock(side_effect=lambda dt, f, v: stored.update({f: v}))
            frappe.get_cached_doc = Mock(
                return_value=Settings(
                    seo_agent_enabled=1, seo_agent_monthly_call_cap=40, seo_agent_model="m", seo_agent_provider="Anthropic",
                    seo_target_keywords="FMCG distribution software\nrestaurant billing app",
                    seo_visibility_questions="What is the best ERP for FMCG distributors?\nWhich ERP suits wholesalers?",
                )
            )
            frappe.db.exists = Mock(side_effect=lambda doctype, filters=None: True if doctype == "DocType" else None)
            created = []
            frappe.get_doc = Mock(side_effect=lambda values: Mock(insert=lambda ignore_permissions=False: created.append(values)))
            agent.call_model = Mock(side_effect=lambda settings, prompt, max_tokens=1500: next(replies))

            result = agent.run_agent("manual")

        kinds = sorted((row["kind"], row.get("page_path"), row.get("source")) for row in created)
        self.assertEqual(
            kinds,
            [
                ("Content Idea", "/", "Audit"),
                ("FAQ", "/faq", "AI"),
                ("Title and Description", "/modules", "AI"),
            ],
        )
        self.assertTrue(all(row["status"] == "Pending" for row in created))
        report = "\n".join(result["report"])
        self.assertIn("restaurant billing app", report)
        self.assertIn("1 page text, 1 FAQ", report)
        self.assertIn("named in 1 of 2 answers", report)
        self.assertEqual(stored["seo_agent_report"], report)

    def test_agent_is_off_by_default_and_never_raises(self):
        with platform_modules("marketing", "seo", "seo_agent") as (frappe, (marketing, seo, agent)):
            _site(frappe, marketing)
            frappe.get_cached_doc = Mock(return_value=Settings(seo_agent_enabled=0))
            agent.call_model = Mock()
            self.assertEqual(agent.run_agent("weekly"), {"skipped": "disabled"})
            agent.call_model.assert_not_called()
            frappe.get_cached_doc = Mock(side_effect=RuntimeError("boom"))
            self.assertEqual(agent.run_agent("weekly"), {})
            frappe.log_error.assert_called()

    def test_only_approved_text_reaches_the_site(self):
        rows = [
            {"kind": "Title and Description", "page_path": "/modules", "proposed_title": GOOD_TITLE, "proposed_description": GOOD_DESC},
            {"kind": "Title and Description", "page_path": "/integrations", "proposed_title": "The best integrations page", "proposed_description": GOOD_DESC},
            {"kind": "FAQ", "question": "Does it work offline?", "answer": "Field staff can keep working in the mobile app and sync later."},
            {"kind": "FAQ", "question": "Is it free", "answer": "Short."},
        ]
        with platform_modules("marketing") as (frappe, (marketing,)):
            modules = _site(frappe, marketing)
            baseline = marketing.modules_page(BASE, modules)["title"]
            frappe.get_all = Mock(side_effect=lambda doctype, **kw: rows if doctype == "SEO Suggestion" else [])
            frappe.cache.delete_value(marketing.OVERRIDES_CACHE_KEY)
            page = marketing.modules_page(BASE, modules)
            integrations = marketing.integrations_page(BASE)
            groups = marketing.faq_groups(modules)
        self.assertNotEqual(baseline, GOOD_TITLE)
        self.assertEqual((page["title"], page["description"]), (GOOD_TITLE, GOOD_DESC))
        self.assertNotIn("best", integrations["title"].lower())  # the unverifiable claim is ignored
        more = next(g for g in groups if g["title"] == "More answers")
        self.assertEqual([q for q, _a in more["faqs"]], ["Does it work offline?"])

    def test_wiring_hooks_doctype_and_settings(self):
        from pathlib import Path

        pkg = Path(__file__).resolve().parents[1] / "reckon_saas_platform"
        hooks = (pkg / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"weekly": ["reckon_saas_platform.seo_agent.run_agent_weekly"]', hooks)
        self.assertIn('"SEO Suggestion": "reckon_saas_platform.saas_security.get_vendor_only_query"', hooks)
        doctype = json.loads((pkg / "seo_agent_studio" / "doctype" / "seo_suggestion" / "seo_suggestion.json").read_text(encoding="utf-8"))
        self.assertEqual(doctype["name"], "SEO Suggestion")
        self.assertEqual(doctype["field_order"], [f["fieldname"] for f in doctype["fields"]])
        status = next(f for f in doctype["fields"] if f["fieldname"] == "status")
        self.assertEqual(status["default"], "Pending")
        settings = json.loads((pkg / "saas_platform" / "doctype" / "saas_platform_settings" / "saas_platform_settings.json").read_text(encoding="utf-8"))
        names = [f["fieldname"] for f in settings["fields"]]
        self.assertEqual(settings["field_order"], names)
        enabled = next(f for f in settings["fields"] if f["fieldname"] == "seo_agent_enabled")
        self.assertEqual(enabled["default"], "0")  # off until a vendor enables it
        self.assertEqual(next(f for f in settings["fields"] if f["fieldname"] == "seo_agent_api_key")["fieldtype"], "Password")


if __name__ == "__main__":
    unittest.main()
