"""The Team page edits people itself: name, company admin or team member, remove. Never the User form."""

from __future__ import annotations

import unittest
from pathlib import Path

from frappe_stub import platform_modules

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"


class TeamEditTests(unittest.TestCase):
    def setUp(self):
        with platform_modules("team") as (_frappe, (team,)):
            self.team = team

    def test_the_last_company_admin_can_neither_be_demoted_nor_removed(self):
        left = self.team.leaves_no_admin
        self.assertTrue(left(["a@x.test"], "a@x.test", False))
        self.assertFalse(left(["a@x.test", "b@x.test"], "a@x.test", False))
        self.assertFalse(left(["a@x.test"], "a@x.test", True))
        self.assertFalse(left(["a@x.test"], "c@x.test", False))
        self.assertTrue(left([], "a@x.test", True))

    def test_every_person_has_a_menu_with_name_role_and_remove(self):
        html = (PKG / "www" / "reckonerp_team.html").read_text(encoding="utf-8")
        for needle in ("rs-team__menu", "data-edit-name", 'data-level-set="Company Admin"', 'data-level-set="Company Manager"',
                       "data-remove", "edit_team_member"):
            self.assertIn(needle, html)
        # admins get the menu too, not only the people with a module matrix
        self.assertLess(html.index("rs-team__menu"), html.index("Admin in every module"))

    def test_the_edit_goes_through_the_team_api_which_needs_a_company_admin(self):
        code = (PKG / "team.py").read_text(encoding="utf-8")
        body = code[code.index("def edit_team_member"):code.index("def remove_team_member")]
        self.assertIn("_admin_company(frappe.session.user)", body)
        self.assertIn("leaves_no_admin", body)


if __name__ == "__main__":
    unittest.main()
