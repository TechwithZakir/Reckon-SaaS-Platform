"""The SaaS app icon must open a Desk route that resolves (runs without a database)."""

from __future__ import annotations

import unittest

from frappe_stub import platform_modules


class SaaSAppNavigationTests(unittest.TestCase):
    def test_app_icon_route_matches_a_public_workspace(self):
        with platform_modules("hooks", "install") as (_frappe, (hooks, install)):
            workspace = install._workspace_doc()
            item = hooks.add_to_apps_screen[0]

        slug = workspace["name"].lower().replace(" ", "-")
        self.assertEqual(item["route"], f"/desk/{slug}")
        self.assertEqual(item["desk_route"], f"/desk/{slug}")
        # Desk only routes /desk/<slug> to a public workspace; a private one 404s.
        self.assertEqual(workspace["public"], 1)
        self.assertEqual(workspace["for_user"], "")

    def test_workspace_stays_limited_to_vendor_roles(self):
        with platform_modules("install") as (_frappe, (install,)):
            workspace = install._workspace_doc(update=True)

        self.assertEqual(
            {row["role"] for row in workspace["roles"]},
            {"Reckon Vendor Superuser", "System Manager"},
        )
        self.assertNotIn("name", workspace)


if __name__ == "__main__":
    unittest.main()
