from __future__ import annotations

import re
from urllib.parse import quote, urlencode

import frappe
from frappe.utils import cint, flt, nowdate

from reckon_saas_platform.constants import VENDOR_COMPANY
from reckon_saas_platform.recaptcha import get_recaptcha_site_key
from reckon_saas_platform.saas import get_signup_settings
from reckon_saas_platform.signup_i18n import LANGUAGE_COOKIE, LANGUAGES, get_strings, pick_language

REGISTRATION_NAME = re.compile("REG-[0-9]{1,12}")
MODULE_KEY = re.compile("[a-z][a-z0-9_]{1,59}")
CURRENCY_SYMBOLS = {"BDT": "৳", "USD": "$", "EUR": "€", "INR": "₹"}


def get_context(context):
    context.no_cache = 1
    context.company = VENDOR_COMPANY
    context.current_year = nowdate()[:4]
    context.lang = _request_language()
    context.t = get_strings(context.lang)
    context.js_strings = context.t["js"]
    context.lang_cookie = LANGUAGE_COOKIE
    context.title = f"{context.t['page_title']} · {context.t['product']}"
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
    # and the module selector instead of that module's plans.
    context.module_unavailable = bool(requested) and context.module is None
    context.selected_module = context.module["key"] if context.module else ""
    context.plans, context.plan_groups = get_signup_plans(context.selected_module)
    context.plan_cards = [_plan_card(plan, context.t) for plan in context.plans]
    # Without ?module=, the form shows a module selector and filters the plan
    # cards by the chosen module.
    context.show_module_picker = not context.module and bool(context.modules)
    context.lang_links = {lang: _url_with(lang=lang) for lang in LANGUAGES}
    context.whatsapp_url = _whatsapp_url(context.t, context.module)
    return context


def _request_language() -> str:
    request = getattr(frappe.local, "request", None)
    cookies = getattr(request, "cookies", None) or {}
    headers = getattr(request, "headers", None) or {}
    return pick_language(
        frappe.form_dict.get("lang"),
        cookies.get(LANGUAGE_COOKIE),
        headers.get("Accept-Language"),
    )


def _url_with(**changes) -> str:
    """The signup URL with the current safe parameters plus ``changes``."""
    params = {}
    module = frappe.form_dict.get("module") or ""
    registration = frappe.form_dict.get("registration") or ""
    if MODULE_KEY.fullmatch(module):
        params["module"] = module
    if REGISTRATION_NAME.fullmatch(registration):
        params["registration"] = registration
    params.update(changes)
    return f"/reckonerp-signup?{urlencode(params)}"


def _whatsapp_url(t: dict, module: dict | None) -> str:
    number = re.sub(r"[^0-9]", "", VENDOR_COMPANY.get("whatsapp") or VENDOR_COMPANY.get("phone") or "")
    suffix = f" ({module['name']})" if module else ""
    return f"https://wa.me/{number}?text={quote(t['whatsapp_message'].format(module=suffix))}"


def _plan_card(plan, t: dict) -> dict:
    currency = plan.get("currency") or ""
    price = flt(plan.get("price"))
    amount = f"{price:,.0f}" if price == int(price) else f"{price:,.2f}"
    return {
        "name": plan.get("name"),
        "plan_name": plan.get("plan_name") or plan.get("name"),
        "module": plan.get("saas_module") or "",
        "symbol": CURRENCY_SYMBOLS.get(currency, currency),
        "amount": amount,
        "period": t.get(plan.get("billing_cycle") or "Monthly", ""),
        "features": [line.strip() for line in (plan.get("features") or "").splitlines() if line.strip()],
    }


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
