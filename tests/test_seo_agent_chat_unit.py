"""Database-free tests for the SEO Agent chat: what it understands, what it costs, and what a card does."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from frappe_stub import _Dict, platform_modules

MODULES = ("marketing", "seo", "seo_agent", "blog", "blog_agent", "seo_agent_chat", "api")
DEFINITIONS = [{"key": "distribution", "label": "Distribution SaaS", "description": "FMCG distribution.", "subscription_features": ["dsr_routes"]}]


class Settings(_Dict):
    def get_password(self, fieldname, raise_exception=True):
        return "sk-test" if fieldname == "seo_agent_api_key" and self.get("has_key", True) else None


def ready_settings(**extra):
    values = {
        "seo_agent_enabled": 1,
        "seo_agent_model": "m",
        "seo_agent_monthly_call_cap": 40,
        "seo_target_keywords": "FMCG distribution software\nrestaurant billing app",
        "seo_visibility_questions": "Best ERP for distributors?\nERP for wholesalers?",
    }
    return Settings({**values, **extra})


def prepare(frappe, settings):
    frappe.get_installed_apps = Mock(return_value=["app"])
    frappe.get_hooks = Mock(return_value=[dict(d) for d in DEFINITIONS])
    frappe.db.exists = Mock(return_value=True)
    frappe.get_all = Mock(return_value=[])
    frappe.utils.nowdate = Mock(return_value="2026-11-05")
    frappe.utils.cint = lambda v: int(v or 0)
    frappe.utils.get_url = Mock(return_value="https://example.test/")
    frappe.get_cached_doc = Mock(return_value=settings)
    frappe.roles = ["System Manager"]
    frappe.get_roles = Mock(return_value=["System Manager"])
    frappe.db.count = Mock(side_effect=lambda doctype, filters=None: {"SEO Suggestion": 3, "SEO Article": 2}[doctype])


class IntentTests(unittest.TestCase):
    def test_plain_requests_are_understood_without_the_ai(self):
        with platform_modules(*MODULES) as (_f, mods):
            detect = mods[MODULES.index("seo_agent_chat")].detect_intent
            cases = {
                "": "help",
                "hello": "help",
                "What can you do?": "help",
                "What needs my approval?": "pending",
                "show pending drafts": "pending",
                "Find keyword gaps": "gaps",
                "Improve page titles": "titles",
                "suggest new meta descriptions": "titles",
                "Suggest new FAQs": "faqs",
                "Check if AI assistants mention us": "visibility",
                "is chatgpt naming us": "visibility",
                "random chatter": "help",
            }
            for text, expected in cases.items():
                self.assertEqual(detect(text)["intent"], expected, text)

    def test_article_requests_get_a_topic_and_a_category(self):
        with platform_modules(*MODULES) as (_f, mods):
            detect = mods[MODULES.index("seo_agent_chat")].detect_intent
            one = detect("Write a blog article about planning delivery routes")
            self.assertEqual((one["intent"], one["topic"], one["category"]), ("article", "planning delivery routes", "Article"))
            two = detect("please write a tutorial on how to record a van collection")
            self.assertEqual((two["intent"], two["category"]), ("article", "Tutorial"))
            self.assertEqual(two["topic"], "how to record a van collection")
            three = detect("draft a feature guide for stock reconciliation")
            self.assertEqual(three["category"], "Feature Guide")
            four = detect("write this week's update about new reports")
            self.assertEqual(four["category"], "Weekly Update")
            self.assertEqual(detect("write a blog article")["topic"], "")
            self.assertEqual(detect("blog about van sales")["intent"], "article")


class ChatTests(unittest.TestCase):
    def chat(self, settings=None, **patch):
        ctx = platform_modules(*MODULES)
        frappe, mods = ctx.__enter__()
        self.addCleanup(ctx.__exit__, None, None, None)
        settings = settings if settings is not None else ready_settings()
        prepare(frappe, settings)
        by = dict(zip(MODULES, mods, strict=True))
        for name, value in patch.items():
            setattr(by["seo_agent"], name, value)
        return frappe, by

    def test_only_vendor_users_can_use_it(self):
        frappe, by = self.chat()
        frappe.session = _Dict(user="tenant@example.test")
        frappe.get_roles = Mock(return_value=["Reckon Distribution User"])
        with self.assertRaises(frappe.PermissionError):
            by["seo_agent_chat"].ask("help")
        with self.assertRaises(frappe.PermissionError):
            by["seo_agent_chat"].decide("SEO Suggestion", "SEO-00001", "approve")

    def test_help_and_pending_cost_nothing(self):
        frappe, by = self.chat()
        by["seo_agent"].call_model = Mock(side_effect=AssertionError("no AI call expected"))
        chat = by["seo_agent_chat"]
        help_reply = chat.ask("help")
        self.assertIn("Nothing goes live", help_reply["reply"])
        self.assertTrue(help_reply["chips"])
        frappe.get_all = Mock(side_effect=lambda doctype, **kw: [{"name": "x", "kind": "FAQ", "question": "Q?", "answer": "A", "status": "Pending", "title": "T", "category": "Tutorial"}])
        reply = chat.ask("What needs my approval?")
        self.assertEqual([c["type"] for c in reply["cards"]], ["article", "suggestion"])
        self.assertIn("3 suggestion(s) and 2 blog draft(s)", reply["reply"])
        frappe.get_all = Mock(return_value=[])
        self.assertIn("Nothing is waiting", chat.ask("pending")["reply"])

    def test_keyword_gaps_are_found_locally_and_offer_a_next_step(self):
        frappe, by = self.chat()
        by["seo_agent"].call_model = Mock(side_effect=AssertionError("no AI call expected"))
        reply = by["seo_agent_chat"].ask("find keyword gaps")
        self.assertIn("restaurant billing app", reply["reply"])
        self.assertEqual(reply["chips"], ["Write a blog article about restaurant billing app"])
        frappe_none, by2 = self.chat(ready_settings(seo_target_keywords=""))
        self.assertIn("Target Keywords", by2["seo_agent_chat"].ask("keyword gaps")["reply"])

    def test_ai_requests_explain_what_to_set_up_first(self):
        _f, by = self.chat(Settings(seo_agent_enabled=0))
        by["seo_agent"].call_model = Mock(side_effect=AssertionError("must not call"))
        self.assertIn("switched off", by["seo_agent_chat"].ask("improve titles")["reply"])
        _f, by = self.chat(ready_settings(has_key=False))
        self.assertIn("AI key", by["seo_agent_chat"].ask("write a blog article about routes")["reply"])

    def test_titles_and_faqs_return_the_new_suggestions_as_cards(self):
        frappe, by = self.chat()
        chat = by["seo_agent_chat"]
        agent = by["seo_agent"]
        agent.draft_pages = Mock(return_value=2)
        agent.draft_faqs = Mock(return_value=1)
        row = {"name": "SEO-00007", "kind": "Title and Description", "page_path": "/modules", "current_title": "Old", "current_description": "Old d", "proposed_title": "New title", "proposed_description": "New d", "reason": "clearer", "status": "Pending"}
        frappe.get_all = Mock(return_value=[row])
        reply = chat.ask("Improve page titles")
        self.assertIn("2 page(s)", reply["reply"])
        card = reply["cards"][0]
        self.assertEqual((card["type"], card["name"], card["kind"], card["page"]), ("suggestion", "SEO-00007", "Title and Description", "/modules"))
        self.assertEqual((card["current"], card["proposed"]), ("Old\nOld d", "New title\nNew d"))
        self.assertEqual(frappe.get_all.call_args.kwargs["filters"], {"status": "Pending", "kind": "Title and Description"})
        agent.draft_pages = Mock(return_value=0)
        none = chat.ask("improve titles")
        self.assertEqual(none["cards"], [])
        self.assertIn("nothing worth changing", none["reply"])

    def test_visibility_reports_yes_and_no_per_question(self):
        _f, by = self.chat()
        by["seo_agent"].check_visibility = Mock(return_value=[("Best ERP for distributors?", True), ("ERP for wholesalers?", False)])
        reply = by["seo_agent_chat"].ask("check visibility")
        self.assertIn("named in 1 of 2", reply["reply"])
        self.assertIn("Yes: Best ERP for distributors?", reply["reply"])
        self.assertIn("No: ERP for wholesalers?", reply["reply"])

    def test_an_article_request_writes_one_draft_and_shows_it(self):
        frappe, by = self.chat()
        seen = {}

        def fake_draft(settings, topic, pages, modules, paths, notes, base):
            seen.update(topic=topic, base=base)
            return "Plan routes the simple way", ""

        by["blog_agent"].draft_topic = fake_draft
        frappe.get_all = Mock(return_value=[{"name": "plan-routes-the-simple-way", "title": "Plan routes the simple way", "category": "Tutorial", "summary": "S", "cover_image": "/files/x-cover.webp", "status": "Draft"}])
        reply = by["seo_agent_chat"].ask("write a tutorial on how to plan routes")
        self.assertEqual(seen["topic"]["category"], "Tutorial")
        self.assertEqual(seen["topic"]["title"], "how to plan routes")
        self.assertEqual(seen["base"], "https://example.test")
        card = reply["cards"][0]
        self.assertEqual((card["type"], card["name"], card["cover"], card["status"]), ("article", "plan-routes-the-simple-way", "/files/x-cover.webp", "Draft"))
        self.assertIn("promotion kit", reply["reply"])
        # No topic: it asks instead of spending a call.
        frappe.get_all = Mock(return_value=[])
        frappe.cache.delete_value("reckon_saas_blog_articles")
        by["blog_agent"].draft_topic = Mock(side_effect=AssertionError("no call without a topic"))
        self.assertIn("What should the article be about", by["seo_agent_chat"].ask("write a blog article")["reply"])
        # A draft that fails the checks is explained, not hidden.
        by["blog_agent"].draft_topic = Mock(return_value=(None, "body must be 350-2200 words"))
        self.assertIn("350-2200 words", by["seo_agent_chat"].ask("write a blog article about van sales tips")["reply"])

    def test_the_monthly_limit_and_errors_end_politely(self):
        frappe, by = self.chat()
        by["seo_agent"].draft_pages = Mock(side_effect=by["seo_agent"].AgentLimit("Monthly call cap of 40 reached"))
        self.assertIn("Monthly call cap of 40 reached", by["seo_agent_chat"].ask("improve titles")["reply"])
        by["seo_agent"].draft_pages = Mock(side_effect=RuntimeError("boom"))
        reply = by["seo_agent_chat"].ask("improve titles")
        self.assertIn("Something went wrong", reply["reply"])
        frappe.log_error.assert_called()

    def test_approve_reject_and_publish_save_the_record_and_report_problems(self):
        frappe, by = self.chat()
        chat = by["seo_agent_chat"]
        doc = Mock(kind="Title and Description")
        frappe.get_doc = Mock(return_value=doc)
        result = chat.decide("SEO Suggestion", "SEO-00001", "approve")
        self.assertEqual((result["ok"], doc.status), (True, "Approved"))
        doc.save.assert_called_with(ignore_permissions=True)
        self.assertEqual(chat.decide("SEO Suggestion", "SEO-00001", "reject")["status"], "Rejected")
        self.assertEqual(chat.decide("SEO Article", "my-post", "publish")["status"], "Published")
        doc.kind = "Content Idea"
        self.assertIn("approved idea", chat.decide("SEO Suggestion", "SEO-00002", "approve")["message"])
        doc.save = Mock(side_effect=frappe.ValidationError("<b>The summary must be 70-160 characters before publishing.</b>"))
        failed = chat.decide("SEO Article", "my-post", "publish")
        self.assertEqual((failed["ok"], failed["message"]), (False, "The summary must be 70-160 characters before publishing."))
        with self.assertRaises(frappe.ValidationError):
            chat.decide("SEO Article", "my-post", "approve")  # not a valid action for an article
        with self.assertRaises(frappe.ValidationError):
            chat.decide("User", "Administrator", "reject")  # only the two agent doctypes can be changed

    def test_status_reports_counts_calls_and_setup(self):
        frappe, by = self.chat()
        stored = {"seo_agent_calls": 5, "seo_agent_month": "2026-11"}
        frappe.db.get_single_value = Mock(side_effect=lambda dt, f: stored.get(f))
        result = by["seo_agent_chat"].status()
        self.assertEqual((result["suggestions"], result["drafts"], result["calls_used"], result["calls_cap"], result["setup"]), (3, 2, 5, 40, ""))
        stored["seo_agent_month"] = "2026-10"
        self.assertEqual(by["seo_agent_chat"].status()["calls_used"], 0)


if __name__ == "__main__":
    unittest.main()
