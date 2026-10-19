"""Google reCAPTCHA verification for public signup.

Two key types are supported, chosen in SaaS Platform Settings:

- ``v2 Checkbox``: the "I'm not a robot" widget.
- ``v3 Invisible``: no widget; Google scores the request and signups below the
  configured minimum score are refused.

Each type needs its own key pair. Restrict the site key to the signup domain in
the reCAPTCHA admin console so Google rejects tokens minted elsewhere.
"""

from __future__ import annotations

import frappe
import requests
from frappe.utils import flt

RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
RECAPTCHA_TIMEOUT_SECONDS = 10
RECAPTCHA_V2 = "v2 Checkbox"
RECAPTCHA_V3 = "v3 Invisible"
RECAPTCHA_V3_ACTION = "signup"
RECAPTCHA_V3_DEFAULT_MIN_SCORE = 0.5


def get_recaptcha_site_key() -> str | None:
    settings = frappe.get_cached_doc("SaaS Platform Settings")
    if not settings.get_password("recaptcha_secret_key", raise_exception=False):
        return None
    return (settings.recaptcha_site_key or "").strip() or None


def get_recaptcha_type() -> str:
    value = frappe.get_cached_doc("SaaS Platform Settings").get("recaptcha_type")
    return RECAPTCHA_V3 if value == RECAPTCHA_V3 else RECAPTCHA_V2


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
    if get_recaptcha_type() == RECAPTCHA_V3:
        # A v2 token carries no score or action, so a mismatched key fails closed.
        if data.get("action") != RECAPTCHA_V3_ACTION:
            return False
        min_score = flt(settings.get("recaptcha_min_score")) or RECAPTCHA_V3_DEFAULT_MIN_SCORE
        score = data.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or score < min_score:
            return False
    return True
