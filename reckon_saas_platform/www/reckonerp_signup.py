from __future__ import annotations

import re

import frappe
from frappe.utils import cint

from reckon_saas_platform.recaptcha import get_recaptcha_site_key
from reckon_saas_platform.saas import get_signup_settings

REGISTRATION_NAME = re.compile("REG-[0-9]{1,12}")


def get_context(context):
    context.no_cache = 1
    context.title = "Reckon ERP Signup"
    context.verified = frappe.form_dict.get("verified") == "1"
    context.phone_pending = context.verified and frappe.form_dict.get("phone_pending") == "1"
    registration = frappe.form_dict.get("registration") or ""
    # Echoed into an HTML attribute: accept only the REG-##### naming pattern.
    context.registration = (
        registration if context.phone_pending and REGISTRATION_NAME.fullmatch(registration) else ""
    )
    context.phone_required = bool(cint(get_signup_settings().require_phone_verification))
    context.recaptcha_site_key = get_recaptcha_site_key()
    context.selected_module = frappe.form_dict.get("module") or ""
    context.plans, context.plan_groups = get_signup_plans(context.selected_module)
    return context


def get_signup_plans(module_key: str | None = None) -> tuple[list[dict], list[dict]]:
    """Enabled plans of modules that are on sale, grouped by module.

    ``?module=<key>`` on the signup URL limits the list to one module, so each
    product can link to its own signup page.
    """
    modules = {
        row.name: row.module_name
        for row in frappe.get_all(
            "SaaS Module",
            filters={"enabled": 1},
            fields=["name", "module_name"],
            order_by="module_name asc",
            ignore_permissions=True,
        )
    }
    filters = {"enabled": 1}
    if module_key:
        filters["saas_module"] = module_key
    plans = [
        plan
        for plan in frappe.get_all(
            "SaaS Plan",
            filters=filters,
            fields=[
                "name",
                "plan_name",
                "plan_version",
                "saas_module",
                "price",
                "currency",
                "billing_cycle",
                "features",
            ],
            order_by="price asc",
            ignore_permissions=True,
        )
        if not plan.saas_module or plan.saas_module in modules
    ]
    groups: dict[str, dict] = {}
    for plan in plans:
        key = plan.saas_module or ""
        group = groups.setdefault(
            key, {"module": key, "module_name": modules.get(key) or "Plans", "plans": []}
        )
        group["plans"].append(plan)
    return plans, sorted(groups.values(), key=lambda group: group["module_name"])
