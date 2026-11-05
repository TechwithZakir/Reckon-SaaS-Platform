"""The SEO Agent Studio module lives inside the SaaS Admin page: one workspace, one left rail, no second window."""

from __future__ import annotations

import json
import unittest
from unittest.mock import Mock

from frappe_stub import REPO_ROOT, platform_modules

APP = REPO_ROOT / "reckon_saas_platform"
NAME = "SEO Agent Studio"


def scrub(text: str) -> str:
    return text.replace(" ", "_").replace("-", "_").lower()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class StudioInsideSaasAdminTests(unittest.TestCase):
    def test_module_is_registered_and_owns_the_agent_doctypes(self):
        modules = (APP / "modules.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(modules, ["SaaS Platform", NAME])
        self.assertTrue((APP / scrub(NAME) / "__init__.py").exists())
        for doctype in ("seo_suggestion", "seo_article"):
            folder = APP / scrub(NAME) / "doctype" / doctype
            self.assertEqual(read(folder / f"{doctype}.json")["module"], NAME, doctype)
            self.assertTrue((folder / f"{doctype}.py").exists())

    def test_there_is_no_second_workspace_rail_or_apps_tile(self):
        self.assertFalse((APP / scrub(NAME) / "workspace").exists())
        self.assertFalse((APP / "workspace_sidebar" / f"{scrub(NAME)}.json").exists())
        hooks = (APP / "hooks.py").read_text(encoding="utf-8")
        self.assertNotIn("seo-agent-studio", hooks)
        self.assertNotIn('"seo_agent_studio"', hooks)
        install = (APP / "install.py").read_text(encoding="utf-8")
        self.assertNotIn("SEO_STUDIO", install)
        self.assertNotIn("setup_seo_studio", install)

    def test_saas_admin_workspace_has_the_seo_section_with_in_app_links(self):
        workspace = read(APP / "saas_platform" / "workspace" / "reckon_saas_admin" / "reckon_saas_admin.json")
        seo = {s["label"]: s for s in workspace["shortcuts"] if s["label"] in ("SEO Suggestions", "Blog Articles", "SEO Agent Settings")}
        self.assertEqual(set(seo), {"SEO Suggestions", "Blog Articles", "SEO Agent Settings"})
        for shortcut in seo.values():
            self.assertEqual(shortcut["type"], "DocType")  # opens inside the desk, not a new window
        self.assertEqual(json.loads(seo["SEO Suggestions"]["stats_filter"]), {"status": "Pending"})
        self.assertEqual(json.loads(seo["Blog Articles"]["stats_filter"]), {"status": "Draft"})
        self.assertFalse([s for s in workspace["shortcuts"] if s.get("type") == "URL" and "seo" in s["label"].lower()])
        blocks = json.loads(workspace["content"])
        self.assertIn("SEO Agent Studio", [b["data"].get("text") for b in blocks if b["type"] == "header"])
        shortcut_blocks = {b["data"]["shortcut_name"] for b in blocks if b["type"] == "shortcut"}
        self.assertEqual(shortcut_blocks, {s["label"] for s in workspace["shortcuts"]})

    def test_saas_left_rail_has_the_same_section(self):
        rail = read(APP / "workspace_sidebar" / "saas_platform.json")
        labels = [(i["label"], i["type"]) for i in rail["items"]]
        position = labels.index((NAME, "Section Break"))
        after = rail["items"][position + 1 : position + 4]
        self.assertEqual([i["label"] for i in after], ["SEO Suggestions", "Blog Articles", "SEO Agent Settings"])
        for item in after:
            self.assertEqual((item["type"], item["link_type"]), ("Link", "DocType"))
        self.assertEqual(sum(1 for label, kind in labels if label == NAME and kind == "Section Break"), 1)

    def test_rail_filter_keeps_urls_and_drops_missing_doctypes(self):
        with platform_modules("install") as (frappe, (install,)):
            frappe.db.exists = Mock(side_effect=lambda doctype, name: name != "SEO Article")
            labels = [i["label"] for i in install._workspace_sidebar_doc()["items"]]
        self.assertNotIn("Blog Articles", labels)
        self.assertIn("SEO Suggestions", labels)

    def test_the_article_form_stays_in_the_same_window(self):
        script = (APP / scrub(NAME) / "doctype" / "seo_article" / "seo_article.js").read_text(encoding="utf-8")
        self.assertNotIn("window.open", script)
        self.assertIn("window.location.assign", script)

    def test_ci_expects_both_modules(self):
        workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn('["SaaS", "Platform", "SEO", "Agent", "Studio"]', workflow)


if __name__ == "__main__":
    unittest.main()
