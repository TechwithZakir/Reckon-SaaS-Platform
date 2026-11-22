"""One plan, two ways to pay: monthly, or (when the plan allows it) a year at once.

There is no separate Yearly plan. A Monthly SaaS Plan with "Allow paying a year at once" sells a yearly option priced at
its monthly price times the months charged, in its own currency. ``variant_of`` returns the plan as it bills for a cycle,
so a yearly subscription, invoice, coupon or card price all read the same row.
"""

from __future__ import annotations

import frappe

PLAN_FIELDS = [
    "name", "plan_name", "plan_version", "saas_module", "covered_modules", "enabled", "currency", "price", "billing_cycle",
    "trial_days", "grace_days", "paddle_price_id", "paddle_environment", "paddle_price_signature",
    "allow_yearly_payment", "yearly_months_charged", "yearly_price", "paddle_yearly_price_id", "paddle_yearly_price_signature",
]


def yearly_offered(plan) -> bool:
    """True when this plan row sells a yearly payment: a Monthly plan with the switch on and its months set."""
    return bool(
        plan
        and (plan.get("billing_cycle") or "Monthly") == "Monthly"
        and plan.get("allow_yearly_payment")
        and int(plan.get("yearly_months_charged") or 0) > 0
    )


def cycle_for(plan, wanted: str | None) -> str:
    """The cycle a plan bills in: its own, or Yearly when it offers that and the buyer chose it."""
    if (wanted or "") == "Yearly" and yearly_offered(plan):
        return "Yearly"
    return plan.get("billing_cycle") or "Monthly"


def variant_of(plan, cycle: str | None):
    """``plan`` (a dict or document) as it bills for ``cycle``: the yearly option swaps in the yearly price and Paddle price."""
    out = frappe._dict(plan.as_dict() if callable(getattr(plan, "as_dict", None)) else plan)
    if cycle_for(plan, cycle) == "Yearly" and (plan.get("billing_cycle") or "Monthly") == "Monthly":
        out.update(
            price=plan.get("yearly_price"),
            billing_cycle="Yearly",
            paddle_price_id=plan.get("paddle_yearly_price_id"),
            paddle_price_signature=plan.get("paddle_yearly_price_signature"),
        )
    return out


def plan_variant(plan_name: str, cycle: str | None = None):
    """The SaaS Plan ``plan_name`` as it bills for ``cycle``, or None when there is no such plan."""
    row = frappe.db.get_value("SaaS Plan", plan_name, PLAN_FIELDS, as_dict=True) if plan_name else None
    return variant_of(row, cycle) if row else None
