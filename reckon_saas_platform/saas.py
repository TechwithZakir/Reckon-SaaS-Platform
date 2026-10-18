from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from collections import Counter
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import (
    add_days,
    add_to_date,
    cint,
    get_datetime,
    get_url,
    getdate,
    now_datetime,
    nowdate,
    validate_email_address,
)

from reckon_saas_platform.constants import (
    CURRENT_SEED_VERSION,
    OPERATIONAL_ACCESS_CACHE_TTL_SECONDS,
    OTP_MAX_RESENDS,
    REGISTRATION_VERIFICATION_TTL_HOURS,
    SAAS_ACTIVE_STATUSES,
    SIGNUP_RATE_LIMIT_PER_HOUR,
    VERIFY_RATE_LIMIT_PER_HOUR,
)
from reckon_saas_platform.module_registry import (
    get_default_module,
    get_landing_workspace,
    get_module_definition,
    get_seed_handlers,
)
from reckon_saas_platform.recaptcha import is_recaptcha_configured, verify_recaptcha
from reckon_saas_platform.saas_security import is_vendor_user
from reckon_saas_platform.sms import (
    is_sms_configured,
    normalize_bd_mobile,
    send_sms,
)
from reckon_saas_platform.tenant_security import get_user_companies, resolve_tenant

BILLING_CYCLES = frozenset({"Monthly", "Quarterly", "Yearly"})
MAX_SIGNUP_FIELD_LENGTH = 140
# Control characters and markup never belong in a Company name or User name.
_UNSAFE_NAME_CHARACTERS = re.compile(r"[\x00-\x1f\x7f<>]")
OPERATIONAL_ACCESS_CACHE_PREFIX = "reckon_saas_operational_access"
SETTINGS_DOCTYPE = "SaaS Platform Settings"


class SubscriptionGateError(frappe.PermissionError):
    pass


class SignupValidationError(frappe.ValidationError):
    http_status_code = 400


class SignupConflictError(frappe.ValidationError):
    http_status_code = 409


class SignupUnavailableError(SignupValidationError):
    """Signup is switched on but a required verifier (SMS, captcha) is not configured."""

    http_status_code = 503


class InvalidOTPError(SignupValidationError):
    pass


class OTPThrottledError(frappe.ValidationError):
    http_status_code = 429


class PaymentGatewayAdapter:
    def verify(self, reference: str) -> bool:
        raise NotImplementedError


def _signup_rate_limit() -> int:
    return cint(frappe.conf.get("reckon_saas_signup_rate_limit")) or SIGNUP_RATE_LIMIT_PER_HOUR


def _verify_rate_limit() -> int:
    return cint(frappe.conf.get("reckon_saas_verify_rate_limit")) or VERIFY_RATE_LIMIT_PER_HOUR


def get_signup_settings():
    return frappe.get_cached_doc(SETTINGS_DOCTYPE)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=_signup_rate_limit, seconds=60 * 60)
def public_signup(
    business_name: str,
    owner_email: str,
    owner_name: str,
    plan: str,
    billing_cycle: str = "Monthly",
    captcha_token: str | None = None,
    owner_phone: str | None = None,
    module: str | None = None,
):
    verify_signup_captcha(captcha_token)
    registration = create_registration(
        business_name=business_name,
        owner_email=owner_email,
        owner_name=owner_name,
        plan=plan,
        billing_cycle=billing_cycle,
        owner_phone=owner_phone,
        saas_module=module,
    )
    send_registration_verification(registration)
    phone_required = bool(registration.phone_verification_required)
    return {
        "ok": True,
        "registration": registration.name,
        "phone_verification_required": phone_required,
        "message": _(
            "Signup received. Enter the code we sent by SMS, then open the verification link in your email."
        )
        if phone_required
        else _("Signup received. Check your email and open the verification link to continue."),
    }


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=_verify_rate_limit, seconds=60 * 60)
def verify_registration_email(key: str):
    registration = confirm_registration_email(key)
    # GET requests are not committed by Frappe; the verification link is a GET.
    frappe.db.commit()
    phone_pending = bool(registration.phone_verification_required and not registration.phone_verified)
    request = getattr(frappe.local, "request", None)
    if request is not None and request.method == "GET":
        from werkzeug.utils import redirect

        query = {"verified": "1", "registration": registration.name}
        if phone_pending:
            query["phone_pending"] = "1"
        if registration.get("saas_module"):
            query["module"] = registration.saas_module
        return redirect(f"/reckonerp-signup?{urlencode(query)}")
    return {
        "ok": True,
        "phone_verification_pending": phone_pending,
        "message": _("Email verified. Enter the SMS code to finish verification.")
        if phone_pending
        else _("Email verified. Your workspace is being prepared."),
    }


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=_verify_rate_limit, seconds=60 * 60)
def verify_registration_phone(registration: str, otp: str):
    try:
        doc = confirm_registration_phone(registration, otp)
    except InvalidOTPError:
        # Keep the failed-attempt count even though this request fails.
        frappe.db.commit()
        raise
    email_pending = not doc.email_verified
    return {
        "ok": True,
        "email_verification_pending": email_pending,
        "message": _("Phone verified. Open the verification link in your email to continue.")
        if email_pending
        else _("Phone verified. Your workspace is being prepared."),
    }


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=_verify_rate_limit, seconds=60 * 60)
def resend_registration_otp(registration: str):
    resend_registration_phone_otp(registration)
    return {"ok": True, "message": _("A new code has been sent by SMS.")}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=_verify_rate_limit, seconds=60 * 60)
def resend_registration_email(registration: str):
    resend_registration_verification_email(registration)
    return {"ok": True, "message": _("A new verification link has been sent to your email.")}


def _status_rate_limit() -> int:
    # The signup page polls this while the owner verifies, so allow more calls.
    return _verify_rate_limit() * 10


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=_status_rate_limit, seconds=60 * 60)
def get_registration_verification_status(registration: str):
    return registration_verification_status(registration)


REGISTRATION_STAGES = {
    "Pending Verification": "verify",
    "Provisioning": "provisioning",
    "Pending Payment": "ready",
    "Active": "ready",
    "Failed": "failed",
}


def registration_verification_status(registration: str) -> dict:
    """Progress of a signup for the public page. Only booleans, never contact details."""
    row = None
    if isinstance(registration, str) and registration:
        row = frappe.db.get_value(
            "SaaS Registration",
            registration,
            ["status", "email_verified", "phone_verification_required", "phone_verified"],
            as_dict=True,
        )
    if not row:
        frappe.throw(_("This verification request is invalid or has expired."), SignupValidationError)
    return {
        "stage": REGISTRATION_STAGES.get(row.status, "closed"),
        "email_verified": bool(row.email_verified),
        "phone_required": bool(row.phone_verification_required),
        "phone_verified": bool(row.phone_verified),
    }


def resend_registration_verification_email(registration: str):
    """Send a fresh email link. The previous link stops working."""
    invalid = _("This verification request is invalid or has expired.")
    name = None
    if isinstance(registration, str) and registration:
        name = frappe.db.get_value(
            "SaaS Registration",
            {"name": registration, "status": "Pending Verification", "email_verified": 0},
            "name",
        )
    if not name:
        frappe.throw(invalid, SignupValidationError)
    doc = frappe.get_doc("SaaS Registration", name, for_update=True)
    if _verification_expired(doc):
        doc.db_set({"status": "Cancelled", "email_verification_hash": None, "phone_otp_hash": None})
        frappe.throw(invalid, SignupValidationError)

    cooldown_key = f"reckon_saas_email_resend_cooldown::{name}"
    count_key = f"reckon_saas_email_resend_count::{name}"
    if frappe.cache.get_value(cooldown_key):
        frappe.throw(_("Please wait before requesting another email."), OTPThrottledError)
    sent = cint(frappe.cache.get_value(count_key))
    if sent >= OTP_MAX_RESENDS:
        frappe.throw(_("Too many emails requested. Please sign up again later."), OTPThrottledError)

    token = frappe.generate_hash(length=32)
    doc.db_set("email_verification_hash", _hash_token(token))
    _send_verification_email(doc, token)
    cooldown = cint(get_signup_settings().otp_resend_cooldown_seconds) or 60
    frappe.cache.set_value(cooldown_key, 1, expires_in_sec=cooldown)
    frappe.cache.set_value(
        count_key, sent + 1, expires_in_sec=REGISTRATION_VERIFICATION_TTL_HOURS * 3600
    )
    return doc


def verify_signup_captcha(token: str | None) -> None:
    """Run the signup captcha verifiers.

    Google reCAPTCHA runs when its keys are set in SaaS Platform Settings. Apps
    can add verifiers with the ``reckon_saas_signup_captcha_verifier`` hook; each
    is called as ``verifier(token=..., ip=...)`` and must return truthy. When
    captcha is required (settings or ``reckon_saas_require_captcha`` in site
    config) and no verifier is available, signups are refused.
    """
    verifiers = []
    if is_recaptcha_configured():
        verifiers.append(verify_recaptcha)
    verifiers.extend(frappe.get_attr(path) for path in frappe.get_hooks("reckon_saas_signup_captcha_verifier") or [])
    if not verifiers:
        if cint(get_signup_settings().require_captcha) or cint(frappe.conf.get("reckon_saas_require_captcha")):
            frappe.throw(_("Signup is temporarily unavailable."), SignupUnavailableError)
        return

    ip = getattr(frappe.local, "request_ip", None)
    for verifier in verifiers:
        if not verifier(token=token, ip=ip):
            frappe.throw(_("Captcha verification failed. Please try again."), SignupValidationError)


@frappe.whitelist()
def verify_payment_manual(payment: str, reference: str | None = None):
    _require_vendor()
    return verify_payment(payment, reference=reference).name


@frappe.whitelist()
def retry_tenant_seed_job(company: str):
    _require_vendor()
    return run_tenant_seed_job(company).name


@frappe.whitelist()
def retry_registration_provisioning(registration: str):
    _require_vendor()
    status = frappe.db.get_value("SaaS Registration", registration, "status")
    if status != "Failed":
        frappe.throw(_("Only failed registrations can be retried."), SignupValidationError)
    frappe.db.set_value("SaaS Registration", registration, "status", "Provisioning")
    enqueue_registration_provisioning(registration)
    return registration


@frappe.whitelist()
def get_subscription_summary():
    tenant = resolve_tenant()
    subscription = get_company_subscription(tenant.company)
    if not subscription:
        return {"company": tenant.company, "status": "Missing", "modules": []}

    payment = frappe.db.get_value(
        "SaaS Payment",
        {"subscription": subscription.name},
        ["name", "status", "amount", "currency", "gateway_reference"],
        as_dict=True,
    )
    job = frappe.db.get_value(
        "Tenant Provisioning Job",
        {"company": tenant.company, "seed_version": CURRENT_SEED_VERSION},
        ["name", "status", "current_step", "error"],
        as_dict=True,
    )
    return {
        "company": tenant.company,
        "subscription": subscription.name,
        "saas_module": subscription.saas_module,
        "status": subscription.status,
        "plan": subscription.plan,
        "price": subscription.price,
        "currency": subscription.currency,
        "end_date": subscription.end_date,
        "grace_until": subscription.grace_until,
        "payment": payment,
        "provisioning": job,
        "modules": get_company_module_subscriptions(tenant.company),
        "operational_access": _has_operational_access(tenant.company),
    }


@frappe.whitelist()
def get_vendor_saas_summary():
    _require_vendor()
    return {
        "modules": frappe.db.count("SaaS Module", {"enabled": 1}),
        "plans": frappe.db.count("SaaS Plan"),
        "registrations": frappe.db.count("SaaS Registration"),
        "registrations_failed": frappe.db.count("SaaS Registration", {"status": "Failed"}),
        "subscriptions": frappe.db.count("SaaS Subscription"),
        "subscriptions_active": frappe.db.count(
            "SaaS Subscription", {"status": ["in", sorted(SAAS_ACTIVE_STATUSES)]}
        ),
        "payments_pending": frappe.db.count("SaaS Payment", {"status": "Pending Verification"}),
        "seed_jobs_pending": frappe.db.count("Tenant Provisioning Job", {"status": ["!=", "Complete"]}),
    }


@frappe.whitelist()
def get_vendor_dashboard() -> dict:
    """Everything the vendor dashboards show: Desk page and /reckon-saas-admin."""
    _require_vendor()
    return {
        "summary": get_vendor_saas_summary(),
        "modules": frappe.get_all(
            "SaaS Module",
            fields=["name", "module_name", "enabled", "app_name", "description"],
            order_by="module_name asc",
            ignore_permissions=True,
        ),
        "module_stats": _module_stats(),
        "pending_payments": frappe.get_all(
            "SaaS Payment",
            filters={"status": "Pending Verification"},
            fields=[
                "name",
                "company",
                "amount",
                "currency",
                "gateway_provider",
                "gateway_reference",
                "subscription",
                "creation",
            ],
            ignore_permissions=True,
            order_by="creation desc",
        ),
        "seed_jobs": frappe.get_all(
            "Tenant Provisioning Job",
            fields=["name", "company", "seed_version", "status", "current_step", "error"],
            ignore_permissions=True,
            order_by="modified desc",
            limit=20,
        ),
        "registrations": frappe.get_all(
            "SaaS Registration",
            fields=[
                "name",
                "business_name",
                "owner_email",
                "owner_phone",
                "saas_module",
                "plan",
                "status",
                "email_verified",
                "phone_verification_required",
                "phone_verified",
                "error",
                "company",
                "payment",
                "provisioning_job",
                "creation",
            ],
            ignore_permissions=True,
            order_by="creation desc",
            limit=20,
        ),
        "subscriptions": frappe.get_all(
            "SaaS Subscription",
            fields=[
                "name",
                "company",
                "company_admin",
                "saas_module",
                "plan",
                "status",
                "price",
                "currency",
                "end_date",
                "grace_until",
            ],
            ignore_permissions=True,
            order_by="modified desc",
            limit=20,
        ),
    }


def _module_stats() -> list[dict]:
    """Per-module plan, registration and active-subscription counts."""
    stats = {}
    for module in frappe.get_all("SaaS Module", fields=["name", "module_name"], ignore_permissions=True):
        stats[module.name] = {
            "module": module.name,
            "module_name": module.module_name,
            "plans": 0,
            "registrations": 0,
            "active_subscriptions": 0,
        }
    queries = (
        ("plans", "SaaS Plan", {}),
        ("registrations", "SaaS Registration", {}),
        ("active_subscriptions", "SaaS Subscription", {"status": ["in", sorted(SAAS_ACTIVE_STATUSES)]}),
    )
    for key, doctype, filters in queries:
        # Count in Python: Frappe v16 rejects SQL functions written as field
        # strings ("count(name)"), and the v16 dict syntax does not exist in v15.
        modules = frappe.get_all(
            doctype, filters=filters, pluck="saas_module", ignore_permissions=True
        )
        for module, total in Counter(modules).items():
            if module in stats:
                stats[module][key] = total
    return list(stats.values())


def get_company_module_subscriptions(company: str) -> list[dict]:
    """The company's latest subscription per module, with whether it is active."""
    rows = frappe.get_all(
        "SaaS Subscription",
        filters={"company": company},
        fields=["name", "saas_module", "plan", "status", "end_date", "grace_until"],
        order_by="creation desc",
        ignore_permissions=True,
    )
    latest = {}
    for row in rows:
        latest.setdefault(row.saas_module or "", row)
    return [
        {**row, "active": _subscription_row_active(row)}
        for row in latest.values()
    ]


def get_user_home_page(user: str):
    if not user or user == "Guest":
        return "reckonerp-signup"
    if is_vendor_user(user):
        return "reckon-saas-admin"

    companies = get_user_companies(user)
    if len(companies) != 1:
        return "reckonerp-subscription"
    return get_landing_workspace() if has_operational_access(companies[0]) else "reckonerp-subscription"


def create_registration(
    *,
    business_name: str,
    owner_email: str,
    owner_name: str,
    plan: str,
    billing_cycle: str = "Monthly",
    owner_phone: str | None = None,
    saas_module: str | None = None,
):
    """Record a signup request without touching Company or User.

    The registration stays ``Pending Verification`` until the owner proves control
    of the email address and, when SaaS Platform Settings require it, of the
    mobile number (SMS one-time code). Only then does :func:`provision_registration`
    create the tenant, and it refuses to reuse any Company or User that exists.
    The email token and SMS code are exposed on ``registration.flags`` only.
    """
    business_name = _clean_name(business_name, _("Business Name"))
    owner_name = _clean_name(owner_name, _("Owner Name"))
    owner_email = _clean_email(owner_email)
    plan = (plan or "").strip() if isinstance(plan, str) else ""
    billing_cycle = (billing_cycle or "Monthly").strip() if isinstance(billing_cycle, str) else ""

    phone_required = bool(cint(get_signup_settings().require_phone_verification))
    phone = None
    if owner_phone not in (None, ""):
        phone = normalize_bd_mobile(owner_phone)
        if not phone:
            frappe.throw(_("Please enter a valid Bangladesh mobile number."), SignupValidationError)
    if phone_required:
        if not phone:
            frappe.throw(_("Owner Mobile is required."), SignupValidationError)
        if not is_sms_configured():
            frappe.throw(_("Signup is temporarily unavailable."), SignupUnavailableError)

    if billing_cycle not in BILLING_CYCLES:
        frappe.throw(_("Please select a valid billing cycle."), SignupValidationError)
    plan_row = frappe.db.get_value("SaaS Plan", plan, ["enabled", "saas_module"], as_dict=True) if plan else None
    if not plan_row or not plan_row.enabled:
        frappe.throw(_("Please select a valid SaaS plan."), SignupValidationError)
    if plan_row.saas_module and not frappe.db.get_value("SaaS Module", plan_row.saas_module, "enabled"):
        frappe.throw(_("This module is not available for signup."), SignupValidationError)
    # A module-specific signup page (?module=<key>) may only sell that module's plans.
    if saas_module and isinstance(saas_module, str) and saas_module.strip():
        if plan_row.saas_module != saas_module.strip():
            frappe.throw(_("Please select a plan for this module."), SignupValidationError)

    _assert_signup_identity_available(business_name, owner_email, owner_phone=phone)

    token = frappe.generate_hash(length=32)
    values = {
        "doctype": "SaaS Registration",
        "business_name": business_name,
        "owner_email": owner_email,
        "owner_name": owner_name,
        "owner_phone": phone,
        "plan": plan,
        "saas_module": plan_row.saas_module,
        "billing_cycle": billing_cycle,
        "status": "Pending Verification",
        "email_verified": 0,
        "email_verification_hash": _hash_token(token),
        "verification_sent_on": now_datetime(),
        "phone_verification_required": 1 if phone_required else 0,
        "phone_verified": 0,
    }
    otp = None
    if phone_required:
        otp = _new_otp()
        values.update(
            {
                "phone_otp_hash": _hash_otp(otp),
                "phone_otp_sent_on": now_datetime(),
                "phone_otp_attempts": 0,
                "phone_otp_resends": 0,
            }
        )
    registration = frappe.get_doc(values).insert(ignore_permissions=True)
    registration.flags.verification_token = token
    registration.flags.phone_otp = otp
    return registration


def send_registration_verification(registration) -> None:
    """Send the email link and, when required, the SMS code for a new registration."""
    otp = registration.flags.get("phone_otp")
    if otp:
        _send_otp_sms(registration.owner_phone, otp)

    token = registration.flags.get("verification_token")
    if token:
        _send_verification_email(registration, token)


def _send_verification_email(registration, token: str) -> None:
    link = get_url(f"/api/method/reckon_saas_platform.saas.verify_registration_email?key={token}")
    frappe.sendmail(
        recipients=[registration.owner_email],
        subject=_("Verify your Reckon ERP signup"),
        message=_(
            "Hello {0},<br><br>Open this link to verify your email and create the "
            "workspace for {1}:<br><a href=\"{2}\">{2}</a><br><br>The link expires in {3} hours."
        ).format(
            frappe.utils.escape_html(registration.owner_name or registration.owner_email),
            frappe.utils.escape_html(registration.business_name),
            link,
            REGISTRATION_VERIFICATION_TTL_HOURS,
        ),
        reference_doctype="SaaS Registration",
        reference_name=registration.name,
    )


def confirm_registration_email(key: str):
    """Mark the email verified; start provisioning once every check has passed."""
    if not key or not isinstance(key, str):
        frappe.throw(_("The verification link is invalid or has expired."), SignupValidationError)

    name = frappe.db.get_value(
        "SaaS Registration",
        {"email_verification_hash": _hash_token(key), "status": "Pending Verification"},
        "name",
    )
    if not name:
        frappe.throw(_("The verification link is invalid or has expired."), SignupValidationError)

    registration = frappe.get_doc("SaaS Registration", name, for_update=True)
    if _verification_expired(registration):
        registration.db_set({"status": "Cancelled", "email_verification_hash": None})
        frappe.throw(_("The verification link is invalid or has expired."), SignupValidationError)

    registration.db_set(
        {
            "email_verified": 1,
            "verified_on": now_datetime(),
            "email_verification_hash": None,
            "error": "",
        }
    )
    _start_provisioning_if_verified(registration)
    return registration


def confirm_registration_phone(registration: str, otp: str):
    """Check the SMS code. A wrong code counts against the attempt limit."""
    doc = _get_pending_phone_registration(registration)
    settings = get_signup_settings()
    max_attempts = cint(settings.otp_max_attempts) or 5
    if cint(doc.phone_otp_attempts) >= max_attempts:
        frappe.throw(_("Too many incorrect codes. Request a new code."), OTPThrottledError)
    validity = cint(settings.otp_validity_minutes) or 10
    sent_on = doc.phone_otp_sent_on and get_datetime(doc.phone_otp_sent_on)
    if not sent_on or add_to_date(sent_on, minutes=validity) < now_datetime():
        frappe.throw(_("The code has expired. Request a new code."), SignupValidationError)

    if not isinstance(otp, str) or not _otp_matches(otp.strip(), doc.phone_otp_hash):
        doc.db_set("phone_otp_attempts", cint(doc.phone_otp_attempts) + 1)
        frappe.throw(_("The code is not correct."), InvalidOTPError)

    doc.db_set(
        {
            "phone_verified": 1,
            "phone_verified_on": now_datetime(),
            "phone_otp_hash": None,
            "phone_otp_attempts": 0,
        }
    )
    _start_provisioning_if_verified(doc)
    return doc


def resend_registration_phone_otp(registration: str):
    doc = _get_pending_phone_registration(registration)
    settings = get_signup_settings()
    cooldown = cint(settings.otp_resend_cooldown_seconds)
    sent_on = doc.phone_otp_sent_on and get_datetime(doc.phone_otp_sent_on)
    if sent_on and add_to_date(sent_on, seconds=cooldown) > now_datetime():
        frappe.throw(_("Please wait before requesting another code."), OTPThrottledError)
    if cint(doc.phone_otp_resends) >= OTP_MAX_RESENDS:
        frappe.throw(_("Too many codes requested. Please sign up again later."), OTPThrottledError)

    otp = _new_otp()
    doc.db_set(
        {
            "phone_otp_hash": _hash_otp(otp),
            "phone_otp_sent_on": now_datetime(),
            "phone_otp_attempts": 0,
            "phone_otp_resends": cint(doc.phone_otp_resends) + 1,
        }
    )
    _send_otp_sms(doc.owner_phone, otp)
    return doc


def _get_pending_phone_registration(registration: str):
    invalid = _("This verification request is invalid or has expired.")
    if not registration or not isinstance(registration, str):
        frappe.throw(invalid, SignupValidationError)
    name = frappe.db.get_value(
        "SaaS Registration",
        {
            "name": registration,
            "status": "Pending Verification",
            "phone_verification_required": 1,
            "phone_verified": 0,
        },
        "name",
    )
    if not name:
        frappe.throw(invalid, SignupValidationError)
    doc = frappe.get_doc("SaaS Registration", name, for_update=True)
    if _verification_expired(doc):
        doc.db_set({"status": "Cancelled", "email_verification_hash": None, "phone_otp_hash": None})
        frappe.throw(invalid, SignupValidationError)
    return doc


def _start_provisioning_if_verified(registration) -> None:
    if not registration.email_verified:
        return
    if registration.phone_verification_required and not registration.phone_verified:
        return
    registration.db_set("status", "Provisioning")
    enqueue_registration_provisioning(registration.name)


def _send_otp_sms(phone: str, otp: str) -> None:
    validity = cint(get_signup_settings().otp_validity_minutes) or 10
    send_sms(
        phone,
        _("Your Reckon ERP verification code is {0}. It expires in {1} minutes.").format(otp, validity),
    )


def _new_otp() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def _hash_otp(otp: str) -> str:
    salt = secrets.token_hex(8)
    return f"{salt}${hashlib.sha256(f'{salt}:{otp}'.encode()).hexdigest()}"


def _otp_matches(otp: str, stored: str | None) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, digest = stored.split("$", 1)
    candidate = hashlib.sha256(f"{salt}:{otp}".encode()).hexdigest()
    return hmac.compare_digest(candidate, digest)


def enqueue_registration_provisioning(registration: str) -> None:
    frappe.enqueue(
        "reckon_saas_platform.saas.provision_registration",
        queue="long",
        timeout=1800,
        job_id=f"reckon-saas-provision::{registration}",
        deduplicate=True,
        enqueue_after_commit=True,
        registration=registration,
    )


def provision_registration(registration: str):
    """Background job: create the tenant for a verified registration.

    Everything runs inside one savepoint, so a failure leaves no Company, User,
    assignment or billing record behind and the job can simply run again.
    """
    previous_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        return _provision_registration(registration)
    finally:
        frappe.set_user(previous_user)


def _provision_registration(registration: str):
    doc = frappe.get_doc("SaaS Registration", registration, for_update=True)
    if doc.status not in {"Provisioning", "Failed"}:
        return doc
    if not doc.email_verified or (doc.phone_verification_required and not doc.phone_verified):
        frappe.throw(_("Registration {0} is not verified.").format(doc.name), SignupValidationError)

    savepoint = "reckon_saas_provision"
    frappe.db.savepoint(savepoint)
    try:
        _assert_signup_identity_available(
            doc.business_name, doc.owner_email, registration=doc.name, owner_phone=doc.owner_phone
        )
        plan_doc = frappe.get_doc("SaaS Plan", doc.plan)
        company = _create_tenant_company(doc.business_name)
        admin_user = _create_tenant_admin_user(
            doc.owner_email, doc.owner_name, doc.owner_phone, doc.get("saas_module")
        )
        # Subscription before the owner's assignment: module apps decide on
        # assignment save which module the company belongs to.
        subscription = _create_registration_subscription(doc, plan_doc, company.name, admin_user.name)
        _assign_company_admin(admin_user.name, company.name)
        payment = frappe.get_doc(
            {
                "doctype": "SaaS Payment",
                "subscription": subscription.name,
                "company": company.name,
                "amount": plan_doc.price,
                "currency": plan_doc.currency,
                "status": "Pending Verification",
            }
        ).insert(ignore_permissions=True)
        job = ensure_tenant_seed_job(company.name)
    except Exception as exc:
        _rollback_to(savepoint)
        _mark_registration_failed(doc, exc)
        return doc

    doc.db_set(
        {
            "company": company.name,
            "company_admin": admin_user.name,
            "subscription": subscription.name,
            "payment": payment.name,
            "provisioning_job": job.name,
            "status": "Pending Payment",
            "error": "",
        }
    )
    run_tenant_seed_job(company.name)
    return doc


def _create_registration_subscription(doc, plan_doc, company: str, admin_user: str):
    return frappe.get_doc(
        {
            "doctype": "SaaS Subscription",
            "registration": doc.name,
            "company": company,
            "company_admin": admin_user,
            "plan": plan_doc.name,
            "saas_module": plan_doc.saas_module or doc.get("saas_module"),
            "plan_version": plan_doc.plan_version,
            "billing_cycle": doc.billing_cycle,
            "status": "Pending",
            "price": plan_doc.price,
            "currency": plan_doc.currency,
            "start_date": nowdate(),
        }
    ).insert(ignore_permissions=True)


def _mark_registration_failed(doc, exc: Exception) -> None:
    error = _short_error(exc)
    doc.db_set({"status": "Failed", "error": error})
    frappe.log_error(title=f"SaaS registration {doc.name} provisioning failed", message=frappe.get_traceback())


def ensure_tenant_seed_job(company: str, seed_version: str = CURRENT_SEED_VERSION):
    existing = frappe.db.exists(
        "Tenant Provisioning Job",
        {"company": company, "seed_version": seed_version},
    )
    if existing:
        return frappe.get_doc("Tenant Provisioning Job", existing)

    try:
        return frappe.get_doc(
            {
                "doctype": "Tenant Provisioning Job",
                "company": company,
                "seed_version": seed_version,
                "status": "Pending",
                "idempotency_key": f"{company}:{seed_version}",
            }
        ).insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        # Another worker created the job between the exists check and insert.
        existing = frappe.db.exists(
            "Tenant Provisioning Job",
            {"company": company, "seed_version": seed_version},
        )
        return frappe.get_doc("Tenant Provisioning Job", existing)


def run_tenant_seed_job(company: str, seed_version: str = CURRENT_SEED_VERSION):
    """Run the module seed handlers for one company, safely re-runnable.

    The job row is locked so two workers cannot seed the same company at once.
    Handler writes run inside a savepoint: on failure they are rolled back, the job
    is marked ``Failed`` with the error, and the job is returned rather than raised
    so the background worker commits that status. Handlers are get-or-create, so a
    retry after a failure (or after a partial run that committed) is safe.
    """
    job = ensure_tenant_seed_job(company, seed_version)
    status = frappe.db.get_value("Tenant Provisioning Job", job.name, "status", for_update=True)
    if status == "Complete":
        job.reload()
        return job

    job.db_set({"status": "Running", "current_step": "generic-defaults", "error": ""})

    savepoint = "reckon_saas_tenant_seed"
    frappe.db.savepoint(savepoint)
    try:
        # Seed only generic non-sensitive placeholders. Do not copy Items, Customers,
        # Suppliers, prices, balances, contacts, or stock.
        for handler_path in get_seed_handlers(_company_module_keys(company)):
            job.db_set("current_step", handler_path)
            frappe.get_attr(handler_path)(company=company, seed_version=seed_version)
    except Exception as exc:
        _rollback_to(savepoint)
        job.db_set({"status": "Failed", "error": _short_error(exc)})
        frappe.log_error(
            title=f"Tenant seed job {job.name} failed for {company}",
            message=frappe.get_traceback(),
        )
        invalidate_operational_access_cache(company)
        return job

    job.db_set(
        {
            "status": "Complete",
            "current_step": "verified",
            "completed_on": nowdate(),
            "error": "",
        }
    )
    invalidate_operational_access_cache(company)
    return job


def _company_module_keys(company: str) -> set[str] | None:
    """Modules the company subscribes to; ``None`` (all modules) for legacy rows."""
    keys = set(
        frappe.get_all(
            "SaaS Subscription",
            filters={"company": company, "saas_module": ["is", "set"]},
            pluck="saas_module",
            ignore_permissions=True,
        )
    )
    return keys or None


def verify_payment(payment: str, reference: str | None = None):
    payment_doc = frappe.get_doc("SaaS Payment", payment)
    payment_doc.status = "Verified"
    if reference:
        payment_doc.gateway_reference = reference
    payment_doc.verified_on = nowdate()
    payment_doc.save(ignore_permissions=True)

    subscription = frappe.get_doc("SaaS Subscription", payment_doc.subscription)
    subscription.status = "Active"
    subscription.start_date = subscription.start_date or nowdate()
    subscription.end_date = subscription.end_date or add_days(nowdate(), 30)
    subscription.save(ignore_permissions=True)
    return subscription


def is_subscription_active(company: str, saas_module: str | None = None) -> bool:
    """True when the company has an active subscription.

    With ``saas_module`` only that module's latest subscription counts. Without
    it, any module's latest subscription being active is enough, so a tenant who
    buys several modules keeps Desk access while one of them is still live.
    """
    if saas_module:
        subscription = get_company_subscription(company, saas_module=saas_module)
        return bool(subscription) and _subscription_row_active(subscription)
    return any(row["active"] for row in get_company_module_subscriptions(company))


def _subscription_row_active(subscription) -> bool:
    if subscription.status not in SAAS_ACTIVE_STATUSES:
        return False
    if subscription.status == "Grace" and subscription.grace_until:
        return getdate(subscription.grace_until) >= getdate(nowdate())
    if subscription.end_date and getdate(subscription.end_date) < getdate(nowdate()):
        return False
    return True


def assert_operational_access(company: str) -> None:
    seed_complete = frappe.db.exists(
        "Tenant Provisioning Job",
        {"company": company, "seed_version": CURRENT_SEED_VERSION, "status": "Complete"},
    )
    if not seed_complete:
        raise SubscriptionGateError(_("Tenant seed provisioning is not complete."))
    if not is_subscription_active(company):
        raise SubscriptionGateError(_("Subscription is not active."))


def _has_operational_access(company: str) -> bool:
    try:
        assert_operational_access(company)
    except SubscriptionGateError:
        return False
    return True


def has_operational_access(company: str) -> bool:
    """Cached form of :func:`assert_operational_access` for the request gate.

    The value is cached per company for a few minutes (dates move on by
    themselves) and dropped whenever a SaaS Subscription or Tenant Provisioning
    Job for the company changes.
    """
    if not company:
        return False
    key = _operational_access_cache_key(company)
    cached = frappe.cache.get_value(key)
    if cached is not None:
        return bool(cint(cached))
    allowed = _has_operational_access(company)
    frappe.cache.set_value(
        key, 1 if allowed else 0, expires_in_sec=OPERATIONAL_ACCESS_CACHE_TTL_SECONDS
    )
    return allowed


def invalidate_operational_access_cache(company: str | None) -> None:
    if not company:
        return
    keys = (_operational_access_cache_key(company), _company_modules_cache_key(company))
    for key in keys:
        frappe.cache.delete_value(key)
    # A request may re-cache the old value before this transaction commits.
    after_commit = getattr(frappe.db, "after_commit", None)
    if after_commit is not None:
        after_commit.add(lambda: [frappe.cache.delete_value(key) for key in keys])


def get_company_module_keys(company: str | None) -> list[str]:
    """Modules the company has a subscription for (any status), cached per company.

    Module apps use this to decide whether a tenant user belongs to them, so two
    modules can share one site without their Desk guards fighting.
    """
    if not company:
        return []
    key = _company_modules_cache_key(company)
    cached = frappe.cache.get_value(key)
    if cached is not None:
        return list(cached)
    modules = sorted(
        set(
            frappe.get_all(
                "SaaS Subscription",
                filters={"company": company, "saas_module": ["is", "set"]},
                pluck="saas_module",
                ignore_permissions=True,
            )
        )
    )
    frappe.cache.set_value(key, modules, expires_in_sec=OPERATIONAL_ACCESS_CACHE_TTL_SECONDS)
    return modules


def get_user_module_keys(user: str | None = None) -> list[str]:
    """Union of the modules subscribed by the user's active tenant companies."""
    modules: set[str] = set()
    for company in get_user_companies(user or frappe.session.user):
        modules.update(get_company_module_keys(company))
    return sorted(modules)


def get_module_admin_role(saas_module: str | None) -> str | None:
    module = get_module_definition(saas_module) if saas_module else None
    if module and module.get("admin_role"):
        return module["admin_role"]
    default = get_default_module()
    return (default or {}).get("admin_role") or "Reckon Distribution Admin"


def _company_modules_cache_key(company: str) -> str:
    return f"reckon_saas_company_modules::{company}"


def _operational_access_cache_key(company: str) -> str:
    return f"{OPERATIONAL_ACCESS_CACHE_PREFIX}::{company}"


def get_company_subscription(company: str, saas_module: str | None = None):
    filters = {"company": company}
    if saas_module:
        filters["saas_module"] = saas_module
    name = frappe.db.get_value(
        "SaaS Subscription",
        filters,
        "name",
        order_by="creation desc",
    )
    return frappe.get_doc("SaaS Subscription", name) if name else None


def _assert_signup_identity_available(
    business_name: str,
    owner_email: str,
    registration: str | None = None,
    owner_phone: str | None = None,
) -> None:
    """Refuse any signup that would attach the owner to an existing tenant or login."""
    conflict = _("This business name, email or mobile is already registered. Sign in or contact support.")
    if owner_phone and (
        frappe.db.exists("User", {"mobile_no": owner_phone})
        or frappe.db.exists("User", {"mobile_no": f"0{owner_phone[3:]}"})
    ):
        frappe.throw(conflict, SignupConflictError)
    if frappe.db.exists("Company", business_name) or frappe.db.exists(
        "Company", {"company_name": business_name}
    ):
        frappe.throw(conflict, SignupConflictError)
    if frappe.db.exists("User", owner_email) or frappe.db.exists("User", {"email": owner_email}):
        frappe.throw(conflict, SignupConflictError)

    filters = {"status": ["in", ["Pending Verification", "Provisioning"]]}
    if registration:
        filters["name"] = ["!=", registration]
    or_filters = {"owner_email": owner_email}
    if owner_phone:
        or_filters["owner_phone"] = owner_phone
    for pending in frappe.get_all(
        "SaaS Registration",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "status", "verification_sent_on"],
    ):
        if pending.status == "Pending Verification" and _verification_expired(pending):
            frappe.db.set_value(
                "SaaS Registration",
                pending.name,
                {"status": "Cancelled", "email_verification_hash": None},
            )
            continue
        frappe.throw(
            _("A signup for this email or mobile is already in progress. Finish its verification first."),
            SignupConflictError,
        )


def _verification_expired(registration) -> bool:
    sent_on = registration.get("verification_sent_on")
    if not sent_on:
        return True
    expires_on = add_to_date(get_datetime(sent_on), hours=REGISTRATION_VERIFICATION_TTL_HOURS)
    return expires_on < now_datetime()


def _clean_name(value, label: str) -> str:
    value = value.strip() if isinstance(value, str) else ""
    if not value:
        frappe.throw(_("{0} is required.").format(label), SignupValidationError)
    if len(value) > MAX_SIGNUP_FIELD_LENGTH or _UNSAFE_NAME_CHARACTERS.search(value):
        frappe.throw(_("{0} is not valid.").format(label), SignupValidationError)
    return value


def _clean_email(value) -> str:
    value = value.strip().lower() if isinstance(value, str) else ""
    if not value:
        frappe.throw(_("Owner Email is required."), SignupValidationError)
    if len(value) > MAX_SIGNUP_FIELD_LENGTH or not validate_email_address(value, throw=False):
        frappe.throw(_("Please enter a valid Owner Email."), SignupValidationError)
    return value


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _short_error(exc: Exception) -> str:
    message = frappe.utils.strip_html(str(exc)) if str(exc) else ""
    return f"{type(exc).__name__}: {message}"[:1000]


def _rollback_to(savepoint: str) -> None:
    try:
        frappe.db.rollback(save_point=savepoint)
    except Exception:
        # An implicit commit (e.g. DDL) can drop the savepoint; fall back to a full
        # rollback so no half-written tenant survives.
        frappe.db.rollback()


def _create_tenant_company(company_name: str):
    return frappe.get_doc(
        {
            "doctype": "Company",
            "company_name": company_name,
            "abbr": _unique_abbr(company_name),
            "default_currency": "BDT",
            "country": "Bangladesh",
        }
    ).insert(ignore_permissions=True)


def _create_tenant_admin_user(
    email: str, full_name: str, mobile_no: str | None = None, saas_module: str | None = None
):
    """The owner's login. Its first role is the module's ``admin_role``; the
    module app adds the rest when the Tenant User Assignment is saved."""
    roles = []
    admin_role = get_module_admin_role(saas_module)
    if admin_role and frappe.db.exists("Role", admin_role):
        roles.append({"role": admin_role})

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": full_name or email,
            # The owner verified this address; the welcome email carries the
            # link to set a password and sign in.
            "send_welcome_email": 1,
            "enabled": 1,
            "roles": roles,
            "mobile_no": mobile_no,
        }
    )
    return user.insert(ignore_permissions=True)


def _assign_company_admin(user: str, company: str):
    existing = frappe.db.exists(
        "Tenant User Assignment",
        {"user": user, "company": company, "active": 1},
    )
    if existing:
        return frappe.get_doc("Tenant User Assignment", existing)
    return frappe.get_doc(
        {
            "doctype": "Tenant User Assignment",
            "user": user,
            "company": company,
            "role_profile": "Company Admin",
            "active": 1,
            "is_default": 1,
        }
    ).insert(ignore_permissions=True)


def _abbr(company_name: str) -> str:
    letters = "".join(part[:1] for part in company_name.split() if part).upper()[:5]
    return letters or "RDS"


def _unique_abbr(company_name: str) -> str:
    base = _abbr(company_name)
    if not frappe.db.exists("Company", {"abbr": base}):
        return base

    for index in range(2, 100):
        suffix = str(index)
        candidate = f"{base[: 5 - len(suffix)]}{suffix}"
        if not frappe.db.exists("Company", {"abbr": candidate}):
            return candidate

    frappe.throw(_("Could not generate a unique company abbreviation."))


def _require_vendor() -> None:
    if not is_vendor_user():
        frappe.throw(_("Only vendor administrators can perform this action."), frappe.PermissionError)
