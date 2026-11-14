"""Database-free tests: Paddle card payments (catalog sync, checkout, webhook and events)."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import time
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from frappe_stub import REPO_ROOT, _Dict, platform_modules

APP = REPO_ROOT / "reckon_saas_platform"
HAS_SDK = importlib.util.find_spec("paddle_billing") is not None
if HAS_SDK:
    # Import before the frappe stub replaces ``requests``, which the SDK's client needs.
    import paddle_billing.Notifications  # noqa: F401
SECRET = "pdl_ntfset_test_secret"


def _paddle_on(frappe, **values):
    frappe.settings.update(paddle_enabled=1, paddle_environment="Sandbox", paddle_client_token="test_token")
    frappe.settings["passwords"] = {"paddle_api_key": "pdl_sdbx_apikey_x", "paddle_webhook_secret": SECRET}
    frappe.settings.update(values)


def _signed(body: bytes, ts: int | None = None) -> dict:
    ts = int(time.time()) if ts is None else ts
    digest = hmac.new(SECRET.encode(), f"{ts}:{body.decode()}".encode(), hashlib.sha256).hexdigest()
    return {"Paddle-Signature": f"ts={ts};h1={digest}"}


class AmountsTests(unittest.TestCase):
    def test_lowest_unit_amounts(self):
        with platform_modules("paddle") as (_frappe, (paddle,)):
            self.assertEqual(paddle.to_lowest_unit(25, "USD"), "2500")
            self.assertEqual(paddle.to_lowest_unit("19.99", "usd"), "1999")
            self.assertEqual(paddle.to_lowest_unit(1200, "JPY"), "1200")
            self.assertEqual(paddle.from_lowest_unit("2500", "USD"), 25.0)
            self.assertEqual(paddle.from_lowest_unit("1200", "JPY"), 1200.0)
            with self.assertRaisesRegex(Exception, "more than zero"):
                paddle.to_lowest_unit(0, "USD")

    def test_bdt_is_never_sold_through_paddle(self):
        with platform_modules("paddle") as (_frappe, (paddle,)):
            self.assertFalse(paddle.supports_currency("BDT"))
            self.assertTrue(paddle.supports_currency("usd"))
            self.assertEqual(paddle.CYCLE_TO_PADDLE["Quarterly"], ("month", 3))
            self.assertEqual(paddle.CYCLE_TO_PADDLE["Yearly"], ("year", 1))

    def test_plan_price_only_counts_in_its_own_environment(self):
        with platform_modules("paddle", "saas") as (frappe, (paddle, _saas)):
            _paddle_on(frappe)
            plan = _Dict(currency="USD", paddle_price_id="pri_1", paddle_environment="sandbox")
            self.assertTrue(paddle.card_payment_available(plan))
            frappe.settings["paddle_environment"] = "Production"
            self.assertFalse(paddle.card_payment_available(plan))
            frappe.settings.update(paddle_environment="Sandbox", paddle_enabled=0)
            self.assertFalse(paddle.card_payment_available(plan))


@unittest.skipUnless(HAS_SDK, "paddle-python-sdk is not installed")
class SignatureTests(unittest.TestCase):
    def test_valid_signature_passes_and_anything_else_fails(self):
        with platform_modules("paddle") as (_frappe, (paddle,)):
            body = b'{"event_id":"evt_1"}'
            self.assertTrue(paddle.verify_signature(_signed(body), body, SECRET))
            self.assertFalse(paddle.verify_signature(_signed(body), b'{"event_id":"evt_2"}', SECRET))
            self.assertFalse(paddle.verify_signature({}, body, SECRET))
            self.assertFalse(paddle.verify_signature(_signed(body), body, "other"))
            self.assertFalse(paddle.verify_signature(_signed(body), body, ""))
            self.assertFalse(paddle.verify_signature(_signed(body, ts=int(time.time()) - 60), body, SECRET))
            self.assertFalse(paddle.verify_signature({"Paddle-Signature": "garbage=1"}, body, SECRET))

    def test_webhook_rejects_unsigned_and_queues_signed_once(self):
        with platform_modules("paddle", "saas") as (frappe, (paddle, _saas)):
            _paddle_on(frappe)
            frappe.local.response = {}
            body = json.dumps({"event_id": "evt_1", "event_type": "subscription.updated",
                               "occurred_at": "2026-11-11T05:00:00.000000Z", "data": {}}).encode()
            frappe.request = SimpleNamespace(headers={}, get_data=lambda cache=True: body)
            self.assertEqual(paddle.webhook(), {"ok": False})
            self.assertEqual(frappe.local.response["http_status_code"], 401)
            frappe.enqueue.assert_not_called()

            frappe.local.response = {}
            frappe.request = SimpleNamespace(headers=_signed(body), get_data=lambda cache=True: body)
            self.assertEqual(paddle.webhook(), {"ok": True})
            frappe.enqueue.assert_called_once()
            self.assertEqual(frappe.enqueue.call_args.kwargs["event_id"], "evt_1")
            stored = frappe.get_doc.call_args.args[0]
            self.assertEqual((stored["doctype"], stored["event_id"]), ("Paddle Webhook Event", "evt_1"))
            self.assertEqual(stored["occurred_at"], datetime(2026, 11, 11, 5, 0))

            # Paddle redelivers: already stored, so nothing is queued again.
            frappe.db.exists.return_value = "evt_1"
            frappe.request = SimpleNamespace(headers=_signed(body), get_data=lambda cache=True: body)
            self.assertEqual(paddle.webhook(), {"ok": True})
            frappe.enqueue.assert_called_once()


class SyncPlanTests(unittest.TestCase):
    def _sync(self, plan, module=None):
        with platform_modules("paddle", "saas") as (frappe, (paddle, saas)):
            _paddle_on(frappe)
            frappe.get_doc.return_value = plan
            frappe.db.get_value.side_effect = lambda doctype, *a, **k: (
                module or _Dict(name="sales_agent", module_name="Sales AI Agent", description="d")
            ) if doctype == "SaaS Module" else None
            with patch.object(saas, "_require_vendor") as vendor, \
                    patch.object(paddle, "_api_create_product", return_value="pro_1") as create_product, \
                    patch.object(paddle, "_api_create_price", return_value="pri_new") as create_price, \
                    patch.object(paddle, "_api_archive_price") as archive:
                result = paddle.sync_plan(plan.name)
            vendor.assert_called_once()
            return result, frappe, create_product, create_price, archive

    def test_new_plan_creates_product_and_price(self):
        plan = _Dict(name="SA USD Monthly", plan_name="SA USD Monthly", saas_module="sales_agent", currency="USD",
                     price=49, billing_cycle="Quarterly")
        result, frappe, create_product, create_price, archive = self._sync(plan)
        self.assertEqual(result, {"price_id": "pri_new", "product_id": "pro_1", "created": True})
        create_product.assert_called_once_with("Sales AI Agent", "d", "sales_agent")
        kwargs = create_price.call_args.kwargs
        self.assertEqual((kwargs["amount"], kwargs["currency"], kwargs["cycle"]), ("4900", "USD", "Quarterly"))
        saved = {call.args[0]: call.args[2] for call in frappe.db.set_value.call_args_list}
        self.assertEqual(saved["SaaS Module"], {"paddle_product_id": "pro_1", "paddle_product_environment": "sandbox"})
        self.assertEqual(saved["SaaS Plan"]["paddle_price_id"], "pri_new")
        self.assertEqual(saved["SaaS Plan"]["paddle_price_signature"], "sandbox:USD:4900:Quarterly")
        archive.assert_not_called()

    def test_unchanged_plan_is_a_no_op_and_changed_price_archives_the_old_one(self):
        module = _Dict(name="sales_agent", module_name="Sales AI Agent", paddle_product_id="pro_1",
                       paddle_product_environment="sandbox")
        plan = _Dict(name="P", plan_name="P", saas_module="sales_agent", currency="USD", price=49,
                     billing_cycle="Monthly", paddle_price_id="pri_old", paddle_environment="sandbox",
                     paddle_price_signature="sandbox:USD:4900:Monthly")
        result, _frappe, create_product, create_price, archive = self._sync(plan, module)
        self.assertFalse(result["created"])
        create_price.assert_not_called()

        plan["price"] = 59
        result, _frappe, create_product, create_price, archive = self._sync(plan, module)
        self.assertEqual(result["price_id"], "pri_new")
        create_product.assert_not_called()  # the module's product is reused
        archive.assert_called_once_with("pri_old")

    def test_bdt_plan_is_refused(self):
        plan = _Dict(name="P", plan_name="P", saas_module="sales_agent", currency="BDT", price=2500,
                     billing_cycle="Monthly")
        with self.assertRaisesRegex(Exception, "cannot charge in BDT"):
            self._sync(plan)


class CheckoutTests(unittest.TestCase):
    def _checkout(self, subscription=None, plan=None, company="Acme"):
        with platform_modules("paddle", "saas", "tenant_security") as (frappe, (paddle, saas, tenant_security)):
            _paddle_on(frappe)
            sub = _Dict(name="SUB-1", company="Acme", company_admin="o@acme.test", plan="SA USD", status="Trial")
            sub.update(subscription or {})
            plan_row = _Dict(name="SA USD", currency="USD", paddle_price_id="pri_1", paddle_environment="sandbox")
            plan_row.update(plan or {})

            def get_value(doctype, name, *args, **kwargs):
                return {"SaaS Subscription": sub, "SaaS Plan": plan_row, "User": "o@acme.test"}.get(doctype)

            frappe.db.get_value.side_effect = get_value
            with patch.object(tenant_security, "resolve_tenant", return_value=_Dict(company=company, user="o@acme.test")), \
                    patch.object(saas, "_require_company_admin"):
                return paddle.create_checkout("SUB-1")

    def test_checkout_uses_the_server_side_price_and_tags_the_subscription(self):
        result = self._checkout()
        self.assertEqual(result["price_id"], "pri_1")
        self.assertEqual((result["environment"], result["client_token"]), ("sandbox", "test_token"))
        self.assertEqual(result["custom_data"], {"saas_subscription": "SUB-1", "company": "Acme"})
        self.assertEqual(result["customer_email"], "o@acme.test")

    def test_checkout_refusals(self):
        not_available = "Card payment is not available"
        for label, kwargs, error in (
            ("other company", {"company": "Other"}, "Subscription not found"),
            ("bdt plan", {"plan": {"currency": "BDT"}}, not_available),
            ("not synced", {"plan": {"paddle_price_id": None}}, not_available),
            ("other environment", {"plan": {"paddle_environment": "production"}}, not_available),
            ("suspended", {"subscription": {"status": "Suspended"}}, "closed"),
            ("already on card", {"subscription": {"paddle_subscription_id": "sub_1", "paddle_status": "active"}},
             "already paid by card"),
        ):
            with self.subTest(label), self.assertRaisesRegex(Exception, error):
                self._checkout(**kwargs)


def _transaction(**values):
    data = {
        "id": "txn_1",
        "subscription_id": "sub_1",
        "customer_id": "ctm_1",
        "currency_code": "USD",
        "custom_data": {"saas_subscription": "SUB-1", "company": "Acme"},
        "items": [{"price": {"id": "pri_1"}}],
        "details": {"totals": {"grand_total": "4900"}},
        "billing_period": {"starts_at": "2026-11-11T05:00:00Z", "ends_at": "2026-12-11T05:00:00Z"},
    }
    data.update(values)
    return {"event_type": "transaction.completed", "data": data}


class EventTests(unittest.TestCase):
    def _apply(self, event, sub=None, payment=None, plan_prices=("pri_1",)):
        with platform_modules("paddle", "saas") as (frappe, (paddle, saas)):
            row = _Dict(name="SUB-1", company="Acme", plan="SA USD", saas_module="sales_agent", status="Trial",
                        paddle_subscription_id=None, paddle_updated_at=None)
            row.update(sub or {})

            def get_value(doctype, name, *args, **kwargs):
                if doctype == "SaaS Subscription":
                    if isinstance(name, dict):
                        return row if row.paddle_subscription_id == name["paddle_subscription_id"] else None
                    return row if name == row.name else None
                if doctype == "SaaS Payment":
                    return payment
                return None

            frappe.db.get_value.side_effect = get_value
            frappe.get_all.return_value = list(plan_prices)
            frappe.get_doc.return_value.insert.return_value.name = "PAY-9"
            with patch.object(saas, "verify_payment") as verify, \
                    patch.object(saas, "invalidate_operational_access_cache"):
                handled = paddle.apply_event(event)
            return handled, frappe, verify

    def test_first_payment_verifies_and_matches_paddles_period(self):
        handled, frappe, verify = self._apply(_transaction())
        self.assertTrue(handled)
        payment = frappe.get_doc.call_args.args[0]
        self.assertEqual((payment["amount"], payment["currency"]), (49.0, "USD"))
        self.assertEqual((payment["gateway_provider"], payment["gateway_reference"]), ("Paddle", "txn_1"))
        verify.assert_called_once_with("PAY-9", reference="txn_1", period_end=date(2026, 12, 11))
        linked = frappe.db.set_value.call_args_list[0].args
        self.assertEqual(linked[2], {"paddle_subscription_id": "sub_1", "paddle_customer_id": "ctm_1"})

    def test_replayed_transaction_adds_nothing(self):
        handled, frappe, verify = self._apply(
            _transaction(), sub={"paddle_subscription_id": "sub_1"}, payment=_Dict(name="PAY-9", status="Verified")
        )
        self.assertTrue(handled)
        verify.assert_not_called()
        frappe.get_doc.assert_not_called()

    def test_renewal_after_plan_resync_keeps_working(self):
        # Linked subscription, renewal billed on a price the plan no longer uses.
        handled, _frappe, verify = self._apply(
            _transaction(items=[{"price": {"id": "pri_old"}}], custom_data=None),
            sub={"paddle_subscription_id": "sub_1"},
        )
        self.assertTrue(handled)
        verify.assert_called_once()

    def test_first_payment_on_another_modules_price_is_refused(self):
        with self.assertRaisesRegex(Exception, "not prices of module"):
            self._apply(_transaction(items=[{"price": {"id": "pri_cheap"}}]))

    def test_custom_data_naming_another_company_is_refused(self):
        with self.assertRaisesRegex(Exception, "another company"):
            self._apply(_transaction(custom_data={"saas_subscription": "SUB-1", "company": "Evil"}))

    def test_vendor_suspension_records_money_but_does_not_reopen(self):
        handled, frappe, verify = self._apply(_transaction(), sub={"status": "Suspended"})
        self.assertTrue(handled)
        payment = frappe.get_doc.call_args.args[0]
        self.assertEqual(payment["status"], "Pending Verification")
        verify.assert_not_called()

    def test_one_off_transactions_are_ignored(self):
        handled, _frappe, verify = self._apply(_transaction(subscription_id=None))
        self.assertFalse(handled)
        verify.assert_not_called()

    def test_cancel_is_recorded_and_access_left_to_the_paid_dates(self):
        event = {
            "event_type": "subscription.canceled",
            "occurred_at": "2026-11-20T10:00:00Z",
            "data": {"id": "sub_1", "status": "canceled", "customer_id": "ctm_1", "items": [{"price": {"id": "pri_1"}}],
                     "scheduled_change": None},
        }
        handled, frappe, verify = self._apply(event, sub={"paddle_subscription_id": "sub_1", "status": "Active"})
        self.assertTrue(handled)
        values = frappe.db.set_value.call_args.args[2]
        self.assertEqual(values["paddle_status"], "canceled")
        self.assertNotIn("status", values)  # SaaS status follows end_date, not the card
        verify.assert_not_called()

    def test_scheduled_cancel_and_late_events(self):
        event = {
            "event_type": "subscription.updated",
            "occurred_at": "2026-11-20T10:00:00Z",
            "data": {"id": "sub_1", "status": "active", "items": [{"price": {"id": "pri_1"}}],
                     "scheduled_change": {"action": "cancel", "effective_at": "2026-12-11T05:00:00Z"}},
        }
        _handled, frappe, _verify = self._apply(event, sub={"paddle_subscription_id": "sub_1"})
        self.assertEqual(frappe.db.set_value.call_args.args[2]["paddle_scheduled_change"], "cancel on 2026-12-11")

        _handled, frappe, _verify = self._apply(
            event, sub={"paddle_subscription_id": "sub_1", "paddle_updated_at": datetime(2026, 11, 21)}
        )
        frappe.db.set_value.assert_not_called()

    def _upgrade_event(self, price="pri_std"):
        return {
            "event_type": "subscription.updated",
            "occurred_at": "2026-11-20T10:00:00Z",
            "data": {"id": "sub_1", "status": "active", "items": [{"price": {"id": price}}], "scheduled_change": None},
        }

    def _apply_with_plan(self, event, plan):
        with platform_modules("paddle", "saas") as (frappe, (paddle, saas)):
            row = _Dict(name="SUB-1", company="Acme", plan="SA USD", saas_module="sales_agent", status="Active",
                        paddle_subscription_id="sub_1", paddle_updated_at=None)

            def get_value(doctype, name, *args, **kwargs):
                if doctype == "SaaS Subscription":
                    return row
                if doctype == "SaaS Plan" and isinstance(name, dict):
                    self.plan_filter = name
                    return plan
                return None

            frappe.db.get_value.side_effect = get_value
            frappe.get_all.return_value = ["pri_1", "pri_std"]
            with patch.object(saas, "invalidate_operational_access_cache") as invalidate:
                paddle.apply_event(event)
            return frappe.db.set_value.call_args.args[2], invalidate

    def test_an_upgrade_in_paddle_switches_the_plan_of_the_same_module(self):
        plan = _Dict(name="SA Standard USD", price=40.0, currency="USD", billing_cycle="Monthly", plan_version="2")
        values, invalidate = self._apply_with_plan(self._upgrade_event(), plan)
        self.assertEqual((values["plan"], values["price"], values["currency"], values["billing_cycle"], values["plan_version"]),
                         ("SA Standard USD", 40.0, "USD", "Monthly", "2"))
        self.assertEqual((self.plan_filter["paddle_price_id"], self.plan_filter["saas_module"]), ("pri_std", "sales_agent"))
        self.assertIn("paddle_environment", self.plan_filter)  # never a plan priced in the other environment
        invalidate.assert_called_once_with("Acme")

    def test_no_switch_for_the_same_plan_or_a_price_that_is_no_plans(self):
        same, invalidate = self._apply_with_plan(self._upgrade_event("pri_1"), _Dict(name="SA USD", price=15.0, currency="USD"))
        self.assertNotIn("plan", same)
        invalidate.assert_not_called()
        unknown, _ = self._apply_with_plan(self._upgrade_event("pri_old"), None)
        self.assertNotIn("plan", unknown)

    def test_unknown_events_are_ignored(self):
        handled, _frappe, _verify = self._apply({"event_type": "customer.updated", "data": {}})
        self.assertFalse(handled)


class ProcessEventTests(unittest.TestCase):
    def test_failures_are_kept_for_review_and_processed_events_never_rerun(self):
        with platform_modules("paddle") as (frappe, (paddle,)):
            doc = _Dict(status="Received", attempts=0, payload=json.dumps(_transaction()))
            doc.save = Mock()
            frappe.get_doc.return_value = doc
            with patch.object(paddle, "apply_event", side_effect=paddle.PaddleEventError("no subscription")):
                self.assertEqual(paddle.process_event("evt_1"), "Failed")
            self.assertEqual((doc.error, doc.attempts), ("no subscription", 1))

            with patch.object(paddle, "apply_event", return_value=True):
                self.assertEqual(paddle.process_event("evt_1"), "Processed")
            with patch.object(paddle, "apply_event") as apply:
                self.assertEqual(paddle.process_event("evt_1"), "Processed")
                apply.assert_not_called()


class WiringTests(unittest.TestCase):
    def _fields(self, doctype):
        data = json.loads((APP / f"saas_platform/doctype/{doctype}/{doctype}.json").read_text(encoding="utf-8"))
        paddle_fields = [f["fieldname"] for f in data["fields"] if "paddle" in f["fieldname"]]
        self.assertTrue(paddle_fields)
        self.assertEqual(paddle_fields, [name for name in data["field_order"] if "paddle" in name])
        return {f["fieldname"]: f for f in data["fields"]}

    def test_doctypes_carry_the_paddle_fields(self):
        settings = self._fields("saas_platform_settings")
        self.assertEqual(settings["paddle_api_key"]["fieldtype"], "Password")
        self.assertEqual(settings["paddle_webhook_secret"]["fieldtype"], "Password")
        self.assertEqual(settings["paddle_environment"]["default"], "Sandbox")
        self.assertIn("paddle_price_id", self._fields("saas_plan"))
        self.assertIn("paddle_product_id", self._fields("saas_module"))
        self.assertTrue(self._fields("saas_subscription")["paddle_subscription_id"]["unique"])
        event = json.loads(
            (APP / "saas_platform/doctype/paddle_webhook_event/paddle_webhook_event.json").read_text(encoding="utf-8")
        )
        self.assertEqual([f["fieldname"] for f in event["fields"]], event["field_order"])
        self.assertEqual(event["autoname"], "field:event_id")

    def test_blocked_tenants_can_still_pay_by_card(self):
        with platform_modules("saas_gate") as (_frappe, (gate,)):
            self.assertIn("reckon_saas_platform.paddle.create_checkout", gate.EXEMPT_METHODS)
            self.assertIn("reckon_saas_platform.paddle.get_portal_url", gate.EXEMPT_METHODS)


if __name__ == "__main__":
    unittest.main()
