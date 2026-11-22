import json
import sys
import unittest

from frappe_stub import REPO_ROOT

PKG = REPO_ROOT / "reckon_saas_platform"
sys.path.insert(0, str(REPO_ROOT))


def load():
    import importlib.util

    spec = importlib.util.spec_from_file_location("plan_yearly_under_test", PKG / "plan_yearly.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class YearlyRules(unittest.TestCase):
    def setUp(self):
        self.m = load()

    def test_price_follows_months_per_currency(self):
        self.assertEqual(self.m.yearly_price(1000, 10), 10000.0)
        self.assertEqual(self.m.yearly_price(29, 11), 319.0)
        self.assertEqual(self.m.yearly_price(9.99, 12), 119.88)

    def test_names_follow_the_shop_pattern(self):
        n = self.m.yearly_plan_name
        self.assertEqual(n("Basic - Accounts"), "Basic - Accounts (Yearly)")
        self.assertEqual(n("Basic - Accounts (USD)"), "Basic - Accounts (USD, Yearly)")
        self.assertEqual(n("Basic - Accounts (USD, Yearly)"), "Basic - Accounts (USD, Yearly)")

    def test_validation(self):
        v = self.m.validate_yearly
        self.assertIsNone(v("Monthly", False, None))
        self.assertIsNone(v("Monthly", True, 10))
        self.assertIsNotNone(v("Monthly", True, None))
        self.assertIsNotNone(v("Monthly", True, 13))
        self.assertIsNotNone(v("Yearly", True, 10))


class Wiring(unittest.TestCase):
    def test_doctype_fields(self):
        d = json.loads((PKG / "saas_platform/doctype/saas_plan/saas_plan.json").read_text(encoding="utf-8"))
        names = {f["fieldname"] for f in d["fields"]}
        self.assertTrue({"allow_yearly_payment", "yearly_months_charged", "yearly_plan"} <= names)
        self.assertTrue(set(d["field_order"]) == names)
        months = next(f for f in d["fields"] if f["fieldname"] == "yearly_months_charged")
        self.assertFalse(months.get("default"))

    def test_controller_and_api(self):
        c = (PKG / "saas_platform/doctype/saas_plan/saas_plan.py").read_text(encoding="utf-8")
        self.assertIn("def on_update", c)
        self.assertIn("in_yearly_sync", c)
        s = (PKG / "saas.py").read_text(encoding="utf-8")
        i = s.index("def set_plans_enabled")
        self.assertIn('methods=["POST"]', s[i - 80:i])
        self.assertIn("_require_vendor()", s[i:i + 400])

    def test_dashboard_switches(self):
        j = (PKG / "saas_platform/page/saas_dashboard/saas_dashboard.js").read_text(encoding="utf-8")
        for token in ("data-plan-toggle", "data-plan-group", "set_plans_enabled"):
            self.assertIn(token, j)


if __name__ == "__main__":
    unittest.main()
