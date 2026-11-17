import json
import unittest
from unittest.mock import Mock, patch

from frappe_stub import REPO_ROOT, _Dict, platform_modules

PKG = REPO_ROOT / "reckon_saas_platform"
DOCTYPES = PKG / "saas_platform" / "doctype"


def coupon(**kw):
    base = dict(name="WELCOME10", enabled=1, discount_type="Percent", percent=10, amount=0, currency=None,
                valid_from=None, valid_until=None, max_redemptions=0, times_redeemed=0, plan=None, saas_module=None)
    base.update(kw)
    return _Dict(**base)


class DiscountTests(unittest.TestCase):
    def test_percent_fixed_and_the_cap(self):
        with platform_modules("coupons") as (_f, (coupons,)):
            self.assertEqual(coupons.discount_for(coupon(), 1000, "BDT"), 100.0)
            fixed = coupon(discount_type="Fixed Amount", amount=300, currency="BDT")
            self.assertEqual(coupons.discount_for(fixed, 1000, "BDT"), 300.0)
            self.assertEqual(coupons.discount_for(fixed, 200, "BDT"), 200.0)  # never more than the price
            self.assertEqual(coupons.discount_for(fixed, 1000, "USD"), 0.0)  # another currency
            self.assertEqual(coupons.discount_for(coupon(percent=100), 49, "USD"), 49.0)

    def test_normalize(self):
        with platform_modules("coupons") as (_f, (coupons,)):
            self.assertEqual(coupons.normalize(" wel come-10 "), "WELCOME-10")


class ValidationTests(unittest.TestCase):
    def check(self, row, plan_row=None, code="welcome10"):
        plan_row = plan_row if plan_row is not None else _Dict(name="Basic", saas_module="distribution", price=1000, currency="BDT")
        with platform_modules("coupons") as (frappe, (coupons,)):
            frappe.db.get_value = Mock(side_effect=lambda doctype, *a, **k: row if doctype == "SaaS Coupon" else plan_row)
            try:
                return coupons.get_valid(code, "Basic")
            except coupons.CouponError as exc:
                return str(exc)

    def test_a_good_code_gives_its_discount(self):
        result = self.check(coupon())
        self.assertEqual((result.name, result.discount), ("WELCOME10", 100.0))

    def test_each_refusal_says_why(self):
        self.assertIn("not valid", self.check(None))
        self.assertIn("not valid", self.check(coupon(enabled=0)))
        self.assertIn("expired", self.check(coupon(valid_until="2020-01-01")))
        self.assertIn("not active", self.check(coupon(valid_from="2999-01-01")))
        self.assertIn("fully used", self.check(coupon(max_redemptions=5, times_redeemed=5)))
        self.assertIn("this plan", self.check(coupon(plan="Pro")))
        self.assertIn("this module", self.check(coupon(saas_module="crm")))
        self.assertIn("priced in", self.check(coupon(discount_type="Fixed Amount", amount=5, currency="USD")))

    def test_a_use_is_counted_inside_one_guarded_statement(self):
        with platform_modules("coupons") as (frappe, (coupons,)):
            frappe.db.sql = Mock()
            coupons.redeem("welcome10")
            query, params = frappe.db.sql.call_args[0]
            self.assertIn("times_redeemed < max_redemptions", query)
            self.assertEqual(params, ("WELCOME10",))


class WiringTests(unittest.TestCase):
    def test_the_coupon_doctype_is_vendor_only_and_has_its_fields(self):
        meta = json.loads((DOCTYPES / "saas_coupon" / "saas_coupon.json").read_text(encoding="utf-8"))
        names = {f["fieldname"] for f in meta["fields"]}
        self.assertTrue({"code", "discount_type", "percent", "amount", "currency", "valid_until", "max_redemptions", "times_redeemed", "plan", "saas_module"} <= names)
        self.assertEqual({p["role"] for p in meta["permissions"]}, {"Reckon Vendor Superuser", "System Manager"})
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"SaaS Coupon": "reckon_saas_platform.saas_security.get_vendor_only_query"', hooks)
        self.assertIn('"SaaS Coupon": "reckon_saas_platform.saas_security.has_vendor_only_permission"', hooks)
        self.assertIn("paddle.queue_coupon_sync", hooks)

    def test_subscription_registration_and_invoice_carry_the_coupon(self):
        for doctype, fields in (("saas_subscription", {"coupon", "discount_amount"}), ("saas_registration", {"coupon"}),
                                ("saas_invoice", {"coupon", "discount_amount", "erp_sales_invoice", "erp_payment_entry"})):
            meta = json.loads((DOCTYPES / doctype / f"{doctype}.json").read_text(encoding="utf-8"))
            self.assertTrue(fields <= {f["fieldname"] for f in meta["fields"]}, doctype)
            self.assertTrue(fields <= set(meta["field_order"]), doctype)

    def test_signup_and_subscription_pages_take_a_coupon_before_confirming(self):
        signup = (PKG / "www" / "reckonerp_signup.html").read_text(encoding="utf-8")
        self.assertIn('name="coupon_code"', signup)
        self.assertLess(signup.index('name="coupon_code"'), signup.index('id="rk-submit"'))
        self.assertIn("coupons.check_coupon", signup)
        self.assertIn("discountId", signup)
        subscription = (PKG / "www" / "reckonerp_subscription.html").read_text(encoding="utf-8")
        self.assertIn('name="coupon_code"', subscription)
        self.assertLess(subscription.index('name="coupon_code"'), subscription.index("Confirm subscription"))
        saas = (PKG / "saas.py").read_text(encoding="utf-8")
        self.assertIn("coupon_code: str | None = None", saas)

    def test_the_admin_can_reach_coupons(self):
        sidebar = (PKG / "workspace_sidebar" / "saas_platform.json").read_text(encoding="utf-8")
        self.assertIn('"link_to": "SaaS Coupon"', sidebar)


class InvoiceDiscountTests(unittest.TestCase):
    def make(self, period_start=None):
        with platform_modules("invoices") as (frappe, (invoices,)):
            inserted = []
            subscription = _Dict(name="SUB-1", company="Acme", registration=None, saas_module="distribution", plan="Basic",
                                 billing_cycle="Monthly", start_date="2026-11-17", trial_end_date=None, grace_days=3,
                                 price=1000, discount_amount=100, coupon="WELCOME10", currency="BDT", company_admin="a@x.test")
            frappe.get_doc = Mock(side_effect=lambda *a: subscription if len(a) == 2 else _Dict(**a[0], insert=lambda **k: inserted.append(a[0])))
            frappe.db.get_value = Mock(return_value=None)
            invoices._owner = Mock(return_value={"name": "A", "email": "a@x.test", "phone": ""})
            invoices.create_invoice("SUB-1", period_start)
            return inserted[0]

    def test_the_first_invoice_is_discounted_and_a_renewal_is_not(self):
        first = self.make()
        self.assertEqual((first["amount"], first["discount_amount"], first["coupon"]), (900.0, 100.0, "WELCOME10"))
        renewal = self.make("2026-12-17")
        self.assertEqual((renewal["amount"], renewal["discount_amount"], renewal["coupon"]), (1000, 0.0, None))


class ErpBillingTests(unittest.TestCase):
    def test_off_by_default_and_nothing_is_queued(self):
        with platform_modules("erp_billing") as (frappe, (erp,)):
            frappe.get_cached_doc = Mock(return_value=_Dict(erp_invoicing_enabled=0, erp_company="Mine"))
            self.assertFalse(erp.enabled())
            erp.queue_sales_invoice(_Dict(name="INV-1"))
            frappe.enqueue.assert_not_called()

    def test_a_paid_invoice_with_a_sales_invoice_queues_its_payment_entry(self):
        with platform_modules("erp_billing") as (frappe, (erp,)):
            frappe.get_cached_doc = Mock(return_value=_Dict(erp_invoicing_enabled=1, erp_company="Mine"))
            frappe.db.exists = Mock(return_value=True)
            erp.queue_payment_entry(_Dict(name="INV-1", status="Paid", erp_sales_invoice="SINV-1", erp_payment_entry=None, get=lambda k, d=None: {"status": "Paid", "erp_sales_invoice": "SINV-1", "erp_payment_entry": None}.get(k, d)))
            frappe.enqueue.assert_called_once()
            self.assertEqual(frappe.enqueue.call_args[0][0], "reckon_saas_platform.erp_billing.record_payment")

    def test_a_failed_sales_invoice_is_noted_and_never_raises(self):
        with platform_modules("erp_billing") as (frappe, (erp,)):
            settings = _Dict(erp_invoicing_enabled=1, erp_company="Mine", erp_item_code="Sub", erp_income_account=None, erp_customer_group=None)
            frappe.get_cached_doc = Mock(return_value=settings)
            frappe.db.exists = Mock(return_value=True)
            invoice = _Dict(name="INV-1", status="Unpaid", amount=900, discount_amount=100, currency="BDT", company="Acme",
                            customer_name="Acme", erp_sales_invoice=None, issue_date="2026-11-17", due_date="2026-11-20",
                            period_start="2026-11-17", period_end="2026-12-16", saas_module="distribution", coupon="WELCOME10")
            frappe.get_doc = Mock(return_value=invoice)
            frappe.get_traceback = Mock(return_value="Traceback\nValueError: no income account")
            frappe.db.get_value = Mock(return_value="Acme Ltd")
            with patch.object(erp, "ensure_item", side_effect=ValueError("no income account")):
                self.assertIsNone(erp.create_sales_invoice("INV-1"))
            frappe.db.set_value.assert_called()
            self.assertIn("no income account", frappe.db.set_value.call_args[0][3])

    def test_a_usd_invoice_stays_in_usd_with_its_own_accounts(self):
        with platform_modules("erp_billing") as (frappe, (erp,)):
            settings = _Dict(erp_invoicing_enabled=1, erp_company="Mine", erp_fallback_rates="USD=120", erp_item_code="Sub",
                             erp_income_account=None, erp_customer_group=None)
            frappe.get_cached_doc = Mock(return_value=settings)
            frappe.db.exists = Mock(return_value=True)
            frappe.db.get_value = Mock(side_effect=lambda doctype, *a, **k: "BDT" if (doctype, a[1:] if len(a) > 1 else a) and a and a[-1] == "default_currency" else None)
            self.assertEqual(erp.company_currency("Mine"), "BDT")
            self.assertEqual(erp.fallback_rate("USD"), 120.0)
            self.assertEqual(erp.fallback_rate("EUR"), 0.0)
            self.assertEqual(erp.exchange_rate("BDT", "Mine", "2026-11-17"), 1.0)
            self.assertEqual(erp.exchange_rate("USD", "Mine", "2026-11-17"), 120.0)  # no ERPNext rate: the fallback
            self.assertIsNone(erp.ensure_currency_account("Mine", "BDT", "Receivable"))  # own currency: default accounts

    def test_a_missing_rate_is_noted_not_raised(self):
        with platform_modules("erp_billing") as (frappe, (erp,)):
            settings = _Dict(erp_invoicing_enabled=1, erp_company="Mine", erp_fallback_rates="", erp_item_code="Sub")
            frappe.get_cached_doc = Mock(return_value=settings)
            frappe.db.exists = Mock(return_value=True)
            frappe.db.get_value = Mock(side_effect=lambda doctype, *a, **k: "BDT" if a and a[-1] == "default_currency" else "Acme")
            invoice = _Dict(name="INV-2", status="Unpaid", amount=49, discount_amount=0, currency="USD", company="Acme", customer_name="Acme",
                            erp_sales_invoice=None, issue_date="2026-11-17", due_date="2026-11-20", period_start="2026-11-17",
                            period_end="2026-12-16", saas_module="crm", coupon=None)
            frappe.get_doc = Mock(return_value=invoice)
            frappe.get_traceback = Mock(return_value="Traceback\nValueError: No exchange rate for USD")
            with patch.object(erp, "ensure_item", return_value="Sub"):
                self.assertIsNone(erp.create_sales_invoice("INV-2"))
            self.assertIn("exchange rate", frappe.db.set_value.call_args[0][3])

    def test_settings_and_the_daily_retry_are_wired(self):
        settings = json.loads((DOCTYPES / "saas_platform_settings" / "saas_platform_settings.json").read_text(encoding="utf-8"))
        names = {f["fieldname"] for f in settings["fields"]}
        self.assertTrue({"erp_invoicing_enabled", "erp_company", "erp_item_code", "erp_income_account", "erp_mode_of_payment"} <= names)
        self.assertTrue({"erp_invoicing_enabled", "erp_company"} <= set(settings["field_order"]))
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        self.assertIn("erp_billing.queue_sales_invoice", hooks)
        self.assertIn("erp_billing.queue_payment_entry", hooks)
        self.assertIn("erp_billing.sync_pending", hooks)


if __name__ == "__main__":
    unittest.main()


class SidebarPatchTests(unittest.TestCase):
    def test_a_patch_adds_coupons_to_the_menus_desk_actually_shows(self):
        source = (PKG / "patches" / "add_coupons_to_saas_sidebars.py").read_text(encoding="utf-8")
        self.assertIn('frappe.get_doc("Sidebar", name)', source)  # the Sidebar record, not the old Workspace Sidebar file
        self.assertIn("SaaS Coupon", source)
        self.assertIn("add_coupons_to_saas_sidebars", (PKG / "patches.txt").read_text(encoding="utf-8"))


class CompanyFormScriptTests(unittest.TestCase):
    def test_the_company_form_offers_save_to_the_company_admin_and_stays_read_only_for_others(self):
        js = (PKG / "public" / "js" / "tenant_company_default.js").read_text(encoding="utf-8")
        self.assertIn("frappe.boot.reckon_company_editable", js)
        self.assertIn("You can update your contact and registration details", js)
        self.assertIn("Your company details are managed by Reckon. Contact support to change them.", js)  # everyone else
        self.assertLess(js.index("reckon_company_editable"), js.index("frm.disable_save()"))
