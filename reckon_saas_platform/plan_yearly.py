"""Paying a year at once for a monthly plan (pure: no Frappe imports, so the rules are unit-tested directly).

A Monthly plan row (one plan in one currency) can offer "pay a year at once": the vendor says how many months that one
payment covers (for example 10 in BDT and 11 in USD, each currency row has its own number). There is no separate Yearly
plan: ``plan_billing`` bills a yearly subscription from the Monthly row.
"""

from __future__ import annotations


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
