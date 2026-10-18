from __future__ import annotations

import hashlib
import re

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
    REGISTRATION_VERIFICATION_TTL_HOURS,
    SAAS_ACTIVE_STATUSES,
    SIGNUP_RATE_LIMIT_PER_HOUR,
    VERIFY_RATE_LIMIT_PER_HOUR,
)
from reckon_saas_platform.module_registry import get_landing_workspace, get_seed_handlers
from reckon_saas_platform.saas_security import is_vendor_user
from reckon_saas_platform.tenant_security import get_user_companies, resolve_tenant

BILLING_CYCLES = frozenset({"Monthly", "Quarterly", "Yearly"})
MAX_SIGNUP_FIELD_LENGTH = 140
# Control characters and markup never belong in a Company name or User name.
_UNSAFE_NAME_CHARACTERS = re.compile(r"[\x00-\x1f\x7f<>]")
OPERATIONAL_ACCESS_CACHE_PREFIX = "reckon_saas_operational_access"


class SubscriptionGateError(frappe.PermissionError):
    pass


class SignupValidationError(frappe.ValidationError):
    http_status_code = 400


class SignupConflictError(frappe.ValidationError):
    http_status_code = 409


class PaymentGatewayAdapter:
    def verify(self, reference: str) -> bool:
        raise NotImplementedError


def _signup_rate_limit() -> int:
    return cint(frappe.conf.get("reckon_saas_signup_rate_limit")) or SIGNUP_RATE_LIMIT_PER_HOUR


def _verify_rate_limit() -> int:
    return cint(frappe.conf.get("reckon_saas_verify_rate_limit")) or VERIFY_RATE_LIMIT_PER_HOUR


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=_signup_rate_limit, seconds=60 * 60)
def public_signup(
    business_name: str,
    owner_email: str,
    owner_name: str,
    plan: str,
    billing_cycle: str = "Monthly",
    captcha_token: str | None = None,
):
    verify_signup_captcha(captcha_token)
    registration = create_registration(
        business_name=business_name,
        owner_email=owner_email,
        owner_name=owner_name,
        plan=plan,
        billing_cycle=billing_cycle,
    )
    send_registration_verification(registration)
    return {
        "ok": True,
        "registration": registration.name,
        "message": _(
            "Signup received. Check your email and open the verification link to continue."
        ),
    }


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=_verify_rate_limit, seconds=60 * 60)
def verify_registration_email(key: str):
    confirm_registration_email(key)
    # GET requests are not committed by Frappe; the verification link is a GET.
    frappe.db.commit()
    request = getattr(frappe.local, "request", None)
    if request is not None and request.method == "GET":
        from werkzeug.utils import redirect

        return redirect("/reckonerp-signup?verified=1")
    return {
        "ok": True,
        "message": _("Email verified. Your workspace is being prepared."),
    }


def verify_signup_captcha(token: str | None) -> None:
    """Run the site's captcha verifiers.

    Apps or sites register verifiers with the ``reckon_saas_signup_captcha_verifier``
    hook; each is called as ``verifier(token=..., ip=...)`` and must return truthy.
    Setting ``reckon_saas_require_captcha`` in site config refuses signups when no
    verifier is installed, so production cannot silently run without one.
    """
    verifiers = frappe.get_hooks("reckon_saas_signup_captcha_verifier") or []
    if not verifiers:
        if cint(frappe.conf.get("reckon_saas_require_captcha")):
            frappe.throw(_("Signup is temporarily unavailable."), SignupValidationError)
        return

    ip = getattr(frappe.local, "request_ip", None)
    for verifier in verifiers:
        if not frappe.get_attr(verifier)(token=token, ip=ip):
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
        return {"company": tenant.company, "status": "Missing"}

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
        "status": subscription.status,
        "plan": subscription.plan,
        "price": subscription.price,
        "currency": subscription.currency,
        "end_date": subscription.end_date,
        "grace_until": subscription.grace_until,
        "payment": payment,
        "provisioning": job,
        "operational_access": _has_operational_access(tenant.company),
    }


@frappe.whitelist()
def get_vendor_saas_summary():
    _require_vendor()
    return {
        "plans": frappe.db.count("SaaS Plan"),
        "registrations": frappe.db.count("SaaS Registration"),
        "subscriptions": frappe.db.count("SaaS Subscription"),
        "payments_pending": frappe.db.count("SaaS Payment", {"status": "Pending Verification"}),
        "seed_jobs_pending": frappe.db.count("Tenant Provisioning Job", {"status": ["!=", "Complete"]}),
    }


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
):
    """Record a signup request without touching Company or User.

    The registration stays ``Pending Verification`` until the owner proves control
    of the email address. Only then does :func:`provision_registration` create the
    tenant, and it refuses to reuse any Company or User that already exists.
    The one-time verification token is exposed on ``registration.flags`` only.
    """
    business_name = _clean_name(business_name, _("Business Name"))
    owner_name = _clean_name(owner_name, _("Owner Name"))
    owner_email = _clean_email(owner_email)
    plan = (plan or "").strip() if isinstance(plan, str) else ""
    billing_cycle = (billing_cycle or "Monthly").strip() if isinstance(billing_cycle, str) else ""

    if billing_cycle not in BILLING_CYCLES:
        frappe.throw(_("Please select a valid billing cycle."), SignupValidationError)
    if not plan or not frappe.db.get_value("SaaS Plan", plan, "enabled"):
        frappe.throw(_("Please select a valid SaaS plan."), SignupValidationError)

    _assert_signup_identity_available(business_name, owner_email)

    token = frappe.generate_hash(length=32)
    registration = frappe.get_doc(
        {
            "doctype": "SaaS Registration",
            "business_name": business_name,
            "owner_email": owner_email,
            "owner_name": owner_name,
            "plan": plan,
            "billing_cycle": billing_cycle,
            "status": "Pending Verification",
            "email_verified": 0,
            "email_verification_hash": _hash_token(token),
            "verification_sent_on": now_datetime(),
        }
    ).insert(ignore_permissions=True)
    registration.flags.verification_token = token
    return registration


def send_registration_verification(registration) -> None:
    token = registration.flags.get("verification_token")
    if not token:
        return
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
    """Mark the registration verified and hand Company creation to a background job."""
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
            "status": "Provisioning",
            "error": "",
        }
    )
    enqueue_registration_provisioning(registration.name)
    return registration


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
    if not doc.email_verified:
        frappe.throw(_("Registration {0} is not verified.").format(doc.name), SignupValidationError)

    savepoint = "reckon_saas_provision"
    frappe.db.savepoint(savepoint)
    try:
        _assert_signup_identity_available(doc.business_name, doc.owner_email, registration=doc.name)
        plan_doc = frappe.get_doc("SaaS Plan", doc.plan)
        company = _create_tenant_company(doc.business_name)
        admin_user = _create_tenant_admin_user(doc.owner_email, doc.owner_name)
        _assign_company_admin(admin_user.name, company.name)
        subscription = _create_registration_subscription(doc, plan_doc, company.name, admin_user.name)
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
        for handler_path in get_seed_handlers():
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


def is_subscription_active(company: str) -> bool:
    subscription = get_company_subscription(company)
    if not subscription:
        return False
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
    key = _operational_access_cache_key(company)
    frappe.cache.delete_value(key)
    # A request may re-cache the old value before this transaction commits.
    after_commit = getattr(frappe.db, "after_commit", None)
    if after_commit is not None:
        after_commit.add(lambda: frappe.cache.delete_value(key))


def _operational_access_cache_key(company: str) -> str:
    return f"{OPERATIONAL_ACCESS_CACHE_PREFIX}::{company}"


def get_company_subscription(company: str):
    name = frappe.db.get_value(
        "SaaS Subscription",
        {"company": company},
        "name",
        order_by="creation desc",
    )
    return frappe.get_doc("SaaS Subscription", name) if name else None


def _assert_signup_identity_available(
    business_name: str, owner_email: str, registration: str | None = None
) -> None:
    """Refuse any signup that would attach the owner to an existing tenant or login."""
    conflict = _("This business name or email is already registered. Sign in or contact support.")
    if frappe.db.exists("Company", business_name) or frappe.db.exists(
        "Company", {"company_name": business_name}
    ):
        frappe.throw(conflict, SignupConflictError)
    if frappe.db.exists("User", owner_email) or frappe.db.exists("User", {"email": owner_email}):
        frappe.throw(conflict, SignupConflictError)

    filters = {
        "owner_email": owner_email,
        "status": ["in", ["Pending Verification", "Provisioning"]],
    }
    if registration:
        filters["name"] = ["!=", registration]
    for pending in frappe.get_all(
        "SaaS Registration", filters=filters, fields=["name", "status", "verification_sent_on"]
    ):
        if pending.status == "Pending Verification" and _verification_expired(pending):
            frappe.db.set_value(
                "SaaS Registration",
                pending.name,
                {"status": "Cancelled", "email_verification_hash": None},
            )
            continue
        frappe.throw(
            _("A signup for this email is already in progress. Check your inbox for the verification link."),
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


def _create_tenant_admin_user(email: str, full_name: str):
    roles = []
    if frappe.db.exists("Role", "Reckon Distribution Admin"):
        roles.append({"role": "Reckon Distribution Admin"})

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": full_name or email,
            "send_welcome_email": 0,
            "enabled": 1,
            "roles": roles,
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
