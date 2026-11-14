"""Desk guard for tenants whose only module is a guarded one.

A module opts in with ``desk_guard: True`` in its ``reckon_saas_modules`` definition,
and lists ``desk_doctypes`` and ``desk_workspaces``. A tenant user whose companies
subscribe to exactly one such module may open only that module's Desk routes and
Resource API DocTypes. Users with several modules, or none, are not restricted here
(Distribution keeps its own guard). Vendor administrators are never restricted.
"""

from __future__ import annotations

import frappe

from reckon_saas_platform.desk_paths import classify, is_allowed, is_desk_home
from reckon_saas_platform.module_registry import get_saas_modules
from reckon_saas_platform.tenant_security import get_user_companies, user_can_bypass_tenant


def guarded_module_for_user(user: str | None) -> dict | None:
    if not user or user == "Guest" or user_can_bypass_tenant(user):
        return None
    companies = get_user_companies(user)
    if not companies:
        return None
    from reckon_saas_platform.saas import is_subscription_active

    # Every module the user's companies subscribe to counts, guarded or not: a company with
    # Accounts and HRMS has two modules, and must not be shut inside HRMS because only HRMS is guarded.
    subscribed = [
        module
        for module in get_saas_modules()
        if any(is_subscription_active(company, module.get("key")) for company in companies)
    ]
    if len(subscribed) != 1 or not subscribed[0].get("desk_guard"):
        return None
    return subscribed[0]


def enforce_module_desk_access() -> None:
    """before_request hook. Raises PermissionError for Desk or DocType requests outside the module."""
    module = guarded_module_for_user(frappe.session.user)
    if not module:
        return
    request = frappe.local.request
    kind, value = classify(request.path)
    if is_desk_home(kind, value):
        # The Desk home lists every app. A single-module tenant goes to its module instead.
        from werkzeug.routing import RequestRedirect

        raise RequestRedirect(module.get("home_route") or "/")
    if is_allowed(kind, value, module.get("desk_doctypes"), module.get("desk_workspaces")):
        return
    # An HTTPException is returned as a real 403 response (a PermissionError from
    # before_request is rendered as a normal page with status 200).
    from werkzeug.exceptions import Forbidden

    raise Forbidden(f"Your subscription covers {module.get('label') or module.get('key')} only.")
