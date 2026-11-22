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
        self.assertTrue({"allow_yearly_payment", "yearly_months_charged", "yearly_price", "paddle_yearly_price_id"} <= names)
        self.assertNotIn("yearly_plan", names)
        self.assertTrue(set(d["field_order"]) == names)
        months = next(f for f in d["fields"] if f["fieldname"] == "yearly_months_charged")
        self.assertFalse(months.get("default"))

    def test_controller_and_api(self):
        c = (PKG / "saas_platform/doctype/saas_plan/saas_plan.py").read_text(encoding="utf-8")
        self.assertNotIn("on_update", c)  # no separate Yearly row is made
        self.assertIn("yearly_price(", c)
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


class SignupDeal(unittest.TestCase):
    def test_signup_lists_the_yearly_option_of_a_monthly_plan(self):
        from frappe_stub import _Dict, platform_modules

        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            t = {"yearly_deal": "Pay {months} months, get 12", "trial_days": "{days}", "Monthly": "month", "Yearly": "year"}
            monthly = _Dict(name="Basic", plan_name="Basic", saas_module="a", currency="BDT", price=1000, billing_cycle="Monthly",
                            trial_days=0, features="", comparison=[], allow_yearly_payment=1, yearly_months_charged=10, yearly_price=10000)
            yearly = page._yearly_option(monthly)
            card = page._plan_card(yearly, t)
            self.assertEqual((card["cycle"], card["price"], card["name"]), ("Yearly", 10000, "Basic"))
            self.assertEqual(card["deal"], "Pay 10 months, get 12")
            self.assertEqual(page._plan_card(monthly, t)["deal"], "")


class Billing(unittest.TestCase):
    def test_variant_swaps_in_the_yearly_price(self):
        from frappe_stub import platform_modules

        with platform_modules("plan_billing") as (frappe, (mod,)):
            plan = {"name": "B", "billing_cycle": "Monthly", "price": 100, "allow_yearly_payment": 1, "yearly_months_charged": 10,
                    "yearly_price": 1000, "paddle_price_id": "m", "paddle_yearly_price_id": "y"}
            self.assertEqual(mod.cycle_for(plan, "Yearly"), "Yearly")
            v = mod.variant_of(plan, "Yearly")
            self.assertEqual((v.price, v.billing_cycle, v.paddle_price_id), (1000, "Yearly", "y"))
            m = mod.variant_of(plan, "Monthly")
            self.assertEqual((m.price, m.paddle_price_id), (100, "m"))
            off = dict(plan, allow_yearly_payment=0)
            self.assertEqual(mod.cycle_for(off, "Yearly"), "Monthly")
            self.assertEqual(mod.cycle_for(dict(plan, yearly_months_charged=0), "Yearly"), "Monthly")


if __name__ == "__main__":
    unittest.main()


class PaddleKeys(unittest.TestCase):
    def test_credentials_follow_the_environment(self):
        from frappe_stub import platform_modules

        with platform_modules("paddle") as (frappe, (paddle,)):
            self.assertEqual(paddle.credential_name("paddle_api_key", "sandbox"), "paddle_api_key")
            self.assertEqual(paddle.credential_name("paddle_api_key", "production"), "paddle_live_api_key")
            self.assertEqual(paddle.credential_name("paddle_client_token", "production"), "paddle_live_client_token")
            self.assertEqual(paddle.credential_name("paddle_webhook_secret", "production"), "paddle_live_webhook_secret")

    def test_settings_hold_both_sets(self):
        d = json.loads((PKG / "saas_platform/doctype/saas_platform_settings/saas_platform_settings.json").read_text(encoding="utf-8"))
        names = {f["fieldname"] for f in d["fields"]}
        self.assertTrue({"paddle_live_api_key", "paddle_live_client_token", "paddle_live_webhook_secret"} <= names)
        self.assertEqual(set(d["field_order"]), names)
