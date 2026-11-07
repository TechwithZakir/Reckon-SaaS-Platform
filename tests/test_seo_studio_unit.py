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
        self.assertEqual(modules[:2], ["SaaS Platform", NAME])
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

    def test_saas_admin_workspace_has_one_seo_agent_tile_and_its_settings(self):
        workspace = read(APP / "saas_platform" / "workspace" / "reckon_saas_admin" / "reckon_saas_admin.json")
        seo = {s["label"]: s for s in workspace["shortcuts"] if s["label"].startswith("SEO")}
        self.assertEqual(set(seo), {"SEO Agent", "SEO Agent Settings"})
        self.assertEqual((seo["SEO Agent"]["type"], seo["SEO Agent"]["link_to"]), ("Page", "seo-agent"))
        self.assertEqual(seo["SEO Agent Settings"]["link_to"], "SaaS Platform Settings")
        self.assertFalse([s for s in workspace["shortcuts"] if s.get("type") == "URL" and "seo" in s["label"].lower()])
        blocks = json.loads(workspace["content"])
        self.assertIn("SEO Agent Studio", [b["data"].get("text") for b in blocks if b["type"] == "header"])
        shortcut_blocks = [b["data"]["shortcut_name"] for b in blocks if b["type"] == "shortcut"]
        self.assertEqual(shortcut_blocks, [s["label"] for s in workspace["shortcuts"]])

    def test_saas_left_rail_has_the_same_two_links(self):
        rail = read(APP / "workspace_sidebar" / "saas_platform.json")
        labels = [(i["label"], i["type"]) for i in rail["items"]]
        position = labels.index((NAME, "Section Break"))
        after = rail["items"][position + 1 :]
        self.assertEqual([i["label"] for i in after], ["SEO Agent", "SEO Agent Settings"])
        self.assertEqual((after[0]["link_type"], after[0]["link_to"]), ("Page", "seo-agent"))
        self.assertEqual(sum(1 for label, kind in labels if label == NAME and kind == "Section Break"), 1)

    def test_the_agent_page_exists_for_vendor_roles_only(self):
        page = read(APP / scrub(NAME) / "page" / "seo_agent" / "seo_agent.json")
        self.assertEqual((page["name"], page["module"], page["standard"]), ("seo-agent", NAME, "Yes"))
        self.assertEqual({r["role"] for r in page["roles"]}, {"Reckon Vendor Superuser", "System Manager"})
        script = (APP / scrub(NAME) / "page" / "seo_agent" / "seo_agent.js").read_text(encoding="utf-8")
        self.assertIn('frappe.pages["seo-agent"].on_page_load', script)
        self.assertNotIn("window.open", script)  # everything stays in this window

    def test_rail_filter_keeps_urls_and_drops_missing_doctypes(self):
        with platform_modules("install") as (frappe, (install,)):
            frappe.db.exists = Mock(side_effect=lambda doctype, name: name != "SEO Article")
            labels = [i["label"] for i in install._workspace_sidebar_doc()["items"]]
        self.assertIn("SEO Agent", labels)
        frappe.db.exists = Mock(side_effect=lambda doctype, name: name != "seo-agent")
        self.assertNotIn("SEO Agent", [i["label"] for i in install._workspace_sidebar_doc()["items"]])

    def test_the_article_form_stays_in_the_same_window(self):
        script = (APP / scrub(NAME) / "doctype" / "seo_article" / "seo_article.js").read_text(encoding="utf-8")
        self.assertNotIn("window.open", script)
        self.assertIn("window.location.assign", script)

    def test_ci_expects_both_modules(self):
        workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn('["SaaS", "Platform", "SEO", "Agent", "Studio", "SaaS", "CRM"]', workflow)


if __name__ == "__main__":
    unittest.main()
