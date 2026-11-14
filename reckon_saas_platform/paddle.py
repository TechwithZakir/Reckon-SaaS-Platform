"""Card payments and auto-renewal through Paddle Billing.

Paddle is offered only for plans priced in a currency Paddle supports (USD and
others; never BDT). Those plans keep the manual bKash / bank flow as well.

* ``sync_plan`` (vendor) creates the module's Paddle product and the plan's price.
* ``create_checkout`` (tenant admin) hands Paddle.js what it needs to open checkout.
* ``webhook`` (Paddle) verifies the signature, stores the event once and queues it.
* ``process_event`` applies it: a completed transaction is a verified SaaS Payment
  whose period ends where Paddle's billing period ends; subscription events keep
  the Paddle id, status and scheduled change on the SaaS Subscription.

The Paddle SDK (``paddle-python-sdk``) is imported only where it is used, so the
rest of the app keeps working on a bench where it is not installed yet.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, now_datetime

from reckon_saas_platform.constants import HARD_BLOCKED_STATUSES

EVENT_DOCTYPE = "Paddle Webhook Event"
PROVIDER = "Paddle"
SIGNATURE_HEADER = "Paddle-Signature"
# Currencies Paddle Billing charges in (paddle_billing.Entities.Shared.CurrencyCode).
SUPPORTED_CURRENCIES = frozenset(
    "USD EUR GBP JPY AUD CAD CHF HKD SGD SEK ARS BRL CLP CNY COP CZK DKK HUF ILS INR "
    "KRW MXN NOK NZD PEN PLN RUB THB TRY TWD UAH VND ZAR".split()
)
# Paddle amounts are in the lowest unit, except these, which have no minor unit in Paddle.
ZERO_DECIMAL_CURRENCIES = frozenset({"JPY", "KRW", "CLP"})
CYCLE_TO_PADDLE = {"Monthly": ("month", 1), "Quarterly": ("month", 3), "Yearly": ("year", 1)}
# Paddle subscription statuses that mean the card is still being charged.
LIVE_PADDLE_STATUSES = frozenset({"active", "trialing", "past_due"})
HANDLED_EVENTS = frozenset(
    {
        "transaction.completed",
        "subscription.created",
        "subscription.updated",
        "subscription.activated",
        "subscription.past_due",
        "subscription.paused",
        "subscription.resumed",
        "subscription.canceled",
    }
)


class PaddleNotConfigured(frappe.ValidationError):
    pass


class PaddleEventError(Exception):
    """An event that is genuine but cannot be applied; the vendor reviews it."""


# Settings


def _settings():
    from reckon_saas_platform.saas import get_signup_settings

    return get_signup_settings()


def _password(settings, fieldname: str) -> str:
    try:
        return settings.get_password(fieldname, raise_exception=False) or ""
    except Exception:
        return ""


def environment() -> str:
    """``sandbox`` or ``production``; anything unset counts as sandbox."""
    value = (_settings().get("paddle_environment") or "Sandbox").strip().lower()
    return "production" if value == "production" else "sandbox"


def is_enabled() -> bool:
    settings = _settings()
    return bool(cint(settings.get("paddle_enabled"))) and bool(_password(settings, "paddle_api_key"))


def supports_currency(currency: str | None) -> bool:
    return (currency or "").upper() in SUPPORTED_CURRENCIES


def to_lowest_unit(amount, currency: str) -> str:
    """A plan price as Paddle's amount string: ``25`` USD is ``"2500"``, ``1200`` JPY is ``"1200"``."""
    value = Decimal(str(amount or 0))
    if currency.upper() not in ZERO_DECIMAL_CURRENCIES:
        value *= 100
    value = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if value <= 0:
        frappe.throw(_("The plan price must be more than zero to sell it through Paddle."))
    return str(int(value))


def from_lowest_unit(amount, currency: str) -> float:
    value = Decimal(str(amount or 0))
    if (currency or "").upper() not in ZERO_DECIMAL_CURRENCIES:
        value /= 100
    return float(value)


def plan_price_id(plan) -> str | None:
    """The plan's Paddle price, but only when it belongs to the configured environment."""
    if not plan or not plan.get("paddle_price_id"):
        return None
    if (plan.get("paddle_environment") or "") != environment():
        return None
    return plan.get("paddle_price_id")


def card_payment_available(plan) -> bool:
    return is_enabled() and supports_currency(plan.get("currency")) and bool(plan_price_id(plan))


# Paddle API (the only place the SDK is used for API calls)


def _client():
    settings = _settings()
    if not cint(settings.get("paddle_enabled")):
        frappe.throw(_("Paddle is switched off in SaaS Platform Settings."), PaddleNotConfigured)
    api_key = _password(settings, "paddle_api_key")
    if not api_key:
        frappe.throw(_("Add the Paddle API key in SaaS Platform Settings."), PaddleNotConfigured)
    from paddle_billing import Client, Environment, Options

    return Client(api_key, options=Options(Environment(environment())))


def _api_create_product(name: str, description: str | None, saas_module: str) -> str:
    from paddle_billing.Entities.Shared import CustomData, TaxCategory
    from paddle_billing.Resources.Products.Operations import CreateProduct

    product = _client().products.create(
        CreateProduct(
            name=name,
            tax_category=TaxCategory("saas"),
            description=description or None,
            custom_data=CustomData({"saas_module": saas_module}),
        )
    )
    return product.id


def _api_create_price(
    product_id: str, name: str, description: str, amount: str, currency: str, cycle: str, plan: str
) -> str:
    from paddle_billing.Entities.Shared import CurrencyCode, CustomData, Duration, Interval, Money
    from paddle_billing.Resources.Prices.Operations import CreatePrice

    interval, frequency = CYCLE_TO_PADDLE[cycle]
    price = _client().prices.create(
        CreatePrice(
            description=description,
            name=name,
            product_id=product_id,
            unit_price=Money(amount, CurrencyCode(currency)),
            billing_cycle=Duration(Interval(interval), frequency),
            custom_data=CustomData({"saas_plan": plan}),
        )
    )
    return price.id


def _api_archive_price(price_id: str) -> None:
    from paddle_billing.Entities.Shared import Status
    from paddle_billing.Resources.Prices.Operations import UpdatePrice

    _client().prices.update(price_id, UpdatePrice(status=Status.Archived))


def _api_portal_urls(customer_id: str, subscription_id: str | None) -> dict:
    from paddle_billing.Resources.CustomerPortalSessions.Operations import (
        CreateCustomerPortalSession,
    )

    session = _client().customer_portal_sessions.create(
        customer_id,
        CreateCustomerPortalSession(subscription_ids=[subscription_id] if subscription_id else []),
    )
    urls = {"overview": session.urls.general.overview}
    for row in session.urls.subscriptions or []:
        if row.id == subscription_id:
            urls["cancel"] = row.cancel_subscription
            urls["update_payment_method"] = row.update_subscription_payment_method
    return urls


# Catalog


def price_signature(plan) -> str:
    """What the Paddle price was made from; a change means a new price is needed."""
    return ":".join(
        [
            environment(),
            (plan.get("currency") or "").upper(),
            to_lowest_unit(plan.get("price"), plan.get("currency") or ""),
            plan.get("billing_cycle") or "Monthly",
        ]
    )


@frappe.whitelist(methods=["POST"])
def sync_plan(plan: str) -> dict:
    """Create (or replace) the Paddle product and price for one SaaS Plan. Vendor only.

    Paddle prices cannot change amount after a sale, so a changed price, currency
    or billing cycle archives the old Paddle price and creates a new one. Card
    subscriptions already running keep their old price.
    """
    from reckon_saas_platform.saas import _require_vendor

    _require_vendor()
    doc = frappe.get_doc("SaaS Plan", plan)
    currency = (doc.get("currency") or "").upper()
    if not supports_currency(currency):
        frappe.throw(
            _("Paddle cannot charge in {0}. Card payment is for plans priced in USD or another Paddle currency.").format(
                currency or "-"
            )
        )
    cycle = doc.get("billing_cycle") or "Monthly"
    if cycle not in CYCLE_TO_PADDLE:
        frappe.throw(_("Unsupported billing cycle: {0}").format(cycle))
    if not doc.get("saas_module"):
        frappe.throw(_("Set the plan's Module before syncing it to Paddle."))

    env = environment()
    signature = price_signature(doc)
    if doc.get("paddle_price_id") and doc.get("paddle_environment") == env and doc.get("paddle_price_signature") == signature:
        return {"price_id": doc.paddle_price_id, "product_id": _module_product(doc.saas_module, env), "created": False}

    product_id = _module_product(doc.saas_module, env)
    old_price = doc.get("paddle_price_id") if doc.get("paddle_environment") == env else None
    price_id = _api_create_price(
        product_id,
        name=doc.get("plan_name") or doc.name,
        description=f"{doc.get('plan_name') or doc.name} ({cycle}, {currency})",
        amount=to_lowest_unit(doc.get("price"), currency),
        currency=currency,
        cycle=cycle,
        plan=doc.name,
    )
    frappe.db.set_value(
        "SaaS Plan",
        doc.name,
        {"paddle_price_id": price_id, "paddle_environment": env, "paddle_price_signature": signature},
    )
    if old_price and old_price != price_id:
        try:
            _api_archive_price(old_price)
        except Exception:
            # The new price is saved; an old price left active only shows up in the Paddle catalog.
            frappe.log_error(frappe.get_traceback(), f"Archive Paddle price {old_price}")
    return {"price_id": price_id, "product_id": product_id, "created": True}


def _module_product(saas_module: str, env: str) -> str:
    row = frappe.db.get_value(
        "SaaS Module",
        saas_module,
        ["name", "module_name", "description", "paddle_product_id", "paddle_product_environment"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("SaaS Module {0} not found.").format(saas_module))
    if row.get("paddle_product_id") and row.get("paddle_product_environment") == env:
        return row.paddle_product_id
    product_id = _api_create_product(row.get("module_name") or row.name, row.get("description"), row.name)
    frappe.db.set_value(
        "SaaS Module", row.name, {"paddle_product_id": product_id, "paddle_product_environment": env}
    )
    return product_id


# Tenant: checkout and customer portal


def _tenant_subscription(subscription: str):
    """The tenant admin's own subscription, with its plan, or an error."""
    from reckon_saas_platform.saas import _require_company_admin
    from reckon_saas_platform.tenant_security import resolve_tenant

    tenant = resolve_tenant()
    _require_company_admin(tenant)
    row = (
        frappe.db.get_value(
            "SaaS Subscription",
            subscription,
            ["name", "company", "company_admin", "plan", "status", "paddle_subscription_id", "paddle_customer_id",
             "paddle_status"],
            as_dict=True,
        )
        if isinstance(subscription, str) and subscription
        else None
    )
    if not row or row.company != tenant.company:
        frappe.throw(_("Subscription not found."), frappe.PermissionError)
    return row


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=60 * 60)
def create_checkout(subscription: str) -> dict:
    """Everything Paddle.js needs to open checkout for one of the tenant's subscriptions.

    The price comes from the plan on the server. The webhook checks the paid price
    belongs to the subscription's module before it extends anything.
    """
    row = _tenant_subscription(subscription)
    if row.status in HARD_BLOCKED_STATUSES:
        frappe.throw(_("This subscription is closed. Please contact support."))
    if row.get("paddle_subscription_id") and (row.get("paddle_status") or "") in LIVE_PADDLE_STATUSES:
        frappe.throw(_("This subscription is already paid by card. Use Manage card to change or cancel it."))
    plan = frappe.db.get_value(
        "SaaS Plan", row.plan, ["name", "currency", "paddle_price_id", "paddle_environment"], as_dict=True
    )
    if not plan or not card_payment_available(plan):
        frappe.throw(_("Card payment is not available for this plan."))
    settings = _settings()
    client_token = (settings.get("paddle_client_token") or "").strip()
    if not client_token:
        frappe.throw(_("Card payment is not set up yet. Please contact support."), PaddleNotConfigured)
    email = frappe.db.get_value("User", row.company_admin, "email") if row.get("company_admin") else None
    return {
        "environment": environment(),
        "client_token": client_token,
        "price_id": plan_price_id(plan),
        "customer_email": email or None,
        "custom_data": {"saas_subscription": row.name, "company": row.company},
    }


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=60 * 60)
def get_portal_url(subscription: str) -> dict:
    """A short-lived Paddle customer portal link to change the card or cancel."""
    row = _tenant_subscription(subscription)
    if not row.get("paddle_customer_id"):
        frappe.throw(_("This subscription is not paid by card."))
    return _api_portal_urls(row.paddle_customer_id, row.get("paddle_subscription_id"))


# Webhook


class _SignedRequest:
    """The shape paddle_billing's Verifier reads: ``headers`` and raw ``body`` bytes."""

    def __init__(self, headers: dict, body: bytes):
        self.headers = headers
        self.body = body


def verify_signature(headers, body: bytes, secret: str) -> bool:
    """Paddle's HMAC signature over the raw body, with the SDK's 5-second replay window."""
    if not secret or not body:
        return False
    header = headers.get(SIGNATURE_HEADER) if headers else None
    if not header:
        return False
    from paddle_billing.Notifications import Secret, Verifier

    try:
        return bool(Verifier().verify(_SignedRequest({SIGNATURE_HEADER: header}, body), Secret(secret)))
    except (ValueError, TypeError):
        # A malformed header is a failed check, never a server error.
        return False


@frappe.whitelist(allow_guest=True, methods=["POST"])
def webhook():
    """Paddle notification endpoint. Verifies, records once, queues, and answers fast."""
    request = getattr(frappe, "request", None)
    body = request.get_data(cache=True) if request is not None else b""
    secret = _password(_settings(), "paddle_webhook_secret")
    if not verify_signature(request.headers if request is not None else {}, body, secret):
        frappe.local.response["http_status_code"] = 401
        return {"ok": False}

    try:
        event = json.loads(body)
    except ValueError:
        frappe.local.response["http_status_code"] = 400
        return {"ok": False}
    event_id = event.get("event_id") if isinstance(event, dict) else None
    if not event_id:
        frappe.local.response["http_status_code"] = 400
        return {"ok": False}

    if record_event(event, body):
        frappe.enqueue(
            "reckon_saas_platform.paddle.process_event",
            event_id=event_id,
            queue="short",
            enqueue_after_commit=True,
        )
    return {"ok": True}


def record_event(event: dict, body: bytes) -> bool:
    """Store a verified event. False when it was already stored (a redelivery)."""
    event_id = event["event_id"]
    if frappe.db.exists(EVENT_DOCTYPE, event_id):
        return False
    try:
        frappe.get_doc(
            {
                "doctype": EVENT_DOCTYPE,
                "event_id": event_id,
                "event_type": event.get("event_type") or "",
                "occurred_at": _naive_utc(event.get("occurred_at")),
                "status": "Received",
                "payload": body.decode("utf-8") if isinstance(body, bytes) else body,
            }
        ).insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        return False
    return True


@frappe.whitelist(methods=["POST"])
def reprocess_event(event_id: str):
    """Run a failed event again after the vendor fixed its cause. System Manager only."""
    if "System Manager" not in frappe.get_roles():
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    return process_event(event_id)


def process_event(event_id: str) -> str:
    doc = frappe.get_doc(EVENT_DOCTYPE, event_id)
    if doc.status == "Processed":
        return doc.status
    doc.attempts = cint(doc.get("attempts")) + 1
    try:
        event = json.loads(doc.payload or "{}")
        handled = apply_event(event)
        doc.status = "Processed" if handled else "Ignored"
        doc.error = None
    except PaddleEventError as exc:
        doc.status = "Failed"
        doc.error = str(exc)
    except Exception:
        doc.status = "Failed"
        doc.error = frappe.get_traceback()[-2000:]
        frappe.log_error(frappe.get_traceback(), f"Paddle event {event_id}")
    doc.processed_on = now_datetime()
    doc.save(ignore_permissions=True)
    return doc.status


def apply_event(event: dict) -> bool:
    event_type = event.get("event_type") or ""
    data = event.get("data") or {}
    if event_type not in HANDLED_EVENTS:
        return False
    if event_type == "transaction.completed":
        return _apply_transaction(data)
    return _apply_subscription(data, event.get("occurred_at"))


def _find_saas_subscription(custom_data: dict | None, paddle_subscription_id: str | None):
    """The SaaS Subscription an event is about: by the Paddle id, else by checkout custom data."""
    fields = ["name", "company", "plan", "saas_module", "status", "paddle_subscription_id", "paddle_updated_at"]
    if paddle_subscription_id:
        row = frappe.db.get_value(
            "SaaS Subscription", {"paddle_subscription_id": paddle_subscription_id}, fields, as_dict=True
        )
        if row:
            return row
    custom_data = custom_data or {}
    name = custom_data.get("saas_subscription")
    if not name:
        return None
    row = frappe.db.get_value("SaaS Subscription", name, fields, as_dict=True)
    if not row or row.company != custom_data.get("company"):
        raise PaddleEventError(f"Checkout data names subscription {name} of another company.")
    if row.get("paddle_subscription_id") and paddle_subscription_id and row.paddle_subscription_id != paddle_subscription_id:
        raise PaddleEventError(
            f"{name} is already linked to Paddle subscription {row.paddle_subscription_id}, not {paddle_subscription_id}."
        )
    return row


def _module_price_ids(saas_module: str | None) -> set[str]:
    if not saas_module:
        return set()
    return {
        price
        for price in frappe.get_all(
            "SaaS Plan", filters={"saas_module": saas_module}, pluck="paddle_price_id", ignore_permissions=True
        )
        if price
    }


def _apply_transaction(data: dict) -> bool:
    """A completed (paid) transaction: a verified payment for the period Paddle billed."""
    paddle_subscription_id = data.get("subscription_id")
    if not paddle_subscription_id:
        return False  # A one-off charge; nothing here sells those.
    transaction_id = data.get("id")
    if not transaction_id:
        raise PaddleEventError("Transaction without an id.")
    row = _find_saas_subscription(data.get("custom_data"), paddle_subscription_id)
    if not row:
        raise PaddleEventError(f"No SaaS Subscription for Paddle subscription {paddle_subscription_id}.")

    _check_first_link(row, paddle_subscription_id, data.get("items"))
    _link_paddle_ids(row, paddle_subscription_id, data.get("customer_id"))

    currency = (data.get("currency_code") or "").upper()
    totals = (data.get("details") or {}).get("totals") or {}
    amount = from_lowest_unit(totals.get("grand_total") or totals.get("total") or 0, currency)
    period_end = _date_of((data.get("billing_period") or {}).get("ends_at"))

    payment = frappe.db.get_value(
        "SaaS Payment", {"gateway_provider": PROVIDER, "gateway_reference": transaction_id}, ["name", "status"],
        as_dict=True,
    )
    if payment and payment.status == "Verified":
        return True  # Already applied.
    blocked = row.status in HARD_BLOCKED_STATUSES
    if not payment:
        payment_doc = frappe.get_doc(
            {
                "doctype": "SaaS Payment",
                "subscription": row.name,
                "company": row.company,
                "amount": amount,
                "currency": currency,
                "status": "Pending Verification",
                "gateway_provider": PROVIDER,
                "gateway_reference": transaction_id,
                "notes": (
                    "Paid by card through Paddle while the subscription is "
                    f"{row.status}. Verify to reopen it, or refund in Paddle."
                    if blocked
                    else "Paid by card through Paddle."
                ),
            }
        ).insert(ignore_permissions=True)
        payment_name = payment_doc.name
    else:
        payment_name = payment.name
    if blocked:
        # The vendor suspended or cancelled it: money is recorded, the decision stays theirs.
        return True

    from reckon_saas_platform.saas import invalidate_operational_access_cache, verify_payment

    verify_payment(payment_name, reference=transaction_id, period_end=period_end)
    _close_placeholder_payments(row.name, payment_name, transaction_id)
    invalidate_operational_access_cache(row.company)
    return True


def _close_placeholder_payments(subscription: str, paid_by: str, transaction_id: str) -> None:
    """Close the unpaid payment the signup opened, once the card has paid for the same period.

    Only a payment nobody reported is closed: one with a transaction reference is a real manual
    payment waiting for the vendor, and stays in the queue.
    """
    for name in frappe.get_all(
        "SaaS Payment",
        filters={"subscription": subscription, "status": "Pending Verification", "name": ["!=", paid_by]},
        or_filters=[["gateway_reference", "is", "not set"], ["gateway_reference", "=", ""]],
        pluck="name",
        ignore_permissions=True,
    ):
        frappe.db.set_value(
            "SaaS Payment", name,
            {"status": "Rejected", "notes": f"Not needed: paid by card through Paddle ({transaction_id}, {paid_by})."},
        )


def _apply_subscription(data: dict, occurred_at) -> bool:
    paddle_subscription_id = data.get("id")
    row = _find_saas_subscription(data.get("custom_data"), paddle_subscription_id)
    if not row:
        raise PaddleEventError(f"No SaaS Subscription for Paddle subscription {paddle_subscription_id}.")
    occurred = _naive_utc(occurred_at)
    last = row.get("paddle_updated_at")
    if occurred and last and _as_datetime(last) > occurred:
        return True  # An older event arriving late must not undo a newer state.

    _check_first_link(row, paddle_subscription_id, data.get("items"))
    change = data.get("scheduled_change") or {}
    scheduled = ""
    if change.get("action"):
        when = _date_of(change.get("effective_at"))
        scheduled = f"{change['action']} on {when.isoformat()}" if when else change["action"]
    values = {
        "paddle_subscription_id": paddle_subscription_id,
        "paddle_status": data.get("status") or "",
        "paddle_scheduled_change": scheduled,
        "paddle_updated_at": occurred,
    }
    if data.get("customer_id"):
        values["paddle_customer_id"] = data["customer_id"]
    switched = _plan_for_items(row, data.get("items"))
    if switched:
        # An upgrade or downgrade made in Paddle: the plan, and with it the user and storage limits, follows.
        values.update(
            {
                "plan": switched.name,
                "price": switched.price,
                "currency": switched.currency,
                "billing_cycle": switched.billing_cycle or "Monthly",
                "plan_version": switched.plan_version or "1",
            }
        )
    frappe.db.set_value("SaaS Subscription", row.name, values)
    if switched:
        from reckon_saas_platform.saas import invalidate_operational_access_cache

        invalidate_operational_access_cache(row.company)
        try:
            frappe.get_doc("SaaS Subscription", row.name).add_comment(
                "Info", f"Plan changed from {row.plan} to {switched.name} by Paddle subscription {paddle_subscription_id}."
            )
        except Exception:
            pass  # the note is a courtesy; the change itself is saved
    # Access follows the paid dates (subscription_billing_state): a canceled or past-due
    # card subscription keeps access to the end of what was paid, then the grace days.
    return True


def _plan_for_items(row, items):
    """The SaaS Plan a Paddle subscription now bills, when it is a different plan of the same module.

    ``None`` when nothing should change: the same plan, more than one item, or a price that is no
    plan's current price in this environment (a renewal on a price the plan has since replaced).
    """
    price_ids = {((item.get("price") or {}).get("id")) for item in items or []}
    price_ids.discard(None)
    if len(price_ids) != 1 or not row.get("saas_module"):
        return None
    plan = frappe.db.get_value(
        "SaaS Plan",
        {"paddle_price_id": price_ids.pop(), "saas_module": row.saas_module, "paddle_environment": environment()},
        ["name", "price", "currency", "billing_cycle", "plan_version"],
        as_dict=True,
    )
    if not plan or plan.name == row.get("plan"):
        return None
    return plan


def _check_first_link(row, paddle_subscription_id: str, items) -> None:
    """Before a Paddle subscription is first linked, make sure it bills one of this module's prices.

    Checkout runs in the browser, so its price could be swapped. Once linked, renewals keep
    whatever price the subscription started on, even after the plan is synced to a new one.
    """
    if row.get("paddle_subscription_id") == paddle_subscription_id:
        return
    price_ids = {((item.get("price") or {}).get("id")) for item in items or []}
    price_ids.discard(None)
    if not price_ids or not price_ids <= _module_price_ids(row.get("saas_module")):
        raise PaddleEventError(
            f"Paddle price(s) {sorted(price_ids)} are not prices of module {row.get('saas_module')}; "
            "review and refund in Paddle."
        )


def _link_paddle_ids(row, paddle_subscription_id: str, customer_id: str | None) -> None:
    values = {}
    if row.get("paddle_subscription_id") != paddle_subscription_id:
        values["paddle_subscription_id"] = paddle_subscription_id
    if customer_id:
        values["paddle_customer_id"] = customer_id
    if values:
        frappe.db.set_value("SaaS Subscription", row.name, values)


def _parse_timestamp(value):
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _naive_utc(value):
    """Paddle's RFC 3339 time as a naive UTC datetime, the way Frappe stores Datetime."""
    return _parse_timestamp(value)


def _date_of(value):
    parsed = _parse_timestamp(value)
    return parsed.date() if parsed else None


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    return _parse_timestamp(str(value))
