"""Which apps a tenant sees on the Apps menu and the apps screen.

A company sees the app of each module it subscribes to, and nothing else. Without this every
installed app whose own permission check passes is listed (ERPNext, other modules' apps), because
tenants share roles with those apps. Vendor staff and users with no company are not restricted.

This only tidies what is offered. What a tenant may open is decided by roles, the Company
permission and the Desk guard, as before.
"""

from __future__ import annotations

import frappe

from reckon_saas_platform.module_registry import get_saas_modules
from reckon_saas_platform.tenant_security import get_user_companies, user_can_bypass_tenant

# Frappe's own CRM and HR are replaced by Reckon CRM and Reckon HRMS, and the Reckon Accounts engine by ReckonBooks (Accounts SaaS), which cover the same ground. Their tiles are
# hidden from the Apps screen once the Reckon app is installed; the apps themselves stay (Reckon CRM is built on CRM).
SUPERSEDED_APPS = {"crm": "reckon_crm", "hrms": "reckon_hrms", "reckon_accounts": "reckon_accounts_saas"}


def superseded_apps() -> set[str]:
    try:
        installed = set(frappe.get_installed_apps())
    except Exception:
        return set()  # never let a menu detail stop the other app filtering
    return {app for app, replacement in SUPERSEDED_APPS.items() if replacement in installed}


def allowed_apps_for_user(user: str | None = None) -> set[str] | None:
    """Apps of the modules the user's companies hold; ``None`` when the user is not restricted."""
    user = user or frappe.session.user
    if not user or user == "Guest" or user_can_bypass_tenant(user):
        return None
    companies = get_user_companies(user)
    if not companies:
        return None
    from reckon_saas_platform.saas import _open_module_keys

    held: set[str] = set()
    for company in companies:
        held |= _open_module_keys(company)
    return {module.get("app") for module in get_saas_modules() if module.get("key") in held and module.get("app")}


def is_company_admin(user: str | None = None) -> bool:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False
    return bool(
        frappe.db.exists("Tenant User Assignment", {"user": user, "active": 1, "role_profile": "Company Admin"})
    )


def _default_company_to_tenant(bootinfo) -> None:
    """Reports and forms that default to the system's Company must open on the tenant's own company."""
    from reckon_saas_platform.tenant_security import tenant_company_or_none

    company = tenant_company_or_none(frappe.session.user)
    if company and isinstance(bootinfo.get("sysdefaults"), dict):
        bootinfo["sysdefaults"]["company"] = company
        bootinfo["reckon_tenant_company"] = company


def filter_bootinfo(bootinfo) -> None:
    """``extend_bootinfo`` hook: keep other modules' apps off a tenant's Apps menu and apps screen."""
    try:
        bootinfo["reckon_company_admin"] = is_company_admin()
        _default_company_to_tenant(bootinfo)
        hidden = superseded_apps()
        for app in bootinfo.get("app_data") or []:
            if app.get("app_name") in hidden:
                app["on_apps_screen"] = False
        allowed = allowed_apps_for_user()
        if allowed is None:
            return
        for app in bootinfo.get("app_data") or []:
            if app.get("app_name") not in allowed:
                app["on_apps_screen"] = False
    except Exception:
        frappe.log_error(title="Tenant apps filter failed")  # never break the Desk over a menu


@frappe.whitelist()
def get_apps():
    """``frappe.apps.get_apps`` for the apps screen, limited the same way."""
    from frappe.apps import get_apps as all_apps

    hidden = superseded_apps()
    apps = [app for app in all_apps() if app.get("name") not in hidden]
    allowed = allowed_apps_for_user()
    return apps if allowed is None else [app for app in apps if app.get("name") in allowed]
