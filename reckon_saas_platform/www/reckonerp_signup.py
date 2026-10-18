from __future__ import annotations

import re

import frappe
from frappe.utils import cint, nowdate

from reckon_saas_platform.constants import VENDOR_COMPANY
from reckon_saas_platform.recaptcha import get_recaptcha_site_key
from reckon_saas_platform.saas import get_signup_settings

REGISTRATION_NAME = re.compile("REG-[0-9]{1,12}")
MODULE_KEY = re.compile("[a-z][a-z0-9_]{1,59}")


def get_context(context):
    context.no_cache = 1
    context.title = "Reckon ERP Signup"
    context.company = VENDOR_COMPANY
    context.current_year = nowdate()[:4]
    context.verified = frappe.form_dict.get("verified") == "1"
    context.phone_pending = context.verified and frappe.form_dict.get("phone_pending") == "1"
    registration = frappe.form_dict.get("registration") or ""
    # Echoed into HTML attributes: accept only the REG-##### naming pattern.
    context.registration = registration if REGISTRATION_NAME.fullmatch(registration) else ""
    context.phone_required = bool(cint(get_signup_settings().require_phone_verification))
    context.recaptcha_site_key = get_recaptcha_site_key()

    context.modules = get_signup_modules()
    requested = frappe.form_dict.get("module") or ""
    context.module = next((m for m in context.modules if m["key"] == requested), None)
    # ?module=<key> naming a module that is unknown or not on sale shows a notice
    # and the module picker instead of silently listing every plan.
    context.module_unavailable = bool(requested) and context.module is None
    context.selected_module = context.module["key"] if context.module else ""
    context.plans, context.plan_groups = get_signup_plans(context.selected_module)
    if context.module_unavailable:
        context.plans, context.plan_groups = [], []
    context.show_module_picker = not context.module and len(context.modules) > 1
    return context


def get_signup_modules() -> list[dict]:
    """Modules on sale, for the picker and the module-specific heading."""
    modules = []
    for row in frappe.get_all(
        "SaaS Module",
        filters={"enabled": 1},
        fields=["name", "module_name", "description", "features"],
        order_by="module_name asc",
        ignore_permissions=True,
    ):
        if not MODULE_KEY.fullmatch(row.name or ""):
            continue
        modules.append(
            {
                "key": row.name,
                "name": row.module_name or row.name,
                "description": row.description or "",
                "features": [
                    _feature_label(line) for line in (row.features or "").splitlines() if line.strip()
                ],
            }
        )
    return modules


ACRONYMS = frozenset({"sr", "dsr", "pwa", "erp", "crm", "hr", "pos", "sms", "vat", "gl"})


def _feature_label(key: str) -> str:
    """``dsr_cash_custody`` -> ``DSR cash custody``."""
    words = key.strip().replace("_", " ").split()
    labelled = [word.upper() if word.lower() in ACRONYMS else word.lower() for word in words]
    if labelled and labelled[0].islower():
        labelled[0] = labelled[0].capitalize()
    return " ".join(labelled)


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
