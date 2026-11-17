import json
import unittest
from unittest.mock import Mock, patch

from frappe_stub import REPO_ROOT, _Dict, platform_modules

PKG = REPO_ROOT / "reckon_saas_platform"


class AiFillPolicyTests(unittest.TestCase):
    def policy(self, plans, bypass=False, companies=("Acme",)):
        with platform_modules("plan_limits") as (frappe, (limits,)):
            frappe.get_all = Mock(return_value=[name for name in plans])
            frappe.db.get_value = Mock(side_effect=lambda doctype, name, fields, as_dict=False: plans[name])
            with patch.object(limits, "user_can_bypass_tenant", return_value=bypass), \
                    patch.object(limits, "get_user_companies", return_value=list(companies)):
                return limits.ai_fill_policy("u@x.test")

    def test_vendor_staff_and_people_with_no_company_are_never_held_back(self):
        self.assertEqual(self.policy({}, bypass=True), {"enabled": True, "daily_limit": None, "create": True})
        self.assertEqual(self.policy({}, companies=()), {"enabled": True, "daily_limit": None, "create": True})

    def test_a_plan_can_switch_it_off(self):
        self.assertFalse(self.policy({"Basic": _Dict(ai_fill_enabled=0, ai_fill_daily_limit=5)})["enabled"])

    def test_the_daily_limit_comes_from_the_plan(self):
        self.assertEqual(self.policy({"Basic": _Dict(ai_fill_enabled=1, ai_fill_daily_limit=20)}), {"enabled": True, "daily_limit": 20, "create": True})

    def test_blank_or_zero_means_unlimited(self):
        self.assertIsNone(self.policy({"Pro": _Dict(ai_fill_enabled=1, ai_fill_daily_limit=0)})["daily_limit"])

    def test_with_several_plans_the_best_one_counts_and_an_off_plan_is_ignored(self):
        plans = {
            "Basic": _Dict(ai_fill_enabled=1, ai_fill_daily_limit=10),
            "CRM": _Dict(ai_fill_enabled=1, ai_fill_daily_limit=50),
            "Trial": _Dict(ai_fill_enabled=0, ai_fill_daily_limit=0),
        }
        self.assertEqual(self.policy(plans)["daily_limit"], 50)

    def test_a_plan_can_switch_off_creating_missing_records(self):
        on = {"Basic": _Dict(ai_fill_enabled=1, ai_fill_daily_limit=20, ai_fill_create_enabled=1)}
        off = {"Basic": _Dict(ai_fill_enabled=1, ai_fill_daily_limit=20, ai_fill_create_enabled=0)}
        self.assertTrue(self.policy(on)["create"])
        self.assertFalse(self.policy(off)["create"])
        self.assertTrue(self.policy({"Old": _Dict(ai_fill_enabled=None, ai_fill_daily_limit=None, ai_fill_create_enabled=None)})["create"])

    def test_a_plan_saved_before_the_field_existed_counts_as_on(self):
        self.assertTrue(self.policy({"Old": _Dict(ai_fill_enabled=None, ai_fill_daily_limit=None)})["enabled"])


class WiringTests(unittest.TestCase):
    def test_the_plan_has_the_two_settings_and_a_patch_sets_defaults(self):
        meta = json.loads((PKG / "saas_platform" / "doctype" / "saas_plan" / "saas_plan.json").read_text(encoding="utf-8"))
        fields = {f["fieldname"]: f for f in meta["fields"]}
        self.assertEqual(fields["ai_fill_enabled"]["fieldtype"], "Check")
        self.assertEqual(fields["ai_fill_daily_limit"]["fieldtype"], "Int")
        self.assertTrue({"ai_fill_enabled", "ai_fill_daily_limit", "ai_fill_create_enabled"} <= set(meta["field_order"]))
        self.assertIn("patches.set_ai_fill_plan_defaults", (PKG / "patches.txt").read_text(encoding="utf-8"))
        self.assertTrue((PKG / "patches" / "set_ai_fill_plan_defaults.py").is_file())


if __name__ == "__main__":
    unittest.main()
