"""Discount coupons: checking a code against a plan, the discount it gives, and counting its uses.

A coupon takes money off the **first payment** of a subscription (the first invoice); renewals are at the plan
price. Card checkout (Paddle) gets the same discount through a Paddle discount the coupon creates by itself.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import getdate, nowdate

DOCTYPE = "SaaS Coupon"


class CouponError(frappe.ValidationError):
    pass


def normalize(code) -> str:
    return re.sub(r"\s+", "", str(code or "")).upper()


def discount_for(coupon, price, currency: str | None) -> float:
    """The amount this coupon takes off ``price``. Never more than the price."""
    price = Decimal(str(price or 0))
    if price <= 0:
        return 0.0
    if coupon.get("discount_type") == "Percent":
        off = price * Decimal(str(coupon.get("percent") or 0)) / 100
    else:
        if (coupon.get("currency") or "") != (currency or ""):
            return 0.0
        off = Decimal(str(coupon.get("amount") or 0))
    return float(min(off, price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def get_valid(code, plan, cycle=None):
    """The coupon for ``code`` if it can be used on ``plan`` (a SaaS Plan name) now; otherwise raises CouponError."""
    code = normalize(code)
    row = frappe.db.get_value(DOCTYPE, code, ["*"], as_dict=True) if code else None
    if not row or not row.get("enabled"):
        frappe.throw(_("This coupon code is not valid."), CouponError)
    today = getdate(nowdate())
    if row.get("valid_from") and getdate(row.valid_from) > today:
        frappe.throw(_("This coupon is not active yet."), CouponError)
    if row.get("valid_until") and getdate(row.valid_until) < today:
        frappe.throw(_("This coupon has expired."), CouponError)
    if int(row.get("max_redemptions") or 0) and int(row.get("times_redeemed") or 0) >= int(row.max_redemptions):
        frappe.throw(_("This coupon has been fully used."), CouponError)
    from reckon_saas_platform.plan_billing import plan_variant

    plan_row = plan_variant(plan, cycle) if plan else None
    if not plan_row:
        frappe.throw(_("Please select a plan first."), CouponError)
    if row.get("plan") and row.plan != plan_row.name:
        frappe.throw(_("This coupon is not valid for this plan."), CouponError)
    if row.get("saas_module") and row.saas_module != plan_row.saas_module:
        frappe.throw(_("This coupon is not valid for this module."), CouponError)
    if row.get("discount_type") != "Percent" and (row.get("currency") or "") != (plan_row.currency or ""):
        frappe.throw(_("This coupon is for plans priced in {0}.").format(row.get("currency")), CouponError)
    row.plan_price, row.plan_currency = plan_row.price, plan_row.currency
    row.discount = discount_for(row, plan_row.price, plan_row.currency)
    return row


def redeem(code) -> None:
    """Count one use. The limit is checked in the same statement so two buyers cannot both take the last use."""
    frappe.db.sql(
        f"update `tab{DOCTYPE}` set times_redeemed = times_redeemed + 1 "
        "where name = %s and (max_redemptions = 0 or times_redeemed < max_redemptions)",
        (normalize(code),),
    )


def release(code) -> None:
    """Give a use back (the signup it was counted for did not go through)."""
    code = normalize(code)
    if code:
        frappe.db.sql(f"update `tab{DOCTYPE}` set times_redeemed = greatest(times_redeemed - 1, 0) where name = %s", (code,))


def money(amount, currency) -> str:
    from reckon_saas_platform import invoices

    return invoices.money(amount, currency)


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=60, seconds=60 * 60)
def check_coupon(plan: str, code: str, billing_cycle: str | None = None) -> dict:
    """What a coupon would take off a plan, for the signup and add-module pages."""
    try:
        row = get_valid(code, plan, billing_cycle)
    except CouponError as exc:
        return {"valid": False, "message": str(exc)}
    final = max(float(row.plan_price or 0) - row.discount, 0)
    return {
        "valid": True,
        "code": row.name,
        "discount": row.discount,
        "discount_text": money(row.discount, row.plan_currency),
        "final_text": money(final, row.plan_currency),
        "message": _("Coupon applied: {0} off your first payment.").format(money(row.discount, row.plan_currency)),
    }
