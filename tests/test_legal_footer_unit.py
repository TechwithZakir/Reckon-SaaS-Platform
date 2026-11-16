"""Policy pages, the payment footer and the Pay in currency chooser."""

from __future__ import annotations

import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"


def text(*parts):
    return (PKG.joinpath(*parts)).read_text(encoding="utf-8")


class LegalPagesTests(unittest.TestCase):
    def test_the_four_policies_exist_with_the_company_contact(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("legal_pages", PKG / "legal_pages.py")
        legal = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legal)
        self.assertEqual(set(legal.PAGES), {"privacy-policy", "refund-policy", "payment-policy", "security"})
        self.assertEqual(legal.CONTACT_EMAIL, "info@reckon.tech")
        for slug, page in legal.PAGES.items():
            self.assertTrue(page["sections"], slug)
        hooks = text("hooks.py")
        for slug in legal.PAGES:
            self.assertIn(f'"/{slug}"', hooks)

    def test_footers_link_the_policies_and_mention_every_payment_way(self):
        footer = text("templates", "marketing", "pay_footer.html")
        for needle in ("/security", "/payment-policy", "/refund-policy", "/privacy-policy", "info@reckon.tech",
                       "bKash", "Nagad", "Rocket", "Bank transfer", "Visa", "PayPal", "Apple Pay",
                       "developer.paddle.com/concepts/payment-methods"):
            self.assertIn(needle, footer)
        self.assertIn("pay_footer.html", text("www", "reckonerp_signup.html"))
        self.assertIn("pay_footer.html", text("www", "reckonerp_subscription.html"))
        self.assertIn("/privacy-policy", text("templates", "marketing", "footer.html"))

    def test_checkout_opens_in_the_chosen_currencys_country(self):
        for page in ("reckonerp_signup.html", "reckonerp_subscription.html"):
            self.assertIn("countryCode", text("www", page))
        self.assertIn("PAY_CURRENCIES", text("paddle.py"))

    def test_usd_plans_do_not_offer_bank_or_wallet_payment(self):
        self.assertIn('info["manual"]', text("saas.py"))
        self.assertIn("more.hidden = info.manual === false", text("www", "reckonerp_signup.html"))
        self.assertIn('sub.currency != "BDT"', text("www", "reckonerp_subscription.html"))

    def test_each_policy_has_its_own_at_a_glance_facts(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("legal_pages", PKG / "legal_pages.py")
        legal = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legal)
        self.assertEqual(set(legal.GLANCE), set(legal.PAGES))
        self.assertEqual(len({tuple(v) for v in map(tuple, legal.GLANCE.values())}), len(legal.PAGES))


if __name__ == "__main__":
    unittest.main()
