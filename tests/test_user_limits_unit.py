"""Plan user limits: the rule, the refusal, and the Users row of the plan comparison."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from frappe_stub import platform_modules
from test_agent_and_speed_unit import plan

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"


class UserLimitRuleTests(unittest.TestCase):
    def rule(self, limits):
        with platform_modules("entitlements") as (_f, (entitlements,)):
            return entitlements.effective_user_limit(limits)

    def test_no_plan_or_a_blank_limit_means_unlimited(self):
        self.assertIsNone(self.rule([]))
        self.assertIsNone(self.rule([None]))
        self.assertIsNone(self.rule([0]))
        self.assertIsNone(self.rule([5, 0]))  # one unlimited plan frees the company

    def test_the_highest_limit_of_several_modules_applies(self):
        self.assertEqual(self.rule([5, 20, 10]), 20)
        self.assertEqual(self.rule([5]), 5)


class UserLimitEnforcementTests(unittest.TestCase):
    def check(self, limit, people, user="new@x.test"):
        with platform_modules("tenant_security") as (frappe, (security,)):
            frappe.get_all = Mock(side_effect=lambda doctype, **kw: ["PLAN"] if doctype == "SaaS Subscription" else list(people))
            frappe.db.get_value = Mock(return_value=limit)
            frappe.throw = Mock(side_effect=Exception("limit"))
            security.assert_user_limit_allows("Acme", user)

    def test_a_new_person_is_refused_at_the_limit(self):
        with self.assertRaises(Exception) as ctx:
            self.check(2, ["a@x.test", "b@x.test"])
        self.assertEqual(str(ctx.exception), "limit")

    def test_a_new_person_fits_below_the_limit(self):
        self.check(3, ["a@x.test", "b@x.test"])

    def test_someone_already_counted_is_never_refused(self):
        self.check(2, ["a@x.test", "b@x.test"], user="a@x.test")

    def test_blank_limit_is_unlimited(self):
        self.check(0, [f"u{i}@x.test" for i in range(500)])


class UserLimitWiringTests(unittest.TestCase):
    def test_every_way_of_adding_a_person_checks_the_limit(self):
        assignment = (PKG / "saas_platform" / "doctype" / "tenant_user_assignment" / "tenant_user_assignment.py").read_text(encoding="utf-8")
        self.assertIn("_validate_plan_user_limit", assignment)
        team = (PKG / "team.py").read_text(encoding="utf-8")
        self.assertLess(team.index("assert_user_limit_allows(company, email)"), team.index('"doctype": "User", "email": email'))

    def test_plan_has_a_maximum_users_field(self):
        data = json.loads((PKG / "saas_platform" / "doctype" / "saas_plan" / "saas_plan.json").read_text(encoding="utf-8"))
        field = next(f for f in data["fields"] if f["fieldname"] == "max_users")
        self.assertEqual(field["fieldtype"], "Int")
        self.assertIn("max_users", data["field_order"])

    def test_comparison_starts_with_a_users_row_from_the_plan_limit(self):
        with platform_modules("marketing") as (_f, (marketing,)):
            a = {**plan("A", 1, "BDT"), "max_users": 5, "comparison": [{"feature": "X", "included": True, "value": ""}]}
            b = {**plan("B", 2, "BDT"), "max_users": 0, "comparison": [{"feature": "X", "included": True, "value": ""}]}
            rows = marketing.comparison_matrix([a, b])["rows"]
        self.assertEqual([r["feature"] for r in rows], ["Users", "X"])
        self.assertEqual([c["users"] for c in rows[0]["cells"]], [5, 0])


if __name__ == "__main__":
    unittest.main()
