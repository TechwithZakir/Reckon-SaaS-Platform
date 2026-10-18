from __future__ import annotations

import frappe

from reckon_saas_platform.saas import get_vendor_dashboard
from reckon_saas_platform.saas_security import is_vendor_user


def get_context(context):
    if not is_vendor_user():
        frappe.throw("Not permitted", frappe.PermissionError)

    context.no_cache = 1
    context.title = "SaaS Admin"
    data = get_vendor_dashboard()
    context.summary = frappe._dict(data["summary"])
    context.module_stats = data["module_stats"]
    context.plans = data["plans"]
    context.pending_payments = data["pending_payments"]
    context.seed_jobs = data["seed_jobs"]
    context.registrations = data["registrations"]
    context.subscriptions = data["subscriptions"]
    return context
