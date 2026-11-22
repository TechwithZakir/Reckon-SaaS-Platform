"""Signup plan picker: grouped by currency and billing period, with the plan's own features on the side."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from frappe_stub import _Dict, platform_modules
from test_signup_page_unit import _page_context

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"
ACCOUNTS = _Dict(name="accounts", module_name="Accounts SaaS", description="", features="")


def plan(name, module, currency, price, cycle="Monthly"):
    return _Dict(name=name, plan_name=name, saas_module=module, currency=currency, price=price, billing_cycle=cycle, trial_days=15, features="")


PLANS = (
    plan("Basic - Accounts", "accounts", "BDT", 1000),
    plan("Standard - Accounts", "accounts", "BDT", 2000),
    plan("Basic - Accounts (USD)", "accounts", "USD", 10),
    plan("Standard - Accounts (USD)", "accounts", "USD", 20),
    plan("Basic - Accounts (USD, Yearly)", "accounts", "USD", 100, "Yearly"),
)


class PlanGroupingTests(unittest.TestCase):
    def test_a_selected_module_groups_plans_by_currency_and_cycle_not_one_flat_list(self):
        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            context = _page_context(page, frappe, {"module": "accounts"}, modules=(ACCOUNTS,), plans=PLANS)
        sets = {(s["cur"], s["cycle"]): [c["tier"] for c in s["cards"]] for s in context.plan_sets}
        self.assertEqual(sets, {
            ("BDT", "Monthly"): ["Basic", "Standard"],
            ("USD", "Monthly"): ["Basic", "Standard"],
            ("USD", "Yearly"): ["Basic"],
        })
        self.assertEqual(context.plan_currencies, ["BDT", "USD"])  # BDT first by default
        self.assertEqual(context.plan_cycles, ["Monthly", "Yearly"])

    def test_a_requested_currency_opens_first_but_nothing_is_dropped(self):
        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            context = _page_context(page, frappe, {"module": "accounts", "currency": "USD"}, modules=(ACCOUNTS,), plans=PLANS)
        self.assertEqual(context.plan_currencies[0], "USD")
        self.assertEqual(context.plan_sets[0]["cur"], "USD")
        self.assertEqual(sum(len(s["cards"]) for s in context.plan_sets), len(PLANS))  # every plan is still offered

    def test_the_module_picker_without_a_module_keeps_the_old_flat_list(self):
        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            context = _page_context(page, frappe, {}, modules=(ACCOUNTS,), plans=PLANS)
        self.assertEqual(context.plan_sets, [])  # no grouping until a module is chosen

    def test_each_card_carries_its_own_comparison_rows_for_the_detail_panel(self):
        with platform_modules("www.reckonerp_signup") as (frappe, (page,)):
            frappe.get_all.side_effect = lambda doctype, **kw: (
                list((ACCOUNTS,)) if doctype == "SaaS Module"
                else [_Dict(parent="Basic - Accounts", feature="Users", included=1, value="Up to 5")] if doctype == "SaaS Plan Feature"
                else [p for p in PLANS if not (kw.get("filters") or {}).get("saas_module") or p.saas_module == (kw.get("filters") or {})["saas_module"]]
            )
            frappe.form_dict = _Dict({"module": "accounts"})
            frappe.local.form_dict = frappe.form_dict
            frappe.local.request = Mock(cookies={}, headers={})
            context = _Dict()
            with patch.object(page, "get_recaptcha_site_key", return_value=None), patch.object(page, "nowdate", return_value="2026-10-18"):
                page.get_context(context)
        basic = next(c for c in context.plan_cards if c["name"] == "Basic - Accounts")
        self.assertEqual(basic["comparison"], [{"feature": "Users", "included": True, "value": "Up to 5"}])
        others = [c for c in context.plan_cards if c["name"] != "Basic - Accounts"]
        self.assertTrue(all(c["comparison"] == [] for c in others))


class TemplateWiringTests(unittest.TestCase):
    def test_signup_page_has_the_grouping_and_detail_panel_hooks(self):
        html = (PKG / "www" / "reckonerp_signup.html").read_text(encoding="utf-8")
        for needle in (
            "{% if plan_sets %}", 'data-cur-set="', 'data-cycle-set="', 'data-comparison=',
            "data-plan-detail", "data-pd-name", "data-pd-list", "data-tier=",
            "ensurePlanSelected", "syncDetail",
        ):
            self.assertIn(needle, html, needle)
        self.assertNotIn("parentloop", html)  # Django syntax; Jinja has no loop.parentloop and the page would be a 500

    def test_the_plan_picker_block_renders_with_real_data(self):
        """Parsing is not enough: an undefined attribute only fails when the block is rendered."""
        import re

        import jinja2

        html = (PKG / "www" / "reckonerp_signup.html").read_text(encoding="utf-8")
        start = html.index("{% if plan_currencies|length > 1 %}")
        end = html.index('<div class="rk-plans" role="radiogroup"', html.index("</div>\n              {% else %}", start))
        block = html[start:html.rindex("{% else %}", start, end)]
        card = {"name": "P", "plan_name": "P", "tier": "Basic", "module": "accounts", "trial_days": 15, "comparison": [{"feature": "Users", "included": True, "value": "5"}],
                "symbol": "$", "amount": "10", "period": "month", "trial": "15-day free trial", "cycle": "Monthly", "deal": ""}
        sets = [{"cur": "BDT", "cycle": "Monthly", "cards": [card, dict(card, name="Q")]}, {"cur": "USD", "cycle": "Monthly", "cards": [dict(card, name="R")]}]
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        out = env.from_string(block).render(plan_sets=sets, plan_currencies=["BDT", "USD"], plan_cycles=["Monthly"], t={"currency": "Currency", "billing_period": "Billing period"})
        self.assertEqual(len(re.findall(r" checked", out)), 1)  # exactly one plan starts selected
        self.assertEqual(out.count('class="cur-set'), 2)

    def test_modules_page_uses_the_same_comparison_table_as_pricing(self):
        html = (PKG / "www" / "reckon_modules.html").read_text(encoding="utf-8")
        self.assertIn("m.plan_compare(page.module)", html)
        self.assertNotIn("m.plan_cards(page.module)", html)


if __name__ == "__main__":
    unittest.main()
