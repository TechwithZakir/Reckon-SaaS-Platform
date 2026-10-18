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
    context.plans = frappe.get_all(
        "SaaS Plan",
        filters={"enabled": 1},
        fields=["name", "plan_name", "plan_version", "price", "currency", "billing_cycle", "features"],
        order_by="price asc",
        ignore_permissions=True,
    )
    return context
