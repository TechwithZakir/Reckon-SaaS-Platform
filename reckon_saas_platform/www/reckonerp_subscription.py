from __future__ import annotations

import frappe

from reckon_saas_platform import invoices, paddle
from reckon_saas_platform.constants import VENDOR_COMPANY
from reckon_saas_platform.saas import (
    PAYMENT_PROVIDERS,
    get_addable_modules,
    get_subscription_summary,
)
from reckon_saas_platform.tenant_security import TenantResolutionError

BILLING_LABELS = {
    "trial": "Free trial",
    "active": "Active",
    "grace": "Payment due",
    "blocked": "Locked",
}


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect

    context.no_cache = 1
    context.title = "Subscription and Payment"
    context.company_info = VENDOR_COMPANY
    context.payment_providers = PAYMENT_PROVIDERS
    try:
        context.summary = frappe._dict(get_subscription_summary())
    except TenantResolutionError:
        context.summary = frappe._dict({"status": "Missing", "company": "", "modules": []})
    context.subscriptions = [subscription_card(row) for row in context.summary.get("modules") or []]
    company = context.summary.get("company") or ""
    context.invoices = []
    context.addable = []
    context.can_add_modules = False
    if company:
        context.invoices = _safely(lambda: invoices.invoices_for_company(company), [])
        context.addable = _safely(lambda: get_addable_modules(company), [])
        context.can_add_modules = _safely(lambda: _is_company_admin(company), False)
    by_subscription = {}
    for invoice in context.invoices:
        by_subscription.setdefault(invoice["subscription"], invoice)
    for card in context.subscriptions:
        card["invoice"] = by_subscription.get(card["name"])
    context.paddle_environment = ""
    if company and context.can_add_modules:
        context.paddle_environment = _safely(lambda: _add_card_payment(context.subscriptions), "")
    context.payment_instructions = _safely(lambda: invoices._setting("invoice_payment_instructions"), "") or invoices.DEFAULT_INSTRUCTIONS
    context.product = " · ".join(card["module_name"] for card in context.subscriptions if card["module_name"])
    return context


def _safely(fn, default):
    """A problem in an optional section must not take the whole Subscription page down."""
    try:
        return fn()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Subscription page section")
        return default


PADDLE_STATUS_LABELS = {
    "active": "Card payments on",
    "trialing": "Card payments on",
    "past_due": "Card payment failed; Paddle will retry",
    "paused": "Card payments paused",
    "canceled": "Card payments cancelled",
}


def _add_card_payment(cards: list[dict]) -> str:
    """Mark the cards a company admin can pay by card through Paddle.

    Returns the Paddle environment for Paddle.js, or "" when no card can be paid that way.
    """
    if not paddle.is_enabled():
        return ""
    offered = False
    for card in cards:
        details = frappe.db.get_value(
            "SaaS Subscription",
            card["name"],
            ["paddle_subscription_id", "paddle_customer_id", "paddle_status", "paddle_scheduled_change"],
            as_dict=True,
        ) or {}
        plan = frappe.db.get_value(
            "SaaS Plan", card["plan"], ["currency", "paddle_price_id", "paddle_environment"], as_dict=True
        ) if card.get("plan") else None
        status = details.get("paddle_status") or ""
        card_live = bool(details.get("paddle_subscription_id")) and status in paddle.LIVE_PADDLE_STATUSES
        card["paddle"] = {
            "status_label": PADDLE_STATUS_LABELS.get(status, status) if details.get("paddle_subscription_id") else "",
            "scheduled_change": details.get("paddle_scheduled_change") or "",
            "can_manage": bool(details.get("paddle_customer_id")),
        }
        card["card_payment"] = bool(
            card.get("can_pay") and plan and not card_live and paddle.card_payment_available(plan)
        )
        offered = offered or card["card_payment"] or card["paddle"]["can_manage"]
    return paddle.environment() if offered else ""


def _is_company_admin(company: str) -> bool:
    return (
        frappe.db.get_value(
            "Tenant User Assignment", {"user": frappe.session.user, "company": company, "active": 1}, "role_profile"
        )
        == "Company Admin"
    )


def subscription_card(row: dict) -> dict:
    """One module's subscription as the page shows it."""
    billing = row.get("billing") or {}
    state = billing.get("state") or "blocked"
    if state == "trial":
        detail = f"Trial ends on {billing.get('trial_end_date')}"
    elif state == "active":
        detail = f"Paid until {billing['paid_until']}" if billing.get("paid_until") else "Active"
    elif state == "grace":
        detail = f"Pay by {billing.get('grace_end')} to keep access"
    elif billing.get("dues") and row.get("status") != "Pending":
        detail = "Payment overdue. Pay to unlock your workspace."
    else:
        detail = "Your workspace opens when your payment is verified."
    payment = row.get("payment") or {}
    return {
        "name": row.get("name"),
        "module": row.get("saas_module") or "",
        "module_name": row.get("module_name") or row.get("saas_module") or "",
        "plan": row.get("plan") or "",
        "status": row.get("status") or "",
        "price": row.get("price"),
        "currency": row.get("currency") or "",
        "billing_cycle": row.get("billing_cycle") or "Monthly",
        "state": state,
        "state_label": BILLING_LABELS.get(state, state),
        "detail": detail,
        "dues": bool(billing.get("dues")),
        "access": bool(billing.get("access")),
        "landing_route": row.get("landing_route") or "",
        "payment": payment,
        "payment_pending": payment.get("status") == "Pending Verification",
        # Paying is open in a trial, with dues, or before the first payment.
        "can_pay": row.get("status") not in {"Suspended", "Cancelled"},
        # Filled in by _add_card_payment for company admins when Paddle is set up.
        "card_payment": False,
        "paddle": {},
    }
