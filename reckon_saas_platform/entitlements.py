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
