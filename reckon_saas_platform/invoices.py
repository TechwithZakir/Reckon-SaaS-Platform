"""Invoices for SaaS subscriptions: created at signup, sent as a PDF by email, linked by SMS.

One **SaaS Invoice** is issued for each subscription period that needs paying. After signup
the owner gets the invoice by email (PDF attached) and, if SMS is set up, a link by SMS.
Anyone with the link can read the invoice and download the PDF (the link holds a random key);
paying works as before: the tenant reports the transaction on the Subscription page and a
vendor user verifies it, which marks the invoice paid.

Every send is optional and never blocks a signup or a payment: a failure is logged and the
invoice stays available at its link.
"""

from __future__ import annotations

import re
import secrets
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, nowdate

from reckon_saas_platform import marketing
from reckon_saas_platform.constants import VENDOR_COMPANY

DOCTYPE = "SaaS Invoice"
SETTINGS = "SaaS Platform Settings"
KEY = re.compile(r"[a-f0-9]{32}")
MONTHS = {"Monthly": 1, "Quarterly": 3, "Half Yearly": 6, "Yearly": 12, "Annual": 12}
TEMPLATE = "reckon_saas_platform/templates/saas_invoice.html"
DEFAULT_INSTRUCTIONS = (
    "Pay by bKash, Nagad, Rocket or bank transfer using the details we gave you, then open your Subscription "
    "page and enter the transaction reference. We unlock your workspace once the payment is verified."
)


# --- creating the invoice --------------------------------------------------------------
def _period(subscription, start=None) -> tuple[str, str]:
    start = str(start or subscription.get("start_date") or nowdate())
    months = MONTHS.get(subscription.get("billing_cycle") or "Monthly", 1)
    return start, str(add_days(add_months(start, months), -1))


def _due_date(subscription) -> str:
    """After a trial the first payment is due the day it ends; otherwise after the plan's grace days."""
    trial_end = subscription.get("trial_end_date")
    if trial_end:
        return str(add_days(trial_end, 1))
    return str(add_days(nowdate(), max(cint(subscription.get("grace_days")), 0)))


def create_invoice(subscription_name: str, period_start: str | None = None, due_date: str | None = None):
    """The invoice for a subscription period (the first one by default); the same one if it already exists."""
    subscription = frappe.get_doc("SaaS Subscription", subscription_name)
    start, end = _period(subscription, period_start)
    existing = frappe.db.get_value(DOCTYPE, {"subscription": subscription.name, "period_start": start}, "name")
    if existing:
        return frappe.get_doc(DOCTYPE, existing)
    owner = _owner(subscription)
    invoice = frappe.get_doc(
        {
            "doctype": DOCTYPE,
            "subscription": subscription.name,
            "company": subscription.company,
            "registration": subscription.get("registration"),
            "saas_module": subscription.get("saas_module"),
            "plan": subscription.get("plan"),
            "billing_cycle": subscription.get("billing_cycle") or "Monthly",
            "customer_name": owner["name"],
            "customer_email": owner["email"],
            "customer_phone": owner["phone"],
            "issue_date": nowdate(),
            "due_date": due_date or _due_date(subscription),
            "period_start": start,
            "period_end": end,
            "currency": subscription.get("currency"),
            "amount": subscription.get("price"),
            "status": "Unpaid",
            "access_key": secrets.token_hex(16),
        }
    )
    invoice.insert(ignore_permissions=True)
    return invoice


def _owner(subscription) -> dict:
    """Who the invoice is addressed to: the registration's owner, else the company admin."""
    registration = subscription.get("registration")
    if registration and frappe.db.exists("SaaS Registration", registration):
        row = frappe.db.get_value("SaaS Registration", registration, ["owner_name", "owner_email", "owner_phone"], as_dict=True)
        if row:
            return {"name": row.owner_name or "", "email": row.owner_email or "", "phone": row.owner_phone or ""}
    admin = subscription.get("company_admin") or ""
    row = frappe.db.get_value("User", admin, ["full_name", "email", "mobile_no"], as_dict=True) if admin else None
    return {"name": (row or {}).get("full_name") or admin, "email": (row or {}).get("email") or admin, "phone": (row or {}).get("mobile_no") or ""}


def mark_paid(subscription_name: str, payment_name: str | None = None):
    """A verified payment settles the subscription's open invoice."""
    name = frappe.db.get_value(DOCTYPE, {"subscription": subscription_name, "status": "Unpaid"}, "name", order_by="period_start asc")
    if not name:
        return None
    invoice = frappe.get_doc(DOCTYPE, name)
    invoice.status = "Paid"
    invoice.payment = payment_name
    invoice.paid_on = nowdate()
    invoice.save(ignore_permissions=True)
    return invoice


# --- what the invoice looks like -----------------------------------------------------------
def _setting(field: str):
    try:
        return frappe.db.get_single_value(SETTINGS, field)
    except Exception:
        return None


def public_url(invoice) -> str:
    return f"{marketing.site_base()}/invoice/{invoice.access_key}"


def pdf_url(invoice) -> str:
    return f"{marketing.site_base()}/api/method/reckon_saas_platform.invoices.download?key={invoice.access_key}"


def money(amount, currency: str) -> str:
    return f"{currency} {float(amount or 0):,.2f}".strip()


def share_text(invoice) -> str:
    return f"Invoice {invoice.name} from {VENDOR_COMPANY['name']}: {money(invoice.amount, invoice.currency)}. {public_url(invoice)}"


def whatsapp_share_url(invoice) -> str:
    """A WhatsApp link that carries the invoice link, for the owner to forward or save."""
    return "https://wa.me/?text=" + quote(share_text(invoice))


def whatsapp_to_customer_url(invoice) -> str:
    """For a vendor user: opens WhatsApp to the customer with the invoice link ready to send."""
    from reckon_saas_platform.sms import normalize_bd_mobile

    digits = normalize_bd_mobile(invoice.get("customer_phone") or "") or ""  # 8801XXXXXXXXX
    return f"https://wa.me/{digits}?text=" + quote(share_text(invoice))


def _module_label(key: str | None) -> str:
    from reckon_saas_platform.saas import module_label

    return module_label(key) or "ReckonERP"


def invoice_context(invoice, pdf: bool = False) -> dict:
    base = marketing.site_base()
    plan_name = frappe.db.get_value("SaaS Plan", invoice.plan, "plan_name") if invoice.get("plan") else ""
    description = f"ReckonERP {_module_label(invoice.get('saas_module'))}" + (f" - {plan_name or invoice.plan}" if invoice.get("plan") else "")
    return {
        "pdf": pdf,
        "invoice": invoice,
        "seller": VENDOR_COMPANY,
        "description": description,
        "billing_cycle": invoice.get("billing_cycle") or "Monthly",
        "amount_text": money(invoice.amount, invoice.currency),
        "paid": invoice.status == "Paid",
        "instructions": _setting("invoice_payment_instructions") or DEFAULT_INSTRUCTIONS,
        "note": _setting("invoice_footer_note") or "",
        "subscription_url": f"{base}/reckonerp-subscription",
        "public_url": public_url(invoice),
        "pdf_url": pdf_url(invoice),
        "whatsapp_url": whatsapp_share_url(invoice),
        "vendor_whatsapp_url": f"https://wa.me/{VENDOR_COMPANY['whatsapp']}?text=" + quote(f"Hello, about invoice {invoice.name}"),
    }


def render_html(invoice, pdf: bool = False) -> str:
    return frappe.render_template(TEMPLATE, invoice_context(invoice, pdf))


def render_pdf(invoice) -> bytes:
    from frappe.utils.pdf import get_pdf

    return get_pdf(render_html(invoice, pdf=True))


def get_invoice_by_key(key: str):
    """The invoice behind a link key, or ``None``. Only the exact 32-hex key matches."""
    if not isinstance(key, str) or not KEY.fullmatch(key):
        return None
    name = frappe.db.get_value(DOCTYPE, {"access_key": key}, "name")
    return frappe.get_doc(DOCTYPE, name) if name else None


@frappe.whitelist(allow_guest=True)
def download(key: str):
    """The invoice PDF for a link key."""
    invoice = get_invoice_by_key(key)
    if not invoice:
        frappe.throw(_("Invoice not found."), frappe.DoesNotExistError)
    frappe.local.response.filename = f"{invoice.name}.pdf"
    frappe.local.response.filecontent = render_pdf(invoice)
    frappe.local.response.type = "pdf"


# --- sending -------------------------------------------------------------------------------
def _enabled(field: str) -> bool:
    return (_setting(field) or "Yes") != "No"


def send_email(invoice, receipt: bool = False, reminder: str = "") -> bool:
    """Email the invoice (or the paid receipt) with the PDF attached."""
    from reckon_saas_platform.saas import is_outgoing_email_configured

    if not invoice.get("customer_email") or not is_outgoing_email_configured() or not _enabled("invoice_email_enabled"):
        return False
    context = invoice_context(invoice)
    subject = (f"Payment received: invoice {invoice.name}" if receipt else reminder or f"Your ReckonERP invoice {invoice.name}")
    body = frappe.render_template(
        "reckon_saas_platform/templates/saas_invoice_email.html", {**context, "receipt": receipt, "reminder": reminder}
    )
    try:
        frappe.sendmail(
            recipients=[invoice.customer_email],
            subject=subject,
            message=body,
            attachments=[{"fname": f"{invoice.name}.pdf", "fcontent": render_pdf(invoice)}],
            reference_doctype=DOCTYPE,
            reference_name=invoice.name,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"Invoice email {invoice.name}")
        return False
    invoice.db_set("email_sent_on", frappe.utils.now_datetime())
    return True


def send_sms_link(invoice, reminder: str = "") -> bool:
    """Text the invoice link to a Bangladeshi mobile number, when SMS is set up."""
    from reckon_saas_platform.sms import is_sms_configured, normalize_bd_mobile, send_sms

    number = normalize_bd_mobile(invoice.get("customer_phone") or "")
    if not number or not is_sms_configured() or not _enabled("invoice_sms_enabled"):
        return False
    text = reminder or f"ReckonERP invoice {invoice.name}: {money(invoice.amount, invoice.currency)} due {invoice.due_date}."
    text = f"{text} View and pay: {public_url(invoice)}"
    try:
        send_sms(number, text)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"Invoice SMS {invoice.name}")
        return False
    invoice.db_set("sms_sent_on", frappe.utils.now_datetime())
    return True


def issue_and_send(subscription: str) -> str | None:
    """Create the subscription's invoice and send it. Runs in the background after signup.

    Never raises: the tenant's workspace does not depend on an invoice email.
    """
    try:
        invoice = create_invoice(subscription)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"Invoice for {subscription}")
        return None
    send_email(invoice)
    send_sms_link(invoice)
    return invoice.name


def invoices_for_company(company: str) -> list[dict]:
    """A tenant's invoices for the Subscription page: newest first, each with its link."""
    rows = frappe.get_all(
        DOCTYPE,
        filters={"company": company},
        fields=["name", "subscription", "saas_module", "plan", "amount", "currency", "status", "issue_date", "due_date", "access_key"],
        order_by="creation desc",
        limit=50,
        ignore_permissions=True,
    )
    base = marketing.site_base()
    return [
        {
            "name": r.name,
            "subscription": r.get("subscription") or "",
            "module_name": _module_label(r.saas_module),
            "plan": r.plan,
            "amount_text": money(r.amount, r.currency),
            "status": r.status,
            "issue_date": str(r.issue_date or ""),
            "due_date": str(r.due_date or ""),
            "url": f"{base}/invoice/{r.access_key}",
            "pdf_url": f"{base}/api/method/reckon_saas_platform.invoices.download?key={r.access_key}",
        }
        for r in rows
    ]


def _require_vendor() -> None:
    from reckon_saas_platform.saas_security import is_vendor_user

    if not is_vendor_user():
        frappe.throw(_("Not permitted"), frappe.PermissionError)


@frappe.whitelist()
def resend(name: str) -> dict:
    """Vendor button: send the invoice email and SMS again."""
    _require_vendor()
    invoice = frappe.get_doc(DOCTYPE, name)
    return {"email": send_email(invoice), "sms": send_sms_link(invoice)}


@frappe.whitelist()
def whatsapp_link(name: str) -> str:
    """Vendor button: a WhatsApp link to the customer with the invoice link ready to send."""
    _require_vendor()
    invoice = frappe.get_doc(DOCTYPE, name)
    return whatsapp_to_customer_url(invoice) if invoice.get("customer_phone") else ""


def send_receipt(invoice: str) -> bool:
    """Background job: the paid copy of the invoice, by email."""
    return send_email(frappe.get_doc(DOCTYPE, invoice), receipt=True)


# --- renewals -----------------------------------------------------------------------------------
DEFAULT_RENEWAL_DAYS = 7
RENEWABLE_STATUSES = ["Active", "Grace", "Due"]
MAX_RENEWALS_PER_RUN = 500


def renewal_lead_days() -> int:
    """Days before a paid period ends that its renewal invoice is issued. 0 switches renewals off."""
    value = _setting("invoice_renewal_days")
    return DEFAULT_RENEWAL_DAYS if value in (None, "") else max(cint(value), 0)


def create_renewal_invoices() -> list[str]:
    """Daily job: invoice the next period of every paying subscription that is about to run out.

    A subscription is renewable while it is Active, Due or in Grace and has a paid-until date. Its next
    period starts the day after that date; the invoice is due on the date itself. One invoice per
    period, so running the job twice, or after an outage, never doubles up. One bad subscription never
    stops the others.
    """
    lead = renewal_lead_days()
    if not lead:
        return []
    cutoff = str(add_days(nowdate(), lead))
    rows = frappe.get_all(
        "SaaS Subscription",
        filters={"status": ["in", RENEWABLE_STATUSES], "end_date": ["<=", cutoff]},
        fields=["name", "end_date"],
        order_by="end_date asc",
        limit=MAX_RENEWALS_PER_RUN,
        ignore_permissions=True,
    )
    created = []
    for row in rows:
        if not row.get("end_date"):
            continue
        start = str(add_days(row.end_date, 1))
        try:
            if frappe.db.exists(DOCTYPE, {"subscription": row.name, "period_start": start}):
                continue
            invoice = create_invoice(row.name, period_start=start, due_date=str(row.end_date))
            send_email(invoice)
            send_sms_link(invoice)
            created.append(invoice.name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Renewal invoice for {row.name}")
    return created


# --- payment reminders -----------------------------------------------------------------------------
DEFAULT_REMINDER_SCHEDULE = "-2,1,7"
MAX_REMINDERS = 6
MAX_REMINDER_ROWS = 500
QUIET_SUBSCRIPTION_STATUSES = ("Cancelled", "Suspended", "Expired")


def parse_schedule(text) -> list[int]:
    """``"-2,1,7"`` -> ``[-2, 1, 7]``: days from the due date, sorted, unique, sensible and few."""
    offsets = set()
    for part in re.split(r"[,;\s]+", str(text or "")):
        if re.fullmatch(r"-?\d{1,2}", part) and -30 <= int(part) <= 60:
            offsets.add(int(part))
    return sorted(offsets)[:MAX_REMINDERS]


def reminder_schedule() -> list[int]:
    value = _setting("invoice_reminder_schedule")
    return parse_schedule(DEFAULT_REMINDER_SCHEDULE if value is None else value)


def reminder_wording(invoice, days_from_due: int) -> tuple[str, str]:
    """``(email subject, sms text)`` for a reminder sent ``days_from_due`` days from the due date."""
    amount = money(invoice.amount, invoice.currency)
    if days_from_due < 0:
        when = "is due tomorrow" if days_from_due == -1 else f"is due in {-days_from_due} days"
        return f"Reminder: invoice {invoice.name} {when}", f"ReckonERP reminder: invoice {invoice.name} ({amount}) {when}."
    if days_from_due == 0:
        return f"Invoice {invoice.name} is due today", f"ReckonERP: invoice {invoice.name} ({amount}) is due today."
    late = "1 day" if days_from_due == 1 else f"{days_from_due} days"
    return f"Overdue: invoice {invoice.name} ({late} late)", f"ReckonERP: invoice {invoice.name} ({amount}) is {late} overdue."


def send_payment_reminders() -> list[str]:
    """Daily job: remind owners about unpaid invoices on the schedule (days from the due date).

    The default schedule is 2 days before, then 1 and 7 days after. Each invoice gets each step once.
    If the job missed days, one reminder goes out, not one per missed step. Paid or cancelled invoices,
    and invoices of cancelled, suspended or expired subscriptions, are left alone.
    """
    schedule = reminder_schedule()
    if not schedule:
        return []
    today = frappe.utils.getdate(nowdate())
    rows = frappe.get_all(
        DOCTYPE,
        filters={"status": "Unpaid", "reminders_sent": ["<", len(schedule)], "due_date": ["is", "set"]},
        fields=["name", "due_date", "reminders_sent", "subscription"],
        order_by="due_date asc",
        limit=MAX_REMINDER_ROWS,
        ignore_permissions=True,
    )
    sent = []
    for row in rows:
        try:
            days = (today - frappe.utils.getdate(row.due_date)).days
            reached = sum(1 for offset in schedule if offset <= days)
            if reached <= cint(row.reminders_sent):
                continue
            if frappe.db.get_value("SaaS Subscription", row.subscription, "status") in QUIET_SUBSCRIPTION_STATUSES:
                continue
            invoice = frappe.get_doc(DOCTYPE, row.name)
            step = schedule[reached - 1]
            subject, text = reminder_wording(invoice, days if days >= 0 else step)
            send_email(invoice, reminder=subject)
            send_sms_link(invoice, reminder=text)
            invoice.db_set({"reminders_sent": reached, "last_reminder_on": today})
            sent.append(invoice.name)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Payment reminder for {row.name}")
    return sent
