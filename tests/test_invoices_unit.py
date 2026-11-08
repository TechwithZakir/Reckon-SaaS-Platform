"""Invoices: created at signup, emailed as a PDF, linked by SMS, settled by a verified payment."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from unittest.mock import Mock

from frappe_stub import _Dict, platform_modules

try:
    import jinja2
except ModuleNotFoundError:
    jinja2 = None

PKG = Path(__file__).resolve().parents[1] / "reckon_saas_platform"
KEY = "a" * 32
MODS = ("marketing", "sms", "saas", "invoices")


def prepare(frappe, settings=None):
    settings = settings or {}
    frappe.utils.nowdate = Mock(return_value="2026-11-08")
    frappe.utils.add_days = Mock(side_effect=lambda value, days: __import__("datetime").date.fromisoformat(str(value)) + __import__("datetime").timedelta(days=days))
    frappe.utils.now_datetime = Mock(return_value="now")
    frappe.utils.get_url = Mock(return_value="https://example.test/")
    frappe.db.get_single_value = Mock(side_effect=lambda dt, f: settings.get(f))


def subscription(**extra):
    values = {
        "name": "SUB-1", "company": "Acme Ltd", "registration": "REG-00001", "saas_module": "distribution", "plan": "Dist Pro",
        "billing_cycle": "Monthly", "start_date": "2026-11-08", "trial_end_date": None, "grace_days": 3, "price": 1500, "currency": "BDT",
        "company_admin": "owner@example.test",
    }
    values.update(extra)
    return _Dict(values)


class InvoiceCreationTests(unittest.TestCase):
    def make(self, sub, existing=None):
        ctx = platform_modules(*MODS)
        frappe, mods = ctx.__enter__()
        self.addCleanup(ctx.__exit__, None, None, None)
        prepare(frappe)
        invoices = mods[MODS.index("invoices")]
        invoices.add_months = lambda value, months: __import__("datetime").date(2026, 11 + months if 11 + months <= 12 else 11 + months - 12, 8) if months < 12 else __import__("datetime").date(2027, 11, 8)
        created = []

        def get_doc(arg, name=None):
            if isinstance(arg, dict):
                doc = _Dict(arg)
                doc.insert = Mock(side_effect=lambda ignore_permissions=False: created.append(doc) or doc)
                return doc
            return sub if arg == "SaaS Subscription" else _Dict(name=name)

        frappe.get_doc = Mock(side_effect=get_doc)
        frappe.db.exists = Mock(return_value=True)

        def get_value(doctype, filters, *fields, **kw):
            if doctype == "SaaS Invoice":
                return existing
            if doctype == "SaaS Registration":
                return _Dict(owner_name="Rahim Uddin", owner_email="rahim@example.test", owner_phone="01712345678")
            return None

        frappe.db.get_value = Mock(side_effect=get_value)
        return frappe, invoices, created

    def test_invoice_has_the_period_amount_owner_and_a_private_link_key(self):
        _f, invoices, created = self.make(subscription())
        invoice = invoices.create_invoice("SUB-1")
        data = created[0]
        self.assertEqual((data["subscription"], data["company"], data["status"], data["amount"], data["currency"]), ("SUB-1", "Acme Ltd", "Unpaid", 1500, "BDT"))
        self.assertEqual((data["customer_name"], data["customer_email"], data["customer_phone"]), ("Rahim Uddin", "rahim@example.test", "01712345678"))
        self.assertEqual((data["period_start"], data["period_end"]), ("2026-11-08", "2026-12-07"))
        self.assertEqual(data["due_date"], "2026-11-11")  # the plan's three grace days
        self.assertRegex(data["access_key"], r"^[a-f0-9]{32}$")
        self.assertIs(invoice, data)

    def test_a_trial_pushes_the_first_payment_to_the_day_after_it_ends(self):
        _f, invoices, created = self.make(subscription(trial_end_date="2026-11-21"))
        invoices.create_invoice("SUB-1")
        self.assertEqual(created[0]["due_date"], "2026-11-22")

    def test_the_same_period_is_never_invoiced_twice(self):
        frappe, invoices, created = self.make(subscription(), existing="INV-2026-00001")
        invoice = invoices.create_invoice("SUB-1")
        self.assertEqual(created, [])
        self.assertEqual(invoice.name, "INV-2026-00001")

    def test_two_invoices_never_share_a_link_key(self):
        _f, invoices, created = self.make(subscription())
        for _ in range(5):
            invoices.create_invoice("SUB-1")
        self.assertEqual(len({c["access_key"] for c in created}), 5)

    def test_a_verified_payment_marks_the_open_invoice_paid(self):
        frappe, invoices, _created = self.make(subscription())
        doc = _Dict(name="INV-2026-00002", status="Unpaid")
        doc.save = Mock()
        frappe.db.get_value = Mock(return_value="INV-2026-00002")
        frappe.get_doc = Mock(return_value=doc)
        result = invoices.mark_paid("SUB-1", "PAY-1")
        self.assertEqual((result.status, result.payment, result.paid_on), ("Paid", "PAY-1", "2026-11-08"))
        doc.save.assert_called_once_with(ignore_permissions=True)
        frappe.db.get_value = Mock(return_value=None)
        self.assertIsNone(invoices.mark_paid("SUB-1", "PAY-2"))


def invoice_doc(**extra):
    values = {
        "name": "INV-2026-00001", "customer_name": "Rahim <b>Uddin</b>", "customer_email": "rahim@example.test", "customer_phone": "01712345678",
        "company": "Acme Ltd", "saas_module": "distribution", "plan": "Dist Pro", "billing_cycle": "Monthly", "amount": 1500, "currency": "BDT",
        "status": "Unpaid", "issue_date": "2026-11-08", "due_date": "2026-11-11", "period_start": "2026-11-08", "period_end": "2026-12-07",
        "access_key": KEY, "paid_on": None,
    }
    values.update(extra)
    doc = _Dict(values)
    doc.db_set = Mock()
    return doc


class SendingTests(unittest.TestCase):
    def env(self, settings=None):
        ctx = platform_modules(*MODS)
        frappe, mods = ctx.__enter__()
        self.addCleanup(ctx.__exit__, None, None, None)
        prepare(frappe, settings)
        by = dict(zip(MODS, mods, strict=True))
        by["saas"].is_outgoing_email_configured = Mock(return_value=True)
        by["saas"].module_label = Mock(return_value="Distribution SaaS")
        frappe.db.get_value = Mock(return_value="Distribution Pro")
        frappe.render_template = Mock(side_effect=lambda template, context: f"<html>{template}</html>")
        frappe.sendmail = Mock()
        by["invoices"].render_pdf = Mock(return_value=b"%PDF-1.4 fake")
        return frappe, by

    def test_email_carries_the_pdf_and_a_receipt_has_its_own_subject(self):
        frappe, by = self.env()
        invoice = invoice_doc()
        self.assertTrue(by["invoices"].send_email(invoice))
        sent = frappe.sendmail.call_args.kwargs
        self.assertEqual(sent["recipients"], ["rahim@example.test"])
        self.assertEqual(sent["subject"], "Your ReckonERP invoice INV-2026-00001")
        self.assertEqual(sent["attachments"], [{"fname": "INV-2026-00001.pdf", "fcontent": b"%PDF-1.4 fake"}])
        self.assertEqual((sent["reference_doctype"], sent["reference_name"]), ("SaaS Invoice", "INV-2026-00001"))
        invoice.db_set.assert_called_with("email_sent_on", "now")
        by["invoices"].send_email(invoice, receipt=True)
        self.assertEqual(frappe.sendmail.call_args.kwargs["subject"], "Payment received: invoice INV-2026-00001")

    def test_email_is_skipped_without_mail_setup_an_address_or_when_switched_off(self):
        frappe, by = self.env()
        by["saas"].is_outgoing_email_configured = Mock(return_value=False)
        self.assertFalse(by["invoices"].send_email(invoice_doc()))
        by["saas"].is_outgoing_email_configured = Mock(return_value=True)
        self.assertFalse(by["invoices"].send_email(invoice_doc(customer_email="")))
        frappe2, by2 = self.env({"invoice_email_enabled": "No"})
        self.assertFalse(by2["invoices"].send_email(invoice_doc()))
        frappe.sendmail.assert_not_called()
        frappe2.sendmail.assert_not_called()

    def test_a_mail_failure_is_logged_not_raised(self):
        frappe, by = self.env()
        frappe.sendmail = Mock(side_effect=RuntimeError("smtp down"))
        self.assertFalse(by["invoices"].send_email(invoice_doc()))
        frappe.log_error.assert_called()

    def test_sms_link_goes_to_a_bangladeshi_mobile_when_sms_is_set_up(self):
        frappe, by = self.env()
        by["sms"].is_sms_configured = Mock(return_value=True)
        sent = []
        by["sms"].send_sms = lambda number, text: sent.append((number, text))
        invoice = invoice_doc()
        self.assertTrue(by["invoices"].send_sms_link(invoice))
        number, text = sent[0]
        self.assertEqual(number, "8801712345678")
        self.assertIn("BDT 1,500.00", text)
        self.assertIn(f"https://example.test/invoice/{KEY}", text)
        invoice.db_set.assert_called_with("sms_sent_on", "now")
        # no number, no gateway, or switched off: nothing is sent
        self.assertFalse(by["invoices"].send_sms_link(invoice_doc(customer_phone="")))
        self.assertFalse(by["invoices"].send_sms_link(invoice_doc(customer_phone="+441234567890")))
        by["sms"].is_sms_configured = Mock(return_value=False)
        self.assertFalse(by["invoices"].send_sms_link(invoice_doc()))
        self.assertEqual(len(sent), 1)

    def test_issue_and_send_never_raises(self):
        frappe, by = self.env()
        inv = by["invoices"]
        inv.create_invoice = Mock(side_effect=RuntimeError("db"))
        self.assertIsNone(inv.issue_and_send("SUB-1"))
        frappe.log_error.assert_called()
        invoice = invoice_doc()
        inv.create_invoice = Mock(return_value=invoice)
        inv.send_email = Mock(return_value=True)
        inv.send_sms_link = Mock(return_value=True)
        self.assertEqual(inv.issue_and_send("SUB-1"), "INV-2026-00001")
        inv.send_email.assert_called_once_with(invoice)
        inv.send_sms_link.assert_called_once_with(invoice)

    def test_links_and_the_whatsapp_share_urls(self):
        _f, by = self.env()
        inv = by["invoices"]
        invoice = invoice_doc()
        self.assertEqual(inv.public_url(invoice), f"https://example.test/invoice/{KEY}")
        self.assertIn("/api/method/reckon_saas_platform.invoices.download?key=" + KEY, inv.pdf_url(invoice))
        share = inv.whatsapp_share_url(invoice)
        self.assertTrue(share.startswith("https://wa.me/?text="))
        self.assertIn("INV-2026-00001", share)
        self.assertTrue(inv.whatsapp_to_customer_url(invoice).startswith("https://wa.me/8801712345678?text="))

    def test_only_an_exact_key_finds_an_invoice(self):
        frappe, by = self.env()
        inv = by["invoices"]
        frappe.db.get_value = Mock(return_value="INV-2026-00001")
        frappe.get_doc = Mock(return_value=invoice_doc())
        self.assertIsNotNone(inv.get_invoice_by_key(KEY))
        for bad in ("", "abc", KEY[:-1], KEY + "0", "A" * 32, "../" + "a" * 29, None, 5):
            frappe.db.get_value.reset_mock()
            self.assertIsNone(inv.get_invoice_by_key(bad), bad)
            frappe.db.get_value.assert_not_called()  # a bad key never reaches the database
        frappe.db.get_value = Mock(return_value=None)
        self.assertIsNone(inv.get_invoice_by_key(KEY))

    def test_download_returns_the_pdf_or_not_found(self):
        frappe, by = self.env()
        inv = by["invoices"]
        frappe.local.response = _Dict()
        frappe.db.get_value = Mock(return_value="INV-2026-00001")
        frappe.get_doc = Mock(return_value=invoice_doc())
        inv.download(KEY)
        self.assertEqual((frappe.local.response.filename, frappe.local.response.type), ("INV-2026-00001.pdf", "pdf"))
        self.assertEqual(frappe.local.response.filecontent, b"%PDF-1.4 fake")
        frappe.db.get_value = Mock(return_value=None)
        with self.assertRaises(frappe.DoesNotExistError):
            inv.download(KEY)

    def test_a_tenants_invoice_list_has_links_and_no_other_companys_rows(self):
        frappe, by = self.env()
        frappe.get_all = Mock(return_value=[_Dict(name="INV-1", saas_module="distribution", plan="P", amount=10, currency="BDT", status="Paid", issue_date="2026-11-01", due_date="2026-11-02", access_key=KEY)])
        rows = by["invoices"].invoices_for_company("Acme Ltd")
        self.assertEqual(frappe.get_all.call_args.kwargs["filters"], {"company": "Acme Ltd"})
        self.assertEqual((rows[0]["amount_text"], rows[0]["status"], rows[0]["url"]), ("BDT 10.00", "Paid", f"https://example.test/invoice/{KEY}"))


class RenewalTests(unittest.TestCase):
    def env(self, rows, lead=None, existing=()):
        ctx = platform_modules(*MODS)
        frappe, mods = ctx.__enter__()
        self.addCleanup(ctx.__exit__, None, None, None)
        settings = {} if lead is None else {"invoice_renewal_days": lead}
        prepare(frappe, settings)
        frappe.utils.cint = lambda v: int(v or 0)
        inv = mods[MODS.index("invoices")]
        inv.cint = frappe.utils.cint
        frappe.get_all = Mock(return_value=rows)
        frappe.db.exists = Mock(side_effect=lambda doctype, filters=None: (filters or {}).get("period_start") in existing)
        made = []
        inv.create_invoice = Mock(side_effect=lambda name, period_start=None, due_date=None: made.append((name, period_start, due_date)) or _Dict(name=f"INV-{len(made)}"))
        inv.send_email = Mock(return_value=True)
        inv.send_sms_link = Mock(return_value=True)
        return frappe, inv, made

    def test_the_next_period_is_invoiced_a_week_before_the_paid_period_ends(self):
        frappe, inv, made = self.env([_Dict(name="SUB-1", end_date="2026-11-14"), _Dict(name="SUB-2", end_date="2026-11-01")])
        created = inv.create_renewal_invoices()
        self.assertEqual(made, [("SUB-1", "2026-11-15", "2026-11-14"), ("SUB-2", "2026-11-02", "2026-11-01")])
        self.assertEqual(created, ["INV-1", "INV-2"])
        filters = frappe.get_all.call_args.kwargs["filters"]
        self.assertEqual(filters, {"status": ["in", ["Active", "Grace", "Due"]], "end_date": ["<=", "2026-11-15"]})
        self.assertEqual(inv.send_email.call_count, 2)
        self.assertEqual(inv.send_sms_link.call_count, 2)

    def test_a_period_is_never_invoiced_twice(self):
        _f, inv, made = self.env([_Dict(name="SUB-1", end_date="2026-11-14")], existing=("2026-11-15",))
        self.assertEqual(inv.create_renewal_invoices(), [])
        self.assertEqual(made, [])
        inv.send_email.assert_not_called()

    def test_renewals_can_be_switched_off_and_the_lead_time_is_configurable(self):
        frappe, inv, made = self.env([_Dict(name="SUB-1", end_date="2026-11-14")], lead=0)
        self.assertEqual(inv.create_renewal_invoices(), [])
        frappe.get_all.assert_not_called()
        frappe2, inv2, made2 = self.env([_Dict(name="SUB-1", end_date="2026-11-14")], lead=14)
        inv2.create_renewal_invoices()
        self.assertEqual(frappe2.get_all.call_args.kwargs["filters"]["end_date"], ["<=", "2026-11-22"])
        self.assertEqual(inv2.renewal_lead_days(), 14)
        _f3, inv3, _m3 = self.env([])
        self.assertEqual(inv3.renewal_lead_days(), 7)  # unset means the default

    def test_one_bad_subscription_does_not_stop_the_rest(self):
        frappe, inv, made = self.env([_Dict(name="SUB-1", end_date="2026-11-10"), _Dict(name="SUB-2", end_date="2026-11-12")])
        calls = []

        def create(name, period_start=None, due_date=None):
            calls.append(name)
            if name == "SUB-1":
                raise RuntimeError("bad row")
            return _Dict(name="INV-OK")

        inv.create_invoice = Mock(side_effect=create)
        self.assertEqual(inv.create_renewal_invoices(), ["INV-OK"])
        self.assertEqual(calls, ["SUB-1", "SUB-2"])
        frappe.log_error.assert_called_once()

    def test_a_subscription_without_a_paid_until_date_is_skipped(self):
        _f, inv, made = self.env([_Dict(name="SUB-1", end_date=None)])
        self.assertEqual(inv.create_renewal_invoices(), [])
        self.assertEqual(made, [])

    def test_a_payment_settles_the_oldest_unpaid_invoice_first(self):
        frappe, inv, _m = self.env([])
        frappe.db.get_value = Mock(return_value=None)
        inv.mark_paid("SUB-1", "PAY-1")
        self.assertEqual(frappe.db.get_value.call_args.kwargs["order_by"], "period_start asc")

    def test_job_setting_and_schedule_are_wired(self):
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"reckon_saas_platform.invoices.create_renewal_invoices"', hooks)
        settings = json.loads((PKG / "saas_platform" / "doctype" / "saas_platform_settings" / "saas_platform_settings.json").read_text(encoding="utf-8"))
        names = [f["fieldname"] for f in settings["fields"]]
        self.assertEqual(settings["field_order"], names)
        field = next(f for f in settings["fields"] if f["fieldname"] == "invoice_renewal_days")
        self.assertEqual((field["fieldtype"], field["default"]), ("Int", "7"))


class ReminderTests(unittest.TestCase):
    def env(self, rows, schedule=None, status="Active"):
        ctx = platform_modules(*MODS)
        frappe, mods = ctx.__enter__()
        self.addCleanup(ctx.__exit__, None, None, None)
        settings = {} if schedule is None else {"invoice_reminder_schedule": schedule}
        prepare(frappe, settings)
        frappe.utils.cint = lambda v: int(v or 0)
        frappe.utils.getdate = lambda v: __import__("datetime").date.fromisoformat(str(v)[:10])
        inv = mods[MODS.index("invoices")]
        inv.cint = frappe.utils.cint
        frappe.get_all = Mock(return_value=rows)
        frappe.db.get_value = Mock(return_value=status)
        self.docs = {}

        def get_doc(doctype, name):
            doc = invoice_doc(name=name)
            self.docs[name] = doc
            return doc

        frappe.get_doc = Mock(side_effect=get_doc)
        inv.send_email = Mock(return_value=True)
        inv.send_sms_link = Mock(return_value=True)
        return frappe, inv

    def row(self, due, sent=0, name="INV-1"):
        return _Dict(name=name, due_date=due, reminders_sent=sent, subscription="SUB-1")

    def test_schedule_is_parsed_safely(self):
        _f, inv = self.env([])
        self.assertEqual(inv.parse_schedule("-2,1,7"), [-2, 1, 7])
        self.assertEqual(inv.parse_schedule(" 7; 1 ,1, -2 "), [-2, 1, 7])
        self.assertEqual(inv.parse_schedule("abc, 999, -99, 3"), [3])
        self.assertEqual(inv.parse_schedule(""), [])
        self.assertEqual(len(inv.parse_schedule(",".join(str(n) for n in range(10)))), 6)
        self.assertEqual(inv.reminder_schedule(), [-2, 1, 7])  # unset means the default

    def test_a_reminder_goes_out_on_each_step_once(self):
        # today is 2026-11-08
        for due, sent, expect in (
            ("2026-11-10", 0, 1),   # due in 2 days: the "-2" step
            ("2026-11-11", 0, 0),   # due in 3 days: too early
            ("2026-11-07", 1, 1),   # 1 day late: the "+1" step
            ("2026-11-07", 2, 0),   # already sent that step
            ("2026-11-01", 2, 1),   # 7 days late: the last step
        ):
            frappe, inv = self.env([self.row(due, sent)])
            sent_names = inv.send_payment_reminders()
            self.assertEqual(len(sent_names), expect, (due, sent))
            if expect:
                inv.send_email.assert_called_once()
                inv.send_sms_link.assert_called_once()

    def test_missed_days_send_one_reminder_and_record_every_step_reached(self):
        frappe, inv = self.env([self.row("2026-10-20", 0)])  # 19 days late, nothing sent yet
        self.assertEqual(inv.send_payment_reminders(), ["INV-1"])
        inv.send_email.assert_called_once()
        self.docs["INV-1"].db_set.assert_called_once_with({"reminders_sent": 3, "last_reminder_on": __import__("datetime").date(2026, 11, 8)})

    def test_wording_says_before_today_and_late(self):
        _f, inv = self.env([])
        doc = invoice_doc()
        self.assertEqual(inv.reminder_wording(doc, -2)[0], "Reminder: invoice INV-2026-00001 is due in 2 days")
        self.assertEqual(inv.reminder_wording(doc, -1)[0], "Reminder: invoice INV-2026-00001 is due tomorrow")
        self.assertEqual(inv.reminder_wording(doc, 0)[0], "Invoice INV-2026-00001 is due today")
        self.assertEqual(inv.reminder_wording(doc, 1)[0], "Overdue: invoice INV-2026-00001 (1 day late)")
        subject, text = inv.reminder_wording(doc, 7)
        self.assertEqual(subject, "Overdue: invoice INV-2026-00001 (7 days late)")
        self.assertIn("BDT 1,500.00", text)

    def test_subject_and_text_reach_the_email_and_sms(self):
        frappe, inv = self.env([self.row("2026-11-07", 1)])
        inv.send_payment_reminders()
        subject = inv.send_email.call_args.kwargs["reminder"]
        text = inv.send_sms_link.call_args.kwargs["reminder"]
        self.assertEqual(subject, "Overdue: invoice INV-1 (1 day late)")
        self.assertIn("1 day overdue", text)

    def test_closed_subscriptions_and_an_empty_schedule_are_left_alone(self):
        for status in ("Cancelled", "Suspended", "Expired"):
            _f, inv = self.env([self.row("2026-11-07", 1)], status=status)
            self.assertEqual(inv.send_payment_reminders(), [], status)
            inv.send_email.assert_not_called()
        frappe, inv = self.env([self.row("2026-11-07", 1)], schedule="")
        self.assertEqual(inv.send_payment_reminders(), [])
        frappe.get_all.assert_not_called()

    def test_query_asks_only_for_unpaid_invoices_still_owed_a_reminder(self):
        frappe, inv = self.env([])
        inv.send_payment_reminders()
        filters = frappe.get_all.call_args.kwargs["filters"]
        self.assertEqual((filters["status"], filters["reminders_sent"]), ("Unpaid", ["<", 3]))

    def test_one_failure_does_not_stop_the_others(self):
        frappe, inv = self.env([self.row("2026-11-07", 1, "INV-1"), self.row("2026-11-07", 1, "INV-2")])
        inv.send_email = Mock(side_effect=[RuntimeError("smtp"), True])
        self.assertEqual(inv.send_payment_reminders(), ["INV-2"])
        frappe.log_error.assert_called_once()

    def test_wiring_and_the_reminder_email_text(self):
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"reckon_saas_platform.invoices.send_payment_reminders"', hooks)
        doctype = json.loads((PKG / "saas_platform" / "doctype" / "saas_invoice" / "saas_invoice.json").read_text(encoding="utf-8"))
        self.assertEqual(doctype["field_order"], [f["fieldname"] for f in doctype["fields"]])
        self.assertEqual(next(f for f in doctype["fields"] if f["fieldname"] == "reminders_sent")["default"], "0")
        settings = json.loads((PKG / "saas_platform" / "doctype" / "saas_platform_settings" / "saas_platform_settings.json").read_text(encoding="utf-8"))
        names = [f["fieldname"] for f in settings["fields"]]
        self.assertEqual(settings["field_order"], names)
        self.assertEqual(next(f for f in settings["fields"] if f["fieldname"] == "invoice_reminder_schedule")["default"], "-2,1,7")
        if jinja2:
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(PKG.parent)))
            ctx = {
                "invoice": invoice_doc(), "description": "ReckonERP HRMS", "amount_text": "BDT 1,500.00", "instructions": "Pay by bKash.",
                "subscription_url": "https://example.test/reckonerp-subscription", "public_url": "https://example.test/invoice/x",
                "seller": {"name": "R", "email": "e", "phone": "p"}, "receipt": False, "reminder": "Overdue: invoice X (1 day late)",
            }
            body = env.get_template("reckon_saas_platform/templates/saas_invoice_email.html").render(**ctx)
            self.assertIn("Overdue: invoice X (1 day late)", body)
            self.assertIn("already paid", body)
            self.assertNotIn("Thank you for choosing ReckonERP", body)


class WiringTests(unittest.TestCase):
    def test_signup_sends_an_invoice_and_a_verified_payment_settles_it(self):
        source = (PKG / "saas.py").read_text(encoding="utf-8")
        self.assertIn('"reckon_saas_platform.invoices.issue_and_send"', source)
        self.assertIn("enqueue_after_commit=True", source[source.index("issue_and_send") - 200 : source.index("issue_and_send") + 200])
        self.assertIn("_settle_invoice(subscription.name, payment_doc.name)", source)
        self.assertIn('"reckon_saas_platform.invoices.send_receipt"', source)

    def test_route_permissions_doctype_and_settings(self):
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('{"from_route": "/invoice/<key>", "to_route": "reckon_invoice"}', hooks)
        self.assertIn('"SaaS Invoice": "reckon_saas_platform.saas_security.get_vendor_only_query"', hooks)
        doctype = json.loads((PKG / "saas_platform" / "doctype" / "saas_invoice" / "saas_invoice.json").read_text(encoding="utf-8"))
        self.assertEqual(doctype["autoname"], "format:INV-{YYYY}-{#####}")
        self.assertEqual(doctype["field_order"], [f["fieldname"] for f in doctype["fields"]])
        key = next(f for f in doctype["fields"] if f["fieldname"] == "access_key")
        self.assertEqual((key["unique"], key["read_only"]), (1, 1))
        settings = json.loads((PKG / "saas_platform" / "doctype" / "saas_platform_settings" / "saas_platform_settings.json").read_text(encoding="utf-8"))
        names = [f["fieldname"] for f in settings["fields"]]
        self.assertEqual(settings["field_order"], names)
        for field in ("invoice_email_enabled", "invoice_sms_enabled", "invoice_payment_instructions"):
            self.assertIn(field, names)
        page = (PKG / "www" / "reckon_invoice.html").read_text(encoding="utf-8")
        self.assertIn("saas_invoice.html", page)  # a standalone page, not wrapped in the site theme

    def test_the_pdf_template_avoids_css_the_pdf_engine_cannot_draw(self):
        template = (PKG / "templates" / "saas_invoice.html").read_text(encoding="utf-8")
        for unsupported in ("display:flex", "display:grid", "var(--", "gap:"):
            self.assertNotIn(unsupported, template)


@unittest.skipUnless(jinja2, "jinja2 is not installed")
class TemplateTests(unittest.TestCase):
    def render(self, name, **context):
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(PKG.parent)))
        return env.get_template(f"reckon_saas_platform/templates/{name}").render(**context)

    def context(self, **extra):
        invoice = invoice_doc()
        values = {
            "pdf": False, "invoice": invoice, "seller": {"name": "Reckon Technologies Ltd.", "email": "hello@reckon.tech", "phone": "+8801325-009955", "website": "https://www.reckon.tech/"},
            "description": "ReckonERP Distribution SaaS - Distribution Pro", "billing_cycle": "Monthly", "amount_text": "BDT 1,500.00", "paid": False,
            "instructions": "Pay by bKash, then report it.", "note": "", "subscription_url": "https://example.test/reckonerp-subscription",
            "public_url": f"https://example.test/invoice/{KEY}", "pdf_url": f"https://example.test/api/method/x?key={KEY}",
            "whatsapp_url": "https://wa.me/?text=hi", "vendor_whatsapp_url": "https://wa.me/8801325009955",
        }
        values.update(extra)
        return values

    def test_invoice_page_shows_amounts_actions_and_escapes_customer_text(self):
        page = self.render("saas_invoice.html", **self.context())
        for needle in ("INV-2026-00001", "BDT 1,500.00", "2026-11-08 to 2026-12-07", "How to pay", "Download PDF", "Report your payment", "Share on WhatsApp", "noindex"):
            self.assertIn(needle, page, needle)
        self.assertIn("Rahim &lt;b&gt;Uddin&lt;/b&gt;", page)
        self.assertNotIn("<b>Uddin</b>", page)

    def test_pdf_copy_has_no_buttons_and_a_paid_invoice_says_so(self):
        pdf = self.render("saas_invoice.html", **self.context(pdf=True))
        self.assertNotIn("Download PDF", pdf)
        paid = self.render("saas_invoice.html", **self.context(paid=True, invoice=invoice_doc(status="Paid", paid_on="2026-11-09")))
        self.assertIn("on 2026-11-09", paid)
        self.assertNotIn("How to pay", paid)
        self.assertNotIn("Report your payment", paid)

    def test_email_text_for_an_invoice_and_for_a_receipt(self):
        invoice_mail = self.render("saas_invoice_email.html", **self.context(receipt=False))
        self.assertIn("Open your Subscription page", invoice_mail)
        self.assertIn("is attached as a PDF", invoice_mail)
        receipt = self.render("saas_invoice_email.html", **self.context(receipt=True))
        self.assertIn("We received your payment", receipt)
        self.assertNotIn("Open your Subscription page", receipt)
        self.assertEqual(len(re.findall(r"INV-2026-00001", receipt)), 1)


if __name__ == "__main__":
    unittest.main()
