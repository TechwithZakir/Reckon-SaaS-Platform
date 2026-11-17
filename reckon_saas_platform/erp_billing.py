"""Post SaaS invoices and payments into the vendor's own ERPNext books.

When "Post to ERPNext" is on in SaaS Platform Settings, every SaaS Invoice becomes a submitted Sales Invoice in the
selling company, and when the invoice is paid a Payment Entry settles it. Nothing here can undo or block a signup,
an invoice or a payment: a failure is written on the invoice (``erp_error``) and retried by ``sync_pending``.
"""

from __future__ import annotations

import frappe
from frappe.utils import flt, getdate, nowdate

DOCTYPE = "SaaS Invoice"
DEFAULT_ITEM = "ReckonERP Subscription"


def _settings():
    return frappe.get_cached_doc("SaaS Platform Settings")


def enabled() -> bool:
    """On in Settings, a selling company chosen, and ERPNext's accounting doctypes present."""
    try:
        settings = _settings()
        return bool(
            settings.get("erp_invoicing_enabled")
            and settings.get("erp_company")
            and frappe.db.exists("DocType", "Sales Invoice")
        )
    except Exception:
        return False


def queue_sales_invoice(doc, method=None) -> None:
    """SaaS Invoice ``after_insert``."""
    if enabled():
        frappe.enqueue(
            "reckon_saas_platform.erp_billing.create_sales_invoice", invoice=doc.name, queue="short", enqueue_after_commit=True
        )


def queue_payment_entry(doc, method=None) -> None:
    """SaaS Invoice ``on_update``: a paid invoice settles its Sales Invoice."""
    if enabled() and doc.get("status") == "Paid" and doc.get("erp_sales_invoice") and not doc.get("erp_payment_entry"):
        frappe.enqueue(
            "reckon_saas_platform.erp_billing.record_payment", invoice=doc.name, queue="short", enqueue_after_commit=True
        )


def _note_error(invoice: str, error: str) -> None:
    frappe.db.set_value(DOCTYPE, invoice, "erp_error", (error or "")[:1000], update_modified=False)


def company_currency(company: str) -> str:
    return frappe.db.get_value("Company", company, "default_currency") or ""


def fallback_rate(currency: str) -> float:
    """A rate from Settings ("USD=120" per line) for when ERPNext has no Currency Exchange record."""
    for line in str(_settings().get("erp_fallback_rates") or "").splitlines():
        code, _sep, value = line.partition("=")
        if code.strip().upper() == (currency or "").upper() and flt(value) > 0:
            return flt(value)
    return 0.0


def exchange_rate(currency: str, company: str, date) -> float:
    """Company-currency units per one unit of ``currency``; 1 when it is the company's own currency."""
    base = company_currency(company)
    if not currency or currency == base:
        return 1.0
    rate = 0.0
    try:
        from erpnext.setup.utils import get_exchange_rate

        rate = flt(get_exchange_rate(currency, base, date))
    except Exception:
        rate = 0.0
    return rate or fallback_rate(currency)


def _account_parent(company: str, kind: str) -> str | None:
    """The group the company keeps its receivable or bank accounts under."""
    fields = ("default_receivable_account",) if kind == "Receivable" else ("default_bank_account", "default_cash_account")
    for field in fields:
        account = frappe.db.get_value("Company", company, field)
        if account:
            return frappe.db.get_value("Account", account, "parent_account")
    return None


def ensure_currency_account(company: str, currency: str, kind: str) -> str | None:
    """A Receivable or Bank account kept in ``currency`` (created once), so a USD invoice stays in USD.

    ``None`` for the company's own currency: its default accounts are used.
    """
    if not currency or currency == company_currency(company):
        return None
    account_type = "Receivable" if kind == "Receivable" else "Bank"
    existing = frappe.db.get_value("Account", {"company": company, "account_type": account_type, "account_currency": currency, "is_group": 0}, "name")
    if existing:
        return existing
    parent = _account_parent(company, kind)
    if not parent:
        return None
    label = "Debtors" if kind == "Receivable" else "Bank"
    doc = frappe.get_doc(
        {
            "doctype": "Account",
            "account_name": f"{label} {currency}",
            "company": company,
            "parent_account": parent,
            "account_type": account_type,
            "account_currency": currency,
            "is_group": 0,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def ensure_item(company: str) -> str:
    code = (_settings().get("erp_item_code") or DEFAULT_ITEM).strip()
    if not frappe.db.exists("Item", code):
        group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
        frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": code,
                "item_name": code,
                "item_group": group,
                "stock_uom": frappe.db.get_value("UOM", "Nos", "name") or frappe.db.get_value("UOM", {}, "name"),
                "is_stock_item": 0,
                "include_item_in_manufacturing": 0,
            }
        ).insert(ignore_permissions=True)
    return code


def ensure_customer(invoice) -> str:
    """One ERPNext Customer per tenant company, named after the business."""
    name = (
        frappe.db.get_value("Company", invoice.get("company"), "company_name") if invoice.get("company") else None
    ) or invoice.get("customer_name") or invoice.get("company") or invoice.name
    existing = frappe.db.get_value("Customer", {"customer_name": name}, "name")
    if existing:
        return existing
    settings = _settings()
    customer = frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": name,
            "customer_type": "Company",
            "customer_group": settings.get("erp_customer_group")
            or frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
            or "All Customer Groups",
            "territory": frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories",
            "email_id": invoice.get("customer_email") or None,
            "mobile_no": invoice.get("customer_phone") or None,
        }
    )
    customer.insert(ignore_permissions=True)
    return customer.name


def create_sales_invoice(invoice: str) -> str | None:
    """The submitted Sales Invoice for a SaaS Invoice; the same one if it already exists."""
    if not enabled():
        return None
    doc = frappe.get_doc(DOCTYPE, invoice)
    if doc.get("erp_sales_invoice") or doc.status == "Cancelled":
        return doc.get("erp_sales_invoice")
    settings = _settings()
    company = settings.get("erp_company")
    try:
        list_price = flt(doc.amount) + flt(doc.get("discount_amount"))
        row = {
            "item_code": ensure_item(company),
            "qty": 1,
            "rate": list_price,
            "description": f"{doc.get('saas_module') or 'ReckonERP'} subscription {doc.get('period_start')} to {doc.get('period_end')}",
        }
        if settings.get("erp_income_account"):
            row["income_account"] = settings.get("erp_income_account")
        posting_date = getdate(doc.get("issue_date") or nowdate())
        # The invoice stays in its own currency (USD stays USD); it is booked to a receivable account in that currency.
        rate = exchange_rate(doc.get("currency"), company, posting_date)
        if not rate:
            raise ValueError(f"No exchange rate for {doc.get('currency')}: add a Currency Exchange record or a fallback rate in Settings.")
        debit_to = ensure_currency_account(company, doc.get("currency"), "Receivable")
        sales_invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "company": company,
                "customer": ensure_customer(doc),
                "posting_date": posting_date,
                "set_posting_time": 1,
                "due_date": getdate(doc.get("due_date") or doc.get("issue_date") or nowdate()),
                "currency": doc.get("currency"),
                "conversion_rate": rate,
                "price_list_currency": doc.get("currency"),
                "plc_conversion_rate": rate,
                **({"debit_to": debit_to} if debit_to else {}),
                "po_no": doc.name,
                "remarks": f"SaaS invoice {doc.name}" + (f", coupon {doc.coupon}" if doc.get("coupon") else ""),
                "items": [row],
                **({"apply_discount_on": "Net Total", "discount_amount": flt(doc.get("discount_amount"))} if flt(doc.get("discount_amount")) else {}),
            }
        )
        sales_invoice.insert(ignore_permissions=True)
        sales_invoice.submit()
    except Exception:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), f"ERPNext Sales Invoice for {invoice}")
        _note_error(invoice, frappe.get_traceback(with_context=False).strip().splitlines()[-1])
        frappe.db.commit()
        return None
    frappe.db.set_value(DOCTYPE, invoice, {"erp_sales_invoice": sales_invoice.name, "erp_error": None}, update_modified=False)
    frappe.db.commit()
    if doc.status == "Paid":
        record_payment(invoice)
    return sales_invoice.name


def record_payment(invoice: str) -> str | None:
    """The Payment Entry that settles the Sales Invoice of a paid SaaS Invoice."""
    if not enabled():
        return None
    doc = frappe.get_doc(DOCTYPE, invoice)
    if doc.status != "Paid" or not doc.get("erp_sales_invoice") or doc.get("erp_payment_entry"):
        return doc.get("erp_payment_entry")
    try:
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        settings = _settings()
        entry = get_payment_entry("Sales Invoice", doc.erp_sales_invoice)
        payment = frappe.db.get_value("SaaS Payment", doc.get("payment"), ["gateway_provider", "gateway_reference"], as_dict=True) if doc.get("payment") else None
        if settings.get("erp_mode_of_payment"):
            entry.mode_of_payment = settings.get("erp_mode_of_payment")
        # Money received in USD goes to a USD bank account, so nothing is converted to Taka on the way in.
        company = settings.get("erp_company")
        bank = ensure_currency_account(company, doc.get("currency"), "Bank")
        if bank:
            entry.paid_to = bank
            entry.paid_to_account_currency = doc.get("currency")
            entry.target_exchange_rate = entry.source_exchange_rate
            entry.received_amount = entry.paid_amount
            entry.mode_of_payment = None
        entry.reference_no = (payment or {}).get("gateway_reference") or doc.name
        entry.reference_date = getdate(doc.get("paid_on") or nowdate())
        entry.posting_date = getdate(doc.get("paid_on") or nowdate())
        entry.insert(ignore_permissions=True)
        entry.submit()
    except Exception:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), f"ERPNext Payment Entry for {invoice}")
        _note_error(invoice, frappe.get_traceback(with_context=False).strip().splitlines()[-1])
        frappe.db.commit()
        return None
    frappe.db.set_value(DOCTYPE, invoice, {"erp_payment_entry": entry.name, "erp_error": None}, update_modified=False)
    frappe.db.commit()
    return entry.name


def sync_pending() -> int:
    """Daily: retry invoices whose posting failed, and settle paid ones that have no Payment Entry.

    Invoices made before posting was switched on are not back-filled; only ones that tried and failed are retried."""
    if not enabled():
        return 0
    done = 0
    for name in frappe.get_all(DOCTYPE, filters={"status": ["!=", "Cancelled"], "erp_sales_invoice": ["in", ["", None]], "erp_error": ["not in", ["", None]]}, pluck="name", limit=200):
        done += bool(create_sales_invoice(name))
    for name in frappe.get_all(
        DOCTYPE, filters={"status": "Paid", "erp_sales_invoice": ["not in", ["", None]], "erp_payment_entry": ["in", ["", None]]}, pluck="name", limit=200
    ):
        done += bool(record_payment(name))
    return done
