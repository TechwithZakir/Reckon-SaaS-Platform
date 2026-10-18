"""Google reCAPTCHA v2 ("I'm not a robot") verification for public signup.

Keys live in SaaS Platform Settings. Restrict the site key to the signup domain
in the reCAPTCHA admin console so Google rejects tokens minted elsewhere.
"""

from __future__ import annotations

import frappe
import requests

RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
RECAPTCHA_TIMEOUT_SECONDS = 10


def get_recaptcha_site_key() -> str | None:
    settings = frappe.get_cached_doc("SaaS Platform Settings")
    if not settings.get_password("recaptcha_secret_key", raise_exception=False):
        return None
    return (settings.recaptcha_site_key or "").strip() or None


def is_recaptcha_configured() -> bool:
    return bool(get_recaptcha_site_key())


def verify_recaptcha(token: str | None = None, ip: str | None = None) -> bool:
    """Return True only when Google confirms the token. Fails closed on errors."""
    if not token or not isinstance(token, str):
        return False
    settings = frappe.get_cached_doc("SaaS Platform Settings")
    secret = settings.get_password("recaptcha_secret_key", raise_exception=False)
    if not secret:
        return False

    payload = {"secret": secret, "response": token}
    if ip:
        payload["remoteip"] = ip
    try:
        response = requests.post(
            RECAPTCHA_VERIFY_URL, data=payload, timeout=RECAPTCHA_TIMEOUT_SECONDS
        )
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        frappe.log_error(title="reCAPTCHA verification failed", message=type(exc).__name__)
        return False

    if not isinstance(data, dict) or data.get("success") is not True:
        return False
    return True
