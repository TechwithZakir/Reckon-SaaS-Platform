"""Paying a year at once for a monthly plan (pure: no Frappe imports, so the rules are unit-tested directly).

A Monthly plan row (one plan in one currency) can offer "pay a year at once": the vendor says how many months that one
payment covers (for example 10 in BDT and 11 in USD, each currency row has its own number). The matching Yearly plan row
is then created or kept in step from the monthly one, so signup, invoices, renewals and the Paddle price sync all keep
working on ordinary Yearly rows.
"""

from __future__ import annotations

import re

# What a Yearly row inherits from the Monthly row it follows. The price, cycle, name and Paddle fields are its own.
YEARLY_COPY_FIELDS = (
    "plan_version", "saas_module", "covered_modules", "currency", "trial_days", "grace_days", "max_users", "max_storage_mb",
    "ai_fill_enabled", "ai_fill_daily_limit", "ai_fill_create_enabled", "features",
)


def validate_yearly(billing_cycle: str | None, allow: bool, months) -> str | None:
    """A message for the person when the yearly settings do not make sense, else None."""
    if not allow:
        return None
    if (billing_cycle or "Monthly") != "Monthly":
        return "Only a Monthly plan can offer paying a year at once."
    try:
        n = int(months or 0)
    except (TypeError, ValueError):
        n = 0
    if not 1 <= n <= 12:
        return "Months charged for the year must be a whole number from 1 to 12."
    return None


def yearly_price(monthly_price, months) -> float:
    """What one yearly payment costs: the monthly price for the months charged (2 decimals)."""
    return round(float(monthly_price or 0) * int(months), 2)


def yearly_plan_name(monthly_name: str) -> str:
    """The Yearly row's name, in the shop's own pattern: "Basic" -> "Basic (Yearly)", "Basic (USD)" -> "Basic (USD, Yearly)"."""
    name = (monthly_name or "").strip()
    if re.search(r"Yearly\)\s*$", name):
        return name
    match = re.search(r"\(([^)]*)\)\s*$", name)
    if match:
        return f"{name[:match.start()]}({match.group(1)}, Yearly)"
    return f"{name} (Yearly)"
