"""Pay Now: the payment comes first, then the workspace."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from frappe_stub import _Dict, platform_modules

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"


def registration(**values):
    doc = _Dict(name="REG-1", status="Pending Verification", email_verified=1, phone_verification_required=0, start_mode="Free Trial", plan="Plan")
    doc.update(values)
    doc.db_set = Mock()
    return doc


class HoldTests(unittest.TestCase):
    def test_a_pay_now_signup_waits_for_its_payment_and_a_trial_signup_does_not(self):
        with platform_modules("saas") as (_frappe, (saas,)):
            with patch.object(saas, "enqueue_registration_provisioning") as enqueue:
                pay = registration(start_mode="Pay Now")
                saas._start_provisioning_if_verified(pay)
                pay.db_set.assert_called_once_with("status", "Awaiting Payment")
                enqueue.assert_not_called()
                trial = registration()
                saas._start_provisioning_if_verified(trial)
                trial.db_set.assert_called_once_with("status", "Provisioning")
                enqueue.assert_called_once_with("REG-1")
                unverified = registration(start_mode="Pay Now", email_verified=0)
                saas._start_provisioning_if_verified(unverified)
                unverified.db_set.assert_not_called()  # payment comes after verification

    def test_paying_creates_the_workspace_once(self):
        with platform_modules("saas") as (frappe, (saas,)):
            doc = registration(status="Awaiting Payment", start_mode="Pay Now")
            frappe.get_doc = Mock(return_value=doc)
            with patch.object(saas, "enqueue_registration_provisioning") as enqueue:
                saas.mark_registration_paid("REG-1", "Paddle", "txn_1", "evt_1")
                values = doc.db_set.call_args.args[0]
                self.assertEqual(
                    (values["status"], values["payment_provider"], values["payment_reference"], values["payment_event"]),
                    ("Provisioning", "Paddle", "txn_1", "evt_1"),
                )
                enqueue.assert_called_once_with("REG-1")
                doc.status = "Provisioning"
                saas.mark_registration_paid("REG-1", "Paddle", "txn_1", "evt_1")  # a repeated event
                enqueue.assert_called_once()

    def test_a_manual_payment_needs_a_reference_a_known_provider_and_a_signup_that_is_waiting(self):
        with platform_modules("saas") as (frappe, (saas,)):
            frappe.throw = Mock(side_effect=ValueError("refused"))
            frappe.db.get_value = Mock(return_value="Awaiting Payment")
            with patch.object(saas, "mark_registration_paid") as paid:
                for provider, reference in (("bKash", ""), ("bKash", "x" * 141), ("Nope", "TX1")):
                    with self.assertRaises(ValueError):
                        saas.submit_registration_payment("REG-1", provider, reference)
                paid.assert_not_called()
                frappe.db.get_value = Mock(return_value="Pending Verification")
                with self.assertRaises(ValueError):
                    saas.submit_registration_payment("REG-1", "bKash", "TX1")
                frappe.db.get_value = Mock(return_value="Awaiting Payment")
                out = saas.submit_registration_payment("REG-1", "bKash", " TX1 ")
                paid.assert_called_once_with("REG-1", "bKash", "TX1")
                self.assertTrue(out["ok"])

    def test_the_status_page_gets_the_payment_panel_only_in_the_payment_stage(self):
        with platform_modules("saas") as (frappe, (saas,)):
            row = dict(email_verification_required=1, email_verified=1, phone_verification_required=0, phone_verified=0)
            frappe.db.get_value = Mock(return_value=_Dict(status="Awaiting Payment", **row))
            with patch.object(saas, "signup_payment_info", return_value={"amount": "USD 20.00"}):
                status = saas.registration_verification_status("REG-1")
            self.assertEqual((status["stage"], status["payment"]), ("payment", {"amount": "USD 20.00"}))
            frappe.db.get_value = Mock(return_value=_Dict(status="Provisioning", **row))
            self.assertNotIn("payment", saas.registration_verification_status("REG-1"))


class CardPaymentTests(unittest.TestCase):
    def data(self, price="pri_1"):
        return {
            "id": "txn_1", "subscription_id": "sub_1", "customer_id": "ctm_1",
            "items": [{"price": {"id": price}}], "custom_data": {"registration": "REG-1"},
        }

    def run_paid(self, row, price="pri_1"):
        with platform_modules("paddle", "saas") as (frappe, (paddle, saas)):
            def get_value(doctype, name, *args, **kwargs):
                if doctype == "SaaS Registration":
                    return row
                if doctype == "SaaS Plan":
                    return _Dict(paddle_price_id="pri_1", paddle_environment="sandbox")
                return None

            frappe.db.get_value = Mock(side_effect=get_value)
            with patch.object(paddle, "environment", return_value="sandbox"), patch.object(saas, "mark_registration_paid") as paid:
                result = paddle._apply_transaction(self.data(price), "evt_9")
            return result, paid

    def test_the_first_card_payment_for_the_chosen_plan_creates_the_workspace(self):
        result, paid = self.run_paid(_Dict(status="Awaiting Payment", plan="Plan", subscription=None))
        self.assertTrue(result)
        paid.assert_called_once_with("REG-1", "Paddle", "txn_1", "evt_9")

    def test_a_payment_for_another_price_or_for_a_signup_not_waiting_is_refused_for_review(self):
        with self.assertRaisesRegex(Exception, "not the price"):
            self.run_paid(_Dict(status="Awaiting Payment", plan="Plan", subscription=None), price="pri_other")
        with self.assertRaisesRegex(Exception, "not waiting for a payment"):
            self.run_paid(_Dict(status="Failed", plan="Plan", subscription=None))
        result, paid = self.run_paid(_Dict(status="Provisioning", plan="Plan", subscription=None))
        self.assertTrue(result)  # a replayed event changes nothing
        paid.assert_not_called()

    def test_events_that_arrive_before_the_workspace_exists_wait_and_are_replayed(self):
        with platform_modules("paddle") as (frappe, (paddle,)):
            frappe.db.get_value = Mock(return_value=None)
            with self.assertRaisesRegex(Exception, "still being created"):
                paddle._find_saas_subscription({"registration": "REG-1"}, "sub_1")
        source = (PKG / "saas.py").read_text(encoding="utf-8")
        self.assertIn("reckon_saas_platform.paddle.finish_registration_payment", source)  # replay after provisioning


class WiringTests(unittest.TestCase):
    def test_the_page_takes_the_payment_before_the_workspace(self):
        html = (PKG / "www" / "reckonerp_signup.html").read_text(encoding="utf-8")
        needles = ('data-step="payment"', "data-pay-card-button", "rk-pay-form", 'status.stage === "payment"', "checkout.completed", "customData: card.custom_data", "submit_registration_payment")
        for needle in needles:
            self.assertIn(needle, html)
        data = json.loads((PKG / "saas_platform" / "doctype" / "saas_registration" / "saas_registration.json").read_text(encoding="utf-8"))
        self.assertIn("Awaiting Payment", next(f for f in data["fields"] if f["fieldname"] == "status")["options"])
        self.assertTrue({"payment_provider", "payment_reference", "payment_event"} <= {f["fieldname"] for f in data["fields"]})


if __name__ == "__main__":
    unittest.main()
