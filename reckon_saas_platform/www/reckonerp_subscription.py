from __future__ import annotations

import frappe

from reckon_saas_platform.constants import VENDOR_COMPANY
from reckon_saas_platform.saas import PAYMENT_PROVIDERS, get_subscription_summary
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
    context.product = " · ".join(card["module_name"] for card in context.subscriptions if card["module_name"])
    return context


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
    }
