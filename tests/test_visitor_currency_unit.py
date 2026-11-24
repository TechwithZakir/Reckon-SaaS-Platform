"""Taka for visitors in Bangladesh, US dollars for everyone else; the pages ask after they load."""

from __future__ import annotations

import unittest
from pathlib import Path

from frappe_stub import platform_modules

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"


class VisitorCurrencyTests(unittest.TestCase):
    def setUp(self):
        with platform_modules() as (_frappe, _mods):
            import importlib

            self.mod = importlib.import_module("reckon_saas_platform.visitor_currency")

    def test_bangladesh_is_taka_and_everywhere_else_is_dollars(self):
        self.assertEqual(self.mod.currency_for("BD"), "BDT")
        self.assertEqual(self.mod.currency_for("bd"), "BDT")
        for code in ("US", "IN", "GB", "AE", "", None):
            self.assertEqual(self.mod.currency_for(code), "USD")

    def test_the_provider_header_wins_then_the_ip_table(self):
        headers = {"CF-IPCountry": "BD"}
        self.assertEqual(self.mod.visitor_country(headers.get, "1.2.3.4", lambda ip: "US"), "BD")
        self.assertEqual(self.mod.visitor_country({}.get, "1.2.3.4", lambda ip: "IN"), "IN")
        self.assertEqual(self.mod.visitor_country({"CF-IPCountry": "XX"}.get, "1.2.3.4", lambda ip: "GB"), "GB")
        self.assertEqual(self.mod.visitor_country({}.get, "", lambda ip: "US"), "")

    def test_the_plan_pages_ask_after_loading_and_keep_the_visitors_own_choice(self):
        js = (PKG / "templates" / "marketing" / "chrome_js.html").read_text(encoding="utf-8")
        self.assertIn("reckon_saas_platform.visitor_currency.visitor_currency", js)
        self.assertIn("if(!chosen&&want&&want!==cur)showCur(want)", js)
        self.assertIn("get('currency')", js)


if __name__ == "__main__":
    unittest.main()
