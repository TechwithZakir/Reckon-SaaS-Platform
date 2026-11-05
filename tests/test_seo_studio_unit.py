"""The SEO Agent Studio module: its own module folder, workspace and left rail, shipped as files like the SaaS ones."""

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


class StudioFilesTests(unittest.TestCase):
    def test_module_is_registered_and_owns_the_agent_doctypes(self):
        modules = (APP / "modules.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(modules, ["SaaS Platform", NAME])
        self.assertTrue((APP / scrub(NAME) / "__init__.py").exists())
        for doctype in ("seo_suggestion", "seo_article"):
            folder = APP / scrub(NAME) / "doctype" / doctype
            definition = read(folder / f"{doctype}.json")
            self.assertEqual(definition["module"], NAME, doctype)
            self.assertTrue((folder / f"{doctype}.py").exists())
            self.assertFalse((APP / "saas_platform" / "doctype" / doctype).joinpath(f"{doctype}.json").exists(), "old copy left behind")

    def test_workspace_file_sits_where_frappe_imports_and_keeps_it(self):
        with platform_modules("install") as (_frappe, (install,)):
            path = install.SEO_STUDIO_WORKSPACE_FILE
        workspace = read(path)
        expected = APP / scrub(workspace["module"]) / "workspace" / scrub(NAME) / f"{scrub(NAME)}.json"
        self.assertEqual(path.resolve(), expected.resolve())
        self.assertEqual((workspace["doctype"], workspace["name"], workspace["label"], workspace["public"]), ("Workspace", NAME, NAME, 1))
        self.assertIn(workspace["module"], (APP / "modules.txt").read_text(encoding="utf-8").splitlines())
        self.assertRegex(workspace["modified"], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d")
        roles = {row["role"] for row in workspace["roles"]}
        self.assertEqual(roles, {"Reckon Vendor Superuser", "System Manager"})  # never visible to tenants
        shortcut_names = {s["label"] for s in workspace["shortcuts"]}
        blocks = json.loads(workspace["content"])
        self.assertEqual({b["data"]["shortcut_name"] for b in blocks if b["type"] == "shortcut"}, shortcut_names)
        targets = {s.get("link_to") or s.get("url") for s in workspace["shortcuts"]}
        for expected_target in ("SEO Suggestion", "SEO Article", "SaaS Platform Settings", "/blog", "/sitemap.xml"):
            self.assertIn(expected_target, targets)

    def test_sidebar_file_sits_where_the_orphan_sweep_looks(self):
        with platform_modules("install") as (_frappe, (install,)):
            path = install.SEO_STUDIO_SIDEBAR_FILE
        sidebar = read(path)
        expected = REPO_ROOT / sidebar["app"] / "workspace_sidebar" / f"{scrub(NAME)}.json"
        self.assertEqual(path.resolve(), expected.resolve())
        self.assertEqual((sidebar["doctype"], sidebar["name"], sidebar["app"], sidebar["standard"]), ("Workspace Sidebar", NAME, "reckon_saas_platform", 1))
        self.assertEqual(sidebar["module"], NAME)
        self.assertRegex(sidebar["modified"], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d")
        for item in sidebar["items"]:
            if item["type"] == "Link":
                self.assertTrue(item.get("link_to") or item.get("url"), item["label"])

    def test_studio_is_reachable_from_saas_admin_the_left_rail_and_the_apps_screen(self):
        admin = read(APP / "saas_platform" / "workspace" / "reckon_saas_admin" / "reckon_saas_admin.json")
        link = next(s for s in admin["shortcuts"] if s["label"] == "SEO Agent Studio")
        self.assertEqual((link["type"], link["url"]), ("URL", "/desk/seo-agent-studio"))
        blocks = json.loads(admin["content"])
        self.assertIn("SEO Agent Studio", {b["data"]["shortcut_name"] for b in blocks if b["type"] == "shortcut"})
        rail = read(APP / "workspace_sidebar" / "saas_platform.json")
        item = next(i for i in rail["items"] if i.get("label") == "SEO Agent Studio")
        self.assertEqual((item["link_type"], item["url"]), ("URL", "/desk/seo-agent-studio"))
        back = read(APP / "workspace_sidebar" / "seo_agent_studio.json")
        self.assertIn("/desk/reckon-saas-admin", {i.get("url") for i in back["items"]})
        hooks = (APP / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"route": "/desk/seo-agent-studio"', hooks)
        self.assertTrue((APP / "public" / "images" / "seo-agent-studio-icon.svg").exists())

    def test_the_saas_rail_filter_keeps_url_links(self):
        with platform_modules("install") as (frappe, (install,)):
            frappe.db.exists = Mock(return_value=True)
            labels = [item["label"] for item in install._workspace_sidebar_doc()["items"]]
        self.assertIn("SEO Agent Studio", labels)

    def test_ci_expects_both_modules(self):
        workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn('["SaaS", "Platform", "SEO", "Agent", "Studio"]', workflow)


class StudioInstallTests(unittest.TestCase):
    def test_workspace_doc_is_the_file(self):
        with platform_modules("install") as (_frappe, (install,)):
            shipped = read(install.SEO_STUDIO_WORKSPACE_FILE)
            created = install._studio_workspace_doc()
            updated = install._studio_workspace_doc(update=True)
        shipped.pop("modified")
        self.assertEqual(created, shipped)
        self.assertEqual(updated, {k: v for k, v in shipped.items() if k != "name"})

    def test_workspace_is_created_then_refreshed(self):
        with platform_modules("install") as (frappe, (install,)):
            frappe.db.exists = Mock(return_value=None)
            install.ensure_seo_studio_workspace()
            self.assertEqual(frappe.get_doc.call_args.args[0]["name"], NAME)
            frappe.get_doc.return_value.insert.assert_called_once_with(ignore_permissions=True)
            frappe.get_doc.reset_mock()
            frappe.db.exists = Mock(return_value=True)
            install.ensure_seo_studio_workspace()
            frappe.get_doc.return_value.save.assert_called_once_with(ignore_permissions=True)

    def test_sidebar_keeps_url_links_and_drops_missing_doctypes(self):
        with platform_modules("install") as (frappe, (install,)):
            shipped = read(install.SEO_STUDIO_SIDEBAR_FILE)
            frappe.db.exists = Mock(side_effect=lambda doctype, name: name != "SEO Article")
            definition = install._studio_sidebar_doc()
        labels = [item["label"] for item in definition["items"]]
        self.assertNotIn("Blog Articles", labels)
        for kept in ("SEO Suggestions", "Agent Settings", "Blog", "Sitemap", "llms.txt", "RSS Feed"):
            self.assertIn(kept, labels)
        self.assertEqual(len(definition["items"]), len(shipped["items"]) - 1)

    def test_missing_sidebar_is_inserted_and_an_existing_one_is_refreshed(self):
        with platform_modules("install") as (frappe, (install,)):
            frappe.db.exists = Mock(side_effect=lambda doctype, name=None: doctype != "Workspace Sidebar" or None)
            frappe.get_all = Mock(return_value=[])
            install.ensure_seo_studio_sidebar()
            self.assertEqual(frappe.get_doc.call_args.args[0]["name"], NAME)
            frappe.get_doc.return_value.insert.assert_called_once()
            frappe.get_doc.reset_mock()
            frappe.db.exists = Mock(return_value=True)
            frappe.get_all = Mock(return_value=[NAME])
            install.ensure_seo_studio_sidebar()
            frappe.get_doc.return_value.save.assert_called_once_with(ignore_permissions=True)

    def test_a_navigation_problem_never_stops_a_migrate(self):
        with platform_modules("install") as (frappe, (install,)):
            frappe.db.exists = Mock(side_effect=RuntimeError("db down"))
            install.setup_seo_studio()
            frappe.log_error.assert_called_once()

    def test_install_and_migrate_both_set_up_the_studio(self):
        source = (APP / "install.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("    setup_seo_studio()\n"), 2)


if __name__ == "__main__":
    unittest.main()
