"""Request-level subscription and provisioning gate for tenant users.

Every Desk (``/app``, ``/desk``) and API (``/api``, ``?cmd=``) request from a user
with an active Tenant User Assignment must belong to a company whose seed job is
complete and whose subscription is active. Login, logout, the subscription
status API and static assets stay reachable so a blocked tenant can still sign
in, see why, and sign out. Vendor administrators and Guests are not gated here.
"""

from __future__ import annotations

from urllib.parse import unquote

import frappe
from frappe import _

from reckon_saas_platform.saas import SubscriptionGateError, has_operational_access
from reckon_saas_platform.tenant_security import get_user_companies

SUBSCRIPTION_ROUTE = "/reckonerp-subscription"

GATED_PATH_PREFIXES = ("/app", "/desk", "/api")
EXEMPT_PATH_PREFIXES = ("/assets/", "/files/", "/api/method/ping", "/api/method/version")
EXEMPT_METHODS = frozenset(
    {
        "login",
        "logout",
        "web_logout",
        "frappe.handler.logout",
        "frappe.handler.web_logout",
        "frappe.auth.get_logged_user",
        "frappe.www.login.login_via_token",
        "reckon_saas_platform.saas.get_subscription_summary",
        "reckon_saas_platform.saas.public_signup",
        "reckon_saas_platform.saas.verify_registration_email",
        "reckon_saas_platform.saas.verify_registration_phone",
        "reckon_saas_platform.saas.resend_registration_otp",
    }
)
_API_METHOD_PREFIXES = ("/api/method/", "/api/v1/method/", "/api/v2/method/")


def enforce_operational_access() -> None:
    """``before_request`` hook."""
    frappe.flags.saas_gate_blocked = False
    frappe.flags.saas_gate_redirect = None
    user = frappe.session.user
    if not user or user in {"Guest", "Administrator"}:
        return

    path = _request_path()
    method = _requested_method(path)
    if not _is_gated(path, method):
        return
    if is_user_gated(user):
        frappe.flags.saas_gate_blocked = True
        if method is not None or path.startswith("/api"):
            raise SubscriptionGateError(
                _("Your subscription or workspace setup is not active. Open {0} for details.").format(
                    SUBSCRIPTION_ROUTE
                )
            )
        # Raising in before_request renders a 500 for Desk pages; the response is
        # replaced with a redirect in ``redirect_blocked_response`` instead.
        frappe.flags.saas_gate_redirect = SUBSCRIPTION_ROUTE


def redirect_blocked_response(response, request) -> None:
    """``after_request`` hook."""
    location = getattr(frappe.flags, "saas_gate_redirect", None)
    if not location or response is None:
        return
    response.status_code = 302
    response.headers["Location"] = location
    response.set_data(b"")


def is_user_gated(user: str | None = None) -> bool:
    """True when ``user`` is a tenant user whose company may not operate yet."""
    user = user or frappe.session.user
    if not user or user in {"Guest", "Administrator"}:
        return False
    companies = get_user_companies(user)
    if not companies:
        return False
    return not all(has_operational_access(company) for company in companies)


def _is_gated(path: str, method: str | None) -> bool:
    if method is not None:
        return method not in EXEMPT_METHODS
    if path.startswith(EXEMPT_PATH_PREFIXES):
        return False
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in GATED_PATH_PREFIXES)


def _requested_method(path: str) -> str | None:
    for prefix in _API_METHOD_PREFIXES:
        if path.startswith(prefix):
            return unquote(path.removeprefix(prefix).split("/", 1)[0])
    form_dict = getattr(frappe.local, "form_dict", None) or {}
    cmd = form_dict.get("cmd")
    return cmd if isinstance(cmd, str) and cmd else None


def _request_path() -> str:
    request = getattr(frappe.local, "request", None)
    if not request:
        return ""
    return request.path or ""
