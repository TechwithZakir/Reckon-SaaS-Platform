"""Module entitlements of a subscription. No Frappe import, so the rule is unit-testable.

A subscription covers its primary module and any modules listed in ``covered_modules``
(one module key per line). One subscription can therefore give a company several modules.
"""

from __future__ import annotations


def parse_covered_modules(text: str | None) -> set[str]:
    return {line.strip() for line in (text or "").splitlines() if line.strip()}


def subscription_covers(module_key: str | None, primary: str | None, covered_text: str | None) -> bool:
    if not module_key:
        return False
    return module_key == primary or module_key in parse_covered_modules(covered_text)


def effective_user_limit(limits: list[int | None]) -> int | None:
    """How many users a company may have, from the user limits of its live subscriptions' plans.

    ``None`` means unlimited: the company has no live subscription, or any plan has a blank or zero limit.
    Otherwise the highest limit wins, so a company is never held below what its best plan allows.
    """
    if not limits or any(not limit or int(limit) <= 0 for limit in limits):
        return None
    return max(int(limit) for limit in limits)
