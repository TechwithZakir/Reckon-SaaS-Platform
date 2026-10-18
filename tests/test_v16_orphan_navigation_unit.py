"""The SaaS workspace and left rail are shipped as files, so v16 ``bench migrate`` keeps them.

Frappe v16's ``remove_orphan_entities`` deletes a public, app-owned Workspace unless some installed
app has a ``workspace/**/<file>.json`` whose ``name`` matches, and a standard Workspace Sidebar
unless its ``app`` has ``<app>/workspace_sidebar/<frappe.scrub(name)>.json``. These tests pin
those paths and keep the after_migrate code reading the same files (runs without a database).
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import Mock

from frappe_stub import REPO_ROOT, platform_modules

APP = REPO_ROOT / "reckon_saas_platform"


def scrub(text: str) -> str:
    return text.replace(" ", "_").replace("-", "_").lower()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ShippedFilesTests(unittest.TestCase):
    def test_workspace_file_sits_where_frappe_imports_and_keeps_it(self):
        with platform_modules("install", "constants") as (_frappe, (install, constants)):
            name = constants.SAAS_PLATFORM_WORKSPACE
            path = install.WORKSPACE_FILE
        module_folder = scrub(read(path)["module"])
        # sync_for imports <module>/workspace/<doc>/<doc>.json; the sweep globs **/workspace/**.
        expected = APP / module_folder / "workspace" / scrub(name) / f"{scrub(name)}.json"
        self.assertEqual(path.resolve(), expected.resolve())
        workspace = read(path)
        self.assertEqual(workspace["doctype"], "Workspace")
        self.assertEqual(workspace["name"], name)
        self.assertEqual(workspace["label"], name)
        self.assertEqual(workspace["public"], 1)
        self.assertIn(workspace["module"], (APP / "modules.txt").read_text(encoding="utf-8").splitlines())

    def test_sidebar_file_sits_where_the_orphan_sweep_looks(self):
        with platform_modules("install") as (_frappe, (install,)):
            name = install.SAAS_SIDEBAR
            path = install.SIDEBAR_FILE
        sidebar = read(path)
        # Mirrors frappe.model.sync.check_if_record_exists("app", get_app_path(app), ...).
        expected = REPO_ROOT / sidebar["app"] / "workspace_sidebar" / f"{scrub(name)}.json"
        self.assertEqual(path.resolve(), expected.resolve())
        self.assertEqual(sidebar["doctype"], "Workspace Sidebar")
        self.assertEqual(sidebar["name"], name)
        self.assertEqual(sidebar["app"], "reckon_saas_platform")
        self.assertEqual(sidebar["standard"], 1)

    def test_files_have_a_fixed_timestamp_so_migrate_does_not_reimport_them(self):
        # Without `modified`, Frappe's import treats a file as newer than the database row on
        # every migrate and deletes and re-inserts it.
        with platform_modules("install") as (_frappe, (install,)):
            paths = (install.WORKSPACE_FILE, install.SIDEBAR_FILE)
        for path in paths:
            with self.subTest(path=path.name):
                self.assertRegex(read(path)["modified"], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d")


class AfterMigrateUsesTheFilesTests(unittest.TestCase):
    def test_workspace_doc_is_the_file(self):
        with platform_modules("install") as (_frappe, (install,)):
            shipped = read(install.WORKSPACE_FILE)
            created = install._workspace_doc()
            updated = install._workspace_doc(update=True)
        shipped.pop("modified")
        self.assertEqual(created, shipped)
        self.assertEqual(updated, {k: v for k, v in shipped.items() if k != "name"})

    def test_setup_workspace_inserts_the_file_when_missing(self):
        with platform_modules("install") as (frappe, (install,)):
            frappe.db.exists = Mock(return_value=None)
            install.setup_workspace()
            inserted = frappe.get_doc.call_args.args[0]
            self.assertEqual(inserted["name"], "Reckon SaaS Admin")
            frappe.get_doc.return_value.insert.assert_called_once_with(ignore_permissions=True)

    def test_sidebar_doc_is_the_file_minus_missing_links(self):
        with platform_modules("install") as (frappe, (install,)):
            shipped = read(install.SIDEBAR_FILE)
            frappe.db.exists = Mock(side_effect=lambda doctype, name: name != "SaaS Payment")
            definition = install._workspace_sidebar_doc()
        expected = [item for item in shipped["items"] if item.get("link_to") != "SaaS Payment"]
        self.assertEqual(definition["items"], expected)
        self.assertEqual(len(expected), len(shipped["items"]) - 1)
        self.assertNotIn("modified", definition)

    def test_missing_sidebar_is_inserted_from_the_file(self):
        with platform_modules("install") as (frappe, (install,)):
            frappe.db.exists = Mock(side_effect=lambda doctype, name=None: doctype != "Workspace Sidebar")
            frappe.get_all = Mock(return_value=[])
            install.ensure_workspace_sidebar()
            inserted = frappe.get_doc.call_args.args[0]
            self.assertEqual(inserted["name"], "SaaS Platform")
            frappe.get_doc.return_value.insert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
