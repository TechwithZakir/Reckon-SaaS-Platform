"""BulkSMSBD SMS gateway used for signup phone verification.

API reference: https://bulksmsbd.com/bulksms-api-bangladesh.php
``POST https://bulksmsbd.net/api/smsapi`` with ``api_key``, ``senderid``,
``number`` (``8801XXXXXXXXX``) and ``message``; ``response_code`` 202 means the
SMS was accepted. Credentials live in SaaS Platform Settings.
"""

from __future__ import annotations

import re

import frappe
import requests
from frappe import _

BULKSMSBD_SEND_URL = "https://bulksmsbd.net/api/smsapi"
BULKSMSBD_SUCCESS_CODE = 202
BULKSMSBD_TIMEOUT_SECONDS = 15
BULKSMSBD_ERRORS = {
    1002: "Sender ID is not correct or is disabled",
    1003: "Required fields are missing",
    1005: "Internal error",
    1006: "Balance validity not available",
    1007: "Insufficient balance",
    1011: "User ID not found",
    1012: "Masking SMS must be sent in Bengali",
    1013: "Sender ID has no gateway for this API key",
    1014: "Sender type name not found for this sender",
    1015: "Sender ID has no valid gateway for this API key",
    1016: "Active price info not found for this sender",
    1017: "Price info not found for this sender",
    1018: "Account owner is disabled",
    1019: "Sender type price is disabled for this account",
    1020: "Parent account not found",
    1021: "Parent account active price not found",
}

# Bangladesh mobile numbers: 01[3-9] followed by 8 digits, sent as 8801XXXXXXXXX.
_BD_MOBILE = re.compile(r"^8801[3-9]\d{8}$")


class SMSNotConfiguredError(frappe.ValidationError):
    http_status_code = 503


class SMSDeliveryError(frappe.ValidationError):
    http_status_code = 502


def normalize_bd_mobile(value) -> str | None:
    """Return ``8801XXXXXXXXX`` for a Bangladesh mobile number, else ``None``."""
    if not isinstance(value, str):
        return None
    digits = re.sub(r"[\s\-().]", "", value.strip())
    if digits.startswith("+"):
        digits = digits[1:]
    if digits.startswith("00"):
        digits = digits[2:]
    if not digits.isdigit():
        return None
    if len(digits) == 11 and digits.startswith("01"):
        digits = f"88{digits}"
    elif len(digits) == 10 and digits.startswith("1"):
        digits = f"880{digits}"
    return digits if _BD_MOBILE.match(digits) else None


def get_bulksmsbd_credentials() -> tuple[str, str] | None:
    settings = frappe.get_cached_doc("SaaS Platform Settings")
    api_key = settings.get_password("bulksmsbd_api_key", raise_exception=False)
    sender_id = (settings.bulksmsbd_sender_id or "").strip()
    if not api_key or not sender_id:
        return None
    return api_key, sender_id


def is_sms_configured() -> bool:
    return get_bulksmsbd_credentials() is not None


def send_sms(number: str, message: str) -> str | None:
    """Send one SMS through BulkSMSBD and return the gateway message id, if any."""
    credentials = get_bulksmsbd_credentials()
    if not credentials:
        frappe.throw(_("SMS verification is not configured."), SMSNotConfiguredError)
    api_key, sender_id = credentials

    try:
        response = requests.post(
            BULKSMSBD_SEND_URL,
            data={
                "api_key": api_key,
                "senderid": sender_id,
                "number": number,
                "message": message,
            },
            timeout=BULKSMSBD_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        _log_failure(number, f"Request failed: {type(exc).__name__}")
        frappe.throw(_("Could not send the verification SMS. Please try again."), SMSDeliveryError)

    code, message_id = _parse_response(response)
    if code != BULKSMSBD_SUCCESS_CODE:
        _log_failure(number, f"HTTP {response.status_code}, code {code}: {BULKSMSBD_ERRORS.get(code, 'Unknown')}")
        frappe.throw(_("Could not send the verification SMS. Please try again."), SMSDeliveryError)
    return message_id


def _parse_response(response) -> tuple[int | None, str | None]:
    try:
        data = response.json()
    except ValueError:
        data = None
    if isinstance(data, dict):
        try:
            code = int(data.get("response_code"))
        except (TypeError, ValueError):
            code = None
        return code, data.get("message_id")
    text = (getattr(response, "text", "") or "").strip()
    return (int(text) if text.isdigit() else None), None


def _log_failure(number: str, detail: str) -> None:
    masked = f"{number[:5]}****{number[-2:]}" if number else ""
    frappe.log_error(title="BulkSMSBD SMS failed", message=f"To {masked}: {detail}")
